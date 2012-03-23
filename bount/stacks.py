from axel import Event
from fabric.context_managers import cd, lcd
from fabric.operations import get, put
import os
import imp
from managers import SqliteManager
from path import path
import sys
from bount import timestamp_str
from bount import cuisine
from bount.cuisine import dir_ensure, cuisine_sudo, dir_attribs, sudo
from bount.managers import UbuntuManager, PythonManager, ApacheManagerForUbuntu, DjangoManager, PostgresManager, ConfigurationException
from bount.utils import local_dir_ensure, file_delete, remote_home

__author__ = 'mturilin'


class Stack(object):
    def setup_os_dependencies(self):
        raise NotImplementedError('Method is not implemented')

    def setup_python_dependencies(self):
        raise NotImplementedError('Method is not implemented')

    def init_dirs(self):
        raise NotImplementedError('Method is not implemented')

    def init_database(self):
        raise NotImplementedError('Method is not implemented')

    def upload(self, update_submodules=True):
        raise NotImplementedError('Method is not implemented')

    def configure_webserver(self):
        raise NotImplementedError('Method is not implemented')

    def start_restart_webserver(self):
        raise NotImplementedError('Method is not implemented')

    def backup_database(self):
        raise NotImplementedError('Method is not implemented')

    def migrate_data(self):
        raise NotImplementedError('Method is not implemented')

    def download_db_dump(self):
        raise NotImplementedError('Method is not implemented')

    def restore_latest_db_dump(self):
        raise NotImplementedError('Method is not implemented')

    def download_media(self):
        raise NotImplementedError('Method is not implemented')

    def archive_local_media(self):
        raise NotImplementedError('Method is not implemented')

    def restore_latest_media(self):
        raise NotImplementedError('Method is not implemented')

    def setup_precompilers(self):
        pass

    def collect_static(self):
        raise NotImplementedError('Method is not implemented')

#    def update_local_media(self):
#        raise NotImplementedError('Method is not implemented')


current_stack = Stack()



# For names see http://bleach.wikia.com/wiki/Characters

def get_setting_from_list(settings_list, property):
    for setting_module in settings_list:
        if setting_module and hasattr(setting_module, property):
            return getattr(setting_module, property)


class DalkStack(Stack):
    """
    Stack supports:
    - Ubuntu 11.10
    - Apache 2
    - Postgres 8
    - Django 1.3

    Project contract:
    1. Fabric script should be run from the project root dir
    2. Project must use 'django.contrib.staticfiles' so we could create the dir for that
    3. Production symlink is used to provide server version os the settings file (or
    a part of the settings file). However, production configuration should not affect realtive
    path inside the project (for example relative path between project root and media path)
    4. Project database is PostgreSQL and the database settings are stored in settings.DATABASES['default']
    5. Dakl stack creates ./site directory in the project dir to place WSGI config file and virtualenv
    6. Logging dir will be created if settings or remote specific settings (from symlink) contain
    LOGGING_PATH variable

    """
    ubuntu = None
    django = None
    python = None
    database = None
    apache = None

    def __init__(self, settings_module, dependencies_path, project_name, source_root, use_virtualenv,
                 local_backup_dir='backup', precompilers=None):
        self.precompilers = precompilers or []

        self.ubuntu = UbuntuManager()
        self.ubuntu.dependencies = [
            "postgresql",
            "apache2",
            "libapache2-mod-wsgi",
            "unzip",
            "python",
            "python-setuptools",
            "python-dev",
            "build-essential",
            "rdiff-backup",
            "python-flup",
            "python-sqlite",
            "git",
            "python-recaptcha",
            "python-imaging",
            "python-pip",
            "libpq-dev",
            "python-psycopg2"
        ]

        for precomp in self.precompilers:
            self.ubuntu.dependencies += precomp.get_os_dependencies()

        self.apache = ApacheManagerForUbuntu()

        # Django
        project_local_path = path(os.getcwd()) # project root is current working dir

        sys.path.append(source_root)
        module = imp.find_module(settings_module)
        settings = imp.load_module(settings_module, *module)

        remote_proj_path = "/usr/local/share/" + project_name

        # SRC - a directory containing settings.py will be considered src path for the server
        # override if necessary
        src_relative_path = path(project_local_path).relpathto(source_root)
        remote_src_path = path(remote_proj_path).joinpath(src_relative_path)

        # remote site path is a directory containing wsgi handler. Also it's recommended to put there
        #
        remote_site_path = path(remote_proj_path).joinpath('site').abspath()

        # MEDIA_PATH
        self.local_media_root = settings.MEDIA_ROOT
        media_rel_path = path(project_local_path).relpathto(self.local_media_root)
        media_root = path(remote_proj_path).joinpath(media_rel_path)
        media_url = settings.MEDIA_URL

        # STATIC_PATH - warning, static path will be empty and contain only symlinks to STATICFILES_DIRS
        # and apps' static files
        static_rel_path = path(project_local_path).relpathto(settings.STATIC_ROOT)
        static_root = path(remote_proj_path).joinpath(static_rel_path)
        static_url = settings.STATIC_URL

        try:
            server_admin = settings.ADMINS[0][1]
        except IndexError:
            server_admin = 'NOBODY'

        self.django = DjangoManager(project_name, remote_proj_path, project_local_path, remote_site_path,
            remote_src_path, settings_module=settings_module,
            use_virtualenv=use_virtualenv, virtualenv_path=remote_site_path,
            media_root=media_root, media_url=media_url, static_root=static_root, static_url=static_url,
            server_admin=server_admin, precompilers=precompilers)

        self.django.webserver = self.apache

        # LOGGING_PATH
        if hasattr(settings, 'LOGGING_PATH'):
            self.django.log_path = settings.LOGGING_PATH


        # Postgres
        if 'postgresql' in settings.DATABASES['default']['ENGINE']:
            # we try to use the same username and password for Postgres as for the local
            # override right after creation if need different
            self.database = PostgresManager(
                database_name=settings.DATABASES['default']['NAME'],
                user=settings.DATABASES['default']['USER'],
                password=settings.DATABASES['default']['PASSWORD'],
            )
        elif 'sqlite' in settings.DATABASES['default']['ENGINE']:
            self.database = SqliteManager('')
        else:
            raise ConfigurationException('Project\'s database is not PostgreSQL or Sqlite')



        # Temporary local paths - override if needed
        self.site_local_path = path(project_local_path).joinpath('site')
        self.local_backup_dir = path(project_local_path).joinpath(local_backup_dir)
        self.local_db_dump_dir = self.local_backup_dir.joinpath('db_dump')
        self.local_media_dump_dir = self.local_backup_dir.joinpath('media_dump')


        # Python manage
        self.python = PythonManager(dependencies_path,
            [('django', '1.3.1'),
                'south', ],
            use_virtualenv, remote_site_path)

        for precomp in self.precompilers:
            self.python.dependencies += precomp.get_python_dependencies()

        self.django.python = self.python


    def setup_os_dependencies(self):
        self.ubuntu.refresh_sources()
        self.ubuntu.setup_dependencies()

    def setup_python_dependencies(self):
        self.python.init(delete_if_exists=False, python_path=self.django.src_root)
        self.python.setup_dependencies()
        self.django.configure_virtualenv()

    def setup_precompilers(self):
        super(DalkStack, self).setup_precompilers()
        for precomp in self.precompilers:
            precomp.setup()


    def init_database(self):
        self.database.configure(enable_remote_access=True)
        self.database.create_user()
        self.database.create_database(delete_if_exists=False)

    def init_dirs(self):
        self.django.init()

    def restart_webserver(self):
        self.apache.restart()

    def upload(self, update_submodules=True):
        self.django.upload_code(update_submodules)

    def collect_static(self):
        self.django.collect_static()


    def configure_webserver(self):
        self.django.configure_wsgi()
        self.apache.configure_webserver(self.django.project_name, self.django.create_apache_config(),
            delete_other_sites=True)
        self.apache.start()

    def start_restart_webserver(self):
        self.apache.restart()

    def _create_db_backup_name(self):
        return "%s_db_%s.sql.gz" %\
               (self.django.project_name,
                timestamp_str())

    def backup_database(self):
        self.database.backup_database(self._create_db_backup_name())

    def migrate_data(self):
        self.django.migrate_data()


    def download_db_dump(self):
        remote_file_basename = self._create_db_backup_name()
        remote_dir = "/tmp"
        remote_file_path = "%s/%s" % (remote_dir, remote_file_basename)

        dir_ensure(remote_dir, mode='777')
        self.database.backup_database(remote_file_basename, folder=remote_dir, zip=True)

        local_dir_ensure(self.local_db_dump_dir)
        get(remote_file_path, self.local_db_dump_dir)

        with cuisine_sudo(): file_delete(remote_file_path)

    def latest_db_dump_basename(self):
        sql_file_list = [file for file in os.listdir(self.local_db_dump_dir)
                         if file.endswith(".sql.gz") and file.startswith(self.django.project_name)]
        if not sql_file_list:
            print("No files found")

        return sorted(sql_file_list)[-1]


    def restore_latest_db_dump(self):
        dump_basename = self.latest_db_dump_basename()
        dump_path = path(self.local_db_dump_dir).joinpath(dump_basename)
        remote_dump_path = "~/%s" % dump_basename

        put(dump_path, "")

        self.database.init_database(init_sql_file=remote_dump_path, delete_if_exists=True, unzip=True)

        self.django.migrate_data()

        with cuisine_sudo(): file_delete(remote_dump_path)

    def download_media(self):
        media_dump_basename = "%s_media_%s.tar.gz" % (self.django.project_name, timestamp_str())
        media_dump_remote_path = "%s/%s" % (remote_home(), media_dump_basename)

        media_dump_local_path = self.local_media_dump_dir.joinpath(media_dump_basename)

        with cd(self.django.media_root): cuisine.run("tar -cvzf %s ." % media_dump_remote_path)
        cuisine.file_attribs(media_dump_remote_path, '777')

        get(media_dump_remote_path, media_dump_local_path)

        with cuisine_sudo(): file_delete(media_dump_remote_path)

    def archive_local_media(self):
        local_dir_ensure(self.local_media_dump_dir)

        media_dump_basename = "%s_media_%s.tar.gz" % (self.django.project_name, timestamp_str())
        media_dump_local_path = self.local_media_dump_dir.joinpath(media_dump_basename)

        with lcd(self.local_media_root): cuisine.local("tar -cvzf %s ." % media_dump_local_path)


    def latest_media_dump_basename(self):
        upload_file_list = [file for file in os.listdir(self.local_media_dump_dir)
                            if file.endswith(".tar.gz") and file.startswith("%s_media" % self.django.project_name)]
        if not upload_file_list:
            print("No files found")
        upload_basename = sorted(upload_file_list)[-1]
        return upload_basename

    def restore_latest_media(self):
        dump_basename = self.latest_media_dump_basename()

        dump_local_path = self.local_media_dump_dir.joinpath(dump_basename)
        dump_remote_path = path(self.django.media_root).joinpath(dump_basename)

        put(str(dump_local_path), str(dump_remote_path), use_sudo=True, mode=0777)

        with cd(self.django.media_root):
            sudo("tar -xvzf %s" % dump_remote_path)

        with cuisine_sudo():
            dir_attribs(self.django.media_root, mode='777', recursive=True)

        with cuisine_sudo(): file_delete(dump_remote_path)


    @classmethod
    def build_stack(cls, settings_path, dependencies_path, project_name, source_root,
                    use_virtualenv=True, precompilers=None):
        global current_stack

        current_stack = cls(settings_path, dependencies_path, project_name, source_root,
            use_virtualenv, precompilers=precompilers)

        return current_stack

#    def update_local_media(self):
#        zip_file = path(local_upload_dump_dir).joinpath(self.latest_uploaded_archive())
#        print("the lastest upload copy found: %s" % zip_file)
#        local_gunzip(zip_file, settings.MEDIA_ROOT, overwrite=True)


before_install = Event()
after_install = Event()

def install():
    before_install()

    current_stack.setup_os_dependencies()
    current_stack.setup_python_dependencies()
    current_stack.setup_precompilers()

    current_stack.init_database()

    current_stack.init_dirs()
    current_stack.upload()
    current_stack.migrate_data()
    current_stack.collect_static()
    current_stack.configure_webserver()
    current_stack.start_restart_webserver()

    after_install()


before_update_code = Event()
after_update_code = Event()

def update_code():
    before_update_code()

    current_stack.upload()
    current_stack.start_restart_webserver()

    after_update_code()


before_update = Event()
after_update = Event()

def update():
    before_update()

    backup_database()
    current_stack.upload()
    current_stack.migrate_data()
    current_stack.collect_static()
    current_stack.start_restart_webserver()

    after_update()

def update_python_dependencies():
    current_stack.setup_python_dependencies()


before_backup_database = Event()
after_backup_database = Event()

def backup_database():
    before_backup_database()
    current_stack.backup_database()
    after_backup_database()


def download_db_dump():
    current_stack.download_db_dump()


def restore_latest_db_dump():
    current_stack.restore_latest_db_dump()


def start_restart_webserver():
    current_stack.start_restart_webserver()


def download_media():
    current_stack.download_media()


def restore_latest_media():
    current_stack.restore_latest_media()


def archive_local_media():
    current_stack.archive_local_media()
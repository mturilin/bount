#coding=utf-8
import textwrap
from bount.managers.django import DjangoManager, ConfigurationException, django_check_config
from bount.managers.gunicorn import GunicornDjangoManager
from bount.managers.ngnix import NginxManager
from bount.managers.postgres import PostgresManager
from bount.managers.python import PythonManager
from bount.managers.sqlite import SqliteManager
from bount.managers.ubuntu import UbuntuManager
from fabric.context_managers import cd, lcd
from fabric.operations import get, put
import os
import imp
from bount.stacks import Stack
from path import path
import sys
from bount import timestamp_str
from bount import cuisine
from bount.cuisine import dir_ensure, cuisine_sudo, dir_attribs, sudo, run
from bount.utils import local_dir_ensure, file_delete, remote_home, dir_delete
from bount import stacks

__author__ = 'mturilin'


# For names see http://bleach.wikia.com/wiki/Characters

def get_setting_from_list(settings_list, property):
    for setting_module in settings_list:
        if setting_module and hasattr(setting_module, property):
            return getattr(setting_module, property)


NGNIX_TEMPLATE = """
server {
    listen   80;
    server_name %(remote_host)s;

    root /path/to/test/hello;

    # serve directly - analogous for static/staticfiles
    location %(media_url)s {
        # if asset versioning is used
        alias %(media_root)s/;
    }

    location %(static_url)s {
        # if asset versioning is used
        alias %(static_root)s/;
    }

    location / {
        proxy_pass_header Server;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_connect_timeout 10;
        proxy_read_timeout 10;
        proxy_pass http://localhost:8000/;
    }
    # what to serve if upstream is not available or crashes
    error_page 500 502 503 504 /media/50x.html;
}"""


class DjangoNgnixGunicornManager(DjangoManager):
    @django_check_config
    def create_ngnix_config(self):
        return NGNIX_TEMPLATE % self.__dict__

GOETHE_DERSCR = """"=======================================================
Welcome to Goethe stack!
Goethe (ゲーテ, Gēte) is Yoshino Sōma's doll. It takes the form of a finger claw (on her left middle finger) and bracelet (on her right wrist) when sealed. To unseal Goethe, Yoshino strikes the two pieces together to create a spark, which releases him when she takes the fire created from the spark and creates an arc over her head, as a fire rages around the area. Goethe is a fire elemental, able to create and control flame. While mostly humanoid in appearance consisting of hardened magma and flames, it has no legs but fire acting as propulsion jets.
======================================================="""
GOETHE_DERSCR_WRAPPED = textwrap.fill(GOETHE_DERSCR, 60)

class GoetheStack(Stack):
    """
    Stack supports:
    - Ubuntu 12.04 LTS - I plan to keep it this way until next LTS
    - Nginx
    - Postgres 8
    - Django 1.4

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
    webserver = None
    services = []


    def local_project_to_remote(self, local_path):
        rel_path = path(self.project_local_path).relpathto(local_path)
        return path(self.remote_proj_path).joinpath(rel_path)

    def __init__(self, settings_module, dependencies_path, project_name, source_root, use_virtualenv,
                 local_backup_dir='backup', precompilers=None, number_of_django_workers=1, number_of_ngnix_workers=2,
                 environment=None):
        print GOETHE_DERSCR_WRAPPED
        print "Added environment:", repr(environment)

        self.precompilers = precompilers or []

        self.ubuntu = UbuntuManager()
        self.ubuntu.dependencies = [
            "postgresql",
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
            "python-psycopg2",
            "ntp",
            "nginx"
        ]

        for precomp in self.precompilers:
            self.ubuntu.dependencies += precomp.get_os_dependencies()

        self.webserver = NginxManager()
        self.services.append(self.webserver)

        # Django
        self.project_local_path = path(os.getcwd()) # project root is current working dir

        sys.path.append(source_root)
        os.environ.update(environment)
        module = imp.find_module(settings_module)
        settings = imp.load_module(settings_module, *module)

        self.remote_proj_path = "/usr/local/share/" + project_name

        # SRC - a directory containing settings.py will be considered src path for the server
        # override if necessary
        remote_src_path = self.local_project_to_remote(source_root)

        # remote site path is a directory containing all locally changes files, such as media and ENV
        remote_site_path = path(self.remote_proj_path).joinpath('site').abspath()

        # MEDIA_PATH
        self.local_media_root = settings.MEDIA_ROOT
        media_root = self.local_project_to_remote(self.local_media_root)
        media_url = settings.MEDIA_URL

        # STATIC_PATH - warning, static path will be empty and contain only symlinks to STATICFILES_DIRS
        # and apps' static files
        static_rel_path = path(self.project_local_path).relpathto(settings.STATIC_ROOT)
        static_root = path(self.remote_proj_path).joinpath(static_rel_path)
        static_url = settings.STATIC_URL

        try:
            server_admin = settings.ADMINS[0][1]
        except IndexError:
            server_admin = 'NOBODY'

        self.django = DjangoNgnixGunicornManager(project_name, self.remote_proj_path, self.project_local_path, remote_site_path,
            remote_src_path, settings_module=settings_module,
            use_virtualenv=use_virtualenv, virtualenv_path=remote_site_path,
            media_root=media_root, media_url=media_url, static_root=static_root, static_url=static_url,
            server_admin=server_admin, precompilers=precompilers, use_south=("south" in settings.INSTALLED_APPS))

        self.django.webserver = self.webserver

        # LOGGING_PATH
        if hasattr(settings, 'LOGGING_PATH') and settings.LOGGING_PATH:
            self.django.log_path = self.local_project_to_remote(settings.LOGGING_PATH)
        else:
            self.django.log_path = remote_site_path.joinpath("logs")


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
        self.site_local_path = path(self.project_local_path).joinpath('site')
        self.local_backup_dir = path(self.project_local_path).joinpath(local_backup_dir)
        self.local_db_dump_dir = self.local_backup_dir.joinpath('db_dump')
        self.local_media_dump_dir = self.local_backup_dir.joinpath('media_dump')


        # Python manage
        self.python = PythonManager(dependencies_path,
            ['django',
             'gunicorn'],
            use_virtualenv, remote_site_path)

        for precomp in self.precompilers:
            self.python.dependencies += precomp.get_python_dependencies()

        self.django.python = self.python

        self.gunicorn = GunicornDjangoManager(
            project_name + "_gunicorn",
            self.webserver.webserver_user,
            self.webserver.webserver_group,
            number_of_django_workers,
            self.python.virtualenv_path(),
            self.remote_proj_path, self.django.src_root, self.django.log_path,
            self.django.remote_site_path,
            environment=environment)

        self.services.append(self.gunicorn)


    def setup_os_dependencies(self):
        self.ubuntu.refresh_sources()
        self.ubuntu.setup_dependencies()

    def setup_python_dependencies(self):
        self.python.init(delete_if_exists=False, python_path=self.django.src_root)
        self.python.setup_dependencies()
        self.django.configure_virtualenv()

    def setup_precompilers(self):
        super(GoetheStack, self).setup_precompilers()
        for precomp in self.precompilers:
            precomp.setup()


    def init_database(self):
        self.database.configure(enable_remote_access=True)
        self.database.create_user()
        self.database.create_database(delete_if_exists=False)

    def init_dirs(self):
        self.django.init()
        #dir_ensure(self.remote_log_path, mode='777', owner=self.webserver.webserver_user, group=self.webserver.webserver_group)


    def start_webserver(self):
        for service in self.services:
            service.start()


    def upload(self, update_submodules=True):
        self.django.upload_code(update_submodules)

    def collect_static(self):
        self.django.collect_static()


    def configure_webserver(self):
        self.stop_webserver()
        self.django.configure_wsgi()
        self.webserver.create_website(self.django.project_name, self.django.create_ngnix_config())

        for service in self.services:
            service.setup()

        self.start_webserver()

    def restart_webserver(self):
        for service in self.services:
            service.restart()

    def stop_webserver(self):
        for service in self.services:
            service.stop()


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

    def media_restore_local_latest(self):
        dump_basename = self.latest_media_dump_basename()
        dump_local_path = self.local_media_dump_dir.joinpath(dump_basename)

        dir_delete(self.local_media_root)
        dir_ensure(self.local_media_root)

        with cd(self.local_media_root):
            run("tar -xvzf %s" % dump_local_path)


    def enable_debug(self):
        self.django.set_debug(True)
        self.restart_webserver()

    def disable_debug(self):
        self.django.set_debug(False)
        self.restart_webserver()

    def recreate_database(self):
        self.database.create_database(delete_if_exists=True)

    def enable_ntpd(self):
        self.ubuntu.enable_ntpd()

    def disable_ntpd(self):
        self.ubuntu.disable_ntpd()

    @classmethod
    def build_stack(cls, settings_module, dependencies_path, project_name, source_root,
                    use_virtualenv=True, precompilers=None, environment=None):
        stacks.current_stack = cls(settings_module, dependencies_path, project_name, source_root,
            use_virtualenv, precompilers=precompilers, environment=environment)

        return stacks.current_stack







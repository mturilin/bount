import logging
from fabric.context_managers import lcd, cd
from fabric.operations import *
from path import path
from bount import cuisine
from bount.cuisine import cuisine_sudo, file_attribs
from bount.utils import local_file_delete, file_delete, python_egg_ensure, file_unzip, text_replace_line_re, sudo_pipeline, sym_link, clear_dir, copy_directory_content

__author__ = 'mturilin'

logger = logging.getLogger(__file__)

def generic_install(dependencies, command):
    for dep in dependencies:
        if isinstance(dep, str):
            dep_str = dep
        elif isinstance(dep, tuple):
            dep_str = dep[0] if len(dep) == 1 else "%s==%s" % dep
        else:
            raise RuntimeError("Dependency must be string or tuple, %s found" % str(dep))

        command(dep_str)


def aptget_install(dependencies):
    generic_install(dependencies, lambda dep_str: cuisine.package_ensure(dep_str
    ))


def pip_install(dependencies):
    generic_install(dependencies, lambda dep_str: python_egg_ensure(dep_str))


class UbuntuManager():
    def __init__(self):
        self.dependencies = []

    def setup_dependencies(self):
        aptget_install(self.dependencies)


class PythonManager():
    def __init__(self):
        self.dependencies = []

    def setup_dependencies(self):
        pip_install(self.dependencies)


class PostgresManager(object):
    def __init__(self, database_name, user, password, superuser_login="postgres", host="localhost"):
        self.database_name = database_name
        self.user = user
        self.password = password
        self.superuser_login = superuser_login
        self.host = host
        self.db_backup_folder = "/tmp"

    def version(self):
        version_info = run("psql --version")
        version_line = version_info.split("\n")[0].strip()
        assert len(version_line) > 7, "There's something wrong with Postgres version info: " + version_info
        return version_line[-6:]

    def short_version(self):
        return self.version()[0:4].strip()

    def create_user(self):
        sudo_pipeline("echo CREATE USER %s WITH PASSWORD \\'%s\\' | psql" % (self.user, self.password),
                   user=self.superuser_login)


    def create_database(self, delete_if_exists=False):
        if delete_if_exists and self.database_exists():
            self.drop_database()

        if not self.database_exists():
            sudo_pipeline("echo CREATE DATABASE %s WITH OWNER %s  ENCODING \\'UNICODE\\' TEMPLATE template0 | psql" % (
                self.database_name, self.user),
                       user=self.superuser_login)
            return "Database was created"
        return "Database already exists"


    def drop_database(self):
        sudo("service postgresql restart")
        sudo("echo DROP DATABASE %s | psql" % self.database_name, user=self.superuser_login)

    def pg_hba_path(self):
        return '/etc/postgresql/%s/main/pg_hba.conf' % self.short_version()

    def process_pg_hba_conf(self):
        with cuisine_sudo():
            pg_hba = cuisine.file_read(self.pg_hba_path())

            # replaces "host all all 127.0.0.1/32 md5" type of lines
            # with "host all all 0.0.0.0/0 md5"
            new_text, replaced = text_replace_line_re(
                pg_hba,
                "^host[\s\w\./]+$",
                "host\tall\tall\t0.0.0.0/0\tmd5")

        return new_text

    def postgresql_conf_path(self):
        return '/etc/postgresql/%s/main/postgresql.conf' % self.short_version()

    def process_postgresql_conf(self):
        with cuisine_sudo():
            pg_hba = cuisine.file_read(self.postgresql_conf_path())

            # replaces "#listen_addresses = 'localhost'	" type of lines
            # with "listen_addresses = '*'"
            new_text, replaced = text_replace_line_re(
                pg_hba,
                ".*listen_addresses\s*=",
                "listen_addresses = '*'	")

        return new_text


    def configure(self, enable_remote_access=False):
        if enable_remote_access:
            with cuisine_sudo():
                cuisine.file_write(self.pg_hba_path(), self.process_pg_hba_conf())
                cuisine.file_write(self.postgresql_conf_path(), self.process_postgresql_conf())


    def database_exists(self):
        result = sudo(
            "psql template1 -c \"SELECT 1 AS result FROM pg_database WHERE datname='%s'\"; "
            % self.database_name,
            user=self.superuser_login)

        if "0" in result:
            return False
        elif "1" in result:
            return True
        else:
            raise RuntimeError("Unknown PostgreSQL result: %s" % result)

    def backup_database(self, filename, zip=False, folder=None):
        folder = folder or self.db_backup_folder

        with cuisine.cuisine_sudo():
            cuisine.dir_ensure(folder, recursive=True, mode="777")

        file_full_path = "/".join([folder, filename])

        run("echo *:*:%s:%s:%s > ~/.pgpass" % (self.database_name, self.user, self.password))
        run("chmod 0600 ~/.pgpass")

        sudo_pipeline(("pg_dump %s | gzip > %s" if zip else "pg_dump %s > %s")
             % (self.database_name, file_full_path), user=self.superuser_login)

    def init_database(self, init_sql_file, delete_if_exists=False, unzip=False):
        self.create_database(delete_if_exists)
        if unzip:
            command = "cat %s | gunzip | psql %s"
        else:
            command = "cat %s | psql %s"
        return sudo_pipeline(command % (init_sql_file, self.database_name), user=self.superuser_login)


class ApacheManager():
    def __init__(self):
        pass

    def status(self):
        result = run("service apache2 status")
        if "running" in result:
            return "running"
        else:
            return "stopped"

    def restart(self):
        sudo("service apache2 restart")

    def start(self):
        sudo("service apache2 start")

    def stop(self):
        sudo("service apache2 stop")


    def configure_webserver(self, name, config, delete_other_sites=False):
        if delete_other_sites:
            with cuisine_sudo():
                clear_dir('/etc/apache2/sites-enabled')

        with cuisine_sudo():
            cuisine.file_write('/etc/apache2/sites-enabled/%s' % name, config)


class GitManager:
    def __init__(self, path):
        self.dir = path

    def local_archive(self, filename, remove_first=False):
        with lcd(self.dir):
            if remove_first: local("rm -f %s" % filename)
            branch = "HEAD"
            local("git archive %s --format zip --output %s" % (branch, filename))


class HgManager:
    def __init__(self, path):
        self.dir = path

    def local_archive(self, filename, remove_first=False):
        # Somebody needs to test this one - I don't use Mercurial
        with lcd(self.dir):
            if remove_first: local("rm -f %s" % filename)
            local("hg archive -t zip %s" % filename)


class DjangoManager:
    """
        This manager uses Django Project Convention:
    """

    def __init__(self, project_name, site_path, project_local_path):
        logger.info("Creating DjangoManager")

        self.project_name = project_name
        self.project_local_path = project_local_path
        self.site_path = site_path
        self.webserver = None

        self.project_path = site_path + "/" + project_name
        self.src_subdir = "src"
        self.src_path = path(self.project_path).joinpath(self.src_subdir)
        self.log_path = site_path + "/logs"
        self.media_path = self.project_path + "/media"
        self.upload_path = site_path + "/uploads"

        # static_upload contains content that should be placed into upload directory after the installation
        self.static_upload = self.project_path + "/static_upload"

        self.webserver_user = "www-data"
        self.webserver_group = "www-data"

        self.archive_file = "source_tree.zip"
        self.scm = GitManager(self.project_local_path)

        # web server configuration
        self.document_root_path = self.media_path

        self.media_root = "/s/"
        self.upload_root = "/u/"

        self.env_path = "/usr/local"
        self.wsgi_handler_path = self.site_path + "/wsgi_handler.py"

        self.settings_module = "production.py"

        self.server_admin = "admin@host.org"

        logger.info(self.__dict__)

    def init(self):
        """
        Should be called at least one before uploading the code. Creates project dirs and copies static_upload files.
        """
        with cuisine_sudo():
            cuisine.dir_ensure(self.site_path, recursive=True, owner=self.webserver_user, group=self.webserver_group)
            cuisine.dir_ensure(self.project_path, recursive=True, owner=self.webserver_user, group=self.webserver_group)
            cuisine.dir_ensure(self.log_path, recursive=True, owner=self.webserver_user, group=self.webserver_group)
            cuisine.dir_ensure(self.upload_path, recursive=True, owner=self.webserver_user, group=self.webserver_group)


    def before_upload_code(self):
        pass

    def after_upload_code(self):
        pass

    def upload_code(self):
        if self.webserver:
            self.webserver.stop()

        self.before_upload_code()

        with cuisine_sudo():
            self.clear_remote_dir()

        # zip and upload file
        archive_remote_full_path = "%s/%s" % (self.project_path, self.archive_file)
        archive_local_full_path = "%s/%s" % (self.project_local_path, self.archive_file)
        self.scm.local_archive(archive_local_full_path, remove_first=True)
        put(archive_local_full_path, archive_remote_full_path, use_sudo=True)
        local_file_delete(archive_local_full_path)

        #unzip file
        with cuisine_sudo():
            file_unzip(archive_remote_full_path, self.project_path)
            file_delete(archive_remote_full_path)

        cuisine.run("cd %s" % self.src_path)
        cuisine.run("pwd")

        # configure settings
        with cd(self.src_path), cuisine_sudo():
            cuisine.run("pwd")
            sym_link(self.settings_module, "config.py")

        with cuisine_sudo():
            cuisine.dir_attribs(self.site_path, mode="777", recursive=True)
            file_attribs(path(self.src_path).joinpath("manage.py"), mode="777")

            # copy static upload
            copy_directory_content(self.static_upload, self.upload_path)

        ## upload ends here

        self.after_upload_code()

        if self.webserver:
            self.webserver.start()

    def migrate_data(self):
        self.manage("syncdb  --noinput")
        self.manage("migrate")


    def dump_database_to_json(self):
        local("python ./src/manage.py dumpdata studentoffice auth > ./src/studentoffice/fixtures/initial_data.json")

    def manage(self, command):
        """
        Django manage.py command execution. Local safe - could be used in cuisine_local() block.
        """
        with cd(self.src_path):
            print cuisine.run("pwd")
            cuisine.run("./manage.py %s" % (command))

    def set_debug(self, debug):
        with cuisine_sudo():
            settings_file_path = path(self.src_path).joinpath(self.settings_module)
            settings_content = cuisine.file_read(settings_file_path)

            # replaces "#listen_addresses = 'localhost'	" type of lines
            # with "listen_addresses = '*'"
            settings_content, replaced = text_replace_line_re(
                settings_content,
                "^DEBUG\s*=",
                "DEBUG=%s" % debug)

            return cuisine.file_write(settings_file_path, settings_content), replaced


    def clear_remote_dir(self):
        dir = self.project_path
        clear_dir(dir)

    def create_apache_config(self):
        apache_template = cuisine.text_strip_margin(
            """
            |<VirtualHost *:80>
            |    ServerAdmin $server_admin
            |
            |    DocumentRoot $upload_path
            |
            |    Alias $media_root $media_path/
            |    <Directory $media_path>
            |           Order deny,allow
            |           Allow from all
            |    </Directory>
            |
            |    Alias $upload_root $upload_path/
            |    <Directory $upload_path>
            |           Order deny,allow
            |           Allow from all
            |    </Directory>
            |
            |    WSGIScriptAlias / $wsgi_handler_path
            |
            |    WSGIDaemonProcess $project_name
            |    WSGIProcessGroup %{GLOBAL}
            |
            |</VirtualHost>
            """)

        if self.document_root_path and self.media_path and self.upload_path:
            return cuisine.text_template(apache_template, self.__dict__)
        else:
            raise RuntimeError(
                "Properties document_root_path, media_path, and upload_path should be set to configure web server")


    def create_wsgi_handler(self):
        wsgi_template = cuisine.text_strip_margin(
            """
            |import os
            |import sys
            |import site
            |
            |# prevent errors with 'print' commands
            |sys.stdout = sys.stderr
            |
            |# adopted from http://code.google.com/p/modwsgi/wiki/VirtualEnvironments
            |def add_to_path(dirs):
            |    # Remember original sys.path.
            |    prev_sys_path = list(sys.path)
            |
            |    # Add each new site-packages directory.
            |    for directory in dirs:
            |        site.addsitedir(directory)
            |
            |    # Reorder sys.path so new directories at the front.
            |    new_sys_path = []
            |    for item in list(sys.path):
            |        if item not in prev_sys_path:
            |            new_sys_path.append(item)
            |            sys.path.remove(item)
            |    sys.path[:0] = new_sys_path
            |
            |add_to_path([
            |     os.path.normpath('$site_root/lib/python2.5/site-packages'),
            |     os.path.normpath('$site_root/lib/python2.6/site-packages'),
            |     os.path.normpath('$site_root/lib/python2.7/site-packages'),
            |
            |#     os.path.normpath('$src_path' + '/..'),
            |     '$src_path',
            |])
            |
            |os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
            |
            |import django.core.handlers.wsgi
            |application = django.core.handlers.wsgi.WSGIHandler()
            """)

        if self.env_path:
            return cuisine.text_template(wsgi_template, self.__dict__)
        else:
            raise RuntimeError("Properties env_path and $project_local_path should be set to configure web server")


    def configure_wsgi(self):
        cuisine.file_write(self.wsgi_handler_path, self.create_wsgi_handler())
























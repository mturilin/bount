import os
from contextlib import contextmanager
from functools import wraps
import logging
from fabric.context_managers import lcd, cd, prefix
from fabric.operations import *
from path import path
import types
from bount import timestamp_str
from bount import cuisine
from bount.cuisine import cuisine_sudo, dir_ensure, file_read, text_ensure_line, file_write, dir_attribs
from bount.utils import local_file_delete, file_delete, python_egg_ensure, file_unzip, text_replace_line_re, sudo_pipeline, clear_dir, dir_delete, remote_home, unix_eol, local_dir_ensure, local_dirs_delete

__author__ = 'mturilin'

logger = logging.getLogger(__file__)

def generic_install(dependencies, command):
    for dep in dependencies:
        if isinstance(dep, str):
            dep_str = dep
        elif isinstance(dep, tuple) or isinstance(dep, types.ListType):
            print(dep)
            dep_str = dep[0] if len(dep) == 1 else "%s==%s" % tuple(dep)
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


    def refresh_sources(self):
        sudo('apt-get update')


@contextmanager
def virtualenv(path, name):
    with prefix('source %s/%s/bin/activate' % (path, name)):
        yield


class PythonManager():
    def __init__(self, req_file=None, dependencies=None, use_virtualenv=True,
                 virtualenv_path='', virtualenv_name='ENV'):
        self.dependencies = dependencies if dependencies else []
        self.req_file = req_file
        self.use_virtualenv = use_virtualenv
        self.virtualenv_name = virtualenv_name
        self.virtualenv_path = virtualenv_path

    def init(self, delete_if_exists, python_path=""):
        if self.use_virtualenv:
            virtualenv_full_path = path(self.virtualenv_path).joinpath(self.virtualenv_name)
            if cuisine.dir_exists(virtualenv_full_path) and delete_if_exists:
                dir_delete(virtualenv_full_path)

            with cuisine_sudo():
                pip_install(['virtualenv'])

            with cuisine_sudo():
                dir_ensure(self.virtualenv_path, recursive=True, mode=777)
                dir_attribs(self.virtualenv_path, mode=777, recursive=True)

            with cd(self.virtualenv_path):
                run('VIRTUALENV_EXTRA_SEARCH_DIR="%s" && virtualenv %s' % (python_path, self.virtualenv_name))


    def setup_dependencies(self):
        file_dependencies = []
        if self.req_file:
            with open(self.req_file, 'r') as file:
                dep_str = file.read()
                file_dependencies = [str.split('==') for str in dep_str.split('\n') if str != '']

        if self.use_virtualenv:
            with virtualenv(self.virtualenv_path, self.virtualenv_name):
                pip_install(self.dependencies)
                pip_install(file_dependencies)
        else:
            with cuisine_sudo():
                pip_install(self.dependencies)
                pip_install(file_dependencies)

    def get_version_pattern(self, pattern):
        ver_str = cuisine.run('python --version')
        regex = re.compile(pattern)
        match = regex.match(ver_str)
        version = match.group(1)
        return version

    def get_full_version(self):
        return self.get_version_pattern("Python\\s+([\\d\\.]+)")

    def get_short_version(self):
        return self.get_version_pattern("Python\\s+(\\d+\\.\\d+).*")


class DatabaseManager(object):
    def create_user(self):
        pass

    def create_database(self, delete_if_exists=False):
        pass

    def drop_database(self):
        pass

    def configure(self, enable_remote_access=False):
        pass

    def backup_database(self, filename, zip=False, folder=None):
        pass

    def init_database(self, init_sql_file, delete_if_exists=False, unzip=False):
        pass

    def create_backup_script(self, folder=None, project_name=None):
        pass


class SqliteManager(DatabaseManager):
    def __init__(self, dbfile):
        self.dbfile = dbfile


class PostgresManager(DatabaseManager):
    def __init__(self, database_name, user, password, superuser_login="postgres", host="localhost"):
        self.database_name = database_name
        self.user = user
        self.password = password
        self.superuser_login = superuser_login
        self.host = host
        self.db_backup_folder = "/tmp"

    def version(self):
        version_info = cuisine.run("psql --version")
        version_line = version_info.split("\n")[0].strip()
#        assert len(version_line) > 7, "There's something wrong with Postgres version info: " + version_info
        return re.search("\\d+\\.\\d+\\.\\d+", version_line).group(0)

    def short_version(self):
        return re.match("(\\d+\\.\\d+)", self.version()).group(1)

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
            host_replaced, replaced = text_replace_line_re(
                pg_hba,
                "^host[\s\w\./]+$",
                "host\tall\tall\t0.0.0.0/0\tmd5")

            local_replaced, replaced = text_replace_line_re(
                host_replaced,
                "^local\s+all\s+all.*$",
                "local\tall\tall\t\tmd5")

        return local_replaced

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
                cuisine.file_write(self.pg_hba_path(), unix_eol(self.process_pg_hba_conf()))
                cuisine.file_write(self.postgresql_conf_path(), unix_eol(self.process_postgresql_conf()))


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


    @contextmanager
    def pg_pass(self):
        run("echo *:*:%s:%s:%s > ~/.pgpass" % (self.database_name, self.user, self.password))
        run("chmod 0600 ~/.pgpass")

        yield

        run("rm ~/.pgpass")


    def backup_database(self, filename, zip=False, folder=None):
        folder = folder or self.db_backup_folder

        with cuisine.cuisine_sudo():
            cuisine.dir_ensure(folder, recursive=True, mode="777")

        file_full_path = "/".join([folder, filename])

        with self.pg_pass():
            sudo_pipeline(("pg_dump -O -x %s | gzip > %s" if zip else "pg_dump %s > %s")
            % (self.database_name, file_full_path), user=self.superuser_login)

    def init_database(self, init_sql_file, delete_if_exists=False, unzip=False):
        self.create_database(delete_if_exists)
        if unzip:
            command = "cat %s | gunzip | psql %s -w -U %s"
        else:
            command = "cat %s | psql %s -w -U %s"

        with self.pg_pass():
            run(command % (init_sql_file, self.database_name, self.user))

        sudo_pipeline("echo GRANT ALL ON SCHEMA public TO %s | psql" % self.user, user=self.superuser_login)
        sudo_pipeline("echo ALTER DATABASE %s OWNER TO %s | psql" % (self.database_name, self.user), user=self.superuser_login)

    def create_backup_script(self, folder=None, project_name=None):
        folder = folder or '/tmp'
        project_name = project_name or self.database_name

        tmpl = cuisine.text_strip_margin(
            """
            |echo *:*:${database_name}:${user}:${password} > ~/.pgpass
            |chmod 0600 ~/.pgpass
            |file_full_path="${folder}/${project_name}_db_`date +%s`.sql.gz"
            |pg_dump -O -x ${database_name} | gzip > $file_full_path
            |echo $file_full_path | env python /usr/local/bin/s3.py
            |rm ~/.pgpass
            |rm $file_full_path
            """)

        context = {
            'database_name': self.database_name,
            'user': self.user,
            'password': self.password,
            'folder': folder,
            'project_name': project_name,
        }

        return cuisine.text_template(tmpl, context)


class ApacheManagerForUbuntu():
    def __init__(self):
        self.webserver_user = "www-data"
        self.webserver_group = "www-data"

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
            print("Apache configured\n%s" % config)


class GitManager:
    def __init__(self, dir):
        self.dir = dir

    def basename(self):
        return "%s_%s" %\
               ("gitarchive_",
                timestamp_str())

    def local_archive(self, file_path, include_submodules=True):
        basename_prefix = self.basename()
        files = dict()
        dirs = [''] # we have atleast one dir


        # adding dirs from submodules
        if include_submodules:
            gitmodule_path = path(self.dir).joinpath('.gitmodules')
            if os.path.exists(gitmodule_path):
                with open(gitmodule_path, 'r') as file:
                    lines = file.read().split('\n')
                    regex = re.compile('\\s*path\\s*=\\s*(.*)\\s*')
                    dirs += [regex.match(line).group(1) for line in lines if regex.match(line)]

        i = 0
        for cur_dir in dirs:
            cur_dur_full_path = path(self.dir).joinpath(cur_dir)
            with lcd(cur_dur_full_path):
                basename = '%s_%d.zip' % (basename_prefix, i)
                local("git archive %s --format zip --output %s" % ("HEAD", path(file_path).joinpath(basename)))
                files[cur_dir] = basename
                i += 1
        return files


class HgManager:
    def __init__(self, path):
        self.dir = path

    def local_archive(self, filename, remove_first=False):
        # Somebody needs to test this one - I don't use Mercurial
        with lcd(self.dir):
            if remove_first: local("rm -f %s" % filename)
            local("hg archive -t zip %s" % filename)


class ConfigurationException(StandardError):
    pass


def create_check_config(attributes):
    """
    This decorator checks the method's self class to have all specified attributes defined and not null.
    To use the decoretor you need to create an instance first specifying the attributes:
    django_check_config = create_check_config(['webserver','src_root','static_root','server_admin'])

    class DjangoManager:

        @django_check_config
        def init_dirs():
            ...
    """

    def check_config_decorator(func):
        def arg_defined(obj, attrs):
            for an_attr in attrs:
                if hasattr(obj, an_attr) and obj.__dict__[an_attr] is not None:
                    continue
                else:
                    return False, an_attr
            return True, ''

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result, attr = arg_defined(self, attributes)

            if not result:
                raise ConfigurationException("Attribute is not defined: %s" % attr)
            return func(self, *args, **kwargs)


        return wrapper

    return check_config_decorator

django_check_config = create_check_config([
    'webserver',
    'src_root',
    'python',
    'media_url',
    'media_root',
    'static_url',
    'static_root',
    'server_admin',
    ])


class DjangoManager:
    """
        This manager uses Django Project Convention:
    """

    @contextmanager
    def virtualenv_aware(self):
        if self.use_virtualenv:
            with virtualenv(self.virtualenv_path, self.virtualenv_name):
                yield
        else:
            yield


    def __init__(self, project_name, remote_project_path, local_project_path,
                 remote_site_path, src_root=None, settings_module='settings',
                 use_virtualenv=True, virtualenv_path=None, virtualenv_name='ENV',
                 media_root=None, media_url=None, static_root=None, static_url=None,
                 server_admin=None, precompilers=None):
        logger.info("Creating DjangoManager")

        self.remote_project_path = remote_project_path
        self.project_name = project_name
        self.project_local_path = local_project_path
        self.remote_site_path = remote_site_path

        self.log_path = None

        self.scm = GitManager(self.project_local_path)

        self.env_path = "/usr/local"
        self.wsgi_handler_path = self.remote_site_path + "/wsgi_handler.py"

        self.settings_module = settings_module
        self.use_virtualenv = use_virtualenv
        self.virtualenv_path = virtualenv_path if virtualenv_path else self.remote_site_path
        self.virtualenv_name = virtualenv_name

        # settings that should be set explicitly
        self.media_root = media_root if media_root else self.remote_site_path + "/media"
        self.static_root = static_root if static_root else self.remote_site_path + "/static"
        self.src_root = src_root
        self.media_url = media_url
        self.static_url = static_url

        self.webserver = None
        self.python = None
        self.server_admin = server_admin

        if precompilers:
            self.precompilers = precompilers
            for precomp in precompilers:
                precomp.root = self.remote_project_path
        else:
            self.precompilers = list()

        logger.info(self.__dict__)


    def configure_virtualenv(self):
        # configure virtualenv - we don't need it for WSGI, however, it's required for ./manage.py and django-admin.py
        if self.use_virtualenv:
            activate_file_name = path(self.virtualenv_path).joinpath(self.virtualenv_name).joinpath('bin/activate')
            activate_text = file_read(activate_file_name)
            new_activate_text = text_ensure_line(activate_text,
                'export DJANGO_SETTINGS_MODULE="%s"' % self.settings_module)

            if new_activate_text != activate_text:
                file_write(activate_file_name, unix_eol(new_activate_text))

    @django_check_config
    def init(self):
        """
        Should be called at least one before uploading the code. Creates project dirs and copies static_upload files.
        """
        with cuisine_sudo():
            cuisine.dir_ensure(self.remote_project_path, recursive=True,
                owner=self.webserver.webserver_user, group=self.webserver.webserver_group)

            cuisine.dir_ensure(self.remote_site_path, recursive=True,
                owner=self.webserver.webserver_user, group=self.webserver.webserver_group)

            cuisine.dir_ensure(self.log_path, recursive=True,
                owner=self.webserver.webserver_user, group=self.webserver.webserver_group)

            cuisine.dir_ensure(self.media_root, recursive=True,
                owner=self.webserver.webserver_user, group=self.webserver.webserver_group)

            cuisine.dir_ensure(self.static_root, recursive=True,
                owner=self.webserver.webserver_user, group=self.webserver.webserver_group)

        self.configure_virtualenv()


    def before_upload_code(self):
        pass

    def after_upload_code(self):
        pass

    def clear_remote_project_path_save_site(self):
        home_dir = remote_home()
        site_path_basename = path(self.remote_site_path).name
        with cuisine_sudo():
            cuisine.dir_ensure(self.remote_site_path, recursive=True, mode='777')
            cuisine.dir_ensure("%s/tmp" % home_dir, mode='777')
            dir_delete("%(home_dir)s/tmp/%(site_path_basename)s" % locals())
            cuisine.run('mv %(site_dir)s %(home_dir)s/tmp' % {'site_dir': self.remote_site_path, 'home_dir': home_dir})

            clear_dir(self.remote_project_path)


            #restore site dir
            cuisine.run('mv %(home_dir)s/tmp/%(site_dir_basename)s %(proj_path)s' % {
                'site_dir_basename': site_path_basename,
                'proj_path': self.remote_project_path,
                'home_dir': home_dir
            })

    @django_check_config
    def upload_code(self, update_submodules=True):
        if self.webserver:
            self.webserver.stop()

        self.before_upload_code()

        # we need to ensure the directory is open for writing
        with cuisine_sudo():
            dir_attribs(self.remote_project_path, mode='777')

        self.clear_remote_project_path_save_site()

        temp_dir_prefix = 'django_temp_'

        # zip and upload file
        temp_dir = temp_dir_prefix + self.project_name + '_' + timestamp_str()

        temp_remote_path = path(self.remote_project_path).joinpath(temp_dir)
        temp_local_path = path(self.project_local_path).joinpath(temp_dir)
        local_dir_ensure(temp_local_path)
        dir_ensure(temp_remote_path)

        files = self.scm.local_archive(temp_local_path, include_submodules=update_submodules)

        for dir, file in files.iteritems():
            local_archive_path = temp_local_path.joinpath(file)
            remote_archive_path = temp_remote_path.joinpath(file)
            put(str(local_archive_path), str(temp_remote_path), use_sudo=True)
            local_file_delete(local_archive_path)

            #unzip file
            with cuisine_sudo():
                extdir = path(self.remote_project_path).joinpath(dir).abspath()
                dir_ensure(extdir, recursive=True, mode='777')
                file_unzip(remote_archive_path, extdir)
                file_delete(remote_archive_path)

        cuisine.run("cd %s" % self.src_root)
        cuisine.run("pwd")

        with cuisine_sudo():
            cuisine.dir_attribs(self.remote_project_path, mode="777", recursive=True)

        for precomp in self.precompilers:
            precomp.compile()

        # clear old archives
        local_dirs_delete(self.project_local_path, '%s%s.*' % (temp_dir_prefix, self.project_name))

        ## upload ends here
        self.after_upload_code()

        if self.webserver:
            self.webserver.start()

    @django_check_config
    def collect_static(self):
        self.manage("collectstatic --noinput")


    @django_check_config
    def migrate_data(self):
        self.manage("syncdb  --noinput")
        self.manage("migrate")


    @django_check_config
    def dump_database_to_json(self):
        local("django-admin.py dumpdata studentoffice auth > ./src/studentoffice/fixtures/initial_data.json")

    @django_check_config
    def manage(self, command):
        """
        Django manage.py command execution. Local safe - could be used in cuisine_local() block.
        """
        with cd(self.src_root):
            with self.virtualenv_safe():
                print ("admin command dir %s" % cuisine.run("pwd"))
                cuisine.run("django-admin.py %s --pythonpath=%s" % (command, self.src_root))


    @contextmanager
    def virtualenv_safe(self):
        if self.use_virtualenv:
            with virtualenv(self.virtualenv_path, self.virtualenv_name):
                yield
        else:
            yield

    @django_check_config
    def set_debug(self, debug):
        with cuisine_sudo():
            settings_file_path = path(self.src_root).joinpath(self.production_symlink)
            settings_content = cuisine.file_read(settings_file_path)

            # replaces "#listen_addresses = 'localhost'	" type of lines
            # with "listen_addresses = '*'"
            settings_content, replaced = text_replace_line_re(
                settings_content,
                "^DEBUG\s*=",
                "DEBUG=%s" % debug)

            return cuisine.file_write(settings_file_path, settings_content), replaced


    @django_check_config
    def create_apache_config(self):
        apache_template = cuisine.text_strip_margin(
            """
            |<VirtualHost *:80>
            |    ServerAdmin $server_admin
            |
            |    DocumentRoot $static_root
            |
            |    Alias $media_url $media_root/
            |    <Directory $media_root>
            |           Order deny,allow
            |           Allow from all
            |    </Directory>
            |
            |    Alias $static_url $static_root/
            |    <Directory $static_root>
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

        return cuisine.text_template(apache_template, self.__dict__)


    @django_check_config
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
            |     $virtualenv_path
            |
            |     '$src_root',
            |])
            |
            |os.environ['DJANGO_SETTINGS_MODULE'] = '$settings_module'
            |
            |import django.core.handlers.wsgi
            |application = django.core.handlers.wsgi.WSGIHandler()
            """)

        if self.use_virtualenv:
            virtualenv_template = cuisine.text_strip_margin("""
            |    os.path.normpath('$site_root/$virtualenv_name/lib/python$python_version/site-packages'),
            """)

            context = {
                'site_root': self.remote_site_path,
                'python_version': self.python.get_short_version(),
                'virtualenv_name': self.virtualenv_name
            }

            virtualenv_path = cuisine.text_template(virtualenv_template, context)
        else:
            virtualenv_path = ''

        if self.env_path:
            context = self.__dict__.copy()
            context['virtualenv_path'] = virtualenv_path
            return cuisine.text_template(wsgi_template, context)
        else:
            raise RuntimeError("Properties env_path and $project_local_path should be set to configure web server")


    @django_check_config
    def configure_wsgi(self):
        wsgi_handler = self.create_wsgi_handler()
        cuisine.file_write(self.wsgi_handler_path, wsgi_handler)
        print(wsgi_handler)


    @django_check_config
    def collect_static(self):
        self.manage("collectstatic --noinput")

    def create_backup_script(self, folder=None):
        folder = folder or '/tmp'

        tmpl = cuisine.text_strip_margin(
            """
            |media_full_path="${folder}/${project_name}_media_`date +%s`.tar.gz"
            |tar -cvzf $media_full_path ${media_root}
            |echo $media_full_path | env python /usr/local/bin/s3.py
            |rm $media_full_path
            """)

        context = {
            'project_name': self.project_name,
            'media_root': self.media_root,
            'folder': folder
        }

        return cuisine.text_template(tmpl, context)



















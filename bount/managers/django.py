from bount.managers import BackupManager
from bount.managers.git import GitManager
from bount.managers.python import virtualenv
from contextlib import contextmanager
from functools import wraps
import logging
from bount.stacks.generic import BackupExecutionError
from fabric.context_managers import  cd
from fabric.operations import *
from path import path
from bount import timestamp_str
from bount import cuisine
from bount.cuisine import cuisine_sudo, dir_ensure, file_read, text_ensure_line, file_write, dir_attribs
from bount.utils import local_file_delete, file_delete, file_unzip, text_replace_line_re, clear_dir, dir_delete, remote_home, unix_eol, local_dir_ensure, local_dirs_delete, whoami, tar_folder, ls_re, untar_file

__author__ = 'mturilin'

logger = logging.getLogger(__file__)


class ConfigurationException(StandardError):
    pass


def create_check_config(attributes):
    """
    This decorator checks the method's self class to have all specified attributes defined and not null.
    To use the decoretor you need to create an instance first specifying the attributes:
    django_check_config = create_check_config(['src_root','static_root','server_admin'])

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
                 static_dirs=None, server_admin=None,
                 user=None, group=None,
                 precompilers=None, use_south=False):
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

        self.static_dirs = static_dirs or []

        self.python = None
        self.server_admin = server_admin

        if precompilers:
            self.precompilers = precompilers
            for precomp in precompilers:
                precomp.root = self.remote_project_path
        else:
            self.precompilers = list()

        logger.info(self.__dict__)

        self.remote_host = env.host
        self.use_south = use_south
        self.__user = user
        self.__group = group

    def get_user(self):
        if not self.__user:
            logger.warn("Django: No user is set. Using whoami to get the current user on the remote host")
            self.__user = whoami()

        return self.__user


    def get_group(self):
        if self.__group:
            return self.__group
        else:
            return self.user

    user = property(get_user)
    group = property(get_group)



    def virtualenv_activate_path(self):
        return path(self.virtualenv_path).joinpath(self.virtualenv_name).joinpath('bin/activate')

    def configure_virtualenv(self):
        # configure virtualenv - we don't need it for WSGI, however, it's required for ./manage.py and django-admin.py
        if self.use_virtualenv:
            activate_file_name = self.virtualenv_activate_path()
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
                owner=self.user, group=self.group)

            cuisine.dir_ensure(self.remote_site_path, recursive=True,
                owner=self.user, group=self.group)

            cuisine.dir_ensure(self.log_path, recursive=True,
                owner=self.user, group=self.group)

            cuisine.dir_ensure(self.media_root, recursive=True,
                owner=self.user, group=self.group)

            cuisine.dir_ensure(self.static_root, recursive=True,
                owner=self.user, group=self.group)

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


    @django_check_config
    def collect_static(self):
        self.manage("collectstatic --noinput")


    @django_check_config
    def migrate_data(self):
        self.manage("syncdb  --noinput")
        if self.use_south:
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
                cuisine.run(
                    "django-admin.py %s --pythonpath=%s --settings=%s" % (command, self.src_root, self.settings_module))


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
            settings_file_path = path(self.src_root).joinpath(self.settings_module.replace(".", "/") + ".py")
            settings_content = cuisine.file_read(settings_file_path)

            # replaces "#listen_addresses = 'localhost'	" type of lines
            # with "listen_addresses = '*'"
            settings_content, replaced = text_replace_line_re(
                settings_content,
                "^DEBUG\s*=",
                "DEBUG=%s" % debug)

            return cuisine.file_write(settings_file_path, unix_eol(settings_content)), replaced


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
        for dir in self.static_dirs:
            dir_ensure(dir, recursive=True, mode='777')
        self.manage("collectstatic --noinput --clear")

    def create_backup_script(self, folder=None):
        folder = folder or '/tmp'

        tmpl = cuisine.text_strip_margin(
            """
            |media_full_path="${master_folder}/${project_name}_media_`date +%s`.tar.gz"
            |tar -cvzf $media_full_path ${media_root}
            |echo $media_full_path | env python /usr/local/bin/s3.py
            |rm $media_full_path
            """)

        context = {
            'project_name': self.project_name,
            'media_root': self.media_root,
            'master_folder': folder
        }

        return cuisine.text_template(tmpl, context)




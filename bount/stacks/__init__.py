from functools import partial
from fabric.state import env

__author__ = 'mturilin'

from axel import Event

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

    def restart_webserver(self):
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

    def media_restore_local_latest(self):
        raise NotImplementedError('Method is not implemented')

    def enable_debug(self):
        raise NotImplementedError('Method is not implemented')

    def disable_debug(self):
        raise NotImplementedError('Method is not implemented')

    def recreate_database(self):
        raise NotImplementedError('Method is not implemented')

    def stop_webserver(self):
        raise NotImplementedError('Method is not implemented')

#    def update_local_media(self):
#        raise NotImplementedError('Method is not implemented')


stack_builder = None
stacks = dict()

def get_stack():
    if env.host_string not in stacks:
        stacks[env.host_string] = stack_builder()

    return stacks[env.host_string]



before_install = Event()
after_install = Event()


def install(skip_packages=False):
    before_install()

    stop_webserver()

    if not skip_packages:
        get_stack().setup_os_dependencies()
        get_stack().setup_python_dependencies()
        get_stack().setup_precompilers()

    get_stack().init_database()

    get_stack().init_dirs()
    get_stack().upload()
    get_stack().migrate_data()
    get_stack().collect_static()
    configure_webserver() # restart_webserver is already there

    after_install()


before_configure_webserver = Event()
after_configure_webserver = Event()

def configure_webserver():
    before_configure_webserver()
    stop_webserver()
    get_stack().configure_webserver()
    after_configure_webserver()

before_update_code = Event()
after_update_code = Event()

def update_code():
    before_update_code()

    get_stack().upload()
    get_stack().restart_webserver()

    after_update_code()


before_update = Event()
after_update = Event()

def update():
    before_update()

    backup_database()
    get_stack().upload()
    get_stack().migrate_data()
    get_stack().collect_static()
    get_stack().restart_webserver()

    after_update()


def update_python_dependencies():
    get_stack().setup_python_dependencies()


before_restart_webserver = Event()
after_restart_webserver = Event()
def restart_webserver():
    before_restart_webserver()
    get_stack().restart_webserver()
    after_restart_webserver()

before_stop_webserver = Event()
after_stop_webserver = Event()
def stop_webserver():
    before_stop_webserver()
    get_stack().stop_webserver()
    after_stop_webserver()

before_backup_database = Event()
after_backup_database = Event()

def backup_database():
    before_backup_database()
    get_stack().backup_database()
    after_backup_database()


def db_snapshot_remote():
    get_stack().download_db_dump()


def db_restore_remote():
    get_stack().restore_latest_db_dump()


def media_snapshot_remote():
    get_stack().download_media()


def media_restore_remote():
    get_stack().restore_latest_media()


def media_snapshot_local():
    get_stack().archive_local_media()


def media_restore_local():
    get_stack().media_restore_local_latest()


def remote_restore():
    update()
    media_restore_remote()
    db_restore_remote()


def remote_snapshot():
    media_snapshot_remote()
    db_snapshot_remote()


def enable_debug():
    get_stack().enable_debug()


def disable_debug():
    get_stack().disable_debug()


def recreate_database_remote():
    get_stack().recreate_database()


def enable_ntpd():
    get_stack().enable_ntpd()


def disable_ntpd():
    get_stack().disable_ntpd()
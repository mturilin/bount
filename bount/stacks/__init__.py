__author__ = 'mturilin'

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
from bount.cuisine import dir_ensure, cuisine_sudo, dir_attribs, sudo, run
from bount.managers import UbuntuManager, PythonManager, ApacheManagerForUbuntu, DjangoManager, PostgresManager, ConfigurationException
from bount.utils import local_dir_ensure, file_delete, remote_home, dir_delete

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

    def media_restore_local_latest(self):
        raise NotImplementedError('Method is not implemented')

    def enable_debug(self):
        raise NotImplementedError('Method is not implemented')

    def disable_debug(self):
        raise NotImplementedError('Method is not implemented')

    def recreate_database(self):
        raise NotImplementedError('Method is not implemented')

#    def update_local_media(self):
#        raise NotImplementedError('Method is not implemented')


current_stack = Stack()



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


def start_restart_webserver():
    current_stack.start_restart_webserver()

before_backup_database = Event()
after_backup_database = Event()

def backup_database():
    before_backup_database()
    current_stack.backup_database()
    after_backup_database()


def db_snapshot_remote():
    current_stack.download_db_dump()


def db_restore_remote():
    current_stack.restore_latest_db_dump()


def media_snapshot_remote():
    current_stack.download_media()


def media_restore_remote():
    current_stack.restore_latest_media()


def media_snapshot_local():
    current_stack.archive_local_media()

def media_restore_local():
    current_stack.media_restore_local_latest()


def remote_restore():
    update()
    media_restore_remote()
    db_restore_remote()

def remote_snapshot():
    media_snapshot_remote()
    db_snapshot_remote()


def enable_debug():
    current_stack.enable_debug()

def disable_debug():
    current_stack.disable_debug()


def recreate_database_remote():
    current_stack.recreate_database()

def enable_ntpd():
    current_stack.enable_ntpd()

def disable_ntpd():
    current_stack.disable_ntpd()
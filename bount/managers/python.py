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
from bount.managers import generic_install
from bount.utils import local_file_delete, file_delete, python_egg_ensure, file_unzip, text_replace_line_re, sudo_pipeline, clear_dir, dir_delete, remote_home, unix_eol, local_dir_ensure, local_dirs_delete

__author__ = 'mturilin'

logger = logging.getLogger(__file__)



def pip_install(dependencies):
    generic_install(dependencies, lambda dep_str: python_egg_ensure(dep_str))



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
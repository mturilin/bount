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

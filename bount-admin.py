#!/usr/bin/python
import sys
from path import path
from shutil import copyfile
import bount

__author__ = 'mturilin'


def init(fabfile_dir):
    admin_templates_dir = path(bount.__file__).dirname().joinpath("admin_templates")
    copyfile(admin_templates_dir.joinpath("fabfile.py"), fabfile_dir)
    copyfile(admin_templates_dir.joinpath("fabfile_common.py"), fabfile_dir)


def bount_admin(argv):
    if argv[1] == "init":
        init(argv[2])



if __name__ == "__main__":
    bount_admin(sys.argv)

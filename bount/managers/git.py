import os
import logging
from fabric.context_managers import lcd
from fabric.operations import *
from path import path
from bount import timestamp_str

__author__ = 'mturilin'

logger = logging.getLogger(__file__)


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
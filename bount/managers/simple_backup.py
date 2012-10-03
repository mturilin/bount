from bount import cuisine, timestamp_str
from bount.utils import ls_re, local_ls_re, untar_file, tar_folder
import os
from bount.managers import BackupStorage, BackupManager
from bount.stacks.generic import BackupConfigurationError, BackupExecutionError
from fabric.operations import get, put
from path import path

__author__ = 'mturilin'


class ClientBackupStorage(BackupStorage):
    """
    The backup storage for the client computer that executes the bount. This class doesn't
    check any of the directories to exist or being writeable.
    """

    def __init__(self, local_folder):
        self.local_folder = local_folder

    def save_script(self):
        raise BackupConfigurationError("Upload script is not supported for ClientBackupStorage")

    def save(self, file):
        # 2. get it to local computer
        get(file, self.local_folder)

    def list(self):
        return local_ls_re(self.remote_folder, ".*tar\\.gz")

    def get(self, file, path_to):
        file_path = path(self.local_folder).joinpath(file)
        if file_path.exists():
            put(file_path, path_to)

        return file_path


class ServerBackupStorage(BackupStorage):
    """
    The simplest possible backup solution - just copies the stuff to a master_folder
    """


    def __init__(self, remote_folder):
        self.remote_folder = remote_folder


    def save_script(self):
        raise BackupConfigurationError("Upload script is not supported for ServerBackupStorage")

    def save(self, file):
        # 2. get it to local computer
        cuisine.run("cp %s %s" % (file, self.remote_folder))

    def list(self):
        return ls_re(self.remote_folder, ".*tar\\.gz")

    def get(self, file, path_to):
        file_path = path(self.remote_folder).joinpath(file)
        if file_path.exists():
            cuisine.run("cp %s %s" % (file_path, path_to))

        return file_path


class FolderBackupManager(BackupManager):
    def __init__(self, master_folder, tag):
        super(FolderBackupManager, self).__init__()
        self.master_folder = master_folder
        self.tag = tag

    def backup(self, temp_folder):
        dump_basename = "%s_%s.tar.gz" % (self.tag, timestamp_str())
        file_path = path(temp_folder).joinpath(dump_basename)

        tar_folder(self.master_folder, file_path)

        return file_path

    def create_backup_script(self):
        pass

    def get_name(self):
        return "Folder %s" % self.master_folder

    def restore(self, folder):
        pattern = "%s_\d+_\d+\\.tar\\.gz" % self.tag
        files = ls_re(folder, pattern)

        if len(files) == 0:
            raise BackupExecutionError("File not found for the pattern %s" % pattern)
        elif len(files) > 1:
            raise BackupExecutionError("Multiple files conforms the pattern %s" % pattern)

        file_path = path(folder).joinpath(files[0])

        return untar_file(file_path, self.master_folder)
import logging
from bount import timestamp_str
from bount.cuisine import dir_ensure
from bount.stacks import Stack
from bount.utils import whoami, tar_folder, file_delete, dir_delete, untar_file

__author__ = 'mturilin'

logger = logging.getLogger()

class BackupConfigurationError(StandardError): pass


class BackupExecutionError(StandardError): pass


class GenericStack(Stack):
    services = []
    backup_managers = []
    backup_storage = dict()
    default_backup_storage = None
    temp_dir = "/tmp"

    def get_user(self):
        if not self.__user:
            logger.warn("GoetheStack: No user is set. Using whoami to get the current user on the remote host")
            self.__user = whoami()

        return self.__user


    def get_group(self):
        if self.__group:
            return self.__group
        else:
            return self.user

    user = property(get_user)
    group = property(get_group)

    def __init__(self, project_name, user=None, group=None):
        self.project_name = project_name
        self.__user = user
        self.__group = group

    def get_backup_storage(self, destination):
        if destination:
            if destination in self.backup_storage:
                backup_storage = self.backup_storage[destination]
            else:
                raise BackupConfigurationError("Unknown destination %s" % destination)
        else:
            if not self.default_backup_storage:
                raise BackupConfigurationError("No destinatio specified and there's no default backaup starage")
            backup_storage = self.default_backup_storage

        return backup_storage

    def backup(self, destination=None):
        temp_folder = self.create_temp_folder()
        for backup_manager in self.backup_managers:
            print "Backing up: ", backup_manager.get_name()
            backup_manager.backup(temp_folder, self.project_name)

        temp_folder_targz = tar_folder(temp_folder)

        self.get_backup_storage(destination).save(temp_folder_targz)

        file_delete(temp_folder_targz)
        dir_delete(temp_folder)


    def list_backups(self, destination=None):
        return self.get_backup_storage(destination).list()


    def restore(self, name, destination=None):
        file_path = self.get_backup_storage(destination).get(name, self.temp_dir)
        if not file_path.endsWith("tar.gz"):
            raise BackupExecutionError("Backup file doesn't end with 'tar.gz'")

        untar_file(file_path)

        backup_dir_name = file_path[:-7]

        for backup_manager in self.backup_managers:
            print "Restoring: ", backup_manager.get_name()
            backup_manager.restore(backup_dir_name)


    def list_destinations(self):
        if self.backup_storage:
            print "Backup destinations:"
            for (dest, storage) in self.backup_storage.iteritems():
                if storage == self.default_backup_storage:
                    print "-", dest, "(default)"
                else:
                    print "-", dest
        else:
            print "There are no destinations configured"

    def create_temp_folder(self):
        folder_name = "%s/backup_%s_%s" % (self.temp_dir, self.project_name, timestamp_str())
        dir_ensure(folder_name)
        return folder_name
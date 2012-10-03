import types

__author__ = 'mturilin'


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


class DatabaseManager(object):
    def create_user(self):
        pass

    def create_database(self, delete_if_exists=False):
        pass

    def drop_database(self):
        pass

    def configure(self, enable_remote_access=False):
        pass

    def init_database(self, init_sql_file, delete_if_exists=False, unzip=False):
        pass




class Service(object):
    def setup(self):
        pass

    def start(self):
        raise NotImplementedError('Method is not implemented')

    def stop(self):
        raise NotImplementedError('Method is not implemented')

    def restart(self):
        raise NotImplementedError('Method is not implemented')

    def is_running(self):
        raise NotImplementedError('Method is not implemented')


class WebServer(Service):
    def create_website(self, name, config, delete_other_sites=False):
        raise NotImplementedError('Method is not implemented')


class BackupManager(object):

    def backup(self, temp_folder):
        """
        Backs up the data to a single file ready to store.
        @param temp_folder: local master_folder to put the backup to
        @return: backup file name
        """
        raise NotImplementedError('Method is not implemented')


    def restore(self, folder):
        """
        Restore data from a file.
        @param file_path: File with a backup
        @return: None
        """
        raise NotImplementedError('Method is not implemented')

    def create_backup_script(self):
        """

        @return: A shell script text to backup the resource. First argument is master_folder, second is the backup name.
        """
        raise NotImplementedError('Method is not implemented')

    def get_name(self):
        raise NotImplementedError('Method is not implemented')



class BackupStorage(object):

    def get(self, file_name, path_to):
        """
        Uploads master_folder to the storage
        @param file_name: file name to get
        @param path_to: where to put the file at the server
        @return: None
        """
        raise NotImplementedError('Method is not implemented')

    def list(self):
        """
        List all backups available at the storage.
        @return: list of the remote master_folder names that could be used to download them
        """
        raise NotImplementedError('Method is not implemented')


    def save(self, file):
        """
        Download master_folder from the storage to the local path.
        @param file: path to the file to save
        @return: None
        """
        raise NotImplementedError('Method is not implemented')

    def save_script(self):
        """

        @return: Shell script code that upload the first argument to the storage.
        """
        raise NotImplementedError('Method is not implemented')

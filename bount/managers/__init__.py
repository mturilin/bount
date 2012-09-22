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

    def backup_database(self, filename, zip=False, folder=None):
        pass

    def init_database(self, init_sql_file, delete_if_exists=False, unzip=False):
        pass

    def create_backup_script(self, folder=None, project_name=None):
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

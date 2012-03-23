from bount.stacks import media_restore_local, media_snapshot_local

__author__ = 'mturilin'



class LocalDbManager(object):
    def backup_database(self):
        raise NotImplementedError("The function is not implemented")

    def restore_database(self, delete_if_exists = False):
        raise NotImplementedError("The function is not implemented")

    def create_database(self, delete_if_exists=False):
        raise NotImplementedError("The function is not implemented")


current_local_db_manager = None



def db_snapshot_local():
    current_local_db_manager.backup_database()

def db_restore_local(delete_if_exists=False):
    current_local_db_manager.restore_database(delete_if_exists=delete_if_exists)


def local_snapshot():
    db_snapshot_local()
    media_snapshot_local()


def local_restore():
    db_restore_local(delete_if_exists=True)
    media_restore_local()
__author__ = 'mturilin'



class LocalDbManager(object):
    def backup_database(self):
        raise NotImplementedError("The function is not implemented")

    def restore_database(self, delete_if_exists = False):
        raise NotImplementedError("The function is not implemented")

    def create_database(self, delete_if_exists=False):
        raise NotImplementedError("The function is not implemented")


current_local_db_manager = None



def backup_local_database():
    current_local_db_manager.backup_database()

def restore_local_latest_backup():
    current_local_db_manager.backup_database()
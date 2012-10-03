from bount.managers import BackupStorage

__author__ = 'mturilin'


class AmazonS3BackupStorageManager(BackupStorage):
    def save_script(self):
        return super(AmazonS3BackupStorageManager, self).save_script()

    def download_folder(self, folder, local_root):
        return super(AmazonS3BackupStorageManager, self).download_folder(folder, local_root)

    def list_folders(self):
        return super(AmazonS3BackupStorageManager, self).list_folders()

    def get(self, folder):
        return super(AmazonS3BackupStorageManager, self).get(folder)
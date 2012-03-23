import os
import bount
from bount.cuisine import run
from bount import timestamp_str
from bount.local import LocalDbManager
from path import path

__author__ = 'mturilin'


class MacLocalPostgres9Manager(LocalDbManager):
    """
    Prerequisites:
    1. Current user should be able to sudo w/o password
    2. psql should be in $PATH (it usually is)
    3. pg_ctl should be in $PATH (ex: a new file "postgres" should be placed to /etc/paths.d/
    More info at: http://serverfault.com/questions/16355/how-to-set-global-path-on-os-x
    """

    def __init__(self, database_name, user, password, backup_path, dba_login="", dba_password="",
                 host="localhost", port=5432, bin_path="/usr/local/Cellar/postgresql/9.1.2/bin", use_zip=True,
                 backup_prefix=None, pgdata='/usr/local/var/postgres'):
        self.database_name = database_name
        self.user = user
        self.password = password
        self.host = host
        self.db_backup_folder = "/tmp"
        self.port = port
        self.bin_path = bin_path
        self.use_zip = use_zip
        self.backup_path = backup_path
        self.dba_login = dba_login
        self.dba_password = dba_password
        self.backup_prefix = backup_prefix
        self.pgdata = pgdata

    def psql_command(self, database='', query=None, as_dba=False):
        if as_dba:
            user = self.dba_login
            password = self.dba_password
        else:
            user = self.user
            password = self.password

        command = "%s/psql -h %s -p %d -U %s" % (self.bin_path, self.host, self.port, user)

        if database:
            command = '%s %s' % (command, database)

        if query:
            command = '%s -c "%s"' % (command, query)

        return command

    def psql_command_db(self, as_dba=False):
        """
        Returns psql command for the active database
        """
        return self.psql_command(self.database_name, as_dba=as_dba)


    def create_user(self):
        run("echo CREATE USER %s WITH PASSWORD \\'%s\\' | %s" %
            (self.user, self.password, self.psql_command(as_dba=True)))


    def create_database(self, delete_if_exists=False):
        if self.database_exists():
            if delete_if_exists:
                self.drop_database_connections()
                self.psql("DROP database %s" % self.database_name)
            else:
                print("Skipping database creation because it is already exists")
                return

        run("echo \"CREATE DATABASE %s WITH OWNER %s  ENCODING 'UNICODE'\" | %s" % (
            self.database_name, self.user, self.psql_command()))

        print("Database was created")


    def database_exists(self):
        query = "SELECT 1 AS result FROM pg_database WHERE datname='%s'" % self.database_name
        result = run(self.psql_command('template1', query))

        if "0" in result:
            return False
        elif "1" in result:
            return True
        else:
            print("Result: %s" % result)
            raise RuntimeError("Unknown PostgreSQL result: %s" % result)



    def latest_db_dump_basename(self):
        sql_file_list = [filename for filename in os.listdir(self.backup_path)
                         if filename.endswith(".sql.gz") and filename.startswith(self.backup_prefix)]
        if not sql_file_list:
            raise RuntimeError("No files found")

        return sorted(sql_file_list)[-1]

    def restore_database(self, delete_if_exists=False):
        self.create_database(delete_if_exists)
        if self.use_zip:
            command = "cat %s | gunzip | %s"
        else:
            command = "cat %s | %s"


        init_sql_file = path(self.backup_path).joinpath(self.latest_db_dump_basename())

        return run(command % (init_sql_file, self.psql_command_db()))

    def _create_db_backup_name(self):
        prefix = self.backup_prefix if self.backup_prefix else self.database_name
        return "%s_db_%s_local.sql.gz" % (prefix, timestamp_str())

    def backup_database(self):
        filepath = path(self.backup_path).joinpath(self._create_db_backup_name())

        dump_command = "%s/pg_dump -O -x %s -U %s -w -h %s" % (self.bin_path, self.database_name, self.user, self.host)

        if self.use_zip:
            command = "%s | gzip > %s" % (dump_command, filepath)
        else:
            command = "%s > %s" % (dump_command, filepath)

        run(command)

    @classmethod
    def build_manager(cls, database_name, user, password, backup_path,
                      dba_login="", dba_password="",
                      host="localhost", port=5432, bin_path="/usr/local/Cellar/postgresql/9.1.2/bin", use_zip=True,
                      backup_prefix=None):
        bount.local.current_local_db_manager = MacLocalPostgres9Manager(database_name, user, password, backup_path,
            dba_login, dba_password, host, port, bin_path, use_zip, backup_prefix)

    def psql(self, command):
        return run("echo \"%s\" | %s" % (command, self.psql_command()))


    def pg_ctl_path(self):
        return path(self.bin_path).joinpath('pg_ctl')

    def drop_database_connections(self):
#        self.psql("SELECT pg_terminate_backend(pg_stat_activity.procpid) FROM pg_stat_activity " \
#             "WHERE pg_stat_activity.datname = '%s';" % self.database_name)
#
        run("%s restart -D %s -w -m f" % (self.pg_ctl_path(), self.pgdata))





































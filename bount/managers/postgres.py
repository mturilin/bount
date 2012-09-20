from contextlib import contextmanager
import logging
from fabric.operations import *
from bount import cuisine
from bount.cuisine import cuisine_sudo
from bount.managers import DatabaseManager
from bount.utils import  text_replace_line_re, sudo_pipeline, unix_eol

__author__ = 'mturilin'

logger = logging.getLogger(__file__)


class PostgresManager(DatabaseManager):
    def __init__(self, database_name, user, password, superuser_login="postgres", host="localhost"):
        self.database_name = database_name
        self.user = user
        self.password = password
        self.superuser_login = superuser_login
        self.host = host
        self.db_backup_folder = "/tmp"

    def version(self):
        version_info = cuisine.run("psql --version")
        version_line = version_info.split("\n")[0].strip()
        #        assert len(version_line) > 7, "There's something wrong with Postgres version info: " + version_info
        return re.search("\\d+\\.\\d+\\.\\d+", version_line).group(0)

    def short_version(self):
        return re.match("(\\d+\\.\\d+)", self.version()).group(1)

    def create_user(self):
        sudo_pipeline("echo CREATE USER %s WITH PASSWORD \\'%s\\' | psql" % (self.user, self.password),
            user=self.superuser_login)


    def create_database(self, delete_if_exists=False):
        if delete_if_exists and self.database_exists():
            self.drop_database()

        if not self.database_exists():
            sudo_pipeline("echo CREATE DATABASE %s WITH OWNER %s  ENCODING \\'UNICODE\\' TEMPLATE template0 | psql" % (
                self.database_name, self.user),
                user=self.superuser_login)
            return "Database was created"
        return "Database already exists"


    def drop_database(self):
        sudo("service postgresql restart")
        sudo("echo DROP DATABASE %s | psql" % self.database_name, user=self.superuser_login)

    def pg_hba_path(self):
        return '/etc/postgresql/%s/main/pg_hba.conf' % self.short_version()

    def process_pg_hba_conf(self):
        with cuisine_sudo():
            pg_hba = cuisine.file_read(self.pg_hba_path())

            # replaces "host all all 127.0.0.1/32 md5" type of lines
            # with "host all all 0.0.0.0/0 md5"
            host_replaced, replaced = text_replace_line_re(
                pg_hba,
                "^host[\s\w\./]+$",
                "host\tall\tall\t0.0.0.0/0\tmd5")

            local_replaced, replaced = text_replace_line_re(
                host_replaced,
                "^local\s+all\s+all.*$",
                "local\tall\tall\t\tmd5")

        return local_replaced

    def postgresql_conf_path(self):
        return '/etc/postgresql/%s/main/postgresql.conf' % self.short_version()

    def process_postgresql_conf(self):
        with cuisine_sudo():
            pg_hba = cuisine.file_read(self.postgresql_conf_path())

            # replaces "#listen_addresses = 'localhost'	" type of lines
            # with "listen_addresses = '*'"
            new_text, replaced = text_replace_line_re(
                pg_hba,
                ".*listen_addresses\s*=",
                "listen_addresses = '*'	")

        return new_text


    def configure(self, enable_remote_access=False):
        if enable_remote_access:
            with cuisine_sudo():
                cuisine.file_write(self.pg_hba_path(), unix_eol(self.process_pg_hba_conf()))
                cuisine.file_write(self.postgresql_conf_path(), unix_eol(self.process_postgresql_conf()))


    def database_exists(self):
        result = sudo(
            "psql template1 -c \"SELECT 1 AS result FROM pg_database WHERE datname='%s'\"; "
            % self.database_name,
            user=self.superuser_login)

        if "0" in result:
            return False
        elif "1" in result:
            return True
        else:
            raise RuntimeError("Unknown PostgreSQL result: %s" % result)


    @contextmanager
    def pg_pass(self):
        run("echo *:*:%s:%s:%s > ~/.pgpass" % (self.database_name, self.user, self.password))
        run("chmod 0600 ~/.pgpass")

        yield

        run("rm ~/.pgpass")


    def backup_database(self, filename, zip=False, folder=None):
        folder = folder or self.db_backup_folder

        with cuisine.cuisine_sudo():
            cuisine.dir_ensure(folder, recursive=True, mode="777")

        file_full_path = "/".join([folder, filename])

        with self.pg_pass():
            sudo_pipeline(("pg_dump -O -x %s | gzip > %s" if zip else "pg_dump %s > %s")
                          % (self.database_name, file_full_path), user=self.superuser_login)

    def init_database(self, init_sql_file, delete_if_exists=False, unzip=False):
        self.create_database(delete_if_exists)
        if unzip:
            command = "cat %s | gunzip | psql %s -w -U %s"
        else:
            command = "cat %s | psql %s -w -U %s"

        with self.pg_pass():
            run(command % (init_sql_file, self.database_name, self.user))

        sudo_pipeline("echo GRANT ALL ON SCHEMA public TO %s | psql" % self.user, user=self.superuser_login)
        sudo_pipeline("echo ALTER DATABASE %s OWNER TO %s | psql" % (self.database_name, self.user),
            user=self.superuser_login)

    def create_backup_script(self, folder=None, project_name=None):
        folder = folder or '/tmp'
        project_name = project_name or self.database_name

        tmpl = cuisine.text_strip_margin(
            """
            |echo *:*:${database_name}:${user}:${password} > ~/.pgpass
            |chmod 0600 ~/.pgpass
            |file_full_path="${folder}/${project_name}_db_`date +%s`.sql.gz"
            |pg_dump -O -x ${database_name} | gzip > $file_full_path
            |echo $file_full_path | env python /usr/local/bin/s3.py
            |rm ~/.pgpass
            |rm $file_full_path
            """)

        context = {
            'database_name': self.database_name,
            'user': self.user,
            'password': self.password,
            'folder': folder,
            'project_name': project_name,
        }

        return cuisine.text_template(tmpl, context)


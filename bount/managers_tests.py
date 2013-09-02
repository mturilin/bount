from functools import wraps
import unittest
from fabric.operations import local
from fabric.state import env
import os
import getpass
from fabric.tasks import execute
from bount import cuisine
from bount.cuisine import run
from bount.managers import PythonManager
from managers import PostgresManager

__author__ = 'mturilin'


def fabric_method(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return execute(func, *args, **kwargs)
    return wrapper


class PythonTest(unittest.TestCase):
    python_manager = PythonManager()

    def test_full_version(self):
        cuisine.run = lambda arg: 'Python 2.6.6'
        tt = cuisine.run("python --version")
        a = self.python_manager.get_full_version()
        self.assertNotEquals(a, None)
        self.assertRegexpMatches(a, "^[\\d\\.]+$")


class PostgresTest(unittest.TestCase):
    postgres_manager = PostgresManager("aaa", "bbb", "ccc")
    VERSION_STR_9 = "psql (PostgreSQL) 9.1.3"
    VERSION_STR_8 = "PostgreSQL 8.1.1"


    def test_full_version_9 (self):
        self.full_version_test(self.VERSION_STR_9)

    def test_full_version_8 (self):
        self.full_version_test(self.VERSION_STR_8)

    def test_short_version_9 (self):
        self.short_version_test(self.VERSION_STR_9)

    def test_short_version_8 (self):
        self.short_version_test(self.VERSION_STR_8)

    def full_version_test (self, version_str):
        cuisine.run = lambda arg: version_str

        a = self.postgres_manager.version()

        self.assertNotEquals(a, None)
        self.assertRegexpMatches(a, "\\d+\\.\\d+\\.\\d+")

    def short_version_test (self, version_str):
        cuisine.run = lambda arg: version_str

        a = self.postgres_manager.short_version()

        self.assertNotEquals(a, None)
        self.assertRegexpMatches(a, "\\d+\\.\\d+")

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

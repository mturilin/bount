import logging
from fabric.operations import *
from bount import cuisine
from bount.managers import generic_install

__author__ = 'mturilin'

logger = logging.getLogger(__file__)


def aptget_install(dependencies):
    generic_install(dependencies, lambda dep_str: cuisine.package_ensure(dep_str
    ))


class UbuntuManager():
    def __init__(self):
        self.dependencies = []

    def setup_dependencies(self):
        aptget_install(self.dependencies)


    def refresh_sources(self):
        sudo('apt-get update')

    def enable_ntpd(self):
        sudo('service ntp start')

    def disable_ntpd(self):
        sudo('service ntp stop')
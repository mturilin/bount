import logging
from bount.managers import WebServer
from fabric.operations import *
from bount import cuisine
from bount.cuisine import cuisine_sudo
from bount.utils import   clear_dir

__author__ = 'mturilin'

logger = logging.getLogger(__file__)


class ApacheManagerForUbuntu(WebServer):
    def __init__(self):
        self.webserver_user = "www-data"
        self.webserver_group = "www-data"

    def is_running(self):
        return "running" in run("service apache2 status")

    def restart(self):
        sudo("service apache2 restart")

    def start(self):
        sudo("service apache2 start")

    def stop(self):
        if not self.is_running():
            sudo("service apache2 stop")


    def create_website(self, name, config, delete_other_sites=False):
        if delete_other_sites:
            with cuisine_sudo():
                clear_dir('/etc/apache2/sites-enabled')

        with cuisine_sudo():
            cuisine.file_write('/etc/apache2/sites-enabled/%s' % name, config)
            print("Apache configured\n%s" % config)
import logging
from fabric.operations import *
from bount import cuisine
from bount.cuisine import cuisine_sudo
from bount.utils import   clear_dir

__author__ = 'mturilin'

logger = logging.getLogger(__file__)


class ApacheManagerForUbuntu():
    def __init__(self):
        self.webserver_user = "www-data"
        self.webserver_group = "www-data"

    def status(self):
        result = run("service apache2 status")
        if "running" in result:
            return "running"
        else:
            return "stopped"

    def restart(self):
        sudo("service apache2 restart")

    def start(self):
        sudo("service apache2 start")

    def stop(self):
        sudo("service apache2 stop")


    def configure_webserver(self, name, config, delete_other_sites=False):
        if delete_other_sites:
            with cuisine_sudo():
                clear_dir('/etc/apache2/sites-enabled')

        with cuisine_sudo():
            cuisine.file_write('/etc/apache2/sites-enabled/%s' % name, config)
            print("Apache configured\n%s" % config)
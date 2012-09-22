from bount.managers import WebServer
import logging
from fabric.operations import *
from bount import cuisine
from bount.cuisine import cuisine_sudo
from bount.utils import  clear_dir

__author__ = 'mturilin'

logger = logging.getLogger(__file__)


class NginxManager(WebServer):
    def __init__(self):
        self.webserver_user = "www-data"
        self.webserver_group = "www-data"

    def is_running(self):
        return "running" in run("service nginx status")

    def restart(self):
        sudo("service nginx restart")

    def start(self):
        sudo("service nginx start")

    def stop(self):
        sudo("service nginx stop")


    def create_website(self, name, config, delete_other_sites=False):
        if delete_other_sites:
            with cuisine_sudo():
                clear_dir('/etc/nginx/sites-enabled')

        with cuisine_sudo():
            cuisine.file_write('/etc/nginx/sites-enabled/%s' % name, config)
            print("Nginx configured\n%s" % config)

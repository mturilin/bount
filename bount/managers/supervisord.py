from bount import cuisine
from bount.managers import Service
from fabric.api import settings as fabric_settings, hide

__author__ = 'mturilin'


def supervisord_stop():
    cuisine.sudo("killall supervisord")

def supervisord_start():
    cuisine.sudo("supervisord")

def supervisord_restart():
    supervisord_stop()
    supervisord_start()

def supervisord_is_running():
    with fabric_settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        return "supervisord" in cuisine.run("ps -A | grep supervisord")

def supervisord_update():
    cuisine.sudo("killall -s HUP supervisord")


class SupervisordService(Service):

    def __init__(self, service_name, environment=None):
        self.service_name = service_name
        self.environment = environment or {}

    def get_supervisorctl_service_name(self):
        return self.service_name

    def service(self, action):
        cuisine.sudo("supervisorctl %s %s" % (action, self.get_supervisorctl_service_name()))

    def start(self):
        if not supervisord_is_running():
            supervisord_start()

        self.service("start")

    def stop(self):
        self.service("stop")

    def restart(self):
        self.service("restart")

    def cold_restart(self):
        supervisord_restart()
        self.restart()

    def create_service(self, supervisor_config):
        cuisine.file_write("/etc/supervisor/conf.d/%s.conf" % self.service_name, supervisor_config)
        if supervisord_is_running():
            supervisord_update()

    def build_environment_str(self):
        return ','.join(["%s='%s'" % pair for pair in self.environment.iteritems()])

    environment_str = property(build_environment_str)
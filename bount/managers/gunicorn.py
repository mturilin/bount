import logging
from bount.managers.supervisord import  SupervisordService
from path import path
from bount import cuisine
from bount.cuisine import cuisine_sudo, dir_ensure, dir_attribs, file_attribs
from bount.utils import  file_delete
import pystache

__author__ = 'mturilin'

logger = logging.getLogger(__file__)


SUPERVISOR_TEMPLATE = """
[program:{{service_name}}]
directory={{src_path}}
user=ubuntu
command={{virtualenv_dir}}/bin/gunicorn wsgi:application
stdout_logfile = {{log_dir}}/supervisor_out.log
stderr_logfile = {{log_dir}}/supervisor_err.log
autostart=true
autorestart=true
redirect_stderr=True
environment={{environment_str}}
"""

class GunicornDjangoManager(SupervisordService):
    def __init__(self, service_name, user, group, num_of_workers, virtualenv_dir, project_path, src_path, log_dir,
                 site_path, environment=None):
        super(GunicornDjangoManager, self).__init__(service_name, environment)

        self.user = user
        self.group = group
        self.num_of_workers = num_of_workers
        self.virtualenv_dir = virtualenv_dir
        self.project_name = service_name
        self.project_path = project_path
        self.src_path = src_path
        self.log_dir = log_dir
        self.site_path = site_path

    def setup(self):
#        dir_ensure(self.log_dir, True, '777')
#        dir_attribs(self.log_dir, mode='777')
#
        with cuisine_sudo():
            supervisor_config = pystache.render(SUPERVISOR_TEMPLATE, self)
            self.create_service(supervisor_config)
            print supervisor_config















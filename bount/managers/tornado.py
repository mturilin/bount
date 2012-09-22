import logging
from bount.managers import Service
from bount import cuisine
from bount.cuisine import cuisine_sudo, dir_ensure, dir_attribs
from bount.managers.supervisord import SupervisordService
import pystache

__author__ = 'mturilin'

logger = logging.getLogger(__file__)


SUPERVISOR_TEMPLATE = """
[program:{{service_name}}]
directory={{src_path}}
user={{user}}
{{#group}}group={{.}}{{/group}}
stdout_logfile = {{log_dir}}/tornado_out.log
stderr_logfile = {{log_dir}}/tornado_err.log
autostart=true
autorestart=true
redirect_stderr=True

process_name = main-%(process_num)s
numprocs = {{num_of_workers}}
numprocs_start = {{start_port}}
command={{virtualenv_dir}}/bin/python {{script_path}} %(process_num)s
environment={{environment_str}}
"""


class TornadoManager(SupervisordService):
    def __init__(self,
                 script_path,
                 service_name,
                 user,
                 group,
                 num_of_workers,
                 start_port,
                 virtualenv_dir,
                 src_path,
                 log_dir,
                 site_path,
                 environment=None):
        super(TornadoManager, self).__init__(service_name, environment)
        self.user = user
        self.group = group
        self.num_of_workers = num_of_workers
        self.start_port = start_port
        self.virtualenv_dir = virtualenv_dir
        self.project_name = service_name
        self.src_path = src_path
        self.log_dir = log_dir
        self.site_path = site_path
        self.script_path = script_path

    def setup(self):
        dir_ensure(self.log_dir, True, '777')
        dir_attribs(self.log_dir, mode='777')

        with cuisine_sudo():
            supervisor_config = pystache.render(SUPERVISOR_TEMPLATE, self)
            self.create_service(supervisor_config)
            print supervisor_config



TORNADO_NGINX_TEMPLATE = """
# Enumerate all the Tornado servers here
upstream frontends {
    {{#ports}}
    server 127.0.0.1:{{.}};
    {{/ports}}
}
server {
    listen {{nginx_port}};

    # for your tornado's app
    location / {
        proxy_pass_header Server;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_pass http://frontends;
    }
}
"""


class TornadoNginxManager(TornadoManager):
    def __init__(self,
                 script_path,
                 service_name,
                 user,
                 group,
                 num_of_workers,
                 start_port,
                 virtualenv_dir,
                 src_path,
                 log_dir,
                 site_path,
                 nginx,
                 nginx_port,
                 nginx_template=TORNADO_NGINX_TEMPLATE,
                 environment=None):

        TornadoManager.__init__(self, script_path, service_name, user, group, num_of_workers, start_port,
            virtualenv_dir, src_path, log_dir, site_path, environment)

        self.nginx = nginx
        self.nginx_port = nginx_port
        self.nginx_template = nginx_template

    def setup(self):
        super(TornadoNginxManager, self).setup()
        self.ports = [port_num for port_num in range(self.start_port, self.start_port + self.num_of_workers)]
        nginx_conf = pystache.render(self.nginx_template, self.__dict__)
        self.nginx.create_website(self.service_name, nginx_conf)

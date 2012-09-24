import bount
from bount.managers.tornado import TornadoManager
from bount.precompilers import LessPrecompiler, CoffeePrecompiler
from bount.stacks.goethe import GoetheStack
from fabric.state import env
from path import path
from bount.stacks import *

__author__ = 'mturilin'

WEBSOCKET_PORT = 8888
PROJECT_ROOT = path(__file__).dirname()

def build_stack():

    precompilers = [
        LessPrecompiler('less', 'compiled/css'),
        CoffeePrecompiler('less', 'compiled/js'),
        ]

    stack = GoetheStack.build_stack(
        settings_module='settings',
        dependencies_path=PROJECT_ROOT.joinpath('requirements.txt'),
        project_name='neji',
        source_root=PROJECT_ROOT.joinpath('src'),
        precompilers=precompilers,
        environment={
            'WEBSOCKET_HOST': env.host_string,
            'WEBSOCKET_PORT': repr(WEBSOCKET_PORT)
        })


    tornado = TornadoManager("socketserver.py", "neji_tornado", "ubuntu", '', 1, WEBSOCKET_PORT, stack.python.virtualenv_path(),
        stack.django.src_root, stack.django.log_path, stack.django.remote_site_path,
        environment={
            "DJANGO_SETTINGS_MODULE": "settings",
            })

    stack.services.append(tornado)

    return stack


bount.stacks.stack_builder = build_stack

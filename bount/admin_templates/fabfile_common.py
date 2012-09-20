from bount.precompilers import LessPrecompiler, CoffeePrecompiler
from bount.stacks import *
from bount.stacks.dalk import DalkStack

__author__ = 'mturilin'

PROJECT_ROOT = path(__file__).dirname()

precompilers = [
    LessPrecompiler('less', 'compiled/css-compiled'),
    CoffeePrecompiler('less', 'compiled/css-compiled'),
    ]

stack = DalkStack.build_stack(
    settings_module='settings_production',
    dependencies_path=PROJECT_ROOT.joinpath('requirements.txt'),
    project_name='getccna',
    source_root=PROJECT_ROOT.joinpath('src'),
    precompilers=precompilers)





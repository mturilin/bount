import getpass
from fabfile_common import *
from fabric.state import env
from bount.local.mac import MacLocalPostgres9Manager
from bount.stacks import *
from bount.local import *

## Hosts ##

def production():
    env.hosts = [r"put host here"]
    env.user = ""
    env.key_filename = [os.path.expanduser('~/.ssh/id_rsa')]


def test():
    env.hosts = [r"put host here"]
    env.user = ""
    env.key_filename = [os.path.expanduser('~/.ssh/id_rsa')]


def localhost():
    env.hosts = [r"localhost"]
    env.user = getpass.getuser()
    env.key_filename = [os.path.expanduser('~/.ssh/id_rsa')]



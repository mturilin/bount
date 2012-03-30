__author__ = 'mturilin'

from fabric.state import env
import getpass
from bount.cuisine import file_read, text_ensure_line, file_write
from bount.local.mac import MacLocalPostgres9Manager
from bount.precompilers import LessPrecompiler
from bount.stacks import *
from bount.local import *

try:
    from fabfile_local import *
except:
    print "Can't import fabfile_local"

__author__ = 'mturilin'

PROJECT_ROOT = path(__file__).dirname()

precompilers = [
    LessPrecompiler('less', 'compiled/css-compiled'),
    ]


stack = DalkStack.build_stack(
    settings_path='settings_production',
    dependencies_path=PROJECT_ROOT.joinpath('REQUIREMENTS'),
    project_name='getccna',
    source_root=PROJECT_ROOT.joinpath('src'),
    precompilers=precompilers)


MacLocalPostgres9Manager.build_manager(
    database_name='getccnaru',
    user='mturilin',
    password='',
    backup_path=path(__file__).dirname().joinpath('backup/db_dump'),
    dba_login='mturilin',
    dba_password='',
    backup_prefix="getccna")




def test1():
    env.hosts = [r"test1.getccna.ru"]
    env.user = "ubuntu"
    env.key_filename = [os.path.expanduser('~/.ssh/id_rsa')]


def localhost():
    env.hosts = [r"localhost"]
    env.user = getpass.getuser()
    env.key_filename = [os.path.expanduser('~/.ssh/id_rsa')]






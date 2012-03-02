from bount import memorize
from bount import cuisine
from bount.cuisine import dir_ensure
from bount.cuisine import file_exists
from fabric.context_managers import cd
from path import path
from utils import local_ls_re, ls_re, remote_home

__author__ = 'mturilin'



class Precompiler(object):
    """
    Server side file compiler
    """
    def __init__(self, dir_from, dir_to, root=None):
        """
        dir_from, dir_to - relative from project_root paths for the directories
        """
        self.dir_from = dir_from
        self.dir_to = dir_to
        self.root = root

    def compile(self):
        dir_ensure(self.abs_dir_to())
        return self.dir_to

    def get_os_dependencies(args):
        return []

    def get_python_dependencies(self):
        return []

    def abs_dir_from(self):
        return path(self.root).joinpath(self.dir_from)

    def abs_dir_to(self):
        return path(self.root).joinpath(self.dir_to)

    def setup(self):
        pass



class LessPrecompiler(Precompiler):
    def get_os_dependencies(args):
        return [
            'npm'
        ]

    def setup(self):
        if not file_exists(self.lessc_path()):
            print("Installing Node and Less")
            cuisine.sudo("sudo apt-get install python-software-properties")
            cuisine.sudo("sudo add-apt-repository ppa:chris-lea/node.js --yes")
            cuisine.sudo("sudo apt-get update")
            cuisine.sudo("sudo apt-get install nodejs")

            cuisine.run("curl http://npmjs.org/install.sh | sudo sh")

            with cd('~'):
                cuisine.run("npm install less")
        else:
            print ("Less is already installed")

    @memorize
    def lessc_path(self):
        return "%s/node_modules/less/bin/lessc" % remote_home()
#        return 'lessc'


    def compile(self):
        super(LessPrecompiler, self).compile()
        abs_dir_from = self.abs_dir_from()
        abs_dir_to = self.abs_dir_to()
        for a_file in ls_re(abs_dir_from, '.*\\.less'):
            cuisine.sudo('%(lessc_path)s %(dir_from)s/%(basename)s.less %(dir_to)s/%(basename)s.css' % \
             {
                 'lessc_path': self.lessc_path(),
                 'dir_from': abs_dir_from,
                 'dir_to': abs_dir_to,
                 'basename': a_file.rstrip('.less')
             })


class CoffeePrecompiler(Precompiler):
    def get_os_dependencies(args):
        return [
            'coffeescript'
        ]

    def compile(self):
        super(CoffeePrecompiler, self).compile()
        cuisine.run('coffee %(dir_from)s/*.coffee %(dir_to)s/*.js' % self.__dict__)



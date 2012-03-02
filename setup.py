__author__ = 'mturilin'

from setuptools import setup, find_packages

setup(name='Bount',
    version='0.1',
    description='Bount deployment library for Django',
    author='Mikhail Turilin',
    author_email='mturilin@gmail.com',
    url='github.com/mturilin/bount',
    packages=find_packages(),
    install_requires=[
        'django>=1.3',
        'fabric',
        'path.py',
        'axel',
    ],
    package_data = {
        '':['git-archive-all.sh']
    }
)
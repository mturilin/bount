# Bount Developer's Guide

Django is a beutilful web development framework and it takes 10 minutes to start your first Django application. However, to deploy the application to a clean Linux image could take more than an hour. Moreover, code update and data backup are usually manual. Also, if you didn't work on this particular project for a few weeks, it could be hard to remember all directory names and passwords. How could we make deployment and managing project data easier?

Here enters the Bount, a simple Django deployment and lifecycle management tool based on the following technogoies:

* fabric
* virtualenv
* south

Bount defines a number of "stacks" (currently one). Each stack defines a stable combination of the platform components. Current stack, DalkStack is able to configure the following set of technologies:

* Ubuntu 11.10 (will be replaced with the next LTS)
* Apache2
* PostgreSQL 8 or 9
* Django 1.3.1 (should work fine with 1.4 as well)

Bount makes all project deployment to be as easy as writing 5-10 lines of code once, and using simple command to perform 80% of project.

Here's an example of project configuration:

	stack = DalkStack.build_stack (
		settings_path = 'settings_production',
		dependencies_path = PROJECT_ROOT.joinpath ('REQUIREMENTS'),
		project_name = 'my_awesome_app',
		source_root = PROJECT_ROOT.joinpath ('src'),
		precompilers=[LessPrecompiler ('less', 'compiled /css-compiled'),])

## Use cases
The ususal use cases include:

1. Prepare a clean Ubuntu Server 11.10 image for Django deplpoyment: install and configure Apache2, PostgerSQL and other required packages
2. Upload code to the server, creating a directories, setting permissions and compiling resource, like LESS and CoffeeScript
3. Manage project's user-generated data
	- Save a database dump (on the remote machine and on the local machine) and download it to the developer's machine
	- Save the dump media files (on the remote machine and on the local machine) and download them to the developer machine
	- Restore the database from a dump (on the remote machine and on the local machine)
	- Restore media files from the dump (on the remote machine and on the local machine)

## Commands quick reference

	# install and configure all the components and upload code
	fab host install
	
	#update your code (commit the code first!!!)
	fab host update
	
	#download db dump from the remore machine
	fab host db_snapshot_remote
	
	#download user media files  from the remore machine
	fab localhost media_snapshot_remote
	
	#save local db dump (for upload or just to keep a copy)
	fab localhost db_snapshot_local
	
	#save local media files (for upload or just to keep a copy)
	fab localhost media_snapshot_local
	
	#restore db to a remote machine
 	fab host db_restore_remote
 	
 	#restore db to a local machine
 	fab localhost db_restore_local
 	
	#restore media to a remote machine
 	fab host media_restore_remote
 	
 	#restore media to a local machine
 	fab localhost media_restore_local
 
## Setup

### From Source
Normal mode (you can't modify bount's sources):

	git clone git://github.com/mturilin/bount.git
	python setup.py install

Developer mode:

	git clone git://github.com/mturilin/bount.git
	python setup.py develop

Everything works under virtualenv.

## Configuration

Bount must have configured the file **fabfile.py** (standard fabric's file) at the root of the project.

What you need to always specify fabfile.py:

1. Configure DalkStack - a stack that implements a bunch of Django-Ubuntu 11.10 - PostgreSQL 8/9 - Apache2. In most cases this is done in fabfile_common.py which is imported into fabfil_dev. Without DalkStack operation with the remote server is impossible.
2. Configure the local stack. The local stack allows you to download and save a dump of PostgreSQL. Single stack, which is implemented at the moment is MacLocalPostgres9Manager, which supports PostgreSQL9 installed on your Mac through Homebrew.

Example configuration DalkStack:

	precompilers = [
		LessPrecompiler ('less', 'compiled /css-compiled'),
	]


	stack = DalkStack.build_stack (
					settings_path = 'settings_production',
					dependencies_path = PROJECT_ROOT.joinpath ('REQUIREMENTS'),
					project_name = 'getccna',
					source_root = PROJECT_ROOT.joinpath ('src'),
					precompilers = precompilers)

Example configuration MacLocalPostgres9Manager:

	MacLocalPostgres9Manager.build_manager(
	    database_name='getccnaru', 
	    user='mturilin', 
	    password='', 
	    backup_path=path(__file__).dirname().joinpath('backup/db_dump'),
	    dba_login='mturilin', 
	    dba_password='', 
	    backup_prefix="getccna")

## Installing PostgreSQL on Mac

Installation:

	brew update
	brew install postgresql
	initdb / usr / local / var / postgres

Fix installation for Mac OS Lion (otherwise will not work the command line):

	curl http://nextmarvel.net/blog/downloads/fixBrewLionPostgres.sh | sh

Configure PostgreSQL data directory:

	echo "export PGDATA = / usr / local / var / postgres" >>. profile

Check the status of the service:

	pg_ctl status

If the server is not running then you need to start it:

	pg_ctl start

Check that the console is working:

	psql

## Configuring fabric

Bount uses a fabric to access servers. For each of the servers needed to determine the function of the form:

	def test2 ():
		env.hosts = [r "test2.getccna.ru"]
		env.user = "username"
		env.key_filename = [os.path.expanduser ('~ / .ssh / id_rsa')]

For a local server, you usually need the following:

	def localhost ():
		env.hosts = [r "localhost"]
		env.user = getpass.getuser ()
		env.key_filename = [os.path.expanduser ('~ / .ssh / id_rsa')]

In order to access the local machine you need to enable SSH (tested on mac and Linux).

## Install the server

To set the project on a clean server should execute [* 1]:

	fab hostname install

After this (long) process, the server will be installed. 

Usually a large part of the web site consists of user-generated contect. Therefore we need to restore the database dump and media files dumps to make the site to working.

## Updating code

When the code was changed, you can re-upload it to the server using:
      
	fab hostname update

Since this command uses git archive to create an archive to upload, you need to commit the code before executing the command.

## Restore the database

Database directory is usually **backup/db_dump**.

The dump's name should follow the pattern:

	<project name>_db_YYYYMMDD_ HHMMSS<anything>. sql.gz

For example:

	getccna_db_20120322_182612648584.sql.gz

To restore the dump to the remote machine, run the following command:

	fab hostname db_restore_remote

To restore the dump to the local machine, run the following command:

	fab hostname db_restore_local

The following file will be restored:

1. The format conforms the specification (above)
2. Is the last in terms of alphabetical sorting

Restoring db dump often leads to errors. Most of the errors happen because of desynchronized version of the code and database. After loading a dump, the system automatically performs the migration of databases using the command **south migrate**, which can fail if, for example, the code is older than the database.

## Restore the media files

Predvolagaet system that dumps are in the database directory backup / media_dump.

The name of the dump media should be the following:

	<project name>_media_YYYYMMDD_ HHMMSS<anything>. tar.gz

For example:

	getccna_media_20120323_020523958142.tar.gz

To restore the media to a remote machine, run the following command:

	fab hostname media_restore_remote

To restore the media to the local machine, run the following command:

	fab hostname media_restore_local

The following file will be loaded:

1. The format conforms the specification (above)
2. Is the last in terms of alphabetical sorting

## Save and download the database
 
To save a dump from a remote machine (to the developer's machine):

 	fab hostname db_snapshot_remote
 
To save the dump from the local machine (to the developer's machine):

 	fab hostname db_snapshot_local
 
 The file will automatically appear in the backup / db_dump
 
## Save and download the media files
 
To save the dump media from a remote machine (to the developer's machine):

 	fab hostname media_snapshot_remote
 
To save a dump of the media from the local machine (to the developer's machine):

 	fab hostname media_snapshot_local
 
 The file will automatically appear in the backup / media_dump

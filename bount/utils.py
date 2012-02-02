import gzip
import os
import re
import tarfile
import zipfile
from fabric.operations import local, sudo, run
from bount import cuisine

__author__ = 'mturilin'


def text_replace_line_re(text, pattern, new):
    res = []
    replaced = 0
    for line in text.split("\n"):
        if re.match(pattern, line):
            res.append(new)
            replaced += 1
        else:
            res.append(line)
    return "\n".join(res), replaced


def file_unzip(filename, extdir="."):
    cuisine.run("unzip %s -d %s" % (filename, extdir))


def local_file_delete(file):
    local("rm %s" % file)


def file_delete(file):
    cuisine.run("rm %s" % file)


def python_egg_ensure(egg_name):
    sudo("pip install %s" % egg_name)


def sudo_pipeline(command, user=None):
    """Enables executing complex commands via sudo"""
    run_function = lambda(command): local(command) if cuisine.mode == cuisine.MODE_LOCAL else run(command)

    if user:
        run_function("echo \"%s\" | sudo -u %s sh" % (command, user))
    else:
        run_function("echo \"%s\" | sudo sh" % command)


def sym_link(file_from, file_to):
    cuisine.run("ln -s %s %s" % (file_from, file_to))


def clear_dir(dir):
    cuisine.run("rm -rf %s/*" % dir)
    cuisine.run("rm -rf %s/.??*" % dir)


def copy_directory_content(from_dir, to_dir):
    cuisine.sudo("cp -pr %s/* %s" % (from_dir, to_dir))


def local_dir_ensure( location, recursive=False, mode=None, owner=None, group=None ):
    """Ensures that there is a remote directory at the given location, optionnaly
     updating its mode/owner/group.

     If we are not updating the owner/group then this can be done as a single
     ssh call, so use that method, otherwise set owner/group after creation."""
    if mode:
        mode_arg = "-m %s" % mode
    else:
        mode_arg = ""
    local(
        "test -d '%s' || mkdir %s %s '%s' && echo OK ; true" % (location, recursive and "-p" or "", mode_arg, location))
    if owner or group:
        local_dir_attribs(location, owner=owner, group=group)


def local_dir_attribs(location, mode=None, owner=None, group=None, recursive=False):
    """Updates the mode/owner/group for the given remote directory."""
    local_file_attribs(location, mode, owner, group, recursive)


def local_file_attribs(location, mode=None, owner=None, group=None, recursive=False):
    """Updates the mode/owner/group for the remote file at the given location."""
    recursive = recursive and "-R " or ""
    if mode:  local("chmod %s %s '%s'" % (recursive, mode, location))
    if owner: local("chown %s %s '%s'" % (recursive, owner, location))
    if group: local("chgrp %s %s '%s'" % (recursive, group, location))



def unzip_zip_file_obj(ziptar_file_object, to_dir, overwrite):
    """
    unzip_zip_file_obj(ziptar_file_object, to_dir, , overwrite)

    Unzip files from zip file object created by zipfile.ZipFile() or tarfile.TarFileCompat().
    This function is defined as separate to be used with zip and tar file objects that share the same interface.

    """
    
    for file_name in ziptar_file_object.namelist(): # for all files in archive
        base_name = os.path.basename(file_name)
        file_dir = os.path.dirname(file_name)

        # making sure the directory exists
        full_dir = os.path.join(to_dir, file_dir)
        if not os.path.exists(full_dir): os.makedirs(full_dir)

        # checking whether file exists, if yes making decision overwrite or skip
        full_file_name = os.path.join(to_dir, file_name)
        if os.path.isfile(full_file_name):
            if overwrite:
                print("File exists, deleting %s..." % full_file_name)
                os.remove(full_file_name)
            else:
                print("File exists, skipping %s" % full_file_name)
                continue

        # writing file
        print("Extracting file '%s'" % file_name)
        with open(full_file_name, 'wb') as outfile:
            outfile.write(ziptar_file_object.read(file_name))


def local_untar(tar_file_name, to_dir, overwrite=False):
    tar_file_object = tarfile.TarFileCompat(tar_file_name)

    print("Extracting tar file %s..." % tar_file_name)
    unzip_zip_file_obj(tar_file_object, overwrite=overwrite, to_dir=to_dir)
        

def local_unzip(zip_file, to_dir, overwrite=False):
    """
    local_unzip(zip_file, to_dir[, overwrite=False])

    Unzip a zip file to a local directory.
    """
    print("Unzipping zip archive '%s'" % zip_file)

    zip_file_object = zipfile.ZipFile(zip_file)
    unzip_zip_file_obj(zip_file_object, to_dir, overwrite)


def local_gunzip(gz_file, to_dir, overwrite=False, autountar=True):
    """
    local_gunzip(zip_file, to_dir[, overwrite=False][, autountar=True])

    Unzip a gz file to a local directory. This function can handle .gz and tar.gz files.
    If autountar=True, function untars the uncompressed tar into the same directory and deletes the tar file.
    """

    base_name = os.path.basename(gz_file)
    if base_name.endswith('.gz'): base_name = base_name[0:-3]

    full_file_name = os.path.join(to_dir, base_name)

    print("Unzipping gz archive '%s'" % gz_file)
    if os.path.isfile(full_file_name):
        if overwrite:
            print("File exists, deleting %s..." % full_file_name)
            os.remove(full_file_name)
        else:
            return

    print("Writing file '%s'" % base_name)
    gz_file_object = gzip.open(gz_file,'r')
    try:
        with open(full_file_name, 'wb') as outfile:
            outfile.write(gz_file_object.read())
            outfile.close()
    finally:
        gz_file_object.close()

    if autountar and tarfile.is_tarfile(full_file_name):
        local_untar(full_file_name, to_dir, overwrite=overwrite)

        print("Deleting extracted tar file %s..." % full_file_name)
        os.remove(full_file_name)

























from os.path import join as j
from os import chdir, getcwd, listdir, mkdir, rename, symlink, walk, \
               readlink, remove

import re
import urllib
import shutil
import hashlib
import optparse

# decorator for commands to obtain and release lock
def lock(f):
    def new_f(home, *args, **opts):
        _get_lock(home)
        result = f(home, *args, **opts)
        _release_lock(home)
        return result
    return new_f

@lock
def init(home):
    contents = filter(lambda x: x != 'lock.txt', listdir(home))
    info = open(j(home, 'dflat-info.txt'), 'w')
    info.write(_anvl('This', 'Dflat/0.10'))
    info.write(_anvl('Manifest-scheme', 'Checkm/0.1'))
    info.write(_anvl('Delta-scheme', 'ReDD/0.1'))
    info.close()
    mkdir(j(home, 'log'))
    version = _new_version(home)
    # move original inhabitants into their new apartment
    for f in contents:
        rename(j(home, f), j(home, version, 'full', 'data', f))
    update_manifest(j(home, version))

@lock
def checkout(home):
    curr_version = current_version(home)
    new_version = _next_version(home)
    shutil.copytree(j(home, curr_version), j(home, new_version))
    return new_version

@lock
def commit(home, msg=None):
    # TODO: calculate differences, and layer them into vn-1
    latest_version = _latest_version(home)
    remove(j(home, 'current'))
    symlink(j(home, _latest_version(home)), j(home, 'current'))
    return latest_version

@lock
def status(home):
    new = _find_add(home)
    modified = _find_modify(home)
    deleted = _find_delete(home)
    return {'add': new, 'modify': modified, 'delete': deleted}

@lock
def update_manifest(version_dir): 
    full_dir = j(version_dir, 'full')
    manifest_file = j(full_dir, 'manifest.txt')
    manifest = open(manifest_file, 'w')
    for dirpath, dirnames, filenames in walk(full_dir):
        for filename in filenames:
            if not dirpath and filename in ('manifest.txt', 'lock.txt'):
                continue
            # make the filename relative to the 'full' directory
            dirpath = re.sub(r'^%s/?' % full_dir, '', dirpath)
            md5 = _md5(j(full_dir, dirpath, filename))
            filename = urllib.quote(j(dirpath, filename))
            manifest.write("%s md5 %s\n" % (filename, md5))
    manifest.close()
    return manifest_file

def current_version(home):
    return readlink(j(home, 'current'))

def _anvl(name, value):
    return "%s: %s\n"

def _get_lock(home):
    # TODO: get lock in home
    pass

def _release_lock(home):
    # TODO: release lock in home
    pass

def _new_version(home):
    v = _next_version(home)
    mkdir(j(home, v))
    mkdir(j(home, v, 'full'))
    mkdir(j(home, v, 'full', 'admin'))
    mkdir(j(home, v, 'full', 'annotation'))
    mkdir(j(home, v, 'full', 'data'))
    mkdir(j(home, v, 'full', 'enrichment'))
    open(j(home, v, 'full', 'manifest.txt'), 'w')
    open(j(home, v, 'full', 'relationships.ttl'), 'w')
    open(j(home, v, 'full', 'splash.txt'), 'w')

    # chdir to make symlink relative, so the dflat can be relocated
    pwd = getcwd()
    chdir(home)
    symlink(v, 'current')
    chdir(pwd)

    return v

def _next_version(home):
    v = _latest_version(home)
    if v == None:
        return 'v001'
    else:
        return 'v%03i' % (_version_number(v) + 1)

def _latest_version(home):
    versions = _versions(home)
    if len(versions) == 0:
        return None
    else:
        return versions.pop()

def _versions(home):
    versions = filter(lambda x: re.match('^v\d+$', x), listdir(home))
    versions.sort(lambda a, b: cmp(_version_number(a), _version_number(b)))
    return versions

def _find_add(home):
    return ['data/d']

def _find_modify(home):
    return []

def _find_delete(home):
    return []

def _version_number(version_dir):
    return int(version_dir[1:])

def _md5(filename):
    f = open(filename, 'rb')
    m = hashlib.md5()
    while True:
        bytes = f.read(0x1000)
        if not bytes:
            break
        m.update(bytes)
    f.close()
    return m.hexdigest()

def main():
    o = optparse.OptionParser()
    values, args = o.parse_args()
    
    cmd = args[0]
    home = getcwd()
    if cmd == 'init':
        init(home)
    elif cmd == 'checkout':
        checkout(home)
    elif cmd == 'commit':
        commit(home)

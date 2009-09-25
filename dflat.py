#!/usr/bin/env python

from os import chdir, getcwd, listdir, mkdir, rename, symlink, walk
from os.path import join as j
from re import match

def init(home):
    _get_lock(home)
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
        rename(j(home, f), j(home, version, 'data', f))
    _update_manifest(j(home, version))
    _release_lock(home)

def checkout(home):
    pass

def _update_manifest(version_dir): 
    manifest_file = j(version_dir, 'manifest.txt')
    manifest = open(manifest_file, 'w')
    for dirpath, dirnames, filenames in walk(version_dir):
        for filename in filenames:
            if filename == 'manifest.txt':
                continue
            # make the filename relative to the version directory
            rel_dirpath = dirpath.replace(version_dir + '/', '')
            manifest.write("%s\n" % j(rel_dirpath, filename))
    manifest.close()
    return manifest_file

def _anvl(name, value):
    return "%s: %s\n"

def _get_lock(home):
    pass

def _release_lock(home):
    pass

def _new_version(home):
    v = _next_version(home)
    mkdir(j(home, v))
    mkdir(j(home, v, 'admin'))
    mkdir(j(home, v, 'annotation'))
    mkdir(j(home, v, 'data'))
    mkdir(j(home, v, 'enrichment'))
    open(j(home, v, 'manifest.txt'), 'w')
    open(j(home, v, 'relationships.ttl'), 'w')
    open(j(home, v, 'splash.txt'), 'w')

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
    versions = filter(lambda x: match('^v\d+$', x), listdir(home))
    versions.sort(lambda a, b: cmp(_version_number(a), _version_number(b)))
    return versions

def _version_number(version_dir):
    return int(version_dir[1:])

def main(cmd):
    if cmd == 'init':
        init()
    elif cmd == 'checkout':
        checkout()
    elif cmd == 'commit':
        commit()

if __name__ == '__main__':
    main(sys.argv[1])

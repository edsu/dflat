dflat_version = '0.16'
dnatural_version = '0.12'
redd_version = '0.1'

import os
import re
import time
import urllib
import shutil
import hashlib
import logging
import namaste
import os.path
import datetime
import optparse

# short alias for this since we call it a lot
j = os.path.join

_quiet = False

def main():
    o = _option_parser()
    values, args = o.parse_args()
    
    cmd = args[0]
    home = _dflat_home(os.getcwd())
    try:
        version = args[1]
    except IndexError:
        # optional arg not passed
        pass

    if cmd == 'init':
        init(os.getcwd())
    elif not home:
        _print("not a dflat")
    elif cmd == 'checkout':
        checkout(home)
    elif cmd == 'commit':
        commit(home)
    elif cmd == 'status':
        status(home)
    elif cmd == 'export':
        export(home, version)
    else: 
        _print("unknown command: %s" % cmd)

# decorator for commands to obtain and release lock
def lock(f):
    def new_f(home, *args, **opts):
        _get_lock(home, f)
        result = f(home, *args, **opts)
        _release_lock(home)
        return result
    return new_f

# decorator to log to the dflat home log
def log(f):
    def new_f(home, *args, **opts):
        log_file = j(home, 'log', 'dflat.log')
        _configure_logger(log_file)
        result = f(home, *args, **opts)
        return result
    return new_f

@lock
def init(home):
    contents = filter(lambda x: x != 'lock.txt', os.listdir(home))
    info = open(j(home, 'dflat-info.txt'), 'w')
    namaste.dirtype(home, 'dflat_%s' % dflat_version, verbose=False)
    info.write(_anvl('Object-scheme', 'Dflat/%s' % dflat_version))
    info.write(_anvl('Manifest-scheme', 'Checkm/0.1'))
    info.write(_anvl('Full-scheme', 'Dnatural/0.12'))
    info.write(_anvl('Delta-scheme', 'ReDD/0.1'))
    info.write(_anvl('Current-scheme', 'file'))
    info.write(_anvl('Class-scheme', 'CLOP/0.3'))
    info.close()
    os.mkdir(j(home, 'log'))
    version = _new_version(home)
    _set_current(home, version)
    # move original inhabitants into their new apartment
    for f in contents:
        os.rename(j(home, f), j(home, version, 'full', 'data', f))
    _update_manifest(j(home, version))

    # can't use decorator since the log directory doesn't exist when 
    # init is called
    log_file = j(home, 'log', 'dflat.log')
    _configure_logger(log_file)
    logging.info("initialized dflat: %s" % home)

@log
@lock
def checkout(home):
    v1 = _current_version(home)
    v2 = _next_version(home)
    if os.path.isdir(j(home, v2)):
        _print("%s already checked out" % v2)
        return v2
    _copy_tree(j(home, v1), j(home, v2))
    logging.info('checked out new version %s' % v2)
    _print("checked out %s" % v2)
    return v2 

@log
@lock
def commit(home, msg=None):
    v1 = _current_version(home)
    v2 = _latest_version(home)
    if v1 == v2:
        _print("nothing to commit")
        return
    _update_manifest(j(home, v2))
    delta = _delta(home, v1, v2)
    if not _has_changes(delta):
        _print("no changes")
        return 

    redd_home = j(home, v1, 'delta')
    os.mkdir(redd_home)
    namaste.dirtype(redd_home, 'redd_%s' % redd_version, verbose=False)

    changed = False
    if len(delta['deleted']) > 0:
        changed = True
        os.mkdir(j(redd_home, 'add'))
        for filename in delta['deleted']:
            os.renames(j(home, v1, 'full', filename), j(redd_home, 'add', filename))
    if len(delta['added']) > 0:
        changed = True
        delete = open(j(redd_home, 'delete.txt'), 'w')
        for filename in delta['added']:
            delete.write("%s\n" % filename)
        delete.close()

    if len(delta['modified']) > 0:
        changed = True
        if not os.path.isdir(j(redd_home, 'add')):
            os.mkdir(j(redd_home, 'add'))
        delete = open(j(redd_home, 'delete.txt'), 'a')
        for filename in delta['modified']:
            delete.write("%s\n" % filename)
            os.renames(j(home, v1, 'full', filename), j(redd_home, 'add', filename))
        delete.close()


    shutil.rmtree(j(home, v1, 'full'))
    _set_current(home, v2)

    if changed:
        _update_manifest(j(home, v1), is_delta=True)

    logging.info('committed %s %s' % (v2, delta))
    _print("committed %s" % v2)


    return delta

# TODO: add lock decorator?
@log
def export(home, version):
    # validate specified version
    versions = _versions(home)
    if version not in versions:
        raise Exception("version %s not found in %s" % (version, ", ".join(versions)))
    # copy the latest version
    current_version = _current_version(home)
    export = 'export-%s' % version
    _copy_tree(j(home, current_version), j(home, export))
    # walk back from latest version-1 to specified version, applying changes
    delta_versions = _versions(home,
                               reverse=True,
                               from_version=current_version,
                               to_version=version)[1:] 
    # apply adds, deletes, and replaces
    for dv in delta_versions:
        # delete deleted files
        if os.path.isfile(j(home, dv, 'delta', 'delete.txt')):
            deletes = open(j(home, dv, 'delta', 'delete.txt')).read().split()
            for delete in deletes:
                os.remove(j(home, export, 'full', delete))

        # add added files
        if os.path.isdir(j(home, dv, 'delta', 'add')): 
            for f in os.listdir(j(home, dv, 'delta', 'add')):
                _copy_tree(j(home, dv, 'delta', 'add', f), j(home, export, 'full', f)) 
    logging.info('exported version %s' % version)

def status(home):
    _print("dflat home: %s" % home)
    v1 = _current_version(home)
    _print("current version: %s" % v1)
    v2 = _latest_version(home)
    if v1 == v2:
        _print("no changes")
        delta = None
    else:
        _update_manifest(j(home, v2))
        delta = _delta(home, v1, v2)
        _print_delta_files(delta, 'added')
        _print_delta_files(delta, 'modified')
        _print_delta_files(delta, 'deleted')
    return delta

def _update_manifest(version_dir, is_delta=False): 
    if is_delta:
        container_dir = j(version_dir, 'delta')
        manifest_file = j(version_dir, 'd-manifest.txt')
    else:
        container_dir = j(version_dir, 'full')
        manifest_file = j(version_dir, 'manifest.txt')
    
    manifest = open(manifest_file, 'w')
    for dirpath, dirnames, filenames in os.walk(container_dir):
        for filename in filenames:
            if dirpath != 'full' and filename in ('manifest.txt', 'lock.txt'):
                continue
            # make the filename relative to the container directory
            dirpath = re.sub(r'^%s/?' % container_dir, '', dirpath)
            md5 = _md5(j(container_dir, dirpath, filename))
            filename = urllib.quote(j(dirpath, filename))
            manifest.write("%s md5 %s\n" % (filename, md5))
    manifest.close()
    return manifest_file

def _current_version(home):
    current_file = j(home, 'current.txt')
    if os.path.isfile(current_file):
        return open(current_file, 'r').read()
    return None

def _anvl(name, value):
    return "%s: %s\n" % (name, value)

def _get_lock(home, caller):
    # TODO: log this operation?
    lockfile = j(home, 'lock.txt')
    if os.path.isfile(lockfile):
        raise Exception("already locked")
    d = _rfc3339(datetime.datetime.now())
    agent = "dflat-%s" % caller.func_name
    lockfile = open(lockfile, 'w')
    lockfile.write("Lock: %s %s\n" % (d, agent))
    lockfile.close()

def _release_lock(home):
    # TODO: log this operation?
    lockfile = j(home, 'lock.txt')
    if not os.path.isfile(lockfile):
        return
    os.remove(lockfile)

def _new_version(home):
    v = _next_version(home)
    os.mkdir(j(home, v))
    os.mkdir(j(home, v, 'full'))
    namaste.dirtype(j(home, v, 'full'), 'dnatural_%s' % dnatural_version,
                    verbose=False)
    os.mkdir(j(home, v, 'full', 'admin'))
    os.mkdir(j(home, v, 'full', 'annotation'))
    os.mkdir(j(home, v, 'full', 'data'))
    os.mkdir(j(home, v, 'full', 'enrichment'))
    os.mkdir(j(home, v, 'full', 'log'))
    os.mkdir(j(home, v, 'full', 'metadata'))
    open(j(home, v, 'manifest.txt'), 'w')
    open(j(home, v, 'full', 'relationships.ttl'), 'w')
    open(j(home, v, 'full', 'splash.txt'), 'w')
    return v

def _next_version(home):
    v = _current_version(home)
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

def _versions(home, reverse=False, from_version=None, to_version=None):
    versions = filter(lambda x: re.match('^v\d+$', x), os.listdir(home))
    if from_version:
        versions = [x for x in versions if _version_number(x) <= _version_number(from_version)]
    if to_version:
        versions = [x for x in versions if _version_number(x) >= _version_number(to_version)]
    versions.sort(lambda a, b: cmp(_version_number(a), _version_number(b)))
    if reverse:
        versions.sort(lambda a, b: cmp(_version_number(b), _version_number(a)))
    return versions

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

def _delta(home, v1, v2):
    delta = {'modified': [], 'deleted': [], 'added': []}
    manifest_v1 = _manifest_dict(home, v1)
    manifest_v2 = _manifest_dict(home, v2)
    for filename in manifest_v2.keys():
        if manifest_v1.has_key(filename):
            if manifest_v2[filename] != manifest_v1[filename]:
                delta['modified'].append(filename)
        else:
            delta['added'].append(filename)
    for filename in manifest_v1.keys():
        if not manifest_v2.has_key(filename):
            delta['deleted'].append(filename)
    return delta

def _print_delta_files(delta, dtype):
    files = delta[dtype]
    files.sort()
    if len(files) > 0:
        _print("%s:" % dtype)
        for filename in files:
            _print("  %s" % urllib.unquote(filename))

def _has_changes(delta):
    for v in delta.values():
        if len(v) > 0:
            return True
    return False

def _manifest_dict(home, v):
    d = {}
    for line in open(j(home, v, 'manifest.txt')):
        if line.startswith('#'):
            continue
        cols = line.split()
        d[urllib.unquote(cols[0])] = cols[2]
    return d

def _dflat_home(directory):
    if 'dflat-info.txt' in os.listdir(directory):
        return os.path.abspath(directory)
    elif directory == '/':
        return None
    else:
        return _dflat_home(os.path.abspath(os.path.dirname(directory)))

def _option_parser():
    parser = optparse.OptionParser()
    return parser

def _set_current(home, v):
    # chdir to make symlink relative, so the dflat can be relocated
    # maybe there's a more elegant way to do this?
    open(j(home, 'current.txt'), 'w').write(v)

def _configure_logger(filename):
    tz = _timezone()
    logging.basicConfig(filename=filename, 
                        level=logging.INFO, 
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%dT%H:%M:%S'+tz)

def _timezone():
    if time.daylight:
        utcoffset = -time.altzone
    else:
        utcoffset = -time.timezone
    hours = int(float(utcoffset)) // 3600
    minutes = abs(utcoffset) % 3600 // 60
    return '%+03d:%02d' % (hours, minutes)

def _rfc3339(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + _timezone()

def _print(s):
    if not _quiet:
        print s

def _copy_tree(src_dir, dest_dir):
    # shutil.copytree doesn't like copying directories that already exist 
    # so here's a new one
    if not os.path.exists(dest_dir):
        os.mkdir(dest_dir)
    for file in os.listdir(src_dir):
        src = j(src_dir, file)
        dest = j(dest_dir, file)
        if os.path.isdir(src):
            if not os.path.exists(dest):
                os.mkdir(dest)
                shutil.copystat(src, dest) # preserve permissions manually
            _copy_tree(src, dest)
        else:
            shutil.copy2(src, dest) # copy2 preserves permissions


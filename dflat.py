"""
An implementation of the Dflat and ReDD specifications from CDL for
versioning of digital objects.
"""
DFLAT_VERSION = '0.16'
DNATURAL_VERSION = '0.17'
REDD_VERSION = '0.1'

import os
import re
import time
import shutil
import hashlib
import logging
import namaste
import os.path
import datetime
import optparse
from functools import wraps
try:
    from urllib.parse import quote, unquote
except ImportError:
    from urllib import quote, unquote

# short alias for this since we call it a lot
j = os.path.join

_QUIET = False

def main():
    """Parse options and dispatch to the appropriate method."""
    parser = _option_parser()
    _, args = parser.parse_args()
    try:
        cmd = args[0]
    except IndexError:
        parser.error('no command specified')
    home = _dflat_home(os.getcwd())
    try:
        version = args[1]
    except IndexError:
        # optional arg not passed
        pass

    if cmd == 'init':
        init(os.getcwd())
    elif cmd == 'help':
        _print(parser.get_usage())
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

def lock(func):
    """Decorator for commands to obtain and release lock."""
    @wraps(func)
    def new_f(home, *args, **opts):
        _get_lock(home, func)
        result = func(home, *args, **opts)
        _release_lock(home)
        return result
    return new_f

def log(func):
    """Decorator to log to the Dflat home log."""
    @wraps(func)
    def new_f(home, *args, **opts):
        log_file = j(home, 'log', 'dflat.log')
        _configure_logger(log_file)
        result = func(home, *args, **opts)
        return result
    return new_f

@lock
def init(home):
    """Convert a directory into a Dflat directory."""
    contents = [x for x in os.listdir(home) if x != 'lock.txt']
    info = open(j(home, 'dflat-info.txt'), 'w')
    namaste.dirtype(home, 'dflat_%s' % DFLAT_VERSION, verbose=False)
    info.write(_anvl('Object-scheme', 'Dflat/%s' % DFLAT_VERSION))
    info.write(_anvl('Manifest-scheme', 'Checkm/0.1'))
    info.write(_anvl('Full-scheme', 'Dnatural/%s' % DNATURAL_VERSION))
    info.write(_anvl('Delta-scheme', 'ReDD/%s' % REDD_VERSION))
    info.write(_anvl('Current-scheme', 'file'))
    info.write(_anvl('Class-scheme', 'CLOP/0.3'))
    info.close()
    os.mkdir(j(home, 'log'))
    version = _new_version(home)
    _set_current(home, version)
    # move original inhabitants into their new apartment
    for filename in contents:
        os.rename(j(home, filename),
                  j(home, version, 'full', 'producer', filename))
    _update_manifest(j(home, version))

    # can't use decorator since the log directory doesn't exist when
    # init is called
    log_file = j(home, 'log', 'dflat.log')
    _configure_logger(log_file)
    logging.info("initialized dflat: %s", home)

@log
@lock
def checkout(home):
    """Check out a new version of the Dflat."""
    current_version = _current_version(home)
    new_version = _next_version(home)
    if os.path.isdir(j(home, new_version)):
        _print("%s already checked out" % new_version)
        return new_version
    _copy_tree(j(home, current_version), j(home, new_version))
    logging.info('checked out new version %s', new_version)
    _print("checked out %s" % new_version)
    return new_version

@log
@lock
def commit(home): #, msg=None):
    """Commit a modified version to the Dflat."""
    current_version = _current_version(home)
    modified_version = _latest_version(home)
    if current_version == modified_version:
        _print("nothing to commit")
        return
    _update_manifest(j(home, modified_version))
    delta = _delta(home, current_version, modified_version)
    if not _has_changes(delta):
        _print("no changes")
        return

    redd_home = j(home, current_version, 'delta')
    os.mkdir(redd_home)
    namaste.dirtype(redd_home, 'redd_%s' % REDD_VERSION, verbose=False)

    changed = False
    if len(delta['deleted']) > 0:
        changed = True
        os.mkdir(j(redd_home, 'add'))
        for filename in delta['deleted']:
            os.renames(j(home, current_version, 'full', filename),
                       j(redd_home, 'add', filename))
    if len(delta['added']) > 0:
        changed = True
        delete = open(j(redd_home, 'delete.txt'), 'w')
        for filename in delta['added']:
            delete.write("%s\n" % quote(filename))
        delete.close()

    if len(delta['modified']) > 0:
        changed = True
        if not os.path.isdir(j(redd_home, 'add')):
            os.mkdir(j(redd_home, 'add'))
        delete = open(j(redd_home, 'delete.txt'), 'a')
        for filename in delta['modified']:
            delete.write("%s\n" % quote(filename))
            os.renames(j(home, current_version, 'full', filename),
                       j(redd_home, 'add', filename))
        delete.close()

    shutil.rmtree(j(home, current_version, 'full'))
    _set_current(home, modified_version)

    if changed:
        _update_manifest(j(home, current_version), is_delta=True)

    logging.info('committed %s %s', modified_version, delta)
    _print("committed %s" % modified_version)

    return delta

# TODO: add lock decorator?
@log
def export(home, version):
    """Export the specified version of the Dflat."""
    # validate specified version
    versions = _versions(home)
    if version not in versions:
        raise Exception("version %s not found in %s" %
                        (version, ", ".join(versions)))
    # copy the latest version
    current_version = _current_version(home)
    export_version = 'export-%s' % version
    _copy_tree(j(home, current_version), j(home, export_version))
    # walk back from latest version-1 to specified version, applying changes
    delta_versions = _versions(home,
                               reverse=True,
                               from_version=current_version,
                               to_version=version)[1:]
    # apply adds, deletes, and replaces
    for delta in delta_versions:
        # delete deleted files
        if os.path.isfile(j(home, delta, 'delta', 'delete.txt')):
            with open(j(home, delta, 'delta', 'delete.txt')) as f:
                deletes = f.read().split()
                for delete in deletes:
                    os.remove(j(home, export_version, 'full',
                                unquote(delete)))

        # add added files
        if os.path.isdir(j(home, delta, 'delta', 'add')):
            for filename in os.listdir(j(home, delta, 'delta', 'add')):
                _copy_tree(j(home, delta, 'delta', 'add', filename),
                           j(home, export_version, 'full', filename))
    logging.info('exported version %s', version)

def status(home):
    """Print current status of the Dflat."""
    _print("dflat home: %s" % home)
    current_version = _current_version(home)
    _print("current version: %s" % current_version)
    latest_version = _latest_version(home)
    _print("working version: %s" % latest_version)
    if current_version == latest_version:
        _print("no changes")
        delta = None
    else:
        _update_manifest(j(home, latest_version))
        delta = _delta(home, current_version, latest_version)
        _print_delta_files(delta, 'added')
        _print_delta_files(delta, 'modified')
        _print_delta_files(delta, 'deleted')
    return delta

def _update_manifest(version_dir, is_delta=False):
    """Update the manifest for a specific version of the Dflat."""
    if is_delta:
        container_dir = j(version_dir, 'delta')
        manifest_file = j(version_dir, 'd-manifest.txt')
    else:
        container_dir = j(version_dir, 'full')
        manifest_file = j(version_dir, 'manifest.txt')

    manifest = open(manifest_file, 'w')
    for dirpath, _, filenames in os.walk(container_dir):
        for filename in filenames:
            if dirpath != 'full' and filename in ('manifest.txt', 'lock.txt'):
                continue
            # make the filename relative to the container directory
            dirpath = re.sub(r'^%s/?' % container_dir, '', dirpath)
            md5 = _md5(j(container_dir, dirpath, filename))
            filename = quote(j(dirpath, filename))
            manifest.write("%s md5 %s\n" % (filename, md5))
    manifest.close()
    return manifest_file

def _current_version(home):
    """Return the current version of the Dflat."""
    current_file = j(home, 'current.txt')
    if os.path.isfile(current_file):
        with open(current_file, 'r') as f:
            return f.read()
    return None

def _anvl(name, value):
    """Encode a name-value pair as an ANVL string."""
    return "%s: %s\n" % (name, value)

def _get_lock(home, caller):
    """Obtain a LockIt lock."""
    # TODO: log this operation?
    lockfile = j(home, 'lock.txt')
    if os.path.isfile(lockfile):
        raise Exception("already locked")
    timestamp = _rfc3339(datetime.datetime.now())
    agent = "dflat-%s" % caller.__name__
    lockfile = open(lockfile, 'w')
    lockfile.write("Lock: %s %s\n" % (timestamp, agent))
    lockfile.close()

def _release_lock(home):
    """Release a LockIt lock."""
    # TODO: log this operation?
    lockfile = j(home, 'lock.txt')
    if not os.path.isfile(lockfile):
        return
    os.remove(lockfile)

def _new_version(home):
    """Create base directories for a new full version of the Dflat."""
    version = _next_version(home)
    os.mkdir(j(home, version))
    os.mkdir(j(home, version, 'full'))
    namaste.dirtype(j(home, version, 'full'), 'dnatural_%s' % DNATURAL_VERSION,
                    verbose=False)
    os.mkdir(j(home, version, 'full', 'producer'))
    open(j(home, version, 'manifest.txt'), 'w').close()
    return version

def _next_version(home):
    """Return the name of the version following the current version."""
    version = _current_version(home)
    if version == None:
        return 'v001'
    else:
        return 'v%03i' % (_version_number(version) + 1)

def _latest_version(home):
    """Return the name of the latest version in the Dflat."""
    versions = _versions(home)
    if len(versions) == 0:
        return None
    else:
        return versions.pop()

def _versions(home, reverse=False, from_version=None, to_version=None):
    """Return an array of all versions in the Dflat."""
    versions = [x for x in os.listdir(home) if re.match(r'^v\d+$', x)]
    if from_version:
        versions = [x for x in versions
                    if _version_number(x) <= _version_number(from_version)]
    if to_version:
        versions = [x for x in versions
                    if _version_number(x) >= _version_number(to_version)]
    #versions.sort(lambda a, b: cmp(_version_number(a), _version_number(b)))
    versions.sort(key=_version_number)
    if reverse:
        #versions.sort(lambda a, b: cmp(_version_number(b), _version_number(a)))
        versions.sort(key=_version_number, reverse=True)
    return versions

def _version_number(version_dir):
    """Convert a version directory name to an integer."""
    return int(version_dir[1:])

def _md5(filename):
    """Helper method to checksum files for a Dflat manifest."""
    with open(filename, 'rb') as f:
        md5 = hashlib.md5()
        while True:
            byte_string = f.read(0x1000)
            if not byte_string:
                break
            md5.update(byte_string)
        f.close()
        return md5.hexdigest()

def _delta(home, old_version, new_version):
    """
    Determine which files must be added to or removed from an old version to
    obtain a new version.
    """
    delta = {'modified': [], 'deleted': [], 'added': []}
    manifest_old_version = _manifest_dict(home, old_version)
    manifest_new_version = _manifest_dict(home, new_version)
    for filename in list(manifest_new_version.keys()):
        if filename in manifest_old_version:
            if manifest_new_version[filename] != manifest_old_version[filename]:
                delta['modified'].append(filename)
        else:
            delta['added'].append(filename)
    for filename in list(manifest_old_version.keys()):
        if filename not in manifest_new_version:
            delta['deleted'].append(filename)
    return delta

def _print_delta_files(delta, dtype):
    """Print the files which appear in a delta between Dflat versions."""
    files = delta[dtype]
    files.sort()
    if len(files) > 0:
        _print("%s:" % dtype)
        for filename in files:
            _print("  %s" % unquote(filename))

def _has_changes(delta):
    """Does the delta contain any changes?"""
    for value in list(delta.values()):
        if len(value) > 0:
            return True
    return False

def _manifest_dict(home, version):
    """Parse a Checkm manifest into a dictionary."""
    manifest_dict = {}
    with open(j(home, version, 'manifest.txt')) as f:
        for line in f:
            if line.startswith('#'):
                continue
            cols = line.split()
            manifest_dict[unquote(cols[0])] = cols[2]
        return manifest_dict

def _dflat_home(directory):
    """
    Return the absolute path of the Dflat containing the given directory,
    if any.
    """
    if 'dflat-info.txt' in os.listdir(directory):
        return os.path.abspath(directory)
    elif directory == '/':
        return None
    else:
        return _dflat_home(os.path.abspath(os.path.dirname(directory)))

def _option_parser():
    """Construct the option parser."""
    parser = optparse.OptionParser(usage='''usage: %prog <command> [args]
    
commands:
    init      initialize current working directory as a dflat
    checkout  check out a new version of the dflat for modification
    commit    commit new version as the current version of the object
    status    report uncommitted changes to the dflat in the current directory
    export    export the current version of the dflat into a new directory''')

    return parser

def _set_current(home, version):
    """Update the Dflat with the current version label."""
    with open(j(home, 'current.txt'), 'w') as f:
        f.write(version)

def _configure_logger(filename):
    """Configure the logger."""
    timezone = _timezone()
    logging.basicConfig(filename=filename,
                        level=logging.INFO,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%dT%H:%M:%S'+timezone)

def _timezone():
    """Return the timezone."""
    if time.daylight:
        utcoffset = -time.altzone
    else:
        utcoffset = -time.timezone
    hours = int(float(utcoffset)) // 3600
    minutes = abs(utcoffset) % 3600 // 60
    return '%+03d:%02d' % (hours, minutes)

def _rfc3339(dt):
    """Convert a datetime into an RFC 3339-formatted timestamp."""
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + _timezone()

def _print(msg):
    """Print messages when in verbose mode."""
    if not _QUIET:
        print(msg)

def _copy_tree(src_dir, dest_dir):
    """
    Replacement for shutil.copytree that will copy directories that already
    exist.
    """
    # shutil.copytree doesn't like copying directories that already exist
    # so here's a new one
    if not os.path.exists(dest_dir):
        os.mkdir(dest_dir)
    for filename in os.listdir(src_dir):
        src = j(src_dir, filename)
        dest = j(dest_dir, filename)
        if os.path.isdir(src):
            if not os.path.exists(dest):
                os.mkdir(dest)
                shutil.copystat(src, dest) # preserve permissions manually
            _copy_tree(src, dest)
        else:
            shutil.copy2(src, dest) # copy2 preserves permissions

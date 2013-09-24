import re
import unittest
from os import mkdir, remove
from os.path import isdir, isfile, islink, basename, realpath
from shutil import rmtree, copytree

import dflat

dflat._quiet = True

class DflatTests(unittest.TestCase):

    def setUp(self):
        if isdir('dflat-test'):
            rmtree('dflat-test')
        copytree('docs', 'dflat-test')

    def tearDown(self):
        if isdir('dflat-test'):
            rmtree('dflat-test')

    def assertFileEqual(self, f1, f2):
        if open(f1).read() == open(f2).read():
            pass
        else:
            self.fail("%s not the same as %s" % (f1, f2))

    def test_init(self):
        dflat.init('dflat-test')
        self.assertTrue(isdir('dflat-test'))
        self.assertTrue(isfile('dflat-test/dflat-info.txt'))
        self.assertTrue(isfile('dflat-test/current.txt'))
        self.assertEqual(open('dflat-test/current.txt').read(), 'v001')
        self.assertTrue(isdir('dflat-test/log'))
        self.assertTrue(isdir('dflat-test/v001/full/producer'))
        self.assertTrue(isfile('dflat-test/v001/manifest.txt'))
        self.assertTrue(isfile('dflat-test/v001/full/producer/canspec.pdf'))
        self.assertTrue(isfile('dflat-test/v001/full/producer/checkmspec.html'))
        self.assertTrue(isfile('dflat-test/v001/full/producer/clopspec.pdf'))
        self.assertTrue(isfile('dflat-test/v001/full/producer/dflatspec.pdf'))
        self.assertTrue(isfile('dflat-test/v001/full/producer/namastespec.html'))
        self.assertTrue(isfile('dflat-test/v001/full/producer/reddspec.html'))

        # check manifest, ordering can be different with different pythons
        manifest = {}
        for line in open('dflat-test/v001/manifest.txt'):
            cols = line.split()
            manifest[cols[0]] = cols[2]
        manifest_files = manifest.keys()
        self.assertEqual(len(manifest_files), 7)
        self.assertTrue('producer/canspec.pdf' in manifest_files)
        self.assertTrue('producer/checkmspec.html' in manifest_files)
        self.assertTrue('producer/clopspec.pdf' in manifest_files)
        self.assertTrue('producer/dflatspec.pdf' in manifest_files)
        self.assertTrue('producer/namastespec.html' in manifest_files)
        self.assertTrue('producer/reddspec.html' in manifest_files)
        self.assertEqual(manifest['producer/canspec.pdf'], '1b1b4a9761cd8bc057f807004e7b2f78')
        self.assertEqual(manifest['producer/checkmspec.html'], '138694ea9958ec66d7cc6e56194f8423')
        self.assertEqual(manifest['producer/clopspec.pdf'], '83b15ce21a9efc504dc421280f6073d8')
        self.assertEqual(manifest['producer/dflatspec.pdf'], 'f79ee8a6b3c79f25308023858d8ce085')
        self.assertEqual(manifest['producer/namastespec.html'], '7cdea11aa319f3a227a108d871285e84')
        self.assertEqual(manifest['producer/reddspec.html'], 'd3fcc19c54d424d53bcd5621fca34183')

    def test_checkout(self):
        dflat.init('dflat-test')
        dflat.checkout('dflat-test')
        self.assertTrue(isdir('dflat-test'))
        self.assertTrue(isfile('dflat-test/dflat-info.txt'))
        self.assertTrue(isfile('dflat-test/current.txt'))
        self.assertTrue(isdir('dflat-test/log'))
        self.assertTrue(isdir('dflat-test/v002/full/producer'))
        self.assertTrue(isfile('dflat-test/v002/manifest.txt'))
        self.assertTrue(isfile('dflat-test/v002/full/producer/canspec.pdf'))
        self.assertTrue(isfile('dflat-test/v002/full/producer/checkmspec.html'))
        self.assertTrue(isfile('dflat-test/v002/full/producer/clopspec.pdf'))
        self.assertTrue(isfile('dflat-test/v002/full/producer/dflatspec.pdf'))
        self.assertTrue(isfile('dflat-test/v002/full/producer/namastespec.html'))
        self.assertTrue(isfile('dflat-test/v002/full/producer/reddspec.html'))

    def test_commit(self):
        dflat.init('dflat-test')
        dflat.checkout('dflat-test')
        self.assertEqual(dflat._current_version('dflat-test'), 'v001')
        open('dflat-test/v002/full/producer/reddspec.html', 'a').write('mod')
        open('dflat-test/v002/full/producer/new file.txt', 'w').write('new file')
        remove('dflat-test/v002/full/producer/dflatspec.pdf')
        delta = dflat.commit('dflat-test')
        self.assertTrue('producer/reddspec.html' in delta['modified'])
        self.assertTrue('producer/new file.txt' in delta['added'])
        self.assertTrue('producer/dflatspec.pdf' in delta['deleted'])
        self.assertTrue(isdir('dflat-test/v001/delta'))
        self.assertTrue(isfile('dflat-test/v001/manifest.txt'))
        self.assertTrue(isfile('dflat-test/v001/d-manifest.txt'))
        self.assertEqual(dflat._current_version('dflat-test'), 'v002')

    def test_status(self):
        dflat.init('dflat-test')
        dflat.checkout('dflat-test')
        open('dflat-test/v002/full/producer/d', 'w').write('foo')
        status = dflat.status('dflat-test')
        self.assertTrue('producer/d' in status['added'])

    def test_locking(self):
        # create named function objects to test user-agent func
        def init(): pass
        def checkout(): pass
        def commit(): pass
        # open the lockfile and spit out, e.g.:
        #   ["Lock:", "2009-08-10T09:09:09.000000", "dflat-init"]
        def contents(f):
            return open(f).read().strip().split()
        lockfile = 'dflat-test/lock.txt'
        # lockfile should not already exist
        self.assertFalse(isfile(lockfile))
        dflat._get_lock('dflat-test', init)
        self.assertTrue(isfile(lockfile))
        (name, date, agent) = contents(lockfile)
        self.assertTrue(name, 'Lock:')
        # TODO: adjust this to check w3c-format time
        self.assertTrue(re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+', date))
        # test that agent string for init is a-okay
        self.assertTrue(agent, 'dflat-init')
        # make sure lockfile blocks calls to dflat functions
        self.assertRaises(Exception, dflat.checkout, 'dflat-test')
        dflat._release_lock('dflat-test')
        # lockfile should have gone bye-bye
        self.assertFalse(isfile(lockfile))
        # test that agent string for checkout is a-okay
        dflat._get_lock('dflat-test', checkout)
        self.assertTrue(isfile(lockfile))
        (name, date, agent) = contents(lockfile)
        self.assertTrue(agent, 'dflat-checkout')
        self.assertRaises(Exception, dflat.commit, 'dflat-test')
        dflat._release_lock('dflat-test')
        self.assertFalse(isfile(lockfile))        
        # test that agent string for commit is a-okay
        dflat._get_lock('dflat-test', commit)
        self.assertTrue(isfile(lockfile))
        (name, date, agent) = contents(lockfile)
        self.assertTrue(agent, 'dflat-commit')
        self.assertRaises(Exception, dflat.init, 'dflat-test')
        dflat._release_lock('dflat-test')
        self.assertFalse(isfile(lockfile))

    def test_export(self):
        home = 'dflat-test'
        dflat.init(home)
        # create v002
        dflat.checkout(home)
        open('dflat-test/v002/full/producer/reddspec.html', 'a').write('mod')
        # commit v002
        dflat.commit(home)
        # create v003
        dflat.checkout(home)
        open('dflat-test/v003/full/producer/new file.txt', 'w').write('new file')
        # commit v003
        dflat.commit(home)
        # create v004
        dflat.checkout(home)
        remove('dflat-test/v004/full/producer/dflatspec.pdf')
        # commit v004
        dflat.commit(home)
        # create v005
        dflat.checkout(home)
        # commit v005
        dflat.commit(home)
        # export an invalid version
        self.assertRaises(Exception, dflat.export, home, 'v000') 
        # export v004 and check it
        dflat.export(home, "v004")
        self.assertTrue(isdir('dflat-test/export-v004'))
        self.assertFalse(isfile('dflat-test/export-v004/full/producer/dflatspec.pdf'))
        self.assertEqual(open('dflat-test/export-v004/full/producer/reddspec.html').read(), 
                         open('dflat-test/v005/full/producer/reddspec.html').read())
        # export v003 and check it
        dflat.export(home, "v003")
        self.assertTrue(isdir('dflat-test/export-v003'))
        self.assertTrue(isfile('dflat-test/export-v003/full/producer/new file.txt'))
        self.assertTrue(isfile('dflat-test/export-v003/full/producer/dflatspec.pdf'))
        self.assertEqual(open('dflat-test/export-v003/full/producer/reddspec.html').read(), 
                         open('dflat-test/v005/full/producer/reddspec.html').read())
        # export v002 and check it
        dflat.export(home, "v002")
        self.assertTrue(isdir('dflat-test/export-v002'))
        self.assertFalse(isfile('dflat-test/export-v002/full/producer/new file.txt'))
        self.assertTrue(isfile('dflat-test/export-v002/full/producer/dflatspec.pdf'))
        self.assertFileEqual('dflat-test/export-v002/full/producer/reddspec.html',
                             'dflat-test/v005/full/producer/reddspec.html')
        # export v001 and check it
        dflat.export(home, "v001")
        self.assertTrue(isdir('dflat-test/export-v001'))
        self.assertFalse(isfile('dflat-test/export-v001/full/producer/new file.txt'))
        self.assertTrue(isfile('dflat-test/export-v001/full/producer/dflatspec.pdf'))
        self.assertNotEqual(open('dflat-test/export-v001/full/producer/reddspec.html').read(), 
                         open('dflat-test/v005/full/producer/reddspec.html').read())
        

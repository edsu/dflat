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

    def test_init(self):
        dflat.init('dflat-test')
        self.assertTrue(isdir('dflat-test'))
        self.assertTrue(isfile('dflat-test/dflat-info.txt'))
        self.assertTrue(islink('dflat-test/current'))
        self.assertEqual(basename(realpath('dflat-test/current')), 'v001')
        self.assertTrue(isdir('dflat-test/log'))
        self.assertTrue(isdir('dflat-test/v001/full/admin'))
        self.assertTrue(isdir('dflat-test/v001/full/annotation'))
        self.assertTrue(isdir('dflat-test/v001/full/data'))
        self.assertTrue(isdir('dflat-test/v001/full/enrichment'))
        self.assertTrue(isfile('dflat-test/v001/full/manifest.txt'))
        self.assertTrue(isfile('dflat-test/v001/full/relationships.ttl'))
        self.assertTrue(isfile('dflat-test/v001/full/splash.txt'))
        self.assertTrue(isfile('dflat-test/v001/full/data/canspec.pdf'))
        self.assertTrue(isfile('dflat-test/v001/full/data/checkmspec.html'))
        self.assertTrue(isfile('dflat-test/v001/full/data/clopspec.pdf'))
        self.assertTrue(isfile('dflat-test/v001/full/data/dflatspec.pdf'))
        self.assertTrue(isfile('dflat-test/v001/full/data/namastespec.html'))
        self.assertTrue(isfile('dflat-test/v001/full/data/reddspec.html'))

        # check manifest, ordering can be different with different pythons
        manifest = {}
        for line in open('dflat-test/v001/full/manifest.txt'):
            cols = line.split()
            manifest[cols[0]] = cols[2]
        manifest_files = manifest.keys()
        self.assertEqual(len(manifest_files), 8)
        self.assertTrue('splash.txt' in manifest_files)
        self.assertTrue('relationships.ttl' in manifest_files)
        self.assertTrue('data/canspec.pdf' in manifest_files)
        self.assertTrue('data/checkmspec.html' in manifest_files)
        self.assertTrue('data/clopspec.pdf' in manifest_files)
        self.assertTrue('data/dflatspec.pdf' in manifest_files)
        self.assertTrue('data/namastespec.html' in manifest_files)
        self.assertTrue('data/reddspec.html' in manifest_files)
        self.assertEqual(manifest['splash.txt'], 'd41d8cd98f00b204e9800998ecf8427e')
        self.assertEqual(manifest['relationships.ttl'], 'd41d8cd98f00b204e9800998ecf8427e')
        self.assertEqual(manifest['data/canspec.pdf'], '1b1b4a9761cd8bc057f807004e7b2f78')
        self.assertEqual(manifest['data/checkmspec.html'], '138694ea9958ec66d7cc6e56194f8423')
        self.assertEqual(manifest['data/clopspec.pdf'], '83b15ce21a9efc504dc421280f6073d8')
        self.assertEqual(manifest['data/dflatspec.pdf'], '82d0542f2dce12da9ab105fb75805da4')
        self.assertEqual(manifest['data/namastespec.html'], '7cdea11aa319f3a227a108d871285e84')
        self.assertEqual(manifest['data/reddspec.html'], 'd3fcc19c54d424d53bcd5621fca34183')

    def test_checkout(self):
        dflat.init('dflat-test')
        dflat.checkout('dflat-test')
        self.assertTrue(isdir('dflat-test'))
        self.assertTrue(isfile('dflat-test/dflat-info.txt'))
        self.assertTrue(islink('dflat-test/current'))
        self.assertEqual(basename(realpath('dflat-test/current')), 'v001')
        self.assertTrue(isdir('dflat-test/log'))
        self.assertTrue(isdir('dflat-test/v002/full/admin'))
        self.assertTrue(isdir('dflat-test/v002/full/annotation'))
        self.assertTrue(isdir('dflat-test/v002/full/data'))
        self.assertTrue(isdir('dflat-test/v002/full/enrichment'))
        self.assertTrue(isfile('dflat-test/v002/full/manifest.txt'))
        self.assertTrue(isfile('dflat-test/v002/full/relationships.ttl'))
        self.assertTrue(isfile('dflat-test/v002/full/splash.txt'))
        self.assertTrue(isfile('dflat-test/v002/full/data/canspec.pdf'))
        self.assertTrue(isfile('dflat-test/v002/full/data/checkmspec.html'))
        self.assertTrue(isfile('dflat-test/v002/full/data/clopspec.pdf'))
        self.assertTrue(isfile('dflat-test/v002/full/data/dflatspec.pdf'))
        self.assertTrue(isfile('dflat-test/v002/full/data/namastespec.html'))
        self.assertTrue(isfile('dflat-test/v002/full/data/reddspec.html'))

    def test_commit(self):
        dflat.init('dflat-test')
        dflat.checkout('dflat-test')
        self.assertEqual(dflat._current_version('dflat-test'), 'v001')
        open('dflat-test/v002/full/data/reddspec.html', 'a').write('mod')
        open('dflat-test/v002/full/data/newfile.txt', 'w').write('newfile')
        remove('dflat-test/v002/full/data/dflatspec.pdf')
        delta = dflat.commit('dflat-test')
        # TODO: look in v001/redd for expected things
        self.assertEqual(dflat._current_version('dflat-test'), 'v002')

    def test_status(self):
        dflat.init('dflat-test')
        dflat.checkout('dflat-test')
        open('dflat-test/v002/full/data/d', 'w').write('foo')
        status = dflat.status('dflat-test')
        self.assertTrue('data/d' in status['added'])

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
        open('dflat-test/v002/full/data/reddspec.html', 'a').write('mod')
        # commit v002
        dflat.commit(home)
        # create v003
        dflat.checkout(home)
        open('dflat-test/v003/full/data/newfile.txt', 'w').write('newfile')
        # commit v003
        dflat.commit(home)
        # create v004
        dflat.checkout(home)
        remove('dflat-test/v004/full/data/dflatspec.pdf')
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
        self.assertFalse(isfile('dflat-test/export-v004/full/data/dflatspec.pdf'))
        self.assertEqual(open('dflat-test/export-v004/full/data/reddspec.html').read(), 
                         open('dflat-test/v005/full/data/reddspec.html').read())
        # export v003 and check it
        dflat.export(home, "v003")
        self.assertTrue(isdir('dflat-test/export-v003'))
        self.assertTrue(isfile('dflat-test/export-v003/full/data/newfile.txt'))
        self.assertTrue(isfile('dflat-test/export-v003/full/data/dflatspec.pdf'))
        self.assertEqual(open('dflat-test/export-v003/full/data/reddspec.html').read(), 
                         open('dflat-test/v005/full/data/reddspec.html').read())
        # export v002 and check it
        dflat.export(home, "v002")
        self.assertTrue(isdir('dflat-test/export-v002'))
        self.assertFalse(isfile('dflat-test/export-v002/full/data/newfile.txt'))
        self.assertTrue(isfile('dflat-test/export-v002/full/data/dflatspec.pdf'))
        self.assertEqual(open('dflat-test/export-v002/full/data/reddspec.html').read(), 
                         open('dflat-test/v005/full/data/reddspec.html').read())
        # export v001 and check it
        dflat.export(home, "v001")
        self.assertTrue(isdir('dflat-test/export-v001'))
        self.assertFalse(isfile('dflat-test/export-v001/full/data/newfile.txt'))
        self.assertTrue(isfile('dflat-test/export-v001/full/data/dflatspec.pdf'))
        self.assertNotEqual(open('dflat-test/export-v001/full/data/reddspec.html').read(), 
                         open('dflat-test/v005/full/data/reddspec.html').read())
        

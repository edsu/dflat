import unittest
from os import mkdir, remove
from os.path import isdir, isfile, islink, basename, realpath
from shutil import rmtree, copytree

import dflat

class DflatTests(unittest.TestCase):

    def setUp(self):
        if isdir('dflat-test'):
            rmtree('dflat-test')
        copytree('docs', 'dflat-test')

    def tearDown(self):
        if isdir('dflat-test'):
            pass #rmtree('dflat-test')

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

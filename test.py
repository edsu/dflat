import unittest
import shutil
from os import mkdir
from os.path import isdir, isfile, islink, basename, realpath

import dflat

class DflatTests(unittest.TestCase):

    def setUp(self):
        if isdir('dflat-test'):
            shutil.rmtree('dflat-test')
        # create a dflat home, and set it up with some initial contents 
        mkdir('dflat-test')
        open('dflat-test/a', 'w')
        open('dflat-test/b', 'w')
        mkdir('dflat-test/c')
        open('dflat-test/c/1', 'w')
        open('dflat-test/c/2', 'w')

    def atearDown(self):
        if isdir('dflat-test'):
            shutil.rmtree('dflat-test')

    def test_init(self):
        dflat.init('dflat-test')
        self.assertTrue(isdir('dflat-test'))
        self.assertTrue(isfile('dflat-test/dflat-info.txt'))
        self.assertTrue(islink('dflat-test/current'))
        self.assertEqual(basename(realpath('dflat-test/current')), 'v001')
        self.assertTrue(isdir('dflat-test/log'))
        self.assertTrue(isdir('dflat-test/v001/admin'))
        self.assertTrue(isdir('dflat-test/v001/annotation'))
        self.assertTrue(isdir('dflat-test/v001/data'))
        self.assertTrue(isdir('dflat-test/v001/enrichment'))
        self.assertTrue(isfile('dflat-test/v001/manifest.txt'))
        self.assertTrue(isfile('dflat-test/v001/relationships.ttl'))
        self.assertTrue(isfile('dflat-test/v001/splash.txt'))
        self.assertTrue(isfile('dflat-test/v001/data/a'))
        self.assertTrue(isfile('dflat-test/v001/data/b'))
        self.assertTrue(isdir('dflat-test/v001/data/c'))
        self.assertTrue(isfile('dflat-test/v001/data/c/1'))
        self.assertTrue(isfile('dflat-test/v001/data/c/2'))

        # check manifest, ordering can be different with different pythons
        manifest = open('dflat-test/v001/manifest.txt').read().split()
        self.assertEqual(len(manifest), 6)
        self.assertTrue('dflat-test/v001/splash.txt' in manifest)
        self.assertTrue('dflat-test/v001/relationships.ttl' in manifest)
        self.assertTrue('data/b' in manifest)
        self.assertTrue('data/a' in manifest)
        self.assertTrue('data/c/2' in manifest)
        self.assertTrue('data/c/1' in manifest)

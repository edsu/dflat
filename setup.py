# bootstrap easy_install
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup

setup(
    name = 'dflat',
    version = '0.4',
    description = "a command line tool for working with dflat digital preservation file systems",
    author = "Ed Summers",
    author_email = "ehs@pobox.com",
    url = "http://github.com/edsu/dflat",
    py_modules = ['dflat', 'ez_setup'],
    test_suite = 'test',
    scripts = ['bin/dflat'],
    install_requires = ['namaste'],
)

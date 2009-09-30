# bootstrap easy_install
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(
    name = 'dflat',
    version = '0.1',
    description = "a command line tool for working with dflat digital preservation file systems",
    author = "Ed Summers",
    author_email = "ehs@pobox.com",
    url = "http://github.com/edsu/dflat",
    download_url = "",
    packages = find_packages(),
    test_suite = 'test',
    scripts = ['bin/dflat']
)

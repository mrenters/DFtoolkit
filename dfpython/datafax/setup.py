from distutils.core import setup
from datafax import __version__

setup(	name='datafax',
    version=__version__,
    description='DataFax Library for Python',
    url='http://www.phri.ca',
    author='Martin Renters',
    author_email='martin@teckelworks.com',
    license='GPLv3',
    packages=['datafax']
)

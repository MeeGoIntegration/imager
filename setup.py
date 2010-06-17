import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name = "meego_img",
    version = "0.1",
    url = 'https://dvcs.projects.maemo.org/git/?p=OBS/img',
    license = 'GPL',
    description = "Image Me Give : Meego Image creation service",
    long_description = read('README'),
    author = 'Aleksi Suomalainen + Co',
    packages = find_packages('src'),
    package_dir = {'': 'src'},
    install_requires = ['setuptools', 'django<1.2', 'amqplib','pyyaml'],
)

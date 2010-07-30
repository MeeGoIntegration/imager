# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name = "img-worker",
    version = "0.1",
    url = 'https://dvcs.projects.maemo.org/git/?p=OBS/img',
    license = 'GPL',
    description = "Image Me Give : Meego Image creation service",
    long_description = read('README'),
    author = 'Ramez Hanna + Co',    
    package_dir = {'worker': 'src/meego_img'},
    packages = ['worker'],    
    #py_modules = ['src.meego_img.worker'],
)

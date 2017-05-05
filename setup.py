# -*- coding: utf-8 -*-
import os, sys
from distutils.core import setup

from setuptools import find_packages

static_files=[('/etc/imager', ['src/img_web/img.conf']),
                ('/usr/share/img_web/processes', 
                   ['src/img_web/processes/CREATE_IMAGE',
                   ]
                )
             ]

setup(
    name = "img",
    version = "0.6.0",
    url = 'http://meego.gitorious.org/meego-infrastructure-tools/imger',
    license = 'GPLv2',
    description = "Meego Image creation service",
    author = 'Aleksi Suomalainen <aleksi.suomalainen@nomovok.com>',
    packages = ['img',
                'img_web',
                'img_web.app',
                'img_web.app.templatetags',
                'img_web.utils'
                ],    
    package_dir = {'img':'src/img',
                   'img_web':'src/img_web',
                   'img_web.app':'src/img_web/app', 
                   'img_web.app.templatetags':'src/img_web/app/templatetags',
                   'img_web.utils':'src/img_web/utils',
                  },
    package_data = { 'img_web' : ['templates/*.html',
                                  'templates/app/*.html', 
                                  'templates/registration/*.html',
                                  ],
                      'img_web.app' : ['static/*.*',
                                       'static/images/*.*',
                                       'static/images/formset/*.*',
                                       'static/js/*.*',
                                       'fixtures/*.*'
                                      ]
                    },
    data_files = static_files,
)

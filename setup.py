# -*- coding: utf-8 -*-
import os, sys
from distutils.core import setup


static_files_dirs=[{'prefix':'src/', 'dir':'src/img_web/site_media'}]
static_files=[]
for static_files_dir in static_files_dirs:
  for root, dirs, files in os.walk(static_files_dir['dir']):
    if not len(files): continue
    for i in xrange(len(files)): files[i] = os.path.join(root, files[i])
    static_files.append((os.path.join('share', root.replace(static_files_dir['prefix'],'')), files))

static_files.append((os.path.join('/etc','imager'), ['img.conf']))

print static_files
setup(
    name = "img",
    version = "0.3",
    url = 'http://meego.gitorious.org/meego-infrastructure-tools/imger',
    license = 'GPLv2',
    description = "Meego Image creation service",
    author = 'Aleksi Suomalainen <aleksi.suomalainen@nomovok.com>',
    scripts = ['src/img_boss/boss_build_ks.py', 'src/img_boss/boss_build_image.py', 'src/img_boss/boss_img_client.py', 'src/img_amqp/img_client.py', 'src/img_amqp/build_image.py'],
    packages = ['img', 'img_web', 'img_web.app'],    
    package_dir = {'img':'src/img', 'img_web':'src/img_web', 'img_web.app':'src/img_web/app', 'img_web.utils':'src/img_web/utils'},
    package_data = { 'img_web' : ['templates/*.html', 'templates/app/*.html', 'templates/registration/*.html'] },
    data_files = static_files,
)

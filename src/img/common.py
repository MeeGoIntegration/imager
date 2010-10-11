'''
Created on Oct 11, 2010

@author: locusfwork
'''
import os
import io
import random
import pwd,grp
from worker import ImageWorker
import ConfigParser

participant_name = "build_image"

# Fallback configuration. If you need to customize it, copy it somewhere 
# ( ideally to your system's configuration directory ), modify it and 
# pass it with the -c option
defaultconf = """[boss]
amqp_host = 127.0.0.1:5672
amqp_user = boss
amqp_pwd = boss
amqp_vhost = boss
[%s]
daemon = Yes 
logfile = /var/log/%s.log
runas_user = root
runas_group = root
[worker]
base_url = http://192.168.11.2/images/
base_dir = /var/www/images
num_workers = 2
post_creation = /bin/echo
use_kvm = yes
; Example, mic_opts = --save-kernel, --use_comps, so comma separated options
mic_opts =
""" % ( participant_name, participant_name )

try:
    conf = open("/etc/imager/img.conf")
except:
    # Fallback
    conf = io.BytesIO(defaultconf)

config = ConfigParser.ConfigParser()
config.readfp(conf)
conf.close()

amqp_vhost = config.get('boss', 'amqp_vhost')
amqp_pwd = config.get('boss', 'amqp_pwd')
amqp_user = config.get('boss', 'amqp_user')
amqp_host = config.get('boss', 'amqp_host')
d = config.get(participant_name, 'daemon')
daemonize = False
if d == "Yes":
    daemonize = True

config_logfile = config.get(participant_name, 'logfile')
config_logfile = config_logfile+'.'+str(random.randint(1,65535))
runas_user = config.get(participant_name, 'runas_user')
runas_group = config.get(participant_name, 'runas_group')
uid = pwd.getpwnam(runas_user)[2]
gid = grp.getgrnam(runas_group)[2]

use_kvm = config.get('worker', 'use_kvm')
base_url = config.get('worker', 'base_url')
base_dir = config.get('worker', 'base_dir')
post = config.get('worker', 'post_creation')
def mic2(id, name,  type, email, kickstart, release, arch,work_item=None):
        dir = "%s/%s"%(base_dir, id)
        print dir
        os.mkdir(dir, 0775)
        
        ksfilename = ""
        if release:    
            ksfilename = dir+'/meego-'+name+'-'+arch+'-'+release +'.ks' 
        else:
            ksfilename = dir+'/'+name+'.ks'
        
        tmp = open(ksfilename, mode='w+b')
        print tmp.name   
        tmpname = tmp.name
        logfile_name = dir+'/'+name+"-log"
        tmp.write(kickstart)            
        tmp.close()
        os.chmod(tmpname, 0644)
        file = base_url+"%s"%id    
        logfile = open(logfile_name,'w')
        logurl = base_url+id+'/'+os.path.split(logfile.name)[-1]
        worker = ImageWorker(id, tmpname, type, logfile, dir, work_item=work_item, name=name, release=release, arch=arch)
        worker.build()
        logfile.close()
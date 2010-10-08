#!/usr/bin/python2.6
#~ Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
#~ Contact: Ramez Hanna <ramez.hanna@nokia.com>
#~ This program is free software: you can redistribute it and/or modify
#~ it under the terms of the GNU General Public License as published by
#~ the Free Software Foundation, either version 3 of the License, or
#~ (at your option) any later version.

#~ This program is distributed in the hope that it will be useful,
#~ but WITHOUT ANY WARRANTY; without even the implied warranty of
#~ MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#~ GNU General Public License for more details.

#~ You should have received a copy of the GNU General Public License
#~ along with this program.  If not, see <http://www.gnu.org/licenses/>.

import RuoteAMQP
try:
     import simplejson as json
except ImportError:
     import json
import sys
import os
import io
from uuid import uuid1
from optparse import OptionParser
import ConfigParser

config = ConfigParser.ConfigParser()
config.read('/etc/imager/img.conf')
amqp_host = config.get('boss', 'amqp_host')
amqp_user = config.get('boss', 'amqp_user')
amqp_pass = config.get('boss', 'amqp_pwd')
amqp_vhost = config.get('boss', 'amqp_vhost')

defaultconf = """[boss]
amqp_host = 127.0.0.1:5672
amqp_user = boss
amqp_pwd = boss
amqp_vhost = boss
"""



def submit(kickstart, type,  email, name, release, arch):
    # Specify a process definition
    process = """
            Ruote.process_definition :name => 'test' do
              sequence do
                build_image
                notify
              end
            end
          """
    fields= {
            "kickstart" : open(kickstart).read(), 
            "email": email, 
            "id":str(uuid1()), 
            "type":type, 
            "name":name, 
            "release": release, 
	    "arch": arch,
            }
    launcher = RuoteAMQP.Launcher(amqp_host=amqp_host, amqp_user=amqp_user,
                              amqp_pass=amqp_pass, amqp_vhost=amqp_vhost)
    launcher.launch(process, fields)
        

if __name__ == '__main__':
    import sys
    
    usage="usage: %prog -n|--name <name> -t|--type <imagetype> -e|--email <author@email> -r|--release <release> -a|--arch <arch >-s|--submit -k <kickstart_file.ks>"
    description = """
%prog Sends a message (poll for result later) to the BOSS, using <kickstart.ks> 
as the kickstart file. 
"""
    parser = OptionParser(usage=usage, description=description)

    parser.add_option("-s", "--submit", dest="submit", action="store_true",
                      help="Submit to BOSS, takes no options")
    parser.add_option("-k", "--kickstart", dest="kickstart", action="store",
                      help="Kickstart file")
    parser.add_option("-t", "--type", dest="type", action="store", 
                      help="Image type")
    parser.add_option("-n", "--name", dest="name", action="store", 
                      help="Image name")
    parser.add_option("-e", "--email", dest="email", action="store", 
                      help="Author email")
    parser.add_option("-r", "--release", dest="release", action="store", 
                      help="Release for mic2")
    parser.add_option("-a", "--arch", dest="arch", action="store", 
                      help="Target architecture (arm, i586)")
    parser.add_option("-c", "--conf", dest="conf", action="store", 
                      help="alternate configuration file")
    parser.add_option("-o", "--host", dest="amqp_host", action="store", 
                      help="BOSS AMQP host")
    parser.add_option("-u", "--user", dest="amqp_user", action="store", 
                      help="BOSS AMQP user")
    parser.add_option("-p", "--pass", dest="amqp_pwd", action="store", 
                      help="BOSS AMQP password")
    parser.add_option("-v", "--vhost", dest="amqp_vhost", action="store", 
                      help="BOSS AMQP vhost")
    (options, args) = parser.parse_args()

    if options.amqp_host and options.amqp_user and options.amqp_pwd and options.amqp_vhost:
        if options.conf:
            print "Don't specify both config file and connection settings at the same time!"
            sys.exit(1)
        amqp_host = options.amqp_host
        amqp_user = options.amqp_user
        amqp_pass = options.amqp_pwd
        amqp_vhost = options.amqp_vhost
    else:
        try:
            conf = open(options.conf)
        except:
            # Fallback
            print "Warning! falling back to default configuration."
            conf = io.BytesIO(defaultconf)
        
        config = ConfigParser.ConfigParser()
        config.readfp(conf)
        conf.close
        
        amqp_host = config.get('boss', 'amqp_host')
        amqp_user = config.get('boss', 'amqp_user')
        amqp_pass = config.get('boss', 'amqp_pwd')
        amqp_vhost = config.get('boss', 'amqp_vhost')

    path=None
    path = options.kickstart
    if not options.submit:
        parser.error("Missing --submit")
    if options.submit:
        if options.submit and os.path.isfile(path) and options.name and options.email and options.type and options.arch:
            submit(path,options.type,options.email, options.name, options.release, options.arch)
        else:
            print "<kickstart.ks> must be a file and along with this file, you must supply a image name, email, image type and architecture"

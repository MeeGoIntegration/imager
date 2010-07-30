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
from uuid import uuid1
from optparse import OptionParser
import ConfigParser

config = ConfigParser.ConfigParser()
config.read('/etc/imger/img.conf')
amqp_host = config.get('boss', 'amqp_host')
amqp_user = config.get('boss', 'amqp_user')
amqp_pass = config.get('boss', 'amqp_pass')
amqp_vhost = config.get('boss', 'amqp_vhost')

def submit(kickstart, type,  email, name):
    # Specify a process definition
    process = """
            Ruote.process_definition :name => 'test' do
              sequence do
                get_image_from_kickstart
                workitem_dumper
              end
            end
          """
    fields= {
            "kickstart" : open(kickstart).read(), 
            "email": email, 
            "id":str(uuid1()), 
            "type":type, 
            "name":name
            }
    launcher = RuoteAMQP.Launcher(amqp_host=amqp_host, amqp_user=amqp_user,
                              amqp_pass=amqp_pass, amqp_vhost=amqp_vhost)
    launcher.launch(process, fields)
        

if __name__ == '__main__':
    import sys
    
    usage="usage: %prog -t|--type <imagetype> -e|--email <author@email> -s|--submit -k <kickstart_file.ks>"
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

    (options, args) = parser.parse_args()
    path=None
    path = options.kickstart
    if not options.submit:
        parser.error("Missing --submit")
    if options.submit:
        if options.submit and os.path.isfile(path) and options.name and options.email and options.type:
            submit(path,options.type,options.email, options.name)
        else:
            print "<kickstart.ks> must be a file and you must supply a image name, email and image type"

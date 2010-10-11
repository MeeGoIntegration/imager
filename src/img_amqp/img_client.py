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

from amqplib import client_0_8 as amqp
from uuid import uuid1
from optparse import OptionParser
import os
try:
     import json
except ImportError:
     import simplejson as json

import ConfigParser

config = ConfigParser.ConfigParser()
config.read('/etc/imager/img.conf')

amqp_host = config.get('amqp', 'amqp_host')
amqp_user = config.get('amqp', 'amqp_user')
amqp_pwd = config.get('amqp', 'amqp_pwd')
amqp_vhost = config.get('amqp', 'amqp_vhost')

def async_send(fname, email, name, imagetype, release):
    conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
    chan = conn.channel()
    # Read configurations.yaml
    file = open(fname)
    config = file.read()
    id = str(uuid1())
    # Format message as python list
    params = {'ksfile':config, 'email':email, 'imagetype':imagetype if imagetype else 'raw', 'id':id, 'name':name, 'release':release}
    data = json.dumps(params)
    
    msg = amqp.Message(data, message_id=id)
    # Send this message to image exchange, use routing key ks (goes to kickstarter process)
    chan.basic_publish(msg,exchange="image_exchange",routing_key="img")
    chan.close()
    conn.close()
    print "Message sent, use the following id for polling the results.\n%s"%id

def check_message(id, message, chan):
    data = json.loads(message.body)
    if data["id"] == id:
        if "status" in data:
            print "Image build status: %s"%data["status"]
            if "url" in data:
                print "Image url available in: %s"%data["url"]
            if "error" in data:
                print "Image build %s was erroneuos: %s"%(data["id"], data["error"])
            if "log" in data:
                print "Log available here: %s"%data['log']
    else:
        pass
        # No reject available so just requeue it.
        chan.basic_publish(message, exchange=message.delivery_info["exchange"], routing_key=message.delivery_info["routing_key"])
        
def poll(id):
    conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
    chan = conn.channel()
    message = chan.basic_get(queue="status_queue", no_ack=True)
    if message:
        check_message(id, message, chan)
    chan.close()
    conn.close()
if __name__ == '__main__':
    import sys
    
    usage="usage: %prog -p|--poll <id> -n|--name <name> -t|--type <imagetype> -e|--email <author@email> -s|--submit -k <kickstart_file.ks>"
    description = """
%prog Sends a message asynchronously (poll for result later) to 
the IMGer service, using <kickstart.ks> as the kickstart file.
"""
    parser = OptionParser(usage=usage, description=description)

    parser.add_option("-s", "--submit", dest="submit", action="store_true",
                      help="Submit a kickstart file")
    parser.add_option("-p", "--poll", dest="poll", action="store", 
                      help="Poll for results with an id")
    parser.add_option("-t", "--type", dest="type", action="store", 
                      help="Poll for results with an id")
    parser.add_option("-n", "--name", dest="name", action="store", 
                      help="Image name")
    parser.add_option("-e", "--email", dest="email", action="store", 
                      help="Author email")
    parser.add_option("-k", "--kickstart", dest="kickstart", action="store",
                      help="Kickstart file")
    parser.add_option("-r", "--release", dest="release", action="store", 
                      help="Release for mic2")
    parser.add_option("-a", "--arch", dest="arch", action="store", 
                      help="Target architecture (arm, i586)")
    parser.add_option("-c", "--conf", dest="conf", action="store", 
                      help="alternate configuration file")
    (options, args) = parser.parse_args()
    if not options.kickstart and not options.poll:
            parser.error("Missing <kickstart.ks> to parse")
    if options.poll:
        poll(options.poll)
    if not options.submit and not options.poll:
        parser.error("Missing --submit or --poll")
    if not options.poll:        
        if options.submit and os.path.isfile(options.kickstart) and options.name and options.email and options.type and options.arch:
            async_send(options.kickstart,options.email, options.name, options.type, options.release)
        else:
            print "<kickstart.ks> must be a file and you must specify a image name, email and image type"

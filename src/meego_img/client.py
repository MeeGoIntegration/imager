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
     import simplejson as json
except ImportError:
     import json

import ConfigParser

config = ConfigParser.ConfigParser()
config.read('/etc/imger/img.conf')

amqp_host = config.get('amqp', 'amqp_host')
amqp_user = config.get('amqp', 'amqp_user')
amqp_pwd = config.get('amqp', 'amqp_pwd')
amqp_vhost = config.get('amqp', 'amqp_vhost')

def async_send(fname, imagetype=None):
    conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
    chan = conn.channel()
    # Read configurations.yaml
    file = open(fname)
    config = file.read()
    id = str(uuid1())
    # Format message as python list
    params = {'ksfile':config, 'email':"test@test.org", 'imagetype':imagetype if imagetype else 'raw', 'id':id}
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
    
    usage="usage: %prog -p|--poll <message_id> -t|--type <imagetype> -a|--async  <kickstart_file.ks>"
    description = """
%prog Sends a message asynchronously (poll for result later) to 
the IMGer service, using <kickstart.ks> as the kickstart file.
"""
    parser = OptionParser(usage=usage, description=description)

    parser.add_option("-a", "--async", dest="async", action="store_true",
                      help="Asynchronous operation")
    parser.add_option("-p", "--poll", dest="poll", action="store", 
                      help="Poll for results with an id")
    parser.add_option("-t", "--type", dest="type", action="store", 
                      help="Poll for results with an id")

    (options, args) = parser.parse_args()
    path=None
    if not options.poll:        
        if len(args) != 1:
            parser.error("Missing <kickstart.ks> to parse")
        else:
            path=args[0]
    if options.poll:
        poll(options.poll)
    if not options.async and not options.poll:
        parser.error("Missing --async or --poll")
    if not options.poll:        
        if options.async and os.path.isfile(path):
            async_send(path,options.type)
        else:
            print "<kickstart.ks> must be a file"

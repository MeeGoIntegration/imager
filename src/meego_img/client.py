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
import json

amqp_host = "localhost:5672"
amqp_user = "img"
amqp_pwd = "imgpwd"
amqp_vhost = "imgvhost"

def async_send(fname, imagetype=None):
    conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
    chan = conn.channel()
    # Read configurations.yaml
    file = open(fname)
    config = file.read()
    id = str(uuid1())
    # Format message as python list
    params = {'config':config, 'email':"test@test.org", 'imagetype':imagetype if imagetype else 'raw', 'id':id}
    data = json.dumps(params)
    
    msg = amqp.Message(data, message_id=id)
    # Send this message to image exchange, use routing key ks (goes to kickstarter process)
    chan.basic_publish(msg,exchange="image_exchange",routing_key="ks")
    chan.close()
    conn.close()
    print "Message sent, use id %s as the id for polling the results."%id

def check_message(id, message, chan):
    data = json.loads(message.body)
    if data["id"] == id:
        if message.delivery_info["routing_key"] == "res":
            pass
            #chan.basic_ack(message.delivery_tag)    
        elif message.delivery_info["routing_key"] == "status":
            print "Image build status: %s"%data["status"]
            #chan.basic_ack(message.delivery_tag)
        elif message.delivery_info["routing_key"] == "err":
            print "Image build was erroneuos with the following error: %s\nDownload the logfile from here: %s"%(data["error"], data["url"])
            #chan.basic_ack(message.delivery_tag)
        elif message.delivery_info["routing_key"] == "link":
            print "Image build was successfull!\nDownload the image from here: %s"%data["url"]
            #chan.basic_ack(message.delivery_tag)
    else:
        pass
        # No reject available so just requeue it.
        chan.basic_publish(message, exchange=message.delivery_info["exchange"], routing_key=message.delivery_info["routing_key"])
        
def poll(id):
    conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
    chan = conn.channel()
    queues = ["result_queue","error_queue", "status_queue", "link_queue"]
    for queue in queues:
        message = chan.basic_get(queue=queue, no_ack=True)
        if message:
            check_message(id, message, chan)
    chan.close()
    conn.close()
if __name__ == '__main__':
    import sys
    
    usage="usage: %prog -p|--poll <message_id> -t|--type <imagetype> -a|--async  <kickstarter_template.yaml>"
    description = """
%prog Sends a message asynchronously (poll for result later) to 
the IMGer service, using <kickstarter_template.yaml> as the template.
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
            parser.error("Missing <kickstarter_template.yaml> to parse")
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
            print "<kickstarter_template.yaml> must be a file"

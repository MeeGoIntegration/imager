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

def error_callback(msg):
    print "Received error message: %s"%msg.body
    chan.basic_ack(msg.delivery_tag)
    
def result_callback(msg):
    print "Result message received: %s"%msg.body
    chan.basic_ack(msg.delivery_tag)

def sync_send(fname):
    conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
    chan = conn.channel()
    # Read configurations.yaml
    file = open(fname)
    config = file.read()
    id = str(uuid1())
    # Format message as python list
    params = {'config':config, 'email':"test@test.org", 'imagetype':'raw', 'id':id}
    data = json.dumps(params)
    
    msg = amqp.Message(data, message_id=id)
    # Send this message to image exchange, use routing key ks (goes to kickstarter process)
    chan.basic_publish(msg,exchange="image_exchange",routing_key="ks")
    
    chan.basic_consume(queue='error_queue', no_ack=True, callback=error_callback)
    chan.basic_consume(queue='result_queue', no_ack=True, callback=result_callback)
    while True:
        chan.wait()
    chan.close()
    conn.close()
    
def async_send(fname):
    conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
    chan = conn.channel()
    # Read configurations.yaml
    file = open(fname)
    config = file.read()
    id = str(uuid1())
    # Format message as python list
    params = {'config':config, 'email':"test@test.org", 'imagetype':'raw', 'id':id}
    data = json.dumps(params)
    
    msg = amqp.Message(data, message_id=id)
    # Send this message to image exchange, use routing key ks (goes to kickstarter process)
    chan.basic_publish(msg,exchange="image_exchange",routing_key="ks")
    chan.close()
    conn.close()
    print "Message sent, use id %s as the id for polling the results."%id
    
def poll(id):
    conn = amqp.Connection(host=amqp_host, userid=amqp_user, password=amqp_pwd, virtual_host=amqp_vhost, insist=False)
    chan = conn.channel()
    result_msg = chan.basic_get("result_queue", no_ack=True)
    error_msg = chan.basic_get("error_queue", no_ack=True)
    status_msg = chan.basic_get("status_queue", no_ack=True)
    link_msg = chan.basic_get("link_queue", no_ack=True)
    if result_msg:
        result_data = json.loads(result_msg.body)
        if result_data["id"] == id:
            print "Got a message from result queue: \nLogfile name: %s"%result_data["logfile"]
            chan.basic_ack(result_msg.delivery_tag)
        else:
            print "Got a message from result queue, but not for this ID. Please repoll!"
            chan.basic_reject(result_msg.delivery_tag, requeue=True)
    if error_msg:
        error_data = json.loads(error_msg.body)
        if error_data["id"] == id:
            print "Got a message from error queue: \nError that occurred: %s\nDownload the log from: %s\n"%(error_data["error"], error_data["imagefile"])
            chan.basic_ack(error_msg.delivery_tag)
        else:
            print "Got a message from error queue, but not for this ID. Please repoll!"
            chan.basic_reject(error_msg.delivery_tag, requeue=True)
    if status_msg:
        status_data = json.loads(status_msg.body)
        if status_data["id"] == id:
            print "Got a message from result queue: \nStatus of build is: %s"%status_data["status"]
            chan.basic_ack(status_msg.delivery_tag)
        else:
            print "Got a message from result queue, but not for this ID. Please repoll!"
            chan.basic_reject(status_msg.delivery_tag, requeue=True)
    if link_msg:
        link_data = json.loads(link_msg.body)
        if link_data["id"] == id:
            print "Got a message from link queue, your download can be found here: %s"%link_data["imagefile"]
            chan.basic_ack(link_msg.delivery_tag)
        else:
            print "Got a message from link queue, but not for this ID. Please repoll!"
            chan.basic_reject(link_msg.delivery_tag, requeue=True)
    chan.close()
    conn.close()
if __name__ == '__main__':
    import sys
    
    usage="usage: %prog -p|--poll <message_id> -a|--async -s|--sync <kickstarter_template.yaml>"
    description = """
%prog Sends a message either asynchronously (poll for result later) or 
synchronously (wait for the result) to the IMGer service, 
using <kickstarter_template.yaml> as the template.
"""
    parser = OptionParser(usage=usage, description=description)

    parser.add_option("-a", "--async", dest="async", action="store_true",
                      help="Asynchronous operation")
    parser.add_option("-s", "--sync", dest="sync", action="store_true",
                      help="Synchronous operation")
    parser.add_option("-p", "--poll", dest="poll", action="store", 
                      help="Poll for results with an id")

    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("Missing <kickstarter_template.yaml> to parse")
    else:
        path=args[0]

    if not options.async and not options.sync:
        parser.error("Missing --async or --sync")
    if options.sync and os.path.isfile(path):
        sync_send(path)
    else:
        print "<kickstarter_template.yaml> must be a file"
    if options.async and os.path.isfile(path):
        async_send(path)
    else:
        print "<kickstarter_template.yaml> must be a file"

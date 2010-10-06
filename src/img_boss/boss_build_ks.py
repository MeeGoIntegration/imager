#!/usr/bin/python
import pykickstart.commands as kscommands
import pykickstart.constants as ksconstants
import pykickstart.errors as kserrors
import pykickstart.parser as ksparser
import pykickstart.version as ksversion
from pykickstart.handlers.control import commandMap
from pykickstart.handlers.control import dataMap

from mic.imgcreate.kscommands import desktop 
from mic.imgcreate.kscommands import moblinrepo
from mic.imgcreate.kscommands import micboot 
from  RuoteAMQP.workitem import Workitem
from  RuoteAMQP.participant import Participant
try:
     import json
except ImportError:
     import simplejson as json
from uuid import uuid1
import os, sys, traceback, ConfigParser, optparse, io, pwd, grp
import daemon

participant_name = "build_ks"

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
runas_user = nobody
runas_group = nogroup
ksfile = /srv/BOSS/ks/meego-handset-armv7l.ks
reposerver = http://download.meego.com
""" % ( participant_name, participant_name ) 

parser = optparse.OptionParser()
parser.add_option("-c", "--config", dest="filename", 
                  help="read configuration from CFILE", metavar="CFILE")
(options, args) = parser.parse_args()

try:
    conf = open(options.filename)
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

logfile = config.get(participant_name, 'logfile')
runas_user = config.get(participant_name, 'runas_user')
runas_group = config.get(participant_name, 'runas_group')
uid = pwd.getpwnam(runas_user)[2]
gid = grp.getgrnam(runas_group)[2]

ksfile = config.get(participant_name, "ksfile")
reposerver = config.get(participant_name, "reposerver")

using_version = ksversion.DEVEL
commandMap[using_version]["desktop"] = desktop.Moblin_Desktop
commandMap[using_version]["repo"] = moblinrepo.Moblin_Repo
commandMap[using_version]["bootloader"] = micboot.Moblin_Bootloader
dataMap[using_version]["RepoData"] = moblinrepo.Moblin_RepoData
superclass = ksversion.returnClassForVersion(version=using_version)



class KSHandlers(superclass):
    def __init__(self, mapping={}):
        superclass.__init__(self, mapping=commandMap[using_version])
    

packages= {}
class KickstartBuilderParticipant(Participant):    
    def consume(self):
        try:
            wi = self.workitem
            print json.dumps(wi.to_h(), sort_keys=True, indent=4)
            fields = wi.fields()
            project = fields["project"] 
            repo = fields["repository"]
            print str(fields["packages"])
            ks = ksparser.KickstartParser(KSHandlers())
            ks.readKickstart(ksfile)
            ks.handler.packages.add(fields["packages"])
            project_uri = project.replace(":", ":/")
            repo = repo.replace(":", ":/")
            base_url = reposerver+'/'+project_uri+'/'+repo
            ks.handler.repo.repoList.append(moblinrepo.Moblin_RepoData(baseurl=base_url,name=project))
            # We got the damn thing published, move on
            wi.set_field("kickstart", str(ks.handler))
            wi.set_field("id", str(uuid1()))
            wi.set_field("name", os.path.basename(ksfile)[0:-3])
            print json.dumps(wi.to_h(), sort_keys=True, indent=4)
            result = True
        except Exception as e:
            print type(e)
            print e
            traceback.print_exc(file=sys.stdout)
            result = False
            pass
        wi.set_result(result)
  
def main():
    print "Kickstart building participant running"
    # Create an instance
    p = KickstartBuilderParticipant(ruote_queue=participant_name, amqp_host=amqp_host,  amqp_user=amqp_user, amqp_pass=amqp_pwd, amqp_vhost=amqp_vhost)
    # Register with BOSS
    p.register(participant_name, {'queue':participant_name})
    # Enter event loop
    p.run()               

if __name__ == "__main__":
    if daemonize:
        log = open(logfile,'a+')
        with daemon.DaemonContext(stdout=log, stderr=log, uid=uid, gid=gid):
            main()
    else:
        main() 

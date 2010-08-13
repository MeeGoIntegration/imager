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
     import simplejson as json
except ImportError:
     import json
from uuid import uuid1
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
    
        
    def collect_and_send(self, wi):            
        print json.dumps(wi.to_h(), sort_keys=True, indent=4)       
        fields = wi.fields()
        event = fields["obsEvent"]
        type = event["type"]
        print type
        print fields
        if type == "OBS_BUILD_SUCCESS":
            package = event["package"]
            project = event["project"]
            reposerver = event["reposerver"]
            repo = event["repository"]
            if project in packages:
                if repo in packages[project]:
                    packages[project][repo]["packages"].append(package)
                    packages[project][repo]["reposerver"] = reposerver
                else:
                    packages[project][repo] = {"packages":[]}    
            else:                                                
                packages[project] = {repo:{"packages":[],}}                
                packages[project][repo]["packages"].append(package)
                packages[project][repo]["reposerver"] = reposerver
            wi.set_result(False)
            
        elif type == "OBS_REPO_PUBLISHED":            
            project = event["project"]
            repo = event["repo"]
            print str(packages[project][repo]["packages"])
            ks = ksparser.KickstartParser(KSHandlers())
            ks.readKickstart("/home/locusfwork/kickstart/meego-netbook-chromium-ia32-1.0-20100524.1.ks")
            ks.handler.packages.add(packages[project][repo]["packages"])
            reposerver = packages[project][repo]["reposerver"]
            project_uri = project.replace(":", ":/")
            repo = repo.replace(":", ":/")
            base_url = reposerver+'/'+project_uri+'/'+repo
            ks.handler.repo.repoList.append(moblinrepo.Moblin_RepoData(baseurl=base_url,name=project))
            # We got the damn thing published, move on
            packages[project][repo]["packages"] = []
            packages[project][repo]["reposerver"] = ""
            wi.set_field("kickstart", str(ks.handler))
            wi.set_field("email", "test@vm1")
            wi.set_field("id", str(uuid1()))
            wi.set_field("type", "raw")
            wi.set_field("name", project)
        
    def consume(self):
        wi = self.workitem                
        self.collect_and_send(wi)
        
        
if __name__ == "__main__":
    print "Kickstart building participant running"
    p = KickstartBuilderParticipant(ruote_queue="build_ks", amqp_host="boss", amqp_user='boss', amqp_pass='boss', amqp_vhost="boss" )
    p.register("build_ks", {'queue':'build_ks'})
    p.run()

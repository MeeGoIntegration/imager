
from  RuoteAMQP.workitem import Workitem
from  RuoteAMQP.participant import Participant
import json

class DumpParticipant(Participant):
    def consume(self):
        wi = self.workitem
        print json.dumps(wi.to_h())
        
if __name__ == "__main__":
    print "Started a python participant"
    p = DumpParticipant(ruote_queue="dumper", amqp_vhost="ruote-test")
    p.register("workitem_dumper", {'queue':'dumper'})
    p.run()

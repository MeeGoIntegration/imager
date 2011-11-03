import re
import unittest
from ConfigParser import SafeConfigParser

from RuoteAMQP import Workitem
from SkyNET.Control import WorkItemCtrl, ParticipantCtrl

import build_ks as mut

WI_TEMPLATE = """{
 "fei": {"wfid": "x", "subid": "x", "expid": "x", "engine_id": "x"},
 "fields": {"params": {}, "ev":{}},
 "participant_name": "fake_participant"
}"""

class TestParticipantHandler(unittest.TestCase):

    def assertRaisesRegexp(self, exc, rex, method, *args, **kwargs):
        # python 2.7 provides this method by default but we don't require
        # that version yet.
        try:
            method(*args, **kwargs)
        except exc, exobj:
            if isinstance(rex, basestring):
               rex = re.compile(rex)
            exstr = str(exobj)
            if not rex.search(exstr):
                raise AssertionError('"%s" does not match "%s"' %
                                     (rex.pattern, exstr))
            return
        raise AssertionError('"%s" not raised"' % exc.__name__)

    def setUp(self):
        self.participant = mut.ParticipantHandler()
        self.wid = Workitem(WI_TEMPLATE)
        self.wid.fields.image = {}
        self.wid.fields.image.ksfile = "generic.ks"

    def setup_participant(self):
        self.participant.reposerver = "http://example.com/repo"
        self.participant.ksstore = "tests/test_data/ksstore"

    def test_wi_control(self):
        ctrl = ParticipantCtrl()
        self.participant.handle_wi_control(ctrl)

    def test_lifecycle_control(self):
        ctrl = WorkItemCtrl('start')
        ctrl.config = SafeConfigParser()
        ctrl.config.read("img_boss/build_ks.conf")
	self.participant.handle_lifecycle_control(ctrl)

    def test_handle_wi(self):
        self.setup_participant()
        self.participant.handle_wi(self.wid)
        self.assertTrue(self.wid.result)
        self.assertTrue(self.wid.fields.image.kickstart)
        # workitem with no parameters should have left it unchanged
        kickstart = open("tests/test_data/ksstore/generic.ks").read()
        self.assertEqual(self.wid.fields.image.kickstart, kickstart)

    def test_missing_imagefields(self):
        self.wid.fields.image = None
        self.assertRaisesRegexp(RuntimeError, "image",
                                self.participant.handle_wi, self.wid)

    def test_missing_ks(self):
        self.wid.fields.image.kickstart = None
        self.wid.fields.image.ksfile = None
        self.assertRaisesRegexp(RuntimeError, "kickstart",
                          self.participant.handle_wi, self.wid)

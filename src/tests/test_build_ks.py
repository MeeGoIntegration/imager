import json
import re
import os
import unittest
from configparser import SafeConfigParser
from mock import Mock

from RuoteAMQP import Workitem
from buildservice import BuildService
from SkyNET.Control import WorkItemCtrl, ParticipantCtrl

import build_ks as mut

WI_TEMPLATE = """{
 "fei": {"wfid": "x", "subid": "x", "expid": "x", "engine_id": "x"},
 "fields": {"params": {}, "ev":{}},
 "participant_name": "fake_participant"
}"""

REPOSERVER = "http://example.com/repo"
KSSTORE = "tests/test_data/ksstore"
KSFILE = "generic.ks"
IMAGENAME = "generic"


class TestParticipantHandler(unittest.TestCase):

    def assertRaisesRegexp(self, exc, rex, method, *args, **kwargs):
        # python 2.7 provides this method by default but we don't require
        # that version yet.
        try:
            method(*args, **kwargs)
        except exc as exobj:
            if isinstance(rex, str):
                rex = re.compile(rex)
            exstr = str(exobj)
            if not rex.search(exstr):
                raise AssertionError('"%s" does not match "%s"' %
                                     (rex.pattern, exstr))
            return
        raise AssertionError('"%s" not raised"' % exc.__name__)

    def setUp(self):
        self.participant = mut.ParticipantHandler()
        self.participant.reposerver = REPOSERVER
        self.participant.ksstore = KSSTORE
        self.wid = Workitem(WI_TEMPLATE)
        self.wid.fields.image = {}
        self.wid.fields.image.ksfile = KSFILE

    def test_wi_control(self):
        ctrl = ParticipantCtrl()
        self.participant.handle_wi_control(ctrl)

    def test_lifecycle_control(self):
        # Use a fresh participant without any config initialization
        self.participant = mut.ParticipantHandler()
        ctrl = WorkItemCtrl('start')
        ctrl.config = SafeConfigParser()
        ctrl.config.read("img_boss/build_ks.conf")
        self.participant.handle_lifecycle_control(ctrl)

    def test_handle_wi(self):
        self.participant.handle_wi(self.wid)
        self.assertTrue(self.wid.result)
        self.assertTrue(self.wid.fields.image.kickstart)
        self.assertEqual(self.wid.fields.image.name, IMAGENAME)
        # workitem with no parameters should have left it unchanged
        kickstart = open(os.path.join(KSSTORE, KSFILE)).read()
        self.assertEqual(self.wid.fields.image.kickstart, kickstart)

    def test_missing_imagefields(self):
        self.wid.fields.image = None
        self.assertRaisesRegexp(RuntimeError, "image",
                                self.participant.handle_wi, self.wid)

    def test_missing_ks(self):
        self.wid.fields.image.kickstart = None
        self.wid.fields.image.ksfile = None
        self.assertRaisesRegexp(
            RuntimeError, "kickstart",
            self.participant.handle_wi, self.wid
        )

    def handle_wi_helper(self, strings):
        """Call handle_wi and check that it was successful and the
           resulting kickstarts contains certain strings."""
        self.participant.handle_wi(self.wid)
        self.assertTrue(self.wid.result)
        for string in strings:
            self.assertTrue(
                string in self.wid.fields.image.kickstart,
                "%s not found in kickstart" % string
            )

    def test_extra_repos(self):
        repos = ['http://example.com/extra1', 'http://example.com/extra2']
        self.wid.fields.image.extra_repos = repos[:]
        self.handle_wi_helper(repos)

        self.wid.fields.image.extra_repos = "not a list"
        self.assertRaisesRegexp(
            RuntimeError, "list",
            self.participant.handle_wi, self.wid
        )

    def test_packages_field(self):
        packages = ['package1', 'package2', 'package3', 'package4']
        self.wid.fields.image.packages = packages[:]
        self.handle_wi_helper(packages)

        self.wid.fields.image.packages = "not a list"
        self.assertRaisesRegexp(
            RuntimeError, "list",
            self.participant.handle_wi, self.wid
        )

    def test_packages_param(self):
        packages = ['package1', 'package2', 'package3', 'package4']
        self.wid.params.packages = packages[:]
        self.handle_wi_helper(packages)

        self.wid.params.packages = "not a list"
        self.assertRaisesRegexp(
            RuntimeError, "list",
            self.participant.handle_wi, self.wid
        )

    def test_packages_param_added(self):
        packages1 = ['package1', 'package2']
        packages2 = ['parmpackage1', 'parmpackage2']
        self.wid.fields.image.packages = packages1[:]
        self.wid.params.packages = packages2[:]
        self.handle_wi_helper(packages1 + packages2)

    def test_packages_from(self):
        packages = ['package1', 'package2', 'package3', 'package4']
        self.wid.params.packages_from = "arglblargl"
        self.wid.fields.arglblargl = packages[:]
        self.handle_wi_helper(packages)

        self.wid.fields.arglblargl = "not a list"
        self.assertRaisesRegexp(
            RuntimeError, "list",
            self.participant.handle_wi, self.wid
        )

        # nonexistent packages_from field should be treated like an empty list
        self.wid.params.packages_from = "nonexistentfield"
        self.participant.handle_wi(self.wid)
        self.assertTrue(self.wid.result)

    def test_groups_field(self):
        groups = ['group one', 'group two']
        self.wid.fields.image.groups = groups[:]
        self.handle_wi_helper(groups)

        self.wid.fields.image.groups = "not a list"
        self.assertRaisesRegexp(
            RuntimeError, "list",
            self.participant.handle_wi, self.wid
        )

    def test_groups_param(self):
        groups = ['group1', 'group2', 'group3', 'group4']
        self.wid.params.groups = groups[:]
        self.handle_wi_helper(groups)

        self.wid.params.groups = "not a list"
        self.assertRaisesRegexp(
            RuntimeError, "list",
            self.participant.handle_wi, self.wid
        )

    def test_groups_param_added(self):
        groups1 = ['group1', 'group2']
        groups2 = ['parmgroup1', 'parmgroup2']
        self.wid.fields.image.groups = groups1[:]
        self.wid.params.groups = groups2[:]
        self.handle_wi_helper(groups1 + groups2)

    def test_groups_from(self):
        groups = ['group1', 'group2', 'group3', 'group4']
        self.wid.params.groups_from = "arglblargl"
        self.wid.fields.arglblargl = groups[:]
        self.handle_wi_helper(groups)

        self.wid.fields.arglblargl = "not a list"
        self.assertRaisesRegexp(
            RuntimeError, "list",
            self.participant.handle_wi, self.wid
        )

        # nonexistent groups_from field should be treated like an empty list
        self.wid.params.groups_from = "nonexistentfield"
        self.participant.handle_wi(self.wid)
        self.assertTrue(self.wid.result)

    def test_kickstart_field(self):
        kickstart = open(os.path.join(KSSTORE, KSFILE)).read()
        self.wid.fields.image.name = IMAGENAME
        self.wid.fields.image.kickstart = kickstart
        self.wid.fields.image.ksfile = None

        self.participant.handle_wi(self.wid)

        self.assertTrue(self.wid.result)
        self.assertEqual(self.wid.fields.image.name, IMAGENAME)
        self.assertTrue(self.wid.fields.image.kickstart)
        # workitem with no parameters should have left it unchanged
        self.assertEqual(self.wid.fields.image.kickstart, kickstart)

    def test_packages_event_param(self):
        self.wid.fields.ev.actions = [
            dict(sourceproject="fakesource", sourcepackage="fakesourcep1",
                 targetproject="faketarget", targetpackage="faketargetp1"),
            dict(sourceproject="fakesource", sourcepackage="fakesourcep2",
                 targetproject="faketarget", targetpackage="faketargetp2"),
        ]
        self.wid.params.packages_event = 'True'
        self.handle_wi_helper(["faketargetp1", "faketargetp2"])

    def test_stringified_lists(self):
        """For convenience in ruote syntax, the participant should be
           able to take lists in json encoded form. Test this for
           just one parameter because the handling is the same for all
           of them.
        """
        packages = ['package1', 'package2', 'package3', 'package4']
        self.wid.params.packages = json.dumps(packages)
        self.handle_wi_helper(packages)

    def test_project_field(self):
        self.wid.fields.project = "Chalk:Testing"
        self.wid.params.repository = "standard_chalk"
        self.handle_wi_helper([REPOSERVER + "/Chalk:/Testing/standard_chalk"])

    def test_project_repository_lookup(self):
        self.wid.fields.project = "Chalk:Testing"
        self.wid.fields.ev.namespace = "OBS"
        obs = Mock(spec_set=BuildService)
        obs.getProjectRepositories.return_value = ["standard_chalk", "other"]
        mut.BuildService = Mock(return_value=obs)
        urls = [REPOSERVER + "/Chalk:/Testing/standard_chalk",
                REPOSERVER + "/Chalk:/Testing/other"]
        self.handle_wi_helper(urls)

        self.wid.fields.ev.namespace = None
        self.assertRaisesRegexp(
            RuntimeError, "namespace",
            self.participant.handle_wi, self.wid
        )

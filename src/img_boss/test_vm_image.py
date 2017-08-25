#!/usr/bin/python
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
"""test images using testrunner and related tools. 

:term:`Workitem` fields IN:

:Parameters:

:term:`Workitem` fields OUT:

:Returns:
"""

from img.common import tester_config
from img.tester import ImageTester
from RuoteAMQP import Launcher 

class ParticipantHandler(object):
    """Participant class as defined by the SkyNET API"""

    def __init__(self):

        self.launcher = None
        self.process = \
        """Ruote.process_definition 'test_image_ondemand' do
             sequence do
               set :f => 'debug_dump', :value => 'true'
               update_image_status :status => '%s'
             end
           end
        """

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass

    def push_img_status(self, status, fields):
        """ function to push status by launching a process, ?utility """
        fields.update({"priority" : "high"})
        self.launcher.launch(self.process % status, fields)

    def handle_lifecycle_control(self, ctrl):
        if ctrl.message == "start":
            self.config = tester_config(config=ctrl.config)
            self.launcher = Launcher(amqp_host = ctrl.config.get("boss",
                                                                 "amqp_host"),
                                     amqp_user = ctrl.config.get("boss",
                                                                 "amqp_user"),
                                     amqp_pass = ctrl.config.get("boss",
                                                                 "amqp_pwd"),
                                     amqp_vhost = ctrl.config.get("boss",
                                                                  "amqp_vhost")
                                     )

    def handle_wi(self, wid):
        wid.result = False
        f = wid.fields
        if not f.msg:
            f.msg = []

        jargs = f.image.as_dict()

        test_packages = {} 
        if f.qa and f.qa.selected_test_packages:
            test_packages = f.qa.selected_test_packages.as_dict()

        try:
            tester = ImageTester(config=self.config,
                                 job_args=jargs,
                                 test_packages=test_packages)

            self.push_img_status("DONE, TESTING", f.as_dict())

            tester.test()

            f.image.test_result = tester.get_results()["result"]
            if not f.qa:
                f.qa = {}
            f.qa.results = tester.get_results()

        except Exception, error:
            f.__error__ = 'Image test FAILED: %s' % error
            f.msg.append(f.__error__)
            raise
        else:
            self.push_img_status("DONE, TESTED", f.as_dict())
            wid.result = f.image.test_result

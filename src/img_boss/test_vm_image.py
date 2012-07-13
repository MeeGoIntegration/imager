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

class ParticipantHandler(object):

    def __init__(self):
        self.config = None

    def handle_wi_control(self, ctrl):
        pass

    def handle_lifecycle_control(self, ctrl):
        if ctrl.message == "start":
            self.config = tester_config(config=ctrl.config)

    def handle_wi(self, wid):
        wid.result = False
        f = wid.fields
        if not f.msg:
            f.msg = []

        jargs = f.image.as_dict()

        try:
            tester = ImageTester(config=self.config,
                                 job_args=jargs,
                                 test_packages=f.qa.selected_test_packages)

            tester.test()

            f.image.test_result = tester.get_results()["result"]

        except Exception, error:
            f.__error__ = 'Image test FAILED: %s' % error
            f.msg.append(f.__error__)
            raise

#!/usr/bin/python
# Copyright (C) 2013 David Greaves <david@dgreaves.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Converts mic raw image to VDI format.

.. warning ::

   * The make_vdi participant must run on the master nfs share
   * Must have run after build_image and relies on a valid
     build_image workitem

:term:`Workitem` fields IN:

:Parameters:

   :vboxmanage.process (Boolean):
      If false then the participant is skipped
   :vboxmanage.format (string):
      As per VBoxManage --format; one of VDI|VMDK|VHD
   :vboxmanage.variant (string):
      OPTIONAL As per VBoxManage --variant; one or more of:
        Standard,Fixed,Split2G,Stream,ESX

:term:`Workitem` fields OUT:

:Returns:
  :result (Boolean):
     True if everything was OK, False otherwise
"""

from RuoteAMQP.workitem import DictAttrProxy as dap

import os.path
import subprocess


class ParticipantHandler(object):
    """Participant class as defined by the SkyNET API"""

    def __init__(self):
        self.worker_config = None

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass

    def handle_lifecycle_control(self, ctrl):
        """ participant control thread """
        if ctrl.message == "start":
            if ctrl.config.has_section("make_vdi"):
                self.config = dap({})
                self.config.base_url = ctrl.config.get("make_vdi", "base_url")
                self.config.base_dir = ctrl.config.get("make_vdi", "base_dir")
                self.log.debug("config base_url %s" % self.config.base_url)

    def handle_wi(self, wid):
        """Handle the workitem to convert an image
        """
        f = wid.fields

        if not f.image or not f.image.image_type or not f.image.image_url:
            raise RuntimeError("Missing mandatory field 'image'")

        if not f.image.image_type == "raw":
            return False, "Image type is not raw"

        raw = os.path.abspath(
            f.image.image_url.replace(
                self.config.base_url, self.config.base_dir
            )
        )
        if not os.path.isfile(raw):
            return False, "Image file %s not present at %s\n" % (
                f.image.image_url, raw)

        if not raw.endswith(".raw"):
            try:
                orig = raw
                # Try to uncompress
                if raw.endswith(".gz"):
                    self.log.debug("gunzip %s\n" % raw)
                    subprocess.check_output(["gunzip", raw])
                    raw = raw[0:-3]
                if raw.endswith(".tar.bz2"):
                    self.log.debug(
                        "extracting: tar xv -C %s -f %s\n",
                        os.path.dirname(raw), raw,
                    )
                    new_raw = subprocess.check_output(
                        ["tar", "xv", "-C", os.path.dirname(raw), "-f", raw]
                    ).rstrip('\n')
                    subprocess.check_output(["rm", raw])
                    raw = raw[0:-8] + ".raw"
                    os.rename(os.path.join(os.path.dirname(raw), new_raw),
                              raw)
                if raw.endswith(".bz2"):
                    self.log.debug("bunzip2 %s\n" % raw)
                    subprocess.check_output(["bunzip2", raw])
                    raw = raw[0:-4]
            except subprocess.CalledProcessError as e:
                return (
                    False,
                    "Failed whilst trying to uncompress %s.\n%s\n" % (
                        raw, e.output
                    ),
                )
            if not raw.endswith(".raw") and not os.path.isfile(raw):
                return (
                    False,
                    "Failed to convert %s to a .raw called %s" % (orig, raw),
                )
            self.log.info("Unpacked raw file to %s" % raw)
        try:
            vdi = raw[0:-3]+"VDI"
            command = ["VBoxManage", "convertfromraw", raw, vdi]
            if f.vboxmanage and f.vboxmanage.format:
                command.append("--format=%s" % f.vboxmanage.format)
            else:
                command.append("--format=%s" % "VDI")

            if f.vboxmanage and f.vboxmanage.variant:
                command.append("--variant=%s" % f.vboxmanage.variant)

            self.log.info(" ".join(command))
            subprocess.check_output(command)
            subprocess.check_call(["chmod", "0664", vdi])
            subprocess.check_call(["bzip2", "--fast", vdi])
            subprocess.check_call(["chown", "-R", "img", os.path.dirname(raw)])
        except subprocess.CalledProcessError as e:
            return False, "Running convertfromraw failed:\n%s" % e.output

        # Cleanup
        for key in ["image_type", "image_url"]:
            try:
                del f.image.as_dict()[key]
            except IndexError:
                pass
        os.remove(raw)

        return True

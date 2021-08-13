#!/usr/bin/python
"""Creates an Imager Job in the web ui.

The paramaters are similar to the build_image participant.

The job is put in the "requests" queue which doesn't launch a process
as there is already a process calling this participant.

   :image.template_name
      The template to use

   :image.user
      The username that appears in Imager

   :image.overrides contains values to override the template/Imager defaults
      These are the same as the hints in the kickstart header used by Imager.
      They are:
         .displayname
         .kickstarttype : release, rnd
         .devicemodel
         .devicevariant
         .brand
         .features : csv list of feature names
         .imagetype : loop, fs etc
         .architecture
         .tokenmap : csv list of TOKEN:VALUE pairs

   :reports.img.release (string):
      The 4 part release value such as 4.1.0.24
   :reports.img.release_id (string):
      The date-based release value such as 0.20210809.0.1
   :reports.img.device (string):
      The value used to import the image to reports.jollamobile.com

:term:`Workitem` fields OUT:

:Returns:
  :make_vdi :
     True if the make_vdi process should run


  :result (Boolean):
     True if everything was OK, False otherwise

"""

import django
import json
import os
import re
import time
os.environ['DJANGO_SETTINGS_MODULE'] = 'img_web.settings'
# django.setup()  # Not needed for super-early django
from img_web import settings
from img_web.app.models import ImageJob, Queue, Token
from img_web.app.features import list_features, expand_feature
from img_web.app.features import get_repos_packages_for_feature
from django.contrib.auth.models import User
from django.db import IntegrityError

# def parse_template_ks(ksfilename)->[str, dict]:
def parse_template_ks(ksfilename):
    """Takes a ks template and returns the ks part and the analysed header
    comments

    """
    # re's taken from imager forms.py
    suggested_re = re.compile(
        r'^#.*?Suggested(Architecture|ImageType|Features):(.*)$'
    )
    device_re = re.compile(
        r'^#.*?(DeviceModel|DeviceVariant|Brand):(.*)$'
    )
    display_re = re.compile(r'^#.*?(DisplayName):(.+)$')

    # re taken from imager views.py
    type_re = re.compile(r'^#.*?(KickstartType):(.+)$')

    filename = os.path.join(settings.TEMPLATESDIR, ksfilename)
    with open(filename, mode='r') as ffd:
        ks = ffd.read()

    defaults = {}
    for line in ks.splitlines():
        match = (display_re.match(line) or device_re.match(line)
                 or suggested_re.match(line) or type_re.match(line))
        if match:
            key = match.group(1).lower()
            val = match.group(2).strip()
            defaults[key] = val

    print("defaults: %s" % defaults)
    return (ks, defaults)


# https://stackoverflow.com/questions/7204805/how-to-merge-dictionaries-of-dictionaries/7205107#7205107
def merge(a, b, path=None):
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


class ParticipantHandler:
    """Participant class as defined by the SkyNET API"""

    def __init__(self):
        pass

    def handle_wi_control(self, ctrl):
        """ job control thread """
        pass

    def handle_lifecycle_control(self, ctrl):
        """ participant control thread """
        pass

    def handle_wi(self, wid):
        """
        """
        wid.result = False
        f = wid.fields
        if not f.msg:
            f.msg = []

        if not (f.image and f.image.template_name):
        #     missing = [fname for fname in ("image", "image.template_name")
        #                      if not (f.has_key(fname) and
        #                              f[fname])]
             f.__error__ = "One of the mandatory fields doesn't exist."
             f.msg.append(f.__error__)
             raise RuntimeError("Missing mandatory field")
        #     raise RuntimeError("Missing mandatory fields: %s"
        #                        % ",".join(missing))

        # Get the input data from the fields:
        ksname = f.image.template_name
        user = f.image.user
        overrides = f.image.overrides.as_dict()

        # Setup empty containers
        extra_repos = set()
        extra_packages = set()

        # Now we handle the templating in as similar way as possible
        # to the web ui (mainly views.py)

        # Some attrs go into the tokenmap so create that with the defaults
        tokenmap = Token.defaults_as_dict()
        print("Default tokens %s" % tokenmap)
        if "tokenmap" in overrides:
            # split to a csv of "k:v" and then split each on : and use
            # dict on the list of pairs
            tmap = dict(map(lambda s:
                            s.split(":",1), overrides["tokenmap"].split(",")))
            print("tmap")
            print(tmap)
            tokenmap.update(tmap)
        print("Overridden tokens %s" % tokenmap)

        # Get the ks contents (no substitutions) and the parsed out
        # header attributes
        (ks, default_attrs) = parse_template_ks(
            "%s/%s" % (settings.TEMPLATESDIR, ksname))

        # Now we've read the contents, remove the ".ks" as this is now
        # just used to name files (keeping the code similar to views.py)
        if ksname.endswith('.ks'):
            ksname = ksname[0:-3]

        # Handle the headers
        # kickstarttype must be handled before features
        for attr in ("displayname", "kickstarttype", "devicemodel",
                     "devicevariant", "brand", "features", "imagetype",
                     "architecture"):
            # get the value from the field overrides, fallback to the defaults
            try:
                value = overrides[attr]
            except KeyError:
                try:
                    value = default_attrs[attr]
                except KeyError:
                    raise MissingAttrException(
                        "Attribute %s is not in the overrides or ks template" % attr)
            # Some of these also cause tokens to be set
            # see code in views.py
            if attr == "architecture":
                arch = value
                tokenmap["ARCH"] = value
            elif attr in ["devicemodel", "devicevariant", "brand"]:
                tokenmap[attr.upper()] = value
            elif attr == "kickstarttype":
                kstype = value
            elif attr == "imagetype":
                imgtype = value
            elif attr == "features":
                # The feature data is extracted from the *.feature by
                # ConfigParser files and defines extra packages and
                # repositories. The headers provide a csv list of
                # feature names
                f_csv = value
                for ft in f_csv.split(","):
                    ft = ft.strip()
                    print("Handling feature %s" % ft)
                    if ft != "":
                        feat = expand_feature(ft)
                        repos, pkgs = get_repos_packages_for_feature(feat, kstype)
                        extra_repos.update(repos)
                        extra_packages.update(pkgs)
            else:
                # "displayname", "brand"
                # i.__setattr__(attr, value)
                print("Not handling header '%s=%s'" % (attr, value))
        print("extra_repos pre substitutions %s" % extra_repos)

        # Magic RNDPATTERN/RELEASEPATTERN
        if "RNDFLAVOUR" in tokenmap:
            v = tokenmap["RNDFLAVOUR"]
            if v == "devel":
                tokenmap["RNDPATTERN"] = ""
            else:
                tokenmap["RNDPATTERN"] = ":/%s" % v
        if "RELEASE" in tokenmap:
            v = tokenmap["RELEASE"]
            if v == "":
                tokenmap["RELEASEPATTERN"] = ""
            else:
                tokenmap["RELEASEPATTERN"] = ":/%s" % v

        # Handle tokens appearing in the ksname and extra_repos
        tokens_list = []
        extra_repos_tmp = []
        for token, tokenvalue in tokenmap.items():
            ksname = ksname.replace("@%s@" % token, tokenvalue)
            tokens_list.append("%s:%s" % (token, tokenvalue))
            for repo in extra_repos:
                extra_repos_tmp.append(repo.replace("@%s@" % token, tokenvalue))
            extra_repos = extra_repos_tmp[:]
            extra_repos_tmp = []

        print("extra_repos %s" % extra_repos)
        print("extra_packages %s" % extra_packages)
        print("tokens_list %s" % tokens_list)
        # Create an Imager job using the values we just created
        imgjob = ImageJob()
        imgjob.kickstart = ks
        imgjob.name = ksname
        imgjob.arch = arch
        imgjob.tokenmap = ",".join(tokens_list)
        imgjob.image_type = imgtype
        imgjob.user = User.objects.get(username=user)
        imgjob.extra_repos = ",".join(extra_repos)
        imgjob.overlay = ",".join(extra_packages)
        imgjob.queue = Queue.objects.get(name="requests")
        imgjob.pp_args = ""
        # imgjob.pp_args = json.dumps(post_processes_args)
        print("About to save")
        # Yes, this is how it is...
        saved = False
        while not saved:
            try:
                imgjob.image_id = "%s-%s" % ("releasing",
                                             time.strftime('%Y%m%d-%H%M%S'))
                imgjob.save()
                saved = True
            except IntegrityError, exc:
                print exc
                print "couldn't save %s, retrying" % imgjob.image_id
                time.sleep(1)


        new_fields = imgjob.to_fields()

        merge(f.as_dict(), new_fields)
        print("Fields")
        print(json.dumps(f.as_dict(), sort_keys=True, indent=4))

        msg = "Image %s build for arch %s" % (f.image.name, f.image.arch)

        if f.image.result:
            msg = "%s succeeded \nfiles: %s \nimage: %s \nlog %s" % (
                msg, f.image.files_url, f.image.image_url, f.image.logfile_url)
        else:
            msg = "%s failed \nlog %s\nerror %s" % (
                msg, f.image.image_log, f.image.error)
            f.__error__ = 'Image build FAILED: %s' % f.image.error
            f.msg.append(f.__error__)

        f.msg.append(msg)

        wid.result = True

        # --tokenmap=DEVICEVARIANT:tbj,RNDFLAVOUR:devel,DEVICEMODEL:tbj,RELEASE:4.2.0.13,RNDRELEASE:latest,EXTRA_NAME:,ARCH:i486
        # --tokenmap=DEVICEVARIANT:tbj,RNDFLAVOUR:devel,DEVICEMODEL:tbj,RELEASE:4.2.0.13,RNDRELEASE:latest,EXTRA_NAME:,ARCH:i486,RELEASEPATTERN::/4.2.0.13,RNDPATTERN::/devel

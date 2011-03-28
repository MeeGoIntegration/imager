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
#~ along with this program.  If not, see <http://www.gnu.org/licenforms.pyses/>.

""" Image job creation forms """

import os
from django import forms
from django.forms.formsets import formset_factory
from img_web import settings

EXTRA_OBSES = (
    ('None', 'None'),
    ('http://download.meego.com/live/', 'Meego'),
    ('http://repo.pub.meego.com/', 'Community Meego'),
    ('http://download.opensuse.org/repositories/', 'Suse'),
)


class extraReposForm(forms.Form):
    """ Django form that can be used multiple times in the UploadFileForm """

    obs = forms.ChoiceField(label="OBS", choices=EXTRA_OBSES,
                            help_text="Extra OBS instances from which packages \
                                       may be downloaded from.")
    repo = forms.CharField(label = "Repository", required=False, max_length=500,
                           help_text = "Repositories in which the packages \
                           live. For example: Core:Devel:Kernel/standard")

extraReposFormset = formset_factory(extraReposForm)

class UploadFileForm(forms.Form):
    """ Django form that allows users to create image jobs """

    def __init__(self, *args, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)
        self.fields['template'].choices = [('None', 'None')]
        templates_dir = settings.TEMPLATESDIR
        templates = os.listdir(templates_dir)
        for template in templates:
            self.fields['template'].choices.append((template , template))
         
    email = forms.EmailField(label='Email', required=True, help_text="Email: \
            Your email to send a notification when the image building is done.")
    if settings.USE_BOSS:
        notify = forms.BooleanField(label="Notify me", required=False,
                                    help_text="Notify me: Send email when image\
                                               is done.")
        test_image = forms.BooleanField(label="Test image", required=False,
                                help_text="Test image: Send image for testing.")
        devicegroup = forms.CharField(label="Device group", required=False,
                                help_text="Device group: OTS device group to \
                                use for test run.",
                                initial='devicegroup:mygroup')
    release = forms.CharField(label="Release", required=False,
                                help_text="Release: Optional, if used your \
                                kickstart file has to follow the naming \
                                convention $VERTICAL-$ARCH-$VARIANT, \
                                otherwise mic2 will reject it.")
    imagetype = forms.ChoiceField(label='Image type',
                                  choices=[
                                              ('fs', 'RootFS'),
                                              ('livecd',"Live CD"),
                                              ('liveusb', "Live USB"),
                                              ('loop', "Loop file"),
                                              ('raw',"Raw disk image"),
                                              ('nand',"NAND"),
                                              ('mrstnand',"MRST NAND"),
                                              ('vdi',"VDI file"),
                                              ('vmdk',"VMDK file"),
                                          ],
                                  help_text='Type: format of image you want to \
                                             produce.')
    architecture = forms.ChoiceField(label='Architecture',
                                     choices=[
                                                ('i586', "i586"),
                                                ('i686', "i686"),
                                                ('armv7l',"armv7l"),
                                                ('armv7hl','armv7hl'),
                                                ('armv7nhl','armv7nhl'),
                                             ],
                                     help_text="Target architecture of the \
                                                image you want to build from \
                                                your customized kickstart.")
    ksfile = forms.FileField(label="Kickstart file", required=False,
                             help_text="Kickstart: customized kickstart file, \
                                        if the templates don't fit your needs.")
    template = forms.ChoiceField(label='Template',
                                 choices=[
                                            ('None','None')
                                         ],
                                 help_text="Template: Choose a base template \
                                            ontop of which your packages will \
                                            be added. Each template is targeted\
                                            at a certain device and \
                                            architecture so the architecture \
                                            and kickstart fields will be \
                                            ignored.")
    overlay = forms.CharField(label="Packages", required=False,
                              widget=forms.Textarea(attrs={'rows':'4'}),
                                                    help_text='Packages: comma \
                              separated list of packages you want to include \
                              in the image built from the chosen template. \
                              A packagename prefixed wtith "-" is excluded. \
                              Package groups are denoted by "@" prefix.')



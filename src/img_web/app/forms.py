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

import os
from django import forms
from img_web import settings

import yaml
class UploadFileForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(UploadFileForm,self).__init__(*args, **kwargs)
        self.fields['template'].choices = [('None', 'None')]
        templates_dir = settings.TEMPLATESDIR
        templates = os.listdir(templates_dir)
        for template in templates:
            self.fields['template'].choices.append((template , template))
         
    email = forms.EmailField(label='Email', required=True, help_text="Email: Your email to send a notification when the image building is done.")
    if settings.USE_BOSS:
      notify = forms.BooleanField(label="Notify me", required=False, help_text="Notify me: Send email when image is done.")
    release = forms.CharField(label="Release", required=False, help_text="Release: Optional, if used your kickstart file has to follow the naming convention $VERTICAL-$ARCH-$VARIANT, otherwise mic2 will reject it.")
    imagetype = forms.ChoiceField(label='Image type', choices=[('livecd',"livecd"), ('liveusb', "liveusb"), ('loop', "loop"), ('raw',"raw"), ('nand',"nand"), ('mrstnand',"mrstnand"), ('vdi',"vdi"), ('vmdk',"vmdk"), ('fiasco', 'fiasco')], help_text='Type: format of image you want to produce.')
    ksfile = forms.FileField(label="Kickstart file", required=False, help_text="Kickstart: customized kickstart file, if the above templates don't fit your needs.")
    architecture = forms.ChoiceField(label='Architecture', choices=[('i686', "i686"), ('armv7l',"armv7l")], help_text="Target architecture of the image you want to build from your customized kickstart.")
    template = forms.ChoiceField(label='Template', choices=[('None','None')], help_text="Template: Choose a base template ontop of which your packages will be added. Each template is targeted at a certain device and architecture so the architecture and kickstart fields will be ignored.")
    overlay = forms.CharField(label="Packages", required=False, widget=forms.Textarea(attrs={'rows':'4'}), help_text='Packages: comma separated list of packages you want to include in the image built from the chosen template. A packagename prefixed wtith "-" is excluded. Package groups are denoted by "@" prefix.')
    projects = forms.CharField(label="Projects", required=False, widget=forms.Textarea(attrs={'rows':'4'}), help_text='Projects: comma separated list of OBS project repos you want to include in the chosen template in the form project/repository. For example: home:bob/standard')
    if settings.USE_BOSS:
      test_image = forms.BooleanField(label="Test image", required=False, help_text="Test_image: Send image for testing.")

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

from django import forms
import yaml
class UploadFileForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(UploadFileForm,self).__init__(*args, **kwargs)
        defconfig = file('/usr/share/img/kickstarter/configurations.yaml', 'r')
        config = yaml.load(defconfig) 
        platforms = []
        for idx, plat in enumerate(config["Configurations"]):
            platform = plat["Platform"]            
            platforms.append((platform, platform))
        self.fields['platform'].choices = (tuple(platforms))        
        
    
    email = forms.EmailField(label='Email:')
    name = forms.CharField(label="Name:", required=True, help_text="Image name")
    release = forms.CharField(label="Release:", required=True, help_text="Release")
    overlay = forms.CharField(label="Overlay:", required=False, help_text='Kickstarter package overlay (comma separated list of packages)')
    platform = forms.ChoiceField(required=False, choices=[('0', 'YEAH')])
    imagetype = forms.ChoiceField(label='Image type:', choices=[('livecd',"livecd"), ('liveusb', "liveusb"), ('loop', "loop"), ('raw',"raw"), ('nand',"nand"), ('mrstnand',"mrstnand"), ('vdi',"vdi"), ('vmdk',"vmdk"), ('fiasco', 'fiasco')])
    ksfile = forms.FileField(label="Kickstart file (not in yaml)", required=False)
    

        

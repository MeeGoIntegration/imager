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

import os,re
from django import forms
from django.forms.formsets import formset_factory
from django.core.validators import validate_email
from taggit.forms import TagField
from img_web import settings
from img_web.app.models import ImageType, Arch, BuildService, Token

class extraReposForm(forms.Form):
    """ Django form that can be used multiple times in the UploadFileForm """
    obs = forms.ChoiceField(label="OBS", choices=[("None", "None")],
                            help_text="Extra OBS instances from which packages"\
                                      " may be downloaded from.")
    repo = forms.CharField(label = "Repository", required=False, max_length=500,
                           help_text = "Repositories in which the packages "\
                           "live. For example: Core:Devel:Kernel/standard")

    def __init__(self, *args, **kwargs):
        super(extraReposForm, self).__init__(*args, **kwargs)
        self.fields['obs'].choices = [(obs.apiurl , obs.name) for obs in BuildService.objects.all()]

    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data['obs'] == "None":
            cleaned_data['obs'] = None

        if cleaned_data['repo'] == "":
            cleaned_data['repo'] = None

        if cleaned_data['obs'] and not cleaned_data['repo']:
            raise forms.ValidationError("You chose an extra OBS without "\
                                        "adding a corresponding repository.")
        return cleaned_data

extraReposFormset = formset_factory(extraReposForm)

class extraTokensForm(forms.Form):
    """ Django form that can be used multiple times in the UploadFileForm """

    def __init__(self, *args, **kwargs):
        super(extraTokensForm, self).__init__(*args, **kwargs)
        for token in Token.objects.all():
            self.fields[token.name] = forms.CharField(label=token.name, initial=token.default)

    def clean(self):
        data = []
        for token in Token.objects.all():
            if token.name in self.cleaned_data:
                data.append("%s:%s" % ( token.name, cleaned_data[token.name] ))

        return ",".join(data)

extraTokensFormset = formset_factory(extraTokensForm)

class UploadFileForm(forms.Form):
    """ Django form that allows users to create image jobs """
    imagetype = forms.ChoiceField(label='Image type',
                                  choices=[],
                                  help_text="Type: format of image you want to"\
                                            " produce.")

    architecture = forms.ChoiceField(label='Architecture',
                                     choices=[],
                                     help_text="Target architecture of the "\
                                               "image you want to build from "\
                                               "your customized kickstart.")
    ksfile = forms.FileField(label="Kickstart file", required=False,
                             help_text="Kickstart: customized kickstart file, "\
                                       "if the templates don't fit your needs.")

    template = forms.ChoiceField(label='Template',
                                 choices=[("None", "None")],
                                help_text="Template: Choose a base template "\
                                          "ontop of which your packages will "\
                                          "be added. Each template is targeted"\
                                          " at a certain device and "\
                                          "architecture so the architecture "\
                                          "and kickstart fields will be "\
                                          "ignored.")

    if settings.notify_enabled:
        notify_image = forms.BooleanField(label="Notify", required=False,
                                          initial=True,
                            help_text="Notify image: Send notification when "\
                                      "image building process is done. ")
        email = forms.CharField(label="Emails", required=False,
                                 widget=forms.Textarea(attrs={'rows':'2'}),
                                 help_text="Emails: Comma separated list of "\
                                           "emails to send a notification to "\
                                           "when the image building is done.")

    if settings.testing_enabled:
        test_image = forms.BooleanField(label="Test image", required=False,
                                        initial=False,
                            help_text="Test image: Send image for testing. ")
        devicegroup = forms.CharField(label="Device group", required=False,
                                help_text="Device group: device group to "\
                                "use for test run.",
                                initial='')

        test_options = forms.CharField(label="Test options", required=False,
                              widget=forms.Textarea(attrs={'rows':'2'}),
                                                    help_text=\
                              "Test options: comma separated list of test "\
                              "options you want to send to the testing server.")

    overlay = forms.CharField(label="Packages", required=False,
                              widget=forms.Textarea(attrs={'rows':'4'}),
                                                    help_text=\
                              "Packages: comma separated list of packages you "\
                              "want to include in the image built from the "\
                              "chosen template. A packagename prefixed wtit "\
                              '"-" is excluded. Package groups are denoted by '\
                              '"@" prefix.')
    pinned = forms.BooleanField(label="Pin image", required=False,
                                initial=False,
                            help_text="Pin image so it doesn't expire or get "\
                                      "deleted by mistake. ")
    tags = forms.CharField(label="Free Tags", required=False,
                           widget=forms.Textarea(attrs={'rows':'2'}),
                                                 help_text=\
                              "Packages: comma separated list of tags "\
                              "to describe the image built.")


    def __init__(self, *args, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)
        self.fields['template'].choices=[("None", "None")]
        for template in os.listdir(settings.TEMPLATESDIR):
            name = template
            with open("%s/%s" % (settings.TEMPLATESDIR, template)) as tf:
                for line in tf:
                    if re.match(r'^#DisplayName:.+$', line):
                        name = line.split(":")[1].strip()
                        break
            self.fields['template'].choices.append((template , name))
        self.fields['architecture'].choices = [(arch.name, arch.name) for arch in Arch.objects.all()]
        self.fields['imagetype'].choices = [(itype.name, itype.name) for itype in ImageType.objects.all()]

    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data['template'] == "None":
            cleaned_data['template'] = None

        if 'email' in cleaned_data.keys():
            if cleaned_data['email'].endswith(','):
                cleaned_data['email'] = cleaned_data['email'][:-1]
                for email in [i.strip() for i in \
                        cleaned_data['email'].split(",")]:
                    validate_email(email)

        if (('ksfile' in cleaned_data and 'template' in cleaned_data) and
            (cleaned_data['ksfile'] and cleaned_data['template'])):
            raise forms.ValidationError("Please choose template or upload"\
                                            " a kickstart, not both!")
        elif (('ksfile' not in cleaned_data and 'template' not in cleaned_data) and
              (cleaned_data['ksfile'] and cleaned_data['template'])):
            raise forms.ValidationError("Please choose either a template or"\
                                            "upload a kickstart file.")
        return cleaned_data

class TagForm(forms.Form):
    tags = TagField()

class SearchForm(forms.Form):
    searchterm = forms.CharField(label="Search term", required=True,
                                 help_text="partial or full tag name to search with")


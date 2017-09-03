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

import os,re, glob
from itertools import chain
from collections import defaultdict
import ConfigParser
from django import forms
from django.forms.formsets import BaseFormSet, formset_factory
from django.core.validators import validate_email
from taggit.forms import TagField
from img_web import settings
from img_web.app.models import ImageType, Arch, BuildService, Token, PostProcess
from django.utils.encoding import StrAndUnicode, force_unicode, smart_unicode, smart_str

from django.utils.html import escape, conditional_escape

def get_features():
    config = ConfigParser.ConfigParser()
    for feature in glob.glob(os.path.join(settings.FEATURESDIR, '*.feature')):
        config.read(feature)
    return config

def list_features():
    features = get_features()
    choices = set()
    for name in features.sections():
        if name.startswith("repositories"):
            continue
        description = name
        if features.has_option(name, "description"):
            description = features.get(name, "description")
        choices.add((name, description))
    return choices

def expand_feature(name):
    features = get_features()
    repo_sections = [ section for section in features.sections() if section.startswith("repositories") ]
    feat = defaultdict(set)

    if features.has_option(name, "pattern"):
        feat["pattern"].add("@%s" % features.get(name, "pattern"))

    if features.has_option(name, "packages"):
        feat["packages"].update(features.get(name, "packages").split(','))

    if features.has_option(name, "repos"):
        for repo in features.get(name, "repos").split(","):
            for section in repo_sections:
                if features.has_option(section, repo):
                    feat[section].add(features.get(section, repo))
    return dict(feat)

class extraReposForm(forms.Form):

    obs = forms.ChoiceField(label="OBS", choices=[("None", "None")],
                            help_text="Extra OBS instances from which packages"\
                                      " may be downloaded from.")
    project = forms.CharField(label = "Project", required=False, max_length=500,
                              help_text = "Project name in which the repository "\
                              "lives. For example: home:user")
    repo = forms.CharField(label = "Repository", required=False, max_length=500,
                           help_text = "Repository name in which the packages "\
                           "live. For example: latest_i486")

    def __init__(self, *args, **kwargs):
        super(extraReposForm, self).__init__(*args, **kwargs)
        self.fields['obs'].choices = [("None", "None")] + [(obs.apiurl , obs.name) for obs in BuildService.objects.all()]

    def clean(self):
        cleaned_data = self.cleaned_data
        if not 'obs' in cleaned_data or cleaned_data['obs'] == "None":
            cleaned_data['obs'] = None

        if not 'repo' in cleaned_data or cleaned_data['repo'] == "":
            cleaned_data['repo'] = None
        else:
            cleaned_data['repo'] = cleaned_data['repo'].strip()

        if not 'project' in cleaned_data:
            cleaned_data['project'] = ""
        else:
            cleaned_data['project'] = cleaned_data['project'].strip()

        if cleaned_data['obs'] and not cleaned_data['repo']:
            raise forms.ValidationError("You chose an extra OBS without "\
                                        "adding a corresponding repository.")
        return cleaned_data

extraReposFormset = formset_factory(extraReposForm)

class extraTokensForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(extraTokensForm, self).__init__(*args, **kwargs)
        for token in Token.objects.all():
            self.fields[token.name] = forms.CharField(label=token.name, initial=token.default, required=False, help_text=token.description)

extraTokensFormset = formset_factory(extraTokensForm)

class PostProcessForm(forms.Form):

    def __init__(self, *args, **kwargs):
        pp = kwargs["pp"]
        del(kwargs["pp"])
        super(PostProcessForm, self).__init__(*args, **kwargs)
        self.fields[pp.name] = forms.BooleanField(label=pp.name, initial=pp.default, required=False, help_text=pp.description)
        if pp.argname:
            self.fields[pp.argname] = forms.CharField(label=pp.argname, required=False, widget=forms.Textarea(attrs={'rows':'1'}), help_text=pp.description)


class BasePostProcessFormset(BaseFormSet):

    def _construct_forms(self):
        # instantiate all the forms and put them in self.forms
        self.forms = []
        ppobjs = PostProcess.objects.filter(active=True)
        print self.total_form_count()
        count = 0
        for i in xrange(self.total_form_count()):
	    if count >= ppobjs.count():
                break
            self.forms.append(self._construct_form(i, pp=ppobjs[count]))
            count = count + 1

# This has to be done in the view to get new count
#postProcessFormset = formset_factory(PostProcessForm, formset=BasePostProcessFormset, extra=PostProcess.objects.count())

class OptionAttrChoiceField(forms.ChoiceField):

    def valid_value(self, value):
        "Check to see if the provided value is a valid choice"
        for choice in self.choices:
            k = choice[0]
            v = choice[1]
            if isinstance(v, (list, tuple)):
                # This is an optgroup, so look inside the group for options
                for k2, v2 in v:
                    if value == smart_unicode(k2):
                        return True
            else:
                if value == smart_unicode(k):
                    return True
        return False


class OptionAttrSelect(forms.Select):

    def render_option(self, selected_choices, option_value, option_label, option_attrs=None):
        option_value = force_unicode(option_value)
        if option_value in selected_choices:
            selected_html = u' selected="selected"'
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''

        attrs = []
        if option_attrs:
            for key, val in option_attrs.items():
                attrs.append('%s="%s"' % (key, val))

        return u'<option value="%s"%s%s>%s</option>' % (
            escape(option_value), selected_html, " ".join(attrs),
            conditional_escape(force_unicode(option_label)))


    def render_options(self, choices, selected_choices):
        # Normalize to strings.
        selected_choices = set(force_unicode(v) for v in selected_choices)
        output = []
        for option_iterable in chain(self.choices, choices):
            option_value = option_iterable[0]
            option_label = option_iterable[1]
            if isinstance(option_label, (list, tuple)):
                output.append(u'<optgroup label="%s">' % escape(force_unicode(option_value)))
                for option in option_label:
                    output.append(self.render_option(selected_choices, *option))
                output.append(u'</optgroup>')
            else:
                option_attrs = None
                if len(option_iterable) > 2:
                    option_attrs = option_iterable[2]
                output.append(self.render_option(selected_choices, option_value, option_label, option_attrs=option_attrs))
        return u'\n'.join(output)



class ImageJobForm(forms.Form):
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

    template = OptionAttrChoiceField(label='Template',
                                 choices=[("None", "None")],
                                 widget=OptionAttrSelect,
                                help_text="Template: Choose a base template "\
                                          "ontop of which your packages will "\
                                          "be added. Each template is targeted"\
                                          " at a certain device and "\
                                          "architecture so the architecture "\
                                          "and kickstart fields will be "\
                                          "ignored.")


    features = forms.TypedMultipleChoiceField(label="Features", choices=[],
                            help_text="Features: Commonly used extra features", empty_value={},
                            coerce=expand_feature, required = False,
                            widget=forms.widgets.CheckboxSelectMultiple)

    overlay = forms.CharField(label="Packages", required=False,
                              widget=forms.Textarea(attrs={'rows':'1'}),
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
    tags = forms.CharField(label="Tags", required=False,
                           widget=forms.Textarea(attrs={'rows':'1'}),
                                                 help_text=\
                              "Packages: comma separated list of tags "\
                              "to describe the image built.")
    device = forms.CharField(
        label="Device",
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
    )

    def __init__(self, *args, **kwargs):
        super(ImageJobForm, self).__init__(*args, **kwargs)
        self.fields['template'].choices = []
        for template in glob.glob(os.path.join(settings.TEMPLATESDIR, '*.ks')):
            name = os.path.basename(template)
            templatename = os.path.basename(template)
            attrs = {}
            with open(template, 'r') as tf:
                for line in tf:
                    match = re.match(r'^#.*?Suggested([^:]*):(.*)$', line)
                    if match:
                        key = 'data-' + match.group(1).lower()
                        val = match.group(2).strip()
                        attrs[key] = val
                    elif re.match(r'^#.*?DisplayName:.+$', line):
                        name = line.split(":")[1].strip()
                    elif re.match(r'^#.*?Device:.+$', line):
                        attrs['data-device'] = line.split(":")[1].strip()

            self.fields['template'].choices.append((templatename , name, attrs))

        self.fields['template'].choices = sorted(self.fields['template'].choices, key=lambda name: name[1])
        self.fields['template'].choices.insert(0, ("None", "None"))
        self.fields['architecture'].choices = [(arch.name, arch.name) for arch in Arch.objects.all()]
        self.fields['imagetype'].choices = [(itype.name, itype.name) for itype in ImageType.objects.all()]
        self.fields['features'].choices = list_features()

    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data['template'] == "None":
            cleaned_data['template'] = None

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


# Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
# Contact: Ramez Hanna <ramez.hanna@nokia.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenforms.pyses/>.

""" Image job creation forms """

import os
import re
import glob
from itertools import chain
from collections import defaultdict
import configparser
from django import forms
from django.forms.formsets import BaseFormSet, formset_factory
from django.core.validators import validate_email
from taggit.forms import TagField
from img_web import settings
from img_web.app.models import ImageType, Arch, BuildService, Token, PostProcess
from img_web.app.features import list_features, expand_feature
from django.utils.encoding import force_unicode, smart_unicode, smart_str

from django.utils.html import escape, conditional_escape


class extraReposForm(forms.Form):

    obs = forms.ChoiceField(label="OBS", choices=[("None", "None")],
                            help_text="Extra OBS instances from which "
                            "packages may be downloaded from.")
    project = forms.CharField(label="Project", required=False,
                              max_length=500,
                              help_text="Project name in which"
                              " the repository lives. For example: home:user")
    repo = forms.CharField(label="Repository", required=False,
                           max_length=500, help_text="Repository "
                           "name in which the packages live. For "
                           "example: latest_i486")

    def __init__(self, *args, **kwargs):
        super(extraReposForm, self).__init__(*args, **kwargs)
        self.fields['obs'].choices = [("None", "None")] + \
            [(obs.apiurl, obs.name) for obs in BuildService.objects.all()]

    def clean(self):
        cleaned_data = self.cleaned_data
        if 'obs' not in cleaned_data or cleaned_data['obs'] == "None":
            cleaned_data['obs'] = None

        if 'repo' not in cleaned_data or cleaned_data['repo'] == "":
            cleaned_data['repo'] = None
        else:
            cleaned_data['repo'] = cleaned_data['repo'].strip()

        if 'project' not in cleaned_data:
            cleaned_data['project'] = ""
        else:
            cleaned_data['project'] = cleaned_data['project'].strip()

        if cleaned_data['obs'] and not cleaned_data['repo']:
            raise forms.ValidationError("You chose an extra OBS without "
                                        "adding a corresponding repository.")
        return cleaned_data


extraReposFormset = formset_factory(extraReposForm)


class extraTokensForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(extraTokensForm, self).__init__(*args, **kwargs)
        for token in Token.objects.all():
            self.fields[token.name] = \
                forms.CharField(label=token.name,
                                initial=token.default,
                                required=False,
                                help_text=token.description)


extraTokensFormset = formset_factory(extraTokensForm)


class PostProcessForm(forms.Form):

    def __init__(self, *args, **kwargs):
        pp = None
        if "pp" in kwargs:
            pp = kwargs["pp"]
            del(kwargs["pp"])
        super(PostProcessForm, self).__init__(*args, **kwargs)
        if pp:
            self.fields[pp.name] = \
                forms.BooleanField(label=pp.name, initial=pp.default,
                                   required=False, help_text=pp.description)
            if pp.argname:
                self.fields[pp.argname] = \
                    forms.CharField(label=pp.argname, required=False,
                                    widget=forms.Textarea(attrs={'rows': '1'}),
                                    help_text=pp.description)


class BasePostProcessFormset(BaseFormSet):

    # The BaseFormSet method ignores index. I think it's broken This
    # assumes form_kwargs is a list with a dict of kwargs per
    # form. Which I think makes sense.
    def get_form_kwargs(self, index):
        try:
            return self.form_kwargs[index]
        except LookupError:
            return {}


# In the ImageJobForm, when a template is selected from the dropdown
# the features associated with that template are automatically ticked;
# essentially providing a set of default features per template.  This
# is done by reading and parsing each of the ks files in the Form and
# passing the feature data to the dropdown by setting the value of
# each 'features' ChoiceField choices element to be a tuple instead of
# a simple value. The create_option method 'decodes' this to the plain
# value and attrs so the builtin template renders them correctly as
# data- attrs. Returned data is also validated against just the plain
# value. JavaScript in the upload.html template then sets these values
# using the per-option data- attributes
class OptionAttrChoiceField(forms.ChoiceField):

    def valid_value(self, value):
        "Check to see if the provided value is a valid choice"
        for choice in self.choices:
            k = choice[0]
            if isinstance(k, (list, tuple)):  # This needs decoding
                k = k[0]  # so pick the 'value' and discard attrs
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
    # This is the mainly standard method called per-option to be
    # passed to the template value can now be a value or a tuple/list
    # of (value, dict_of_attrs)
    def create_option(self, name, value, label, selected, index,
                      subindex=None, attrs=None):
        index = str(index) if subindex is None else "%s_%s" % (index, subindex)
        if attrs is None:
            attrs = {}
        option_attrs = (self.build_attrs(self.attrs, attrs)
                        if self.option_inherits_attrs else {})
        # Begin modification
        # If the value we were passed is a tuple/list then split it
        # into a value and an attrs dict
        if isinstance(value, (list, tuple)):
            option_attrs.update(value[1])  # add to any existing attrs
            value = value[0]
        # End modification
        if selected:
            option_attrs.update(self.checked_attribute)
        if 'id' in option_attrs:
            option_attrs['id'] = self.id_for_label(option_attrs['id'], index)
        return {
            'name': name,
            'value': value,
            'label': label,
            'selected': selected,
            'index': index,
            'attrs': option_attrs,
            'type': self.input_type,
            'template_name': self.option_template_name,
        }


class ImageJobForm(forms.Form):
    """ Django form that allows users to create image jobs """
    imagetype = forms.ChoiceField(
        label='Image type',
        choices=[],
        help_text="Type: format of image you want to produce.")

    architecture = forms.ChoiceField(
        label='Architecture',
        choices=[],
        help_text="Target architecture of the image you want to build from "
        "your customized kickstart.")

    ksfile = forms.FileField(
        label="Kickstart file", required=False,
        help_text="Kickstart: customized kickstart file, "
        "if the templates don't fit your needs.")

    template = OptionAttrChoiceField(
        label='Template',
        choices=[("None", "None")],
        widget=OptionAttrSelect,
        help_text="Template: Choose a base template ontop of which your "
        "packages will be added. Each template is targeted at a certain "
        "device and architecture so the architecture and kickstart "
        "fields will be ignored.")

    features = forms.TypedMultipleChoiceField(
        label="Features", choices=[],
        help_text="Features: Commonly used extra features",
        empty_value={},
        coerce=expand_feature, required=False,
        widget=forms.widgets.CheckboxSelectMultiple)

    overlay = forms.CharField(
        label="Packages", required=False,
        widget=forms.Textarea(attrs={'rows': '1'}),
        help_text="Packages: comma separated list of packages you want to "
        "include in the image built from the chosen template. A packagename "
        "prefixed with '-' are excluded. Package groups are denoted by "
        "'@' prefix.")

    pinned = forms.BooleanField(
        label="Pin image", required=False,
        initial=False,
        help_text="Pin image so it doesn't expire or get deleted by mistake.")

    tags = forms.CharField(
        label="Tags", required=False,
        widget=forms.Textarea(attrs={'rows': '1'}),
        help_text="Packages: comma separated list of tags to describe the "
        "image built.")

    devicemodel = forms.CharField(
        label="Device model",
        required=False,
        widget=forms.HiddenInput(attrs={'readonly': 'readonly'}))

    devicevariant = forms.CharField(
        label="Device variant",
        required=False,
        widget=forms.HiddenInput(attrs={'readonly': 'readonly'}))

    brand = forms.CharField(
        label="Brand",
        required=False,
        widget=forms.HiddenInput(attrs={'readonly': 'readonly'}))

    def __init__(self, *args, **kwargs):
        super(ImageJobForm, self).__init__(*args, **kwargs)
        choices = []
        suggested_re = re.compile(
            r'^#.*?Suggested(Architecture|ImageType|Features):(.*)$'
        )
        device_re = re.compile(
            r'^#.*?(DeviceModel|DeviceVariant|Brand):(.*)$'
        )

        # find the available ks files and extract the feature
        # defaults from each file
        # See the comment by OptionAttrChoiceField
        for template in glob.glob(os.path.join(settings.TEMPLATESDIR,
                                               '*.ks')):
            name = os.path.basename(template)
            templatename = os.path.basename(template)
            attrs = {}
            with open(template, 'r') as tf:
                for line in tf:
                    match = suggested_re.match(line) or device_re.match(line)
                    if match:
                        key = 'data-' + match.group(1).lower()
                        val = match.group(2).strip()
                        attrs[key] = val
                    elif re.match(r'^#.*?DisplayName:.+$', line):
                        name = line.split(":")[1].strip()

            # Now pass the features as a tuple for our custom widget
            # to unpack into attrs
            choices.append(((templatename, attrs), name))

        self.fields['template'].choices = sorted(choices, key=lambda
                                                 name: name[1])
        self.fields['template'].choices.insert(0, ("None", "None"))
        self.fields['architecture'].choices = [
            (arch.name, arch.name) for arch in Arch.objects.all()]
        self.fields['imagetype'].choices = [
            (itype.name, itype.name) for itype in ImageType.objects.all()]
        self.fields['features'].choices = list_features()

    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data['template'] == "None":
            cleaned_data['template'] = None

        if (('ksfile' in cleaned_data and 'template' in cleaned_data)
            and
            (cleaned_data['ksfile'] and cleaned_data['template'])):
            raise forms.ValidationError("Please choose template or upload"
                                        " a kickstart, not both!")
        elif (('ksfile' not in cleaned_data and 'template' not in cleaned_data)
              and
              (cleaned_data['ksfile'] and cleaned_data['template'])):
            raise forms.ValidationError("Please choose either a template or"
                                        "upload a kickstart file.")
        return cleaned_data


class TagForm(forms.Form):
    tags = TagField()


class SearchForm(forms.Form):
    searchterm = forms.CharField(
        label="Search term", required=True,
        help_text="partial or full tag name to search with")

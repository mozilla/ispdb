# -*- coding: utf-8 -*-

import re
from django.core.urlresolvers import reverse
from django.forms import (ChoiceField, BooleanField, HiddenInput, ModelForm,
    RadioSelect, ValidationError)
from django.forms.models import BaseModelFormSet
from django.forms.models import modelformset_factory
from django.utils.safestring import mark_safe
from django.utils.translation import get_language_info
from django.utils.functional import curry
from django.utils.translation.trans_real import parse_accept_lang_header

from ispdb.config.models import (Config, Domain, DomainRequest, DocURL,
    DocURLDesc, EnableURL, EnableURLInst, Issue)


def clean_port(self,field):
    data = self.cleaned_data[field]
    if data > 65535:
        raise ValidationError("Port number cannot be larger than 65535")
    return data

class DynamicModelForm(ModelForm):
    """
    Class that represents a ModelForm which can work with our dynamic forms
    system
    """
    DELETE = BooleanField(required=False, initial=False, widget=HiddenInput)

    def disable_fields(self):
        for k, field in self.fields.iteritems():
            if k == "DELETE":
                continue
            field.required = False
            w = field.widget
            if (hasattr(w, 'input_type')) and (w.input_type in
                    ["text", "password"]):
                w.attrs['readonly'] = "readonly"
            else:
                w.attrs['disabled'] = "disabled"

    def __init__(self, *args, **kwargs):
        super(DynamicModelForm, self).__init__(*args, **kwargs)
        self.empty_permitted = False
        if self.data.get(self.prefix+'-DELETE', '') == "True":
            self.disable_fields()

    def clean(self, **kwargs):
        cleaned_data = super(DynamicModelForm, self).clean(**kwargs)
        # if form is deleted, clear errors
        if cleaned_data['DELETE']:
            self.errors.clear()
        return cleaned_data

    def save(self, commit=True):
        super(DynamicModelForm, self).save(commit=False)
        if commit:
            # delete if exists
            if self.cleaned_data and self.cleaned_data['DELETE']:
                if self.instance.pk:
                    return self.instance.delete()
                else:
                    return None
            super(DynamicModelForm, self).save()
        return self.instance


class DynamicBaseModelFormSet(BaseModelFormSet):
    """
    Class that represents a BaseModelFormSet which can work with our dynamic
    forms system
    """
    def __init__(self, *args, **kwargs):
        super(DynamicBaseModelFormSet, self).__init__(*args, **kwargs)
        self.can_delete = True

    def save(self, *args, **kwargs):
        for form in self.forms:
            # discard unchanged empty forms
            if (not hasattr(form, 'cleaned_data')) or (not form.cleaned_data):
                continue
            # discard deleted new forms
            if form.cleaned_data['DELETE'] and not form in self.initial_forms:
                continue
            form.save(*args, **kwargs)

    def _get_empty_form(self, **kwargs):
        defaults = {
            'auto_id': 'id_%s',
            'prefix': '{1}-{0}',
            'empty_permitted': True,
        }
        defaults.update(kwargs)
        form = self.form(**defaults)
        return form
    empty_form = property(_get_empty_form)


class IssueForm(ModelForm):
    show_form = BooleanField(required=False, initial=False, widget=HiddenInput)

    class Meta:
        model = Issue
        fields = ['title', 'description']


class LanguageDescModelForm(DynamicModelForm):
    """
    A DynamicModelForm for classes with a language and a description fields
    """
    def __init__(self, *args, **kwargs):
        http_accept_language = kwargs.pop('http_accept_language', '')
        super(LanguageDescModelForm, self).__init__(*args, **kwargs)
        self.fields['description'].widget.attrs.update({'rows': 1, 'cols': 20})
        choices = []
        # add HTTP_ACCEPTED_LANG first
        if http_accept_language:
            for code, q in parse_accept_lang_header(http_accept_language):
                try:
                    li = get_language_info(code)
                except:
                    continue
                choices.append((code, li['name'] + ' - ' + li['name_local']))
        # Redefine our choices, so we can add the translated language names and
        # sort the list by language name
        choices.append(self.fields['language'].choices[0])
        langs = self.fields['language'].choices[1:]
        langs.sort(key=lambda l: l[1].lower())
        for code, lang in langs:
            li = get_language_info(code)
            choices.append((code, lang + ' - ' + li['name_local']))
        self.fields['language'].choices = choices
        self.fields['language'].initial = choices[0]


class DocURLDescForm(LanguageDescModelForm):
    class Meta:
        model = DocURLDesc
        exclude = ['docurl']


class BaseDocURLDescFormSet(DynamicBaseModelFormSet):
    model = DocURLDesc

    def __init__(self, *args, **kwargs):
        self.docurl_delete = kwargs.pop('delete', False)
        super(BaseDocURLDescFormSet, self).__init__(*args, **kwargs)
        # if docurl is deleted, set required to false so they don't
        # need to be filled
        if self.docurl_delete:
            for form in self.forms:
                for k, field in form.fields.iteritems():
                    field.required = False

    def clean(self, **kwargs):
        super(BaseDocURLDescFormSet, self).clean(**kwargs)
        if any(self.errors):
            return
        deleted_forms = 0
        languages = []
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            if (not form.cleaned_data) or form.cleaned_data['DELETE']:
                deleted_forms += 1
                continue
            # Check for repeated languages
            if form.cleaned_data['language'] in languages:
                raise ValidationError("Duplicated language found.")
            if form.cleaned_data['language'] != "Other":
                languages.append(form.cleaned_data['language'])
        # Check if all forms are deleted
        if (not self.docurl_delete) and (self.total_form_count() == 0 or
                self.total_form_count() == deleted_forms):
            raise ValidationError("At least one description should be "
                                  "specified.")


class DocURLForm(DynamicModelForm):
    class Meta:
        model = DocURL
        fields = ['url']

    def save(self, commit=True):
        m = super(DocURLForm, self).save(commit=False)
        self.desc_formset.save(commit=False)
        if commit:
            if self.cleaned_data and self.cleaned_data['DELETE']:
                # delete docurl and docurldesc forms
                if self.instance.pk:
                    for form in self.desc_formset:
                        if form.instance.pk:
                            form.instance.delete()
                    self.instance.delete()
                return None
            m = super(DocURLForm, self).save()
            for form in self.desc_formset:
                form.instance.docurl = m
            self.desc_formset.save()
        return m

class BaseDocURLFormSet(DynamicBaseModelFormSet):
    model = DocURL

    def __init__(self, *args, **kwargs):
        kwargs['prefix'] = 'docurl'
        # get request.META to add HTTP_ACCEPT_LANGUAGE on top of languages
        # choices
        meta = kwargs.pop('meta', {})
        accept_lang = meta.get('HTTP_ACCEPT_LANGUAGE', '')
        super(BaseDocURLFormSet, self).__init__(*args, **kwargs)
        # construct description formsets
        self.DocURLDescFormSet = modelformset_factory(DocURLDesc,
                extra=self.extra, form=DocURLDescForm,
                formset=BaseDocURLDescFormSet)
        self.DocURLDescFormSet.form = staticmethod(curry(DocURLDescForm,
                http_accept_language=accept_lang))
        for index, form in enumerate(self.forms):
            prefix = 'desc_%s' % index
            data = self.data or None
            delete = False
            if self.queryset:
                queryset = DocURLDesc.objects.filter(docurl=form.instance)
            else:
                queryset = DocURLDesc.objects.none()
            # if form is deleted, delete the descriptions
            if (self.data and
                    self.data.get(form.prefix+'-DELETE', '') == "True"):
                delete = True
            form.desc_formset = self.DocURLDescFormSet(data=data,
                                                       prefix=prefix,
                                                       delete=delete,
                                                       queryset=queryset)
        # create a empty_desc_form
        if self.forms:
            self.empty_desc_form = self.forms[0].desc_formset.empty_form
        else:
            formset = self.DocURLDescFormSet()
            self.empty_desc_form = formset.empty_form

    def clean(self, **kwargs):
        super(BaseDocURLFormSet, self).clean(**kwargs)
        if any(self.errors):
            return
        urls = []
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            if (not form.cleaned_data) or form.cleaned_data['DELETE']:
                continue
            # Check for repeated urls
            if form.cleaned_data['url'] in urls:
                raise ValidationError("Duplicated URL found.")
            urls.append(form.cleaned_data['url'])

    def is_valid(self, *args, **kwargs):
        result = super(BaseDocURLFormSet, self).is_valid(*args, **kwargs)
        for form in self.forms:
            result = result and form.desc_formset.is_valid()
        return result

    def delete(self):
        for form in self.forms:
            for desc in form.desc_formset:
                desc.instance.delete()
            form.instance.delete()


class EnableURLInstForm(LanguageDescModelForm):
    class Meta:
        model = EnableURLInst
        exclude = ['enableurl']


class BaseEnableURLInstFormSet(DynamicBaseModelFormSet):
    model = EnableURLInst

    def __init__(self, *args, **kwargs):
        self.enableurl_delete = kwargs.pop('delete', False)
        super(BaseEnableURLInstFormSet, self).__init__(*args, **kwargs)
        # if enableurl is deleted, set required to false so they don't
        # need to be filled
        if self.enableurl_delete:
            for form in self.forms:
                for k, field in form.fields.iteritems():
                    field.required = False

    def clean(self, **kwargs):
        super(BaseEnableURLInstFormSet, self).clean(**kwargs)
        if any(self.errors):
            return
        deleted_forms = 0
        languages = []
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            if (not form.cleaned_data) or form.cleaned_data['DELETE']:
                deleted_forms += 1
                continue
            # Check for repeated languages
            if form.cleaned_data['language'] in languages:
                raise ValidationError("Duplicated language found.")
            if form.cleaned_data['language'] != "Other":
                languages.append(form.cleaned_data['language'])
        # Check if all forms are deleted
        if (not self.enableurl_delete) and (self.total_form_count() == 0 or
                self.total_form_count() == deleted_forms):
            raise ValidationError("At least one instruction should be "
                                  "specified.")


class EnableURLForm(DynamicModelForm):
    class Meta:
        model = EnableURL
        fields = ['url']

    def save(self, commit=True):
        m = super(EnableURLForm, self).save(commit=False)
        self.inst_formset.save(commit=False)
        if commit:
            if self.cleaned_data and self.cleaned_data['DELETE']:
                # delete enableurl and instruction forms
                if self.instance.pk:
                    for form in self.inst_formset:
                        if form.instance.pk:
                            form.instance.delete()
                    self.instance.delete()
                return None
            m = super(EnableURLForm, self).save()
            for form in self.inst_formset:
                form.instance.enableurl = m
            self.inst_formset.save()
        return m

class BaseEnableURLFormSet(DynamicBaseModelFormSet):
    model = EnableURL

    def __init__(self, *args, **kwargs):
        kwargs['prefix'] = 'enableurl'
        # get request.META to add HTTP_ACCEPT_LANGUAGE on top of languages
        # choices
        meta = kwargs.pop('meta', {})
        accept_lang = meta.get('HTTP_ACCEPT_LANGUAGE', '')
        super(BaseEnableURLFormSet, self).__init__(*args, **kwargs)
        # construct instructions formsets
        self.EnableURLInstFormSet = modelformset_factory(EnableURLInst,
                extra=self.extra, form=EnableURLInstForm,
                formset=BaseEnableURLInstFormSet)
        self.EnableURLInstFormSet.form = staticmethod(curry(EnableURLInstForm,
                http_accept_language=accept_lang))
        for index, form in enumerate(self.forms):
            prefix = 'inst_%s' % index
            data = self.data or None
            delete = False
            if self.queryset:
                qs = EnableURLInst.objects.filter(enableurl=form.instance)
            else:
                qs = EnableURLInst.objects.none()
            # if form is deleted, delete the instructions
            if (self.data and
                    self.data.get(form.prefix+'-DELETE', '') == "True"):
                delete = True
            form.inst_formset = self.EnableURLInstFormSet(data=data,
                                                          prefix=prefix,
                                                          delete=delete,
                                                          queryset=qs)
        # create a empty_desc_form
        if self.forms:
            self.empty_desc_form = self.forms[0].inst_formset.empty_form
        else:
            formset = self.EnableURLInstFormSet()
            self.empty_desc_form = formset.empty_form

    def clean(self, **kwargs):
        super(BaseEnableURLFormSet, self).clean(**kwargs)
        if any(self.errors):
            return
        urls = []
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            if (not form.cleaned_data) or form.cleaned_data['DELETE']:
                continue
            # Check for repeated urls
            if form.cleaned_data['url'] in urls:
                raise ValidationError("Duplicated URL found.")
            urls.append(form.cleaned_data['url'])

    def is_valid(self, *args, **kwargs):
        result = super(BaseEnableURLFormSet, self).is_valid(*args, **kwargs)
        for form in self.forms:
            result = result and form.inst_formset.is_valid()
        return result

    def delete(self):
        for form in self.forms:
            for inst in form.inst_formset:
                inst.instance.delete()
            form.instance.delete()


class DomainForm(DynamicModelForm):
    class Meta:
        fields = ('name',)

    def __init__(self, *args, **kwargs):
        if not self._meta.model:
            self._meta.model = DomainRequest
        super(DomainForm, self).__init__(*args, **kwargs)
        self.fields['name'].required = False

    def clean(self, *args, **kwargs):
        cleaned_data = super(DomainForm, self).clean(*args, **kwargs)
        # if it is going to be deleted, dont need to to check it
        if cleaned_data["DELETE"]:
            return cleaned_data
        if not cleaned_data.has_key('name'):
            return cleaned_data
        data = cleaned_data["name"]
        # check if domain name is valid
        regex = re.compile(r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"
                            "(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)",
                           re.IGNORECASE)
        if not regex.match(data):
            # Trivial case failed. Try for possible IDN domain
            msg = ("Domain name is not valid")
            try:
                if not regex.match(data.encode('idna')): # IDN -> ACE
                    raise ValidationError(msg)
            except UnicodeError: # invalid domain
                raise ValidationError(msg)
        return cleaned_data

    def validate_unique(self):
        if not (hasattr(self.instance, 'config') and
                self.instance.config and
                self.instance.config.status == 'suggested'):
            dom = Domain.objects.filter(name=self.instance.name,
                                        config__status='approved')
            if dom and (not self.initial.has_key('name') or (dom[0].name !=
                    self.initial['name'])):
                msg = (u"Domain configuration already exists "
                       "<a href=\"%s\">here</a>." %
                       reverse("ispdb_details", args=[dom[0].config.id]))
                self._update_errors({'name': [mark_safe(msg)]})

    def save(self, commit=True):
        super(DomainForm, self).save(commit=False)
        # search for existing instances
        if not self.instance.pk:
            # if it is a DomainRequest, we want those with no config attached
            if self._meta.model == DomainRequest:
                exists = DomainRequest.objects.filter(name=self.instance.name,
                                                      config=None)
                if exists:
                    exists[0].config = self.instance.config
                    self.instance = exists[0]
            # if it is a Domain, we want those which are not approved
            else:
                exists = Domain.objects.filter(name=self.instance.name)
                if exists and exists[0].config != "approved":
                    exists[0].config = self.instance.config
                    self.instance = exists[0]
        if commit:
            # delete if exists
            if self.cleaned_data and self.cleaned_data['DELETE']:
                if self.instance.pk:
                    return self.instance.delete()
                else:
                    return None
            super(DomainForm, self).save()
        return self.instance

class BaseDomainFormSet(DynamicBaseModelFormSet):
    model = DomainRequest

    def __init__(self, *args, **kwargs):
        kwargs['prefix'] = 'domain'
        super(BaseDomainFormSet, self).__init__(*args, **kwargs)

    def clean(self):
        """Checks that at least one domain is not deleted."""
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        # Get number of deleted forms
        deleted_forms = 0
        names = []
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            if (not form.cleaned_data) or form.cleaned_data['DELETE']:
                deleted_forms += 1
                continue
            # Check for repeated domain names
            if form.cleaned_data['name'] in names:
                raise ValidationError("Duplicated domain name found.")
            names.append(form.cleaned_data['name'])
        # Check if all forms are deleted
        if (self.total_form_count() == 0 or
                self.total_form_count() == deleted_forms):
            raise ValidationError("At least one domain should be specified.")
        # Check if number of non deleted forms is greater then max_num
        if (self.total_form_count() - deleted_forms) > self.max_num:
            raise ValidationError("Number of domains exceeded.")

class ConfigForm(ModelForm):
    class Meta:
        model = Config
        fields = (
                  'display_name',
                  'display_short_name',
                  'incoming_type',
                  'incoming_hostname',
                  'incoming_socket_type',
                  'incoming_port',
                  'incoming_username_form',
                  'incoming_authentication',
                  'outgoing_hostname',
                  'outgoing_socket_type',
                  'outgoing_port',
                  'outgoing_username_form',
                  'outgoing_authentication',
                 )
    incoming_type = ChoiceField(widget=RadioSelect,
                                choices=Config.INCOMING_TYPE_CHOICES)

    def __init__(self, *args, **kwargs):
        self.domain_formset = kwargs.pop('domain_formset', None)
        self.docurl_formset = kwargs.pop('docurl_formset', None)
        self.enableurl_formset = kwargs.pop('enableurl_formset', None)
        if not self.domain_formset:
            raise(Exception('Domain formset required.'))
        if not self.docurl_formset:
            raise(Exception('DocURL formset required.'))
        if not self.enableurl_formset:
            raise(Exception('EnableURL formset required.'))
        super(ConfigForm, self).__init__(*args, **kwargs)

    def clean_incoming_port(self):
        return clean_port(self, "incoming_port")

    def clean_outgoing_port(self):
        return clean_port(self, "outgoing_port")

    def is_valid_all(self, *args, **kwargs):
        return (self.is_valid(*args, **kwargs) and
                self.domain_formset.is_valid(*args, **kwargs) and
                self.docurl_formset.is_valid(*args, **kwargs) and
                self.enableurl_formset.is_valid(*args, **kwargs))

    def save_all(self, *args, **kwargs):
        super(ConfigForm, self).save(*args, **kwargs)
        # Save domain formset
        self.domain_formset.save(commit=False)
        for form in self.domain_formset:
            form.instance.config = self.instance
        self.domain_formset.save()
        # Save DocURL formset
        self.docurl_formset.save(commit=False)
        for form in self.docurl_formset:
            form.instance.config = self.instance
        self.docurl_formset.save()
        # Save EnableURL formset
        self.enableurl_formset.save(commit=False)
        for form in self.enableurl_formset:
            form.instance.config = self.instance
        self.enableurl_formset.save()

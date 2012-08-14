# -*- coding: utf-8 -*-

import re
from django.core.urlresolvers import reverse
from django.db import models
from django.forms import (ChoiceField, BooleanField, HiddenInput, ModelForm,
    RadioSelect, ValidationError)
from django.forms.models import BaseModelFormSet
from django.forms.formsets import BaseFormSet
from django.forms.models import modelformset_factory
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.translation import get_language_info
import ispdb.audit as audit

class Domain(models.Model):
    name = models.CharField(max_length=100, unique=True,
                            verbose_name="Email domain",
                            help_text="(e.g. \"gmail.com\")")
    config = models.ForeignKey('Config', related_name="domains",
                               blank=True) # blank is for requests and rejects

    @staticmethod
    def create_from_domainrequest(domainrequest):
        """create domain from domainrequest
        """
        d = Domain()
        d.name = domainrequest.name
        d.config = domainrequest.config
        return d

    def __str__(self): return str(self.name)
    def __unicode__(self): return self.name

class DomainRequest(models.Model):
    name = models.CharField(max_length=100, verbose_name="Email domain",
                            help_text="(e.g. \"gmail.com\")")
    config = models.ForeignKey('Config', related_name="domainrequests",
                               blank=True, null=True)
    votes = models.IntegerField(default=1)

    def __str__(self): return str(self.name)
    def __unicode__(self): return self.name

def constructXMLTag(name):
    if '_' in name:
        firstword, others = name.split('_', 1)
        words = others.split('_')
        xmlfield = firstword + ''.join([word.capitalize() for word in words])
    else:
        xmlfield = name
    return xmlfield

class Config(models.Model):
    """
    A Config object contains all of the metadata about a configuration.
    It is 1-many mapped to Domain objects which apply to it.

    """

    class Meta:
        permissions = (
            ('can_approve', 'Can approve configurations'),
        )

    def __str__(self):
        "for use in the admin UI"
        return str(self.display_name)

    def __unicode__(self):
        return self.display_name

    owner = models.ForeignKey(User, unique=False, blank=True, null=True,
                              on_delete=models.SET_NULL)
    last_update_datetime = models.DateTimeField(auto_now=True)
    created_datetime = models.DateTimeField(auto_now_add=True)
    deleted_datetime = models.DateTimeField(null=True)
    CONFIG_CHOICES = [
        ("requested", "requested"),
        ("suggested", "suggested"),
        ("approved", "approved"),
        ("invalid", "invalid"),
        ("deleted", "deleted"),
    ]
    status = models.CharField(max_length=20, choices = CONFIG_CHOICES)
    last_status = models.CharField(max_length=20, choices = CONFIG_CHOICES)
    email_provider_id = models.CharField(max_length=50)
    display_name = models.CharField(
        max_length=100,
        verbose_name="The name of this ISP",
        help_text="e.g. \"Google's Gmail Service\"")
    display_short_name = models.CharField(
        max_length=100,
        verbose_name="A short version of the ISP name",
        help_text="e.g. \"Gmail\"")
    INCOMING_TYPE_CHOICES = (
        ('imap', 'IMAP'),
        ('pop3', 'POP'),
    )
    incoming_type = models.CharField(max_length=100,
                                     choices=INCOMING_TYPE_CHOICES)
    incoming_hostname = models.CharField(max_length=100)
    incoming_port = models.PositiveIntegerField()
    INCOMING_SOCKET_TYPE_CHOICES = (
        ("plain", "No encryption"),
        ("SSL", "SSL/TLS"),
        ("STARTTLS", "STARTTLS"),
    )
    incoming_socket_type = models.CharField(
        max_length=8,
        choices=INCOMING_SOCKET_TYPE_CHOICES)
    incoming_username_form = models.CharField(max_length=100,
                                              verbose_name="Username formula")
    INCOMING_AUTHENTICATION_CHOICES = (
        ("password-cleartext", "Unencrypted Password"),
        ("password-encrypted", "Encrypted Password"),
        ("NTLM", "NTLM"),
        ("GSSAPI", "GSSAPI"),
    )
    incoming_authentication = models.CharField(
        max_length = 20,
        choices = INCOMING_AUTHENTICATION_CHOICES,
        default = "password-encrypted",
        help_text = """<strong>Unencrypted Password</strong>: Send password
                    unencrypted in the clear. Dangerous, if SSL isn't used
                    either. PLAIN or LOGIN etc…<br/>

                    <strong>Encrypted Password</strong>: Hashed password.
                    Offers minimal protection for passwords.  CRAM-MD5 or
                    DIGEST-MD5. Not NTLM.<br/>"""
    )
    outgoing_hostname = models.CharField(max_length=100)
    outgoing_port = models.PositiveIntegerField()
    OUTGOING_SOCKET_TYPE_CHOICES = (
        ("plain", "No encryption"),
        ("SSL", "SSL/TLS"),
        ("STARTTLS", "STARTTLS"),
    )
    outgoing_socket_type = models.CharField(
        max_length=8,
        choices=OUTGOING_SOCKET_TYPE_CHOICES)
    outgoing_username_form = models.CharField(max_length=100,
                                              verbose_name="Username formula")
    OUTGOING_AUTHENTICATION_CHOICES = (
        ("password-cleartext", "Unencrypted Password"),
        ("password-encrypted", "Encrypted Password"),
        ("none", "Client IP address"),
        ("smtp-after-pop", "SMTP-after-POP"),
        ("NTLM", "NTLM"),
        ("GSSAPI", "GSSAPI"),
    )
    outgoing_authentication = models.CharField(
        max_length = 20,
        choices = OUTGOING_AUTHENTICATION_CHOICES,
        default = "password-encrypted",
        help_text = """<strong>Unencrypted Password</strong>: Send password
                    unencrypted in the clear. Dangerous, if SSL isn't used
                    either. PLAIN or LOGIN etc…<br/>

                    <strong>Encrypted Password</strong>: Hashed password.
                    Offers minimal protection for passwords.  CRAM-MD5 or
                    DIGEST-MD5. Not NTLM.<br/>"""
    )
    outgoing_add_this_server = models.BooleanField(
        verbose_name="Add this server to list???")
    outgoing_use_global_preferred_server = models.BooleanField(
        verbose_name="Use global server instead")

    flagged_as_incorrect = models.BooleanField()
    flagged_by_email = models.EmailField(blank=True)

    history = audit.AuditTrail()

class Issue(models.Model):
    title = models.CharField(max_length=50)
    description = models.TextField(max_length=3000)
    created_datetime = models.DateTimeField(auto_now_add=True)
    config = models.ForeignKey(Config, related_name="reported_issues")
    updated_config = models.ForeignKey(Config, null=True, related_name="issue")
    owner = models.ForeignKey(User, unique=False, blank=True, null=True,
                              on_delete=models.SET_NULL)
    STATUS_CHOICES = [
        ("open", "open"),
        ("closed", "closed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default="open")

class DocURL(models.Model):
    url = models.URLField(
        verbose_name="URL of the page describing these settings")
    config = models.ForeignKey(Config)

    def __str__(self): return str(self.url)
    def __unicode__(self): return self.url

class DocURLDesc(models.Model):
    description = models.TextField(
        max_length=100,
        verbose_name="Description of the settings page")
    language = models.CharField(
        max_length=10,
        verbose_name="Language",
        choices=settings.LANGUAGES)
    docurl = models.ForeignKey(DocURL, related_name="descriptions")

    def __str__(self): return str(self.description)
    def __unicode__(self): return self.description

# Forms
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


class DocURLDescForm(DynamicModelForm):
    class Meta:
        model = DocURLDesc
        exclude = ['docurl']

    def __init__(self, *args, **kwargs):
        super(DocURLDescForm, self).__init__(*args, **kwargs)
        self.fields['description'].widget.attrs.update({'rows': 2, 'cols': 20})
        # Redefine our choices, so we can add the translated language names and
        # sort the list by language name
        choices = []
        choices.append(self.fields['language'].choices[0])
        langs = self.fields['language'].choices[1:]
        langs.sort(key=lambda l: l[1].lower())
        for code, lang in langs:
            li = get_language_info(code)
            choices.append((code, lang + ' - ' + li['name_local']))
        self.fields['language'].choices = choices

    def save(self, commit=True):
        super(DocURLDescForm, self).save(commit=False)
        if commit:
            # delete if exists
            if self.cleaned_data and self.cleaned_data['DELETE']:
                if self.instance.pk:
                    return self.instance.delete()
                else:
                    return None
            super(DocURLDescForm, self).save()
        return self.instance


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
        super(BaseDocURLFormSet, self).__init__(*args, **kwargs)
        # construct description formsets
        self.DocURLDescFormSet = modelformset_factory(DocURLDesc,
                extra=self.extra, form=DocURLDescForm,
                formset=BaseDocURLDescFormSet)
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
        exclude = ['status',
                   'last_status',
                   'deleted_datetime',
                   'email_provider_id',
                   'flagged_as_incorrect',
                   'flagged_by_email',
                   'outgoing_add_this_server',
                   'outgoing_use_global_preferred_server',
                   'owner',
                   ]
    incoming_type = ChoiceField(widget=RadioSelect,
                                choices=Config.INCOMING_TYPE_CHOICES)

    def __init__(self, *args, **kwargs):
        self.domain_formset = kwargs.pop('domain_formset', None)
        self.docurl_formset = kwargs.pop('docurl_formset', None)
        if not self.domain_formset:
            raise(Exception('Domain formset required.'))
        if not self.docurl_formset:
            raise(Exception('DocURL formset required.'))
        super(ConfigForm, self).__init__(*args, **kwargs)

    def clean_incoming_port(self):
        return clean_port(self, "incoming_port")

    def clean_outgoing_port(self):
        return clean_port(self, "outgoing_port")

    def is_valid_all(self, *args, **kwargs):
        return (self.is_valid(*args, **kwargs) and
                self.domain_formset.is_valid(*args, **kwargs) and
                self.docurl_formset.is_valid(*args, **kwargs))

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

# -*- coding: utf-8 -*-

import re
from django.core.urlresolvers import reverse
from django.db import models
from django.forms import (ChoiceField, BooleanField, HiddenInput, ModelForm,
    RadioSelect, ValidationError)
from django.forms.formsets import BaseFormSet
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
import ispdb.audit as audit

class Domain(models.Model):
    name = models.CharField(max_length=100, unique=True,
                            verbose_name="Email domain",
                            help_text="(e.g. \"gmail.com\")")
    config = models.ForeignKey('Config', related_name="domains",
                               blank=True) # blank is for requests and rejects

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
    settings_page_url = models.URLField(
        verbose_name="URL of the page describing these settings")

    LANGUAGE_CHOICES = (
        ('en', "English"),
        ('fr', "Francais"),
    )
    settings_page_language = models.CharField(
        max_length=20,
        verbose_name="Language of the settings page",
        choices=LANGUAGE_CHOICES)

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

class IssueForm(ModelForm):
    show_form = BooleanField(required=False, initial=False, widget=HiddenInput)

    class Meta:
        model = Issue
        fields = ['title', 'description']

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

    def clean_incoming_port(self):
        return clean_port(self, "incoming_port")
    def clean_outgoing_port(self):
        return clean_port(self, "outgoing_port")

class DomainForm(ModelForm):
    delete = BooleanField(required=False, initial=False, widget=HiddenInput)

    class Meta:
        model = DomainRequest
        fields = ('name',)

    def __init__(self, *args, **kwargs):
        self.config_status = kwargs.pop('config_status', '')
        super(DomainForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(DomainForm, self).clean()
        # if it is going to be deleted, dont need to to check it
        if cleaned_data["delete"]:
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
            msg = ("Domain name it not valid")
            try:
                if not regex.match(data.encode('idna')): # IDN -> ACE
                    raise ValidationError(mark_safe(msg))
            except UnicodeError: # invalid domain
                raise ValidationError(mark_safe(msg))
        # check if domain already exists
        if not self.config_status == 'suggested':
            dom = Domain.objects.filter(name=data, config__status='approved')
            if dom and (not self.initial.has_key('name') or (dom[0].name !=
                    self.initial['name'])):
                msg = ("Domain configuration already exists "
                       "<a href=\"%s\">here</a>." %
                       reverse("ispdb_details", args=[dom[0].config.id]))
                raise ValidationError(mark_safe(msg))
        return cleaned_data

def clean_port(self,field):
    data = self.cleaned_data[field]
    if data > 65535:
        raise ValidationError("Port number cannot be larger than 65535")
    return data

class BaseDomainFormSet(BaseFormSet):
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
            if not form.cleaned_data:
                continue
            if form.cleaned_data['delete']:
                deleted_forms = deleted_forms + 1
            else:
                # Check for repeated domain names
                if form.cleaned_data['name'] in names:
                    raise ValidationError("Duplicated domain name found.")
                names.append(form.cleaned_data['name'])
        # Check if all forms are deleted
        if self.total_form_count() == deleted_forms:
            raise ValidationError("At least one domain should be specifed.")
        # Check if number of non deleted forms is greater then max_num
        if (self.total_form_count() - deleted_forms) > self.max_num:
            raise ValidationError("Number of domains exceeded.")

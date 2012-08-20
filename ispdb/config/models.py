# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

import ispdb.audit as audit


class Domain(models.Model):
    name = models.CharField(max_length=100, unique=True,
                            verbose_name="Email domain",
                            help_text="(e.g. \"gmail.com\")")
    config = models.ForeignKey('Config', related_name="domains",
                               blank=True)  # blank is for requests and rejects

    @staticmethod
    def create_from_domainrequest(domainrequest):
        """create domain from domainrequest
        """
        d = Domain()
        d.name = domainrequest.name
        d.config = domainrequest.config
        return d

    def __str__(self):
        return str(self.name)

    def __unicode__(self):
        return self.name


class DomainRequest(models.Model):
    name = models.CharField(max_length=100, verbose_name="Email domain",
                            help_text="(e.g. \"gmail.com\")")
    config = models.ForeignKey('Config', related_name="domainrequests",
                               blank=True, null=True)
    votes = models.IntegerField(default=1)

    def __str__(self):
        return str(self.name)

    def __unicode__(self):
        return self.name


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
    deleted_datetime = models.DateTimeField(null=True, blank=True)
    CONFIG_CHOICES = [
        ("requested", "requested"),
        ("suggested", "suggested"),
        ("approved", "approved"),
        ("invalid", "invalid"),
        ("deleted", "deleted"),
    ]
    status = models.CharField(max_length=20, choices=CONFIG_CHOICES)
    last_status = models.CharField(max_length=20, choices=CONFIG_CHOICES,
            blank=True)
    email_provider_id = models.CharField(max_length=50, blank=True)
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
        max_length=20,
        choices=INCOMING_AUTHENTICATION_CHOICES,
        default="password-encrypted",
        help_text="""<strong>Unencrypted Password</strong>: Send password
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
        max_length=20,
        choices=OUTGOING_AUTHENTICATION_CHOICES,
        default="password-encrypted",
        help_text="""<strong>Unencrypted Password</strong>: Send password
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

    locked = models.BooleanField()

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


class CommonConfigURL(models.Model):
    url = models.URLField(
        verbose_name="URL of the page")
    config = models.ForeignKey(Config, related_name="%(class)s_set")

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.url)

    def __unicode__(self):
        return self.url


class CommonURLDesc(models.Model):
    description = models.TextField(
        max_length=100,
        verbose_name="Description")
    language = models.CharField(
        max_length=10,
        verbose_name="Language",
        choices=settings.LANGUAGES)

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.description)

    def __unicode__(self):
        return self.description


class DocURL(CommonConfigURL):
    pass
DocURL._meta.get_field('url').verbose_name = ("URL of the page describing "
    "these settings")


class DocURLDesc(CommonURLDesc):
    docurl = models.ForeignKey(DocURL, related_name="descriptions")
DocURLDesc._meta.get_field('description').verbose_name = ('Description of the '
    'settings page')


class EnableURL(CommonConfigURL):
    pass
EnableURL._meta.get_field('url').verbose_name = ("URL of the page with enable "
    "instructions")


class EnableURLInst(CommonURLDesc):
    enableurl = models.ForeignKey(EnableURL, related_name="instructions")
EnableURLInst._meta.get_field('description').verbose_name = ('Instruction')

from django.contrib import admin
from django.core.urlresolvers import reverse
from django.db import models
from django.forms import ChoiceField
from django.forms import ModelForm
from django.forms import RadioSelect
from django.forms import ValidationError
from django.utils.safestring import mark_safe
import ispdb.audit as audit

import lxml.etree as ET

from StringIO import StringIO

class Domain(models.Model):
  name = models.CharField(max_length=100, unique=True,
                          verbose_name="Email domain",
                          help_text="(e.g. \"gmail.com\")")
  config = models.ForeignKey('Config', related_name="domains",
                             blank=True) # blank is for requests and rejects
  votes = models.IntegerField(default=1)
  DOMAIN_CHOICES = [
    ("requested", "requested for inclusion"),
    ("configured", "domain mapped to a configuration"),
    ("rejected", "domain can't be accepted"),
  ]
  status = models.CharField(max_length=20, choices = DOMAIN_CHOICES)
  def __str__(self): return self.name

class UnclaimedDomain(models.Model):
  name = models.CharField(max_length=100, verbose_name="Email domain",
                          help_text="(e.g. \"gmail.com\")")
  votes = models.IntegerField(default=1)
  DOMAIN_CHOICES = [
    ('requested', 'requested for inclusion'),
    ('configured', 'domain mapped to a configuration'),
    ('rejected', 'domain can\'t be accepted'),
  ]
  status = models.CharField(max_length=20, choices = DOMAIN_CHOICES)
  def __str__(self): return self.name

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
  A Config object contains all of the metadata about a configuration.  It is 1-many mapped to Domain objects
  which apply to it.

  """

  class Meta:
    permissions = (
      ('can_approve', 'Can approve configurations'),
      )
  def as_xml(self):
    """
    Return the configuration using the XML document that Thunderbird is expecting.
    """
    desiredOutput = {
      "display_name": "displayName",
      "display_short_name": "displayShortName",
      "incoming_hostname": "hostname",
      "incoming_port": "port",
      "incoming_socket_type": "socketType",
      "incoming_username_form": "username",
      "incoming_authentication": "authentication",
      "outgoing_hostname": "hostname",
      "outgoing_port": "port",
      "outgoing_socket_type": "socketType",
      "outgoing_username_form": "username",
      "outgoing_authentication": "authentication",
      "outgoing_add_this_server": "addThisServer",
      "outgoing_use_global_preferred_server": "useGlobalPreferredServer",
    }
    incoming = None
    outgoing = None
    config = ET.Element("clientConfig")
    emailProvider = ET.SubElement(config,"emailProvider")
    emailProvider.attrib["id"] = self.email_provider_id
    for domain in Domain.objects.filter(config=self):
      ET.SubElement(emailProvider,"domain").text = domain.name
    for field in self._meta.fields:
      if field.name not in desiredOutput:
        continue
      if field.name.startswith('incoming'):
        if incoming is None:
            incoming = ET.SubElement(emailProvider,"incomingServer")
            incoming.attrib["type"] = self.incoming_type
        name = field.name
        currParent = incoming
      elif field.name.startswith('outgoing'):
        if outgoing is None:
            outgoing = ET.SubElement(emailProvider,"outgoingServer")
            outgoing.attrib["type"] = "smtp"
        name = field.name
        currParent = outgoing
      else:
        name = field.name
        currParent = emailProvider
      name = desiredOutput[name]
      e = ET.SubElement(currParent,name)
      e.text = (lambda x: (type(x) is bool) and str(x).lower() or str(x)) (getattr(self,field.name)) #converts True to "true" and False to "false"

    retval = StringIO("w")
    xml = ET.ElementTree(config)
    xml.write(retval, encoding="UTF-8", xml_declaration=True)
    return retval.getvalue()

  def __str__(self):
    "for use in the admin UI"
    return self.display_name

  last_update_datetime = models.DateTimeField(auto_now=True)
  created_datetime = models.DateTimeField(auto_now_add=True)
  approved = models.BooleanField(default=False)
  invalid = models.BooleanField(default=False)
  email_provider_id = models.CharField(max_length=50)
  display_name = models.CharField(max_length=100, verbose_name="The name of this ISP", help_text="e.g. \"Google's Gmail Service\"")
  display_short_name = models.CharField(max_length=100, verbose_name="A short version of the ISP name", help_text="e.g. \"Gmail\"")
  INCOMING_TYPE_CHOICES = (
    ('imap', 'IMAP'),
    ('pop3', 'POP'),
  )
  incoming_type = models.CharField(max_length=100, choices=INCOMING_TYPE_CHOICES)
  incoming_hostname = models.CharField(max_length=100)
  incoming_port = models.PositiveIntegerField()
  INCOMING_SOCKET_TYPE_CHOICES = (
    ("plain", "No encryption"),
    ("SSL", "SSL/TLS"),
    ("STARTTLS", "STARTTLS"),
  )
  incoming_socket_type = models.CharField(max_length=8, choices=INCOMING_SOCKET_TYPE_CHOICES)
  incoming_username_form = models.CharField(max_length=100, verbose_name="Username formula")
  INCOMING_AUTHENTICATION_CHOICES = (
    ('plain', 'Plain (cleartext)'),
  )
  incoming_authentication = models.CharField(max_length=20, choices=INCOMING_AUTHENTICATION_CHOICES)

  outgoing_hostname = models.CharField(max_length=100)
  outgoing_port = models.PositiveIntegerField()
  OUTGOING_SOCKET_TYPE_CHOICES = (
    ("plain", "No encryption"),
    ("SSL", "SSL/TLS"),
    ("STARTTLS", "STARTTLS"),
  )
  outgoing_socket_type = models.CharField(max_length=8, choices=OUTGOING_SOCKET_TYPE_CHOICES)
  outgoing_username_form = models.CharField(max_length=100, verbose_name="Username formula")
  OUTGOING_AUTHENTICATION_CHOICES = (
    ('plain', 'Plain (cleartext)'),
  )
  outgoing_authentication = models.CharField(max_length=20, choices=OUTGOING_AUTHENTICATION_CHOICES)
  outgoing_add_this_server = models.BooleanField(verbose_name="Add this server to list???")
  outgoing_use_global_preferred_server = models.BooleanField(verbose_name="Use global server instead")

  settings_page_url = models.URLField(verbose_name="URL of the page describing these settings")
  LANGUAGE_CHOICES = (
    ('en', "English"),
    ('fr', "Francais"),
  )
  settings_page_language = models.CharField(max_length=20, verbose_name="Language of the settings page",
                                            choices=LANGUAGE_CHOICES)

  flagged_as_incorrect = models.BooleanField()
  flagged_by_email = models.EmailField(blank=True)
  confirmations = models.IntegerField(default=0)
  problems = models.IntegerField(default=0)

  history = audit.AuditTrail()

class DomainInline(admin.TabularInline):
    model = Domain

class UnclaimedDomainAdmin(admin.ModelAdmin):
    model = UnclaimedDomain


class ConfigAdmin(admin.ModelAdmin):
    inlines = [
        DomainInline,
    ]
    radio_fields = {"incoming_type": admin.VERTICAL}

#admin.site.register(Config, ConfigAdmin)
#admin.site.register(UnclaimedDomain, UnclaimedDomainAdmin)

class ConfigForm(ModelForm):
    class Meta:
        model = Config
        exclude = ['approved',
                   'invalid',
                   'email_provider_id',
                   'flagged_as_incorrect',
                   'flagged_by_email',
                   'outgoing_add_this_server',
                   'outgoing_use_global_preferred_server',
                   'incoming_username_form'
                   ]
    incoming_type = ChoiceField(widget=RadioSelect, choices=Config.INCOMING_TYPE_CHOICES)

    def clean_incoming_port(self):
        return clean_port(self, "incoming_port")
    def clean_outgoing_port(self):
        return clean_port(self, "outgoing_port")

class DomainForm(ModelForm):
    class Meta:
        model = Domain
        fields = ('name',)
    def clean_name(self):
        data = self.cleaned_data["name"]
        dom = Domain.objects.filter(name=data)
        if dom:
            msg = 'Domain configuration already exists \
            <a href="%s">here</a>.' % \
            reverse("ispdb_details", kwargs={"id" : dom[0].config.id})
            raise ValidationError(mark_safe(msg))
        return data

def clean_port(self,field):
    data = self.cleaned_data[field]
    if data > 65535:
        raise ValidationError("Port number cannot be larger than 65535")
    return data

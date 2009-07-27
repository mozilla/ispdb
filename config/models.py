from django.db import models
from django.forms import ModelForm, RadioSelect, ChoiceField
import ispdb.audit as audit
from django.contrib import admin

class Domain(models.Model):
  name = models.CharField(max_length=100, verbose_name="Email domain",
                          help_text="(e.g. \"gmail.com\")")
  config = models.ForeignKey('Config', related_name="domains",
                             blank=True) # blank is for requests and rejects
  votes = models.IntegerField(default=1)
  DOMAIN_CHOICES = [
    ('requested', 'requested for inclusion'),
    ('configured', 'domain mapped to a configuration'),
    ('rejected', 'domain can\'t be accepted'),
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

#admin.site.register(Domain)

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
    indent = '  '
    indentLevel = 1
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<clientConfig>',
             indent * indentLevel + '<emailProvider id=\"' + self.email_provider_id +'\">']
    in_incoming = False
    in_outgoing = False
    for field in self._meta.fields:
      if field.name.startswith('incoming'):
        name = field.name[len('incoming_'):]
        if in_outgoing:
          lines.append(indent * indentLevel + '</outgoingServer>')
          in_outgoing = False
          indentLevel -= 1
        if not in_incoming:
          lines.append(indent * indentLevel + '<incomingServer type="' + self.incoming_type + '\">')
          in_incoming = True
          indentLevel += 1
        if name == "type": continue # handled above
      elif field.name.startswith('outgoing'):
        name = field.name[len('outgoing_'):]
        if in_incoming:
          lines.append(indent * indentLevel + '</incomingServer>')
          in_incoming = False
          indentLevel -= 1
        if not in_outgoing:
          lines.append(indent * indentLevel + '<outgoingServer>')
          in_outgoing = True
          indentLevel += 1
      else:
        if in_incoming:
          lines.append(indent * indentLevel + '</incomingServer>')
          in_incoming = False
          indentLevel -= 1
        if in_outgoing:
          lines.append(indent * indentLevel + '</outgoingServer>')
          in_outgoing = False
          indentLevel -= 1
        name = field.name
      if '_' in name:
        firstword, others = name.split('_', 1)
        words = others.split('_')
        xmlfield = firstword + ''.join([word.capitalize() for word in words])
      else:
        xmlfield = name
      value = str(getattr(self, field.name))
      lines.append(indent * indentLevel + "<%(xmlfield)s>%(value)s</%(xmlfield)s>" % locals())
    lines.append(indent * indentLevel + '</emailProvider>')
    lines.append('</clientConfig>')
    return '\n'.join(lines)

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
  incoming_port = models.IntegerField(max_length=5)
  INCOMING_SOCKET_TYPE_CHOICES = (
    ('SSL', 'SSL'),
    ('TLS', 'TLS'),
    ('None', 'None'),
  )
  incoming_socket_type = models.CharField(max_length=5, choices=INCOMING_SOCKET_TYPE_CHOICES)
  incoming_username_form = models.CharField(max_length=100, verbose_name="Username formula")
  INCOMING_AUTHENTICATION_CHOICES = (
    ('plain', 'Plain (cleartext)'),
  )
  incoming_authentication = models.CharField(max_length=20, choices=INCOMING_AUTHENTICATION_CHOICES)
  
  outgoing_hostname = models.CharField(max_length=100)
  outgoing_port = models.IntegerField(max_length=5)
  OUTGOING_SOCKET_TYPE_CHOICES = (
    ('SSL', 'SSL'),
    ('TLS', 'TLS'),
    ('None', 'None'),
  )
  outgoing_socket_type = models.CharField(max_length=5, choices=OUTGOING_SOCKET_TYPE_CHOICES)
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
    
class DomainForm(ModelForm):
    class Meta:
        model = Domain
        fields = ('name',)

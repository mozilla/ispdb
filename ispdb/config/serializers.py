# -*- coding: utf-8 -*-

import lxml.etree as ET
from StringIO import StringIO

from ispdb.config.models import Domain, DomainRequest

# The serializers in reverse order, newest at the top.

def xmlOneDotOne(data):
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
    }
    incoming = None
    outgoing = None
    config = ET.Element("clientConfig")
    config.attrib["version"] = "1.1"
    emailProvider = ET.SubElement(config, "emailProvider")
    qs = Domain.objects.filter(config=data) or (
        DomainRequest.objects.filter(config=data))
    for domain in qs:
      if not data.email_provider_id:
        data.email_provider_id = domain.name
      ET.SubElement(emailProvider, "domain").text = domain.name
    emailProvider.attrib["id"] = data.email_provider_id
    for field in data._meta.fields:
      if field.name not in desiredOutput:
        continue
      if field.name.startswith("incoming"):
        if incoming is None:
            incoming = ET.SubElement(emailProvider, "incomingServer")
            incoming.attrib["type"] = data.incoming_type
        name = field.name
        currParent = incoming
      elif field.name.startswith("outgoing"):
        if outgoing is None:
            outgoing = ET.SubElement(emailProvider, "outgoingServer")
            outgoing.attrib["type"] = "smtp"
        name = field.name
        currParent = outgoing
      else:
        name = field.name
        currParent = emailProvider
      if name == "incoming_username_form" and data.incoming_username_form == "":
        data.incoming_username_form = data.outgoing_username_form
      name = desiredOutput[name]
      e = ET.SubElement(currParent, name)
      text = getattr(data, field.name)

      if type(text) is bool:
        # Force boolean values to use lowercase.
        text = unicode(text).lower()
      else:
        # Force other values to be converted into unicode strings.
        text = unicode(text)

      e.text = text
    # EnableURL
    for enableurl in data.enableurl_set.all():
        enable = ET.SubElement(emailProvider, "enable")
        enable.attrib["visiturl"] = enableurl.url
        for inst in enableurl.instructions.all():
            d = ET.SubElement(enable, "instruction")
            d.attrib["lang"] = inst.language
            d.text = unicode(inst.description)
    # DocURL
    for docurl in data.docurl_set.all():
        doc = ET.SubElement(emailProvider, "documentation")
        doc.attrib["url"] = docurl.url
        for desc in docurl.descriptions.all():
            d = ET.SubElement(doc, "descr")
            d.attrib["lang"] = desc.language
            d.text = unicode(desc.description)

    retval = StringIO("w")
    xml = ET.ElementTree(config)
    xml.write(retval, encoding="UTF-8", xml_declaration=True)
    return retval.getvalue()

def xmlOneDotZero(data):
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
    authentication_values = {
      "password-cleartext": "plain",
      "password-encrypted": "secure",
      "client-ip-address": "none",
      "smtp-after-pop": "none",
    }
    incoming = None
    outgoing = None
    config = ET.Element("clientConfig")
    config.attrib["version"] = "1.0"
    emailProvider = ET.SubElement(config, "emailProvider")
    for domain in Domain.objects.filter(config=data):
      ET.SubElement(emailProvider, "domain").text = domain.name
      if not data.email_provider_id:
        data.email_provider_id = domain.name
    emailProvider.attrib["id"] = data.email_provider_id
    for field in data._meta.fields:
      if field.name not in desiredOutput:
        continue
      if field.name.startswith("incoming"):
        if incoming is None:
            incoming = ET.SubElement(emailProvider, "incomingServer")
            incoming.attrib["type"] = data.incoming_type
        name = field.name
        currParent = incoming
      elif field.name.startswith("outgoing"):
        if outgoing is None:
            outgoing = ET.SubElement(emailProvider, "outgoingServer")
            outgoing.attrib["type"] = "smtp"
        name = field.name
        currParent = outgoing
      else:
        name = field.name
        currParent = emailProvider
      if name == "incoming_username_form" and data.incoming_username_form == "":
        data.incoming_username_form = data.outgoing_username_form
      name = desiredOutput[name]
      e = ET.SubElement(currParent, name)
      text = getattr(data, field.name)

      if type(text) is bool:
        # Force boolean values to use lowercase.
        text = unicode(text).lower()
      else:
        # Force other values to be converted into unicode strings.
        text = unicode(text)

      # Fix up the data to make it 1.0 compliant.
      if name == "authentication":
        text = authentication_values.get(text, text)

      e.text = text

    retval = StringIO("w")
    xml = ET.ElementTree(config)
    xml.write(retval, encoding="UTF-8", xml_declaration=True)
    return retval.getvalue()

# This is the data format version, not the application version.
# It only needs to change when the data format needs to change in a way
# that breaks old clients, which are hopefully exceptional cases.
# In other words, this does *not* change with every TB major release.
_serializers = {
    "1.0" : xmlOneDotZero,
    "1.1" : xmlOneDotOne,
}

def get(version):
    # If there is no version requested, return the most recent version.
    if version == None:
      return xmlOneDotZero
    return _serializers.get(version, None)


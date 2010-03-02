# -*- coding: utf-8 -*-

import lxml.etree as ET
from StringIO import StringIO

from ispdb.config.models import Domain

def xmlThreeDotZero(data):
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
    config.attrib["version"] = "3.0"
    emailProvider = ET.SubElement(config, "emailProvider")
    emailProvider.attrib["id"] = data.email_provider_id
    for domain in Domain.objects.filter(config=data):
      ET.SubElement(emailProvider, "domain").text = domain.name
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
      name = desiredOutput[name]
      e = ET.SubElement(currParent, name)
      text = getattr(data, field.name)

      if type(text) is bool:
        # Force boolean values to use lowercase.
        text = unicode(text).lower()
      else:
        # Force other values to be converted into unicode strings.
        text = unicode(text)

      # Fix up the data to make it 3.0 compliant.
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
    "3.0" : xmlThreeDotZero,
}

def get(version):
    # If there is no version requested, return the most recent version.
    if version == None:
      return xmlThreeDotZero
    return _serializers.get(version, None)


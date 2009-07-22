import os, sys

from ispdb.config.models import Domain, Config
try:
  import xml.etree.ElementTree as ET
except ImportError:
  import elementtree.ElementTree as ET


datadir = os.environ.get("AUTOCONFIG_DATA", "../autoconfig_data")
for fname in os.listdir(datadir):
  if fname.startswith('.') or fname == "README": continue
  print "PROCESSING", fname
  et = ET.parse(os.path.join(datadir, fname))
  root = et.getroot()
  #print root
  incoming = root.find('.//incomingServer')
  outgoing = root.find('.//outgoingServer')
  id = root.find(".//emailProvider").attrib['id']
  # if we have one for this id, skip it
  if Config.objects.filter(email_provider_id=id):
    continue
  c = Config(id=None,
             email_provider_id = id,
             display_name = root.find('.//displayName').text,
             display_short_name = root.find('.//displayShortName').text,
             incoming_type = incoming.attrib['type'],
             incoming_hostname = incoming.find('hostname').text,
             incoming_port = int(incoming.find('port').text),
             incoming_socket_type = incoming.find('socketType').text,
             incoming_authentication = incoming.find('authentication').text,
             incoming_username_form = incoming.find('username').text,

             outgoing_hostname = outgoing.find('hostname').text,
             outgoing_port = int(outgoing.find('port').text),
             outgoing_socket_type = outgoing.find('socketType').text,
             outgoing_username_form = outgoing.find('username').text,
             outgoing_authentication = outgoing.find('authentication').text,
             outgoing_add_this_server = outgoing.find('addThisServer').text == "true",
             outgoing_use_global_preferred_server = outgoing.find('useGlobalPreferredServer').text == "true",

             )
  domains = root.findall('.//domain')
  c.save()
  ds = [Domain(id=None, name=domain.text, config=c) for domain in domains]
  for d in ds:
    d.save()

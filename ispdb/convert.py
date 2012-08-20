import lxml.etree as ET
import os

from ispdb.config.models import Config, Domain


def get_username(element):
    rv = element.find('username')
    if rv is None:
        rv = element.find('usernameForm')
    if rv is None:
        rv = ""
    else:
        rv = rv.text
    return rv


def get_authentication(element):
    rv = element.find('authentication').text
    if (rv == "plain"):
        rv = "password-cleartext"
    elif (rv == "secure"):
        rv = "password-encrypted"
    return rv


def main():
    datadir = os.environ.get("AUTOCONFIG_DATA", "../autoconfig_data")
    for fname in os.listdir(datadir):
        fullpath = os.path.join(datadir, fname)
        if fname.startswith('.') or os.path.isdir(fullpath) or (fname ==
                "README"):
            continue
        print "PROCESSING", fname
        et = ET.parse(fullpath)
        root = et.getroot()
        #print root
        incoming = root.find('.//incomingServer')
        outgoing = root.find('.//outgoingServer')
        id = root.find(".//emailProvider").attrib['id']
        # if we have one for this id, skip it
        if Config.objects.filter(email_provider_id=id):
            continue

        # Handle the older forms of XML.
        incoming_username_form = get_username(incoming)
        outgoing_username_form = get_username(outgoing)
        incoming_authentication = get_authentication(incoming)
        outgoing_authentication = get_authentication(outgoing)

        if not incoming_authentication:
            continue

        try:
            addThisServer = outgoing.find('addThisServer').text == "true"
        except:
            addThisServer = False

        try:
            useGlobalPreferredServer = \
                    outgoing.find('useGlobalPreferredServer').text == "true"
        except:
            useGlobalPreferredServer = False

        c = Config(id=None,
                   email_provider_id=id,
                   display_name=root.find('.//displayName').text,
                   display_short_name=root.find('.//displayShortName').text,
                   incoming_type=incoming.attrib['type'],
                   incoming_hostname=incoming.find('hostname').text,
                   incoming_port=int(incoming.find('port').text),
                   incoming_socket_type=incoming.find('socketType').text,
                   incoming_authentication=incoming_authentication,
                   incoming_username_form=incoming_username_form,
                   outgoing_hostname=outgoing.find('hostname').text,
                   outgoing_port=int(outgoing.find('port').text),
                   outgoing_socket_type=outgoing.find('socketType').text,
                   outgoing_username_form=outgoing_username_form,
                   outgoing_authentication=outgoing_authentication,
                   outgoing_add_this_server=addThisServer,
                   outgoing_use_global_preferred_server=(
                        useGlobalPreferredServer),
                   status='approved',
        )
        domains = root.findall('.//domain')
        c.save()
        ds = [Domain(id=None, name=d.text, config=c) for d in domains]
        for d in ds:
            d.save()


if __name__ == "__main__":
    main()

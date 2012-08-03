"""
This file contains methods to do sanity checks on domains and configs
"""

import re
import os
import socket
import smtplib
import imaplib
import poplib
import ssl
import dns.resolver
import tldextract

TIMEOUT = 10


def get_nameservers(domain):
    try:
        answers = dns.resolver.query(domain, 'NS')
    except:
        return None
    nservers = []
    for ns in answers:
        nservers.append(str(ns))
    return set(nservers)


def get_mxservers(domain):
    try:
        answers = dns.resolver.query(domain, 'MX')
    except:
        return None
    mxservers = []
    for server in answers:
        srv = str(server).split(' ')[1]
        mxservers.append(srv)
    return mxservers


# SMTP methods
def _smtp_parse_supported_auth(string):
    ret = {}
    regex = re.compile('(?P<password_cleartext>(LOGIN|PLAIN))|'
                       '(?P<password_encrypted>CRAM-MD5)|'
                       '(?P<NTLM>(NTLM|MSN))|'
                       '(?P<GSSAPI>GSSAPI)')
    i = regex.finditer(string)
    for m in i:
        ret.update(dict((k, v) for k, v in m.groupdict().iteritems() if
            (not k in ret) or v))
    if ret:
        ret['password-cleartext'] = ret['password_cleartext']
        ret['password-encrypted'] = ret['password_encrypted']
    return ret


def smtp_check_starttls(hostname, port):
    try:
        server = smtplib.SMTP(hostname, port, timeout=TIMEOUT)
        server.ehlo()
        res = server.starttls()
        ehlo = server.ehlo()
        server.quit()
        if res[0] == 220:
            return _smtp_parse_supported_auth(ehlo[1])
        return None
    except:
        try:
            server.quit()
        except:
            pass
        return None


def smtp_check_ssl(hostname, port):
    try:
        server = smtplib.SMTP_SSL(hostname, port, timeout=TIMEOUT)
        ehlo = server.ehlo()
        server.quit()
        return _smtp_parse_supported_auth(ehlo[1])
    except:
        return None


def smtp_check_plain(hostname, port):
    try:
        server = smtplib.SMTP(hostname, port, timeout=TIMEOUT)
        ehlo = server.ehlo()
        server.quit()
        return _smtp_parse_supported_auth(ehlo[1])
    except:
        return None


# IMAP methods
def IMAP_starttls(self, keyfile=None, certfile=None, cert_reqs=ssl.CERT_NONE,
                  ca_certs=None):
    """
    Add STARTTLS support included only in python 3.2
    http://hg.python.org/cpython/rev/8d6516949a71/
    """
    name = 'STARTTLS'
    if name not in self.capabilities:
        raise self.error("STARTTLS extension not supported by server.")
    if hasattr(self, '_tls_established') and self._tls_established:
        raise error_proto('TLS session already established')
    typ, dat = self._simple_command(name)
    if typ == 'OK':
        self.sock = ssl.wrap_socket(self.sock, keyfile, certfile,
                                    cert_reqs=cert_reqs,
                                    ca_certs=ca_certs)
        self.file = self.sock.makefile('rb')
        self._tls_established = True
        typ, dat = self.capability()
        if dat == [None]:
            raise self.error('no CAPABILITY response from server')
        self.capabilities = tuple(dat[-1].upper().split())
    else:
        raise self.error("Couldn't establish TLS session")
    return self._untagged_response(typ, dat, name)

imaplib.IMAP4.__dict__['starttls'] = IMAP_starttls
imaplib.Commands['STARTTLS'] = ('NONAUTH',)
imaplib.socket.setdefaulttimeout(TIMEOUT)


def _imap_parse_supported_auth(string):
    ret = {}
    regex = re.compile('AUTH=(?P<password_cleartext>(LOGIN|PLAIN))|'
                       '(?P<password_encrypted>CRAM-MD5)|'
                       '(?P<NTLM>(NTLM|MSN))|'
                       '(?P<GSSAPI>GSSAPI)')
    i = regex.finditer(string)
    for m in i:
        ret.update(dict((k, v) for k, v in m.groupdict().iteritems() if
            (not k in ret) or v))
    if ret:
        ret['password-cleartext'] = ret['password_cleartext']
        ret['password-encrypted'] = ret['password_encrypted']
    return ret


def imap_check_starttls(hostname, port):
    try:
        server = imaplib.IMAP4(hostname, port)
        server.starttls()
        capa = server.capabilities
        server.shutdown()
        capa_str = ' '.join(str(n) for n in capa)
        return _imap_parse_supported_auth(capa_str)
    except:
        try:
            server.shutdown()
        except:
            pass
        return None


def imap_check_ssl(hostname, port):
    try:
        server = imaplib.IMAP4_SSL(hostname, port)
        capa = server.capabilities
        server.shutdown()
        capa_str = ' '.join(str(n) for n in capa)
        return _imap_parse_supported_auth(capa_str)
    except:
        return None


def imap_check_plain(hostname, port):
    try:
        server = imaplib.IMAP4(hostname, port)
        capa = server.capabilities
        server.shutdown()
        capa_str = ' '.join(str(n) for n in capa)
        return _imap_parse_supported_auth(capa_str)
    except:
        return None


# POP3 methods
def POP_stls(self, keyfile=None, certfile=None, cert_reqs=ssl.CERT_NONE,
                  ca_certs=None):
    """
    Start a TLS session on the active connection as specified in RFC 2595.
    http://bugs.python.org/issue4473
    """
    if hasattr(self, '_tls_established') and self._tls_established:
        raise poplib.error_proto('-ERR TLS session already established')
    try:
        resp = self._shortcmd('STLS')
        self.sock = ssl.wrap_socket(self.sock, keyfile, certfile,
                                    cert_reqs=cert_reqs,
                                    ca_certs=ca_certs)
        self.file = self.sock.makefile('rb')
        self._tls_established = True
    except poplib.error_proto:
        raise poplib.error_proto("Couldn't establish TLS session")
    return resp

poplib.POP3.__dict__['stls'] = POP_stls
poplib.socket.setdefaulttimeout(TIMEOUT)


def _pop3_parse_supported_auth(string):
    ret = {}
    regex = re.compile('(?P<password_cleartext>(PLAIN|LOGIN))|'
                       '(?P<password_encrypted>CRAM-MD5)|'
                       '(?P<NTLM>(NTLM|MSN))|'
                       '(?P<GSSAPI>GSSAPI)')
    i = regex.finditer(string)
    for m in i:
        ret.update(dict((k, v) for k, v in m.groupdict().iteritems() if
            (not k in ret) or v))
    if ret:
        ret['password-cleartext'] = ret['password_cleartext']
        ret['password-encrypted'] = ret['password_encrypted']
    return ret


def pop3_check_starttls(hostname, port):
    try:
        server = poplib.POP3(hostname, port, timeout=TIMEOUT)
        res = server.stls()
        try:
            res = server._longcmd('CAPA')
            res_str = ' '.join(str(n) for n in res[1])
            ret = _pop3_parse_supported_auth(res_str)
        except:
            ret = {}
        server.quit()
        return ret
    except:
        try:
            server.quit()
        except:
            pass
        return None


def pop3_check_ssl(hostname, port):
    try:
        server = poplib.POP3_SSL(hostname, port)
        try:
            res = server._longcmd('CAPA')
            res_str = ' '.join(str(n) for n in res[1])
            ret = _pop3_parse_supported_auth(res_str)
        except:
            ret = {}
        server.quit()
        return ret
    except:
        return None


def pop3_check_plain(hostname, port):
    try:
        server = poplib.POP3(hostname, port, timeout=TIMEOUT)
        try:
            res = server._longcmd('CAPA')
            res_str = ' '.join(str(n) for n in res[1])
            ret = _pop3_parse_supported_auth(res_str)
        except:
            ret = {}
        server.quit()
        return ret
    except:
        return None


def check_socket_type(hostname, proto, socket_type, port=None):
    key = proto + ":" + socket_type.lower()
    funcs = {
             "imap:ssl": (imap_check_ssl, 993),
             "imap:starttls": (imap_check_starttls, 143),
             "imap:plain": (imap_check_plain, 143),
             "pop3:ssl": (pop3_check_ssl, 995),
             "pop3:starttls": (pop3_check_starttls, 110),
             "pop3:plain": (pop3_check_plain, 110),
             "smtp:ssl": (smtp_check_ssl, 465),
             "smtp:starttls": (smtp_check_starttls, 587),
             "smtp:plain": (smtp_check_plain, 587),
            }
    (func, default_port) = funcs[key]
    if not port:
        port = default_port
    return func(hostname, port)


def do_domain_checks(domains):
    domain_errors = []
    domain_warnings = []
    if not domains:
        return (domain_errors, domain_warnings)
    # Check and compare nameservers
    ns = get_nameservers(domains[0].name)
    if not ns:
        domain_warnings.append("Could not compare name servers because DNS "
                               "query of the first domain (%s) returned "
                               "None." % (domains[0].name))
    else:
        for domain in domains[1:]:
            sub_ns = get_nameservers(str(domain))
            if not sub_ns or not sub_ns.issubset(ns):
                domain_warnings.append("Name servers of domain '%s' differ"
                                       " from name servers of the main "
                                       "domain '%s'."
                                       % (domains[0], domain))
     # Check MX records
    tlds = set()
    extract = tldextract.TLDExtract(fetch=False)
    for domain in domains:
        mxservers = get_mxservers(domain.name)
        # check if domain is valid and add it to tlds
        tld = extract(domain.name)
        if (not tld.tld) or tld.subdomain:
            domain_errors.append("Domain '%s' is not valid." %
                                 (domain.name))
        else:
            tlds.add(domain.name)
        # get domain and tld from MX servers
        for server in mxservers:
            tld = extract(server)
            if tld.tld:
                tlds.add(tld.domain + '.' + tld.tld)
        # Check if domain has at least one MX server
        if not mxservers or len(mxservers) < 1:
            domain_errors.append("Couldn't find MX record for '%s'." %
                                 (domain,))
    # Compare incoming/outgoing server TLD with tlds
    tld = extract(domains[0].config.incoming_hostname)
    d = tld.domain + '.' + tld.tld
    if not d in tlds:
        domain_errors.append("Incoming server domain '%s' is different"
                             " from the configured domains and its MX "
                             "servers domains." % (d))
    tld = extract(domains[0].config.outgoing_hostname)
    d = tld.domain + '.' + tld.tld
    if not d in tlds:
        domain_errors.append("Outgoing server domain '%s' is different"
                             " from the configured domains and its MX "
                             "servers domains." % (d))
    return (domain_errors, domain_warnings)


def do_config_checks(config):
    config_errors = []
    config_warnings = []
    # Incoming server checks
    # Check if there is a better socket type available
    if config.incoming_socket_type == 'plain' or (
        config.incoming_socket_type == 'STARTTLS'):
        if check_socket_type(config.incoming_hostname,
                             config.incoming_type,
                             'SSL') != None:
            config_warnings.append("Incoming server '%s' supports SSL "
                                   "using default port." %
                                   (config.incoming_hostname))
        elif config.incoming_socket_type == 'plain':
            if check_socket_type(config.incoming_hostname,
                                 config.incoming_type,
                                 'STARTTLS') != None:
                config_warnings.append("Incoming server '%s' supports "
                                       "STARTTLS using default port." %
                                       (config.incoming_hostname,))
    # Check if current options are working
    capa = check_socket_type(config.incoming_hostname,
                             config.incoming_type,
                             config.incoming_socket_type,
                             port=config.incoming_port)
    if capa == None:
        config_errors.append("Incoming server '%s' does not support "
                             "socket type %s on port %s." %
                              (config.incoming_hostname,
                               config.incoming_socket_type,
                               config.incoming_port))
    elif not capa:
        config_warnings.append("Couldn't retrieve supported authentication"
                               " methods from '%s'. Parser returned None." %
                               (config.incoming_hostname))
    else:  # Check supported authentication methods
        capabilities = ["GSSAPI", "password-encrypted", "NTLM",
                "password-cleartext"]
        for auth in capabilities:
            if config.incoming_authentication == auth:
                if not capa[auth]:
                    config_errors.append("Incoming server '%s' does not "
                                         "support auth type %s." %
                                         (config.incoming_hostname, auth))
                break
            if capa[auth]:
                config_warnings.append("Incoming server '%s' supports "
                                       "auth type %s." %
                                       (config.incoming_hostname, auth))
    # Outgoing server
    # Check if there is a better socket type available
    if (config.outgoing_socket_type == 'plain') or (
            config.outgoing_socket_type == 'STARTTLS'):
        if check_socket_type(config.outgoing_hostname,
                             'smtp',
                             'SSL') != None:
            config_warnings.append("Outgoing server '%s' supports SSL "
                                   "using default port." %
                                   (config.outgoing_hostname))
        elif config.outgoing_socket_type == 'plain':
            if check_socket_type(config.outgoing_hostname,
                                 'smtp',
                                 'STARTTLS') != None:
                config_warnings.append("Outgoing server supports '%s' "
                                       "STARTTLS using default port." %
                                       (config.outgoing_hostname,))
    # Check if current options are working
    capa = check_socket_type(config.outgoing_hostname,
                             'smtp',
                             config.outgoing_socket_type,
                             port=config.outgoing_port)
    if capa == None:
        config_errors.append("Outgoing server '%s' does not support "
                             "socket type %s on port %s." %
                             (config.outgoing_hostname,
                              config.outgoing_socket_type,
                              config.outgoing_port))
    elif not capa:
        config_warnings.append("Couldn't retrieve supported authentication"
                               "methods from '%s'." %
                               (config.incoming_hostname))
    else:  # Check authentication choices
        capabilities = ["GSSAPI", "password-encrypted", "NTLM",
                "password-cleartext"]
        for auth in capabilities:
            if config.outgoing_authentication == auth:
                if not capa[auth]:
                    config_errors.append("Outgoing server '%s' does not "
                                         "support auth type %s." %
                                         (config.outgoing_hostname, auth))
                break
            if capa[auth]:
                config_warnings.append("Outgoing server '%s' supports "
                                       "auth type %s." %
                                       (config.outgoing_hostname, auth))
    return (config_errors, config_warnings)

import re
import os
import socket
import smtplib
import imaplib
import poplib
import ssl
import dns.resolver

TIMEOUT=10

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
    regex = re.compile(r'(?P<password_cleartext>(LOGIN|PLAIN))|'
                        '(?P<password_encrypted>CRAM-MD5)|'
                        '(?P<NTLM>(NTLM|MSN))|'
                        '(?P<GSSAPI>GSSAPI)')
    i = regex.finditer(string)
    for m in i:
        ret.update(dict((k,v) for k,v in m.groupdict().iteritems() if
            not ret.has_key(k) or v))
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
    if hasattr(self,'_tls_established') and self._tls_established:
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

imaplib.IMAP4.__dict__['starttls']=IMAP_starttls
imaplib.Commands['STARTTLS']=('NONAUTH',)
imaplib.socket.setdefaulttimeout(TIMEOUT)

def _imap_parse_supported_auth(string):
    ret = {}
    regex = re.compile(r'AUTH=(?P<password_cleartext>(LOGIN|PLAIN))|'
                        '(?P<password_encrypted>CRAM-MD5)|'
                        '(?P<NTLM>(NTLM|MSN))|'
                        '(?P<GSSAPI>GSSAPI)')
    i = regex.finditer(string)
    for m in i:
        ret.update(dict((k,v) for k,v in m.groupdict().iteritems() if
            not ret.has_key(k) or v))
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
    if hasattr(self,'_tls_established') and self._tls_established:
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

poplib.POP3.__dict__['stls']=POP_stls
poplib.socket.setdefaulttimeout(TIMEOUT)

def _pop3_parse_supported_auth(string):
    ret = {}
    regex = re.compile(r'(?P<password_cleartext>(PLAIN|LOGIN))|'
                        '(?P<password_encrypted>CRAM-MD5)|'
                        '(?P<NTLM>(NTLM|MSN))|'
                        '(?P<GSSAPI>GSSAPI)')
    i = regex.finditer(string)
    for m in i:
        ret.update(dict((k,v) for k,v in m.groupdict().iteritems() if
            not ret.has_key(k) or v))
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
    if proto == 'imap':
        if socket_type.lower() == 'ssl':
            if not port:
                port = 993
            return imap_check_ssl(hostname, port)
        if socket_type.lower() == 'starttls':
            if not port:
                port = 143
            return imap_check_starttls(hostname, port)
        if socket_type.lower() == 'plain':
            if not port:
                port = 143
            return imap_check_plain(hostname, port)
    elif proto == 'pop3':
        if socket_type.lower() == 'ssl':
            if not port:
                port = 995
            return pop3_check_ssl(hostname, port)
        if socket_type.lower() == 'starttls':
            if not port:
                port = 110
            return pop3_check_starttls(hostname, port)
        if socket_type.lower() == 'plain':
            if not port:
                port = 110
            return pop3_check_plain(hostname, port)
    elif proto == 'smtp':
        if socket_type.lower() == 'ssl':
            if not port:
                port = 465
            return smtp_check_ssl(hostname, port)
        if socket_type.lower() == 'starttls':
            if not port:
                port = 587
            return smtp_check_starttls(hostname, port)
        if socket_type.lower() == 'plain':
            if not port:
                port = 587
            return smtp_check_plain(hostname, port)
    raise Exception('Should not get here.')

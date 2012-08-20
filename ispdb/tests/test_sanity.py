# -*- coding: utf-8 -*-

import dns.resolver
import imaplib
import mox
import poplib
import smtplib

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson
from nose.tools import assert_equal

from ispdb.config.configChecks import (do_domain_checks, do_config_checks,
    get_nameservers, get_mxservers, imap_check_plain, imap_check_ssl,
    imap_check_starttls, pop3_check_plain, pop3_check_ssl, pop3_check_starttls,
    smtp_check_plain, smtp_check_ssl, smtp_check_starttls, TIMEOUT)
from ispdb.config.models import Config


def ns_message_text(domain, ndomain):
    return ('id 1234\n'
            'opcode QUERY\n'
            'rcode NOERROR\n'
            'flags QR RD RA\n'
            ';QUESTION\n'
            '%(domain)s. IN  NS\n'
            ';ANSWER\n'
            '%(domain)s. 600 IN  NS  ns2.%(ndomain)s.\n'
            '%(domain)s. 600 IN  NS  ns3.%(ndomain)s.\n'
            '%(domain)s. 600 IN  NS  ns1.%(ndomain)s.\n'
            ';ADDITIONAL\n'
            % {'domain': domain, 'ndomain': ndomain})


def mx_message_text(domain, ndomain):
    return ('id 1234\n'
            'opcode QUERY\n'
            'rcode NOERROR\n'
            'flags QR RD RA\n'
            ';QUESTION\n'
            '%(domain)s. IN  MX\n'
            ';ANSWER\n'
            '%(domain)s. 600 IN  MX 100  mail1.%(ndomain)s.\n'
            '%(domain)s. 600 IN  MX 200  mail2.%(ndomain)s.\n'
            '%(domain)s. 600 IN  MX 300  mail3.%(ndomain)s.\n'
            ';ADDITIONAL\n'
            % {'domain': domain, 'ndomain': ndomain})


class SanityTest(TestCase):
    "A class to test the sanity view."

    fixtures = ['login_testdata', 'sanity']

    def setUp(self):
        self.mox = mox.Mox()
        self.mox.StubOutWithMock(dns.resolver, "query")
        self.mox.StubOutClassWithMocks(smtplib, 'SMTP')
        self.mox.StubOutClassWithMocks(smtplib, 'SMTP_SSL')
        self.mox.StubOutClassWithMocks(imaplib, 'IMAP4')
        self.mox.StubOutClassWithMocks(imaplib, 'IMAP4_SSL')
        self.mox.StubOutClassWithMocks(poplib, 'POP3')
        self.mox.StubOutClassWithMocks(poplib, 'POP3_SSL')

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_dns_methods(self):
        # Set up our mock expectations.
        name = dns.name.from_text('test.org.')
        message = dns.message.from_text(ns_message_text('test.org',
                                                        'test.org'))
        answer = dns.resolver.Answer(name, dns.rdatatype.NS,
                                     dns.rdataclass.IN, message)
        dns.resolver.query('test.org', 'NS').AndReturn(answer)
        message = dns.message.from_text(mx_message_text('test.org',
                                                        'test.org'))
        answer = dns.resolver.Answer(name, dns.rdatatype.MX,
                                     dns.rdataclass.IN, message)
        dns.resolver.query('test.org', 'MX').AndReturn(answer)
        self.mox.ReplayAll()

        #Test methods
        nss = get_nameservers('test.org')
        mxs = get_mxservers('test.org')

        # Verify the results (and the mock expectations.)
        self.mox.VerifyAll()
        assert_equal(nss, set(['ns1.test.org.', 'ns2.test.org.',
                               'ns3.test.org.']))
        assert_equal(mxs, ['mail1.test.org.',
                           'mail2.test.org.',
                           'mail3.test.org.',
                          ])

    def test_smtp_methods(self):
        # Set up our mock expectations.
        #plain
        server = smtplib.SMTP('smtp.test.org', 465, timeout=TIMEOUT)
        server.ehlo().AndReturn((250,
            'mx2.mail.corp.phx1.test.com\nPIPELINING\nSIZE '
            '31457280\nETRN\nAUTH LOGIN PLAIN'
            '\nENHANCEDSTATUSCODES\n8BITMIME\nDSN'))
        server.quit()
        #STARTTLS
        server = smtplib.SMTP('smtp.test.org', 465, timeout=TIMEOUT)
        server.ehlo()
        server.starttls().AndReturn((220, ''))
        server.ehlo().AndReturn((250,
            'mx2.mail.corp.phx1.test.com\nPIPELINING\nSIZE '
            '31457280\nETRN\nAUTH LOGIN'
            'PLAIN\nENHANCEDSTATUSCODES\n8BITMIME\nDSN'))
        server.quit()
        #SSL
        server = smtplib.SMTP_SSL('smtp.test.org', 465, timeout=TIMEOUT)
        server.ehlo().AndReturn((250,
            'mx2.mail.corp.phx1.test.com\nPIPELINING\nSIZE '
            '31457280\nETRN\nAUTH LOGIN PLAIN NTLM CRAM-MD5 GSSAPI UNSUPPORTED'
            '\nENHANCEDSTATUSCODES\n8BITMIME\nDSN'))
        server.quit()
        self.mox.ReplayAll()

        #Test methods
        ret_plain = smtp_check_plain('smtp.test.org', 465)
        ret_starttls = smtp_check_starttls('smtp.test.org', 465)
        ret_ssl = smtp_check_ssl('smtp.test.org', 465)

        # Verify the results (and the mock expectations.)
        self.mox.VerifyAll()
        assert_equal(ret_plain, {'password_cleartext': 'PLAIN',
                                 'NTLM': None,
                                 'password_encrypted': None,
                                 'GSSAPI': None,
                                 'password-cleartext': 'PLAIN',
                                 'password-encrypted': None
                                })
        assert_equal(ret_starttls, {'password_cleartext': 'PLAIN',
                                    'NTLM': None,
                                    'password_encrypted': None,
                                    'GSSAPI': None,
                                    'password-cleartext': 'PLAIN',
                                    'password-encrypted': None
                                   })
        assert_equal(ret_ssl, {'password_cleartext': 'PLAIN',
                               'NTLM': 'NTLM',
                               'password_encrypted': 'CRAM-MD5',
                               'GSSAPI': 'GSSAPI',
                               'password-cleartext': 'PLAIN',
                               'password-encrypted': 'CRAM-MD5'
                              })

    def test_imap_methods(self):
        # Set up our mock expectations.
        #plain
        server = imaplib.IMAP4('imap.test.org', 465)
        server.capabilities = ('IMAP4REV1', 'SASL-IR', 'SORT',
                'THREAD=REFERENCES', 'MULTIAPPEND',
                'UNSELECT', 'LITERAL+', 'IDLE', 'CHILDREN', 'NAMESPACE',
                'LOGIN-REFERRALS', 'QUOTA', 'AUTH=PLAIN', 'AUTH=LOGIN')
        server.shutdown()
        #STARTTLS
        server = imaplib.IMAP4('imap.test.org', 465)
        server.starttls()
        server.capabilities = ('IMAP4REV1', 'SASL-IR', 'SORT',
                'THREAD=REFERENCES', 'MULTIAPPEND',
                'UNSELECT', 'LITERAL+', 'IDLE', 'CHILDREN', 'NAMESPACE',
                'LOGIN-REFERRALS', 'QUOTA', 'AUTH=PLAIN', 'AUTH=LOGIN',
                'AUTH=CRAM-MD5', 'AUTH=NTLM', 'AUTH=GSSAPI',
                'AUTH=UNSUPPORTED')
        server.shutdown()
        #SSL
        server = imaplib.IMAP4_SSL('imap.test.org', 465)
        server.capabilities = ('IMAP4REV1', 'SASL-IR', 'SORT',
                'THREAD=REFERENCES', 'MULTIAPPEND',
                'UNSELECT', 'LITERAL+', 'IDLE', 'CHILDREN', 'NAMESPACE',
                'LOGIN-REFERRALS', 'QUOTA', 'AUTH=PLAIN', 'AUTH=LOGIN')
        server.shutdown()
        self.mox.ReplayAll()

        #Test methods
        ret_plain = imap_check_plain('imap.test.org', 465)
        ret_starttls = imap_check_starttls('imap.test.org', 465)
        ret_ssl = imap_check_ssl('imap.test.org', 465)

        # Verify the results (and the mock expectations.)
        self.mox.VerifyAll()
        assert_equal(ret_plain, {'password_cleartext': 'LOGIN',
                                 'NTLM': None,
                                 'password_encrypted': None,
                                 'GSSAPI': None,
                                 'password-cleartext': 'LOGIN',
                                 'password-encrypted': None
                                })
        assert_equal(ret_starttls, {'password_cleartext': 'LOGIN',
                                    'NTLM': 'NTLM',
                                    'password_encrypted': 'CRAM-MD5',
                                    'GSSAPI': 'GSSAPI',
                                    'password-cleartext': 'LOGIN',
                                    'password-encrypted': 'CRAM-MD5'
                                   })
        assert_equal(ret_ssl, {'password_cleartext': 'LOGIN',
                               'NTLM': None,
                               'password_encrypted': None,
                               'GSSAPI': None,
                               'password-cleartext': 'LOGIN',
                               'password-encrypted': None
                              })

    def test_pop_methods(self):
        # Set up our mock expectations.
        #plain
        server = poplib.POP3('pop3.test.org', 465, timeout=TIMEOUT)
        server._longcmd('CAPA').AndReturn(('+OK', ['CAPA', 'TOP',
            'LOGIN-DELAY 180', 'UIDL', 'RESP-CODES', 'PIPELINING', 'USER',
            'SASL PLAIN LOGIN'], 82))
        server.quit()
        #STARTTLS
        server = poplib.POP3('pop3.test.org', 465, timeout=TIMEOUT)
        server.stls()
        server._longcmd('CAPA').AndReturn(('+OK', ['CAPA', 'TOP',
            'LOGIN-DELAY 180', 'UIDL', 'RESP-CODES', 'PIPELINING', 'USER',
            'SASL PLAIN LOGIN CRAM-MD5 UNSUPPORTED NTLM GSSAPI'], 82))
        server.quit()
        #SSL
        server = poplib.POP3_SSL('pop3.test.org', 465)
        server._longcmd('CAPA').AndReturn(('+OK', ['CAPA', 'TOP',
            'LOGIN-DELAY 180', 'UIDL', 'RESP-CODES', 'PIPELINING', 'USER',
            'SASL PLAIN LOGIN'], 82))
        server.quit()
        self.mox.ReplayAll()

        #Test methods
        ret_plain = pop3_check_plain('pop3.test.org', 465)
        ret_starttls = pop3_check_starttls('pop3.test.org', 465)
        ret_ssl = pop3_check_ssl('pop3.test.org', 465)

        # Verify the results (and the mock expectations.)
        self.mox.VerifyAll()
        assert_equal(ret_plain, {'password_cleartext': 'LOGIN',
                                 'NTLM': None,
                                 'password_encrypted': None,
                                 'GSSAPI': None,
                                 'password-cleartext': 'LOGIN',
                                 'password-encrypted': None
                                })
        assert_equal(ret_starttls, {'password_cleartext': 'LOGIN',
                                    'NTLM': 'NTLM',
                                    'password_encrypted': 'CRAM-MD5',
                                    'GSSAPI': 'GSSAPI',
                                    'password-cleartext': 'LOGIN',
                                    'password-encrypted': 'CRAM-MD5'
                                   })
        assert_equal(ret_ssl, {'password_cleartext': 'LOGIN',
                               'NTLM': None,
                               'password_encrypted': None,
                               'GSSAPI': None,
                               'password-cleartext': 'LOGIN',
                               'password-encrypted': None
                              })

    def test_sanity_view_no_errors(self):
        # Set up our mock expectations.
        # _do_domain_checks for test.org and test.com
        name = dns.name.from_text('test.org.')
        message = dns.message.from_text(ns_message_text('test.org',
                                                        'test.org'))
        answer = dns.resolver.Answer(name, dns.rdatatype.NS,
                                     dns.rdataclass.IN, message)
        dns.resolver.query('test.org', 'NS').AndReturn(answer)
        name = dns.name.from_text('test.com.')
        message = dns.message.from_text(ns_message_text('test.com',
                                                        'test.org'))
        answer = dns.resolver.Answer(name, dns.rdatatype.NS,
                                     dns.rdataclass.IN, message)
        dns.resolver.query('test.com', 'NS').AndReturn(answer)
        name = dns.name.from_text('test.org.')
        message = dns.message.from_text(mx_message_text('test.org',
                                                        'test.org'))
        answer = dns.resolver.Answer(name, dns.rdatatype.MX,
                                     dns.rdataclass.IN, message)
        dns.resolver.query('test.org', 'MX').AndReturn(answer)
        name = dns.name.from_text('test.com.')
        message = dns.message.from_text(mx_message_text('test.com',
                                                        'test.org'))
        answer = dns.resolver.Answer(name, dns.rdatatype.MX,
                                     dns.rdataclass.IN, message)
        dns.resolver.query('test.com', 'MX').AndReturn(answer)
        # _do config _checks (imap SSL and stmp SSL)
        server = imaplib.IMAP4_SSL('mail.test.com', 995)
        server.capabilities = ('IMAP4REV1', 'SASL-IR', 'SORT',
                'THREAD=REFERENCES', 'MULTIAPPEND',
                'UNSELECT', 'LITERAL+', 'IDLE', 'CHILDREN', 'NAMESPACE',
                'LOGIN-REFERRALS', 'QUOTA', 'AUTH=PLAIN', 'AUTH=LOGIN')
        server.shutdown()
        server = smtplib.SMTP_SSL('mail.test.com', 465, timeout=TIMEOUT)
        server.ehlo().AndReturn((250,
            'mx2.mail.corp.phx1.test.com\nPIPELINING\nSIZE '
            '31457280\nETRN\nAUTH LOGIN PLAIN'
            '\nENHANCEDSTATUSCODES\n8BITMIME\nDSN'))
        server.quit()
        self.mox.ReplayAll()

        # Test the method.
        self.client.login(username='test_admin', password='test')
        response = self.client.get(reverse("ispdb_sanity", args=[1]), {})
        data = simplejson.loads(response.content)
        warnings = data["warnings"]
        errors = data["errors"]

        # Verify the results (and the mock expectations.)
        self.mox.VerifyAll()
        assert_equal(len(warnings), 0)
        assert_equal(len(errors), 0)

    def test_do_domain_checks_errors(self):
        """ Test all import error/warnings returned by do_domain_checks
        """
        # Set up our mock expectations.
        # do_domain_checks compares first name servers of the first domain
        # with name servers of other domains. It will create a warning if we
        # return different name servers
        name = dns.name.from_text('test.org.')
        message = dns.message.from_text(ns_message_text('test.org',
                                                        'test.org'))
        answer = dns.resolver.Answer(name, dns.rdatatype.NS,
                                     dns.rdataclass.IN, message)
        dns.resolver.query('test.org', 'NS').AndReturn(answer)
        name = dns.name.from_text('test.com.')
        message = dns.message.from_text(ns_message_text('test.com',
                                                        'test.com'))
        answer = dns.resolver.Answer(name, dns.rdatatype.NS,
                                     dns.rdataclass.IN, message)
        dns.resolver.query('test.com', 'NS').AndReturn(answer)
        # now do_domain_checks will get domain name of all Domain objects and
        # its MX servers and compare against domain names of incoming server
        # and outgoing server. If they are different it will create an error
        # for each server
        name = dns.name.from_text('test.org.')
        message = dns.message.from_text(mx_message_text('test.org',
                                                        'test.org'))
        answer = dns.resolver.Answer(name, dns.rdatatype.MX,
                                     dns.rdataclass.IN, message)
        dns.resolver.query('test.org', 'MX').AndReturn(answer)
        name = dns.name.from_text('test.com.')
        message = dns.message.from_text(mx_message_text('test.com',
                                                        'test.com'))
        answer = dns.resolver.Answer(name, dns.rdatatype.MX,
                                     dns.rdataclass.IN, message)
        dns.resolver.query('test.com', 'MX').AndReturn(answer)

        self.mox.ReplayAll()

        #Test methods
        config = Config.objects.get(pk=1)
        # change to a different domain
        config.incoming_hostname = "mail.test.us"
        config.outgoing_hostname = "mail.test.us"
        config.save()
        errors, warnings = do_domain_checks(config.domains.all())

        # Verify the results (and the mock expectations.)
        self.mox.VerifyAll()
        assert_equal(len(errors), 2)
        assert_equal(len(warnings), 1)

    def test_do_config_checks_no_errors(self):
        # Set up our mock expectations.
        #plain
        server = smtplib.SMTP('smtp.test.org', 465, timeout=TIMEOUT)
        server.ehlo().AndReturn((250,
            'mx2.mail.corp.phx1.test.com\nPIPELINING\nSIZE '
            '31457280\nETRN\nAUTH LOGIN PLAIN'
            '\nENHANCEDSTATUSCODES\n8BITMIME\nDSN'))
        server.quit()
        #STARTTLS
        server = smtplib.SMTP('smtp.test.org', 465, timeout=TIMEOUT)
        server.ehlo()
        server.starttls().AndReturn((220, ''))
        server.ehlo().AndReturn((250,
            'mx2.mail.corp.phx1.test.com\nPIPELINING\nSIZE '
            '31457280\nETRN\nAUTH LOGIN'
            'PLAIN\nENHANCEDSTATUSCODES\n8BITMIME\nDSN'))
        server.quit()
        #SSL
        server = smtplib.SMTP_SSL('smtp.test.org', 465, timeout=TIMEOUT)
        server.ehlo().AndReturn((250,
            'mx2.mail.corp.phx1.test.com\nPIPELINING\nSIZE '
            '31457280\nETRN\nAUTH LOGIN PLAIN NTLM CRAM-MD5 GSSAPI UNSUPPORTED'
            '\nENHANCEDSTATUSCODES\n8BITMIME\nDSN'))
        server.quit()
        self.mox.ReplayAll()

        #Test methods
        ret_plain = smtp_check_plain('smtp.test.org', 465)
        ret_starttls = smtp_check_starttls('smtp.test.org', 465)
        ret_ssl = smtp_check_ssl('smtp.test.org', 465)

        # Verify the results (and the mock expectations.)
        self.mox.VerifyAll()
        assert_equal(ret_plain, {'password_cleartext': 'PLAIN',
                                 'NTLM': None,
                                 'password_encrypted': None,
                                 'GSSAPI': None,
                                 'password-cleartext': 'PLAIN',
                                 'password-encrypted': None
                                })
        assert_equal(ret_starttls, {'password_cleartext': 'PLAIN',
                                    'NTLM': None,
                                    'password_encrypted': None,
                                    'GSSAPI': None,
                                    'password-cleartext': 'PLAIN',
                                    'password-encrypted': None
                                   })
        assert_equal(ret_ssl, {'password_cleartext': 'PLAIN',
                               'NTLM': 'NTLM',
                               'password_encrypted': 'CRAM-MD5',
                               'GSSAPI': 'GSSAPI',
                               'password-cleartext': 'PLAIN',
                               'password-encrypted': 'CRAM-MD5'
                              })

    def test_do_config_checks_socket_type_errors(self):
        # Set up our mock expectations.
        # Our configuration is using STARTTLS. If we return it supports SSL and
        # it doesn't support STARTTLS, do_config_checks should return 1 error
        # and 1 warning for each server (incoming and outgoing)
        # IMAP SSL
        server = imaplib.IMAP4_SSL('mail.test.com', 993)
        server.capabilities = ('IMAP4REV1', 'SASL-IR', 'SORT',
                'THREAD=REFERENCES', 'MULTIAPPEND',
                'UNSELECT', 'LITERAL+', 'IDLE', 'CHILDREN', 'NAMESPACE',
                'LOGIN-REFERRALS', 'QUOTA', 'AUTH=PLAIN', 'AUTH=LOGIN')
        server.shutdown()
        # IMAP STARTTLS
        server = imaplib.IMAP4('mail.test.com', 995)
        server.starttls().AndRaise(Exception("STARTTLS extension not supported"
                "by server."))
        server.shutdown()
        # SMTP SSL
        server = smtplib.SMTP_SSL('mail.test.com', 465, timeout=TIMEOUT)
        server.ehlo().AndReturn((250,
            'mx2.mail.corp.phx1.test.com\nPIPELINING\nSIZE '
            '31457280\nETRN\nAUTH LOGIN PLAIN NTLM CRAM-MD5 GSSAPI UNSUPPORTED'
            '\nENHANCEDSTATUSCODES\n8BITMIME\nDSN'))
        server.quit()
        # SMTP STARTTLS
        server = smtplib.SMTP('mail.test.com', 465, timeout=TIMEOUT)
        server.ehlo()
        server.starttls().AndRaise(smtplib.SMTPException("STARTTLS extension"
                "not supported by server."))
        server.quit()
        self.mox.ReplayAll()

        #Test methods
        config = Config.objects.get(pk=1)
        config.incoming_socket_type = 'STARTTLS'
        config.outgoing_socket_type = 'STARTTLS'
        config.save()
        errors, warnings = do_config_checks(config)

        # Verify the results (and the mock expectations.)
        self.mox.VerifyAll()
        assert_equal(len(errors), 2)
        assert_equal(len(warnings), 2)

    def test_do_config_checks_capabilities_errors(self):
        # Set up our mock expectations.
        # Our configuration is using password-encrypted. If we return it
        # supports GSSAPI and doesn't support password-encrypted,
        # do_config_checks should return 1 error and 1 warning for each server
        # incoming and outgoing)
        # IMAP SSL
        server = imaplib.IMAP4_SSL('mail.test.com', 995)
        server.capabilities = ('IMAP4REV1', 'SASL-IR', 'SORT',
                'THREAD=REFERENCES', 'MULTIAPPEND',
                'UNSELECT', 'LITERAL+', 'IDLE', 'CHILDREN', 'NAMESPACE',
                'LOGIN-REFERRALS', 'QUOTA', 'AUTH=PLAIN', 'AUTH=LOGIN',
                'AUTH=GSSAPI')
        server.shutdown()
        # SMTP SSL
        server = smtplib.SMTP_SSL('mail.test.com', 465, timeout=TIMEOUT)
        server.ehlo().AndReturn((250,
            'mx2.mail.corp.phx1.test.com\nPIPELINING\nSIZE '
            '31457280\nETRN\nAUTH LOGIN PLAIN NTLM GSSAPI UNSUPPORTED'
            '\nENHANCEDSTATUSCODES\n8BITMIME\nDSN'))
        server.quit()
        self.mox.ReplayAll()

        #Test methods
        config = Config.objects.get(pk=1)
        config.incoming_authentication = 'password-encrypted'
        config.outgoing_authentication = 'password-encrypted'
        config.save()
        errors, warnings = do_config_checks(config)

        # Verify the results (and the mock expectations.)
        self.mox.VerifyAll()
        assert_equal(len(errors), 2)
        assert_equal(len(warnings), 2)

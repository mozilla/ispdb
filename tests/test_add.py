# -*- coding: utf-8 -*-

import datetime
from django.test import TestCase
from django.core.urlresolvers import reverse
from nose.tools import *
from ispdb.config import models

class AddTest(TestCase):
    def test_ask(self):
        self.client.post(reverse('ispdb_add'),{'asking_or_adding':'asking',
                                               'form-TOTAL_FORMS':'1',
                                               'form-INITIAL_FORMS':'1',
                                               'form-0-name':'ty.com'})
        domain = models.UnclaimedDomain.objects.get(name='ty.com')
        assert isinstance(domain,models.UnclaimedDomain)

    def test_multiple_ask(self):
        self.client.post(reverse('ispdb_add'),{'asking_or_adding':'asking',
                                               'form-TOTAL_FORMS':'1',
                                               'form-INITIAL_FORMS':'1',
                                               'form-0-name':'ty.com'})
        self.client.post(reverse('ispdb_add'),{'asking_or_adding':'asking',
                                               'form-TOTAL_FORMS':'1',
                                               'form-INITIAL_FORMS':'1',
                                               'form-0-name':'ty.com'})
        domain = models.UnclaimedDomain.objects.get(name='ty.com')
        assert isinstance(domain,models.UnclaimedDomain)
        assert_equal(domain.votes,2);

    def test_add(self):
        res = self.client.post(reverse('ispdb_add'),
                         {'asking_or_adding':'adding',
                          'form-TOTAL_FORMS':'1',
                          'form-INITIAL_FORMS':'1',
                          'form-0-name':'test3.com',
                          'display_name':'test3',
                          'display_short_name':'test3',
                          'incoming_type':'imap',
                          'incoming_hostname':'foo',
                          'incoming_port':'333',
                          'incoming_socket_type':'None',
                          'incoming_authentication':'plain',
                          'outgoing_hostname':'bar',
                          'outgoing_port':'334',
                          'outgoing_socket_type':'TLS',
                          'outgoing_username_form':'%25EMAILLOCALPART%25',
                          'outgoing_authentication':'plain',
                          'settings_page_url':'google.com',
                          'settings_page_language':'en',
                          'confirmations':'0',
                          'problems':'0'})
        assert_equal(res.status_code,302)
        domain = models.Domain.objects.get(name="test3.com")
        assert isinstance(domain,models.Domain)

    def test_add_duplicate_domain(self):
        name = 'test.com';
        dom = models.Domain.objects.filter(name=name)
        assert_false(dom)
        res = self.client.post(reverse('ispdb_add'),
                         {'asking_or_adding':'adding',
                          'form-TOTAL_FORMS':'1',
                          'form-INITIAL_FORMS':'1',
                          'form-0-name':name,
                          'display_name':'test3',
                          'display_short_name':'test3',
                          'incoming_type':'imap',
                          'incoming_hostname':'foo',
                          'incoming_port':'333',
                          'incoming_socket_type':'None',
                          'incoming_authentication':'plain',
                          'outgoing_hostname':'bar',
                          'outgoing_port':'334',
                          'outgoing_socket_type':'TLS',
                          'outgoing_username_form':'%25EMAILLOCALPART%25',
                          'outgoing_authentication':'plain',
                          'settings_page_url':'google.com',
                          'settings_page_language':'en',
                          'confirmations':'0',
                          'problems':'0'})
        assert_equal(res.status_code,302)
        domain = models.Domain.objects.get(name=name)
        res = self.client.post(reverse('ispdb_add'),
                         {'asking_or_adding':'adding',
                          'form-TOTAL_FORMS':'1',
                          'form-INITIAL_FORMS':'1',
                          'form-0-name':name,
                          'display_name':'test3',
                          'display_short_name':'test3',
                          'incoming_type':'imap',
                          'incoming_hostname':'foo',
                          'incoming_port':'333',
                          'incoming_socket_type':'None',
                          'incoming_authentication':'plain',
                          'outgoing_hostname':'bar',
                          'outgoing_port':'334',
                          'outgoing_socket_type':'TLS',
                          'outgoing_username_form':'%25EMAILLOCALPART%25',
                          'outgoing_authentication':'plain',
                          'settings_page_url':'google.com',
                          'settings_page_language':'en',
                          'confirmations':'0',
                          'problems':'0'})
        assert_equal(res.status_code,200)
        assert isinstance(domain,models.Domain)

    def test_add_internationalization(self):
        name = u'Iñtërnâtiônàlizætiøn'
        dom = models.Domain.objects.filter(name=name)
        assert_false(dom)
        res = self.client.post(reverse('ispdb_add'), 
                         {'asking_or_adding':'adding',
                          'form-TOTAL_FORMS':'1',
                          'form-INITIAL_FORMS':'1',
                          'form-0-name':name,
                          'display_name':'test3',
                          'display_short_name':'test3',
                          'incoming_type':'imap',
                          'incoming_hostname':'foo',
                          'incoming_port':'333',
                          'incoming_socket_type':'None',
                          'incoming_authentication':'plain',
                          'outgoing_hostname':'bar',
                          'outgoing_port':'334',
                          'outgoing_socket_type':'TLS',
                          'outgoing_username_form':'%25EMAILLOCALPART%25',
                          'outgoing_authentication':'plain',
                          'settings_page_url':'google.com',
                          'settings_page_language':'en',
                          'confirmations':'0','problems':'0'})
        assert_equal(res.status_code,302)
        domain = models.Domain.objects.get(name=name)
        assert isinstance(domain,models.Domain)
        assert_equal(domain.name,name)

    @raises(models.Domain.DoesNotExist)
    def test_add_long_port(self):
        port = '800000000000000000000000000000000000000000000000'
        res = self.client.post(reverse('ispdb_add'),
                         {'asking_or_adding':'adding',
                          'form-TOTAL_FORMS':'1',
                          'form-INITIAL_FORMS':'1',
                          'form-0-name':'test',
                          'display_name':'test3',
                          'display_short_name':'test3',
                          'incoming_type':'imap',
                          'incoming_hostname':'foo',
                          'incoming_port':port,
                          'incoming_socket_type':'None',
                          'incoming_authentication':'plain',
                          'outgoing_hostname':'bar',
                          'outgoing_port':'334',
                          'outgoing_socket_type':'TLS',
                          'outgoing_username_form':'%25EMAILLOCALPART%25',
                          'outgoing_authentication':'plain',
                          'settings_page_url':'google.com',
                          'settings_page_language':'en',
                          'confirmations':'0',
                          'problems':'0'})
        assert_equal(res.status_code,200)
        model = models.Domain.objects.get(name="test")

    @raises(models.Domain.DoesNotExist)
    def test_add_negative_port(self):
        port = '-1000'
        res = self.client.post(reverse('ispdb_add'),
                         {'asking_or_adding':'adding',
                          'form-TOTAL_FORMS':'1',
                          'form-INITIAL_FORMS':'1',
                          'form-0-name':'test',
                          'display_name':'test3',
                          'display_short_name':'test3',
                          'incoming_type':'imap',
                          'incoming_hostname':'foo',
                          'incoming_port':port,
                          'incoming_socket_type':'None',
                          'incoming_authentication':'plain',
                          'outgoing_hostname':'bar',
                          'outgoing_port':'334',
                          'outgoing_socket_type':'TLS',
                          'outgoing_username_form':'%25EMAILLOCALPART%25',
                          'outgoing_authentication':'plain',
                          'settings_page_url':'google.com',
                          'settings_page_language':'en',
                          'confirmations':'0',
                          'problems':'0'})
        assert_equal(res.status_code,200)
        model = models.Domain.objects.get(name="test")

    @raises(models.Domain.DoesNotExist)
    def test_add_missing_name(self):
        res = self.client.post(reverse('ispdb_add'),
                         {'asking_or_adding':'adding',
                          'form-TOTAL_FORMS':'1',
                          'form-INITIAL_FORMS':'1',
                          'form-0-name':'test',
                          'display_name':'test3',
                          'display_short_name':'',
                          'incoming_type':'imap',
                          'incoming_hostname':'foo',
                          'incoming_port':'343',
                          'incoming_socket_type':'None',
                          'incoming_authentication':'plain',
                          'outgoing_hostname':'bar',
                          'outgoing_port':'334',
                          'outgoing_socket_type':'TLS',
                          'outgoing_username_form':'%25EMAILLOCALPART%25',
                          'outgoing_authentication':'plain',
                          'settings_page_url':'google.com',
                          'settings_page_language':'en',
                          'confirmations':'0',
                          'problems':'0'})
        assert_equal(res.status_code,200)
        model = models.Domain.objects.get(name="test")

    @raises(models.Domain.DoesNotExist)
    def test_add_letters_port(self):
        port = '11a1'
        res = self.client.post(reverse('ispdb_add'),
                         {'asking_or_adding':'adding',
                          'form-TOTAL_FORMS':'1',
                          'form-INITIAL_FORMS':'1',
                          'form-0-name':'test',
                          'display_name':'test3',
                          'display_short_name':'test3',
                          'incoming_type':'imap',
                          'incoming_hostname':'foo',
                          'incoming_port':port,
                          'incoming_socket_type':'None',
                          'incoming_authentication':'plain',
                          'outgoing_hostname':'bar',
                          'outgoing_port':'334',
                          'outgoing_socket_type':'TLS',
                          'outgoing_username_form':'%25EMAILLOCALPART%25',
                          'outgoing_authentication':'plain',
                          'settings_page_url':'google.com',
                          'settings_page_language':'en',
                          'confirmations':'0',
                          'problems':'0'})
        assert_equal(res.status_code,200)
        model = models.Domain.objects.get(name="test")

    def test_add_with_unconfirmed(self):
        name = 'test'
        unclaimed_after = models.UnclaimedDomain.objects.filter(name=name)
        assert_false(unclaimed_after)
        self.client.post(reverse('ispdb_add'),
                         {'asking_or_adding':'asking',
                          'form-TOTAL_FORMS':'1',
                          'form-INITIAL_FORMS':'1',
                          'form-0-name':name})
        unclaimed = models.UnclaimedDomain.objects.filter(name=name)
        assert unclaimed
        self.client.post(reverse('ispdb_add'),
                         {'asking_or_adding':'adding',
                          'form-TOTAL_FORMS':'1',
                          'form-INITIAL_FORMS':'1',
                          'form-0-name':name,
                          'display_name':'test3',
                          'display_short_name':'test3',
                          'incoming_type':'imap',
                          'incoming_hostname':'foo',
                          'incoming_port':'333',
                          'incoming_socket_type':'None',
                          'incoming_authentication':'plain',
                          'outgoing_hostname':'bar',
                          'outgoing_port':'334',
                          'outgoing_socket_type':'TLS',
                          'outgoing_username_form':'%25EMAILLOCALPART%25',
                          'outgoing_authentication':'plain',
                          'settings_page_url':'google.com',
                          'settings_page_language':'en',
                          'confirmations':'0',
                          'problems':'0'})
        unclaimed_after = models.UnclaimedDomain.objects.filter(name=name)
        assert_false(unclaimed_after)
        model = models.Domain.objects.get(name=name)
        assert isinstance(model,models.Domain)

class ModelTest(TestCase): 
    def test_simple_domain(self):
        config = models.Config(id='1',
                               incoming_port=1,
                               outgoing_port=2,
                               created_datetime=datetime.datetime.now())
        config.save()
        d = models.Domain(name='test',votes=1,config=config)
        d.save()
        domain = models.Domain.objects.get(name='test')
        assert isinstance(domain,models.Domain)

    def test_internationalization_domain(self):
        name = u'Iñtërnâtiônàlizætiøn'
        config = models.Config(id='1',
                               incoming_port=1,
                               outgoing_port=2,
                               created_datetime=datetime.datetime.now())
        config.save()
        d = models.Domain(name=name,votes=1,config=config)
        d.save()
        domain = models.Domain.objects.get(name=name)
        assert isinstance(domain,models.Domain)

# -*- coding: utf-8 -*-

from django.test import TestCase
from ispdb.config import views,models
from django.core.urlresolvers import reverse
from django.test.client import Client
import nose.tools
import re


class XMLTest(TestCase):

    fixtures = ['xml_testdata']

    def test_export_xml(self):
        reference_string = """<?xml version="1.0" encoding="UTF-8"?>
        <clientConfig>
          <emailProvider id="">
          <id>1</id>
          <lastUpdateDatetime>2009-09-30 00:24:54</lastUpdateDatetime>
          <createdDatetime>2009-09-30 00:24:54</createdDatetime>
          <approved>False</approved>
          <invalid>False</invalid>
          <emailProviderId></emailProviderId>
          <displayName>NetZero Email</displayName>
          <displayShortName>netzero</displayShortName>
          <incomingServer type="imap">
            <hostname>hostname_in</hostname>
            <port>143</port>
            <socketType>SSL</socketType>
            <usernameForm></usernameForm>
            <authentication>plain</authentication>
            </incomingServer>
          <outgoingServer>
            <hostname>hostname_out</hostname>
            <port>25</port>
            <socketType>None</socketType>
            <usernameForm>%EMAILLOCALPART%</usernameForm>
            <authentication>plain</authentication>
            <addThisServer>False</addThisServer>
            <useGlobalPreferredServer>False</useGlobalPreferredServer>
            </outgoingServer>
          <settingsPageUrl>http://www.referencematerial.com/</settingsPageUrl>
          <settingsPageLanguage>en</settingsPageLanguage>
          <flaggedAsIncorrect>False</flaggedAsIncorrect>
          <flaggedByEmail></flaggedByEmail>
          <confirmations>0</confirmations>
          <problems>0</problems>
          </emailProvider>
        </clientConfig>"""
        reference_string = re.sub(r'\s','',reference_string)

        domain = models.Domain.objects.get(name="test.com")
        config_xml = domain.config.as_xml()
        config_xml = re.sub(r'\s','',config_xml)
        assert config_xml == reference_string


# -*- coding: utf-8 -*-
import re
import os
from StringIO import StringIO

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.test.client import Client

from nose.tools import *
import nose.tools
from lxml import etree

from ispdb.config import views,models

class XMLTest(TestCase):

    fixtures = ['xml_testdata']

    def test_validated_export_xml(self):
        domain = models.Domain.objects.get(name="test.com")
        config_xml = domain.config.as_xml()
        doc = etree.XML(config_xml)
        xml_schema = etree.RelaxNG(file=os.path.join(os.getcwd(),
                                                    'tests/relaxng_schema.xml'))
        xml_schema.assertValid(doc)

    def test_xml_content(self):
        expected = { "domain" : ["test.com", "aim.com"],
            "displayName" : "NetZero Email",
            "displayShortName" : "netzero" }
        expected_incoming = { "hostname" : "hostname_in", "port" : "143",
            "socketType" : "SSL", "username" : None,
            "authentication" : "plain", }
        expected_outgoing = { "hostname" : "hostname_out",
            "port" : "25", "socketType" : "SSL",
            "username" : "%EMAILLOCALPART%", "authentication" : "plain",
            "addThisServer" : "false", "useGlobalPreferredServer" : "false" }
        domain = models.Domain.objects.get(name="test.com")
        config_xml = domain.config.as_xml()
        doc = etree.XML(config_xml)
        #gets incoming/outgoing server element root
        root = doc.getiterator();
        incoming = doc.find("emailProvider/incomingServer")
        outgoing = doc.find("emailProvider/outgoingServer")
        for element in root:
            if element.tag in expected:
                if type(expected[element.tag]) == list:
                    assert element.text in expected[element.tag]
                else:
                    assert_equal(element.text, expected[element.tag])
        for element in incoming:
            assert_equal(element.text, expected_incoming[element.tag])
        for element in outgoing:
            assert_equal(element.text, expected_outgoing[element.tag])


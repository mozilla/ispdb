# -*- coding: utf-8 -*-

import os
from lxml import etree

from django.core.urlresolvers import reverse
from django.test import TestCase
from nose.tools import assert_equal

from ispdb.config import models, serializers


def check_content(config_xml):
    expected = {"domain": ["test.com", "aim.com"],
        "displayName": "NetZero Email",
        "displayShortName": "netzero"}
    expected_incoming = {"hostname": "hostname_in", "port": "143",
        "socketType": "SSL", "username": "%EMAILLOCALPART%",
        "authentication": "plain"}
    expected_outgoing = {"hostname": "hostname_out",
        "port": "25", "socketType": "SSL",
        "username": "%EMAILLOCALPART%", "authentication": "plain",
        "addThisServer": "false", "useGlobalPreferredServer": "false"}
    doc = etree.XML(config_xml)
    #gets incoming/outgoing server element root
    root = doc.getiterator()
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


class XMLTest(TestCase):

    fixtures = ['xml_testdata']

    def test_validated_export_xml_one_zero(self):
        domain = models.Domain.objects.get(name="test.com")
        config_xml = serializers.xmlOneDotZero(domain.config)
        doc = etree.XML(config_xml)

        xml_schema = etree.RelaxNG(file=os.path.join(os.path.dirname(__file__),
                                                     'relaxng_schema.xml'))
        xml_schema.assertValid(doc)

    def test_validated_export_xml_one_one(self):
        domain = models.Domain.objects.get(name="test.com")
        config_xml = serializers.xmlOneDotOne(domain.config)
        doc = etree.XML(config_xml)
        xml_schema = etree.RelaxNG(file=os.path.join(os.path.dirname(__file__),
                                                     'relaxng_schema.1.1.xml'))
        xml_schema.assertValid(doc)

    def test_xml_content(self):
        domain = models.Domain.objects.get(name="test.com")
        config_xml = serializers.xmlOneDotZero(domain.config)
        check_content(config_xml)

    def test_export_xml_view_no_version(self):
        response = self.client.get(reverse("ispdb_export_xml",
                                   args=["1"]), {})
        check_content(response.content)

    def test_export_xml_view_valid_version(self):
        response = self.client.get(reverse("ispdb_export_xml",
                                   args=["1.0", "1"]), {})
        check_content(response.content)

    def test_export_xml_view_invalid_version(self):
        response = self.client.get(reverse("ispdb_export_xml",
                                   args=["10.0", "1"]), {})
        assert_equal(response.status_code, 404)

# -*- coding: utf-8 -*-

from cStringIO import StringIO
import datetime
import re
import xml.etree.ElementTree as ET
import zipfile

from django.test import TestCase
from django.core.urlresolvers import reverse
from nose.tools import *

from ispdb.config import models


# Utility Functions.

def make_config(value):
    "Get the dictionary for a sample config."
    return {"asking_or_adding":"adding",
            "form-TOTAL_FORMS":"1",
            "form-INITIAL_FORMS":"1",
            "form-0-name":"test%s.com" % value,
            "display_name":"test%s" % value,
            "display_short_name":"test%s" % value,
            "incoming_type":"imap",
            "incoming_hostname":"foo",
            "incoming_port":"22%s" % value,
            "incoming_socket_type":"None",
            "incoming_authentication":"plain",
            "outgoing_hostname":"bar",
            "outgoing_port":"22%s" % value,
            "outgoing_socket_type":"TLS",
            "outgoing_username_form":"%EMAILLOCALPART%",
            "outgoing_authentication":"plain",
            "settings_page_url":"google.com",
            "settings_page_language":"en",
            "confirmations":"0",
            "problems":"0"}

def check_returned_xml(response, id_count):
    "Make sure the response xml has the right values."
    assert_equal(response.status_code, 200)
    assert_equal(response["Content-Type"], "text/xml")

    content = ET.XML(response.content)
    assert_equal(len(content.findall("provider")), id_count)

    ids = content.findall("provider/id")
    assert_equal(len(ids), id_count)
    for (n,i) in enumerate(ids):
        assert_equal(int(i.text), n + 1)

    exports = content.findall("provider/export")
    assert_equal(len(exports), id_count)
    for (n,i) in enumerate(exports):
        assert_equal(i.text, "/export_xml/%d" % (n+1))

def check_returned_html(response, id_count):
    assert_equal(response.template[0].name, "config/list.html")
    configs = response.context[0]["configs"]
    assert_equal(len(configs), id_count)

class ListTest(TestCase):
    "A class to test the list view."

    test2dict = make_config("2")
    test3dict = make_config("3")

    def test_empty_xml_reponse(self):
        response = self.client.get(reverse("ispdb_list", args=["xml"]), {})
        check_returned_xml(response, 0)

    def test_single_xml_reponse(self):
        response = self.client.post(reverse("ispdb_add"), ListTest.test2dict)
        assert_equal(response.status_code,302)
        domain = models.Domain.objects.get(name="test2.com")
        assert isinstance(domain,models.Domain)

        response = self.client.post(reverse("ispdb_approve",
                                            kwargs={"id":domain.id}),
                                    {"approved":"mark valid",
                                     "comment":"Always enter a comment here"})
        response = self.client.get(reverse("ispdb_list", args=["xml"]), {})
        check_returned_xml(response, 1)

    def test_two_xml_reponses(self):
        response = self.client.post(reverse("ispdb_add"), ListTest.test2dict)
        domain = models.Domain.objects.get(name="test2.com")
        response = self.client.post(reverse("ispdb_approve",
                                            kwargs={"id":domain.id}),
                                    {"approved":"mark valid",
                                     "comment":"I liked this domain"})

        response = self.client.post(reverse("ispdb_add"), ListTest.test3dict)
        domain = models.Domain.objects.get(name="test3.com")
        response = self.client.post(reverse("ispdb_approve",
                                            kwargs={"id":domain.id}),
                                    {"denied":"mark invalid",
                                     "comment":"I didn't like this domain"})
        response = self.client.get(reverse("ispdb_list", args=["xml"]), {})
        check_returned_xml(response, 2)

    def test_empty_reponse(self):
        response = self.client.get(reverse("ispdb_list"), {})
        check_returned_html(response, 0)

    def test_single_reponse(self):
        response = self.client.post(reverse("ispdb_add"), ListTest.test2dict)
        assert_equal(response.status_code,302)
        domain = models.Domain.objects.get(name="test2.com")
        assert isinstance(domain,models.Domain)

        response = self.client.post(reverse("ispdb_approve",
                                            kwargs={"id":domain.id}),
                                    {"approved":"mark valid",
                                     "comment":"Always enter a comment here"})
        response = self.client.get(reverse("ispdb_list"), {})
        check_returned_html(response, 1)

    def test_two_xml_reponses(self):
        response = self.client.post(reverse("ispdb_add"), ListTest.test2dict)
        domain = models.Domain.objects.get(name="test2.com")
        response = self.client.post(reverse("ispdb_approve",
                                            kwargs={"id":domain.id}),
                                    {"approved":"mark valid",
                                     "comment":"I liked this domain"})

        response = self.client.post(reverse("ispdb_add"), ListTest.test3dict)
        domain = models.Domain.objects.get(name="test3.com")
        response = self.client.post(reverse("ispdb_approve",
                                            kwargs={"id":domain.id}),
                                    {"denied":"mark invalid",
                                     "comment":"I didn't like this domain"})
        response = self.client.get(reverse("ispdb_list"), {})
        check_returned_html(response, 2)

# -*- coding: utf-8 -*-

import datetime
import httplib
from django.test import TestCase
from django.core.urlresolvers import reverse
from nose.tools import *
from ispdb.config import models

# Redirect to /add/ on success
success_code = httplib.FOUND
# Return with form errors if form is invalid
fail_code = httplib.OK

class AddTest(TestCase):
    def test_ask(self):
        self.client.post(reverse("ispdb_add"), asking_domain_form())
        domain = models.UnclaimedDomain.objects.get(name="test.com")
        assert isinstance(domain, models.UnclaimedDomain)

    def test_multiple_ask(self):
        asking_form = asking_domain_form()
        self.client.post(reverse("ispdb_add"), asking_form)
        domain = models.UnclaimedDomain.objects.get(name="test.com")
        assert isinstance(domain, models.UnclaimedDomain)
        assert_equal(domain.votes, 1)
        self.client.post(reverse("ispdb_add"), asking_form)
        domain = models.UnclaimedDomain.objects.get(name="test.com")
        assert isinstance(domain, models.UnclaimedDomain)
        assert_equal(domain.votes, 2)

    def test_add(self):
        domain = models.Domain.objects.filter(name="test.com")
        assert_false(domain)
        res = self.client.post(reverse("ispdb_add"), adding_domain_form())
        assert_equal(res.status_code, success_code)
        domain = models.Domain.objects.get(name="test.com")
        assert isinstance(domain, models.Domain)

    def test_add_duplicate_domain(self):
        name = "test.com"
        domain = models.Domain.objects.filter(name=name)
        assert_false(domain)
        domain_form = adding_domain_form()
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, success_code)
        domain = models.Domain.objects.filter(name=name)
        assert_true(domain)
        assert isinstance(domain[0], models.Domain)
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, fail_code)
        domain = models.Domain.objects.filter(name=name)
        assert_true(domain)

    def test_add_internationalization(self):
        name = u"Iñtërnâtiônàlizætiøn"
        dom = models.Domain.objects.filter(name=name)
        assert_false(dom)
        domain_form = adding_domain_form()
        domain_form["form-0-name"] = name
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, success_code)
        domain = models.Domain.objects.get(name=name)
        assert isinstance(domain, models.Domain)
        assert_equal(domain.name, name)

    def test_add_missing_name(self):
        domain_form = adding_domain_form()
        domain_form["display_name"] = ""
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, fail_code)
        model = models.Domain.objects.filter(name="test.com")
        assert_false(model)

    def test_add_long_port(self):
        port = "800000000000000000000000000000000000000000000000"
        domain_form = adding_domain_form()
        domain_form["incoming_port"] = port
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, fail_code)
        model = models.Domain.objects.filter(name="test.com")
        assert_false(model)

    def test_add_negative_port(self):
        port = "-1000"
        domain_form = adding_domain_form()
        domain_form["incoming_port"] = port
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, fail_code)
        model = models.Domain.objects.filter(name="test.com")
        assert_false(model)

    def test_add_letters_port(self):
        port = "11a1"
        domain_form = adding_domain_form()
        domain_form["incoming_port"] = port
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, fail_code)
        model = models.Domain.objects.filter(name="test.com")
        assert_false(model)

    def test_add_with_unconfirmed(self):
        name = "test.com"
        unclaimed_after = models.UnclaimedDomain.objects.filter(name=name)
        assert_false(unclaimed_after)

        asking_form = asking_domain_form()
        asking_form["form-0-name"] = name
        self.client.post(reverse("ispdb_add"), asking_form)
        unclaimed = models.UnclaimedDomain.objects.filter(name=name)
        assert_true(unclaimed)

        domain_form = adding_domain_form()
        domain_form["form-0-name"] = name
        self.client.post(reverse("ispdb_add"), domain_form)
        unclaimed_after = models.UnclaimedDomain.objects.filter(name=name)
        assert_false(unclaimed_after)
        model = models.Domain.objects.get(name=name)
        assert isinstance(model, models.Domain)

    def test_add_lots_of_domains(self):
        num_domains = 10
        domain_form = adding_domain_form()
        domain_form["form-TOTAL_FORMS"] = num_domains
        for i in range(num_domains):
            domain_form["form-%d-name" % i] = "test%d.com" % i
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, success_code)
        for i in range(num_domains):
            assert_true(models.Domain.objects.filter(name="test%d.com"%i))

    # Tests correct handling of a leading zero in form-TOTAL_FORMS
    def test_add_09_domains(self):
        num_domains = 9
        domain_form = adding_domain_form()
        domain_form["form-TOTAL_FORMS"] = "09"
        for i in range(num_domains):
            domain_form["form-%d-name" % i] = "test%d.com" % i
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, success_code)
        for i in range(num_domains):
            assert_true(models.Domain.objects.filter(name="test%d.com"%i))

    def test_add_aaa_domains(self):
        before = models.Domain.objects.all().count()
        domain_form = adding_domain_form()
        domain_form["form-TOTAL_FORMS"] = "aaa"
        assert_raises(ValueError,
                      self.client.post,
                      reverse("ispdb_add"),
                      domain_form)
        after = models.Domain.objects.all().count()
        assert_equal(before, after)

    def test_add_bad_number_domains(self):
        before = models.Domain.objects.all().count()
        domain_form = adding_domain_form()
        domain_form["form-TOTAL_FORMS"] = "10000"
        assert_raises(KeyError,
                      self.client.post,
                      reverse("ispdb_add"),
                      domain_form)
        after = models.Domain.objects.all().count()
        assert_equal(before, after)

def asking_domain_form():
    return {"asking_or_adding":"asking",
            "form-TOTAL_FORMS":"1",
            "form-INITIAL_FORMS":"1",
            "form-0-name":"test.com"}

def adding_domain_form():
    return {"asking_or_adding":"adding",
            "form-TOTAL_FORMS":"1",
            "form-INITIAL_FORMS":"1",
            "form-0-name":"test.com",
            "display_name":"test",
            "display_short_name":"test",
            "incoming_type":"imap",
            "incoming_hostname":"foo",
            "incoming_port":"333",
            "incoming_socket_type":"plain",
            "incoming_authentication":"plain",
            "outgoing_hostname":"bar",
            "outgoing_port":"334",
            "outgoing_socket_type":"STARTTLS",
            "outgoing_username_form":"%25EMAILLOCALPART%25",
            "outgoing_authentication":"plain",
            "settings_page_url":"google.com",
            "settings_page_language":"en",
            "confirmations":"0",
            "problems":"0"}

class ModelTest(TestCase):
    def test_simple_domain(self):
        config = models.Config(id="1",
                               incoming_port=1,
                               outgoing_port=2,
                               created_datetime=datetime.datetime.now())
        config.save()
        d = models.Domain(name="test", votes=1, config=config)
        d.save()
        domain = models.Domain.objects.get(name="test")
        assert isinstance(domain, models.Domain)

    def test_internationalization_domain(self):
        name = u"Iñtërnâtiônàlizætiøn"
        config = models.Config(id="1",
                               incoming_port=1,
                               outgoing_port=2,
                               created_datetime=datetime.datetime.now())
        config.save()
        d = models.Domain(name=name, votes=1, config=config)
        d.save()
        domain = models.Domain.objects.get(name=name)
        assert isinstance(domain, models.Domain)

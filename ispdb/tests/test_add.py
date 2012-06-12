# -*- coding: utf-8 -*-

import datetime
import httplib
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.forms import ValidationError
from nose.tools import *
from ispdb.config import models

# Redirect to /add/ on success
success_code = httplib.FOUND
# Return with form errors if form is invalid
fail_code = httplib.OK

class AddTest(TestCase):
    fixtures = ['login_testdata.json']

    def test_ask(self):
        self.client.login(username='test', password='test')
        self.client.post(reverse("ispdb_add"), asking_domain_form())
        domain = models.DomainRequest.objects.get(name="test.com", config=None)
        assert isinstance(domain, models.DomainRequest)

    def test_multiple_ask(self):
        self.client.login(username='test', password='test')
        asking_form = asking_domain_form()
        self.client.post(reverse("ispdb_add"), asking_form)
        domain = models.DomainRequest.objects.get(name="test.com", config=None)
        assert isinstance(domain, models.DomainRequest)
        assert_equal(domain.votes, 1)
        self.client.post(reverse("ispdb_add"), asking_form)
        domain = models.DomainRequest.objects.get(name="test.com", config=None)
        assert isinstance(domain, models.DomainRequest)
        assert_equal(domain.votes, 2)

    def test_add(self):
        self.client.login(username='test', password='test')
        domain = models.DomainRequest.objects.filter(name="test.com")
        assert_false(domain)
        res = self.client.post(reverse("ispdb_add"), adding_domain_form())
        assert_equal(res.status_code, success_code)
        domain = models.DomainRequest.objects.get(name="test.com")
        assert isinstance(domain, models.DomainRequest)

    def test_add_duplicate_domain(self):
        self.client.login(username='test', password='test')
        name = "test.com"
        domain = models.Domain.objects.filter(name=name)
        assert_false(domain)
        domain_form = adding_domain_form()
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, success_code)
        domain = models.DomainRequest.objects.filter(name=name)
        assert_true(domain)
        assert isinstance(domain[0], models.DomainRequest)
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, success_code)
        domain = models.DomainRequest.objects.filter(name=name)
        assert_true(len(domain) == 2)

    def test_add_internationalization(self):
        self.client.login(username='test', password='test')
        domains = [
            u"Iñtërnâtiônàlizætiøn.com",
            u"郵件.商務",
            u"मोहन.ईन्फो",
            u"екзампл.ком",
            u"εχαμπλε.ψομ",
            u"ящик-с-апельсинами.рф",
        ]
        for name in domains:
            dom = models.DomainRequest.objects.filter(name=name)
            assert_false(dom)
            domain_form = adding_domain_form()
            domain_form["form-0-name"] = name
            res = self.client.post(reverse("ispdb_add"), domain_form)
            assert_equal(res.status_code, success_code)
            domain = models.DomainRequest.objects.get(name=name)
            assert isinstance(domain, models.DomainRequest)
            assert_equal(domain.name, name)

    def test_add_missing_name(self):
        self.client.login(username='test', password='test')
        domain_form = adding_domain_form()
        domain_form["display_name"] = ""
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, fail_code)
        model = models.DomainRequest.objects.filter(name="test.com")
        assert_false(model)

    def test_add_long_port(self):
        self.client.login(username='test', password='test')
        port = "800000000000000000000000000000000000000000000000"
        domain_form = adding_domain_form()
        domain_form["incoming_port"] = port
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, fail_code)
        model = models.DomainRequest.objects.filter(name="test.com")
        assert_false(model)

    def test_add_negative_port(self):
        self.client.login(username='test', password='test')
        port = "-1000"
        domain_form = adding_domain_form()
        domain_form["incoming_port"] = port
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, fail_code)
        model = models.DomainRequest.objects.filter(name="test.com")
        assert_false(model)

    def test_add_letters_port(self):
        self.client.login(username='test', password='test')
        port = "11a1"
        domain_form = adding_domain_form()
        domain_form["incoming_port"] = port
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, fail_code)
        model = models.DomainRequest.objects.filter(name="test.com")
        assert_false(model)

    def test_add_with_unconfirmed(self):
        self.client.login(username='test', password='test')
        name = "test.com"
        unclaimed_after = models.DomainRequest.objects.filter(name=name,
                                                              config=None)
        assert_false(unclaimed_after)

        asking_form = asking_domain_form()
        asking_form["form-0-name"] = name
        self.client.post(reverse("ispdb_add"), asking_form)
        unclaimed = models.DomainRequest.objects.get(name=name,
                                                     config=None)
        assert_true(unclaimed)

        domain_form = adding_domain_form()
        domain_form["form-0-name"] = name
        self.client.post(reverse("ispdb_add"), domain_form)
        unclaimed_after = models.DomainRequest.objects.filter(name=name,
                                                              config=None)
        assert_false(unclaimed_after)
        model = models.DomainRequest.objects.get(name=name)
        assert isinstance(model, models.DomainRequest)

    def test_add_lots_of_domains(self):
        self.client.login(username='test', password='test')
        num_domains = 10
        domain_form = adding_domain_form()
        domain_form["form-TOTAL_FORMS"] = num_domains
        for i in range(num_domains):
            domain_form["form-%d-name" % i] = "test%d.com" % i
            domain_form["form-%d-delete" % i] = "False"
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, success_code)
        for i in range(num_domains):
            assert_true(models.DomainRequest.objects.filter(
                name="test%d.com"%i))

    # Tests correct handling of a leading zero in form-TOTAL_FORMS
    def test_add_09_domains(self):
        self.client.login(username='test', password='test')
        num_domains = 9
        domain_form = adding_domain_form()
        domain_form["form-TOTAL_FORMS"] = "09"
        for i in range(num_domains):
            domain_form["form-%d-name" % i] = "test%d.com" % i
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, success_code)
        for i in range(num_domains):
            assert_true(models.DomainRequest.objects.filter(
                name="test%d.com"%i))

    def test_add_aaa_domains(self):
        self.client.login(username='test', password='test')
        before = models.DomainRequest.objects.all().count()
        domain_form = adding_domain_form()
        domain_form["form-TOTAL_FORMS"] = "aaa"
        assert_raises(ValidationError,
                      self.client.post,
                      reverse("ispdb_add"),
                      domain_form)
        after = models.DomainRequest.objects.all().count()
        assert_equal(before, after)

    def test_add_bad_number_domains(self):
        self.client.login(username='test', password='test')
        num_domains = 11
        domain_form = adding_domain_form()
        domain_form["form-TOTAL_FORMS"] = num_domains
        for i in range(num_domains):
            domain_form["form-%d-name" % i] = "test%d.com" % i
            domain_form["form-%d-delete" % i] = "False"
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, fail_code)
        for i in range(num_domains):
            assert_false(models.DomainRequest.objects.filter(
                name="test%d.com"%i))

    def test_add_invalid_domains(self):
        self.client.login(username='test', password='test')
        domains = [
            'test',
            'test_test.com',
            'test.c',
            100*'test'+'.com',
            '127.0.0.1',
            'example.',
            'com.',
            'invalid-.com',
            '-invalid.com',
            'inv-.alid-.com',
            'inv-.-alid.com',
            '[a',
        ]
        for domain in domains:
            domain_form = adding_domain_form()
            domain_form["form-0-name"] = domain
            res = self.client.post(reverse("ispdb_add"), domain_form)
            assert_equal(res.status_code, fail_code)
            assert_false(models.DomainRequest.objects.filter(name=domain))

    def test_add_only_deleted_domains(self):
        self.client.login(username='test', password='test')
        domain_form = adding_domain_form()
        domain_form["form-0-delete"] = "True"
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, fail_code)
        model = models.DomainRequest.objects.filter(name="test.com")
        assert_false(model)

    def test_add_one_deleted_domain(self):
        self.client.login(username='test', password='test')
        domain_form = adding_domain_form()
        domain_form["form-TOTAL_FORMS"] = "2",
        domain_form["form-0-name"] = "test.com"
        domain_form["form-0-delete"] = "True"
        domain_form["form-1-name"] = "test2.com"
        domain_form["form-1-delete"] = "False"
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, success_code)
        model = models.DomainRequest.objects.filter(name="test.com")
        assert_false(model)
        model = models.DomainRequest.objects.filter(name="test2.com")
        assert_true(model)

    def test_add_duplicated_domain_names(self):
        self.client.login(username='test', password='test')
        domain_form = adding_domain_form()
        domain_form["form-TOTAL_FORMS"] = "2",
        domain_form["form-0-name"] = "test.com"
        domain_form["form-0-delete"] = "False"
        domain_form["form-1-name"] = "test.com"
        domain_form["form-1-delete"] = "False"
        res = self.client.post(reverse("ispdb_add"), domain_form)
        assert_equal(res.status_code, fail_code)
        model = models.DomainRequest.objects.filter(name="test.com")
        assert_false(model)

def asking_domain_form():
    return {"asking_or_adding":"asking",
            "form-TOTAL_FORMS":"1",
            "form-INITIAL_FORMS":"1",
            "form-0-name":"test.com",
            "form-0-delete":"False"}

def adding_domain_form():
    return {"asking_or_adding":"adding",
            "form-TOTAL_FORMS":"1",
            "form-INITIAL_FORMS":"1",
            "form-MAX_NUM_FORMS": "10",
            "form-0-name":"test.com",
            "form-0-delete":"False",
            "display_name":"test",
            "display_short_name":"test",
            "incoming_type":"imap",
            "incoming_hostname":"foo",
            "incoming_port":"333",
            "incoming_socket_type":"plain",
            "incoming_authentication":"password-cleartext",
            "outgoing_hostname":"bar",
            "outgoing_port":"334",
            "outgoing_socket_type":"STARTTLS",
            "outgoing_username_form":"%25EMAILLOCALPART%25",
            "outgoing_authentication":"password-cleartext",
            "settings_page_url":"http://google.com/",
            "settings_page_language":"en",
            "confirmations":"0"}

class ModelTest(TestCase):
    def test_simple_domain(self):
        config = models.Config(id="1",
                               incoming_port=1,
                               outgoing_port=2,
                               created_datetime=datetime.datetime.now())
        config.save()
        d = models.Domain(name="test", config=config)
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
        d = models.Domain(name=name, config=config)
        d.save()
        domain = models.Domain.objects.get(name=name)
        assert isinstance(domain, models.Domain)

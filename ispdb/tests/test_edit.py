# -*- coding: utf-8 -*-

import httplib
from urllib import quote_plus
from django.test import TestCase
from django.core.urlresolvers import reverse
from nose.tools import *
from ispdb.config import models

# Redirect to /add/ on success
success_code = httplib.FOUND
# Return with form errors if form is invalid
fail_code = httplib.OK

class EditTest(TestCase):
    fixtures = ['login_testdata.json']

    def add_domain(self, name='test.com'):
        self.client.login(username='test', password='test')
        domain = models.DomainRequest.objects.filter(name=name)
        assert_false(domain)
        form = adding_domain_form()
        form["form-0-name"] = name
        res = self.client.post(reverse("ispdb_add"), form)
        assert_equal(res.status_code, success_code)
        domain = models.DomainRequest.objects.get(name=name)
        assert isinstance(domain, models.DomainRequest)
        self.client.logout()

    def test_edit_no_login(self):
        self.add_domain()
        res = self.client.post(reverse("ispdb_edit",args=[1]),
                               adding_domain_form(),
                               follow=True)
        # Make sure it redirects to login page
        goodRedirect = "/login/?next=%s" % (quote_plus("/edit/1"))
        self.assertRedirects(res, goodRedirect)

    def test_edit_invalid_user(self):
        self.add_domain()
        self.client.login(username='test2', password='test')
        res = self.client.post(reverse("ispdb_edit",args=[1]),
                               adding_domain_form(),
                               follow=True)
        # Make sure it redirects to login page
        goodRedirect = "/login/"
        self.assertRedirects(res, goodRedirect)

    def test_edit_same_user(self):
        self.add_domain()
        self.client.login(username='test', password='test')
        form = adding_domain_form()
        form["form-0-name"] = "test1.com"
        form["display_name"] = "testing2"
        res = self.client.post(reverse("ispdb_edit",args=[1]),
                               form,
                               follow=True)
        goodRedirect = "/details/1"
        self.assertRedirects(res, goodRedirect)
        assert_true(len(models.Config.objects.all()), 1)
        domain = models.DomainRequest.objects.get(pk=1)
        assert_true(domain)
        assert isinstance(domain, models.DomainRequest)
        assert_equal(domain.name, 'test1.com')
        assert_equal(domain.config.display_name, 'testing2')

    def test_edit_staff_user(self):
        self.add_domain()
        self.client.login(username='test_admin', password='test')
        form = adding_domain_form()
        form["form-0-name"] = "test1.com"
        form["display_name"] = "testing2"
        res = self.client.post(reverse("ispdb_edit",args=[1]),
                               form,
                               follow=True)
        goodRedirect = "/details/1"
        self.assertRedirects(res, goodRedirect)
        assert_true(len(models.Config.objects.all()), 1)
        domain = models.DomainRequest.objects.get(pk=1)
        assert_true(domain)
        assert isinstance(domain, models.DomainRequest)
        assert_equal(domain.name, 'test1.com')
        assert_equal(domain.config.display_name, 'testing2')

    def test_edit_duplicated_names(self):
        self.add_domain()
        self.client.login(username='test', password='test')
        form = adding_domain_form()
        form["form-1-name"] = "test.com"
        form["form-1-delete"] = "False"
        res = self.client.post(reverse("ispdb_edit",args=[1]),
                               form,
                               follow=True)
        assert_equal(res.status_code, fail_code)

    def test_add_existing_domain(self):
        self.add_domain(name='approved.com')
        self.add_domain()
        self.client.login(username='test_admin', password='test')
        result = self.client.post("/approve/1", {
                                  "approved": True,})
        config = models.Config.objects.get(id=1)
        assert_equal(config.status, 'approved')
        form = adding_domain_form()
        form["form-1-name"] = "approved.com"
        form["form-1-delete"] = "False"
        res = self.client.post(reverse("ispdb_edit",args=[1]),
                               form,
                               follow=True)
        assert_equal(res.status_code, fail_code)

    def test_owner_edit_approved_domain(self):
        self.add_domain(name='approved.com')
        self.client.login(username='test_admin', password='test')
        result = self.client.post("/approve/1", {
                                  "approved": True,})
        config = models.Config.objects.get(id=1)
        assert_equal(config.status, 'approved')
        self.client.logout()
        self.client.login(username='test', password='test')
        form = adding_domain_form()
        form["incoming_hostname"] = "bar"
        res = self.client.post(reverse("ispdb_edit",args=[1]),
                               form,
                               follow=True)
        goodRedirect = "/login/"
        self.assertRedirects(res, goodRedirect)

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
            "incoming_username_form":"%25EMAILLOCALPART%25",
            "outgoing_hostname":"bar",
            "outgoing_port":"334",
            "outgoing_socket_type":"STARTTLS",
            "outgoing_username_form":"%25EMAILLOCALPART%25",
            "outgoing_authentication":"password-cleartext",
            "settings_page_url":"http://google.com/",
            "settings_page_language":"en"}

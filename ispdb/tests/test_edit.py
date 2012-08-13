# -*- coding: utf-8 -*-

from urllib import quote_plus
from django.test import TestCase
from django.core.urlresolvers import reverse
from nose.tools import *
from ispdb.config import models
from ispdb.tests.common import adding_domain_form
from ispdb.tests.common import success_code, fail_code


class EditTest(TestCase):
    fixtures = ['login_testdata.json']

    def add_domain(self, name='test.com'):
        self.client.login(username='test', password='test')
        domain = models.DomainRequest.objects.filter(name=name)
        assert_false(domain)
        form = adding_domain_form()
        form["domain-0-name"] = name
        res = self.client.post(reverse("ispdb_add"), form)
        assert_equal(res.status_code, success_code)
        domain = models.DomainRequest.objects.get(name=name)
        assert isinstance(domain, models.DomainRequest)
        self.client.logout()

    def test_edit_no_login(self):
        self.add_domain()
        res = self.client.post(reverse("ispdb_edit", args=[1]),
                               adding_domain_form(),
                               follow=True)
        # Make sure it redirects to login page
        goodRedirect = "/login/?next=%s" % (quote_plus("/edit/1/"))
        self.assertRedirects(res, goodRedirect)

    def test_edit_invalid_user(self):
        self.add_domain()
        self.client.login(username='test2', password='test')
        res = self.client.post(reverse("ispdb_edit", args=[1]),
                               adding_domain_form(),
                               follow=True)
        # Make sure it redirects to login page
        goodRedirect = "/login/"
        self.assertRedirects(res, goodRedirect)

    def test_edit_locked_config(self):
        self.add_domain()
        config = models.Config.objects.get(pk=1)
        config.locked = True
        config.save()
        form = adding_domain_form()
        form["display_name"] = "testing2"
        self.client.login(username='test', password='test')
        res = self.client.post(reverse("ispdb_edit", args=[1]),
                               form,
                               follow=True)
        config = models.Config.objects.get(pk=1)
        assert_true(config.display_name != "testing2")
        assert_true("This configuration is locked. Only admins can unlock it."
            in res.content)

    def test_edit_same_user(self):
        self.add_domain()
        self.client.login(username='test', password='test')
        form = adding_domain_form()
        form["domain-INITIAL_FORMS"] = "1"
        form["domain-0-id"] = "1"
        form["domain-0-name"] = "test1.com"
        form["display_name"] = "testing2"
        form["docurl-INITIAL_FORMS"] = "1"
        form["docurl-0-id"] = "1"
        form["docurl-0-url"] = "http://test1.com/"
        form["desc_0-INITIAL_FORMS"] = "1"
        form["desc_0-0-id"] = "1"
        form["desc_0-0-description"] = "test1"
        form["enableurl-INITIAL_FORMS"] = "1"
        form["enableurl-0-id"] = "1"
        form["enableurl-0-url"] = "http://test1.com/"
        form["inst_0-INITIAL_FORMS"] = "1"
        form["inst_0-0-id"] = "1"
        form["inst_0-0-description"] = "test1"
        res = self.client.post(reverse("ispdb_edit", args=[1]),
                               form,
                               follow=True)
        goodRedirect = "/details/1/"
        self.assertRedirects(res, goodRedirect)
        assert_true(len(models.Config.objects.all()), 1)
        domain = models.DomainRequest.objects.get(pk=1)
        assert_true(domain)
        assert isinstance(domain, models.DomainRequest)
        assert_equal(domain.name, 'test1.com')
        assert_equal(domain.config.display_name, 'testing2')
        docurl = models.DocURL.objects.get(pk=1)
        assert_equal(docurl.url, 'http://test1.com/')
        desc = models.DocURLDesc.objects.get(pk=1)
        assert_equal(desc.description, 'test1')
        enableurl = models.EnableURL.objects.get(pk=1)
        assert_equal(enableurl.url, 'http://test1.com/')
        inst = models.EnableURLInst.objects.get(pk=1)
        assert_equal(inst.description, 'test1')

    def test_edit_staff_user(self):
        self.add_domain()
        self.client.login(username='test_admin', password='test')
        form = adding_domain_form()
        form["domain-INITIAL_FORMS"] = "1"
        form["domain-0-id"] = "1"
        form["domain-0-name"] = "test1.com"
        form["display_name"] = "testing2"
        form["docurl-INITIAL_FORMS"] = "1"
        form["docurl-0-id"] = "1"
        form["docurl-0-url"] = "http://test1.com/"
        form["desc_0-INITIAL_FORMS"] = "1"
        form["desc_0-0-id"] = "1"
        form["desc_0-0-description"] = "test1"
        form["enableurl-INITIAL_FORMS"] = "1"
        form["enableurl-0-id"] = "1"
        form["enableurl-0-url"] = "http://test1.com/"
        form["inst_0-INITIAL_FORMS"] = "1"
        form["inst_0-0-id"] = "1"
        form["inst_0-0-description"] = "test1"
        res = self.client.post(reverse("ispdb_edit", args=[1]),
                               form,
                               follow=True)
        goodRedirect = "/details/1/"
        self.assertRedirects(res, goodRedirect)
        assert_true(len(models.Config.objects.all()), 1)
        domain = models.DomainRequest.objects.get(pk=1)
        assert_true(domain)
        assert isinstance(domain, models.DomainRequest)
        assert_equal(domain.name, 'test1.com')
        assert_equal(domain.config.display_name, 'testing2')
        docurl = models.DocURL.objects.get(pk=1)
        assert_equal(docurl.url, 'http://test1.com/')
        desc = models.DocURLDesc.objects.get(pk=1)
        assert_equal(desc.description, 'test1')
        enableurl = models.EnableURL.objects.get(pk=1)
        assert_equal(enableurl.url, 'http://test1.com/')
        inst = models.EnableURLInst.objects.get(pk=1)
        assert_equal(inst.description, 'test1')

    def test_edit_duplicated_names(self):
        self.add_domain()
        self.client.login(username='test', password='test')
        form = adding_domain_form()
        form["domain-1-name"] = "test.com"
        form["domain-1-DELETE"] = "False"
        res = self.client.post(reverse("ispdb_edit", args=[1]),
                               form,
                               follow=True)
        assert_equal(res.status_code, fail_code)

    def test_add_existing_domain(self):
        self.add_domain(name='approved.com')
        self.add_domain()
        self.client.login(username='test_admin', password='test')
        result = self.client.post("/approve/1/", {
                                  "approved": True, })
        config = models.Config.objects.get(id=1)
        assert_equal(config.status, 'approved')
        form = adding_domain_form()
        form["domain-1-name"] = "approved.com"
        form["domain-1-DELETE"] = "False"
        res = self.client.post(reverse("ispdb_edit", args=[1]),
                               form,
                               follow=True)
        assert_equal(res.status_code, fail_code)

    def test_owner_edit_approved_domain(self):
        self.add_domain(name='approved.com')
        self.client.login(username='test_admin', password='test')
        result = self.client.post("/approve/1/", {
                                  "approved": True, })
        config = models.Config.objects.get(id=1)
        assert_equal(config.status, 'approved')
        self.client.logout()
        self.client.login(username='test', password='test')
        form = adding_domain_form()
        form["incoming_hostname"] = "bar"
        res = self.client.post(reverse("ispdb_edit", args=[1]),
                               form,
                               follow=True)
        goodRedirect = "/login/"
        self.assertRedirects(res, goodRedirect)

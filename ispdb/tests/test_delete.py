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

class DeleteTest(TestCase):
    fixtures = ['login_testdata', 'domain_testdata']

    def delete_domain(self, id):
        self.client.login(username='test_admin', password='test')
        config = models.Config.objects.get(pk=id)
        assert_true(config.status != 'deleted')
        form = deleting_domain_form()
        res = self.client.post(reverse("ispdb_delete", args=[id]), form)
        assert_equal(res.status_code, success_code)
        config = models.Config.objects.get(pk=id)
        assert_equal(config.status, 'deleted')
        self.client.logout()

    def test_delete_no_superuser_domainrequest(self):
        self.client.login(username='test', password='test')
        form = deleting_domain_form()
        res = self.client.post(reverse("ispdb_delete", args=[1]), form)
        assert_equal(res.status_code, success_code)
        config = models.Config.objects.get(pk=1)
        assert_equal(config.status, 'deleted')
        self.client.logout()

    def test_delete_no_superuser_domain(self):
        self.client.login(username='test', password='test')
        form = deleting_domain_form()
        res = self.client.post(reverse("ispdb_delete", args=[2]), form,
                                       follow=True)
        # Make sure it redirects to login page
        goodRedirect = "/login/"
        self.assertRedirects(res, goodRedirect)

    def test_delete_domainrequest(self):
        self.delete_domain(1)

    def test_delete_valid_domain(self):
        self.delete_domain(2)

    def test_delete_invalid_domain(self):
        self.delete_domain(3)

def deleting_domain_form():
    return {'confirm_delete':'1',
            'delete':'delete'}

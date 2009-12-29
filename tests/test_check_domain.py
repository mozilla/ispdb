# -*- coding: utf-8 -*-

import httplib
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson
from nose.tools import *
from ispdb.config import views,models

success_code = httplib.OK

class CheckDomainTest(TestCase):

    # contains one domain named test.com
    fixtures = ['checkdomain_testdata']

    def test_unique(self):
        domain = models.Domain.objects.filter(name="new.com")
        assert_false(domain)
        response = self.client.get(reverse("ispdb_check_domain_name",
                                           args=["new.com"]))
        assert_equal(response.status_code, success_code)
        json = simplejson.loads(response.content)
        # assert there was no errors returned
        assert_false(json)
        
    def test_not_unique(self):
        domain = models.Domain.objects.filter(name="test.com")
        assert_true(domain)
        response = self.client.get(reverse("ispdb_check_domain_name",
                                           args=["test.com"]))
        assert_equal(response.status_code, success_code)
        json = simplejson.loads(response.content)
        # assert there was a error on the name field
        assert_true(json["name"])
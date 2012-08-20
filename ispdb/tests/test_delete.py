# -*- coding: utf-8 -*-

import httplib

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone
from nose.tools import assert_equal, assert_true

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
        res = self.client.post(reverse("ispdb_delete", args=[id]),
                               {'delete': 'delete'})
        assert_equal(res.status_code, success_code)
        self.client.logout()

    def test_delete_no_superuser_domainrequest(self):
        self.client.login(username='test', password='test')
        res = self.client.post(reverse("ispdb_delete", args=[1]),
                               {'delete': 'delete'})
        assert_equal(res.status_code, success_code)
        config = models.Config.objects.get(pk=1)
        assert_equal(config.status, 'deleted')
        self.client.logout()

    def test_delete_no_superuser_domain(self):
        self.client.login(username='test', password='test')
        res = self.client.post(reverse("ispdb_delete", args=[2]),
                               {'delete': 'delete'}, follow=True)
        # Make sure it redirects to login page
        goodRedirect = "/login/"
        self.assertRedirects(res, goodRedirect)

    def test_delete_locked_config(self):
        config = models.Config.objects.get(pk=1)
        config.locked = True
        config.save()
        self.client.login(username='test_admin', password='test')
        config = models.Config.objects.get(pk=1)
        assert_true(config.status != 'deleted')
        res = self.client.post(reverse("ispdb_delete", args=[1]),
                         {'delete': 'delete'})
        self.client.logout()
        config = models.Config.objects.get(pk=1)
        assert_true(config.status != 'deleted')
        assert_true("This configuration is locked. Only admins can unlock it."
            in res.content)

    def test_delete_domainrequest(self):
        self.delete_domain(1)
        config = models.Config.objects.get(pk=1)
        assert_equal(config.status, 'deleted')

    def test_delete_valid_domain(self):
        self.delete_domain(2)
        config = models.Config.objects.get(pk=2)
        assert_equal(config.status, 'approved')

    def test_delete_invalid_domain(self):
        self.delete_domain(3)
        config = models.Config.objects.get(pk=3)
        assert_equal(config.status, 'deleted')

    def test_undo_invalid_domain_normal_user(self):
        self.delete_domain(4)
        config = models.Config.objects.get(pk=4)
        assert_equal(config.status, 'deleted')
        self.client.login(username='test', password='test')
        res = self.client.post(reverse("ispdb_delete", args=[4]),
                               {'delete': 'undo'},
                               follow=True)
        # Make sure it redirects to login page
        goodRedirect = "/login/"
        self.assertRedirects(res, goodRedirect)

    def test_undo_request_normal_user(self):
        self.delete_domain(1)
        config = models.Config.objects.get(pk=1)
        assert_equal(config.status, 'deleted')
        self.client.login(username='test', password='test')
        self.client.post(reverse("ispdb_delete", args=[1]),
                         {'delete': 'undo'},
                         follow=True)
        config = models.Config.objects.get(pk=1)
        assert_equal(config.status, 'requested')

    def test_undo_invalid_request_superuser(self):
        self.delete_domain(3)
        config = models.Config.objects.get(pk=3)
        assert_equal(config.status, 'deleted')
        self.client.login(username='test_admin', password='test')
        self.client.post(reverse("ispdb_delete", args=[3]),
                         {'delete': 'undo'},
                         follow=True)
        config = models.Config.objects.get(pk=3)
        assert_equal(config.status, 'invalid')

    def test_undo_old_config(self):
        self.delete_domain(4)
        config = models.Config.objects.get(pk=4)
        assert_equal(config.status, 'deleted')
        config.deleted_datetime = timezone.datetime(2000, 10, 10,
                                                    tzinfo=timezone.utc)
        config.save()
        self.client.login(username='test_admin', password='test')
        self.client.post(reverse("ispdb_delete", args=[4]),
                         {'delete': 'undo'},
                         follow=True)
        config = models.Config.objects.get(pk=4)
        assert_equal(config.status, 'deleted')

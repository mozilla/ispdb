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

class IssueTest(TestCase):
    fixtures = ['login_testdata', 'domain_testdata']

    def add_issue(self, updated_config=False, config_id=2):
        self.client.login(username='test', password='test')
        issue = models.Issue.objects.filter(title='Test')
        assert_false(issue)
        form = adding_issue_form()
        if updated_config:
            form['show_form'] = 'True'
        res = self.client.post(reverse("ispdb_report", args=[config_id]), form)
        assert_equal(res.status_code, success_code)
        issue = models.Issue.objects.get(title='Test')
        assert isinstance(issue, models.Issue)
        assert_equal(issue.updated_config != None, updated_config)
        self.client.logout()

    def test_add_issue_no_login(self):
        res = self.client.post(reverse("ispdb_report",args=[2]),
                               adding_issue_form(),
                               follow=True)
        # Make sure it redirects to login page
        goodRedirect = "/login/?next=%s" % (quote_plus("/report/2"))
        self.assertRedirects(res, goodRedirect)

    def test_add_issue(self):
        self.add_issue()

    def test_add_issue_with_updated_config(self):
        self.add_issue(updated_config=True)

    def test_close_issue_normal_user(self):
        self.add_issue()
        self.client.login(username='test', password='test')
        res = self.client.post(reverse("ispdb_show_issue",args=[1]),
                               {"action":"close"},
                               follow=True)
        issue = models.Issue.objects.get(title='Test')
        assert_equal(issue.status, "open")
        # Make sure it redirects to login page
        goodRedirect = "/login/"
        self.assertRedirects(res, goodRedirect)

    def test_close_issue_superuser(self):
        self.add_issue()
        self.client.login(username='test_admin', password='test')
        res = self.client.post(reverse("ispdb_show_issue",args=[1]),
                               {"action":"close"},
                               follow=True)
        issue = models.Issue.objects.get(title='Test')
        assert_equal(issue.status, "closed")

    def test_merge_issue_normal_user(self):
        self.add_issue(updated_config=True)
        self.client.login(username='test', password='test')
        res = self.client.post(reverse("ispdb_show_issue",args=[1]),
                               {"action":"merge"},
                               follow=True)
        issue = models.Issue.objects.get(title='Test')
        assert_equal(issue.status, "open")
        # Make sure it redirects to login page
        goodRedirect = "/login/"
        self.assertRedirects(res, goodRedirect)

    def test_merge_issue_superuser(self):
        self.add_issue(updated_config=True)
        self.client.login(username='test_admin', password='test')
        res = self.client.post(reverse("ispdb_show_issue",args=[1]),
                               {"action":"merge"},
                               follow=True)
        issue = models.Issue.objects.get(title='Test')
        assert_equal(issue.status, "closed")
        assert_equal("test.com", issue.config.domains.all()[0].name)
        assert_equal(issue.config.display_name, "Test")

def adding_issue_form():
    return {
            "form-TOTAL_FORMS":"2",
            "form-INITIAL_FORMS":"1",
            "form-MAX_NUM_FORMS": "10",
            "form-0-name":"validdomain.com",
            "form-0-delete":"True",
            "form-1-name":"test.com",
            "form-1-delete":"False",
            "outgoing_username_form": "Valid Domain",
            "incoming_socket_type": "plain",
            "outgoing_port": 587,
            "incoming_authentication": "password-encrypted",
            "display_name": "Test",
            "outgoing_socket_type": "plain",
            "outgoing_authentication": "password-encrypted",
            "incoming_hostname": "Valid Domain",
            "settings_page_url": "http://teste.com/",
            "display_short_name": "Valid Domain",
            "incoming_port": 143,
            "settings_page_language": "en",
            "outgoing_hostname": "Valid Domain",
            "incoming_type": "imap",
            "show_form":"False",
            "title":"Test",
            "description":"Test",
            "asking_or_adding":"adding",
           }

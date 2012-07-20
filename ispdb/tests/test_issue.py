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
    fixtures = ['login_testdata', 'issue_testdata']

    def add_issue(self, updated_config=False, config_id=1):
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
        assert_equal(issue.config.display_name, "Test")
        assert_equal(1, len(issue.config.domains.all()))
        assert_equal("test2.com", issue.config.domains.all()[0].name)
        assert_equal(1, len(issue.config.docurl_set.all()))
        docurl = issue.config.docurl_set.all()[0]
        assert_equal("http://test2.com/", docurl.url)
        assert_equal(len(docurl.descriptions.all()), 1)

def adding_issue_form():
    return {
            "domain-TOTAL_FORMS":"2",
            "domain-INITIAL_FORMS":"1",
            "domain-MAX_NUM_FORMS": "10",
            "domain-0-id":"1",
            "domain-0-name":"test.com",
            "domain-0-DELETE":"True",
            "domain-1-id":"",
            "domain-1-name":"test2.com",
            "domain-1-DELETE":"False",
            "incoming_username_form":"%EMAILLOCALPART%",
            "outgoing_username_form":"%EMAILLOCALPART%",
            "incoming_socket_type": "plain",
            "outgoing_port": 587,
            "incoming_authentication": "password-encrypted",
            "display_name": "Test",
            "outgoing_socket_type": "plain",
            "outgoing_authentication": "password-encrypted",
            "incoming_hostname": "test.com",
            "display_short_name": "Test",
            "incoming_port": 143,
            "outgoing_hostname": "test.com",
            "incoming_type": "imap",
            "docurl-INITIAL_FORMS": "1",
            "docurl-TOTAL_FORMS": "2",
            "docurl-MAX_NUM_FORMS": "",
            "docurl-0-id": "1",
            "docurl-0-DELETE": "True",
            "docurl-0-url": "http://test.com/",
            "desc_0-INITIAL_FORMS": "1",
            "desc_0-TOTAL_FORMS": "1",
            "desc_0-MAX_NUM_FORMS": "",
            "desc_0-0-id": "1",
            "desc_0-0-DELETE": "False",
            "desc_0-0-language": "en",
            "desc_0-0-description": "test",
            "docurl-1-id": "",
            "docurl-1-DELETE": "False",
            "docurl-1-url": "http://test2.com/",
            "desc_1-INITIAL_FORMS": "0",
            "desc_1-TOTAL_FORMS": "2",
            "desc_1-MAX_NUM_FORMS": "",
            "desc_1-0-id": "",
            "desc_1-0-DELETE": "False",
            "desc_1-0-language": "fr",
            "desc_1-0-description": "test2",
            "desc_1-1-id": "",
            "desc_1-1-DELETE": "True",
            "desc_1-1-language": "en",
            "desc_1-1-description": "test3",
            "show_form":"False",
            "title":"Test",
            "description":"Test",
            "asking_or_adding":"adding",
           }

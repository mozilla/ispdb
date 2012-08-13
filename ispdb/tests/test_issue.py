# -*- coding: utf-8 -*-

from urllib import quote_plus
from django.test import TestCase
from django.core.urlresolvers import reverse
from nose.tools import *
from ispdb.config import models
from ispdb.tests.common import adding_domain_form
from ispdb.tests.common import success_code, fail_code


def adding_issue_form():
    form = adding_domain_form()
    form['show_form'] = 'False'
    form['title'] = 'Test'
    form['description'] = 'Test'
    return form


class IssueTest(TestCase):
    fixtures = ['login_testdata', 'issue_testdata']

    def add_issue(self, updated_config=False, config_id=1):
        self.client.login(username='test', password='test')
        issue = models.Issue.objects.filter(title='Test')
        assert_false(issue)
        form = adding_issue_form()
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
        if updated_config:
            form['show_form'] = 'True'
        res = self.client.post(reverse("ispdb_report", args=[config_id]), form)
        assert_equal(res.status_code, success_code)
        issue = models.Issue.objects.get(title='Test')
        assert isinstance(issue, models.Issue)
        assert_equal(issue.updated_config != None, updated_config)
        self.client.logout()

    def test_add_issue_no_login(self):
        res = self.client.post(reverse("ispdb_report", args=[2]),
                               adding_issue_form(),
                               follow=True)
        # Make sure it redirects to login page
        goodRedirect = "/login/?next=%s" % (quote_plus("/report/2/"))
        self.assertRedirects(res, goodRedirect)

    def test_add_issue(self):
        self.add_issue()

    def test_add_issue_with_updated_config(self):
        self.add_issue(updated_config=True)

    def test_close_issue_normal_user(self):
        self.add_issue()
        self.client.login(username='test', password='test')
        res = self.client.post(reverse("ispdb_show_issue", args=[1]),
                               {"action": "close"},
                               follow=True)
        issue = models.Issue.objects.get(title='Test')
        assert_equal(issue.status, "open")
        # Make sure it redirects to login page
        goodRedirect = "/login/"
        self.assertRedirects(res, goodRedirect)

    def test_close_issue_superuser(self):
        self.add_issue()
        self.client.login(username='test_admin', password='test')
        res = self.client.post(reverse("ispdb_show_issue", args=[1]),
                               {"action": "close"},
                               follow=True)
        issue = models.Issue.objects.get(title='Test')
        assert_equal(issue.status, "closed")

    def test_merge_issue_normal_user(self):
        self.add_issue(updated_config=True)
        self.client.login(username='test', password='test')
        res = self.client.post(reverse("ispdb_show_issue", args=[1]),
                               {"action": "merge"},
                               follow=True)
        issue = models.Issue.objects.get(title='Test')
        assert_equal(issue.status, "open")
        # Make sure it redirects to login page
        goodRedirect = "/login/"
        self.assertRedirects(res, goodRedirect)

    def test_merge_locked_config(self):
        self.add_issue(updated_config=True)
        issue = models.Issue.objects.get(title='Test')
        issue.config.locked = True
        issue.config.save()
        self.client.login(username='test_admin', password='test')
        res = self.client.post(reverse("ispdb_show_issue", args=[1]),
                               {"action": "merge"},
                               follow=True)
        issue = models.Issue.objects.get(title='Test')
        assert_equal(issue.status, "open")
        assert_true(issue.config.display_name != "testing2")
        assert_true("This configuration is locked. Only admins can unlock it."
            in res.content)

    def test_merge_issue_superuser(self):
        self.add_issue(updated_config=True)
        self.client.login(username='test_admin', password='test')
        res = self.client.post(reverse("ispdb_show_issue", args=[1]),
                               {"action": "merge"},
                               follow=True)
        issue = models.Issue.objects.get(title='Test')
        assert_equal(issue.status, "closed")
        assert_equal(issue.config.display_name, "testing2")
        assert_equal(1, len(issue.config.domains.all()))
        assert_equal("test1.com", issue.config.domains.all()[0].name)
        # doc url
        assert_equal(len(issue.config.docurl_set.all()), 1)
        docurl = issue.config.docurl_set.all()[0]
        assert_equal(docurl.url, 'http://test1.com/')
        assert_equal(len(docurl.descriptions.all()), 1)
        desc = docurl.descriptions.all()[0]
        assert_equal(desc.description, 'test1')
        # enable URL
        assert_equal(len(issue.config.enableurl_set.all()), 1)
        enableurl = issue.config.enableurl_set.all()[0]
        assert_equal(enableurl.url, 'http://test1.com/')
        assert_equal(len(enableurl.instructions.all()), 1)
        inst = enableurl.instructions.all()[0]
        assert_equal(inst.description, 'test1')

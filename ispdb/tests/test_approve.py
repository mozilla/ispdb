from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from ispdb.config import views, models
from ispdb.config.models import Config
from urllib import quote_plus
from nose.tools import *

class ApproveTest(TestCase):
    fixtures = ['xml_testdata', 'login_testdata']

    def test_unauthenticated_user(self):
        result = self.client.post("/approve/1", {
                                "approved": True,
                            }, follow=True)
        config = Config.objects.get(id=1)
        # Should not have changed the config
        assert_equal(config.status, 'requested')
        # Make sure it redirects to login page
        redirect = result.redirect_chain[0][0]
        goodRedirect = "/login/?next=%s" % (quote_plus("/approve/1"))
        self.assertRedirects(result, goodRedirect)

    def test_locked_config(self):
        user_info = {"username": "test_admin", "password": "test"}
        self.client.login(**user_info)
        config = Config.objects.get(id=1)
        config.locked = True
        config.save()
        result = self.client.post("/approve/1", {
                                "approved": True,
                            }, follow=True)
        config = Config.objects.get(id=1)
        # Should not have changed the config
        assert_equal(config.status, 'requested')
        assert_true("This configuration is locked. Only admins can unlock it."
            in result.content)

    def test_authenticated_user(self):
        user_info = {"username": "test_admin", "password": "test"}
        self.client.login(**user_info)
        result = self.client.post("/approve/1", {
                                "approved": True,
                                "comment": "Test",
                            }, follow=True)
        config = Config.objects.get(id=1)
        # Should have changed the config
        assert_equal(config.status, 'approved')
        # Make sure it redirects to details page
        redirect = result.redirect_chain[0][0]
        goodRedirect = "/details/1"
        self.assertRedirects(result, goodRedirect)
        comment = Comment.objects.get(pk=1)
        assert_equal(int(comment.object_pk), config.pk)

    def test_authenticated_user_deny_no_comment(self):
        user_info = {"username": "test_admin", "password": "test"}
        self.client.login(**user_info)
        result = self.client.post("/approve/1", {
                                      "denied": True,
                                      "comment": 'Other - invalid',
                                      "commenttext": "",
                                  }, follow=True)

        config = Config.objects.get(id=1)
        # Should not have changed the config status because no comment was
        # supplied
        assert_equal(config.status, 'requested')

    def test_authenticated_user_deny_comment(self):
        user_info = {"username": "test_admin", "password": "test"}
        self.client.login(**user_info)
        result = self.client.post("/approve/1", {
                                      "denied": True,
                                      "comment": 'Other - invalid',
                                      "commenttext": "Test",
                                  }, follow=True)

        config = Config.objects.get(id=1)
        assert_equal(config.status, 'invalid')

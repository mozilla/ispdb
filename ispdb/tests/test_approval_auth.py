from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from ispdb.config import views, models
from ispdb.config.models import Config
from urllib import quote_plus

import nose.tools


class ApprovalAuthTest(TestCase):
    fixtures = ['xml_testdata', 'approval_user']

    def test_unauthenticated_user(self):
        result = self.client.post("/approve/1", {
                                "approved": True,
                            }, follow=True)

        config = Config.objects.get(id=1)

        # Should not have changed the config
        nose.tools.assert_equal(config.status, 'requested')

        # Make sure it redirects to login page
        redirect = result.redirect_chain[0][0]
        goodRedirect = "/login/?next=%s" % (quote_plus("/approve/1"))

        self.assertRedirects(result, goodRedirect)

        # Used after bug 522251 has been fixed
        # Assert config.comments.count() == 0

    def test_authenticated_user(self):
        user_info = {"username": "testuser", "password": "simplepassword"}

        self.client.login(**user_info)

        result = self.client.post("/approve/1", {
                                "approved": True,
                            }, follow=True)

        config = Config.objects.get(id=1)

        # Should have changed the config
        nose.tools.assert_equal(config.status, 'approved')

        # Make sure it redirects to details page
        redirect = result.redirect_chain[0][0]
        goodRedirect = "/details/1"

        self.assertRedirects(result, goodRedirect)

        # TODO(ehenry5): Used after bug 522251 has been fixed
        # Assert config.comments.count() == 1

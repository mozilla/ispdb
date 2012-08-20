# -*- coding: utf-8 -*-

from datetime import datetime
from nose.tools import assert_true

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.timezone import utc

from ispdb.config.models import Config


class CacheTest(TestCase):

    fixtures = ['login_testdata', 'xml_testdata']

    def test_default_cache(self):
        res = self.client.get(reverse("ispdb_list"))
        assert_true('Cache-Control' in res)
        assert_true(res['Cache-Control'] == 'max-age=600')

    def test_list_xml_cache(self):
        res = self.client.get(reverse("ispdb_list", args=['xml']))
        assert_true('Cache-Control' in res)
        assert_true(res['Cache-Control'] == 'no-cache, max-age=600')
        config = Config.objects.get(pk=1)
        assert_true('Last-Modified' in res)
        d = datetime.strptime(res['Last-Modified'], "%a, %d %b %Y %H:%M:%S "
            "%Z").replace(tzinfo=utc)
        c = config.last_update_datetime.replace(microsecond=0)
        assert_true(d == c)

    def test_export_xml_cache(self):
        res = self.client.get(reverse("ispdb_export_xml", args=[2]))
        assert_true('Cache-Control' in res)
        assert_true(res['Cache-Control'] == 'no-cache, max-age=600')
        config = Config.objects.get(pk=2)
        assert_true('Last-Modified' in res)
        d = datetime.strptime(res['Last-Modified'], "%a, %d %b %Y %H:%M:%S "
            "%Z").replace(tzinfo=utc)
        c = config.last_update_datetime.replace(microsecond=0)
        assert_true(d == c)

# -*- coding: utf-8 -*-
from base import LmfdbTest
from flask import url_for
import unittest2

class PermalinkTest(LmfdbTest):

    """
    the following tests check if the url_for() actually gives
    what we expect
    """

    def ec(self):
        assert url_for('by_ec_label', label='17.a3') == '/EllipticCurve/Q/17.a3'


class RootTest(LmfdbTest):

    def test_root(self):
        root = self.tc.get("/")
        assert "database" in root.data

    def test_robots(self):
        r = self.tc.get("/static/robots.txt")
        assert "Disallow: /static" in r.data

    def test_favicon(self):
        assert len(self.tc.get("/favicon.ico").data) > 10

    def test_javscript(self):
        js = self.tc.get("/static/lmfdb.js").data
        # click handler def for knowls
        assert '''$("body").on("click", "*[knowl]", function(evt)''' in js

    def test_css(self):
        css = self.tc.get("/style.css").data
        # def for knowls:
        assert '*[knowl]' in css
        assert 'border-bottom: 1px dotted grey;' in css

    @unittest2.skip("Tests all url_maps, but fails at the moment because of other errors")
    def test_url_map(self):
        """

        """
        for rule in self.app.url_map.iter_rules():
            if "GET" in rule.methods:
                tc = self.app.test_client()
                res = tc.get(rule.rule)
                assert "Database" in res.data, "rule %s failed " % rule

    @unittest2.skip("Tests for latex errors, but fails at the moment because of other errors")
    def test_some_latex_error(self):
        """
          Tests for latex errors, but fails at the moment because of other errors
        """
        for rule in self.app.url_map.iter_rules():
            if "GET" in rule.methods:
                try:
                    tc = self.app.test_client()
                    res = tc.get(rule.rule)
                    assert not ("Undefined control sequence" in res.data), "rule %s failed" % rule
                except KeyError:
                    pass

    random_urls = ["/ModularForm/GL2/Q/Maass/"]

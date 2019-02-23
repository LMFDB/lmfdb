# -*- coding: utf-8 -*-


from lmfdb.tests import LmfdbTest
import unittest2


class SpellingTest(LmfdbTest):
    # this tests the spelling on the website

    @unittest2.skip("Tests for 'zeroes' should be 'zeros', but fails at the moment because of other errors")
    def test_zeroes_spelling(self):
        """
            'zeroes' should be 'zeros'
        """
        for rule in self.app.url_map.iter_rules():

            if "GET" in rule.methods:
                try:
                    tc = self.app.test_client()
                    res = tc.get(rule.rule)
                    assert not ("zeroes" in res.data), "rule %s failed " % rule
                except KeyError:
                    pass

    # This test isn't going to work, because 'Maas' is in 'Maass'.
    # If someone wants it to work correctly, they are going to have
    # to write it better.

    #def test_maass_spelling(self):
    #    """
    #        'Maass', not anything else
    #    """
    #    for rule in self.app.url_map.iter_rules():
    #
    #        if "GET" in rule.methods:
    #            try:
    #                tc = self.app.test_client()
    #                res = tc.get(rule.rule)
    #                assert not ("maas" in res.data), "rule %s failed " % rule
    #                assert not ("mass" in res.data), "rule %s failed " % rule
    #                assert not ("Maas" in res.data), "rule %s failed " % rule
    #                assert not ("Mass" in res.data), "rule %s failed " % rule
    #            except KeyError:
    #                pass

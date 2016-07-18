# -*- coding: utf8 -*-
# testing users blueprint
from lmfdb.base import LmfdbTest


class KnowlTestCase(LmfdbTest):

    def test_knowls_need_to_have_title_and_content(self):
        knowls = self.C.knowledge.knowls
        a = knowls.find({'title': {"$exists": True}}).count()
        b = knowls.find({'content': {"$exists": True}}).count()
        e = knowls.find().count()
        assert a == e, "%s knowl(s) don't have a title" % (e - a)
        assert b == e, "%s knowl(s) don't have a content" % (e - b)

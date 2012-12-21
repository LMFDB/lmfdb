# -*- coding: utf8 -*-
# testing users blueprint
from base import LmfdbTest
from flask import url_for


class KnowlTestCase(LmfdbTest):

    def knowls_need_to_have_title_and_content(self):
        a = knowls.find({'title': {"$exists": True}}).count()
        b = knowls.find({'content': {"$exists": True}}).count()
        e = knowls.find().count()
        assert a == e, "%s knowl(s) don't have a title" % (e - a)
        assert b == e, "%s knowl(s) don't have a content" % (e - b)

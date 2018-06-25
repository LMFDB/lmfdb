# -*- coding: utf-8 -*-
# testing users blueprint
from lmfdb.base import LmfdbTest
from lmfdb.knowledge.knowl import knowldb

class KnowlTestCase(LmfdbTest):

    def test_knowls_need_to_have_title_and_content(self):
        knowldb.check_title_and_content()

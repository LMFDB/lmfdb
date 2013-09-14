
from lmfdb.base import LmfdbTest

from flask import request

from views.emf_main import *


class CmfTest(LmfdbTest):
    def test_get_args(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/10/0/")
        assert '24936' in page.data

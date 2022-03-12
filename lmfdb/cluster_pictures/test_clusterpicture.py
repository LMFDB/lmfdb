# -*- coding: utf-8 -*-
from lmfdb.tests import LmfdbTest


class ClusterPictureTest(LmfdbTest):
    # All tests should pass
    def test_clusters(self):
        self.check_args('/Genus2Curve/Q/762001/a/762001/1', r'c4c2_1~2_0')
        self.check_args('/knowledge/show/clusterpicture.data?label=c4c2_1~2_0', r'Potential toric rank')
        self.check_args('/knowledge/show/clusterpicture.data?label=c4c2_1~2_0', r'6')

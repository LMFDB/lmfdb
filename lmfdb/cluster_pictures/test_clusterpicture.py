from lmfdb.tests import LmfdbTest


class ClusterPictureTest(LmfdbTest):
    # All tests should pass
    def test_clusters(self):
        from lmfdb import db
        if not db.g2c_tamagawa_new.count():
            # cluster picture labels on curve pages come from the tamagawa table
            self.skipTest("g2c_tamagawa_new not yet loaded on devmirror")
        self.check_args('/Genus2Curve/Q/762001/a/762001/1', r'c4c2_1~2_0')
        self.check_args('/knowledge/show/clusterpicture.data?label=c4c2_1~2_0', r'Potential toric rank')
        self.check_args('/knowledge/show/clusterpicture.data?label=c4c2_1~2_0', r'6')

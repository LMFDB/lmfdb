from lmfdb.base import LmfdbTest
from lmfdb.db_backend import db

class ECNFTest(LmfdbTest):

    def runTest():
        pass

    def test_d6_pages(self):
        # check the page of every elliptic curve over a degree 6 field
        errors = []
        n = db.ec_nfcurves.count({'degree':6})
        print "Checking %d elliptic curves over number fields of degree 6"%(n)
        for e in db.ec_nfcurves.search({'degree':6}):
            url = "EllipticCurve/%s/%d"%("/".join(e['class_label'].split("-")),e['number'])
            print "Checking " + url
            page = self.tc.get(url, follow_redirects=True)
            if not e['label'] in page.data or not 'Weierstrass equation' in page.data:
                print 'Failed on', url
                errors.append(url)
        if errors:
            print "Errors occurred for the following URLs: ", errors
        assert not errors

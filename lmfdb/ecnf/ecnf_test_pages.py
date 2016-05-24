from lmfdb.base import LmfdbTest, getDBConnection

from flask import request
import unittest2

class ECNFTest(LmfdbTest):

    def runTest():
        pass

    def test_d6_pages(self):
        # check the page of every elliptic curve over a degree 6 field
        errors = []
        nfcurves = getDBConnection().elliptic_curves.nfcurves
        data = nfcurves.find({'degree':int(6)})
        print "Checking %d elliptic curves over number fields of degree 6"%(data.count())
        for e in data:
            url = "EllipticCurve/%s/%d"%("/".join(e['class_label'].split("-")),e['number'])
            print "Checking " + url
            page = self.tc.get(url, follow_redirects=True)
            if not e['label'] in page.data or not 'Weierstrass equation' in page.data:
                print 'Failed on', url
                errors.append(url)
        if errors:
            print "Errors occurred for the following URLs: ", errors
        assert not errors

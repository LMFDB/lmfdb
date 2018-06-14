from lmfdb.base import LmfdbTest
from lmfdb.db_backend import db

class Genus2Test(LmfdbTest):

    def runTest():
        pass

    def test_all_pages(self):
        errors = []
        n = 0
        for c in db.g2c_curves.search({}, ['label','class']):
            l = c['label'].split('.')
            url = "Genus2Curve/Q/%s/%s/%s/%s"%(l[0],l[1],l[2],l[3])
            print "Checking home page for genus 2 curve " + c['label']
            try:
                n = n+1
                page = self.tc.get(url, follow_redirects=True)
                assert c['label'] in page.data
            except:
                print "Internal server error on page " + url
                errors.append(url)
                continue
            url = "Genus2Curve/Q/%s/%s/"%(l[0],l[1])
            print "Checking home page for genus 2 isogeny class " + c['class']
            try:
                n = n+1
                page = self.tc.get(url, follow_redirects=True)
                assert c['label'] in page.data
            except:
                print "Internal server error on page "+url
                errors.append(url)
                continue
        if not errors:
            print "Tested %s pages with no errors" % n
        else:
            print "Tested %d pages with %d errors occuring on the following pages:" %(n,len(errors))
            for url in errors:
                print url

# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import urllib2, ssl, errno

class HomePageTest(LmfdbTest):

    def check(self,homepage,path,text):
        assert path in homepage
        assert text in self.tc.get(path).data

    def check_external(self, homepage, path, text):
        headers = {'User-Agent': 'Mozilla/5.0'}
        context = ssl._create_unverified_context()
        request = urllib2.Request(path, headers = headers)
        assert path in homepage
        assert text in urllib2.urlopen(request, context = context).read()

    # All tests should pass
    #
    # The acknowledgments page
    def test_acknowledgements(self):
        homepage = self.tc.get("/acknowledgment").data
        assert 'American Institute of Mathematics' in homepage

    #
    # Link to workshops page
    def test_workshops(self):
        homepage = self.tc.get("/acknowledgment/activities").data
        assert 'Computational Aspects of the Langlands Program' in homepage
    #
    # External Links on workshops page
    def test_workshoplinks(self):
        homepage = self.tc.get("/acknowledgment/activities").data
        self.check_external(homepage,
                "http://people.oregonstate.edu/~swisherh/CRTNTconference/index.html",
                'Galois')
        self.check_external(homepage,
                "http://www2.warwick.ac.uk/fac/sci/maths/research/events/2013-2014/nonsymp/lmfdb/",
                'elliptic curves over number fields' )
        try:
            self.check_external(homepage,
                "https://hobbes.la.asu.edu/lmfdb-14/",
                'Arizona State University' )
        except urllib2.URLError, e:
            if e.errno in [errno.ETIMEDOUT, errno.ECONNREFUSED, errno.EHOSTDOWN]:
                pass;
            elif 'Connection refused' in str(e): # not every error comes with a errno
                pass;
            else:
                print e
                print e.errno
                raise

        self.check_external(homepage,
                "http://www.maths.bris.ac.uk/~maarb/public/lmfdb2013.html",
                'Development of algorithms')
        self.check_external(homepage,
                #"http://icms.org.uk/workshops/onlinedatabases"
                "https://aimath.org/pastworkshops/onlinedata.html"
                ,'development of new software tools' )
        self.check_external(homepage, "http://www.msri.org/programs/262",
                'algebraic number fields')
        self.check_external(homepage,
                "http://aimath.org/pastworkshops/lfunctionsandmf.html",
                'L-functions and modular forms')


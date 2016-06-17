from lmfdb.base import LmfdbTest, getDBConnection

class SMFPageTest(LmfdbTest):

    def runTest():
        pass

    def test_all_pages(self):
        errors = []
        samples = getDBConnection().siegel_modular_forms.experimental_samples
        data = samples.find({'collection':{'$exists':True},'name':{'$exists':True}},{'_id':False,'collection':True,'name':True})
        n = 0
        print ""
        for s in data:
            label = s['collection'][0] + "." + s['name']
            url = "/ModularForm/GSp/Q/"+label+"/"
            print "Checking home page for SMF sample " + label
            try:
                n = n+1
                page = self.tc.get(url, follow_redirects=True)
                assert label in page.data and "Hecke eigenform?" in page.data
            except:
                print "Error on page " + url
                errors.append(url)
                continue
        if not errors:
            print "Tested %s pages with no errors" % n
        else:
            print "Tested %d pages with %d errors occuring on the following pages:" %(n,len(errors))
            for url in errors:
                print url

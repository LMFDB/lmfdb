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
            full_label = s['collection'][0] + "." + s['name']
            url = "/ModularForm/GSp/Q/"+full_label+"/"
            print "Checking home page for SMF sample " + full_label
            try:
                n = n+1
                page = self.tc.get(url, follow_redirects=True)
                data = page.data.decode('utf-8')
                assert full_label in data and "Hecke eigenform" in data
            except:
                print "Error on page " + url
                errors.append(url)
                continue
            print "Got %d bytes" % len(page.data)
            label = s['collection'][0]
            url = "/ModularForm/GSp/Q/"+label+"/"
            print "Checking home page for SMF sample family " + label
            try:
                n = n+1
                page = self.tc.get(url, follow_redirects=True)
                data = page.data.decode('utf-8')
                assert full_label in data and "Available samples" in data
            except:
                print "Error on page " + url
                print page.data
                errors.append(url)
            print "Got %d bytes" % len(page.data)
        if not errors:
            print "Tested %s pages with no errors" % n
        else:
            print "Tested %d pages with %d errors occuring on the following pages:" %(n,len(errors))
            for url in errors:
                print url

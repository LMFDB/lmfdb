from lmfdb.base import LmfdbTest, getDBConnection

class BelyiTest(LmfdbTest):

    def runTest():
        pass

    def test_all_pages(self):
        errors = []
        passports = getDBConnection().belyi.curves
        gal_maps = getDBConnection().belyi.gal_maps
        gal_maps_data = gal_maps.find({},{'_id':False,'label':True,})
        passports_data = passports.find({},{'_id':False,'label':True,})
        n = 0
        for c in gal_maps_data:
            l = c['label'].split('-')
            url = "Belyi/%s/%s/%s/%s/%s/%s/%s"%(l[0],l[1],l[2],l[3],l[4],l[5],l[6])
            print "Checking home page for Belyi map" + c['label']
            try:
                n = n+1
                page = self.tc.get(url, follow_redirects=True)
                assert c['label'] in page.data
            except:
                print "Internal server error on page " + url
                errors.append(url)
                continue
            url = "Belyi/%s/%s/%s/%s/%s/%s/%s"%(l[0],l[1],l[2],l[3],l[4],l[5])
            print "Checking home page for Belyi Passport " + c['class']
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

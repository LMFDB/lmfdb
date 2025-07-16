from lmfdb.tests import LmfdbTest


class LocalFieldTest(LmfdbTest):

    # All tests should pass
    #
    def test_search_ramif_cl_deg(self):
        L = self.tc.get('/padicField/?n=8&c=24&gal=8T5&p=2&e=8&count=20')
        assert '4 matches' in L.get_data(as_text=True)

    def test_search_f(self):
        L = self.tc.get('/padicField/?n=6&p=2&f=3')
        dat = L.get_data(as_text=True)
        assert '2.2.3.4a1.1' not in dat
        assert '2.3.2.6a1.2' in dat

    def test_search_top_slope(self):
        L = self.tc.get('/padicField/?p=2&topslope=3.5')
        assert '2.1.4.9a1.1' in L.get_data(as_text=True) # number of matches
        L = self.tc.get('/padicField/?p=2&topslope=3.4..3.55')
        assert '2.1.4.9a1.1' in L.get_data(as_text=True) # number of matches
        L = self.tc.get('/padicField/?p=2&topslope=7/2')
        assert '2.1.4.9a1.1' in L.get_data(as_text=True) # number of matches

    def test_field_page(self):
        L = self.tc.get('/padicField/11.6.4.2', follow_redirects=True)
        assert '11.2.3.4a1.1' in L.get_data(as_text=True)
        assert 'x^{2} + 7 x + 2' in L.get_data(as_text=True) # bad (not robust) test, but it's the best i was able to find...
        assert 'x^{3} + 44 t + 99' in L.get_data(as_text=True) # bad (not robust) test, but it's the best i was able to find...

    def test_global_splitting_models(self):
        # The first one will have to change if we compute a GSM for it
        L = self.tc.get('/padicField/163.1.8.7a1.2')
        assert 'not computed' in L.get_data(as_text=True)
        L = self.tc.get('/padicField/2.8.1.0a1.1')
        assert 'Does not exist' in L.get_data(as_text=True)

    def test_underlying_data(self):
        page = self.tc.get('/padicField/11.2.3.4a1.2').get_data(as_text=True)
        assert 'Underlying data' in page and 'data/11.2.3.4a1.2' in page

    def test_search_download(self):
        page = self.tc.get('/padicField/?Submit=gp&download=1&query=%7B%27p%27%3A+2%2C+%27n%27%3A+2%7D&n=2&p=2').get_data(as_text=True)
        assert '''columns = ["label", "coeffs", "p", "f", "e", "c", "gal", "slopes"];
data = {[
["2.2.1.0a1.1", [1, 1, 1], 2, 2, 1, 0, [2, 1], [[], 1, 2]],
["2.1.2.2a1.1", [2, 2, 1], 2, 1, 2, 2, [2, 1], [[2], 1, 1]],
["2.1.2.2a1.2", [6, 2, 1], 2, 1, 2, 2, [2, 1], [[2], 1, 1]],
["2.1.2.3a1.1", [2, 0, 1], 2, 1, 2, 3, [2, 1], [[3], 1, 1]],
["2.1.2.3a1.2", [10, 0, 1], 2, 1, 2, 3, [2, 1], [[3], 1, 1]],
["2.1.2.3a1.3", [2, 4, 1], 2, 1, 2, 3, [2, 1], [[3], 1, 1]],
["2.1.2.3a1.4", [10, 4, 1], 2, 1, 2, 3, [2, 1], [[3], 1, 1]]
]};

create_record(row) =
{
    out = Map(["label",row[1];"coeffs",row[2];"p",row[3];"f",row[4];"e",row[5];"c",row[6];"gal",row[7];"slopes",row[8]]);
    field = Polrev(mapget(out, "coeffs"));
    mapput(~out, "field", field);
    return(out);''' in page

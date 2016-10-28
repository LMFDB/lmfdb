from lmfdb.base import LmfdbTest

class AVTest(LmfdbTest):

    def check_args(self, path, text):
        assert text in self.tc.get(path, follow_redirects=True).data
        

    # All tests should pass

    def test_frob_angles(self):
        self.check_args("/Variety/Abelian/Fq/3/4/ab_a_i",'0.206216850513')
        
    
        
    # test for ending backslash?
    #def test_bad_label(self):
    

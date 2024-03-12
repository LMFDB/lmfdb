from lmfdb.tests import LmfdbTest

class ModCrvTest(LmfdbTest):
    def test_home(self):
        L = self.tc.get('/ModularCurve/Q/')
        assert 'Modular curves' in L.get_data(as_text=True)
        assert 'Browse' in L.get_data(as_text=True)
        assert 'Search' in L.get_data(as_text=True)
        assert 'Find' in L.get_data(as_text=True)
        assert 'X_0(N)' in L.get_data(as_text=True)

    def test_level_range(self):
        L = self.tc.get("/ModularCurve/Q/?level=10-100")
        assert "10.2.0.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?level_type=prime&level=10-100")
        assert "11.12.1.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?level_type=prime_power&level=25-100")
        assert "25.30.0.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?level_type=squarefree&level=49-150")
        assert "51.6.0.a.1" in L.get_data(as_text=True)
             
    def test_level_search(self):
        L = self.tc.get("/ModularCurve/Q/?level=13")
        assert "13.14.0.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?level_type=prime&level=23")
        assert "23.24.2.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?level_type=prime&level=22")
        assert "No matches" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?level_type=prime_power&level=169")
        assert "169.182.8.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?level_type=squarefree&level=74")
        assert "74.2.0.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?start=0&level_type=divides&level=15")
        assert "15.12.0.b.2" in L.get_data(as_text=True)

    def test_index_range(self):
        L = self.tc.get("/ModularCurve/Q/?index=100-1000")
        assert "6.144.1-6.b.1.1" in L.get_data(as_text=True)
        
    def test_index_search(self):
        L = self.tc.get("/ModularCurve/Q/?index=42")
        assert "7.42.1.a.1" in L.get_data(as_text=True)
    
    def test_genus_range(self):
        L = self.tc.get("/ModularCurve/Q/?genus=10-1000")
        assert "9.648.10-9.a.1.2" in L.get_data(as_text=True)
        
    def test_genus_search(self):
        L = self.tc.get("/ModularCurve/Q/?genus=25")
        assert "12.576.25.a.1" in L.get_data(as_text=True)
    
    def test_rank_range(self):
        L = self.tc.get("/ModularCurve/Q/?rank=20-200")
        assert "13.1092.50.d.1" in L.get_data(as_text=True)
        
    def test_rank_search(self):
        L = self.tc.get("/ModularCurve/Q/?rank=10")
        assert "16.768.41.q.1" in L.get_data(as_text=True)
    
    def test_genus_minus_rank_range(self):
        L = self.tc.get("/ModularCurve/Q/?genus_minus_rank=2-5")
        assert "7.168.3.a.1" in L.get_data(as_text=True)
        
    def test_genus_minus_rank_search(self):
        L = self.tc.get("/ModularCurve/Q/?genus_minus_rank=30")
        assert "15.720.37.h.1" in L.get_data(as_text=True)
    
    def test_Q_gonality_search(self):
        L = self.tc.get("/ModularCurve/Q/?q_gonality=4")
        assert "8.192.3-8.d.1.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?gonality_type=possibly&q_gonality=8")
        assert "10.360.13.b.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?gonality_type=atleast&q_gonality=7")
        assert "11.660.26.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?count=None&gonality_type=atmost&q_gonality=3")
        assert "1.1.0.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?gonality_type=atmost&q_gonality=3-4")
        assert "is not a valid input for" in L.get_data(as_text=True)
    
    def test_cusps_range(self):
        L = self.tc.get("/ModularCurve/Q/?cusps=48-60")
        assert "11.660.26.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?rational_cusps=100-1000")
        assert "211.22260.1751.by.1" in L.get_data(as_text=True)
        
    def test_cusps_search(self):
        L = self.tc.get("/ModularCurve/Q/?cusps=6")
        assert "4.24.0.a.1" in L.get_data(as_text=True)
        
    def test_rational_CM_points_search(self):
        L = self.tc.get("/ModularCurve/Q/?cm_discriminants=yes")
        assert "3.3.0.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?cm_discriminants=no")
        assert "4.24.0.b.1" in L.get_data(as_text=True)
        # Fails due to slow query
        # L = self.tc.get("/ModularCurve/Q/?cm_discriminants=-27")
        # assert "6.8.0-3.a.1.1" in L.get_data(as_text=True)
        
    def test_elliptic_points_order_2_search(self):
        L = self.tc.get("/ModularCurve/Q/?nu2=2")
        assert "4.6.0.e.1" in L.get_data(as_text=True)
    
    def test_elliptic_points_order_3_search(self):
        L = self.tc.get("/ModularCurve/Q/?nu3=10")
        assert "25.100.4.a.1" in L.get_data(as_text=True)
    
    def test_SL2_level(self):
        L = self.tc.get("/ModularCurve/Q/252.432.10-126.dk.1.10",follow_redirects=True)
        assert (
            "$\SL_2$-level" in L.get_data(as_text=True)
            and "$36$" in L.get_data(as_text=True)
            )

    def test_PSL2_index(self):
        L = self.tc.get("/ModularCurve/Q/60.1152.25-60.dh.4.24",follow_redirects=True)
        assert (
            "$\PSL_2$-index" in L.get_data(as_text=True)
            and "$576$" in L.get_data(as_text=True)
            )

    def test_cusp_widths(self):
        L = self.tc.get("/ModularCurve/Q/252.432.10-126.dk.1.10",follow_redirects=True)
        assert (
            "Cusp widths" in L.get_data(as_text=True)
            and "$6^{9}\cdot18^{9}$" in L.get_data(as_text=True)
            )

    def test_newform_level(self):
        L = self.tc.get("/ModularCurve/Q/48.9216.321-48.fnp.1.1",follow_redirects=True)
        assert (
            "Newform level" in L.get_data(as_text=True)
            and "$2304$" in L.get_data(as_text=True)
            )

    def test_cusp_orbits(self):
        L = self.tc.get("/ModularCurve/Q/60.8640.313-60.eqq.1.4",follow_redirects=True)
        assert (
            "Cusp orbits" in L.get_data(as_text=True)
            and "$8^{6}\cdot16^{3}$" in L.get_data(as_text=True)
            )
        
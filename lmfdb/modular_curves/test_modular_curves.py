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
            r"$\SL_2$-level" in L.get_data(as_text=True)
            and "$36$" in L.get_data(as_text=True)
            )

    def test_PSL2_index(self):
        L = self.tc.get("/ModularCurve/Q/60.1152.25-60.dh.4.24",follow_redirects=True)
        assert (
            r"$\PSL_2$-index" in L.get_data(as_text=True)
            and "$576$" in L.get_data(as_text=True)
            )

    def test_cusp_widths(self):
        L = self.tc.get("/ModularCurve/Q/252.432.10-126.dk.1.10",follow_redirects=True)
        assert (
            "Cusp widths" in L.get_data(as_text=True)
            and r"$6^{9}\cdot18^{9}$" in L.get_data(as_text=True)
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
            and r"$8^{6}\cdot16^{3}$" in L.get_data(as_text=True)
            )

    def test_modcrv_label(self):
        L = self.tc.get("/ModularCurve/Q/48.576.21-48.bqz.1.2",follow_redirects=True)
        assert (
            "Cummins and Pauli (CP) label" in L.get_data(as_text=True)
            and "48P21" in L.get_data(as_text=True)
            and "Rouse, Sutherland, and Zureick-Brown (RSZB) label" in L.get_data(as_text=True)
            and "48.576.21.26699"in L.get_data(as_text=True)
        )

    def test_GL2ZNZ_gens(self):
        L = self.tc.get("/ModularCurve/Q/240.288.8-48.jt.2.31",follow_redirects=True)
        assert (
            r"$\GL_2(\Z/240\Z)$-generators" in L.get_data(as_text=True)
            and r"$\begin{bmatrix}31&amp;54\\156&amp;217\end{bmatrix}$" in L.get_data(as_text=True)
            and r"$\begin{bmatrix}110&amp;141\\191&amp;100\end{bmatrix}$" in L.get_data(as_text=True)
            and r"$\begin{bmatrix}132&amp;227\\7&amp;168\end{bmatrix}$" in L.get_data(as_text=True)
            and r"$\begin{bmatrix}164&amp;137\\171&amp;10\end{bmatrix}$" in L.get_data(as_text=True)
            and r"$\begin{bmatrix}181&amp;150\\154&amp;113\end{bmatrix}$" in L.get_data(as_text=True)
            and r"$\begin{bmatrix}191&amp;226\\34&amp;151\end{bmatrix}$" in L.get_data(as_text=True)
        )

    def test_GL2ZNZ_subgroup(self):
        L = self.tc.get("/ModularCurve/Q/40.2880.97-40.blq.2.11",follow_redirects=True)
        assert (
            r"$\GL_2(\Z/40\Z)$-subgroup" in L.get_data(as_text=True)
            and "$C_2^5.D_4$" in L.get_data(as_text=True)
        )

    def test_contains_negative_one_search(self):
        L = self.tc.get("/ModularCurve/Q/?contains_negative_one=yes")
        assert "4.2.0.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?contains_negative_one=no")
        assert "3.24.0-3.a.1.1" in L.get_data(as_text=True)

    def test_cyclic_isogeny_field_degree(self):
        L = self.tc.get("/ModularCurve/Q/252.432.10-126.dk.1.10",follow_redirects=True)
        assert (
            "Cyclic 252-isogeny field degree" in L.get_data(as_text=True)
            and "$48$" in L.get_data(as_text=True)
        )

    def test_cyclic_torsion_field_degree(self):
        L = self.tc.get("/ModularCurve/Q/168.144.4-168.lh.1.28",follow_redirects=True)
        assert (
            "Cyclic 168-torsion field degree" in L.get_data(as_text=True)
            and "$1536$" in L.get_data(as_text=True)
        )

    def test_full_torsion_field_degree(self):
        L = self.tc.get("/ModularCurve/Q/60.2304.81-60.hp.2.4",follow_redirects=True)
        assert (
            "Full 60-torsion field degree" in L.get_data(as_text=True)
            and "$960$" in L.get_data(as_text=True)
        )

    def test_conductor(self):
        L = self.tc.get("/ModularCurve/Q/48.4608.161-48.blz.2.8",follow_redirects=True)
        assert (
            "Conductor" in L.get_data(as_text=True)
            and r"$2^{981}\cdot3^{256}$" in L.get_data(as_text=True)
        )

    def test_is_simple(self):
        L = self.tc.get("/ModularCurve/Q/48.3072.97-48.bmv.8.32",follow_redirects=True)
        assert (
            "Simple" in L.get_data(as_text=True)
        )

    def test_is_squarefree(self):
        L = self.tc.get("/ModularCurve/Q/120.192.1-120.sp.4.13",follow_redirects=True)
        assert (
            "Squarefree" in L.get_data(as_text=True)
        )

    def test_isogeny_decomposition(self):
        L = self.tc.get("/ModularCurve/Q/48.6144.193-48.td.4.12",follow_redirects=True)
        assert (
            "Decomposition" in L.get_data(as_text=True)
            and r"$1^{49}\cdot2^{32}\cdot4^{20}$" in L.get_data(as_text=True)
        )

    def test_newforms(self):
        L = self.tc.get("/ModularCurve/Q/64.3072.113-64.do.2.4",follow_redirects=True)
        assert (
            "Newforms" in L.get_data(as_text=True)
            and r'href="/ModularForm/GL2/Q/holomorphic/16/2/e/a/">16.2.e.a</a>$^{2}$' in L.get_data(as_text=True)
        )

    def test_modcrv_model(self):
        L = self.tc.get("/ModularCurve/Q/180.216.4-18.e.2.8",follow_redirects=True)
        assert (
            "Canonical model" in L.get_data(as_text=True)
            and "$ 12x^{2}+3xy+3y^{2}-z^{2}+zw-w^{2}$" in L.get_data(as_text=True)
            and "Singular plane model" in L.get_data(as_text=True)
            and "$ -2008x^{6}+456x^{5}y+192x^{5}z+408x^{4}y^{2}-564x^{4}yz+324x^{4}z^{2}-79x^{3}y^{3}+129x^{3}y^{2}z-72x^{3}yz^{2}-51x^{3}z^{3}-60x^{2}y^{4}+186x^{2}y^{3}z-189x^{2}y^{2}z^{2}+45x^{2}yz^{3}-18x^{2}z^{4}-12xy^{5}+51xy^{4}z-54xy^{3}z^{2}+9xy^{2}z^{3}+9xyz^{4}-y^{6}+6y^{5}z-9y^{4}z^{2}-3y^{3}z^{3}+9y^{2}z^{4}$" in L.get_data(as_text=True)
        )

    def test_rational_points(self):
        L = self.tc.get("/ModularCurve/Q/48.1152.81.mov.1/",follow_redirects=True)
        assert (
            "Rational points" in L.get_data(as_text=True)
            and r"This modular curve has 2 rational cusps but no known non-cuspidal rational points." in L.get_data(as_text=True)
        )
        L = self.tc.get("/ModularCurve/Q/168.144.3-12.i.1.3",follow_redirects=True)
        assert (
            "Rational points" in L.get_data(as_text=True)
            and "Embedded model" in L.get_data(as_text=True)
            and r"$(1:1:0:0:0)$, $(0:0:0:-1:1)$, $(0:0:1:1:0)$, $(0:0:1/2:1:0)$" in L.get_data(as_text=True)
        )

    def test_obstructions_search(self):
        L = self.tc.get("/ModularCurve/Q/?has_obstruction=yes")
        assert "3.6.0.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?has_obstruction=not_yes")
        assert "1.1.0.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?has_obstruction=no")
        assert "2.2.0.a.1" in L.get_data(as_text=True)

    def test_j_points_range(self):
        L = self.tc.get("/ModularCurve/Q/?points=10-50")
        assert "4.24.0.c.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?points_type=noncm&points=20-40")
        assert "8.12.0.f.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?points_type=all&points=30-60")
        assert "4.24.0.c.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?points_type=all&points=30-60")
        assert "4.24.0.c.1" in L.get_data(as_text=True)

    def test_fiber_product_of_search(self):
        L = self.tc.get("/ModularCurve/Q/?factor=3.8.0-3.a.1.1")
        assert "6.16.0-6.a.1.1" in L.get_data(as_text=True)

    def test_fiber_product_of(self):
        L = self.tc.get("/ModularCurve/Q/10.15.1.a.1",follow_redirects=True)
        assert (
            "Fiber product" in L.get_data(as_text=True)
            and "$X_0(2)$" in L.get_data(as_text=True)
            and "$X_{S_4}(5)$" in L.get_data(as_text=True)
        )

    # Fails due to slow query.
    # def test_minimally_covers_search(self):
    #     L = self.tc.get("/ModularCurve/Q/?covers=13.14.0.a.1")
    #     assert "39.28.0.a.2" in L.get_data(as_text=True)

    def test_minimally_covers(self):
        L = self.tc.get("/ModularCurve/Q/31.192.6-31.a.1.1",follow_redirects=True)
        assert (
            "minimally covers" in L.get_data(as_text=True)
            and "31.64.2-31.a.1.2" in L.get_data(as_text=True)
        )

    def test_minimally_covered_by_search(self):
        L = self.tc.get("/ModularCurve/Q/?covered_by=16.48.3.a.2")
        assert "8.24.1.b.1" in L.get_data(as_text=True)

    def test_minimally_covered_by(self):
        L = self.tc.get("/ModularCurve/Q/40.2304.65-40.mm.4.13",follow_redirects=True)
        covering_curve_urls_set = [
            '/ModularCurve/Q/40.4608.129-40.cf.3.6',
            '/ModularCurve/Q/40.4608.129-40.cl.1.7',
            '/ModularCurve/Q/40.4608.129-40.fz.3.6',
            '/ModularCurve/Q/40.4608.129-40.gb.1.7',
            '/ModularCurve/Q/40.4608.129-40.kp.3.7',
            '/ModularCurve/Q/40.4608.129-40.kr.4.4',
            '/ModularCurve/Q/40.4608.129-40.of.3.7',
            '/ModularCurve/Q/40.4608.129-40.ol.4.6',
            '/ModularCurve/Q/40.11520.385-40.nw.1.13'
        ]
        for url in covering_curve_urls_set:
            L1 = self.tc.get(url)
            assert (
                url[15:] in L.get_data(as_text=True)
                and url[15:] in L1.get_data(as_text=True)
            )

    def test_family_search(self):
        family_set = [
            ('X0','2.3.0.a.1'),
            ('X1','4.12.0-4.c.1.1'),
            ('Xpm1','5.12.0.a.1'),
            ('X','2.6.0.a.1'),
            ('X2','4.24.0-4.b.1.3'),
            ('Xpm2','6.24.0.a.1'),
            ('Xsp','3.12.0.a.1'),
            ('Xns','3.6.0.a.1'),
            ('Xspplus','3.6.0.b.1'),
            ('Xnsplus','3.3.0.a.1'),
            ('XS4','5.5.0.a.1'),
            ('Xsym','4.48.0-4.b.1.1'),
            ('any','1.1.0.a.1')
        ]
        for (family,crv) in family_set:
            url = '/ModularCurve/Q/?family=' + family
            L = self.tc.get(url)
            assert crv in L.get_data(as_text=True)

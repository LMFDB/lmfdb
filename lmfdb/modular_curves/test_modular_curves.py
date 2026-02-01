from lmfdb.tests import LmfdbTest
from lmfdb.modular_curves.family import ALL_FAMILIES

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
        L = self.tc.get("/ModularCurve/Q/?cm_discriminants=-4%2C-16")
        assert "2.3.0.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?cm_discriminants=-3")
        assert "3.6.0.b.1" in L.get_data(as_text=True)

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
        assert r"$\SL_2$-level" in L.get_data(as_text=True)
        assert "$36$" in L.get_data(as_text=True)

    def test_PSL2_index(self):
        L = self.tc.get("/ModularCurve/Q/60.1152.25-60.dh.4.24",follow_redirects=True)
        assert r"$\PSL_2$-index" in L.get_data(as_text=True)
        assert "$576$" in L.get_data(as_text=True)

    def test_cusp_widths(self):
        L = self.tc.get("/ModularCurve/Q/252.432.10-126.dk.1.10",follow_redirects=True)
        assert "Cusp widths" in L.get_data(as_text=True)
        assert r"$6^{9}\cdot18^{9}$" in L.get_data(as_text=True)

    def test_newform_level(self):
        L = self.tc.get("/ModularCurve/Q/48.9216.321-48.fnp.1.1",follow_redirects=True)
        assert "Newform level" in L.get_data(as_text=True)
        assert "$2304$" in L.get_data(as_text=True)

    def test_cusp_orbits(self):
        L = self.tc.get("/ModularCurve/Q/60.8640.313-60.eqq.1.4",follow_redirects=True)
        assert "Cusp orbits" in L.get_data(as_text=True)
        assert r"$8^{6}\cdot16^{3}$" in L.get_data(as_text=True)

    def test_modcrv_label(self):
        L = self.tc.get("/ModularCurve/Q/48.576.21-48.bqz.1.2",follow_redirects=True)
        assert "Cummins and Pauli (CP) label" in L.get_data(as_text=True)
        assert "48P21" in L.get_data(as_text=True)
        assert "Rouse, Sutherland, and Zureick-Brown (RSZB) label" in L.get_data(as_text=True)
        assert "48.576.21.26699" in L.get_data(as_text=True)

    def test_GL2ZNZ_gens(self):
        L = self.tc.get("/ModularCurve/Q/240.288.8-48.jt.2.31",follow_redirects=True)
        for matrix_gens in [
            r"$\GL_2(\Z/240\Z)$-generators",
            r"$\begin{bmatrix}31&amp;54\\156&amp;217\end{bmatrix}$",
            r"$\begin{bmatrix}110&amp;141\\191&amp;100\end{bmatrix}$",
            r"$\begin{bmatrix}132&amp;227\\7&amp;168\end{bmatrix}$",
            r"$\begin{bmatrix}164&amp;137\\171&amp;10\end{bmatrix}$",
            r"$\begin{bmatrix}181&amp;150\\154&amp;113\end{bmatrix}$",
            r"$\begin{bmatrix}191&amp;226\\34&amp;151\end{bmatrix}$"
            ]:
            assert matrix_gens in L.get_data(as_text=True)

    def test_GL2ZNZ_subgroup(self):
        L = self.tc.get("/ModularCurve/Q/40.2880.97-40.blq.2.11",follow_redirects=True)
        assert r"$\GL_2(\Z/40\Z)$-subgroup" in L.get_data(as_text=True)
        assert "$C_2^5.D_4$" in L.get_data(as_text=True)

    def test_contains_negative_one_search(self):
        L = self.tc.get("/ModularCurve/Q/?contains_negative_one=yes")
        assert "4.2.0.a.1" in L.get_data(as_text=True)
        L = self.tc.get("/ModularCurve/Q/?contains_negative_one=no")
        assert "3.24.0-3.a.1.1" in L.get_data(as_text=True)

    def test_cyclic_isogeny_field_degree(self):
        L = self.tc.get("/ModularCurve/Q/252.432.10-126.dk.1.10",follow_redirects=True)
        assert "Cyclic 252-isogeny field degree" in L.get_data(as_text=True)
        assert "$48$" in L.get_data(as_text=True)

    def test_cyclic_torsion_field_degree(self):
        L = self.tc.get("/ModularCurve/Q/168.144.4-168.lh.1.28",follow_redirects=True)
        assert "Cyclic 168-torsion field degree" in L.get_data(as_text=True)
        assert "$1536$" in L.get_data(as_text=True)

    def test_full_torsion_field_degree(self):
        L = self.tc.get("/ModularCurve/Q/60.2304.81-60.hp.2.4",follow_redirects=True)
        assert "Full 60-torsion field degree" in L.get_data(as_text=True)
        assert "$960$" in L.get_data(as_text=True)

    def test_conductor(self):
        L = self.tc.get("/ModularCurve/Q/48.4608.161-48.blz.2.8",follow_redirects=True)
        assert "Conductor" in L.get_data(as_text=True)
        assert r"$2^{981}\cdot3^{256}$" in L.get_data(as_text=True)

    def test_is_simple(self):
        L = self.tc.get("/ModularCurve/Q/48.3072.97-48.bmv.8.32",follow_redirects=True)
        assert "Simple" in L.get_data(as_text=True)

    def test_is_squarefree(self):
        L = self.tc.get("/ModularCurve/Q/120.192.1-120.sp.4.13",follow_redirects=True)
        assert "Squarefree" in L.get_data(as_text=True)

    def test_isogeny_decomposition(self):
        L = self.tc.get("/ModularCurve/Q/48.6144.193-48.td.4.12",follow_redirects=True)
        assert "Decomposition" in L.get_data(as_text=True)
        assert r"$1^{49}\cdot2^{32}\cdot4^{20}$" in L.get_data(as_text=True)

    def test_newforms(self):
        L = self.tc.get("/ModularCurve/Q/64.3072.113-64.do.2.4",follow_redirects=True)
        assert "Newforms" in L.get_data(as_text=True)
        assert r'href="/ModularForm/GL2/Q/holomorphic/16/2/e/a/">16.2.e.a</a>$^{2}$' in L.get_data(as_text=True)

    def test_modcrv_model(self):
        L = self.tc.get("/ModularCurve/Q/180.216.4-18.e.2.8",follow_redirects=True)
        assert "Canonical model" in L.get_data(as_text=True)
        assert "$ 12 x^{2} + 3 x y + 3 y^{2} - z^{2} + z w - w^{2} $" in L.get_data(as_text=True)
        assert "Singular plane model" in L.get_data(as_text=True)
        assert r"$  - 2008 x^{6} + 456 x^{5} y + 192 x^{5} z + 408 x^{4} y^{2} - 564 x^{4} y z + 324 x^{4} z^{2} + \cdots  + 9 y^{2} z^{4} $" in L.get_data(as_text=True)

    def test_rational_points(self):
        data = self.tc.get("/ModularCurve/Q/48.1152.81.mov.1/",follow_redirects=True).get_data(as_text=True)
        assert "Rational points" in data
        assert r"This modular curve has 2 rational cusps but no known non-cuspidal rational points." in data
        data = self.tc.get("/ModularCurve/Q/168.144.3-12.i.1.3",follow_redirects=True).get_data(as_text=True)
        assert "Rational points" in data
        assert "Embedded model" in data
        assert r"$(1:1:0:0:0)$, $(0:0:0:-1:1)$, $(0:0:1:1:0)$, $(0:0:1/2:1:0)$" in data
        data = self.tc.get("/ModularCurve/Q/37.38.2.a.1",follow_redirects=True).get_data(as_text=True)
        assert "Elliptic curve" in data
        assert "CM" in data
        assert "$j$-invariant" in data
        assert "$j$-height" in data
        assert "Plane model" in data
        assert "Weierstrass model" in data
        assert "Embedded model" in data

    def test_low_degree_points_search(self):
        L = self.tc.get("/ModularCurve/Q/low_degree_points?cusp=no")
        assert "31752.f1" in L.get_data(as_text=True)

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
        assert "Fiber product" in L.get_data(as_text=True)
        assert "$X_0(2)$" in L.get_data(as_text=True)
        assert "$X_{S_4}(5)$" in L.get_data(as_text=True)

    # Fails due to slow query.
    # def test_minimally_covers_search(self):
    #     L = self.tc.get("/ModularCurve/Q/?covers=13.14.0.a.1")
    #     assert "39.28.0.a.2" in L.get_data(as_text=True)

    def test_minimally_covers(self):
        L = self.tc.get("/ModularCurve/Q/31.192.6-31.a.1.1",follow_redirects=True)
        assert "minimally covers" in L.get_data(as_text=True)
        assert "31.64.2-31.a.1.2" in L.get_data(as_text=True)

    def test_minimally_covered_by_search(self):
        L = self.tc.get("/ModularCurve/Q/?covered_by=16.48.3.a.2")
        assert "8.24.1.b.1" in L.get_data(as_text=True)
        # Fails due to slow query
        # L = self.tc.get("/ModularCurve/Q/?covered_by=9A11")
        # assert "not the label of a modular curve in the database" in L.get_data(as_text=True)

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
            assert url[15:] in L.get_data(as_text=True)
            assert url[15:] in L1.get_data(as_text=True)

    def test_family_page(self):
        for name, family in ALL_FAMILIES.items():
            self.check_args(
                f"/ModularCurve/Q/family/{name}",
                [
                    family.name,
                    family.genus_formula,
                    family.cusps,
                    family.psl2index,
                    family.nu2,
                    family.nu3,
                ],
            )

    def test_family_search(self):
        family_set = [
            ('X0','2.3.0.a.1'),
            ('X1','4.12.0-4.c.1.1'),
            ('Xpm1','5.12.0.a.1'),
            ('X','2.6.0.a.1'),
            ('Xarith1','4.24.0-4.b.1.3'),
            ('Xarithpm1','6.24.0.a.1'),
            ('Xsp','3.12.0.a.1'),
            ('Xns','3.6.0.a.1'),
            ('Xspplus','3.6.0.b.1'),
            ('Xnsplus','3.3.0.a.1'),
            ('XS4','5.5.0.a.1'),
            ('Xarith','4.48.0-4.b.1.1'),
            ('any','1.1.0.a.1')
        ]
        for family, crv in family_set:
            url = '/ModularCurve/Q/?family=' + family
            L = self.tc.get(url)
            assert crv in L.get_data(as_text=True)

    def test_image(self):
        L = self.tc.get("/ModularCurve/Q/280.288.17.cdv.1", follow_redirects=True)
        assert "image/png" in L.get_data(as_text=True)
        assert "Picture description" in L.get_data(as_text=True)

    def test_interesting(self):
        L = self.tc.get("/ModularCurve/interesting")
        assert "Fermat quartic" in L.get_data(as_text=True)

    def test_random(self):
        for _ in range(5):
            L = self.tc.get("/ModularCurve/Q/random", follow_redirects=True)
            assert "Label" in L.get_data(as_text=True)

    def test_jump(self):
        jump_set = [
            ('60.34560.1297-60.bwg.1.1','60.34560.1297-60.bwg.1.1'),
            ('XSP(3)','3.12.0.a.1'),
            ('Xsp%2B%2811%29','11.66.2.a.1'),
            ('32.1536.41.1175','32.1536.41-32.bz.3.6'),
            ('7B.6.2','7.24.0.b.1'),
            ('4E0-8b','8.12.0.a.1'),
            ('banana','Error: There is no modular curve in the database')
        ]
        for j,l in jump_set:
            L = self.tc.get("/ModularCurve/Q/?jump=%s" % j,follow_redirects=True)
            assert l in L.get_data(as_text=True)

    def test_related_objects(self):
        for url, friends in [
            (
                "/ModularCurve/Q/48.4608.161-48.duj.4.7",
                (
                    # Currently, isogeny/gassmann class links are not available on individual curve pages.
                    # 'Modular isogeny class 48.2304.161.duj',
                    'L-function not available',
                    'Modular curve 48.2304.161.duj.1',
                    'Modular curve 48.2304.161.duj.2',
                    'Modular curve 48.2304.161.duj.3',
                    'Modular curve 48.2304.161.duj.4',
                    'Modular curve 48.2304.161.duj.5',
                    'Modular curve 48.2304.161.duj.6',
                    'Modular curve 48.2304.161.duj.7',
                    'Modular curve 48.2304.161.duj.8',
                    'Modular curve 48.2304.161.dut.1',
                    'Modular curve 48.2304.161.dut.2',
                    'Modular curve 48.2304.161.dut.3',
                    'Modular curve 48.2304.161.dut.4',
                    'Modular curve 48.2304.161.dut.5',
                    'Modular curve 48.2304.161.dut.6',
                    'Modular curve 48.2304.161.dut.7',
                    'Modular curve 48.2304.161.dut.8'
                )
            ),
            (
                "/ModularCurve/Q/60.2880.97-60.bol.1.8",
                (
                    # Currently, isogeny/gassmann class links are not available on individual curve pages.
                    # 'Modular isogeny class 60.1440.97.bol',
                    'L-function not available',
                    'Modular curve 60.1440.97.bog.1',
                    'Modular curve 60.1440.97.bol.1'
                )
            ),
            # The next two cases come from LMFDB#5929
            (
                "/ModularCurve/Q/6.6.1.a.1",
                (
                    'Elliptic curve 36.a3',
                    'Modular form 36.2.a.a'
                )
            ),
            (
                "/ModularCurve/Q/23.24.2.a.1",
                (
                    'Isogeny class 529.a',
                    'Modular form 23.2.a.a'
                )
            )
            ]:
            data = self.tc.get(url,follow_redirects=True).get_data(as_text=True)
            for friend in friends:
                assert friend in data

    def test_download(self):
        self.tc.get("/ModularCurve/download_to_magma/60.11520.409-60.bwm.1.10")
        self.tc.get("/ModularCurve/download_to_sage/60.11520.409-60.bwm.1.10")
        self.tc.get("/ModularCurve/download_to_text/60.11520.409-60.bwm.1.10")

    def test_underlying_data(self):
        data = self.tc.get("/ModularCurve/data/56.4032.139-56.fq.1.17",follow_redirects=True).get_data(as_text=True)
        for underlying_data in [
            'CPlabel',
            'Glabel',
            'RSZBlabel',
            'RZBlabel',
            'SZlabel',
            'Slabel',
            'all_degree1_points_known',
            'bad_primes',
            'canonical_conjugator',
            'canonical_generators',
            'cm_discriminants',
            'coarse_class',
            'coarse_class_num',
            'coarse_index',
            'coarse_label',
            'coarse_level',
            'coarse_num',
            'conductor',
            'contains_negative_one',
            'curve_label',
            'cusp_orbits',
            'cusp_widths',
            'cusps',
            'determinant_label',
            'dims',
            'factorization',
            'fine_num',
            'generators',
            'genus',
            'genus_minus_rank',
            'has_obstruction',
            'index',
            'isogeny_orbits',
            'kummer_orbits',
            'label',
            'lattice_labels',
            'lattice_x',
            'level',
            'level_is_squarefree',
            'level_radical',
            'log_conductor',
            'models',
            'mults',
            'name',
            'newforms',
            'nu2',
            'nu3',
            'num_bad_primes',
            'num_known_degree1_noncm_points',
            'num_known_degree1_noncusp_points',
            'num_known_degree1_points',
            'obstructions',
            'orbits',
            'parents',
            'parents_conj',
            'pointless',
            'power',
            'psl2index',
            'psl2label',
            '56.2016.139.b.1',
            'psl2level',
            'q_gonality',
            'q_gonality_bounds',
            'qbar_gonality',
            'qbar_gonality_bounds',
            'rank',
            'rational_cusps',
            'reductions',
            'scalar_label',
            'simple',
            'sl2label',
            'sl2level',
            'squarefree',
            'trace_hash',
            'traces'
            ]:
            assert underlying_data in data

    def test_gassmann_class(self):
        data = self.tc.get("/ModularCurve/Q/40.720.49.df", follow_redirects=True).get_data(as_text=True)
        for gassmann_data in [
            'Cusp orbits',
            'Level',
            'Elliptic points',
            'Number of curves',
            'Genus',
            '20.2.a.a',
            '40.720.49.1139'
            ]:
            assert gassmann_data in data

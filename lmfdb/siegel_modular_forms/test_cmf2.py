# -*- coding: utf-8 -*-

from lmfdb.tests import LmfdbTest

from . import cmf_logger
cmf_logger.setLevel(100)


class CmfTest(LmfdbTest):
    def runTest():
        pass

    def test_download_qexp(self):
        for label, exp in [
                ['11.7.b.a', '[0, 10, 64]'],
                ['11.2.a.a', '[-2, -1, 2]'],
                ['21.2.g.a', '[0, -a - 1, 2*a - 2]'],
                ['59.2.a.a', '[-a^4 + 7*a^2 + 3*a - 5, a^4 - a^3 - 6*a^2 + 2*a + 3, a^3 - a^2 - 4*a + 3]'],
                ['13.2.e.a', '[-a - 1, 2*a - 2, a]'],
                ['340.1.ba.b', '[z, 0, z^2]'],
                ['24.3.h.a', '[-2, 3, 4]'],
                ['24.3.h.c', '[a, -1/4*a^3 - a^2 - 1/2*a - 3, a^2]'],
                ]:
            sage_code = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_qexp/%s' % label, follow_redirects=True).get_data(as_text=True)
            assert "make_data" in sage_code
            assert "aps_data" in sage_code
            sage_code += "\n\nout = str(make_data().list()[2:5])\n"
            out = self.check_sage_compiles_and_extract_var(sage_code, 'out')
            assert str(out) == exp
        for label in ['212.2.k.a', '887.2.a.b']:
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_qexp/{}'.format(label), follow_redirects=True)
            assert 'No q-expansion found for {}'.format(label) in page.get_data(as_text=True)

    def test_download(self):
        r"""
        Test download function
        """

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_traces/23.10', follow_redirects=True)
        assert '[0, 187, -11, -11, -11, -11, -11, -11, -11, -11, -11, -11, -11, -11, -11, 969023, -478731' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_traces/1161.1.i', follow_redirects=True)
        assert '[0, 14, 0, 0, -2, 0, 0, 0, 0, 0, -2, 0, 0, 1, 0, 0, -10, 0, 0, 1, 0, 0' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_traces/1161.1.i.maria.josefina', follow_redirects=True)
        assert 'Invalid label' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_traces/4021.2.mz', follow_redirects=True)
        assert 'Label not found:' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_traces/4021.2.c', follow_redirects=True)
        assert 'We have not computed traces for' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_traces/27.2.e.a', follow_redirects=True)
        assert '[0, 12, -6, -6, -6, -3, 0, -6, 6, 0, -3, 3, 12, -6, 15, 9, 0, 9, 9, -3, -3, -12, 3, -12, -18, 3, -30' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_newform/27.2.e.a', follow_redirects=True)
        assert '"analytic_rank_proved": true' in page.get_data(as_text=True)
        assert '[1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]' in page.get_data(as_text=True) # a1 (make sure qexp is there)
        assert '[1, 1, 27, 5, 1, 9, 0]' in page.get_data(as_text=True) # non-trivial inner twist
        assert '[0, 12, -6, -6, -6, -3, 0, -6, 6, 0, -3, 3, 12, -6, 15, 9, 0, 9, 9, -3, -3, -12, 3, -12, -18, 3, -30' in page.get_data(as_text=True)
        assert '1.2.3.c9' in page.get_data(as_text=True) # Sato-Tate group

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_full_space/20.5', follow_redirects = True)
        assert r"""["20.5.b.a", "20.5.d.a", "20.5.d.b", "20.5.d.c", "20.5.f.a"]""" in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_newspace/244.4.w')
        assert "[7, 31, 35, 43, 51, 55, 59, 63, 67, 71, 79, 87, 91, 115, 139, 227]" in page.get_data(as_text=True)
        assert "244.4.w" in page.get_data(as_text=True)

    def test_download_magma(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_newform_to_magma/23.1.b.a.z')
        assert 'Label not found' in page.get_data(as_text=True)

        # test MakeNewformModFrm
        for label, expected in [
                ['11.2.a.a',
                    'q - 2*q^2 - q^3 + 2*q^4 + q^5 + 2*q^6 - 2*q^7 - 2*q^9 - 2*q^10 + q^11 + O(q^12)'],
                ['21.2.g.a',
                    'q + (-nu - 1)*q^3 + (2*nu - 2)*q^4 + (-3*nu + 2)*q^7 + 3*nu*q^9 + O(q^12)'],
                ['59.2.a.a',
                    'q + (-nu^4 + 7*nu^2 + 3*nu - 5)*q^2 + (nu^4 - nu^3 - 6*nu^2 + 2*nu + 3)*q^3 + (nu^3 - nu^2 - 4*nu + 3)*q^4 + (nu^4 - 6*nu^2 - 4*nu + 3)*q^5 + (-3*nu^4 + 2*nu^3 + 17*nu^2 - 3*nu - 7)*q^6 + (-nu^2 + 3)*q^7 + (3*nu^4 - 2*nu^3 - 17*nu^2 + 3*nu + 5)*q^8 + (2*nu^4 - 13*nu^2 - 4*nu + 8)*q^9 + (3*nu^4 - 2*nu^3 - 17*nu^2 + nu + 5)*q^10 + (-4*nu^4 + 2*nu^3 + 24*nu^2 + 2*nu - 12)*q^11 + O(q^12)'],
                ['13.2.e.a',
                    'q + (-nu - 1)*q^2 + (2*nu - 2)*q^3 + nu*q^4 + (-2*nu + 1)*q^5 + (-2*nu + 4)*q^6 + (2*nu - 1)*q^8 - nu*q^9 + (3*nu - 3)*q^10 + O(q^12)'],
                ['340.1.ba.b',
                    'q + zeta_8*q^2 + zeta_8^2*q^4 - zeta_8^3*q^5 + zeta_8^3*q^8 - zeta_8*q^9 + q^10 + O(q^12)'],
                ['24.3.h.a',
                    'q - 2*q^2 + 3*q^3 + 4*q^4 + 2*q^5 - 6*q^6 - 10*q^7 - 8*q^8 + 9*q^9 - 4*q^10 - 10*q^11 + O(q^12)'],
                ['24.3.h.c',
                    'q + nu*q^2 + 1/4*(-nu^3 - 4*nu^2 - 2*nu - 12)*q^3 + nu^2*q^4 + (nu^3 + 2*nu)*q^5 + (-nu^3 + nu^2 - 3*nu + 4)*q^6 + 4*q^7 + nu^3*q^8 + 1/2*(-nu^3 - 10*nu - 10)*q^9 + (-4*nu^2 - 16)*q^10 + 1/2*(-3*nu^3 - 6*nu)*q^11 + O(q^12)'],
                ]:
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_newform_to_magma/%s' % label)
            makenewform = 'MakeNewformModFrm_%s_%s_%s_%s' % tuple(label.split('.'))
            assert makenewform in page.get_data(as_text=True)
            magma_code = page.get_data(as_text=True) + '\n' + '%s();\n' % makenewform
            self.assert_if_magma(expected, magma_code, mode='equal')

        for label, expected in [['24.3.h.a',
                    'Modular symbols space of level 24, weight 3, character Kronecker character -24, and dimension 1 over Rational Field'],
                ['24.3.h.c',
                    'Modular symbols space of level 24, weight 3, character Kronecker character -24, and dimension 4 over Rational Field'],
                ['54.2.e.a',
                    'Modular symbols space of level 54, weight 2, character $.1^16, and dimension 1 over Cyclotomic Field of order 9 and degree 6'],
                ['54.2.e.b',
                    'Modular symbols space of level 54, weight 2, character $.1^16, and dimension 2 over Cyclotomic Field of order 9 and degree 6'
                    ],
                ['212.2.k.a',
                    'Modular symbols space of level 212, weight 2, character $.1*$.2^17, and dimension 1 over Cyclotomic Field of order 52 and degree 24'
                    ]
                ]:
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_newform_to_magma/%s' % label)
            makenewform = 'MakeNewformModSym_%s_%s_%s_%s' % tuple(label.split('.'))
            assert makenewform in page.get_data(as_text=True)
            magma_code = page.get_data(as_text=True) + '\n' + '%s();\n' % makenewform
            self.assert_if_magma(expected, magma_code, mode='equal')

    def test_expression_level(self):
        # checks we can search on 2*7^2
        self.check_args('/ModularForm/GL2/Q/holomorphic/?hst=List&level=2*7%5E2&search_type=List', '98.2.a.a')

    def test_download_search(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?Submit=sage&download=1&query=%7B%27level_radical%27%3A+5%2C+%27dim%27%3A+%7B%27%24lte%27%3A+10%2C+%27%24gte%27%3A+1%7D%2C+%27weight%27%3A+10%7D&search_type=Traces', follow_redirects = True)
        assert '5.10.a.a' in page.get_data(as_text=True)
        assert '1, -8, -114, -448, -625, 912, 4242, 7680, -6687, 5000, -46208, 51072, -115934, -33936' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?Submit=sage&download=1&query=%7B%27level_radical%27%3A+5%2C+%27dim%27%3A+%7B%27%24lte%27%3A+10%2C+%27%24gte%27%3A+1%7D%2C+%27weight%27%3A+10%7D&search_type=List', follow_redirects = True)
        assert '5.10.a.a' in page.get_data(as_text=True)
        assert ('[5, 10, 1, 2.5751791808193656, [0, 1], "1.1.1.1", [], [], [-8, -114, -625, 4242]]' in page.get_data(as_text=True)) or ('[5, 10, 1, 2.57517918082, [0, 1], "1.1.1.1", [], [], [-8, -114, -625, 4242]]' in page.get_data(as_text=True)) # Different tests for py2 and py3 due to different number of digits being returned.

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?Submit=gp&download=1&query=%7B%27num_forms%27%3A+%7B%27%24gte%27%3A+1%7D%2C+%27weight%27%3A+5%2C+%27level%27%3A+20%7D&search_type=Spaces')
        for elt in ["20.5.b", "20.5.d", "20.5.f"]:
            assert elt in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?Submit=sage&download=1&query=%7B%27dim%27%3A+%7B%27%24gte%27%3A+2000%7D%2C+%27num_forms%27%3A+%7B%27%24exists%27%3A+True%7D%7D&search_type=SpaceTraces', follow_redirects=True)
        assert 'Error: We limit downloads of traces to' in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?Submit=sage&download=1&query=%7B%27dim%27%3A+%7B%27%24gte%27%3A+30000%7D%2C+%27num_forms%27%3A+%7B%27%24exists%27%3A+True%7D%7D&search_type=SpaceTraces', follow_redirects=True)
        assert '863.2.c' in page.get_data(as_text=True)

    def test_random(self):
        r"""
        Test that we don't hit any error on a random newform
        """
        def check(page):
            assert 'Newspace' in page.get_data(as_text=True), page.url
            assert 'parameters' in page.get_data(as_text=True), page.url
            assert 'Properties' in page.get_data(as_text=True), page.url
            assert 'Newform' in page.get_data(as_text=True), page.url
            assert 'expansion' in page.get_data(as_text=True), page.url
        for i in range(100):
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/random', follow_redirects = True)
            check(page)

        for w in ('1', '2', '3', '4', '5', '6-10', '11-20', '21-40', '41-'):
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?weight=%s&search_type=Random' % w, follow_redirects = True)
            check(page)
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/random?weight=%s' % w, follow_redirects = True)
            check(page)

        for l in ('1', '2-100', '101-500', '501-1000', '1001-2000', '2001-'):
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=%s&search_type=Random' % l, follow_redirects = True)
            check(page)
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/random?level=%s' % l, follow_redirects = True)
            check(page)

    def test_dimension(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=10&weight=1-14&dim=1&search_type=List', follow_redirects = True)
        assert "14 matches" in page.get_data(as_text=True)
        assert 'A-L signs' in page.get_data(as_text=True)

    def test_traces(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=244&weight=4&count=50&search_type=Traces', follow_redirects = True)
        assert "Results (18 matches)" in page.get_data(as_text=True)
        for elt in map(str,[-98,-347,739,0,147,-414,324,306,-144,0,24,-204,153,414,-344,-756,-24,164]):
            assert elt in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=244&weight=4&search_type=Traces&n=1-40&n_primality=prime_powers&an_constraints=a3%3D0%2Ca37%3D0', follow_redirects = True)
        assert "Results (3 matches)" in page.get_data(as_text=True)
        for elt in map(str,[-6,-68, 3224, 206, 4240, -408, -598, 1058]):
            assert elt in page.get_data(as_text=True)

        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?weight_parity=odd&level=7&weight=7&search_type=Traces&n=1-10&n_primality=all")
        assert "Results (4 matches)" in page.get_data(as_text=True)
        for elt in map(str,[17,0,-80,60,3780,-1200]):
            assert elt in page.get_data(as_text=True)

    def test_trivial_searches(self):
        from sage.all import Subsets
        for begin in [
                ('level=10&weight=1-20&dim=1',
                    ['Results (21 matches)', '171901114', 'No', '10.723', 'A-L signs']
                    ),
                ('level=10%2C13%2C17&weight=1-8&dim=1',
                    ['Results (12 matches)', '1373', 'No', '0.136']
                    )]:
            for s in Subsets(['has_self_twist=no', 'is_self_dual=yes', 'nf_label=1.1.1.1','char_order=1','inner_twist_count=1']):
                s = '&'.join(['/ModularForm/GL2/Q/holomorphic/?search_type=List', begin[0]] + list(s))
                page = self.tc.get(s,  follow_redirects=True)
                for elt in begin[1]:
                    assert elt in page.get_data(as_text=True), s

        for begin in [
                ('level=1-330&weight=1&projective_image=D2',
                    ['Results (49 matches)',
                        '328.1.c.a', r"\sqrt{-82}", r"\sqrt{-323}", r"\sqrt{109}"]
                    ),
                ('level=900-1000&weight=1-&projective_image=D2',
                    ['Results (26 matches)', r"\sqrt{-1}", r"\sqrt{-995}", r"\sqrt{137}"]
                    )]:
            for s in Subsets(['has_self_twist=yes', 'has_self_twist=cm', 'has_self_twist=rm',  'projective_image_type=Dn','dim=1-4']):
                s = '&'.join(['/ModularForm/GL2/Q/holomorphic/?search_type=List', begin[0]] + list(s))
                page = self.tc.get(s,  follow_redirects=True)
                for elt in begin[1]:
                    assert elt in page.get_data(as_text=True), s

    def test_parity(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?weight_parity=even&char_parity=even&search_type=List')
        assert '11.2.a.a' in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?weight_parity=odd&char_parity=odd&search_type=List')
        assert '23.1.b.a' in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?weight_parity=even&char_parity=even&weight=3&search_type=List')
        assert "No matches" in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?weight_parity=even&char_parity=odd&search_type=List')

    def test_coefficient_fields(self):
        r"""
        Test the display of coefficient fields.
        """
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/9/8/a/')
        assert r'\Q(\sqrt{10})' in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/11/6/a/')
        assert '3.3.54492.1' in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/27/2/e/a/')
        assert '12.0.1952986685049.1' in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-500&weight=2&nf_label=16.0.1048576000000000000.1&prime_quantifier=subsets&search_type=List')
        assert r'\zeta_{40}' in page.get_data(as_text=True)
        assert "Results (6 matches)" in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-4000&weight=1&nf_label=9.9.16983563041.1&prime_quantifier=subsets&projective_image=D19&search_type=List')
        assert r"Q(\zeta_{38})^+" in page.get_data(as_text=True)
        assert "Results (32 matches)" in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-100&weight=2&dim=4&nf_label=4.0.576.2&prime_quantifier=subsets&search_type=List')
        assert 'Results (7 matches)' in page.get_data(as_text=True)
        assert r'\Q(\sqrt{2}, \sqrt{-3})' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?dim=8&char_order=20&cm=no&rm=no&search_type=List')
        assert "Results (17 matches)" in page.get_data(as_text=True)
        assert r"Q(\zeta_{20})" in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-4000&weight=1&dim=116&search_type=List')
        assert "Results (displaying both matches)" in page.get_data(as_text=True)
        assert r"Q(\zeta_{177})" in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-100&weight=2&dim=4&nf_label=4.0.576.2&prime_quantifier=subsets')
        assert 'Results (7 matches)' in page.get_data(as_text=True)
        assert r'\Q(\sqrt{2}, \sqrt{-3})' in page.get_data(as_text=True)

    def test_inner_twist(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/3992/1/ba/a/')
        assert "499.g" in page.get_data(as_text=True)
        assert "3992.ba" in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/190/2/i/a/')
        for elt in ['5.b', '19.c', '95.i']:
            assert elt in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/1816/1/l/a/')
        for elt in ['227.c','1816.l']:
            assert elt in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/2955/1/c/e/')
        for elt in ['3.b','5.b','197.b','2955.c']:
            assert elt in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/52/18/a/a/')
        assert "This newform does not admit any (" in page.get_data(as_text=True)
        assert "nontrivial" in page.get_data(as_text=True)
        assert "inner twist" in page.get_data(as_text=True)

    def test_self_twist(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/2955/1/c/e/')
        for elt in [r'\Q(\sqrt{-591})', r'\Q(\sqrt{-15})', r'\Q(\sqrt{985})']:
            assert elt in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/1124/1/d/a/')
        for elt in [r'\Q(\sqrt{-281})', r'\Q(\sqrt{-1})', r'\Q(\sqrt{281})']:
            assert elt in page.get_data(as_text=True)

    def test_selft_twist_disc(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-40&weight=1-6&self_twist_discs=-3&search_type=List')
        for elt in [r'\Q(\sqrt{-39})', r'\Q(\sqrt{-3})']:
            assert elt in page.get_data(as_text=True)
        assert 'Results (22 matches)' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-100&self_twist_discs=5&search_type=List')
        for elt in [-55,-11,5,-5,-1,-95,-19]:
            assert (r'\Q(\sqrt{%d})' % elt) in page.get_data(as_text=True)
        assert 'Results (3 matches)' in page.get_data(as_text=True)
        for d in [3,-5]:
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-100&self_twist_discs=%d&search_type=List' % d)
            assert 'is not a valid input for' in page.get_data(as_text=True)

    def test_projective(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/2955/1/c/e/')
        assert 'D_{2}' in page.get_data(as_text=True)
        assert r'\Q(\sqrt{-15}, \sqrt{-591})' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/1124/1/d/a/')
        assert 'D_{2}' in page.get_data(as_text=True)
        assert r'\Q(i, \sqrt{281})' in page.get_data(as_text=True)

    def test_artin(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/2955/1/c/e/')
        assert 'Artin representation 2.3_5_197.8t11.1' in page.get_data(as_text=True)
        assert 'D_4:C_2' in page.get_data(as_text=True)
        assert '8.0.1964705625.1' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/1124/1/d/a/')
        assert 'Artin representation 2.2e2_281.4t3.2' in page.get_data(as_text=True)
        assert '4.0.4496.1' in page.get_data(as_text=True)
        assert 'D_4' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/124/1/i/a/67/1/')
        assert 'Artin representation 2.2e2_31.16t60.1c3' in page.get_data(as_text=True)
        assert 'SL(2,3):C_2' in page.get_data(as_text=True)
        assert '4.0.15376.1' in page.get_data(as_text=True)

    def test_AL_search(self):
        r"""
        Test that we display AL eigenvals/signs
        """
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=15&char_order=1&search_type=List', follow_redirects=True)
        assert 'A-L signs' in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=15&search_type=Spaces', follow_redirects=True)
        assert 'AL-dims.' in page.get_data(as_text=True)
        assert r'\(0\)+\(1\)+\(0\)+\(0\)' in page.get_data(as_text=True)

    def test_Fricke_signs_search(self):
        r"""
        Test that we display Fricke signs
        """
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=15%2C20&weight=2&dim=1&search_type=List',  follow_redirects=True)
        assert 'Fricke sign' in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?char_order=1&search_type=List',  follow_redirects=True)
        assert 'Fricke sign' in page.get_data(as_text=True)

    def displaying_weight1_search(self):
        for typ in ['List', 'Traces', 'Dimensions']:
            for search in ['weight=1', 'rm_discs=5','has_self_twist=rm','cm_discs=-3%2C+-39']:
                page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?%s&search_type=%s' % (search, typ),  follow_redirects=True)
                assert 'Only for weight 1:' in page.get_data(as_text=True)

    def test_is_self_dual(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?is_self_dual=yes&search_type=List',  follow_redirects=True)
        for elt in ['23.1.b.a', '31.1.b.a', '111.1.d.a']:
            assert elt in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?is_self_dual=no&search_type=List',  follow_redirects=True)
        for elt in ['52.1.j.a', '57.1.h.a', '111.1.h.a']:
            assert elt in page.get_data(as_text=True)

    def test_hecke_charpolys(self):
        """Test that the Hecke charpolys are correct.

        Some expected Hecke charpolys are stored in the dict test_data,
        which are then checked to be in the relevant page. These examples
        have been chosen to be readily verifiable from the displayed
        Fourier coefficients of each respective homepage."""

        test_data = {# Dimension 1
                    '11/2/a/a': {2: r'\( T + 2 \)',
                                 17: r'\( T + 2 \)',
                                 29: r'\( T \)'},

                    # Dimension 2
                    '10/3/c/a':  {5: r'\( T^{2} + 25 \)',
                                  11: r'\( (T + 8)^{2} \)',
                                  97: r'\( T^{2} + 126T + 7938 \)'},

                    # Dimension 5
                    '294/5/b/f': {2: r'\( (T^{2} + 8)^{5} \)',
                                    # The following test checks that monomials do not have superfluous parentheses
                                    7: r'\( T^{10} \)'},
                    }

        for label, some_expected_charpolys in test_data.items():
            page_as_text = self.tc.get('/ModularForm/GL2/Q/holomorphic/{}/'.format(label), follow_redirects=True).get_data(as_text=True)
            for _, expected_pth_charpoly in some_expected_charpolys.items():
                assert expected_pth_charpoly in page_as_text

        # Check large dimensions behave as we expect. The following is a form of dimension 108

        large_dimension_page_as_text = self.tc.get('/ModularForm/GL2/Q/holomorphic/671/2/i/a/', follow_redirects=True).get_data(as_text=True)
        assert "Hecke characteristic polynomials" not in large_dimension_page_as_text

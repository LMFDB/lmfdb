# -*- coding: utf-8 -*-
from lmfdb.base import LmfdbTest

class ApiTest(LmfdbTest):

    def test_api_home(self):
        r"""
        Check that the top-level api page works
        """
        data = self.tc.get("/api", follow_redirects=True).data
        assert "API for accessing the LMFDB Database" in data

    def test_api_databases(self):
        r"""
        Check that one collection from each database works
        """
        dbs = [ ['HTPicard','picard'], ['Lattices','lat'],
                ['Lfunctions','Lfunctions'],
                ['MaassWaveForms','Coefficients'],
                ['SL2Zsubgroups','groups'], ['abvar','fq_isog'],
                ['artin','representations'], ['bmfs','forms'],
                ['curve_automorphisms','passports'],
                ['elliptic_curves','curves'],
                ['genus2_curves','curves'],
                ['halfintegralmf','forms'], ['hgm','motives'],
                ['hmfs','forms'], ['localfields','fields'],
                ['mod_l_eigenvalues','modlmf'],
                ['mod_l_galois','reps'],
                ['modularforms2','dimension_table'],
                ['numberfields','fields'],
                ['sato_tate_groups','st_groups'],
                ['siegel_modular_forms','dimensions'],['transitivegroups','groups'],
                ['characters','Dirichlet_char_modl'],
                ['finite_fields','finite_fields'],
                ['hecke_algebras','hecke_algebras'],
                ['embedded_mfs','mfs'], ['belyi','passports']]
        for db, coll in dbs:
            data = self.tc.get("/api/{}/{}".format(db,coll), follow_redirects=True).data
            assert "JSON" in data

    def test_api_examples_html(self):
        r"""
        Check that the sample queries on the top page all work (html output)
        """
        queries = ['elliptic_curves/curves/?rank=i2&torsion=i5',
                   #'elliptic_curves/curves/?isogeny_matrix=py[[1,13],[13,1]]', # no index on isogeny_matrix
                   'elliptic_curves/curves/?xainvs=cs-1215&torsion_structure=ls2;2&_delim=;',
                   'knowledge/knowls/?_fields=authors,last_author',
                   'knowledge/knowls/?_fields=content,authors&_sort=timestamp']
        for query in queries:
            data = self.tc.get("/api/{}".format(query), follow_redirects=True).data
            assert 'Query: <code><a href="/api/' in data
            assert not "Error:" in data

    def test_api_examples_yaml(self):
        r"""
        Check that the sample queries on the top page all work (yaml output)
        """
        queries = [#'elliptic_curves/curves/?ainvs=ls0;1;1;-840;39800&_format=yaml&_delim=;', # no index on ainvs
                   'elliptic_curves/curves/?xainvs=s[0,1,1,-840,39800]&_format=yaml']
        for query in queries:
            data = self.tc.get("/api/{}".format(query), follow_redirects=True).data
            assert "!!python/unicode 'x-coordinates_of_integral_points': !!python/unicode '[-42,-39,-21,0,15,21,24,42,77,126,231,302,420,609,1560,3444,14595]'" in data
            assert not "Error:" in data

    def test_api_examples_json(self):
        r"""
        Check that the sample queries on the top page all work (json output)
        """
        query = 'numberfields/fields/?signature=s2,5&_format=json'
        data = self.tc.get("/api/{}".format(query), follow_redirects=True).data
        assert '"label": "12.2.167630295667.1"' in data


    def test_api_usage(self):
        r"""
        Check that the queries used by ODK demo all work
        """
        queries = ['transitivegroups/groups?_format=json&label=1T1',
                   'transitivegroups/groups?_format=json&label=8T3',
                   'elliptic_curves/curves?_format=json&label=11a1']
        for query in queries:
            data = self.tc.get("/api/{}".format(query), follow_redirects=True).data
            if '1T1' in query:
                assert '"name": "Trivial group"' in data
            if '8T3' in query:
                assert '"name": "E(8)=2[x]2[x]2"' in data
            if '11a1' in query:
                assert '"equation": "\\\\( y^2 + y = x^{3} -  x^{2} - 10 x - 20  \\\\)"' in data

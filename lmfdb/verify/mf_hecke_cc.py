
from dirichlet_conrey import DirichletGroup_conrey
from sage.all import prime_range, CC, gcd, ZZ

from lmfdb.backend.database import db, SQL, Literal, IdentifierWrapper as Identifier
from .mf import MfChecker
from .verification import overall, overall_long, slow

class mf_hecke_cc(MfChecker):
    table = db.mf_hecke_cc
    label_col = 'label'
    uniqueness_constraints = [['label']]

    @overall
    def check_hecke_orbit_code_newforms(self):
        """
        check that hecke_orbit_code is present in mf_newforms
        """
        # TIME about 200s
        return self.check_crosstable_count('mf_newforms', 1, 'hecke_orbit_code')

    @overall_long
    def check_dim(self):
        """
        check that we have dim embeddings per hecke_orbit_code
        """
        query = SQL("WITH foo AS (  SELECT hecke_orbit_code, COUNT(*) FROM mf_hecke_cc GROUP BY hecke_orbit_code) SELECT t1.label FROM mf_newforms t1, foo WHERE t1.hecke_orbit_code = foo.hecke_orbit_code AND NOT t1.dim = foo.count")
        return self._run_query(query=query)

    @overall_long
    def check_label(self):
        """
        check that label is consistent with hecke_orbit_code, conrey_label, and embedding_index
        """
        query = SQL("SELECT t1.label FROM mf_hecke_cc t1, mf_newforms t2 WHERE string_to_array(t1.label,'.') != string_to_array(t2.label, '.') || ARRAY[t1.conrey_index::text, t1.embedding_index::text] AND t1.hecke_orbit_code = t2.hecke_orbit_code")
        return self._run_query(query=query)

    @overall_long
    def check_embedding_index(self):
        """
        check that embedding_index is consistent with conrey_label and embedding_m
        """
        query = SQL("WITH foo AS ( SELECT label, embedding_index, ROW_NUMBER() OVER ( PARTITION BY hecke_orbit_code, conrey_index  ORDER BY embedding_m) FROM mf_hecke_cc) SELECT label FROM foo WHERE embedding_index != row_number")
        return self._run_query(query=query)

    @overall
    def check_embedding_m(self):
        """
        check that embedding_m is consistent with conrey_label and embedding_index
        """
        # About 250s
        query = SQL("WITH foo AS ( SELECT label, embedding_m, ROW_NUMBER() OVER ( PARTITION BY hecke_orbit_code ORDER BY conrey_index, embedding_index) FROM mf_hecke_cc) SELECT label FROM foo WHERE embedding_m != row_number")
        return self._run_query(query=query)

    @overall_long
    def check_conrey_indexes(self):
        """
        when grouped by hecke_orbit_code, check that conrey_indexs
        match conrey_indexes, embedding_index ranges from 1 to
        relative_dim (when grouped by conrey_index), and embedding_m
        ranges from 1 to dim
        """
        # ps: In check_embedding_m and check_embedding_index, we already checked that embedding_m and  check_embedding_index are in an increasing sequence
        query = SQL("WITH foo as (SELECT hecke_orbit_code, sort(array_agg(DISTINCT conrey_index)) conrey_indexes, count(DISTINCT embedding_index) relative_dim, count(embedding_m) dim FROM mf_hecke_cc GROUP BY hecke_orbit_code) SELECT t1.label FROM mf_newforms t1, foo WHERE t1.hecke_orbit_code = foo.hecke_orbit_code AND (t1.conrey_indexes != foo.conrey_indexes OR t1.relative_dim != foo.relative_dim OR t1.dim != foo.dim)")
        return self._run_query(query=query)

    @overall_long
    def check_an_length(self):
        """
        check that an_normalized is a list of pairs of doubles of length at least 1000
        """
        # TIME > 3600s
        return self._run_query(SQL("array_length({0}, 1) < 1000 OR array_length({0}, 2) != 2").format(
            Identifier("an_normalized")))

    @overall_long
    def check_angles_length(self):
        """
        check that angles is a list of length at least 168
        """
        return self.check_array_len_gte_constant('angles', 168)

    @overall_long
    def check_label_hoc(self):
        """
        check that label is consistent with hecke_orbit_code
        """
        return self._run_query(SQL("{0} != from_newform_label_to_hecke_orbit_code({1})").format(Identifier('hecke_orbit_code'), Identifier('label')))

    @overall
    def check_label_conrey(self):
        """
        check that label is consistent with conrey_lebel, embedding_index
        """
        # TIME about 230s
        return self._run_query(SQL("(string_to_array({0},'.'))[5:6] != array[{1}::text,{2}::text]").format(Identifier('label'), Identifier('conrey_index'), Identifier('embedding_index')))

    @overall_long(timeout=36000)
    def check_amn(self):
        """
        Check a_{mn} = a_m*a_n when (m,n) = 1 and m,n < some bound
        """
        pairs = [(2, 3), (2, 5), (3, 4), (2, 7), (3, 5), (2, 9), (4, 5), (3, 7), (2, 11), (3, 8), (2, 13), (4, 7), (2, 15), (3, 10), (5, 6), (3, 11), (2, 17), (5, 7), (4, 9), (2, 19), (3, 13), (5, 8), (3, 14), (6, 7), (4, 11), (5, 9), (3, 16), (3, 17), (4, 13), (5, 11), (7, 8), (3, 19), (3, 20), (4, 15), (5, 12)][:15]
        query = SQL("NOT ({0})").format(SQL(" AND ").join(SQL("check_cc_prod(an_normalized[{0}:{0}], an_normalized[{1}:{1}], an_normalized[{2}:{2}])").format(Literal(int(m)), Literal(int(n)), Literal(int(m*n))) for m, n in pairs))
        return self._run_query(query, ratio=0.1)

    @overall_long
    def check_angles_interval(self):
        """
        check that angles lie in (-0.5,0.5]
        """
        # about 20 min
        query = SQL("array_min(angles) <= -0.5 OR array_max(angles) > 0.5")
        return self._run_query(query)

    @slow(ratio=0.001, projection=['label', 'angles'])
    def check_angles(self, rec, verbose=False):
        """
        check that angles are null exactly for p dividing the level
        """
        # TIME about 200000s for full table?
        level = int(rec['label'].split('.')[0])
        for p, angle in zip(prime_range(1000), rec['angles']):
            if (level % p == 0) != (angle is None):
                if verbose:
                    print "Angle presence failure", p, ZZ(level).factor(), angle
                return False
        return True


    @slow(ratio=0.001, projection=['label', 'an_normalized'])
    def check_ap2_slow(self, rec, verbose=False):
        """
        Check a_{p^2} = a_p^2 - chi(p) for primes up to 31
        """
        ls = rec['label'].split('.')
        level, weight, chi = map(int, [ls[0], ls[1], ls[-2]])
        char = DirichletGroup_conrey(level, CC)[chi]
        Z = rec['an_normalized']
        for p in prime_range(31+1):
            if level % p != 0:
                # a_{p^2} = a_p^2 - chi(p)
                charval = CC(2*char.logvalue(int(p)) * CC.pi()*CC.gens()[0]).exp()
            else:
                charval = 0
            if (CC(*Z[p**2 - 1]) - (CC(*Z[p-1])**2 - charval)).abs() > 1e-13:
                if verbose:
                    print "ap2 failure", p, CC(*Z[p**2 - 1]), CC(*Z[p-1])**2 - charval
                return False
        return True

    @slow(ratio=0.001, projection=['label', 'an_normalized'])
    def check_amn_slow(self, rec, verbose=False):
        """
        Check that a_{pn} = a_p * a_n for p < 32 prime, n prime to p
        """
        Z = [0] + [CC(*elt) for elt in rec['an_normalized']]
        for pp in prime_range(len(Z)-1):
            for k in range(1, (len(Z) - 1)//pp + 1):
                if gcd(k, pp) == 1:
                    if (Z[pp*k] - Z[pp]*Z[k]).abs() > 1e-13:
                        if verbose:
                            print "amn failure", k, pp, Z[pp*k], Z[pp]*Z[k]
                        return False
        return True

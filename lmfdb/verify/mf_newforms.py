
from sage.all import prime_range, Integer, kronecker_symbol, PolynomialRing, ComplexField, ZZ, gap, infinity

from lmfdb.backend.database import db, SQL, Literal, IdentifierWrapper as Identifier
from lmfdb.utils import names_and_urls
from .mf import MfChecker
from .verification import overall, overall_long, slow, fast, accumulate_failures

CCC = ComplexField(200)

class mf_newforms(MfChecker):
    table = db.mf_newforms
    label = ['level', 'weight', 'char_orbit_index', 'hecke_orbit']
    label_conversion = {'char_orbit_index': -1, 'hecke_orbit': -1}
    hecke_orbit_code = ['hecke_orbit_code', label]
    uniqueness_constraints = [[table._label_col], label, ['hecke_orbit_code']]

    @overall
    def check_box_count(self):
        """
        there should be exactly one row for every newform in a box
        listed in mf_boxes with newform_count set; for each such box
        performing mf_newforms.count(box query) should match
        newform_count for box, and mf_newforms.count() should be the
        sum of these
        """
        # TIME about 15s
        total_count = 0
        for box in db.mf_boxes.search({'newform_count':{'$exists':True}}):
            bad_label = self.check_count(box['newform_count'], self._box_query(box))
            if bad_label:
                return bad_label
            total_count += box['newform_count']
        return self.check_count(total_count)

    @overall
    def check_hecke_ring_generator_nbound(self):
        """
        hecke_ring_generator_nbound > 0
        """
        return self.check_values({'hecke_ring_generator_nbound': {'$gt': 0}})

    @overall
    def check_space_label(self):
        """
        check that space_label matches level, weight, char_orbit_index
        """
        return self.check_string_concatenation('space_label', ['level', 'weight', 'char_orbit_label'])

    @overall
    def check_relative_dim(self):
        """
        check that char_degree * relative_dim = dim
        """
        return self.check_product('dim', ['char_degree', 'relative_dim'])

    @overall
    def check_newspaces_overlap(self):
        """
        check that all columns mf_newforms has in common with
        mf_newspaces other than label, dim, relative_dim, traces,
        trace_display match (this covers all atributes that depend
        only on level, weight, char) (this implies) check that
        space_label is present in mf_newspaces

        """
        # TIME > 120s
        bad_labels = []
        labels = self.check_crosstable_count('mf_newspaces', 1, 'space_label', 'label')
        bad_labels.extend([label + " (count)" for label in labels])
        for col in ['Nk2', 'analytic_conductor', 'char_conductor', 'char_degree', 'char_is_real', 'char_orbit_index', 'char_orbit_label', 'char_order', 'char_parity', 'char_values', 'conrey_indexes', 'level', 'level_is_prime', 'level_is_prime_power', 'level_is_square', 'level_is_squarefree', 'level_primes', 'level_radical', 'prim_orbit_index', 'weight', 'weight_parity']:
            labels = self.check_crosstable('mf_newspaces', col, 'space_label', col, 'label')
            bad_labels.extend([label + " (%s)"%col for label in labels])
        return bad_labels

    @overall
    def check_polredabs_set(self):
        """
        check that if nf_label is set, then is_polredabs is true
        """
        return self.check_values({'is_polredabs':True}, {'nf_label':{'$exists':True}})

    @overall
    def check_field_poly_consequences(self):
        """
        check that is_polredabs is present whenever field_poly is
        check that hecke_ring_generator_nbound is set whenever field_poly is set
        check that qexp_display is present whenever field_poly is present
        """
        return self.check_non_null(['is_polredabs', 'hecke_ring_generator_nbound', 'qexp_display'],
                                   {'field_poly': {'$exists':True}})

    @overall
    def check_field_poly(self):
        """
        if field_poly is set, check that is monic and of degree dim
        """
        return self._run_query(SQL('array_length(field_poly, 1) = 1 AND field_poly[dim + 1]  = 1'), {'field_poly': {'$exists':True}})

    @overall
    def check_traces_length(self):
        """
        check that traces is present and has length at least 1000*k for a k depending on th level
        """
        # TIME about 20s
        return (self.check_non_null(['traces']) +
                self.check_array_len_gte_constant('traces', 1000, constraint={'level':{'$lte':1000}}) +
                self.check_array_len_gte_constant('traces', 2000, constraint={'level':{'$gt':1000, '$lte':4000}}) +
                self.check_array_len_gte_constant('traces', 3000, constraint={'level':{'$gt':4000}}))

    @overall
    def check_trace_display(self):
        """
        check that trace_display is present and has length at least 4
        """
        # TIME about 150s
        return (self.check_non_null(['trace_display']) +
                self.check_array_len_gte_constant('traces', 4))

    @overall
    def check_number_field(self):
        """
        if nf_label is present, check that there is a record in
        nf_fields and that mf_newforms field_poly matches nf_fields
        coeffs, and check that is_self_dual agrees with signature, and
        field_disc agrees with disc_sign * disc_abs in nf_fields
        """
        nfyes = {'nf_label':{'exists':True}}
        selfdual = {'nf_label':{'exists':True}, 'is_self_dual':True}
        return (self.check_crosstable_count('nf_fields', 1, 'nf_label', 'label', constraint=nfyes) +
                # since coeffs is still jsonb, we must use coeffs_array
                self.check_crosstable('nf_fields', 'field_poly', 'nf_label', 'coeffs_array', 'label', constraint=nfyes) +
                self.check_crosstable('nf_fields', 0, 'nf_label', 'r2', 'label', constraint=selfdual) +
                self.check_crosstable_dotprod('nf_fields', 'field_disc', 'nf_label', ['disc_sign', 'disc_abs'], 'label', constraint=nfyes))

    @overall
    def check_field_disc(self):
        """
        if hecke_ring_index_proved is true, verify that field_disc is set
        """
        return self.check_non_null(['field_disc'], {'hecke_ring_index_proved':True})

    @overall(max_failures=2000)
    def check_analytic_rank_proved(self):
        """
        check that analytic_rank_proved is true when analytic rank set (log warning if not)
        """
        # TIME about 5s
        return list(self.table.search({'analytic_rank_proved':False, 'analytic_rank': {'$exists':True}}, 'label'))

    @overall
    def check_self_twist_type(self):
        """
        check that self_twist_type is in {0,1,2,3} and matches is_cm and is_rm
        """
        # TIME about 6s
        return (self.check_non_null(['is_cm', 'is_rm']) +
                self.check_iff({'self_twist_type':0}, {'is_cm':False, 'is_rm':False}) +
                self.check_iff({'self_twist_type':1}, {'is_cm':True, 'is_rm':False}) +
                self.check_iff({'self_twist_type':2}, {'is_cm':False, 'is_rm':True}) +
                self.check_iff({'self_twist_type':3}, {'is_cm':True, 'is_rm':True}))

    @overall
    def check_cmrm_discs(self):
        """
        check that self_twist_discs is consistent with self_twist_type
        (e.g. if self_twist_type is 3, there should be 3
        self_twist_discs, one pos, two neg)
        """
        # TIME about 10s
        return (self.check_array_len_eq_constant('rm_discs', 0, {'is_rm': False}) +
                self.check_array_len_eq_constant('rm_discs', 1, {'is_rm': True}) +
                self.check_array_len_eq_constant('cm_discs', 0, {'is_cm': False}) +
                self.check_array_len_eq_constant('cm_discs', 1, {'self_twist_type': 1}) +
                self.check_array_len_eq_constant('cm_discs', 2, {'self_twist_type': 3}))

    @overall
    def check_self_twist_discs(self):
        """
        check that cm_discs and rm_discs have correct signs and that their union is self_twist_discs
        """
        # TIME about 2s
        return (self.check_array_bound('cm_discs', -1) +
                self.check_array_bound('rm_discs', 1, upper=False) +
                self.check_array_concatenation('self_twist_discs', ['cm_discs', 'rm_discs']))

    @overall(max_failures=100)
    def check_self_twist_proved(self):
        """
        check that self_twist_proved is set (log warning if not, currently there is 1 where it is not set)
        """
        return self.check_values({'self_twist_proved':True})

    @overall
    def check_fricke_eigenval(self):
        """
        if present, check that fricke_eigenval is product of atkin_lehner_eigenvals
        """
        # TIME about 3s
        return self._run_query(SQL('fricke_eigenval != prod2(atkin_lehner_eigenvals)'), {'fricke_eigenval':{'$exists':True}})

    @overall
    def check_sato_tate_set(self):
        """
        for k>1 check that sato_tate_group is set
        """
        return self.check_non_null(['sato_tate_group'], {'weight':{'$gt':1}})

    @overall
    def check_sato_tate_value(self):
        """
        for k>1 check that sato_tate_group is consistent with is_cm
        and char_order (it should be (k-1).2.3.cn where n=char_order
        if is_cm is false, and (k-1).2.1.dn if is_cm is true)
        """
        return (self._run_query(SQL("sato_tate_group != (weight-1) || {0} || char_order").format(Literal(".2.3.c")), constraint={'is_cm':False, 'weight':{'$gt':1}}) +
                self._run_query(SQL("sato_tate_group != (weight-1) || {0} || char_order").format(Literal(".2.1.d")), constraint={'is_cm':True, 'weight':{'$gt':1}}))

    @overall
    def check_projective_image_type(self):
        """
        for k=1 check that projective_image_type is present,
        """
        return self.check_non_null('projective_image_type', {'weight':1})

    @overall
    def check_projective_image(self):
        """
        if present, check that projective_image is consistent with projective_image_type
        """
        return (self.check_eq('projective_image_type', 'projective_image', {'projective_image_type':{'$ne':'Dn'}}) +
                self.check_string_startswith('projective_image', 'D', {'projective_image_type':'Dn'}))

    @overall_long
    def check_projective_field(self):
        """
        if present, check that projective_field_label identifies a
        number field in nf_fields with coeffs = projective_field
        """
        # TIME > 240s
        return (self.check_crosstable_count('nf_fields', 1, 'projective_field_label', 'label', constraint={'projective_field_label':{'$exists':True}}) +
                self.check_crosstable('nf_fields_new', 'projective_field', 'projective_field_label', 'coeffs', 'label'))

    @overall_long
    def check_artin_field(self):
        """
        if present, check that artin_field_label identifies a number
        field in nf_fields with coeffs = artin_field
        """
        # TIME > 600s
        return (self.check_crosstable_count('nf_fields', 1, 'artin_field_label', 'label', constraint={'artin_field_label':{'$exists':True}}) +
                self.check_crosstable('nf_fields_new', 'artin_field', 'artin_field_label', 'coeffs', 'label'))

    @overall
    def check_artin_degree(self):
        """
        if present, we'd like to check that artin_field has Galois group of order artin_degree
        this is hard, so we just check that the degree of the polynomial is a divisor of artin_degree
        """
        return self.check_divisible('artin_degree', SQL("array_length(artin_field, 1) - 1"),
                                    constraint={'artin_field':{'$exists':True}})

    @overall
    def check_trivial_character_cols(self):
        """
        check that atkin_lehner_eigenvals, atkin_lehner_string, and
        fricke_eigenval are present if and only if char_orbit_index=1
        (trivial character)
        """
        # TIME about 1s
        yes = {'$exists':True}
        return self.check_iff({'atkin_lehner_eigenvals':yes, 'atkin_lehner_string':yes, 'fricke_eigenval':yes}, {'char_orbit_index':1})

    @overall
    def check_inner_twists(self):
        """
        check that inner_twists is consistent with inner_twist_count
        and that both are present if field_poly is set
        """
        return (self._run_query(SQL("inner_twist_count != (SELECT SUM(s) FROM UNNEST((inner_twists[1:array_length(inner_twists,1)][2:2])) s)"), constraint={'inner_twist_count':{'$gt':0}}) +
                self.check_values({'inner_twists':{'$exists':True}, 'inner_twist_count':{'$gt':0}}, {'field_poly':{'$exists':True}}))

    @overall
    def check_has_non_self_twist(self):
        """
        check that has_non_self_twist is consistent with inner_twist_count and self_twist_type
        """
        # TIME about 3s
        # TODO - is there a better way to do this?
        return (self.check_iff({'inner_twist_count':-1}, {'has_non_self_twist':-1}) +
                self.check_values({'inner_twist_count':1}, {'has_non_self_twist':0, 'self_twist_type':0}) +
                self.check_values({'inner_twist_count':2}, {'has_non_self_twist':0, 'self_twist_type':1}) +
                self.check_values({'inner_twist_count':2}, {'has_non_self_twist':0, 'self_twist_type':2}) +
                self.check_values({'inner_twist_count':4}, {'has_non_self_twist':0, 'self_twist_type':3}) +
                self.check_values({'inner_twist_count':{'$gt':1}}, {'has_non_self_twist':1, 'self_twist_type':0}) +
                self.check_values({'inner_twist_count':{'$gt':2}}, {'has_non_self_twist':1, 'self_twist_type':1}) +
                self.check_values({'inner_twist_count':{'$gt':2}}, {'has_non_self_twist':1, 'self_twist_type':2}) +
                self.check_values({'inner_twist_count':{'$gt':4}}, {'has_non_self_twist':1, 'self_twist_type':3}))

    @overall
    def check_portraits(self):
        """
        check that there is a portrait present for every nonempty newspace in box where straces is set
        """
        # TIME about 4s
        # from mf_newform_portraits
        return self.check_crosstable_count('mf_newform_portraits', 1, 'label')



    @overall
    def check_field_disc_factorization(self):
        """
        if present, check that field_disc_factorization matches field_disc
        """
        # TIME about 3s
        return self._run_query(SQL('field_disc != prod_factorization(field_disc_factorization)'), {'field_disc':{'$exists':True}});

    @overall
    def check_hecke_ring_index_factorization(self):
        """
        if present, verify that hecke_ring_index_factorization matches hecke_ring_index
        """
        # TIME about 2s
        return self._run_query(SQL('hecke_ring_index != prod_factorization(hecke_ring_index_factorization)'), {'hecke_ring_index_factorization':{'$exists':True}});


    @overall(max_failures=1000)
    def check_analytic_rank_set(self):
        """
        Check that analytic_rank is non-null in every box where lfunctions are computed
        """
        return accumulate_failures(self.check_non_null(['analytic_rank'], self._box_query(box))
                                   for box in db.mf_boxes.search({'lfunctions':True}))


    @overall_long
    def check_analytic_rank(self):
        """
        if analytic_rank is present, check that matches
        order_of_vanishing in lfunctions record, and is are constant
        across the orbit
        """
        # TIME about 1200s
        db._execute(SQL("CREATE TEMP TABLE temp_mftbl AS SELECT label, string_to_array(label,'.'), analytic_rank, dim FROM mf_newforms WHERE analytic_rank is NOT NULL"))
        db._execute(SQL("CREATE TEMP TABLE temp_ltbl AS SELECT order_of_vanishing,(string_to_array(origin,'/'))[5:8],degree FROM lfunc_lfunctions WHERE origin LIKE 'ModularForm/GL2/Q/holomorphic%' and degree=2"))
        db._execute(SQL("CREATE INDEX temp_ltbl_string_to_array_index on temp_ltbl using HASH(string_to_array)"))
        db._execute(SQL("CREATE INDEX temp_mftbl_string_to_array_index on temp_mftbl using HASH(string_to_array)"))
        query = SQL("SELECT label FROM temp_mftbl t1 WHERE array_fill(t1.analytic_rank::smallint, ARRAY[t1.dim]) != ARRAY(SELECT t2.order_of_vanishing FROM temp_ltbl t2 WHERE t2.string_to_array = t1.string_to_array )")
        res = self._run_query(query=query)
        db._execute(SQL("DROP TABLE temp_mftbl"))
        db._execute(SQL("DROP TABLE temp_ltbl"))
        return res

    @overall_long
    def check_self_dual_by_embeddings(self):
        """
        if is_self_dual is present but field_poly is not present,
        check that embedding data in mf_hecke_cc is consistent with
        is_self_dual
        """
        # TIME > 1300s
        # I expect this to take about 3/4h
        # we a create a temp table as we can't use aggregates under WHERE
        db._execute(SQL("CREATE TEMP TABLE tmp_cc AS SELECT t1.hecke_orbit_code, every(0 = all(t1.an_normalized[:][2:2] )) self_dual FROM mf_hecke_cc t1, mf_newforms t2 WHERE t1.hecke_orbit_code=t2.hecke_orbit_code AND t2.is_self_dual AND t2.field_poly is NULL GROUP BY t1.hecke_orbit_code"))
        query = SQL("SELECT t1.label FROM mf_newforms t1, tmp_cc t2 WHERE NOT t2.self_dual AND t1.hecke_orbit_code = t2.hecke_orbit_code")
        return self._run_query(query=query)

    @overall_long
    def check_self_dual_lfunctions(self):
        """
        check that the lfunction self_dual attribute is consistent with newforms
        """
        # TIME > 1200s
        db._execute(SQL("CREATE TEMP TABLE temp_mftbl AS SELECT label, string_to_array(label,'.'), is_self_dual FROM mf_newforms"))
        db._execute(SQL("CREATE TEMP TABLE temp_ltbl AS SELECT (string_to_array(origin,'/'))[5:8], every(self_dual) self_dual FROM lfunc_lfunctions WHERE origin LIKE 'ModularForm/GL2/Q/holomorphic%' and degree=2 GROUP BY (string_to_array(origin,'/'))[5:8]"))
        db._execute(SQL("CREATE INDEX temp_ltbl_string_to_array_index on temp_ltbl using HASH(string_to_array)"))
        db._execute(SQL("CREATE INDEX temp_mftbl_string_to_array_index on temp_mftbl using HASH(string_to_array)"))
        query = SQL("SELECT t1.label FROM temp_mftbl t1, temp_ltbl t2 WHERE t1.is_self_dual != t2.self_dual AND t2.string_to_array = t1.string_to_array")
        res = self._run_query(query=query)
        db._execute(SQL("DROP TABLE temp_mftbl"))
        db._execute(SQL("DROP TABLE temp_ltbl"))
        return res

    @fast(constraint={'projective_field':{'$exists':True}}, projection=['projective_field', 'projective_image', 'projective_image_type'])
    def check_projective_field_degree(self, rec, verbose=False):
        """
        if present, check that projective_field has degree matching
        projective_image (4 for A4,S4, 5 for A5, 4 for D2, n for other
        Dn)
        """
        # TIME about 10s
        # TODO - rewrite as an overall check
        coeffs = rec.get('projective_field')
        deg = Integer(rec['projective_image'][1:])
        if rec['projective_image'] == 'D2':
            deg *= 2
        return self._test_equality(deg, len(coeffs) - 1, verbose)

    @fast(constraint={'inner_twists':{'$exists':True}}, projection=['self_twist_discs', 'inner_twists'])
    def check_self_twist_disc(self, rec, verbose=False):
        """
        check that self_twist_discs = is compatible with the last entries of inner_twists.
        """
        return self._test_equality(set(rec['self_twist_discs']), set([elt[6] for elt in rec['inner_twists'] if elt[6] not in [None, 0, 1]]), verbose)

    #### slow ####

    @slow(projection=['level', 'self_twist_discs', 'traces'])
    def check_inert_primes(self, rec, verbose=False):
        """
        for each discriminant D in self_twist_discs, check that for
        each prime p not dividing the level for which (D/p) = -1,
        check that traces[p] = 0 (we could also check values in
        mf_hecke_nf and/or mf_hecke_cc, but this would be far more
        costly)
        """
        # TIME about 3600s for full table
        N = rec['level']
        traces = [0] + rec['traces'] # shift so indexing correct
        primes = [p for p in prime_range(len(traces)) if N % p != 0]
        for D in rec['self_twist_discs']:
            for p in primes:
                if kronecker_symbol(D, p) == -1 and traces[p] != 0:
                    if verbose:
                        print "CM failure", D, p, traces[p]
                    return False
        return True

    ZZx = PolynomialRing(ZZ, 'x')

    @fast(constraint={'field_poly':{'$exists':True}}, projection=['field_poly', 'field_poly_is_cyclotomic'])
    def check_field_poly_properties(self, rec, verbose=False):
        """
        if present, check that field_poly is irreducible
        """
        # TIME about 180s
        f = self.ZZx(rec['field_poly'])
        if not f.is_irreducible():
            if verbose:
                print "Irreducibility failure", f.factor()
            return False
        # if field_poly_is_cyclotomic, verify this
        if rec['field_poly_is_cyclotomic'] and not f.is_cyclotomic():
            if verbose:
                print "Cyclotomic failure", f
            return False
        return True

    @fast(constraint={'nf_label':None, 'field_poly':{'$exists':True}}, projection=['field_poly', 'is_self_dual'])
    def check_self_dual_by_poly(self, rec, verbose=False):
        """
        if nf_label is not present and field_poly is present, check
        whether is_self_dual is correct (if feasible)
        """
        f = self.ZZx(rec['field_poly'])
        success = (rec.get('is_self_dual') == f.is_real_rooted())
        if not success and verbose:
            print "Real roots failure", f, f.roots(CCC, multiplicities=False)
        return success

    @slow(projection=['level', 'weight', 'char_orbit_index', 'dim', 'related_objects'])
    def check_related_objects(self, rec, verbose=False):
        """
        check that URLS in related_objects are valid and identify objects present in the LMFDB
        """
        names = names_and_urls(rec['related_objects'])
        if len(names) != len(rec['related_objects']):
            if verbose:
                print "Length failure", len(names), len(rec['related_objects'])
            return False
        # if related_objects contains an Artin rep, check that k=1 and that conductor of artin rep matches level N
        for name, url in names:
            if name.startswith('Artin representation '):
                if rec['weight'] != 1:
                    if verbose:
                        print "Artin weight failure", name, rec['weight']
                    return False
                artin_label = name.split()[-1]
                conductor_string = artin_label.split('.')[1]
                conductor = 1
                for elt in conductor_string.split('_'):
                    pe = map(int, elt.split('e'))
                    if len(pe) == 1:
                        conductor *= pe[0]
                    elif len(pe) == 2:
                        conductor *= pe[0]**pe[1]
                    else:
                        raise ValueError(str(pe))
                if conductor != rec['level']:
                    if verbose:
                        print "Conductor failure", name, conductor, rec['level']
                    return False

        # if k=2, char_orbit_index=1 and dim=1 check that elliptic curve isogeny class of conductor N is present in related_objects
            if url.startswith('/EllipticCurve/Q/'):
                if rec['weight'] != 2:
                    if verbose:
                        print "EC weight failure", url, rec['weight']
                    return False
                if rec['dim'] == 1:
                    # Curve over Q
                    if rec['level'] != int(name.split()[-1].split('.')[0]):
                        if verbose:
                            print "EC level failure", url, rec['level'], int(name.split()[-1].split('.')[0])
                        return False
        if (rec['weight'] == 2 and rec['char_orbit_index'] == 1 and rec['dim'] == 1 and
            not any(url.startswith('/EllipticCurve/Q/') for name, url in names)):
            if verbose:
                print "Modularity failure"
            return False
        return True

    @slow(ratio=1, constraint={'artin_image':{'$exists':True}}, projection=['projective_image', 'artin_image', 'artin_degree'])
    def check_artin_image(self, rec, verbose=False):
        """
        if present, check that artin_image is consistent with
        artin_degree and projective_image (quotient of artin_image by
        its center should give projective_image)
        """
        aimage = rec['artin_image']
        pimage = rec.get('projective_image')
        if pimage is None:
            if verbose:
                print "No projective image"
            return False
        aid = map(ZZ, aimage.split('.'))
        if aid[0] != rec['artin_degree']:
            if verbose:
                print "Artin degree mismatch", aid, rec['artin_degree']
            return False
        if pimage == 'A4':
            pid = [12,3]
        elif pimage == 'S4':
            pid = [24,12]
        elif pimage == 'A5':
            pid = [60,5]
        else:
            pid = gap.DihedralGroup(2*ZZ(pimage[1:])).IdGroup().sage()
        G = gap.SmallGroup(*aid)
        qid = G.FactorGroup(G.Center()).IdGroup().sage()
        success = (pid == qid)
        if not success and verbose:
            print "Quotient failure", pid, qid
        return success

    #### char_dir_orbits ####

    #@slow(disabled = True)
    #def check_inner_twist_character(self, rec, verbose=False):
    #    # TODO - use zipped table
    #    # check that each level M in inner twists divides the level and that M.o identifies a character orbit in char_dir_orbits with the listed parity
    #    return True

    #### mf_hecke_traces ####

    @overall_long
    def check_traces_count(self):
        """
        there should be exactly 1000 records in mf_hecke_traces for each record in mf_newforms
        """
        # TIME > 500s
        return self.check_crosstable_count('mf_hecke_traces', 1000, 'hecke_orbit_code')

    @overall_long
    def check_traces_match(self):
        """
        check that traces[n] matches trace_an in mf_hecke_traces
        """
        # TIME > 600s
        return self.check_crosstable_aggregate('mf_hecke_traces', 'traces', 'hecke_orbit_code', 'trace_an', sort=['n'], truncate=1000)

    #### mf_hecke_lpolys ####

    @overall
    def check_lpoly_count(self):
        """
        there should be exactly 25 records in mf_hecke_lpolys for each record in mf_newforms with field_poly
        """
        # TIME about 200s
        return self.check_crosstable_count('mf_hecke_lpolys', 25, 'hecke_orbit_code', constraint={'field_poly':{'$exists':True}})


    #### mf_hecke_cc ####

    @overall_long
    def check_embeddings_count(self):
        """
        check that for such box with embeddings set, the number of
        rows in mf_hecke_cc per hecke_orbit_code matches dim
        """
        # TIME > 1000s
        return accumulate_failures(self.check_crosstable_count('mf_hecke_cc', 'dim', 'hecke_orbit_code', constraint=self._box_query(box)) for box in db.mf_boxes.search({'embeddings':True}))

    @overall
    def check_embeddings_count_boxcheck(self):
        """
        check that for such box with embeddings set, that summing over `dim` matches embeddings_count
        """
        # embedding_count is enough to identify the box
        return [str(box['embedding_count']) for box in db.mf_boxes.search({'embeddings':True}) if sum(self.table.search(self._box_query(box), 'dim')) != box['embedding_count']]

    @overall_long
    def check_roots(self):
        """
        check that embedding_root_real, and embedding_root_image
        present in mf_hecke_cc whenever field_poly is present
        """
        # TIME > 240s
        # I didn't manage to write a generic one for this one
        join = self._make_join('hecke_orbit_code', None)
        query = SQL("SELECT t1.{0} FROM {1} t1, {2} t2 WHERE {3} AND t2.{4} is NULL AND t2.{5} is NULL AND t1.{6} IS NOT NULL").format(
                Identifier(self.table._label_col),
                Identifier(self.table.search_table),
                Identifier('mf_hecke_cc'),
                join,
                Identifier("embedding_root_real"),
                Identifier("embedding_root_imag"),
                Identifier("field_poly")
                )
        return self._run_query(query=query)

    @slow(constraint={'field_poly':{'$exists':True}}, projection=['field_poly', 'hecke_orbit_code'])
    def check_roots_are_roots(self, rec, verbose=False):
        """
        check that  embedding_root_real, and embedding_root_image  approximate a root of field_poly
        """
        poly = PolynomialRing(ZZ, "x")(rec['field_poly'])
        dpoly = poly.derivative()
        dbroots = db.mf_hecke_cc.search({'hecke_orbit_code': rec['hecke_orbit_code']}, ["embedding_root_real", "embedding_root_imag"])
        dbroots = [CCC(root["embedding_root_real"], root["embedding_root_imag"]) for root in dbroots]
        if len(dbroots) != poly.degree():
            if verbose:
                print "Wrong number of roots"
            return False
        for r in dbroots:
            # f is irreducible, so all roots are simple and checking relative error is the way to go
            if poly(r)/dpoly(r) > 1e-11:
                # It's still possible that the roots are correct; it could just be a problem of numerical instability
                print r, poly(r)/dpoly(r)
                break
        else:
            return True
        roots = poly.roots(CCC, multiplicities=False)
        # greedily match.  The degrees are all at most 20, so it's okay to use a quadratic algorithm
        while len(roots) > 0:
            best_dist = infinity
            r = roots[0]
            for i, s in enumerate(dbroots):
                dist = abs(r-s)
                if dist < best_dist:
                    best_dist, best_i = dist, i
            # The dim 1 case where poly=x is handled correctly in the earlier loop, so r != 0.
            if best_dist/abs(r) > 1e-13:
                if verbose:
                    print "Roots mismatch", sorted(roots), sorted(dbroots)
                return False
            roots.pop(0)
            dbroots.pop(best_i)
        return True

    #@slow(disabled=True)
    #def check_an_embedding(self, rec, verbose=False):
    #    # TODO - zipped table
    #    # When we have exact an, check that the inexact values are correct
    #    pass

    @overall_long
    def check_traces(self):
        """
        check that summing (unnormalized) an over embeddings with a
        given hecke_orbit_code gives an approximation to tr(a_n) -- we
        probably only want to do this for specified
        newforms/newspaces, otherwise this will take a very long time.
        """
        howmany = 200
        # we restrict to weight <= 272
        query = SQL("WITH foo AS (  SELECT hecke_orbit_code, traces(array_agg(an_normalized[1:%s])) traces FROM mf_hecke_cc GROUP BY hecke_orbit_code) SELECT t1.label FROM mf_newforms t1, foo WHERE t1.hecke_orbit_code = foo.hecke_orbit_code AND NOT compare_traces(t1.traces[1:%s], foo.traces, -0.5*(t1.weight - 1)) AND t1.weight <= 272")
        return self._run_query(query=query, values=[howmany, howmany])

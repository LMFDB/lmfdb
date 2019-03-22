
from dirichlet_conrey import DirichletGroup_conrey
from sage.all import (
    Gamma0, floor, cached_function, dimension_new_cusp_forms,
    dimension_eis, dimension_cusp_forms, dimension_modular_forms)

from lmfdb.backend.database import db, SQL
from .mf import MfChecker, check_analytic_conductor
from .verification import overall, overall_long, fast, slow, accumulate_failures

@cached_function
def sturm_bound0(level, weight):
    return floor(weight * Gamma0(level).index()/12)

class mf_newspaces(MfChecker):
    table = db.mf_newspaces

    uniqueness_constraints = [
       ['label'],
       ['level', 'weight', 'char_orbit_index'],
       ['level', 'weight', 'char_orbit_label']]

    label = ['level', 'weight', 'char_orbit_label']

    hecke_orbit_code = ['hecke_orbit_code', ['level', 'weight', 'char_orbit_index']]

    @overall
    def check_box_count(self):
        """
        there should be exactly one row for every newspace in
        mf_boxes; for each box performing mf_newspaces.count(box
        query) should match newspace_count for box, and
        mf_newspaces.count() should be the sum of these
        """
        # TIME about 20s
        return accumulate_failures(self.check_count(box['newspace_count'], self._box_query(box))
                   for box in db.mf_boxes.search())

    @overall
    def check_box_hecke_cutter_primes(self):
        """
        check that hecke_cutter_primes is set whenever space is in a
        box with eigenvalues set, `min(dims) <= 20`, and weight > 1
        """
        # TIME about 2s
        return accumulate_failures(self.check_non_null(['hecke_cutter_primes'], self._box_query(box, {'dim':{'$lte':20,'$gt':0}, 'weight':{'$gt':1}}))
                   for box in db.mf_boxes.search({'eigenvalues':True}))

    @overall
    def check_box_straces(self):
        """
        check that traces, trace_bound, num_forms, and
        hecke_orbit_dims are set if space is in a box with straces set
        """
        # TIME about 5s
        return accumulate_failures(
                self.check_non_null(
                    ['traces'],
                        self._box_query(box, {'dim':{'$gt':0}}))
                   for box in db.mf_boxes.search({'straces':True}))

    @overall
    def check_box_traces(self):
        """
        check that traces, trace_bound, num_forms, and
        hecke_orbit_dims are set if space is in a box with straces set
        """
        # TIME about ??s
        return accumulate_failures(
                self.check_non_null([
                        'traces',
                        'trace_bound',
                        'num_forms',
                        'hecke_orbit_dims'], self._box_query(box, {'dim':{'$gt':0}}))
                   for box in db.mf_boxes.search({'traces':True}))


    @overall
    def check_char_orbit(self):
        """
        check that char_orbit matches char_orbit_label
        """
        # TIME 20s
        return self.check_letter_code('char_orbit_index', 'char_orbit_label')

    @overall
    def check_trace_display(self):
        """
        check that trace_display is set whenever traces is set and dim > 0
        """
        # TIME about 2s
        return self.check_non_null(['trace_display'], {'traces':{'$exists': True}, 'dim':{'$gt': 0}})

    @overall
    def check_traces_len(self):
        """
        if present, check that traces has length at least 1000
        """
        # TIME about 45s
        return self.check_array_len_gte_constant('traces', 1000, {'traces':{'$exists': True}})

    @overall
    def check_trace_bound0(self):
        """
        check that trace_bound=0 if num_forms=1
        """
        # TIME about 1s
        return self.check_values({'trace_bound': 0}, {'num_forms':1})

    @overall
    def check_trace_bound1(self):
        """
        check that trace_bound = 1 if hecke_orbit_dims set and all dims distinct
        """
        # TIME about 2s
        return self._run_query(SQL("hecke_orbit_dims!= ARRAY(SELECT DISTINCT UNNEST(hecke_orbit_dims) ORDER BY 1)"), {'trace_bound':1})

    @overall
    def check_trace_bound1_from_dims(self):
        """
        check that trace_bound = 1 if hecke_orbit_dims set and all dims distinct
        """
        # TIME about 2s
        return self._run_query(SQL("hecke_orbit_dims IS NOT NULL AND hecke_orbit_dims = ARRAY(SELECT DISTINCT UNNEST(hecke_orbit_dims) ORDER BY 1) AND num_forms > 1 AND trace_bound != 1"))

    @overall
    def check_AL_dims_plus_dim(self):
        """
        check that AL_dims and plus_dim is set whenever char_orbit_index=1 and dim > 0
        """
        # TIME about 20s
        return self.check_non_null(['AL_dims', 'plus_dim'], {'char_orbit_index':1, 'dim':{'$gt':0}})

    @overall
    def check_dim0_num_forms(self):
        """
        check that if dim = 0 then num_forms = 0 and hecke_orbit_dims = []
        """
        # TIME about 2s
        return self.check_values({'num_forms': 0, 'hecke_orbit_dims':[]}, {'num_forms':0})

    @overall
    def check_mf_dim(self):
        """
        check that eis_dim + cusp_dim = mf_dim
        """
        # TIME about 2s
        return self.check_sum(['eis_dim','cusp_dim'], ['mf_dim'])

    @overall
    def check_mf_new_dim(self):
        """
        check that eis_new_dim+dim=mf_new_dim
        """
        # TIME about 2s
        return self.check_sum(['eis_new_dim','dim'], ['mf_new_dim'])

    @overall
    def check_dim_wt1(self):
        """
        for k = 1 check that dim = dihedral_dim + a4_dim + a5_dim + s4_dim
        """
        # TIME about 1s
        return self.check_sum(['dim'], ['dihedral_dim', 'a4_dim', 'a5_dim', 's4_dim'],{'weight':1})

    @overall
    def check_relative_dim(self):
        """
        check that char_degree * relative_dim = dim
        """
        # TIME about 20s
        return self.check_product('dim', ['char_degree', 'relative_dim'])

    @overall
    def check_len_hecke_orbit_dims(self):
        """
        if present, check that len(hecke_orbit_dims) = num_forms
        """
        # TIME about 2s
        return self.check_array_len_col('hecke_orbit_dims', 'num_forms',{'hecke_orbit_dims':{'$exists':True}})

    @overall
    def check_sum_hecke_orbit_dims(self):
        """
        if present, check that sum(hecke_orbit_dims) = dim
        """
        # TIME about 4s
        return self.check_array_sum('hecke_orbit_dims', 'dim', {'hecke_orbit_dims':{'$exists':True}})

    @overall
    def check_sum_AL_dims(self):
        """
        If AL_dims is set, check that AL_dims sum to dim
        """
        # TIME 0.3 s
        query = SQL(r'SELECT label FROM mf_newspaces t1  WHERE t1.dim !=( SELECT  SUM(s.d) FROM (SELECT ((jsonb_array_elements("AL_dims"))->>1)::int d FROM mf_newspaces t2 WHERE t2.label = t1.label) s ) AND  "AL_dims" is not NULL')
        return self._run_query(query=query)

    @overall
    def check_Nk2(self):
        """
        check that Nk2 = N*k*k
        """
        # TIME about 1s
        return self.check_product('Nk2', ['level', 'weight', 'weight'])

    @overall
    def weight_parity_even(self):
        """
        check weight_parity
        """
        # TIME about 2s
        return self.check_divisible('weight', 2, {'weight_parity':1})

    @overall
    def weight_parity_odd(self):
        """
        check weight_parity
        """
        # TIME about 2s
        return self.check_non_divisible('weight', 2, {'weight_parity':-1})

    @overall
    def check_against_char_dir_orbits(self):
        """
        check that char_* atrributes and prim_orbit_index match data in char_dir_orbits table (conrey_indexes should match galois_orbit)
        """
        # TIME about 50s
        return accumulate_failures(self.check_crosstable('char_dir_orbits', col, ['level', 'char_orbit_label'], charcol, ['modulus', 'orbit_label']) for col, charcol in [('char_orbit_index', 'orbit_index'), ('conrey_indexes', 'galois_orbit'), ('char_order', 'order'), ('char_conductor', 'conductor'), ('char_degree', 'char_degree'), ('prim_orbit_index', 'prim_orbit_index'), ('char_parity', 'parity'), ('char_is_real', 'is_real')])

    @overall
    def check_hecke_orbit_dims_sorted(self):
        """
        check that hecke_orbit_dims is sorted in increasing order
        """
        # TIME about 2s
        return self.check_sorted('hecke_orbit_dims')

    ### mf_hecke_newspace_traces ###
    @overall_long
    def check_traces_count(self):
        """
        there should be exactly 1000 records in mf_hecke_traces for each record in mf_newspaces with traces set
        """
        # TIME about 800s
        return self.check_crosstable_count('mf_hecke_newspace_traces', 1000, 'hecke_orbit_code', constraint={'traces':{'$exists':True}})

    @overall_long
    def check_traces_match(self):
        """
        check that traces[n] matches trace_an in mf_hecke_newspace_traces
        """
        # TIME about 1000s
        return self.check_crosstable_aggregate('mf_hecke_newspace_traces', 'traces', 'hecke_orbit_code', 'trace_an', sort=['n'], truncate=1000, constraint={'traces':{'$exists':True}})

    ### mf_subspaces ###
    @overall
    def check_oldspace_decomposition_totaldim(self):
        """
        check that summing sub_dim * sub_mult over rows with a given label gives dim of S_k^old(N,chi)
        """
        # TIME about 20s
        # from mf_subspaces
        return self.check_crosstable_dotprod('mf_subspaces', 'cusp_dim', 'label', ['sub_mult', 'sub_dim'])

    ### mf_newspace_portraits ###
    @overall
    def check_portraits_count(self):
        """
        check that there is a portrait present for every nonempty newspace in box where straces is set
        """
        return accumulate_failures(
                self.check_crosstable_count('mf_newspace_portraits', 1, 'label',
                    constraint=self._box_query(box, extras = {'dim':{'$gt':1}}))
                for box in db.mf_boxes.search({'straces':True}))

    ### mf_newforms ###
    @overall
    def check_hecke_orbit_dims_newforms(self):
        """
        check that dim is present in hecke_orbit_dims array in newspace record and that summing dim over rows with the same space label gives newspace dim
        """
        # TIME about 40s
        return (self.check_crosstable_aggregate('mf_newforms', 'hecke_orbit_dims', ['level', 'weight','char_orbit_index'], 'dim', constraint={'num_forms':{'$exists':True}}) +
                self.check_crosstable_sum('mf_newforms', 'dim', 'label', 'dim', 'space_label', constraint={'num_forms':{'$exists':True}}))

    @fast(projection=['level', 'weight', 'analytic_conductor'])
    def check_analytic_conductor(self, rec, verbose=False):
        """
        check analytic_conductor
        """
        # TIME about 60s
        return check_analytic_conductor(rec['level'], rec['weight'], rec['analytic_conductor'], verbose=verbose)

    @fast(projection=['level', 'level_radical', 'level_primes', 'level_is_prime', 'level_is_prime_power',  'level_is_squarefree', 'level_is_square'])
    def check_level(self, rec, verbose=False):
        """
        Check the level_* columns
        """
        # TIME about 60s
        return self._check_level(rec, verbose=verbose)

    @fast(projection=['sturm_bound', 'level', 'weight'])
    def check_sturm_bound(self, rec, verbose=False):
        """
        check that sturm_bound is exactly floor(k*Index(Gamma0(N))/12)
        """
        # TIME about 70s
        return self._test_equality(rec['sturm_bound'], sturm_bound0(rec['level'], rec['weight']), verbose, "Sturm bound failure: {0} != {1}")

    @slow(ratio=0.001, report_slow=60, max_slow=10000, constraint={'weight':{'$gt':1}}, projection=['level', 'weight', 'relative_dim', 'conrey_indexes'])
    def check_Skchi_dim_formula(self, rec, verbose=False):
        """
        for k > 1 check that dim is the Q-dimension of S_k^new(N,chi) (using sage dimension formula)
        """
        # sample: dimension_new_cusp_forms(DirichletGroup(100).1^2,4)
        # Work around a bug in sage for Dirichlet characters in level 1 and 2
        if rec['level'] < 3:
            dirchar = rec['level']
        else:
            dirchar = DirichletGroup_conrey(rec['level'])[rec['conrey_indexes'][0]].sage_character()
        return self._test_equality(rec['relative_dim'], dimension_new_cusp_forms(dirchar, rec['weight']), verbose)

    @slow(ratio=0.01, report_slow=10, constraint={'weight':{'$gt':1}}, projection=['level', 'weight', 'char_degree', 'eis_dim', 'cusp_dim', 'mf_dim', 'conrey_indexes'])
    def check_dims(self, rec, verbose=False):
        """
        for k > 1 check each of eis_dim, eis_new_dim, cusp_dim, mf_dim, mf_new_dim using Sage dimension formulas (when applicable)
        """
        # Work around a bug in sage for Dirichlet characters in level 1
        if rec['level'] < 3:
            dirchar = rec['level']
        else:
            dirchar = DirichletGroup_conrey(rec['level'])[rec['conrey_indexes'][0]].sage_character()
        k = rec['weight']
        m = rec['char_degree']
        for func, key in [(dimension_eis, 'eis_dim'), (dimension_cusp_forms, 'cusp_dim'), (dimension_modular_forms, 'mf_dim')]:
            if not self._test_equality(rec[key], func(dirchar, k)*m, verbose):
                return False
        return True

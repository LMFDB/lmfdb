# -*- coding: utf-8 -*-
from ast import literal_eval
from flask import url_for, redirect, abort
from lmfdb import db
from psycodict.encoding import Json
from lmfdb.utils import Downloader, flash_error
from lmfdb.siegel_modular_forms.web_newform import WebNewform
from lmfdb.siegel_modular_forms.web_space import WebNewformSpace, WebGamma1Space


class SMF_download(Downloader):
    table = db.smf_newforms
    title = 'Siegel modular forms'
    data_format = ['N=level', 'k=weight', 'dim', 'analytic conductor', 'defining polynomial', 'number field label', 'CM discriminants', 'RM discriminants', 'first few traces - a2,a3,a5,a7']
    columns = ['level', 'weight', 'dim', 'analytic_conductor', 'field_poly', 'nf_label', 'cm_discs', 'rm_discs', 'trace_display']

    def _get_hecke_nf(self, label):
        proj = ['ap', 'hecke_ring_rank', 'hecke_ring_power_basis','hecke_ring_numerators', 'hecke_ring_denominators', 'field_poly','hecke_ring_cyclotomic_generator', 'hecke_ring_character_values', 'maxp']
        data = db.smf_hecke_nf.lucky({'label':label}, proj)
        if not data:
            return None
        # Make up for db_backend currently deleting Nones
        for elt in proj:
            if elt not in data:
                data[elt] = None

        return data

    def _get_traces(self, label):
        if label.count('.') == 4:
            traces = db.smf_gamma1.lookup(label, projection=['traces'])
        elif label.count('.') == 5:
            traces = db.smf_newspaces.lookup(label, projection=['traces'])
        elif label.count('.') == 6:
            traces = db.smf_newforms.lookup(label, projection=['traces'])
        else:
            return abort(404, "Invalid label: %s"%label)
        if traces is None:
            return abort(404, "Label not found: %s"%label)
        elif traces.get('traces') is None:
            return abort(404, "We have not computed traces for: %s"%label)
        else:
            return [0] + traces['traces']

    # Sage functions to generate everything
    discrete_log_sage = [
            'def discrete_log(elts, gens, mod):',
            '    # algorithm 2.2, page 16 of https://arxiv.org/abs/0903.2785',
            '    def table_gens(gens, mod):',
            '        T = [1]',
            '        n = len(gens)',
            '        r = [None]*n',
            '        s = [None]*n',
            '        for i in range(n):',
            '            beta = gens[i]',
            '            r[i] = 1',
            '            N = len(T)',
            '            while beta not in T:',
            '                for Tj in T[:N]:',
            '                    T.append((beta*Tj) % mod)',
            '                beta = (beta*gens[i]) % mod',
            '                r[i] += 1',
            '            s[i] = T.index(beta)',
            '        return T, r, s',
            '    T, r, s = table_gens(gens, mod)',
            '    n = len(gens)',
            '    N = [ prod(r[:j]) for j in range(n) ]',
            '    Z = lambda s: [ (floor(s/N[j]) % r[j]) for j in range(n)]',
            '    return [Z(T.index(elt % mod)) for elt in elts]']

    extend_multiplicatively_sage = [
            'def extend_multiplicatively(an):',
            '    for pp in prime_powers(len(an)-1):',
            '        for k in range(1, (len(an) - 1)//pp + 1):',
            '            if gcd(k, pp) == 1:',
            '                an[pp*k] = an[pp]*an[k]']

    field_and_convert_sage_powbasis = [
            'from sage.all import PolynomialRing, NumberField',
            'R = PolynomialRing(QQ, "x")',
            'f = R(poly_data)',
            'K = NumberField(f, "a")',
            'betas = [K.gens()[0]**i for i in range(len(poly_data))]',
            'convert_elt_to_field = lambda elt: sum(c*beta for c, beta in zip(elt, betas))']

    field_and_convert_sage_generic = [
            'from sage.all import PolynomialRing, NumberField, ZZ',
            'R = PolynomialRing(QQ, "x")',
            'f = R(poly_data)',
            'K = NumberField(f, "a")',
            'betas = [K([c/ZZ(den) for c in num]) for num, den in basis_data]',
            'convert_elt_to_field = lambda elt: sum(c*beta for c, beta in zip(elt, betas))']

    field_and_convert_sage_sparse_cyclotomic = [
            'from sage.all import CyclotomicField',
            'K = CyclotomicField(poly_data, "z")',
            'convert_elt_to_field = lambda elt: sum(c * K.gens()[0]**e for c,e in elt)']

    convert_aps = ['# convert aps to K elements',
            'primes = primes_first_n(len(aps_data))',
            'good_primes = [p for p in primes if not p.divides(level)]',
            'aps = map(convert_elt_to_field, aps_data)'
            ]

    char_values_sage_generic = [
            'if not hecke_ring_character_values:',
            '    # trivial character',
            '    char_values = dict(zip(good_primes, [1]*len(good_primes)))',
            'else:',
            '    gens = [elt[0] for elt in hecke_ring_character_values]',
            '    gens_values = [convert_elt_to_field(elt[1]) for elt in hecke_ring_character_values]',
            '    char_values = dict([(',
            '        p,prod(g**k for g, k in zip(gens_values, elt)))',
            '        for p, elt in zip(good_primes, discrete_log(good_primes, gens, level))',
            '        ])']

    an_code_sage = [
            'an_list_bound = next_prime(primes[-1])',
            'an = [0]*an_list_bound',
            'an[1] = 1',
            '',
            'from sage.all import PowerSeriesRing',
            'PS = PowerSeriesRing(K, "q")',
            'for p, ap in zip(primes, aps):',
            '    if p.divides(level):',
            '        euler_factor = [1, -ap]',
            '    else:',
            '        euler_factor = [1, -ap, p**(weight - 1) * char_values[p]]',
            '    k = RR(an_list_bound).log(p).floor() + 1',
            '    foo = (1/PS(euler_factor)).padded_list(k)',
            '    for i in range(1, k):',
            '        an[p**i] = foo[i]',
            'extend_multiplicatively(an)',
            'return PS(an)']

    header = ["from sage.all import prod, floor, prime_powers, gcd, QQ, primes_first_n, next_prime, RR\n"]
    qexp_function_body_generic = {'sage': header + discrete_log_sage + extend_multiplicatively_sage +  field_and_convert_sage_generic + convert_aps + char_values_sage_generic + an_code_sage}
    qexp_function_body_powbasis = {'sage': header +  discrete_log_sage + extend_multiplicatively_sage +  field_and_convert_sage_powbasis + convert_aps + char_values_sage_generic + an_code_sage}
    qexp_function_body_sparse_cyclotomic = {'sage': header +  discrete_log_sage + extend_multiplicatively_sage +  field_and_convert_sage_sparse_cyclotomic + convert_aps + char_values_sage_generic + an_code_sage}





    def download_qexp(self, label, lang='sage'):
        """
        The stored Fourier coefficients of a newform (tables smf_qexp_reduction and
        smf_qexp_coeffs), one for each class of indices, in the basis of its coefficient ring.
        """
        lang = self.languages['sage']
        form = db.smf_newforms.lookup(label, ['level', 'weight', 'family', 'hecke_orbit_code'])
        if form is None:
            return abort(404, "Label not found: %s" % label)
        coeffs = {(tuple(r['qf_legendre']), tuple(r['qf_tag'])): r['coeff'] for r in
                  db.smf_qexp_coeffs.search({'hecke_orbit_code': form['hecke_orbit_code']}, ['qf_legendre', 'qf_tag', 'coeff'])}
        if not coeffs:
            return abort(404, "No Fourier coefficients stored for %s" % label)
        hecke_nf = db.smf_hecke_nf.lookup(label, ['field_poly', 'hecke_ring_power_basis', 'hecke_ring_numerators', 'hecke_ring_denominators',
                                                  'qexp_order_index', 'qexp_order_numerators', 'qexp_order_denominators', 'qexp_ideal_index', 'qexp_ideal'])
        level, k = form['level'], form['weight'][0]
        data = []
        for r in db.smf_qexp_reduction.search({'level': level, 'family': form['family']},
                                              ['qf_legendre', 'qf_tag', 'qf_orbit_rep'], sort=['index']):
            v = coeffs.get((tuple(r['qf_legendre']), tuple(r['qf_tag'])))
            if v is not None:
                data.append([r['qf_orbit_rep'], v])
        poly = hecke_nf['field_poly']
        d = len(poly) - 1
        order_index = hecke_nf.get('qexp_order_index') or 1
        ideal_index = hecke_nf.get('qexp_ideal_index') or 1
        if order_index > 1:
            # the coefficients are in a basis of the larger order O' (see the explanation)
            basis = [[n, den] for n, den in zip(hecke_nf['qexp_order_numerators'], hecke_nf['qexp_order_denominators'])]
        elif hecke_nf['hecke_ring_power_basis'] or not hecke_nf.get('hecke_ring_numerators'):
            basis = [[[0] * i + [1], 1] for i in range(d)]
        else:
            basis = [[n, den] for n, den in zip(hecke_nf['hecke_ring_numerators'], hecke_nf['hecke_ring_denominators'])]
        if order_index == 1:
            ring = "the coefficient ring O (the ring generated by the Hecke eigenvalues)"
        else:
            ring = ("the order O' = {x : x I in I}, where I is the module the Fourier coefficients\n"
                    "generate; O' contains the coefficient ring O (the ring generated by the Hecke\n"
                    "eigenvalues) with index %s" % order_index)
        o = "O" if order_index == 1 else "O'"
        if ideal_index == 1:
            norm = ("The newform is normalized so that its Fourier coefficients generate %s,\n"
                    "which determines it up to a unit of %s." % (o, o))
        else:
            norm = ("No multiple of the newform has Fourier coefficients generating %s (I is not a\n"
                    "principal ideal of %s).  It is normalized so that they generate the ideal J of %s\n"
                    "given by ideal_data (the coordinates in basis_data of a Z-basis of J): among the\n"
                    "integral ideals c I (c in the coefficient field) J is one of least index [%s : J] = %s,\n"
                    "and the least in Hermite normal form if there are several.  This determines the\n"
                    "newform up to a unit of %s." % (o, o, o, o, ideal_index, o))

        explain = rf"""
Fourier coefficients of the paramodular newform {label} of degree 2, weight {form['weight']}
and level N = {level}.  It is
    f(Z) = sum_T a(T) exp(2 pi i tr(T Z)),
over the positive definite half-integral matrices T = [[a, b/2], [b/2, c]] with N | c.
Below, [a, b, c] stands for T, and also for the binary quadratic form a x^2 + b x y + c y^2.

If T' is the form T(alpha x + beta y, gamma x + delta y), where alpha delta - beta gamma = +-1
and N | beta, then a(T') = (alpha delta - beta gamma)^k a(T), here with k = {k}.
fourier_data lists one [T, a(T)] for each class of T under these substitutions, for every
class with a member [a, b, c] with a + c/N < {self._qexp_box(data, level)}; the coefficient of
the other members follows from that rule.  (T and its image under a substitution of
determinant -1 are in general listed separately.)

The coefficient a(T) is a vector of coordinates in the basis basis_data of {ring},
each basis element given as [numerator, denominator], with the numerator the list of
coefficients of a polynomial in a root nu of the defining polynomial poly_data (constant
term first).  {norm}

To get a dictionary from [a, b, c] to a(T), as an element of the coefficient field,
type "F = make_data()".
"""
        code = """
def make_data():
    R = PolynomialRing(QQ, 'x')
    poly = R(poly_data)
    if poly.degree() == 1:
        K, nu = QQ, -poly[0]
    else:
        K = NumberField(poly, 'nu')
        nu = K.gen()
    basis = [sum(QQ(c) * nu**i for i, c in enumerate(num)) / den for num, den in basis_data]
    return {tuple(T): sum(c * b for c, b in zip(v, basis)) for T, v in fourier_data}

"""
        explain = "\n".join(" " + line if line else line for line in explain.split("\n"))
        return self._wrap(lang.comment(explain) + code
                          + lang.assign('level', level)
                          + lang.assign('weight', form['weight'])
                          + lang.assign('poly_data', poly)
                          + lang.assign('basis_data', basis)
                          + (lang.assign('ideal_data', hecke_nf['qexp_ideal']) if ideal_index > 1 else '')
                          + lang.assign('fourier_data', data),
                          label + '.qexp',
                          lang=lang,
                          title='Fourier coefficients of newform %s,' % label)

    @staticmethod
    def _qexp_box(data, level):
        """The least B such that the stored representatives all have a + c/N < B."""
        return 1 + max(a + c // level for (a, b, c), _ in data)

    def download_traces(self, label, lang='text'):
        data = self._get_traces(label)
        # to return errors
        if not isinstance(data,list):
            return data
        return self._wrap(Json.dumps(data),
                          label + '.traces',
                          lang=lang,
                          title='Trace form for %s,'%(label))

    def download_multiple_traces(self, info, spaces=False):
        lang = info.get(self.lang_key,'text').strip()
        query = literal_eval(info.get('query', '{}'))
        if spaces:
            count = db.smf_newspaces.count(query)
        else:
            count = db.smf_newforms.count(query)
        limit = 1000
        if count > limit:
            flash_error("We limit downloads of traces to %s forms", limit)
            return redirect(url_for('.index'))
        if spaces:
            res = list(db.smf_newspaces.search(query, projection=['label', 'traces']))
        else:
            res = list(db.smf_newforms.search(query, projection=['label', 'traces']))
        s = ""
        c = self.comment_prefix[lang]
        s += c + ' Query "%s" returned %d %s.\n\n' % (str(info.get('query')), len(res), 'spaces' if spaces else 'forms')
        s += c + ' Below are two lists, one called labels, and one called traces (in matching order).\n'
        s += c + ' Each list of traces starts with a_1 (giving the dimension).\n\n'
        s += 'labels ' + self.assignment_defn[lang] + self.start_and_end[lang][0] + '\\\n'
        s += ',\n'.join(rec['label'] for rec in res)
        s += self.start_and_end[lang][1] + '\n\n'
        s += 'traces ' + self.assignment_defn[lang] + self.start_and_end[lang][0] + '\\\n'
        s += ',\n'.join('[' + ', '.join(str(t) for t in rec['traces']) for rec in res)
        s += self.start_and_end[lang][1]
        return self._wrap(s, 'smf_newforms_traces', lang=lang)

    def download_multiple_space_traces(self, info):
        return self.download_multiple_traces(info, spaces=True)

#    def _download_cc(self, label, lang, col, suffix, title):
#        try:
#            code = encode_hecke_orbit(label)
#        except ValueError:
#            return abort(404, "Invalid label: %s"%label)
#        if not db.mf_hecke_cc.exists({'hecke_orbit_code':code}):
#            return abort(404, "No form found for %s"%(label))
#        def cc_generator():
#            yield '[\n'
#            for ev in db.mf_hecke_cc.search(
#                    {'hecke_orbit_code':code},
#                    ['label',
#                     'embedding_root_real',
#                     'embedding_root_imag',
#                     col],
#                    sort=['conrey_index', 'embedding_index']):
#                D = {'label':ev.get('label'),
#                     col:ev.get(col)}
#                root = (ev.get('embedding_root_real'),
#                        ev.get('embedding_root_imag'))
#                if root != (None, None):
#                    D['root'] = root
#                yield Json.dumps(D) + ',\n\n'
#            yield ']\n'
#        filename = label + suffix
#        title += ' for newform %s,'%(label)
#        return self._wrap_generator(cc_generator(),
#                                    filename,
#                                    lang=lang,
#                                    title=title)
#
#    def download_cc_data(self, label, lang='text'):
#        return self._download_cc(label, lang, 'an_normalized', '.cplx', 'Complex embeddings')
#
#    def download_satake_angles(self, label, lang='text'):
#        return self._download_cc(label, lang, 'angles', '.angles', 'Satake angles')

    def download_embedding(self, label, lang='text'):
        data = db.smf_hecke_cc.lucky({'label':label},
                                    ['label',
                                     'embedding_root_real',
                                     'embedding_root_imag',
                                     'an_normalized',
                                     'angles'])
        if data is None:
            return abort(404, "No embedded newform found for %s"%(label))
        root = (data.pop('embedding_root_real', None),
                data.pop('embedding_root_imag', None))
        if root != (None, None):
            data['root'] = root
        return self._wrap(Json.dumps(data),
                          label,
                          lang=lang,
                          title='Coefficient data for embedded newform %s,'%label)

    def download_newform(self, label, lang='text'):
        data = db.smf_newforms.lookup(label)
        if data is None:
            return abort(404, "Label not found: %s"%label)
        form = WebNewform(data)
        if form.has_exact_qexp:
            data['qexp'] = form.qexp
            data['traces'] = form.texp
        return self._wrap(Json.dumps(data),
                          label,
                          lang=lang,
                          title='Stored data for newform %s,'%(label))

    def download_newspace(self, label, lang='text'):
        data = db.smf_newspaces.lookup(label)
        if data is None:
            return abort(404, "Label not found: %s"%label)
        space = WebNewformSpace(data)
        data['newforms'] = [form['label'] for form in space.newforms]
        # Oldspace data is not yet available (see WebNewformSpace.__init__)
        # data['oldspaces'] = space.oldspaces
        return self._wrap(Json.dumps(data),
                          label,
                          lang=lang,
                          title='Stored data for newspace %s,'%(label))

    def download_full_space(self, label, lang='text'):
        try:
            space = WebGamma1Space.by_label(label)
        except ValueError:
            return abort(404, "Label not found: %s"%label)
        data = {}
        for attr in ['level', 'weight', 'label', 'oldspaces']:
            data[attr] = getattr(space, attr)
        data['newspaces'] = [spc['label'] for spc, forms in space.decomp]
        data['newforms'] = sum([[form['label'] for form in forms] if spc.get('num_forms') is not None else [None] for spc, forms in space.decomp], [])
        if None in data['newforms']:
            data.pop('newforms')
        data['dimgrid'] = space.dim_grid._grid
        return self._wrap(Json.dumps(data),
                          label,
                          lang=lang,
                          title='Stored data for newspace %s,'%(label))

    def download_spaces(self, info):
        lang = info.get(self.lang_key,'text').strip()
        query = literal_eval(info.get('query', '{}'))
        proj = ['label', 'analytic_conductor', 'conrey_indexes', 'char_order']
        spaces = list(db.smf_newspaces.search(query, projection=proj))
        s = ""
        c = self.comment_prefix[lang]
        s += c + ' Query "%s" returned %d spaces.\n\n' % (str(info.get('query')), len(spaces))
        s += c + ' Below one list called data.\n'
        s += c + ' Each entry in the list has the form:\n'
        s += c + " %s\n" % proj
        s += 'data ' + self.assignment_defn[lang] + self.start_and_end[lang][0] + '\\\n'
        s += ',\n'.join('[' + ', '.join(str(spc[col]) for col in proj) + ']' for spc in spaces)
        s += self.start_and_end[lang][1]
        return self._wrap(s, 'smf_newspaces', lang=lang)




    # Magma
    """
    For possible later use: functions to cut out a space of modular symbols using a linear combination of T_n's.

    function ModularSymbolsDual(M, V)   // copied from modsym.m
       assert V subset DualRepresentation(M); MM := New(ModSym); MM`root := AmbientSpace(M); MM`is_ambient_space := false;
       MM`dual_representation := V; MM`dimension := Dimension(V); MM`sign := M`sign; MM`F := M`F; MM`k := M`k;
       return MM;
    end function;

    function KernelLinearCombo(I, M)
      //The kernel of I on M, the subspace of M defined as the kernel of sum_i I[i][1]*T_{I[i][2]}.

      cutter := &+[c[2]*DualHeckeOperator(M,c[1]) : c in I];
      W := RowSpace(KernelMatrix(cutter)*BasisMatrix(DualRepresentation(M)));
      N := ModularSymbolsDual(AmbientSpace(M),W);
      return N;
    end function;
    """
    def _magma_ConvertToHeckeField(self, newform, hecke_nf):
        begin = ['function ConvertToHeckeField(input: pass_field := false, Kf := [])',
                 '    if not pass_field then']
        if newform.dim == 1:
            return begin + [
                    '        Kf := Rationals();',
                    '    end if;',
                    '    return [Kf!elt[1] : elt in input];',
                    'end function;',
                    ]
        elif hecke_nf['hecke_ring_cyclotomic_generator'] > 0:
            return begin + [
                    '        Kf := CyclotomicField(%d);' % hecke_nf['hecke_ring_cyclotomic_generator'],
                    '    end if;',
                    '    return [ #coeff eq Kf!0 select 0 else &+[ elt[1]*Kf.1^elt[2] : elt in coeff]  : coeff in input];',
                    'end function;',
                    ]
        elif hecke_nf['hecke_ring_power_basis']:
            return begin + [
                    '        ' + self.assign('magma', 'poly', newform.field_poly, level = 1).rstrip('\n'),
                    '        Kf := NumberField(Polynomial([elt : elt in poly]));',
                    '        AssignNames(~Kf, ["nu"]);',
                    '    end if;',
                    '    Rfbasis := [Kf.1^i : i in [0..Degree(Kf)-1]];',
                    '    inp_vec := Vector(Rfbasis)*ChangeRing(Transpose(Matrix([[elt : elt in row] : row in input])),Kf);',
                    '    return Eltseq(inp_vec);',
                    'end function;',
                    ]
        else:
            return begin + [
                    '        ' + self.assign('magma', 'poly', newform.field_poly, level = 1).rstrip('\n'),
                    '        Kf := NumberField(Polynomial([elt : elt in poly]));',
                    '        AssignNames(~Kf, ["nu"]);',
                    '    end if;',
                    '    ' + self.assign('magma', 'Rf_num', hecke_nf['hecke_ring_numerators']).rstrip('\n'),
                    '    ' + self.assign('magma', 'Rf_basisdens', hecke_nf['hecke_ring_denominators']).rstrip('\n'),
                    '    Rf_basisnums := ChangeUniverse([[z : z in elt] : elt in Rf_num], Kf);',
                    '    Rfbasis := [Rf_basisnums[i]/Rf_basisdens[i] : i in [1..Degree(Kf)]];',
                    '    inp_vec := Vector(Rfbasis)*ChangeRing(Transpose(Matrix([[elt : elt in row] : row in input])),Kf);',
                    '    return Eltseq(inp_vec);',
                    'end function;',
                    ]

    def _magma_MakeCharacters(self, newform, hecke_nf):
        """
            Given a WebNewform r from smf_newforms containing columns
            level,weight,char_orbit_label,char_values
            returns a string containing magma code to create the character
            for r in magma using the default generators.
        """
        level = newform.level
        order = newform.char_values[1]
        char_gens = newform.char_values[2]
        explain = '// To make the character of type GrpDrchElt, type "MakeCharacter_%d_%s();"' % (newform.level, newform.char_orbit_label)
        self.explain.append(explain)
        out = [
                explain,
                'function MakeCharacter_%d_%s()' % (newform.level, newform.char_orbit_label),
                '    ' + self.assign('magma', 'N', level).rstrip('\n'), # level
                '    ' + self.assign('magma', 'order', order).rstrip('\n'), # order of the character
                '    ' + self.assign('magma', 'char_gens', char_gens, level = 1).rstrip('\n'), # generators
                '    ' + self.assign('magma', 'v', newform.char_values[3]).rstrip('\n'),
                '    // chi(gens[i]) = zeta^v[i]',
                '    assert SequenceToList(UnitGenerators(DirichletGroup(N))) eq char_gens;',
                '    F := CyclotomicField(order);',
                '    chi := DirichletCharacterFromValuesOnUnitGenerators(DirichletGroup(N,F),[F|F.1^e:e in v]);',
                '    return MinimalBaseRingCharacter(chi);',
                'end function;',
                '',
                ]
        if hecke_nf is None or hecke_nf['hecke_ring_character_values'] is None:
            return out + [
                    'function MakeCharacter_%d_%s_Hecke(Kf)' % (newform.level, newform.char_orbit_label),
                    '    return MakeCharacter_%d_%s();' % (newform.level, newform.char_orbit_label),
                    'end function;'
                    ]
        else:
            # hecke_nf['hecke_ring_character_values'] = list of pairs
            #   [[m1,[a11,...a1n]],[m2,[a12,...,a2n]],...] where [m1,m2,...,mr]
            #   are generators for Z/NZ and [ai1,...,ain] is the value of chi(mi)
            #   expressed in terms of the Hecke ring basis or in cyclotomic representation
            #   [[c,e]] encoding c x zeta_m^e where m is hecke_ring_cyclotomic_generator
            assert char_gens == [elt[0] for elt in hecke_nf['hecke_ring_character_values']]
            char_values = [elt[1] for elt in hecke_nf['hecke_ring_character_values']]
            explain = '// To make the character of type GrpDrchElt with Codomain the HeckeField, type "MakeCharacter_%d_%s_Hecke();"' % (newform.level, newform.char_orbit_label)
            self.explain.append(explain)
            out += [
                explain,
                'function MakeCharacter_%d_%s_Hecke(Kf)' % (newform.level, newform.char_orbit_label),
                    '    ' + self.assign('magma', 'N', level).rstrip('\n'), # level
                    '    ' + self.assign('magma', 'order', order).rstrip('\n'), # order of the character
                    '    ' + self.assign('magma', 'char_gens', char_gens, level = 1).rstrip('\n'), # generators
                    '    ' + self.assign('magma', 'char_values', char_values, level = 1).rstrip('\n'), # chi(gens[i]) = zeta_n^exp[i]
                    '    assert SequenceToList(UnitGenerators(DirichletGroup(N))) eq char_gens;',
                    '    values := ConvertToHeckeField(char_values : pass_field := true, Kf := Kf); // the value of chi on the gens as elements in the Hecke field',
                    '    F := Universe(values);// the Hecke field',
                    '    chi := DirichletCharacterFromValuesOnUnitGenerators(DirichletGroup(N,F),values);',
                    '    return chi;',
                    'end function;'
                    ]
            return out

    def _magma_ExtendMultiplicatively(self):
        return [
                'function ExtendMultiplicatively(weight, aps, character)',
                '    prec := NextPrime(NthPrime(#aps)) - 1; // we will able to figure out a_0 ... a_prec',
                '    primes := PrimesUpTo(prec);',
                '    prime_powers := primes;',
                '    assert #primes eq #aps;',
                '    log_prec := Floor(Log(prec)/Log(2)); // prec < 2^(log_prec+1)',
                '    F := Universe(aps);',
                '    FXY<X, Y> := PolynomialRing(F, 2);',
                '    // 1/(1 - a_p T + p^(weight - 1) * char(p) T^2) = 1 + a_p T + a_{p^2} T^2 + ...',
                '    R<T> := PowerSeriesRing(FXY : Precision := log_prec + 1);',
                '    recursion := Coefficients(1/(1 - X*T + Y*T^2));',
                '    coeffs := [F!0: i in [1..(prec+1)]];',
                '    coeffs[1] := 1; //a_1',
                '    for i := 1 to #primes do',
                '        p := primes[i];',
                '        coeffs[p] := aps[i];',
                '        b := p^(weight - 1) * F!character(p);',
                '        r := 2;',
                '        p_power := p * p;',
                '        //deals with powers of p',
                '        while p_power le prec do',
                '            Append(~prime_powers, p_power);',
                '            coeffs[p_power] := Evaluate(recursion[r + 1], [aps[i], b]);',
                '            p_power *:= p;',
                '            r +:= 1;',
                '        end while;    ',
                '    end for;',
                '    Sort(~prime_powers);',
                '    for pp in prime_powers do',
                '        for k := 1 to Floor(prec/pp) do',
                '            if GCD(k, pp) eq 1 then',
                '                coeffs[pp*k] := coeffs[pp]*coeffs[k];',
                '            end if;',
                '        end for;',
                '    end for;',
                '    return coeffs;',
                'end function;',
                ]

    def _magma_qexpCoeffs(self, newform, hecke_nf):
        explain = '// To make the coeffs of the qexp of the newform in the Hecke field type "qexpCoeffs();"'
        self.explain.append(explain)
        return [
            'function qexpCoeffs()',
            '    ' + explain,
            '    ' + self.assign('magma', 'weight', newform.weight).rstrip('\n'),
            '    ' + self.assign('magma', 'raw_aps', hecke_nf['ap'], prepend = '    '*2).rstrip('\n'),
            '    aps := ConvertToHeckeField(raw_aps);',
            '    chi := MakeCharacter_%d_%s_Hecke(Universe(aps));' % (newform.level, newform.char_orbit_label),
            '    return ExtendMultiplicatively(weight, aps, chi);',
            'end function;',
            ]

    def _magma_MakeNewformModSym(self, newform, hecke_nf ):
        """
        Given a WebNewform r from smf_newforms containing columns::

            label,level,weight,char_orbit_label,char_values,cutters

        returns a string containing magma code to create the newform
        Galois orbit as a modular symbols space using Hecke cutters in magma.
        """
        N = newform.level
        k = newform.weight
        o = newform.char_orbit_label

        assert k >= 2   # modular symbols only in weight >= 2

        cutters = "[" + ",".join("<%d,R!%s" % (c[0], c[1]) + ">" for c in newform.hecke_cutters) + "]"
        explain = [ '// To make the Hecke irreducible modular symbols subspace (type ModSym)',
                    '// containing the newform, type "MakeNewformModSym_%s();".' % (newform.label.replace(".","_"), ),
                    '// This may take a long time!  To see verbose output, uncomment the SetVerbose line below.'
        ]
        self.explain += explain
        return explain + [
                "function MakeNewformModSym_%s()"  % (newform.label.replace(".","_"), ),
                "    R<x> := PolynomialRing(Rationals());",
                "    chi := MakeCharacter_%d_%s();" % (N, o),
                "    // SetVerbose(\"ModularSymbols\", true);",
                "    Snew := NewSubspace(CuspidalSubspace(ModularSymbols(chi,%d,-1)));" % (k, ),
                "    Vf := Kernel(%s,Snew);" % (cutters,),
                "    return Vf;",
                "end function;",
                ]

    def _magma_MakeNewformModFrm(self, newform, hecke_nf):
        """
        Given a WebNewform r from smf_newforms containing columns::

            label,level,weight,char_orbit_label,char_values

        and h a row from smf_hecke_nf containing columns::

            hecke_ring_numerators,hecke_ring_denominators,
            hecke_ring_cyclotomic_generator

        and v a list whose nth entry is the entry an from the table smf_hecke_nf
        (consisting of a list of integers giving the Hecke eigenvalue
        as a linear combination of the basis specified in the orbit table)
        so in particular v[0] = 0 and v[1] = 1,
        returns a string containing magma code to create the newform
        as a representative q-expansion (type ModFrm) in magma.
        """
        explain = [
                '// To make the newform (type ModFrm), type "MakeNewformModFrm_%s();".' % (newform.label.replace(".", "_"), ),
                '// This may take a long time!  To see verbose output, uncomment the SetVerbose lines below.',
                '// The precision argument determines an initial guess on how many Fourier coefficients to use.',
                '// This guess is increased enough to uniquely determine the newform.'
        ]
        self.explain += explain
        return explain + [
                'function MakeNewformModFrm_%s(:prec:=%d)' % (newform.label.replace(".","_"), newform.dim),
                '    chi := MakeCharacter_%d_%s();' % (newform.level, newform.char_orbit_label),
                '    f_vec := qexpCoeffs();',
                '    Kf := Universe(f_vec);',
                '    // SetVerbose("ModularForms", true);',
                '    // SetVerbose("ModularSymbols", true);',
                '    S := CuspidalSubspace(ModularForms(chi, %d));' % newform.weight,
                '    S := BaseChange(S, Kf);',
                '    maxprec := NextPrime(%d) - 1;' % hecke_nf['maxp'],
                '    while true do',
                '        trunc_vec := Vector(Kf, [0] cat [f_vec[i]: i in [1..prec]]);',
                # weight 1 does not have NewSpace functionality, and anyway that
                # would be an extra possibly expensive linear algebra step
                '        B := Basis(S, prec + 1);',
                '        S_basismat := Matrix([AbsEltseq(g): g in B]);',
                '        if Rank(S_basismat) eq Min(NumberOfRows(S_basismat), NumberOfColumns(S_basismat)) then',
                '            S_basismat := ChangeRing(S_basismat,Kf);',
                '            f_lincom := Solution(S_basismat,trunc_vec);',
                '            f := &+[f_lincom[i]*Basis(S)[i] : i in [1..#Basis(S)]];',
                '            return f;',
                '        end if;',
                '        error if prec eq maxprec, "Unable to distinguish newform within newspace";',
                '        prec := Min(Ceiling(1.25 * prec), maxprec);',
                '    end while;',
                'end function;'
                ]


    def download_newform_to_magma(self, label, lang='magma'):
        data = db.smf_newforms.lookup(label)
        if data is None:
            return abort(404, "Label not found: %s"%label)
        newform = WebNewform(data)
        hecke_nf = self._get_hecke_nf(label)

        self.explain = []
        out = []
        newlines = [''] * 2
        if newform.has_exact_qexp:
            out += self._magma_ConvertToHeckeField(newform, hecke_nf) + newlines

        out += self._magma_MakeCharacters(newform, hecke_nf) + newlines

        if newform.has_exact_qexp:
            # to return errors
            # this line will never be ran if the data is correct
            if not isinstance(hecke_nf, dict): # pragma: no cover
                return hecke_nf  # pragma: no cover
            out += self._magma_ExtendMultiplicatively() + newlines
            out += self._magma_qexpCoeffs(newform, hecke_nf) + newlines


            # The Sturm bound is not enough precision; see Github issue 4354
            # prec = db.smf_newspaces.lucky({'label': newform.space_label}, 'sturm_bound')
            out += self._magma_MakeNewformModFrm(newform, hecke_nf) + newlines
        if newform.hecke_cutters is not None and newform.weight > 1:
            out += self._magma_MakeNewformModSym(newform, hecke_nf)

        outstr = "\n".join(self.explain + out)

        return self._wrap(outstr,
                          label,
                          lang=lang,
                          title='Make newform %s in Magma,'%(label))

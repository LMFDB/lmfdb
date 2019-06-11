# -*- coding: utf-8 -*-
from ast import literal_eval
from flask import  url_for, redirect, abort
from lmfdb import db
from lmfdb.backend.encoding import Json
from lmfdb.utils import Downloader, flash_error
from lmfdb.classical_modular_forms.web_newform import WebNewform, encode_hecke_orbit
from lmfdb.classical_modular_forms.web_space import WebNewformSpace, WebGamma1Space

class CMF_download(Downloader):
    table = db.mf_newforms
    title = 'Classical modular forms'
    data_format = ['N=level', 'k=weight', 'dim', 'N*k^2', 'defining polynomial', 'number field label', 'CM discriminants', 'RM discriminants', 'first few traces']
    columns = ['level', 'weight', 'dim', 'analytic_conductor', 'field_poly', 'nf_label', 'cm_discs', 'rm_discs', 'trace_display']

    def _get_hecke_nf(self, label):
        proj = ['ap', 'hecke_ring_rank', 'hecke_ring_power_basis','hecke_ring_numerators', 'hecke_ring_denominators', 'field_poly','hecke_ring_cyclotomic_generator', 'hecke_ring_character_values', 'maxp']
        data = db.mf_hecke_nf.lucky({'label':label}, proj)
        if not data:
            return None
        # Make up for db_backend currently deleting Nones
        for elt in proj:
            if elt not in data:
                data[elt] = None

        return data

    def _get_traces(self, label):
        if label.count('.') == 1:
            traces = db.mf_gamma1.lookup(label, projection=['traces'])
        elif label.count('.') == 2:
            traces = db.mf_newspaces.lookup(label, projection=['traces'])
        elif label.count('.') == 3:
            traces = db.mf_newforms.lookup(label, projection=['traces'])
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

    field_and_convert_sage_dim1 = [
            'K = QQ',
            'convert_elt_to_field = lambda elt: K(elt)']

    field_and_convert_sage_powbasis = [
            'from sage.all import PolynomialRing, NumberField',
            'R = PolynomialRing(QQ, "x")',
            'f = R(poly_data)',
            'K = NumberField(f, "a")',
            'betas = [K.gens()[0]**i for i in range(len(poly_data))]',
            'convert_elt_to_field = lambda elt: sum(c*beta for c, beta in zip(elt, betas))']

    field_and_convert_sage_generic = [
            'from sage.all import PolynomialRing, NumberField',
            'R = PolynomialRing(QQ, "x")',
            'f = R(poly_data)',
            'K = NumberField(f, "a")',
            'betas = [K([c/den for c in num]) for num, den in basis_data]',
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
            '        an[p] = ap',
            '    else:',
            '        k = RR(an_list_bound).log(p).floor() + 1',
            '        euler_factor = [1, -ap, p**(weight - 1) * char_values[p]]',
            '        foo = (1/PS(euler_factor)).padded_list(k)',
            '        for i in range(1, k):',
            '            an[p**i] = foo[i]',
            'extend_multiplicatively(an)',
            'return PS(an)']

    header = ["from sage.all import prod, floor, prime_powers, gcd, QQ, primes_first_n, next_prime, RR\n"]
    qexp_dim1_function_body = {'sage': header + extend_multiplicatively_sage + field_and_convert_sage_dim1 + convert_aps + ['char_values = dict(zip(good_primes, [1]*len(good_primes)))'] + an_code_sage }
    qexp_function_body_generic = {'sage': header +  discrete_log_sage + extend_multiplicatively_sage +  field_and_convert_sage_generic + convert_aps + char_values_sage_generic + an_code_sage}
    qexp_function_body_powbasis = {'sage': header +  discrete_log_sage + extend_multiplicatively_sage +  field_and_convert_sage_powbasis + convert_aps + char_values_sage_generic + an_code_sage}
    qexp_function_body_sparse_cyclotomic = {'sage': header +  discrete_log_sage + extend_multiplicatively_sage +  field_and_convert_sage_sparse_cyclotomic + convert_aps + char_values_sage_generic + an_code_sage}





    def download_qexp(self, label, lang='sage'):
        hecke_nf = self._get_hecke_nf(label)
        if hecke_nf is None:
            return abort(404, "No q-expansion found for %s" % label)

        dim = hecke_nf['hecke_ring_rank']
        aps = hecke_nf['ap']
        level, weight = map(int, label.split('.')[:2])
        level_data = self.assign(lang, 'level', level);
        weight_data = self.assign(lang, 'weight', weight);

        c = self.comment_prefix[lang]
        func_start = self.get('function_start',{}).get(lang,[])
        func_end = self.get('function_end',{}).get(lang,[])

        explain = '\n'
        explain += c + ' We generate the q-expansion using the Hecke eigenvalues a_p at the primes.\n'
        aps_data = self.assign(lang, 'aps_data', aps);
        code = ''
        if dim == 1:
            func_body = self.get('qexp_dim1_function_body',{}).get(lang,[])
            basis_data = poly_data = hecke_ring_character_values = ''
        else:
            hecke_ring_character_values = self.assign(lang, 'hecke_ring_character_values', hecke_nf['hecke_ring_character_values']);

            if hecke_nf['hecke_ring_cyclotomic_generator'] > 0:
                func_body =  self.get('qexp_function_body_sparse_cyclotomic',{}).get(lang,[])
                explain += c + ' Each a_p is given as list of pairs\n'
                explain += c + ' Each pair (c, e) corresponds to c*zeta^e\n'
                basis_data = ''
                poly_data =  self.assign(lang, 'poly_data', hecke_nf['hecke_ring_cyclotomic_generator'])
            else:
                explain += c + ' Each a_p is given as a linear combination\n'
                explain += c + ' of the following basis for the coefficient ring.\n'
                poly_data = '\n' + c + ' The following line gives the coefficients of\n'
                poly_data += c + ' the defining polynomial for the coefficient field.\n'
                poly_data =  self.assign(lang, 'poly_data', hecke_nf['field_poly'], level = 1)
                if hecke_nf['hecke_ring_power_basis']:
                    basis_data = '\n' + c + ' The basis for the coefficient ring is just the power basis\n'
                    basis_data += c + ' in the root of the defining polynomial above.\n'
                    basis_data = ''
                    func_body = self.get('qexp_function_body_powbasis',{}).get(lang,[])
                else:
                    basis_data = '\n' + c + ' The entries in the following list give a basis for the\n'
                    basis_data += c + ' coefficient ring in terms of a root of the defining polynomial above.\n'
                    basis_data += c + ' Each line consists of the coefficients of the numerator, and a denominator.\n'
                    basis_data += self.assign(lang,  'basis_data ', zip(hecke_nf['hecke_ring_numerators'], hecke_nf['hecke_ring_denominators']))
                    basis_data += '\n'
                    func_body = self.get('qexp_function_body_generic',{}).get(lang,[])

            if lang in ['sage']:
                explain += c + ' To create the q-expansion as a power series, type "qexp%smake_data()%s"\n' % (self.assignment_defn[lang], self.line_end[lang])


        if lang in ['sage']:
            code = '\n' + '\n'.join(func_start) + '\n'
            code += '    ' + '\n    '.join(func_body) + '\n'
            code += '\n'.join(func_end)

        return self._wrap(explain + code + level_data + weight_data + poly_data + basis_data + hecke_ring_character_values + aps_data,
                          label + '.qexp',
                          lang=lang,
                          title='q-expansion of newform %s,'%(label))

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
            count = db.mf_newspaces.count(query)
        else:
            count = db.mf_newforms.count(query)
        limit = 1000
        if count > limit:
            flash_error("We limit downloads of traces to %s forms", limit)
            return redirect(url_for('.index'))
        if spaces:
            res = list(db.mf_newspaces.search(query, projection=['label', 'traces']))
        else:
            res = list(db.mf_newforms.search(query, projection=['label', 'traces']))
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
        return self._wrap(s, 'mf_newforms_traces', lang=lang)

    def download_multiple_space_traces(self, info):
        return self.download_multiple_traces(info, spaces=True)

    def _download_cc(self, label, lang, col, suffix, title):
        try:
            code = encode_hecke_orbit(label)
        except ValueError:
            return abort(404, "Invalid label: %s"%label)
        if not db.mf_hecke_cc.exists({'hecke_orbit_code':code}):
            return abort(404, "No form found for %s"%(label))
        def cc_generator():
            yield '[\n'
            for ev in db.mf_hecke_cc.search(
                    {'hecke_orbit_code':code},
                    ['label',
                     'embedding_root_real',
                     'embedding_root_imag',
                     col],
                    sort=['conrey_index', 'embedding_index']):
                D = {'label':ev.get('label'),
                     col:ev.get(col)}
                root = (ev.get('embedding_root_real'),
                        ev.get('embedding_root_imag'))
                if root != (None, None):
                    D['root'] = root
                yield Json.dumps(D) + ',\n\n'
            yield ']\n'
        filename = label + suffix
        title += ' for newform %s,'%(label)
        return self._wrap_generator(cc_generator(),
                                    filename,
                                    lang=lang,
                                    title=title)

    def download_cc_data(self, label, lang='text'):
        return self._download_cc(label, lang, 'an_normalized', '.cplx', 'Complex embeddings')

    def download_satake_angles(self, label, lang='text'):
        return self._download_cc(label, lang, 'angles', '.angles', 'Satake angles')

    def download_embedding(self, label, lang='text'):
        data = db.mf_hecke_cc.lucky({'label':label},
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
        data = db.mf_newforms.lookup(label)
        if data is None:
            return abort(404, "Label not found: %s"%label)
        form = WebNewform(data)
        form.setup_cc_data({'m':'1-%s'%form.dim})
        if form.has_exact_qexp:
            data['qexp'] = form.qexp
            data['traces'] = form.texp
        if form.has_complex_qexp:
            data['complex_embeddings'] = form.cc_data
        return self._wrap(Json.dumps(data),
                          label,
                          lang=lang,
                          title='Stored data for newform %s,'%(label))

    def download_newspace(self, label, lang='text'):
        data = db.mf_newspaces.lookup(label)
        if data is None:
            return abort(404, "Label not found: %s"%label)
        space = WebNewformSpace(data)
        data['newforms'] = [form['label'] for form in space.newforms]
        data['oldspaces'] = space.oldspaces
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
        data['newforms'] = sum([[form['label'] for form in forms] for spc, forms in space.decomp], [])
        data['dimgrid'] = space.dim_grid._grid
        return self._wrap(Json.dumps(data),
                          label,
                          lang=lang,
                          title='Stored data for newspace %s,'%(label))

    def download_spaces(self, info):
        lang = info.get(self.lang_key,'text').strip()
        query = literal_eval(info.get('query', '{}'))
        proj = ['label', 'analytic_conductor', 'conrey_indexes', 'char_order']
        spaces = list(db.mf_newspaces.search(query, projection=proj))
        s = ""
        c = self.comment_prefix[lang]
        s += c + ' Query "%s" returned %d spaces.\n\n' % (str(info.get('query')), len(spaces))
        s += c + ' Below one list called data.\n'
        s += c + ' Each entry in the list has the form:\n'
        s += c + " %s\n" % proj
        s += 'data ' + self.assignment_defn[lang] + self.start_and_end[lang][0] + '\\\n'
        s += ',\n'.join('[' + ', '.join([str(spc[col]) for col in proj]) + ']' for spc in spaces)
        s += self.start_and_end[lang][1]
        return self._wrap(s, 'mf_newspaces', lang=lang)




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
                    '    end if;'
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
            Given a WebNewform r from mf_newforms containing columns
            level,weight,char_orbit_label,char_values
            returns a string containing magma code to create the character
            for r in magma using the default generators.
        """
        level = newform.level
        order = newform.char_values[1]
        char_gens = newform.char_values[2]
        out = [
                '// To make the character of type GrpDrchElt, type "MakeCharacter_%d_%s();"' % (newform.level, newform.char_orbit_label),
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
            out += [
                '// To make the character of type GrpDrchElt with Codamain the HeckeField, type "MakeCharacter_%d_%s_Hecke();"' % (newform.level, newform.char_orbit_label),
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
        return [
            'function qexpCoeffs()',
            '    // To make the coeffs of the qexp of the newform in the Hecke field type "qexpCoeffs();"',
            '    ' + self.assign('magma', 'weight', newform.weight).rstrip('\n'),
            '    ' + self.assign('magma', 'raw_aps', hecke_nf['ap'], prepend = '    '*2).rstrip('\n'),
            '    aps := ConvertToHeckeField(raw_aps);',
            '    chi := MakeCharacter_%d_%s_Hecke(Universe(aps));' % (newform.level, newform.char_orbit_label),
            '    return ExtendMultiplicatively(weight, aps, chi);',
            'end function;',
            ]

    def _magma_MakeNewformModSym(self, newform, hecke_nf ):
        """
        Given a WebNewform r from mf_newforms containing columns
           label,level,weight,char_orbit_label,char_values,cutters
        returns a string containing magma code to create the newform
        Galois orbit as a modular symbols space using Hecke cutters in magma.
        """
        N = newform.level
        k = newform.weight
        o = newform.char_orbit_label

        assert k >= 2   # modular symbols only in weight >= 2

        cutters = "[" + ",".join(["<%d,R!%s"%(c[0],c[1])+">" for c in newform.hecke_cutters]) + "]"

        return [
                '// To make the Hecke irreducible modular symbols subspace (type ModSym)',
                '// containing the newform, type "MakeNewformModSym_%s();".' % (newform.label.replace(".","_"), ),
                '// This may take a long time!  To see verbose output, uncomment the SetVerbose line below.',
                "function MakeNewformModSym_%s()"  % (newform.label.replace(".","_"), ),
                "    R<x> := PolynomialRing(Rationals());",
                "    chi := MakeCharacter_%d_%s();" % (N, o),
                "    // SetVerbose(\"ModularSymbols\", true);",
                "    Snew := NewSubspace(CuspidalSubspace(ModularSymbols(chi,%d,-1)));" % (k, ),
                "    Vf := Kernel(%s,Snew);" % (cutters,),
                "    return Vf;",
                "end function;",
                ]

    def _magma_MakeNewformModFrm(self, newform, hecke_nf, prec):
        """
        Given a WebNewform r from mf_newforms containing columns
           label,level,weight,char_orbit_label,char_values
        and h a row from mf_hecke_nf containing columns
           hecke_ring_numerators,hecke_ring_denominators,
           hecke_ring_cyclotomic_generator
        and v a list whose nth entry is the entry an from the table mf_hecke_nf
        (consisting of a list of integers giving the Hecke eigenvalue
        as a linear combination of the basis specified in the orbit table)
        so in particular v[0] = 0 and v[1] = 1,
        returns a string containing magma code to create the newform
        as a representative q-expansion (type ModFrm) in magma.
        """
        return [
                '// To make the newform (type ModFrm), type "MakeNewformModFrm_%s();".' % (newform.label.replace(".", "_"), ),
                '// This may take a long time!  To see verbose output, uncomment the SetVerbose lines below.',
                'function MakeNewformModFrm_%s(:prec:=%d)' % (newform.label.replace(".","_"), prec),
                '    prec := Min(prec, NextPrime(%d) - 1);' % hecke_nf['maxp'],
                '    chi := MakeCharacter_%d_%s();' % (newform.level, newform.char_orbit_label),
                '    f_vec := qexpCoeffs();',
                '    Kf := Universe(f_vec);',
                '    f_vec := Vector(Kf, [0] cat [f_vec[i]: i in [1..prec]]);',
                '    // SetVerbose("ModularForms", true);',
                '    // SetVerbose("ModularSymbols", true);',
                '    S := CuspidalSubspace(ModularForms(chi, %d));' % newform.weight,
                # weight 1 does not have NewSpace functionality, and anyway that
                # would be an extra possibly expensive linear algebra step
                '    S := BaseChange(S, Kf);',
                '    B := Basis(S, prec + 1);',
                '    S_basismat := Matrix([AbsEltseq(g): g in B]);',
                '    S_basismat := ChangeRing(S_basismat,Kf);',
                '    f_lincom := Solution(S_basismat,f_vec);',
                '    f := &+[f_lincom[i]*Basis(S)[i] : i in [1..#Basis(S)]];',
                '    return f;',
                'end function;'
                ]


    def download_newform_to_magma(self, label, lang='magma'):
        data = db.mf_newforms.lookup(label)
        if data is None:
            return abort(404, "Label not found: %s"%label)
        newform = WebNewform(data)
        hecke_nf = self._get_hecke_nf(label)

        out = []
        newlines = ['']*2;
        if newform.has_exact_qexp:
            out += self._magma_ConvertToHeckeField(newform, hecke_nf) + newlines

        out += self._magma_MakeCharacters(newform, hecke_nf) + newlines

        if newform.hecke_cutters:
            out += self._magma_MakeNewformModSym(newform, hecke_nf) + newlines
        if newform.has_exact_qexp:
            # to return errors
            # this line will never be ran if the data is correct
            if not isinstance(hecke_nf, dict): # pragma: no cover
                return hecke_nf  # pragma: no cover
            out += self._magma_ExtendMultiplicatively() + newlines
            out += self._magma_qexpCoeffs(newform, hecke_nf) + newlines


            # figure out prec
            prec = db.mf_newspaces.lucky({'label': newform.space_label}, 'sturm_bound')
            out += self._magma_MakeNewformModFrm(newform, hecke_nf, prec)

        outstr = "\n".join(out)


        return self._wrap(outstr,
                          label,
                          lang=lang,
                          title='Make newform %s in Magma,'%(label))


from flask import  url_for, redirect, abort
from collections import defaultdict
from ast import literal_eval
from lmfdb.db_backend import db
from lmfdb.db_encoding import Json
from lmfdb.downloader import Downloader
from lmfdb.utils import flash_error
from lmfdb.classical_modular_forms.web_newform import WebNewform, encode_hecke_orbit
from lmfdb.classical_modular_forms.web_space import WebNewformSpace, WebGamma1Space
from lmfdb.classical_modular_forms.magma_newform_download import magma_char_code_string, magma_newform_modsym_cutters_code_string, magma_newform_modfrm_heigs_code_string
from sage.all import ZZ, Gamma0, nth_prime

class CMF_download(Downloader):
    table = db.mf_newforms
    title = 'Classical modular forms'
    data_format = ['N=level', 'k=weight', 'dim', 'N*k^2', 'defining polynomial', 'number field label', 'CM discriminants', 'RM discriminants', 'first few traces']
    columns = ['level', 'weight', 'dim', 'analytic_conductor', 'field_poly', 'nf_label', 'cm_discs', 'rm_discs', 'trace_display']

    def _get_hecke_nf(self, label):
        proj = ['ap', 'hecke_ring_rank', 'hecke_ring_power_basis','hecke_ring_numerators', 'hecke_ring_denominators', 'field_poly','hecke_ring_cyclotomic_generator', 'hecke_ring_character_values', 'maxp']
        data = db.mf_hecke_nf.lucky({'label':label}, proj)
        if not data:
            return abort(404, "Missing coefficient ring information for %s"%label)
        # Make up for db_backend currently deleting Nones
        for elt in proj:
            if elt not in data:
                data[elt] = None

        return data

    def _get_traces(self, label):
        try:
            code = encode_hecke_orbit(label)
        except ValueError:
            return abort(404, "Invalid label: %s"%label)
        traces = db.mf_hecke_traces.search({'hecke_orbit_code':code}, ['n', 'trace_an'], sort=['n'])
        if not traces:
            return abort(404, "No form found for %s"%(label))
        tr = []
        for i, trace in enumerate(traces):
            if trace['n'] != i+1:
                return abort(404, "Database error (please report): %s missing a(%s)"%(label, i+1))
            tr.append(trace['trace_an'])
        return tr

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
            'R.<x> = PolynomialRing(QQ)',
            'f = R(poly_data)',
            'K.<a> = NumberField(f)',
            'betas = [a^i for i in range(len(poly_data))]',
            'convert_elt_to_field = lambda elt: sum(c*beta for c, beta in zip(elt, betas))']

    field_and_convert_sage_generic = [
            'R.<x> = PolynomialRing(QQ)',
            'f = R(poly_data)',
            'K.<a> = NumberField(f)',
            'betas = [K([c/den for c in num]) for num, den in basis_data]',
            'convert_elt_to_field = lambda elt: sum(c*beta for c, beta in zip(elt, betas))']

    field_and_convert_sage_sparse_cyclotomic = [
            'K.<z> = CyclotomicField(poly_data)',
            'convert_elt_to_field = lambda elt: sum(c * z**e for c,e in elt)']

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
            'PS.<q> = PowerSeriesRing(K)',
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

    qexp_dim1_function_body = {'sage': extend_multiplicatively_sage + field_and_convert_sage_dim1 + convert_aps + ['char_values = dict(zip(good_primes, [1]*len(good_primes)))'] + an_code_sage }
    qexp_function_body_generic = {'sage': discrete_log_sage + extend_multiplicatively_sage +  field_and_convert_sage_generic + convert_aps + char_values_sage_generic + an_code_sage}
    qexp_function_body_powbasis = {'sage': discrete_log_sage + extend_multiplicatively_sage +  field_and_convert_sage_powbasis + convert_aps + char_values_sage_generic + an_code_sage}
    qexp_function_body_sparse_cyclotomic = {'sage': discrete_log_sage + extend_multiplicatively_sage +  field_and_convert_sage_sparse_cyclotomic + convert_aps + char_values_sage_generic + an_code_sage}

    def download_qexp(self, label, lang='sage'):
        data = self._get_hecke_nf(label)
        # to return errors
        if not isinstance(data, dict):
            return data

        dim = data['hecke_ring_rank']
        aps = data['ap']
        level, weight = label.split('.')[:2]
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
            hecke_ring_character_values = self.assign(lang, 'hecke_ring_character_values', data['hecke_ring_character_values']);

            if data['hecke_ring_cyclotomic_generator'] > 0:
                func_body =  self.get('qexp_function_body_sparse_cyclotomic',{}).get(lang,[])
                explain += c + ' Each a_p is given as list of pairs\n'
                explain += c + ' Each pair (c, e) corresponds to c*zeta^e\n'
                basis_data = ''
                poly_data =  self.assign(lang, 'poly_data', data['hecke_ring_cyclotomic_generator'])
            else:
                explain += c + ' Each a_p is given as a linear combination\n'
                explain += c + ' of the following basis for the coefficient ring.\n'
                poly_data = '\n' + c + ' The following line gives the coefficients of\n'
                poly_data += c + ' the defining polynomial for the coefficient field.\n'
                poly_data =  self.assign(lang, 'poly_data', data['field_poly'], level = 1)
                if data['hecke_ring_power_basis']:
                    basis_data = '\n' + c + ' The basis for the coefficient ring is just the power basis\n'
                    basis_data += c + ' in the root of the defining polynomial above.\n'
                    basis_data = ''
                    func_body = self.get('qexp_function_body_powbasis',{}).get(lang,[])
                else:
                    basis_data = '\n' + c + ' The entries in the following list give a basis for the\n'
                    basis_data += c + ' coefficient ring in terms of a root of the defining polynomial above.\n'
                    basis_data += c + ' Each line consists of the coefficients of the numerator, and a denominator.\n'
                    basis_data += self.assign(lang,  'basis_data ', zip(data['hecke_ring_numerators'], data['hecke_ring_denominators']))
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
        qexp = [0] + data
        return self._wrap(Json.dumps(qexp),
                          label + '.traces',
                          lang=lang,
                          title='Trace form for %s,'%(label))

    def download_multiple_traces(self, info):
        lang = info.get(self.lang_key,'text').strip()
        query = literal_eval(info.get('query', '{}'))
        count = db.mf_newforms.count(query)
        limit = 1000
        if count > limit:
            msg = "We limit downloads of traces to %d forms" % limit
            flash_error(msg)
            return redirect(url_for('.index'))
        forms = list(db.mf_newforms.search(query, projection=['label', 'hecke_orbit_code']))
        codes = [form['hecke_orbit_code'] for form in forms]
        traces = db.mf_hecke_traces.search({'hecke_orbit_code':{'$in':codes}}, projection=['hecke_orbit_code', 'n', 'trace_an'], sort=[])
        trace_dict = defaultdict(dict)
        for rec in traces:
            trace_dict[rec['hecke_orbit_code']][rec['n']] = rec['trace_an']
        s = ""
        c = self.comment_prefix[lang]
        s += c + ' Query "%s" returned %d forms.\n\n' % (str(info.get('query')), len(forms))
        s += c + ' Below are two lists, one called labels, and one called traces (in matching order).\n'
        s += c + ' Each list of traces starts with a_1 (giving the dimension).\n\n'
        s += 'labels ' + self.assignment_defn[lang] + self.start_and_end[lang][0] + '\\\n'
        s += ',\n'.join(form['label'] for form in forms)
        s += self.start_and_end[lang][1] + '\n\n'
        s += 'traces ' + self.assignment_defn[lang] + self.start_and_end[lang][0] + '\\\n'
        s += ',\n'.join('[' + ', '.join(str(trace_dict[form['hecke_orbit_code']][n]) for n in range(1,1001)) + ']' for form in forms)
        s += self.start_and_end[lang][1]
        return self._wrap(s, 'mf_newforms_traces', lang=lang)

    def _download_cc(self, label, lang, col, suffix, title):
        try:
            code = encode_hecke_orbit(label)
        except ValueError:
            return abort(404, "Invalid label: %s"%label)
        if not db.mf_hecke_cc.exists({'hecke_orbit_code':code}):
            return abort(404, "No form found for %s"%(label))
        def cc_generator():
            for ev in db.mf_hecke_cc.search(
                    {'hecke_orbit_code':code},
                    ['lfunction_label',
                     'embedding_root_real',
                     'embedding_root_imag',
                     col],
                    sort=['conrey_label', 'embedding_index']):
                D = {'label':ev.get('lfunction_label'),
                     col:ev.get(col)}
                root = (ev.get('embedding_root_real'),
                        ev.get('embedding_root_imag'))
                if root != (None, None):
                    D['root'] = root
                yield Json.dumps(D) + '\n\n'
        filename = label + suffix
        title += ' for newform %s,'%(label)
        return self._wrap_generator(cc_generator(),
                                    filename,
                                    lang=lang,
                                    title=title)

    def download_cc_data(self, label, lang='text'):
        return self._download_cc(label, lang, 'an', '.cplx', 'Complex embeddings')

    def download_satake_angles(self, label, lang='text'):
        return self._download_cc(label, lang, 'angles', '.angles', 'Satake angles')

    def download_newform(self, label, lang='text'):
        data = db.mf_newforms.lookup(label)
        if data is None:
            return abort(404, "Label not found: %s"%label)
        form = WebNewform(data)
        form.setup_cc_data({'m':'1-%s'%form.dim,
                            'n':'1-1000'})
        if form.has_exact_qexp:
            data['qexp'] = form.qexp
            data['traces'] = form.texp
        if form.has_complex_qexp:
            data['complex_embeddings'] = form.cc_data
        return self._wrap(Json.dumps(data),
                          label,
                          lang=lang,
                          title='Stored data for newform %s,'%(label))

    def download_newform_to_magma(self, label, lang='magma'):
        data = db.mf_newforms.lookup(label)
        if data is None:
            return abort(404, "Label not found: %s"%label)
        form = WebNewform(data)

        outstr = magma_char_code_string(form)
        if form.hecke_cutters:
            outstr += magma_newform_modsym_cutters_code_string(form,include_char=False)
        if form.has_exact_qexp:

            hecke_data = self._get_hecke_nf(label);
            # to return errors
            if not isinstance(data,dict):
                return data


            # figure out prec
            if form.hecke_cutters:
                prec  = max(elt[0] for elt in form.hecke_cutters)
            else:
                # Using Sec 9.4 of Stein - Modular forms, a computational approach. 
                # it is key to cast these ints to ZZ for the code below to work
                level, weight, char_conductor = map(ZZ, [form.level, form.weight, form.char_conductor])
                m = Gamma0(level).index()
                if level.is_squarefree():
                    # Theorem 9.21 - Improved Sturm bound for cusp forms with square free level
                    i = len(level.prime_divisors())
                    prec = ((m*weight)/ (12 * 2**i)).floor()
                elif level > 4:
                    # Theorem 9.22 - Improved Sturm bound for cusp forms without square free level
                    notI = ZZ(level/char_conductor).prime_divisors();
                    levelp = level.prime_divisors()
                    I = [p  for p in levelp if p not in notI]
                    i = len(I)
                    prec = max(((m*weight)/ (12 * 2**i)).floor(), 0 if len(I) == 0 else max(I))
                else:
                    # Theorem 9.19 - Generic Sturm bound for cusp forms
                    prec = (m*weight/12  - (m - 1)/level).floor()

            if prec == 1:
                # if the dim > 1, we need at least one ap != 0
                # so we can pin down the form in terms of the Z basis
                if hecke_data['hecke_ring_cyclotomic_generator'] > 0:
                    zero = lambda x: len(x) == 0
                else:
                    zero = lambda x: all(elt == 0 for elt in x)
                for i, elt in enumerate(hecke_data['ap']):
                    if not zero(elt):
                        prec = nth_prime(i+1)
                        break

            if prec > hecke_data['maxp']:
                return abort(404, "Not enough eigenvalues to reconstruct form in Magma")
            outstr += magma_newform_modfrm_heigs_code_string(prec, form, hecke_data, include_char=False)
        return self._wrap(outstr,
                          label,
                          lang=lang,
                          title='Make newform %s in Magma,'%(label))

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

    def download_space_trace(self, label, lang='text'):
        if label.count('.') == 1:
            traces = db.mf_gamma1.lookup(label, projection='traces')
        elif label.count('.') == 2:
            traces = db.mf_newspaces.lookup(label, projection='traces')
        else:
            return abort(404, "Malformed label: %s"%label)
        if traces is None:
            return abort(404, "Label not found: %s"%label)
        return self._wrap(Json.dumps([0] + traces),
                          label + '.traces',
                          lang=lang,
                          title='Trace form for %s,'%(label))

    def download_spaces(self, info):
        lang = info.get(self.lang_key,'text').strip()
        query = literal_eval(info.get('query', '{}'))
        proj = ['label', 'analytic_conductor', 'char_labels', 'char_order']
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


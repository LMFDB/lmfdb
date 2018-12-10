from flask import render_template, url_for, redirect, abort, request, flash
from markupsafe import Markup
from collections import defaultdict
from ast import literal_eval
from lmfdb.db_backend import db
from lmfdb.db_encoding import Json
from lmfdb.classical_modular_forms import cmf
from lmfdb.search_parsing import parse_ints, parse_floats, parse_bool, parse_bool_unknown, parse_primes, parse_nf_string, parse_noop, parse_equality_constraints, integer_options, search_parser, parse_subset
from lmfdb.search_wrapper import search_wrap
from lmfdb.downloader import Downloader
from lmfdb.utils import flash_error, to_dict, comma, display_knowl, polyquo_knowl
from lmfdb.WebNumberField import field_pretty, nf_display_knowl
from lmfdb.classical_modular_forms.web_newform import WebNewform, convert_newformlabel_from_conrey, encode_hecke_orbit, quad_field_knowl
from lmfdb.classical_modular_forms.web_space import WebNewformSpace, WebGamma1Space, DimGrid, convert_spacelabel_from_conrey, get_bread, get_search_bread, get_dim_bread, newform_search_link, ALdim_table, OLDLABEL_RE as OLD_SPACE_LABEL_RE
from lmfdb.display_stats import StatsDisplay, boolean_unknown_format
from sage.databases.cremona import class_to_int
from sage.all import ZZ, next_prime, cartesian_product_iterator, cached_function
import re

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Classical modular form labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

def credit():
    return "Alex J Best, Jonathan Bober, Andrew Booker, Edgar Costa, John Cremona, David Roe, Andrew Sutherland, John Voight"

@cached_function
def Nk2_bound():
    return db.mf_newforms.max('Nk2')
@cached_function
def weight_bound():
    return db.mf_newforms.max('weight')

@cached_function
def level_bound():
    return db.mf_newforms.max('level')


def ALdims_knowl(al_dims, level, weight):
    dim_dict = {}
    for vec, dim, cnt in al_dims:
        dim_dict[tuple(ev for (p, ev) in vec)] = dim
    short = "+".join(r'\(%s\)'%dim_dict.get(vec,0) for vec in cartesian_product_iterator([[1,-1] for _ in range(len(al_dims[0][0]))]))
    # We erase plus_dim and minus_dim if they're obvious
    AL_table = ALdim_table(al_dims, level, weight)
    return r'<a title="[ALdims]" knowl="dynamic_show" kwargs="%s">%s</a>'%(AL_table, short)

def set_info_funcs(info):
    info["mf_url"] = lambda mf: url_for_label(mf['label'])
    def nf_link(mf):
        nf_label = mf.get('nf_label')
        if nf_label:
            name = field_pretty(nf_label)
            if name == nf_label and len(name) > 16:
                # truncate if too long
                parts = nf_label.split('.')
                parts[2] = r'\(\cdots\)'
                name = '.'.join(parts)
            return nf_display_knowl(nf_label, name)
        elif mf['dim'] == mf['char_degree'] and mf.get('field_poly_root_of_unity'):
            return r'\(\Q(\zeta_{%s})\)' % mf['field_poly_root_of_unity']
        else:
            poly = mf.get('field_poly')
            if poly:
                return polyquo_knowl(poly)
            return ""

    info["nf_link"] = nf_link

    def quad_links(mf, is_field, disc_field, bound = None):
        if mf[is_field]:
            discs = mf[disc_field]
            if bound:
                discs = discs[:bound]
            return ', '.join( map(quad_field_knowl, discs) )
        else:
            return "No"
    info["self_twist_link"] = lambda mf: quad_links(mf, 'is_self_twist', 'self_twist_discs', bound = 1)
    info["cm_link"] = lambda mf: quad_links(mf, 'is_cm', 'cm_discs')
    info["rm_link"] = lambda mf: quad_links(mf, 'is_rm', 'rm_discs')
    info["cm_col"] = info.get('cm_discs') is not None or 'cm' in  info.get('has_self_twist', '')
    info["rm_col"] = info.get('rm_discs') is not None or 'rm' in  info.get('has_self_twist', '')
    info["self_twist_col"] = not (info["cm_col"] or info["rm_col"])


    info["space_type"] = {'M':'Modular forms',
                          'S':'Cusp forms',
                          'E':'Eisenstein series'}
    def display_AL(results):
        if not results:
            return False
        N = results[0]['level']
        if not all(mf['level'] == N for mf in results):
            return False
        if N == 1:
            return False
        return all(mf['char_order'] == 1 for mf in results)
    info["display_AL"] = display_AL

    def display_Fricke(results):
        # only called if display_AL has returned False
        return any(mf['char_order'] == 1 for mf in results)
    info["display_Fricke"] = display_Fricke

    def all_weight1(results):
        return all(mf.get('weight') == 1 for mf in results)
    info["all_weight1"] = all_weight1

    def all_D2(results):
        return all(mf.get('projective_image') == 'D2' for mf in results)
    info["all_D2"] = all_D2


    # assumes the format Dn A4 S4 S5
    info["display_projective_image"] = lambda mf: ('%s_{%s}' % (mf['projective_image'][:1], mf['projective_image'][1:])) if 'projective_image' in mf else ''

    def display_decomp(space):
        hecke_orbit_dims = space.get('hecke_orbit_dims')
        if hecke_orbit_dims is None: # shouldn't happen
            return 'unknown'
        dim_dict = defaultdict(int)
        terms = []
        for dim in hecke_orbit_dims:
            dim_dict[dim] += 1
        for dim in sorted(dim_dict.keys()):
            count = dim_dict[dim]
            query = {'weight':space['weight'],
                     'char_label':'%s.%s'%(space['level'],space['char_orbit_label']),
                     'dim':dim}
            short = '+'.join([r'\(%s\)'%dim]*count)
            if count == 1:
                query['jump'] = 'yes'
            link = newform_search_link(short, **query)
            terms.append(link)
        return r'+'.join(terms)
    info['display_decomp'] = display_decomp

    def display_ALdims(space):
        al_dims = space.get('AL_dims')
        if al_dims:
            return ALdims_knowl(al_dims, space['level'], space['weight'])
        else:
            return ''
    info['display_ALdims'] = display_ALdims

@cmf.route("/")
def index():
    if len(request.args) > 0:
        info = to_dict(request.args)
        # hidden_search_type for prev/next buttons
        info['search_type'] = search_type = info.get('search_type', info.get('hidden_search_type', 'List'))

        if search_type == 'Dimensions':
            for key in newform_only_fields:
                if key in info:
                    return dimension_form_search(info)
            return dimension_space_search(info)
        elif search_type == 'Spaces':
            return space_search(info)
        elif search_type == 'Traces':
            return trace_search(info)
        elif search_type == 'Random':
            return newform_search(info, random=True)
        elif search_type == 'List':
            return newform_search(info)
        assert False
    info = {"stats": CMF_stats()}
    newform_labels = ('1.12.a.a','11.2.a.a', '23.2.a.a', '39.1.d.a', '49.2.e.b', '95.6.a.a', '124.1.i.a', '148.1.f.a', '633.1.m.b', '983.2.c.a')
    info["newform_list"] = [ {'label':label,'url':url_for_label(label)} for label in newform_labels ]
    space_labels = ('20.5','60.2','55.3.d', '147.5.n', '148.4.q', '164.4.o', '244.4.w', '292.3.u', '847.2.f', '309.3.n', '356.3.n', '580.2.be')
    info["space_list"] = [ {'label':label,'url':url_for_label(label)} for label in space_labels ]
    info["weight_list"] = ('1', '2', '3', '4', '5', '6-10', '11-20', '21-40', '41-%d' % weight_bound() )
    info["level_list"] = ('1', '2-100', '101-500', '501-1000', '1001-2000', '2001-%d' % level_bound() )
    return render_template("cmf_browse.html",
                           info=info,
                           credit=credit(),
                           title="Classical Modular Forms",
                           learnmore=learnmore_list(),
                           bread=get_bread())

@cmf.route("/random")
def random_form():
    if len(request.args) > 0:
        info = to_dict(request.args)
        return newform_search(info, random=True)
    else:
        label = db.mf_newforms.random()
        return redirect(url_for_label(label), 307)

# Add routing for specifying an initial segment of level, weight, etc.
# Also url_for_...

def render_newform_webpage(label):
    try:
        newform = WebNewform.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404, err.args)
    info = to_dict(request.args)
    info['format'] = info.get('format','embed' if newform.dim > 1 else 'satake')
    p, maxp = 2, 10
    if info['format'] in ['satake', 'satake_angle']:
        while p <= maxp:
            if newform.level % p == 0:
                maxp = next_prime(maxp)
            p = next_prime(p)
    errs = []
    info['n'] = info.get('n', '2-%s'%maxp)
    try:
        info['CC_n'] = integer_options(info['n'], 1000)
    except (ValueError, TypeError) as err:
        info['n'] = '2-%s'%maxp
        info['CC_n'] = range(2,maxp+1)
        if err.args and err.args[0] == 'Too many options':
            errs.append(r"Only \(a_n\) up to %s are available"%(newform.cqexp_prec-1))
        else:
            errs.append("<span style='color:black'>n</span> must be an integer, range of integers or comma separated list of integers")
    maxm = min(newform.dim, 20)
    info['m'] = info.get('m', '1-%s'%maxm)
    try:
        info['CC_m'] = integer_options(info['m'], 1000)
    except (ValueError, TypeError) as err:
        info['m'] = '1-%s'%maxm
        info['CC_m'] = range(1,maxm+1)
        if err.args and err.args[0] == 'Too many options':
            errs.append('Web interface only supports 1000 embeddings at a time.  Use download link to get more (may take some time).')
        else:
            errs.append("<span style='color:black'>Embeddings</span> must be an integer, range of integers or comma separated list of integers")
    try:
        info['prec'] = int(info.get('prec',6))
        if info['prec'] < 1 or info['prec'] > 15:
            raise ValueError
    except (ValueError, TypeError):
        info['prec'] = 6
        errs.append("<span style='color:black'>Precision</span> must be a positive integer, at most 15 (for higher precision, use the download button)")
    newform.setup_cc_data(info)
    if newform.cqexp_prec != 0 and max(info['CC_n']) >= newform.cqexp_prec:
        errs.append(r"Only \(a_n\) up to %s are available"%(newform.cqexp_prec-1))
    if errs:
        flash(Markup("<br>".join(errs)), "error")
    return render_template("cmf_newform.html",
                           info=info,
                           newform=newform,
                           properties2=newform.properties,
                           downloads=newform.downloads,
                           credit=credit(),
                           bread=newform.bread,
                           learnmore=learnmore_list(),
                           title=newform.title,
                           friends=newform.friends)

def render_space_webpage(label):
    try:
        space = WebNewformSpace.by_label(label)
    except (TypeError,KeyError,ValueError) as err:
        return abort(404, err.args)
    info = {'results':space.newforms} # so we can reuse search result code
    set_info_funcs(info)
    return render_template("cmf_space.html",
                           info=info,
                           space=space,
                           properties2=space.properties,
                           downloads=space.downloads,
                           credit=credit(),
                           bread=space.bread,
                           learnmore=learnmore_list(),
                           title=space.title,
                           friends=space.friends)

def render_full_gamma1_space_webpage(label):
    try:
        space = WebGamma1Space.by_label(label)
    except (TypeError,KeyError,ValueError) as err:
        return abort(404, err.args)
    info={}
    set_info_funcs(info)
    return render_template("cmf_full_gamma1_space.html",
                           info=info,
                           space=space,
                           properties2=space.properties,
                           downloads=space.downloads,
                           credit=credit(),
                           bread=space.bread,
                           learnmore=learnmore_list(),
                           title=space.title,
                           friends=space.friends)

@cmf.route("/<level>/")
def by_url_level(level):
    if "." in level:
        return redirect(url_for_label(label = level), code=301)
    info = to_dict(request.args)
    if 'level' in info:
        return redirect(url_for('.index', **request.args), code=307)
    else:
        info['level'] = level
    return newform_search(info)

@cmf.route("/<int:level>/<int:weight>/")
def by_url_full_gammma1_space_label(level, weight):
    label = str(level)+"."+str(weight)
    return render_full_gamma1_space_webpage(label)

@cmf.route("/<int:level>/<int:weight>/<char_orbit_label>/")
def by_url_space_label(level, weight, char_orbit_label):
    label = str(level)+"."+str(weight)+"."+char_orbit_label
    return render_space_webpage(label)

# Backward compatibility from before 2018
@cmf.route("/<int:level>/<int:weight>/<int:conrey_label>/")
def by_url_space_conreylabel(level, weight, conrey_label):
    label = convert_spacelabel_from_conrey(str(level)+"."+str(weight)+"."+str(conrey_label))
    return redirect(url_for_label(label), code=301)

@cmf.route("/<int:level>/<int:weight>/<char_orbit_label>/<hecke_orbit>/")
def by_url_newform_label(level, weight, char_orbit_label, hecke_orbit):
    label = str(level)+"."+str(weight)+"."+char_orbit_label+"."+hecke_orbit
    return render_newform_webpage(label)

# Backward compatibility from before 2018
@cmf.route("/<int:level>/<int:weight>/<int:conrey_label>/<hecke_orbit>/")
def by_url_newform_conreylabel(level, weight, conrey_label, hecke_orbit):
    label = convert_newformlabel_from_conrey(str(level)+"."+str(weight)+"."+str(conrey_label)+"."+hecke_orbit)
    return redirect(url_for_label(label), code=301)

# From L-functions
@cmf.route("/<int:level>/<int:weight>/<char_orbit_label>/<hecke_orbit>/<int:conrey_label>/<int:embedding>/")
def by_url_newform_conreylabel_with_embedding(level, weight, char_orbit_label, hecke_orbit, conrey_label, embedding):
    assert conrey_label > 0
    assert embedding > 0
    return by_url_newform_label(level, weight, char_orbit_label, hecke_orbit)




def url_for_label(label):
    slabel = label.split(".")
    if len(slabel) == 4:
        return url_for(".by_url_newform_label", level=slabel[0], weight=slabel[1], char_orbit_label=slabel[2], hecke_orbit=slabel[3])
    elif len(slabel) == 3:
        return url_for(".by_url_space_label", level=slabel[0], weight=slabel[1], char_orbit_label=slabel[2])
    elif len(slabel) == 2:
        return url_for(".by_url_full_gammma1_space_label", level=slabel[0], weight=slabel[1])
    elif len(slabel) == 1:
        return url_for(".by_url_level", level=slabel[0])
    else:
        raise ValueError("Invalid label")

def jump_box(info):
    jump = info.pop("jump").strip()
    errmsg = None
    if OLD_SPACE_LABEL_RE.match(jump):
        jump = convert_spacelabel_from_conrey(jump)
    #handle direct trace_hash search
    if re.match(r'^\#\d+$',jump) and long(jump[1:]) < 2**61:
        label = db.mf_newforms.lucky({'trace_hash': long(jump[1:].strip())}, projection="label")
        if label:
            return redirect(url_for_label(label), 301)
        else:
            errmsg = "hash %s not found"
    elif jump == 'yes':
        query = {}
        newform_parse(info, query)
        jump = db.mf_newforms.lucky(query, 'label')
        if jump is None:
            errmsg = "There are no newforms specified by the query %s"%(query)
    if errmsg is None:
        try:
            return redirect(url_for_label(jump), 301)
        except ValueError:
            errmsg = "%s is not a valid newform or space label"
    flash_error (errmsg, jump)
    return redirect(url_for(".index"))

class CMF_download(Downloader):
    table = db.mf_newforms
    title = 'Classical modular forms'
    data_format = ['N=level', 'k=weight', 'dim', 'N*k^2', 'defining polynomial', 'number field label', 'CM discriminant', 'first few traces']
    columns = ['level','weight', 'dim', 'analytic_conductor', 'field_poly', 'nf_label', 'cm_discs', 'rm_discs', 'trace_display']

    def _get_hecke_nf(self, label):
        try:
            code = encode_hecke_orbit(label)
        except ValueError:
            return abort(404, "Invalid label: %s"%label)
        eigenvals = db.mf_hecke_nf.search({'hecke_orbit_code':code}, ['n','an','trace_an'], sort=['n'])
        if not eigenvals:
            return abort(404, "No form found for %s"%(label))
        data = []
        for i, ev in enumerate(eigenvals):
            if ev['n'] != i+1:
                return abort(404, "Database error (please report): %s missing a(%s)"%(label, i+1))
            data.append((ev.get('an'),ev.get('trace_an')))
        return data

    qexp_function_body = {'sage': ['R.<x> = PolynomialRing(QQ)',
                                   'f = R(poly_data)',
                                   'K.<a> = NumberField(f)',
                                   'betas = [K([c/den for c in num]) for num, den in basis_data]',
                                   'S.<q> = PowerSeriesRing(K)',
                                   'return S([sum(c*beta for c, beta in zip(coeffs, betas)) for coeffs in data])']}
    qexp_dim1_function_body = {'sage': ['S.<q> = PowerSeriesRing(QQ)',
                                        'return S(data)']}
    def download_qexp(self, label, lang='sage'):
        data = self._get_hecke_nf(label)
        if not isinstance(data,list):
            return data
        #filename = label + self.file_suffix[lang]
        dim = None
        qexp = []
        for an, trace_an in data:
            if not an:
                # only had traces
                return abort(404, "No q-expansion found for %s"%(label))
            if dim is None:
                dim = len(an)
                qexp.append([0] * dim)
            qexp.append(an)
        c = self.comment_prefix[lang]
        func_start = self.get('function_start',{}).get(lang,[])
        func_end = self.get('function_end',{}).get(lang,[])
        explain = '\n'
        data = 'data ' + self.assignment_defn[lang] + self.start_and_end[lang][0] + '\\\n'
        code = ''
        if dim == 1:
            func_body = self.get('qexp_dim1_function_body',{}).get(lang,[])
            data += ', '.join([an[0] for an in qexp])
            data += self.start_and_end[lang][1]
            explain += c + ' The q-expansion is given as a list of integers.\n'
            explain += c + ' Each entry gives a Hecke eigenvalue a_n.\n'
            basis = poly = ''
        else:
            hecke_data = db.mf_newforms.lucky({'label':label},['hecke_ring_numerators','hecke_ring_denominators', 'field_poly'])
            if not hecke_data or not hecke_data.get('hecke_ring_numerators') or not hecke_data.get('hecke_ring_denominators') or not hecke_data.get('field_poly'):
                return abort(404, "Missing coefficient ring information for %s"%label)
            start = self.delim_start[lang]
            end = self.delim_end[lang]
            func_body = self.get('qexp_function_body',{}).get(lang,[])
            data += ",\n".join(start + ",".join(str(c) for c in an) + end for an in qexp)
            data += self.start_and_end[lang][1] + '\n'
            explain += c + ' The q-expansion is given as a list of lists.\n'
            explain += c + ' Each entry gives a Hecke eigenvalue a_n.\n'
            explain += c + ' Each a_n is given as a linear combination\n'
            explain += c + ' of the following basis for the coefficient ring.\n'
            basis = '\n' + c + ' The entries in the following list give a basis for the\n'
            basis += c + ' coefficient ring in terms of a root of the defining polynomial above.\n'
            basis += c + ' Each line consists of the coefficients of the numerator, and a denominator.\n'
            basis += 'basis_data ' + self.assignment_defn[lang] + self.start_and_end[lang][0] + '\\\n'
            basis += ",\n".join(start + start + ",".join(str(c) for c in num) + end + ', %s' % den + end for num, den in zip(hecke_data['hecke_ring_numerators'], hecke_data['hecke_ring_denominators']))
            basis += self.start_and_end[lang][1] + '\n'
            if lang in ['sage']:
                explain += c + ' To create the q-expansion as a power series, type "qexp%smake_data()%s"\n' % (self.assignment_defn[lang], self.line_end[lang])
            poly = '\n' + c + ' The following line gives the coefficients of\n'
            poly += c + ' the defining polynomial for the coefficient field.\n'
            poly += 'poly_data ' + self.assignment_defn[lang] + self.start_and_end[lang][0]
            poly += ', '.join(str(c) for c in hecke_data['field_poly'])
            poly += self.start_and_end[lang][1] + '\n'
        if lang in ['sage']:
            code = '\n' + '\n'.join(func_start) + '\n'
            code += '    ' + '\n    '.join(func_body) + '\n'
            code += '\n'.join(func_end)
        return self._wrap(explain + code + poly + basis + data,
                          label + '.qexp',
                          lang=lang,
                          title='q-expansion of newform %s,'%(label))

    def download_traces(self, label, lang='text'):
        data = self._get_hecke_nf(label)
        if not isinstance(data,list):
            return data
        qexp = [0] + [trace_an for an, trace_an in data]
        return self._wrap(Json.dumps(qexp),
                          label + '.traces',
                          lang=lang,
                          title='Trace form for %s,'%(label))

    def download_multiple_traces(self, info):
        lang = info.get(self.lang_key,'text').strip()
        query = literal_eval(info.get('query','{}'))
        forms = list(db.mf_newforms.search(query, projection=['label', 'hecke_orbit_code']))
        codes = [form['hecke_orbit_code'] for form in forms]
        traces = db.mf_hecke_nf.search({'hecke_orbit_code':{'$in':codes}}, projection=['hecke_orbit_code', 'n','trace_an'], sort=[])
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
        s += ',\n'.join('[' + ','.join(str(trace_dict[form['hecke_orbit_code']][n]) for n in range(1,1001)) + ']' for form in forms)
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
                    sort=['conrey_label','embedding_index']):
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
        for attr in ['level','weight','label','oldspaces']:
            data[attr] = getattr(space, attr)
        data['newspaces'] = [spc['label'] for spc, forms in space.decomp]
        data['newforms'] = sum([[form['label'] for form in forms] for spc, forms in space.decomp], [])
        data['dimgrid'] = space.dim_grid._grid
        return self._wrap(Json.dumps(data),
                          label,
                          lang=lang,
                          title='Stored data for newspace %s,'%(label))

@cmf.route("/download_qexp/<label>")
def download_qexp(label):
    return CMF_download().download_qexp(label, lang='sage')

@cmf.route("/download_traces/<label>")
def download_traces(label):
    return CMF_download().download_traces(label)

@cmf.route("/download_cc_data/<label>")
def download_cc_data(label):
    return CMF_download().download_cc_data(label)

@cmf.route("/download_satake_angles/<label>")
def download_satake_angles(label):
    return CMF_download().download_satake_angles(label)

@cmf.route("/download_newform/<label>")
def download_newform(label):
    return CMF_download().download_newform(label)

@cmf.route("/download_newspace/<label>")
def download_newspace(label):
    return CMF_download().download_newspace(label)

@cmf.route("/download_full_space/<label>")
def download_full_space(label):
    return CMF_download().download_full_space(label)

@search_parser(default_name='Character orbit label') # see SearchParser.__call__ for actual arguments when calling
def parse_character(inp, query, qfield, level_field='level', conrey_field='char_labels'):
    pair = inp.split('.')
    if len(pair) != 2:
        raise ValueError("It must be of the form N.i")
    level, orbit = pair
    level = int(level)
    if level_field in query and query[level_field] != level:
        raise ValueError("Inconsistent level")
    query[level_field] = level
    if orbit.isalpha():
        query[qfield] = class_to_int(orbit) + 1 # we don't store the prim_orbit_label
    else:
        if conrey_field is None:
            raise ValueError("You must use the orbit label when searching by primitive character")
        query[conrey_field] = {'$contains': int(orbit)}

newform_only_fields = ['dim','nf_label','is_self_twist','cm_discs','rm_discs','is_twist_minimal','has_inner_twist','analytic_rank']
def common_parse(info, query):
    parse_ints(info, query, 'weight', name="Weight")
    if 'weight_parity' in info:
        parity=info['weight_parity']
        if parity == 'even':
            query['odd_weight'] = False
        elif parity == 'odd':
            query['odd_weight'] = True
    if 'char_parity' in info:
        parity=info['char_parity']
        if parity == 'even':
            query['char_parity'] = 1
        elif parity == 'odd':
            query['char_parity'] = -1
    parse_ints(info, query, 'level', name="Level")
    parse_floats(info, query, 'analytic_conductor', name="Analytic conductor")
    parse_character(info, query, 'char_label', qfield='char_orbit_index')
    parse_character(info, query, 'prim_label', qfield='prim_orbit_index', level_field='char_conductor', conrey_field=None)
    parse_ints(info, query, 'char_order', name="Character order")
    prime_mode = info['prime_quantifier'] = info.get('prime_quantifier','exact')
    parse_primes(info, query, 'level_primes', name='Primes dividing level', mode=prime_mode, radical='level_radical')

def parse_self_twist(info, query):
    # self_twist_values = [('', 'unrestricted'), ('yes', 'has self-twist'), ('cm', 'has CM'), ('rm', 'has RM'), ('cm_and_rm', 'has CM and RM'), ('no', 'no self-twists') ]
    translate = {'cm': '1', 'rm': '2', 'cm_and_rm':'3'}
    inp = info.get('has_self_twist')
    if inp:
        if inp in ['no','yes']:
            info['is_self_twist'] = inp
            parse_bool(info, query, 'is_self_twist', name='Has self-twist')
        else:
            try:
                info['self_twist_type'] = translate[inp]
                parse_ints(info, query, 'self_twist_type',name='Has self-twist')
            except KeyError:
                raise ValueError('%s not in %s' % (inp, translate.keys()))

def parse_discriminant(d, sign = 0):
    d = int(d)
    if d*sign < 0:
        raise ValueError('%d %s 0' % (d, '<' if sign > 0 else '>'))
    if (d % 4) not in [0, 1]:
        raise ValueError('%d != 0 or 1 mod 4' % d)
    return d


def newform_parse(info, query):
    common_parse(info, query)
    parse_ints(info, query, 'dim', name="Dimension")
    parse_nf_string(info, query,'nf_label', name="Coefficient field")
    parse_self_twist(info, query)
    parse_subset(info, query, 'cm_discs', name="CM discriminant", parse_singleton=lambda d: parse_discriminant(d, -1))
    parse_subset(info, query, 'rm_discs', name="RM discriminant", parse_singleton=lambda d: parse_discriminant(d, 1))
    parse_bool(info, query, 'is_twist_minimal')
    parse_bool_unknown(info, query, 'has_inner_twist')
    parse_ints(info, query, 'analytic_rank')
    parse_noop(info, query, 'atkin_lehner_string')
    parse_ints(info, query, 'fricke_eigenval')
    parse_bool_unknown(info, query, 'is_self_dual')
    parse_noop(info, query, 'projective_image')
    parse_noop(info, query, 'projective_image_type')
    parse_ints(info, query, 'artin_degree', name="Artin degree")

@search_wrap(template="cmf_newform_search_results.html",
             table=db.mf_newforms,
             title='Newform Search Results',
             err_title='Newform Search Input Error',
             shortcuts={'jump':jump_box,
                        'download':CMF_download(),
                        #'download_exact':download_exact,
                        #'download_complex':download_complex
             },
             url_for_label=url_for_label,
             bread=get_search_bread,
             learnmore=learnmore_list,
             credit=credit)
def newform_search(info, query):
    newform_parse(info, query)
    set_info_funcs(info)

def trace_postprocess(res, info, query):
    if res:
        hecke_codes = [mf['hecke_orbit_code'] for mf in res]
        trace_dict = defaultdict(dict)
        for rec in db.mf_hecke_nf.search({'n':{'$in': info['Tr_n']}, 'hecke_orbit_code':{'$in':hecke_codes}}, projection=['hecke_orbit_code', 'n', 'trace_an'], sort=[]):
            trace_dict[rec['hecke_orbit_code']][rec['n']] = rec['trace_an']
        for mf in res:
            mf['tr_an'] = trace_dict[mf['hecke_orbit_code']]
    return res

@search_wrap(template="cmf_trace_search_results.html",
             table=db.mf_newforms,
             title='Newform Search Results',
             err_title='Newform Search Input Error',
             shortcuts={'jump':jump_box,
                        'download':CMF_download().download_multiple_traces},
             projection=['label','dim','hecke_orbit_code'],
             postprocess=trace_postprocess,
             bread=get_search_bread,
             learnmore=learnmore_list,
             credit=credit)
def trace_search(info, query):
    newform_parse(info, query)
    parse_equality_constraints(info, query, 'an_constraints', qfield='traces', shift=-1)
    set_info_funcs(info)
    ns = info['n'] = info.get('n', '1-40')
    n_primality = info['n_primality'] = info.get('n_primality', 'primes')
    Trn = integer_options(ns, 1000)
    if n_primality == 'primes':
        Trn = [n for n in Trn if n > 1 and ZZ(n).is_prime()]
    elif n_primality == 'prime_powers':
        Trn = [n for n in Trn if n > 1 and ZZ(n).is_prime_power()]
    else:
        Trn = [n for n in Trn if n > 1]
    info['Tr_n'] = Trn

def set_rows_cols(info, query):
    """
    Sets weight_list and level_list, which are the row and column headers
    """
    info['weight_list'] = integer_options(info['weight'], max_opts=100)
    if 'odd_weight' in query:
        if query['odd_weight']:
            info['weight_list'] = [k for k in info['weight_list'] if k%2 == 1]
        else:
            info['weight_list'] = [k for k in info['weight_list'] if k%2 == 0]
    info['level_list'] = integer_options(info['level'], max_opts=2000)
    if len(info['weight_list']) * len(info['level_list']) > 10000:
        raise ValueError("Table too large: must have at most 10000 entries")

def has_data(N, k):
    return N*k*k <= Nk2_bound()

def dimension_space_postprocess(res, info, query):
    set_rows_cols(info, query)
    dim_dict = {(N,k):DimGrid() for N in info['level_list'] for k in info['weight_list'] if has_data(N,k)}
    for space in res:
        dims = DimGrid.from_db(space)
        N = space['level']
        k = space['weight']
        dim_dict[N,k] += dims
    if query.get('char_order') == 1:
        def url_generator(N, k):
            return url_for(".by_url_space_label", level=N, weight=k, char_orbit_label="a")
    else:
        def url_generator(N, k):
            return url_for(".by_url_full_gammma1_space_label", level=N, weight=k)
    def pick_table(entry, X, typ):
        return entry[X][typ]
    def switch_text(X, typ):
        space_type = {'M':' modular forms',
                      'S':' cusp forms',
                      'E':' Eisenstein series'}
        return typ.capitalize() + space_type[X]
    info['pick_table'] = pick_table
    info['cusp_types'] = ['M','S','E']
    info['newness_types'] = ['all','new','old']
    info['one_type'] = False
    info['switch_text'] = switch_text
    info['url_generator'] = url_generator
    info['has_data'] = has_data
    return dim_dict

def dimension_form_postprocess(res, info, query):
    urlgen_info = dict(info)
    urlgen_info['search_type'] = ''
    urlgen_info['count'] = 50
    set_rows_cols(info, query)
    dim_dict = {(N,k):0 for N in info['level_list'] for k in info['weight_list'] if has_data(N,k)}
    for form in res:
        N = form['level']
        k = form['weight']
        dim_dict[N,k] += form['dim']
    def url_generator(N, k):
        info_copy = dict(urlgen_info)
        info_copy['submit'] = 'Search'
        info_copy['level'] = str(N)
        info_copy['weight'] = str(k)
        return url_for(".index", **info_copy)
    def pick_table(entry, X, typ):
        # Only support one table
        return entry
    info['pick_table'] = pick_table
    info['cusp_types'] = ['S']
    info['newness_types'] = ['new']
    info['one_type'] = True
    info['url_generator'] = url_generator
    info['has_data'] = has_data
    return dim_dict

@search_wrap(template="cmf_dimension_search_results.html",
             table=db.mf_newforms,
             title='Dimension Search Results',
             err_title='Dimension Search Input Error',
             per_page=None,
             postprocess=dimension_form_postprocess,
             bread=get_dim_bread,
             learnmore=learnmore_list,
             credit=credit)
def dimension_form_search(info, query):
    info.pop('count',None) # remove per_page so that we get all results
    if 'weight' not in info:
        info['weight'] = '1-12'
    if 'level' not in info:
        info['level'] = '1-24'
    newform_parse(info, query)

@search_wrap(template="cmf_dimension_search_results.html",
             table=db.mf_newspaces,
             title='Dimension Search Results',
             err_title='Dimension Search Input Error',
             per_page=None,
             postprocess=dimension_space_postprocess,
             bread=get_dim_bread,
             learnmore=learnmore_list,
             credit=credit)
def dimension_space_search(info, query):
    info.pop('count',None) # remove per_page so that we get all results
    if 'weight' not in info:
        info['weight'] = '1-12'
    if 'level' not in info:
        info['level'] = '1-24'
    common_parse(info, query)

@search_wrap(template="cmf_space_search_results.html",
             table=db.mf_newspaces,
             title='Newform Space Search Results',
             err_title='Newform Space Search Input Error',
             bread=get_search_bread,
             learnmore=learnmore_list,
             credit=credit)
def space_search(info, query):
    common_parse(info, query)
    parse_ints(info, query, 'dim', name='Dimension')
    parse_ints(info, query, 'num_forms', name='Number of newforms')
    set_info_funcs(info)

@cmf.route("/Completeness")
def completeness_page():
    t = 'Completeness of classical modular form data'
    return render_template("single.html", kid='dq.mf.elliptic.extent',
                           credit=credit(), title=t,
                           bread=get_bread(other='Completeness'),
                           learnmore=learnmore_list_remove('Completeness'))


@cmf.route("/Source")
def how_computed_page():
    t = 'Source of classical modular form data'
    return render_template("single.html", kid='dq.mf.elliptic.source',
                           credit=credit(), title=t,
                           bread=get_bread(other='Source'),
                           learnmore=learnmore_list_remove('Source'))

@cmf.route("/Labels")
def labels_page():
    t = 'Labels for classical modular forms'
    return render_template("single.html", kid='mf.elliptic.label',
                           credit=credit(), title=t,
                           bread=get_bread(other='Labels'),
                           learnmore=learnmore_list_remove('labels'))

@cmf.route("/Reliability")
def reliability_page():
    t = 'Reliability of classical modular form data'
    return render_template("single.html", kid='dq.mf.elliptic.reliability',
                           credit=credit(), title=t,
                           bread=get_bread(other='Reliability'),
                           learnmore=learnmore_list_remove('Reliability'))

def cm_format(D):
    if D == 1:
        return 'Not CM'
    elif D == 0:
        return 'Unknown'
    else:
        cm_label = "2.0.%s.1"%(-D)
        return nf_display_knowl(cm_label, field_pretty(cm_label))

def projective_image_sort_key(tup):
    im_type = tup[0]
    if im_type == 'A4':
        return -3
    elif im_type == 'S4':
        return -2
    elif im_type == 'A5':
        return -1
    else:
        return int(im_type[1:])

class CMF_stats(StatsDisplay):
    """
    Class for creating and displaying statistics for classical modular forms
    """
    def __init__(self):
        nforms = comma(db.mf_newforms.count())
        nspaces = comma(db.mf_newspaces.count())
        ndim = comma(db.mf_hecke_cc.count())
        weight_knowl = display_knowl('mf.elliptic.weight', title = 'weight')
        level_knowl = display_knowl('mf.elliptic.level', title='level')
        newform_knowl = display_knowl('mf.elliptic.newform', title='newforms')
        #stats_url = url_for(".statistics")
        self.short_summary = r'The database currently contains %s (Galois orbits of) %s of %s \(k\) and %s \(N\) satisfying \(Nk^2 \le %s\), corresponding to %s modular forms over the complex numbers.' % (nforms, newform_knowl, weight_knowl, level_knowl, Nk2_bound(), ndim)
        self.summary = r"The database currently contains %s (Galois orbits of) %s and %s spaces of %s \(k\) and %s \(N\) satisfying \(Nk^2 \le %s\), corresponding to %s modular forms over the complex numbers." % (nforms, newform_knowl, nspaces, weight_knowl, level_knowl, Nk2_bound(), ndim)

    table = db.mf_newforms
    baseurl_func = ".index"

    stat_list = [
        {'cols': [],
         'buckets':{'dim':[1,1,2,3,4,10,20,100,1000,10000,100000]},
         'row_title':'dimension',
         'knowl':'mf.elliptic.dimension'},
        {'cols': [],
         'buckets':{'level':[1,1,10,100,200,400,600,800,1000,2000,4000]},
         'row_title':'level',
         'knowl':'mf.elliptic.level'},
        {'cols': [],
         'buckets':{'weight':[1,1,2,3,4,5,10,20,40,62]},
         'row_title':'weight',
         'knowl':'mf.elliptic.weight'},
        {'cols':[],
         'buckets':{'char_order':[1,1,2,3,4,5,10,20,100,1000]},
         'row_title':'character order',
         'knowl':'character.dirichlet.order'},
        {'cols':'has_inner_twist',
         'top_title':'inner twisting',
         'row_title':'has inner twist',
         'knowl':'mf.elliptic.inner_twist',
         'formatter':boolean_unknown_format},
        {'cols':'analytic_rank',
         'top_title':'analytic ranks for forms of weight greater than 1',
         'row_title':'analytic rank',
         'knowl':'lfunction.analytic_rank',
         'avg':True},
        {'cols':'projective_image',
         'top_title':'projective images for weight 1 forms',
         'row_title':'projective image',
         'sort_key': projective_image_sort_key,
         'knowl':'mf.elliptic.projective_image',
         'formatter': (lambda t: r'\(%s_{%s}\)' % (t[0], t[1:]))},
        {'cols':'num_forms',
         'table':db.mf_newspaces,
         'top_title': r'number of newforms in \(S_k(\Gamma_0(N), \chi)\)',
         'row_title': 'newforms',
         'knowl': 'mf.elliptic.galois-orbits',
         'url_extras': 'search_type=Spaces&'},
        {'cols': 'cm_discs',
         'top_title':'complex multiplication',
         'row_title':'CM disc',
         'knowl':'mf.elliptic.cm_form',
         'denominator':{},
         'reverse':True,
         'split_list':True},
        {'cols': 'rm_discs',
         'top_title':'real multiplication',
         'row_title':'RM disc',
         'knowl':'mf.elliptic.rm_form',
         'denominator':{},
         'split_list':True},
        #{'cols': 'self_twist_discs',
        # 'top_title':'self twist discriminants',
        # 'row_title':'twist disc',
        # 'knowl':'mf.elliptic.cm_form',
        # 'sort_key': (lambda x: (abs(x[0]),x[0])),
        # 'split_list':True}
    ]

@cmf.route("/stats")
def statistics():
    title = 'Cupsidal Newforms: Statistics'
    return render_template("display_stats.html", info=CMF_stats(), credit=credit(), title=title, bread=get_bread(other='Statistics'), learnmore=learnmore_list())

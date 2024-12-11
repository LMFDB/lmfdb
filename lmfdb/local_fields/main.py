# This Blueprint is about p-adic fields (aka local number fields)
# Author: John Jones

from flask import abort, render_template, request, url_for, redirect
from sage.all import (
    PolynomialRing, ZZ, QQ, RR, latex, cached_function, Integers)
from sage.plot.all import line, points, text, Graphics

from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import (
    web_latex, coeff_to_poly, teXify_pol, display_multiset, display_knowl,
    parse_inertia, parse_newton_polygon, parse_bracketed_posints, parse_floats,
    parse_galgrp, parse_ints, clean_input, parse_rats, parse_noop, flash_error,
    SearchArray, TextBox, TextBoxWithSelect, SubsetBox, SelectBox, SneakyTextBox, TextBoxNoEg, CountBox, to_dict, comma,
    search_wrap, embed_wrap, yield_wrap, Downloader, StatsDisplay, totaler, proportioners, encode_plot,
    EmbeddedSearchArray, embed_wrap,
    redirect_no_cache, raw_typeset)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, ProcessedCol, MultiProcessedCol, ListCol, RationalListCol, PolynomialCol, eval_rational_list
from lmfdb.api import datapage
from lmfdb.local_fields import local_fields_page, logger
from lmfdb.local_fields.family import pAdicSlopeFamily, FAMILY_RE
from lmfdb.groups.abstract.main import abstract_group_display_knowl
from lmfdb.galois_groups.transitive_group import (
    transitive_group_display_knowl, group_display_inertia,
    knowl_cache, galdata, galunformatter,
    group_pretty_and_nTj, WebGaloisGroup)
from lmfdb.number_fields.web_number_field import (
    WebNumberField, string2list, nf_display_knowl)

from collections import Counter
import re
OLD_LF_RE = re.compile(r'^\d+\.\d+\.\d+\.\d+$')
NEW_LF_RE = re.compile(r'^\d+\.\d+\.\d+\.\d+[a-z]+\d+\.\d+$')

def get_bread(breads=[]):
    bc = [("$p$-adic fields", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def learnmore_list():
    return [('Source and acknowledgments', url_for(".source")),
            ('Completeness of the data', url_for(".cande")),
            ('Reliability of the data', url_for(".reliability")),
            ('$p$-adic field labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


def display_poly(coeffs):
    return web_latex(coeff_to_poly(coeffs))

def format_coeffs(coeffs):
    return latex(coeff_to_poly(coeffs))

def lf_formatfield(coef):
    coef = string2list(coef)
    thefield = WebNumberField.from_coeffs(coef)
    thepoly = coeff_to_poly(coef)
    thepolylatex = '$%s$' % latex(coeff_to_poly(coef))
    if thefield._data is None:
        return raw_typeset(thepoly, thepolylatex)
    return nf_display_knowl(thefield.get_label(),thepolylatex)

def local_algebra_data(labels):
    labs = labels.split(',')
    f1 = labs[0].split('.')
    labs = sorted(labs, key=lambda u: (int(j) for j in u.split('.')), reverse=True)
    ans = '<div align="center">'
    ans += '$%s$-adic algebra' % str(f1[0])
    ans += '</div>'
    ans += '<p>'
    ans += "<table class='ntdata'><th>Label<th>Polynomial<th>$e$<th>$f$<th>$c$<th>$G$<th>Slopes"
    if all(OLD_LF_RE.fullmatch(lab) for lab in labs):
        fall = {rec["label"]: rec for rec in db.lf_fields.search({"label":{"$in": labs}})}
    elif all(NEW_LF_RE.fullmatch(lab) for lab in labs):
        fall = {rec["new_label"]: rec for rec in db.lf_fields.search({"new_label":{"$in": labs}})}
    else:
        fall = {}
        for lab in labs:
            if OLD_LF_RE.fullmatch(lab):
                fall[lab] = db.lf_fields.lucky({"label":lab})
            elif NEW_LF_RE.fullmatch(lab):
                fall[lab] = db.lf_fields.lucky({"new_label":lab})
            else:
                fall[lab] = None
    for lab in labs:
        f = fall[lab]
        if f is None:
            ans += '<tr><td>Invalid label %s</td></tr>' % lab
            continue
        l = str(f['new_label'])
        ans += '<tr><td><a href="%s">%s</a><td>'%(url_for_label(l),l)
        ans += format_coeffs(f['coeffs'])
        ans += '<td>%d<td>%d<td>%d<td>' % (f['e'],f['f'],f['c'])
        ans += transitive_group_display_knowl(f['galois_label'])
        ans += '<td>$' + show_slope_content(f['slopes'],f['t'],f['u'])+'$'
    ans += '</table>'
    if len(labs) != len(set(labs)):
        ans += '<p>Fields which appear more than once occur according to their given multiplicities in the algebra'
    return ans

def local_field_data(label):
    if OLD_LF_RE.fullmatch(label):
        f = db.lf_fields.lookup(label)
    elif NEW_LF_RE.fullmatch(label):
        f = db.lf_fields.lucky({"new_label": label})
    else:
        return "Invalid label %s" % label
    nicename = ''
    if f['n'] < 3:
        nicename = ' = ' + prettyname(f)
    ans = '$p$-adic field %s%s<br><br>' % (label, nicename)
    ans += r'Extension of $\Q_{%s}$ defined by %s<br>' % (str(f['p']),web_latex(coeff_to_poly(f['coeffs'])))
    gn = f['n']
    ans += 'Degree: %s<br>' % str(gn)
    ans += 'Ramification index $e$: %s<br>' % str(f['e'])
    ans += 'Residue field degree $f$: %s<br>' % str(f['f'])
    ans += 'Discriminant ideal:  $(p^{%s})$ <br>' % str(f['c'])
    if 'galois_label' in f:
        gt = int(f['galois_label'].split('T')[1])
        ans += 'Galois group $G$: %s<br>' % group_pretty_and_nTj(gn, gt, True)
    else:
        ans += 'Galois group $G$: not computed<br>'
    ans += '<div align="right">'
    ans += '<a href="%s">%s home page</a>' % (str(url_for("local_fields.by_label", label=label)),label)
    ans += '</div>'
    return ans


def lf_display_knowl(label, name=None):
    if name is None:
        name = label
    return '<a title = "%s [lf.field.data]" knowl="lf.field.data" kwargs="label=%s">%s</a>' % (label, label, name)


def local_algebra_display_knowl(labels):
    return '<a title = "{0} [lf.algebra.data]" knowl="lf.algebra.data" kwargs="labels={0}">{0}</a>' % (labels)


def plot_ramification_polygon(verts, p, polys=None, inds=None):
    # print("VERTS", verts)
    verts = [tuple(pt) for pt in verts]
    if not verts:
        # Unramified, so we won't be displaying the plot
        return
    # Extract the coefficients to be associated to x
    ymax = verts[0][1]
    xmax = verts[-1][0]
    # How far we need to shift text depends on the scale
    txshift = xmax / 80
    tyshift = xmax / 48
    tick = xmax / 160
    nextq = p
    L = Graphics()
    if ymax > 0:
        asp_ratio = (xmax + 2*txshift) / (2 * (ymax + 2*tyshift)) # 2 comes from the fact that the actual image has width 500 and height 250.
    else:
        # Add in silly white dot
        L += points([(0,1)], color="white")
        asp_ratio = (xmax + 2*txshift) / (8 + 16*tyshift)
    L += line([(0,0), (0, ymax)], color="grey")
    L += line([(0,0), (-xmax, 0)], color="grey")
    for i in range(1, ymax + 1):
        L += line([(0, i), (-tick, i)], color="grey")
    for i in range(0, xmax + 1):
        L += line([(-i, 0), (-i, tick/asp_ratio)], color="grey")
    for P in verts:
        L += text(
            f"${-P[0]}$", (-P[0], -tyshift/asp_ratio),
            color="black")
        L += text(
            f"${P[1]}$", (txshift, P[1]),
            horizontal_alignment="left",
            color="black")

    if polys is not None:
        R = ZZ["t"]["z"]
        polys = [R(poly) for poly in polys]
        # print("POLYS", polys)

        def restag(c, a, b):
            return text(f"${latex(c)}$", (-a - txshift, b + tyshift/asp_ratio),
                        horizontal_alignment="left",
                        color="black")
        L += restag(polys[0][0], 1, ymax)
    for i in range(len(verts) - 1):
        P = verts[i]
        Q = verts[i+1]
        slope = ZZ(P[1] - Q[1]) / ZZ(Q[0] - P[0]) # actually the negative of the slope
        d = slope.denominator()
        if slope != 0:
            if polys is not None:
                # Need to check that this is compatible with the residual polynomial normalization
                while nextq <= Q[0]:
                    j = (nextq - P[0]) / d
                    if j in ZZ and polys[i][j]:
                        L += restag(polys[i][j], nextq, P[1] - (nextq - P[0]) * slope)
                    nextq *= p
            L += text(
                f"${slope}$", (-P[0] + txshift, (P[1] + Q[1]) / 2),
                horizontal_alignment="left",
                color="blue")
            for x in range(P[0], Q[0] + 1):
                L += line(
                    [(-x, Q[1]), (-x, P[1] - (x - P[0]) * slope)],
                    color="grey",
                )
            for y in range(Q[1], P[1]):
                L += line(
                    [(-P[0] + (y - P[1]) / slope, y), (-P[0], y)],
                    color="grey",
                )
        elif polys:
            # For tame inertia, the coefficients can occur at locations other than powers of p
            for j, c in enumerate(polys[i]):
                if j and c:
                    L += restag(c, P[0] + j, P[1])
    L += line([(-x,y) for (x,y) in verts], thickness=2)
    if inds is not None:
        # print("INDS", inds)
        L += points([(-p**i, ind) for (i, ind) in enumerate(inds)], size=30, color="black")
    L.axes(False)
    L.set_aspect_ratio(asp_ratio)
    return encode_plot(L, pad=0, pad_inches=0, bbox_inches="tight", figsize=(8,4))


@app.context_processor
def ctx_local_fields():
    return {'local_field_data': local_field_data,
            'local_algebra_data': local_algebra_data}


# Utilities for subfield display
def format_lfield(label, p):
    if OLD_LF_RE.fullmatch(label):
        data = db.lf_fields.lookup(label, ["n", "p", "rf", "new_label"])
    else:
        data = db.lf_fields.lucky({"new_label": label}, ["n", "p", "rf", "new_label"])
    return lf_display_knowl(label, name=prettyname(data))


# Input is a list of pairs, coeffs of field as string and multiplicity
def format_subfields(sublist, multdata, p):
    if not sublist:
        return ''
    subdata = zip(sublist, multdata)
    return display_multiset(subdata, format_lfield, p)


# Encode string for rational into our special format
def ratproc(inp):
    if '.' in inp:
        inp = RR(inp)
    qs = QQ(inp)
    sstring = str(qs*1.)
    sstring += '0'*14
    if qs < 10:
        sstring = '0'+sstring
    sstring = sstring[0:12]
    sstring += str(qs)
    return sstring

def show_slopes(sl):
    if str(sl) == "[]":
        return "None"
    return('$' + sl + '$')

def show_slopes2(sl):
    # uses empty brackets with a space instead of None
    if str(sl) == "[]":
        return r'[\ ]'
    return(sl)

def show_slope_content(sl,t,u):
    if sl is None or t is None or u is None:
        return ' $not computed$ ' # actually killing math mode
    sc = str(sl)
    if sc == '[]':
        sc = r'[\ ]'
    if t > 1:
        sc += '_{%d}' % t
    if u > 1:
        sc += '^{%d}' % u
    return(sc)

def show_hidden_slopes(sl, vis):
    hidden = sorted((Counter(eval_rational_list(sl)) - Counter(eval_rational_list(vis))).elements())
    if not hidden:
        return r'[\ ]'
    return str(hidden)

@local_fields_page.route("/")
def index():
    bread = get_bread()
    info = to_dict(request.args, search_array=LFSearchArray(), stats=LFStats())
    if len(request.args) != 0:
        return local_field_search(info)
    return render_template("lf-index.html", title="$p$-adic fields", titletag="p-adic fields", bread=bread, info=info, learnmore=learnmore_list())


@local_fields_page.route("/<label>")
def by_label(label):
    clean_label = clean_input(label)
    if label != clean_label:
        return redirect(url_for_label(label=clean_label), 301)
    return render_field_webpage({'label': label})

def url_for_label(label):
    if label == "random":
        return url_for('.random_field')
    return url_for(".by_label", label=label)

def url_for_family(label):
    return url_for(".family_page", label=label)

def url_for_packet(packet):
    return url_for(".index", packet=packet)

def local_field_jump(info):
    return redirect(url_for_label(info['jump']), 301)

def unpack_slopes(slopes, t, u):
    return eval_rational_list(slopes), t, u

def unpack_hidden(slopes, visible):
    return sorted((Counter(eval_rational_list(slopes)) - Counter(eval_rational_list(visible))).elements())

def format_eisen(eisstr):
    Pt = PolynomialRing(QQ, 't')
    Ptx = PolynomialRing(Pt, 'x')
    return latex(Ptx(str(eisstr).replace('y','x')))

class LF_download(Downloader):
    table = db.lf_fields
    title = '$p$-adic fields'
    inclusions = {
        'field': (
            ["p", "coeffs"],
            {
                "magma": 'Prec := 100; // Default precision of 100\n    base := pAdicField(out`p, Prec);\n    field := LocalField(base, PolynomialRing(base)!(out`coeffs));',
                "sage": 'Prec = 100 # Default precision of 100\n    base = Qp(p, Prec)\n    field = base.extension(QQ["x"](out["coeffs"]))',
                "gp": 'field = Polrev(mapget(out, "coeffs"));',
            }
        ),
    }

def galcolresponse(n,t,cache):
    if t is None:
        return 'not computed'
    return group_pretty_and_nTj(n, t, cache=cache)


label_col = LinkCol("new_label", "lf.field.label", "Label", url_for_label)

def packet_col(default):
    return MultiProcessedCol("packet_link", "lf.packet", "Packet", ["packet", "packet_size"], (lambda packet, size: f'<a href="{url_for_packet(packet)}">{size}</a>'), default=default)
def degree_col(default):
    return MathCol("n", "lf.degree", "$n$", short_title="degree", default=default)
poly_col = ProcessedCol("coeffs", "lf.defining_polynomial", "Polynomial", format_coeffs, mathmode=True)
p_col = MathCol("p", "lf.qp", "$p$", short_title="prime")
c_col = MathCol("c", "lf.discriminant_exponent", "$c$", short_title="discriminant exponent")
e_col = MathCol("e", "lf.ramification_index", "$e$", short_title="ramification index")
f_col = MathCol("f", "lf.residue_field_degree", "$f$", short_title="residue field degree")
gal_col = MultiProcessedCol("gal", "nf.galois_group", "Galois group",
                            ["n", "gal", "cache"],
                            galcolresponse,
                            apply_download=lambda n, t, cache: [n, t])
def aut_col(default):
    return MathCol("aut", "lf.automorphism_group", r"$\#\Aut(K/\Q_p)$", short_title="auts", default=default)
def visible_col(default):
    return RationalListCol("visible", "lf.visible_slopes", "Visible slopes",
                   show_slopes2, default=default)
def slopes_col(default):
    return MultiProcessedCol("slopes", "lf.slope_content", "Slope content",
                             ["slopes", "t", "u"],
                             show_slope_content,
                             mathmode=True, apply_download=unpack_slopes, default=default)

lf_columns = SearchColumns([
    label_col,
    degree_col(False),
    poly_col,
    p_col,
    e_col,
    f_col,
    c_col,
    gal_col,
    MathCol("u", "lf.unramified_degree", "$u$", short_title="unramified degree", default=False),
    MathCol("t", "lf.tame_degree", "$t$", short_title="tame degree", default=False),
    visible_col(lambda info: info.get("visible")),
    slopes_col(True),
    aut_col(lambda info:info.get("aut")),
    # want apply_download for download conversion
    PolynomialCol("unram", "lf.unramified_subfield", "Unram. Ext.", default=lambda info:info.get("visible")),
    ProcessedCol("eisen", "lf.eisenstein_polynomial", "Eisen. Poly.", default=lambda info:info.get("visible"), mathmode=True, func=format_eisen),
    MathCol("ind_of_insep", "lf.indices_of_inseparability", "Ind. of Insep.", default=lambda info: info.get("ind_of_insep")),
    ListCol("associated_inertia", "lf.associated_inertia", "Assoc. Inertia", default=lambda info: info.get("associated_inertia"), mathmode=True),
    ProcessedCol("residual_polynomials", "lf.residual_polynomials", "Resid. Poly", default=False, mathmode=True, func=lambda rp: ','.join(teXify_pol(f) for f in rp)),
    ListCol("jump_set", "lf.jump_set", "Jump Set", default=lambda info: info.get("jump_set"), mathmode=True)],
    db_cols=["aut", "c", "coeffs", "e", "f", "gal", "label", "new_label", "n", "p", "slopes", "t", "u", "visible", "ind_of_insep", "associated_inertia", "jump_set", "unram","eisen", "family", "residual_polynomials"])

family_columns = SearchColumns([
    label_col,
    packet_col(lambda info: info.get("one_per") == "packet"),
    poly_col,
    gal_col,
    MathCol("galsize", "nf.galois_group", "Galois degree"),
    aut_col(True),
    slopes_col(False),
    MultiProcessedCol("hidden", "lf.visible_slopes", "Hidden slopes",
                      ["slopes", "visible"],
                      show_hidden_slopes,
                      mathmode=True, apply_download=unpack_hidden),
    MathCol("ind_of_insep", "lf.indices_of_inseparability", "Ind. of Insep."),
    MathCol("associated_inertia", "lf.associated_inertia", "Assoc. Inertia"),
    MathCol("jump_set", "lf.jump_set", "Jump Set")])

class PercentCol(MathCol):
    def display(self, rec):
        x = self.get(rec)
        if x == 0:
            return r"$0\%$"
        elif x == 1:
            return r"$100\%$"
        return fr"${100*x:.2f}\%$"

def pretty_link(label, p, n, rf):
    name = prettyname({"p": p, "n": n, "rf": rf, "new_label": label})
    return f'<a href="{url_for_label(label)}">{name}</a>'

families_columns = SearchColumns([
    LinkCol("label", "lf.family_label", "Label", url_for_family),
    MathCol("p", "lf.residue_field", "$p$", short_title="prime"),
    MathCol("n", "lf.degree", "$n$", short_title="degree"),
    MathCol("n0", "lf.degree", "$n_0$", short_title="base degree", default=False),
    MathCol("n_absolute", "lf.degree", r"$n_{\mathrm{abs}}$", short_title="abs. degree", default=False),
    MathCol("f", "lf.residue_field_degree", "$f$", short_title="res. field degree"),
    MathCol("f0", "lf.residue_field_degree", "$f_0$", short_title="base res. field degree", default=False),
    MathCol("f_absolute", "lf.residue_field_degree", r"$f_{\mathrm{abs}}$", short_title="abs. residue field degree", default=False),
    MathCol("e", "lf.ramification_index", "$e$", short_title="ram. index"),
    MathCol("e0", "lf.ramification_index", "$e_0$", short_title="base ram. index", default=False),
    MathCol("e_absolute", "lf.ramification_index", r"$e_{\mathrm{abs}}$", short_title="abs. ram. index", default=False),
    MathCol("c", "lf.discriminant_exponent", "$c$", short_title="disc. exponent"),
    MathCol("c0", "lf.discriminant_exponent", "$c_0$", short_title="base disc. exponent"),
    MathCol("c_absolute", "lf.discriminant_exponent", r"$c_{\mathrm{abs}}$", short_title="abs. disc. exponent"),
    MultiProcessedCol("base_field", "lf.family_base", "Base",
                      ["base", "p", "n0", "rf0"],
                      pretty_link),
    visible_col(False),
    RationalListCol("slopes", "lf.swan_slopes", "Swan slopes"),
    RationalListCol("heights", "lf.heights", "Heights"),
    RationalListCol("rams", "lf.rams", "Rams"),
    ProcessedCol("poly", "lf.family_polynomial", "Generic poly", lambda pol: teXify_pol(pol, greek_vars=True, subscript_vars=True), mathmode=True, default=False),
    MathCol("ambiguity", "lf.family_ambiguity", "Ambiguity"),
    MathCol("field_count", "lf.family_field_count", "Field count"),
    MathCol("mass", "lf.family_mass", "Mass", orig=["mass_display"]),
    MathCol("mass_stored", "lf.family_mass", "Mass stored", default=False),
    PercentCol("mass_missing", "lf.family_missing_mass", "Mass missing"),
    MathCol("wild_segments", "lf.wild_segments", "Wild segments", default=False),
    MathCol("packet_count", "lf.packet", "Num. Packets"),
])

def lf_postprocess(res, info, query):
    cache = knowl_cache(list({f"{rec['n']}T{rec['gal']}" for rec in res if 'gal' in rec}))
    for rec in res:
        rec["cache"] = cache
        gglabel = f"{rec['n']}T{rec['gal']}"
        rec["galsize"] = cache[gglabel]["order"]
    return res

def families_postprocess(res, info, query):
    quads = list(set(rec["base"] for rec in res if rec["n0"] == 2))
    if quads:
        rflook = {rec["new_label"]: rec["rf"] for rec in db.lf_fields.search({"new_label":{"$in":quads}}, ["new_label", "rf"])}
    for rec in res:
        if rec["n0"] == 1:
            rec["rf0"] = [1, 0]
        elif rec["n0"] == 2:
            rec["rf0"] = rflook[rec["base"]]
        else:
            rec["rf0"] = None
    return res

def common_parse(info, query):
    parse_ints(info,query,'p',name='Prime p')
    parse_ints(info,query,'n',name='Degree')
    parse_ints(info,query,'u',name='Unramified degree')
    parse_ints(info,query,'t',name='Tame degree')
    parse_galgrp(info,query,'gal',qfield=('galois_label','n'))
    parse_ints(info,query,'aut',name='Automorphisms')
    parse_ints(info,query,'c',name='Discriminant exponent c')
    parse_ints(info,query,'e',name='Ramification index e')
    parse_ints(info,query,'f',name='Residue field degree f')
    parse_rats(info,query,'topslope',qfield='top_slope',name='Top slope', process=ratproc)
    parse_newton_polygon(info,query,"slopes", qfield="slopes_tmp", mode=info.get('slopes_quantifier'))
    parse_newton_polygon(info,query,"visible", qfield="visible_tmp", mode=info.get('visible_quantifier'))
    parse_newton_polygon(info,query,"ind_of_insep", qfield="ind_of_insep_tmp", mode=info.get('insep_quantifier'), reversed=True)
    parse_bracketed_posints(info,query,"associated_inertia")
    parse_bracketed_posints(info,query,"jump_set")
    parse_inertia(info,query,qfield=('inertia_gap','inertia'))
    parse_inertia(info,query,qfield=('wild_gap','wild_gap'), field='wild_gap')
    parse_noop(info,query,'packet')
    parse_noop(info,query,'family')

@search_wrap(table=db.lf_fields,
             title='$p$-adic field search results',
             titletag=lambda:'p-adic field search results',
             err_title='Local field search input error',
             columns=lf_columns,
             per_page=50,
             shortcuts={'jump': local_field_jump, 'download': LF_download()},
             postprocess=lf_postprocess,
             bread=lambda:get_bread([("Search results", ' ')]),
             learnmore=learnmore_list,
             url_for_label=url_for_label)
def local_field_search(info,query):
    common_parse(info, query)

def render_field_webpage(args):
    data = None
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        data = db.lf_fields.lucky({"new_label":label})
        if data is None:
            new_label = db.lf_fields.lookup(label, "new_label")
            if new_label is None:
                if NEW_LF_RE.fullmatch(label) or OLD_LF_RE.fullmatch(label):
                    flash_error("Field %s was not found in the database.", label)
                else:
                    flash_error("%s is not a valid label for a $p$-adic field.", label)
                return redirect(url_for(".index"))
            return redirect(url_for_label(label=new_label), 301)
        title = '$p$-adic field ' + prettyname(data)
        titletag = 'p-adic field ' + prettyname(data)
        polynomial = coeff_to_poly(data['coeffs'])
        p = data['p']
        Qp = r'\Q_{%d}' % p
        e = data['e']
        f = data['f']
        n = data['n']
        cc = data['c']
        gn = data['n']
        autstring = r'\Aut'
        if 'galois_label' in data:
            gt = int(data['galois_label'].split('T')[1])
            the_gal = WebGaloisGroup.from_nt(gn,gt)
            isgal = ' Galois' if the_gal.order() == gn else ' not Galois'
            abelian = ' and abelian' if the_gal.is_abelian() else ''
            galphrase = 'This field is'+isgal+abelian+r' over $\Q_{%d}.$' % p
            if the_gal.order() == gn:
                autstring = r'\Gal'
        prop2 = [
            ('Label', label),
            ('Base', r'\(%s\)' % Qp),
            ('Degree', r'\(%s\)' % data['n']),
            ('e', r'\(%s\)' % e),
            ('f', r'\(%s\)' % f),
            ('c', r'\(%s\)' % cc),
            ('Galois group', group_pretty_and_nTj(gn, gt) if 'galois_label' in data else 'not computed'),
        ]
        # Look up the unram poly so we can link to it
        unramdata = db.lf_fields.lucky({'p': p, 'n': f, 'c': 0})
        if unramdata is None:
            logger.fatal("Cannot find unramified field!")
            unramfriend = ''
        else:
            unramfriend = url_for_label(unramdata['new_label'])

        Px = PolynomialRing(QQ, 'x')
        Pt = PolynomialRing(QQ, 't')
        Ptx = PolynomialRing(Pt, 'x')
        if data['f'] == 1:
            unramp = r'$%s$' % Qp
            eisenp = Ptx(str(data['eisen']).replace('y','x'))
            eisenp = raw_typeset(eisenp, web_latex(eisenp))

        else:
            unramp = coeff_to_poly(unramdata['coeffs'])
            #unramp = data['unram'].replace('t','x')
            unramp = raw_typeset(unramp, web_latex(Px(str(unramp))))
            unramp = prettyname(unramdata)+' $\\cong '+Qp+'(t)$ where $t$ is a root of '+unramp
            eisenp = Ptx(str(data['eisen']).replace('y','x'))
            eisenp = raw_typeset(str(eisenp), web_latex(eisenp), extra=r'$\ \in'+Qp+'(t)[x]$')

        rflabel = db.lf_fields.lucky({'p': p, 'n': {'$in': [1, 2]}, 'rf': data['rf']}, projection="new_label")
        if rflabel is None:
            logger.fatal("Cannot find discriminant root field!")
            rffriend = ''
        else:
            rffriend = url_for_label(rflabel)
        gsm = data['gsm']
        if gsm == [0]:
            gsm = 'Not computed'
        elif gsm == [-1]:
            gsm = 'Does not exist'
        else:
            gsm = lf_formatfield(','.join(str(b) for b in gsm))

        if 'wild_gap' in data and data['wild_gap'] != [0,0]:
            wild_inertia = abstract_group_display_knowl(f"{data['wild_gap'][0]}.{data['wild_gap'][1]}")
        else:
            wild_inertia = 'data not computed'

        info.update({
                    'polynomial': raw_typeset(polynomial),
                    'n': n,
                    'p': p,
                    'c': cc,
                    'e': e,
                    'f': f,
                    't': data['t'],
                    'u': data['u'],
                    'rf': lf_display_knowl( rflabel, name=printquad(data['rf'], p)),
                    'base': lf_display_knowl(str(p)+'.1.0.1', name='$%s$' % Qp),
                    'hw': data['hw'],
                    'visible': show_slopes(data['visible']),
                    'wild_inertia': wild_inertia,
                    'unram': unramp,
                    'ind_insep': show_slopes(str(data['ind_of_insep'])),
                    'eisen': eisenp,
                    'gsm': gsm,
                    'autstring': autstring,
                    'subfields': format_subfields(data['subfield'],data['subfield_mult'],p),
                    'aut': data['aut'],
                    'ram_polygon_plot': plot_ramification_polygon(data['ram_poly_vert'], p, data['residual_polynomials'], data['ind_of_insep']),
                    'residual_polynomials': ",".join(f"${teXify_pol(poly)}$" for poly in data['residual_polynomials']),
                    'associated_inertia': ",".join(f"${ai}$" for ai in data['associated_inertia']),
                    'ppow_roots_of_unity': data['ppow_roots_of_unity'],
                    })
        friends = [('Family', url_for(".family_page", label=data["family"]))]
        if 'slopes' in data:
            info['slopes'] = show_slopes(data['slopes'])
        if 'inertia' in data:
            info['inertia'] = group_display_inertia(data['inertia'])
        if 'gms' in data:
            info.update({'gms': data['gms']})
        if 'ram_poly_vert' in data:
            info.update({'ram_polygon_plot': plot_polygon(data['ram_poly_vert'], data['residual_polynomials'], data['ind_of_insep'], p)})
        if 'residual_polynomials' in data:
            info.update({'residual_polynomials': ",".join(f"${teXify_pol(poly)}$" for poly in data['residual_polynomials'])})
        if 'associated_inertia' in data:
            info.update({'associated_inertia': ",".join(f"${ai}$" for ai in data['associated_inertia'])})
        if 'galois_label' in data:
            info.update({'gal': group_pretty_and_nTj(gn, gt, True),
                         'galphrase': galphrase,
                         'gt': gt})
            friends.append(('Galois group', "/GaloisGroup/%dT%d" % (gn, gt)))
        if 'jump_set' in data:
            info['jump_set'] = data['jump_set']
        if unramfriend != '':
            friends.append(('Unramified subfield', unramfriend))
        if rffriend != '':
            friends.append(('Discriminant root field', rffriend))
        if data['is_completion']:
            friends.append(('Number fields with this completion',
                url_for('number_fields.number_field_render_webpage')+"?completions={}".format(label) ))
        downloads = [('Underlying data', url_for('.lf_data', label=label))]

        _, _, _, fam, i = data['new_label'].split(".")
        _, fama, subfam = re.split(r"(\D+)", fam)
        bread = get_bread([(str(p), url_for('.index', p=p)),
                           (f"{f}.{e}", url_for('.index', p=p, e=e, f=f)),
                           (str(cc), url_for('.index', p=p, e=e, f=f, c=cc)),
                           (fama, url_for('.family_page', label=data['family'])),
                           (f'{subfam}.{i}', ' ')])
        return render_template(
            "lf-show-field.html",
            title=title,
            titletag=titletag,
            bread=bread,
            info=info,
            properties=prop2,
            friends=friends,
            downloads=downloads,
            learnmore=learnmore_list(),
            KNOWL_ID="lf.%s" % label, # TODO: BROKEN
        )

def prettyname(ent):
    if ent['n'] <= 2:
        return printquad(ent['rf'], ent['p'])
    return ent['new_label']

@cached_function
def getu(p):
    if p == 2:
        return 5
    return int(Integers(p).quadratic_nonresidue())

def printquad(code, p):
    if code == [1, 0]:
        return(r'$\Q_{%s}$' % p)
    u = getu(p)
    if code == [1, 1]:
        return(r'$\Q_{%s}(\sqrt{%s})$' % (p,u))
    if code == [-1, 1]:
        return(r'$\Q_{%s}(\sqrt{-%s})$' % (p,u))
    s = code[0]
    if code[1] == 1:
        s = str(s) + r'\cdot '+str(u)
    return(r'$\Q_{' + str(p) + r'}(\sqrt{' + str(s) + '})$')

@local_fields_page.route("/data/<label>")
def lf_data(label):
    if not NEW_LF_RE.fullmatch(label):
        return abort(404, f"Invalid label {label}")
    title = f"Local field data - {label}"
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    sorts = [["p", "n", "e", "c", "ctr_family", "ctr_subfamily", "ctr"]]
    return datapage(label, "lf_fields", title=title, bread=bread, label_cols=["new_label"], sorts=sorts)

@local_fields_page.route("/random")
@redirect_no_cache
def random_field():
    label = db.lf_fields.random()
    return url_for(".by_label", label=label)

@local_fields_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "lf",
        db.lf_fields,
        url_for_label,
        title=r"Some interesting $p$-adic fields",
        bread=get_bread([("Interesting", " ")]),
        learnmore=learnmore_list()
    )

@local_fields_page.route("/stats")
def statistics():
    title = "Local fields: statistics"
    bread = get_bread([("Statistics", " ")])
    return render_template("display_stats.html", info=LFStats(), title=title, bread=bread, learnmore=learnmore_list())

@local_fields_page.route("/dynamic_stats")
def dynamic_statistics():
    info = to_dict(request.args, search_array=LFSearchArray())
    LFStats().dynamic_setup(info)
    title = "p-adic fields: Dynamic statistics"
    return render_template(
        "dynamic_stats.html",
        info=info,
        title=title,
        bread=get_bread([("Dynamic Statistics", " ")]),
        learnmore=learnmore_list(),
    )

@local_fields_page.route("/Completeness")
def cande():
    t = 'Completeness of $p$-adic field data'
    tt = 'Completeness of p-adic field data'
    bread = get_bread([("Completeness", )])
    return render_template("single.html", kid='rcs.cande.lf',
                           title=t, titletag=tt, bread=bread,
                           learnmore=learnmore_list_remove('Completeness'))

@local_fields_page.route("/Labels")
def labels_page():
    t = 'Labels for $p$-adic fields'
    tt = 'Labels for p-adic fields'
    bread = get_bread([("Labels", '')])
    return render_template("single.html", kid='lf.field.label',
                  learnmore=learnmore_list_remove('label'),
                  title=t, titletag=tt, bread=bread)

@local_fields_page.route("/Source")
def source():
    t = 'Source and acknowledgments for $p$-adic field pages'
    ttag = 'Source and acknowledgments for p-adic field pages'
    bread = get_bread([("Source", '')])
    return render_template("multi.html", kids=['rcs.source.lf',
                           'rcs.ack.lf','rcs.cite.lf'],
                           title=t,
                           titletag=ttag, bread=bread,
                           learnmore=learnmore_list_remove('Source'))

@local_fields_page.route("/Reliability")
def reliability():
    t = 'Reliability of $p$-adic field data'
    ttag = 'Reliability of p-adic field data'
    bread = get_bread([("Reliability", '')])
    return render_template("single.html", kid='rcs.source.lf',
                           title=t, titletag=ttag, bread=bread,
                           learnmore=learnmore_list_remove('Reliability'))

@local_fields_page.route("/family/<label>")
def family_page(label):
    m = FAMILY_RE.match(label)
    if m is None:
        flash_error("Invalid label %s", label)
        return redirect(url_for(".index"))

    family = pAdicSlopeFamily(label)
    info = to_dict(request.args, search_array=FamilySearchArray(), family_label=label, family=family, stats=LFStats())
    p, n = family.p, family.n
    info['bread'] = get_bread([(str(p), url_for(".families_page", p=p)),
                       (str(family.n), url_for(".families_page", p=p, n=n)),
                       (label, "")])
    info['title'] = f"$p$-adic family {label}"
    info['show_count'] = True
    # Properties?
    return render_family(info)

@embed_wrap(
    table=db.lf_fields,
    template="lf-family.html",
    err_title="Local field family error",
    columns=family_columns,
    learnmore=learnmore_list,
    postprocess=lf_postprocess,
    # Each of the following arguments is set here so that it is overridden when constructing template_kwds,
    # which prioritizes values found in info (which are set in family_page() before calling render_family)
    bread=lambda:None,
    properties=lambda:None,
    family=lambda:None,
)
def render_family(info, query):
    family = info["family"]
    query["family"] = family.label
    #query["p"] = family.p
    #query["visible"] = str(family.artin_slopes)
    #query["f"] = 1 # TODO: Update to allow for tame extensions
    #query["e"] = family.n

    parse_galgrp(info,query,'gal',qfield=('galois_label','n'))
    parse_rats(info,query,'topslope',qfield='top_slope',name='Top slope', process=ratproc)
    parse_newton_polygon(info,query,"slopes", qfield="slopes_tmp", mode=info.get('slopes_quantifier'))
    parse_newton_polygon(info,query,"ind_of_insep", qfield="ind_of_insep_tmp", mode=info.get('insep_quantifier'), reversed=True)
    parse_bracketed_posints(info,query,"associated_inertia")
    if 'one_per' in info and info['one_per'] == 'packet':
        query["__one_per__"] = "packet"

@local_fields_page.route("/families/")
def families_page():
    info = to_dict(request.args, search_array=FamiliesSearchArray())
    return families_search(info)

@search_wrap(
    table=db.lf_families,
    columns=families_columns,
    title='$p$-adic families search results',
    titletag=lambda:'p-adic families search results',
    err_title='p-adic families search input error',
    learnmore=learnmore_list,
    bread=lambda:get_bread([("Families", "")]),
    postprocess=families_postprocess,
    url_for_label=url_for_family,
)
def families_search(info,query):
    parse_ints(info,query,'p',name='Prime p')
    parse_ints(info,query,'n',name='Degree')
    parse_ints(info,query,'n0',name='Base degree')
    parse_ints(info,query,'n_absolute',name='Absolute degree')
    parse_ints(info,query,'e',name='Ramification index')
    parse_ints(info,query,'e0',name='Base ramification index')
    parse_ints(info,query,'e_absolute',name='Absolute ramification index')
    parse_ints(info,query,'f',name='Residue field degree')
    parse_ints(info,query,'f0',name='Base residue field degree')
    parse_ints(info,query,'f_absolute',name='Absolute residue field degree')
    parse_ints(info,query,'c',name='Discriminant exponent c')
    parse_ints(info,query,'c0',name='Base discriminant exponent c')
    parse_ints(info,query,'c_absolute',name='Absolute discriminant exponent c')
    parse_ints(info,query,'w',name='Wild ramification exponent')
    parse_noop(info,query,'base',name='Base')
    parse_floats(info,query,'mass',name='Mass')
    parse_floats(info,query,'mass_missing',name='Missing mass')
    parse_ints(info,query,'ambiguity',name='Ambiguity')
    parse_ints(info,query,'field_count',name='Field count')
    parse_ints(info,query,'wild_segments',name='Wild segments')
    #parse_newton_polygon(info,query,"visible", qfield="visible_tmp", mode=info.get('visible_quantifier'))

def common_boxes():
    degree = TextBox(
        name='n',
        label='Degree',
        knowl='lf.degree',
        example='6',
        example_span='6, or a range like 3..5')
    qp = TextBox(
        name='p',
        label=r'Residue field characteristic',
        short_label='Residue characteristic',
        knowl='lf.residue_field',
        example='3',
        example_span='3, or a range like 3..7')
    c = TextBox(
        name='c',
        label='Discriminant exponent',
        knowl='lf.discriminant_exponent',
        example='8',
        example_span='8, or a range like 2..6')
    e = TextBox(
        name='e',
        label='Ramification index',
        knowl='lf.ramification_index',
        example='3',
        example_span='3, or a range like 2..6')
    f = TextBox(
        name='f',
        label='Residue field degree',
        knowl='lf.residue_field_degree',
        example='3',
        example_span='3, or a range like 2..6')
    topslope = TextBox(
        name='topslope',
        label='Top slope',
        knowl='lf.top_slope',
        example='4/3',
        example_span='4/3, or a range like 3..5')
    slopes_quantifier = SubsetBox(
        name="slopes_quantifier",
    )
    slopes = TextBoxWithSelect(
        name='slopes',
        label='Wild slopes',
        short_label='Wild',
        knowl='lf.wild_slopes',
        select_box=slopes_quantifier,
        example='[2,2,3]',
        example_span='[2,2,3] or [3,7/2,4]')
    visible_quantifier = SubsetBox(
        name="visible_quantifier",
    )
    visible = TextBoxWithSelect(
        name='visible',
        label='Visible slopes',
        short_label='Visible',
        knowl='lf.visible_slopes',
        select_box=visible_quantifier,
        example='[2,2,3]',
        example_span='[2,2,3] or [2,3,17/4]')
    insep_quantifier = SubsetBox(
        name="insep_quantifier",
    )
    ind_insep = TextBoxWithSelect(
        name='ind_of_insep',
        label='Ind. of insep.',
        short_label='Indices',
        knowl='lf.indices_of_inseparability',
        select_box=insep_quantifier,
        example='[1,1,0]',
        example_span='[1,1,0] or [18,10,4,0]')
    associated_inertia = TextBox(
        name='associated_inertia',
        label='Assoc. Inertia',
        knowl='lf.associated_inertia',
        example='[1,2,1]',
        example_span='[1,2,1] or [1,1,1,1]')
    jump_set = TextBox(
        name='jump_set',
        label='Jump Set',
        knowl='lf.jump_set',
        example='[1,2]',
        example_span='[1,2] or [1,3,8]')
    gal = TextBoxNoEg(
        name='gal',
        label='Galois group',
        short_label='Galois group',
        knowl='nf.galois_search',
        example='5T3',
        example_span='e.g. [8,3], 8.3, C5 or 7T2')
    aut = TextBox(
        name='aut',
        label='Num. automorphisms',
        knowl='lf.automorphism_group',
        example='1',
        example_span='2, or a range like 2..3'
    )
    u = TextBox(
        name='u',
        label='Galois unramified degree',
        knowl='lf.unramified_degree',
        example='3',
        example_span='3, or a range like 1..4'
    )
    t = TextBox(
        name='t',
        label='Galois tame degree',
        knowl='lf.tame_degree',
        example='2',
        example_span='2, or a range like 2..3'
    )
    inertia = TextBox(
        name='inertia_gap',
        label='Inertia subgroup',
        knowl='lf.inertia_group_search',
        example='[3,1]',
        example_span='e.g. [8,3], 8.3, C5 or 7T2',
    )
    wild = TextBox(
        name='wild_gap',
        label='Wild inertia subgroup',
        knowl='lf.wild_inertia_group_search',
        example='[4,1]',
        example_span='e.g. [8,3], 8.3, C5 or 7T2',
    )
    family = SneakyTextBox(
        name='family',
        label='Family',
        knowl='lf.family',
    )
    packet = SneakyTextBox(
        name='packet',
        label='Packet',
        knowl='lf.packet',
    )
    return degree, qp, c, e, f, topslope, slopes, visible, ind_insep, associated_inertia, jump_set, gal, aut, u, t, inertia, wild, family, packet

class FamilySearchArray(EmbeddedSearchArray):
    sorts = [
        ("", "Label", ['label']),
        ("gal", "Galois group", ['galT', 'label']),
        ("s", "top slope", ['top_slope', 'label']),
        ("ind_of_insep", "Index of insep", ['ind_of_insep', 'label']),
    ]
    def __init__(self):
        degree, qp, c, e, f, topslope, slopes, visible, ind_insep, associated_inertia, jump_set, gal, aut, u, t, inertia, wild, family, packet = common_boxes()
        one_per = SelectBox(
            name="one_per",
            label="Fields per packet",
            knowl="lf.packet",
            options=[("", "all"),
                     ("packet", "one")])
        self.refine_array = [[gal, slopes, ind_insep, associated_inertia, one_per]]

class FamiliesSearchArray(SearchArray):
    sorts = [
        ("", "base", ['p', 'n', 'e0', 'e', 'c', 'visible']),
        ("c", "discriminant exponent", ['p', 'n', 'c', 'e0', 'e', 'visible']),
        ("slopes", "slopes", ['p', 'n', 'visible']),
        ("ambiguity", "ambiguity", ['p', 'n', 'ambiguity', 'visible']),
        ("field_count", "num fields", ['p', 'n', 'field_count', 'visible']),
        ("mass", "mass", ['mass', 'p', 'n', 'e0', 'e', 'c', 'visible']),
        ("mass_missing", "mass missing", ['mass_missing', 'mass', 'p', 'n', 'e0', 'e', 'c', 'visible']),
    ]
    def __init__(self):
        #degree, qp, c, e, f, topslope, slopes, visible, ind_insep, associated_inertia, jump_set, gal, aut, u, t, inertia, wild, family, packet = common_boxes()
        degree = TextBox(
            name='n',
            label='Relative degree',
            knowl='lf.degree',
            example='6',
            example_span='6, or a range like 3..5')
        qp = TextBox(
            name='p',
            label=r'Residue field characteristic',
            short_label='Residue characteristic',
            knowl='lf.residue_field',
            example='3',
            example_span='3, or a range like 3..7')
        c = TextBox(
            name='c',
            label='Rel. disc. exponent',
            knowl='lf.discriminant_exponent',
            example='8',
            example_span='8, or a range like 2..6')
        e = TextBox(
            name='e',
            label='Rel. ramification index',
            knowl='lf.ramification_index',
            example='3',
            example_span='3, or a range like 2..6')
        f = TextBox(
            name='f',
            label='Rel. residue field degree',
            knowl='lf.residue_field_degree',
            example='3',
            example_span='3, or a range like 2..6')
        n0 = TextBox(
            name='n0',
            label='Base degree',
            knowl='lf.degree',
            example='6',
            example_span='6, or a range like 3..5')
        c0 = TextBox(
            name='c0',
            label='Base Disc. exponent',
            knowl='lf.discriminant_exponent',
            example='8',
            example_span='8, or a range like 2..6')
        e0 = TextBox(
            name='e0',
            label='Base ram. index',
            knowl='lf.ramification_index',
            example='3',
            example_span='3, or a range like 2..6')
        f0 = TextBox(
            name='f0',
            label='Base res. field degree',
            knowl='lf.residue_field_degree',
            example='3',
            example_span='3, or a range like 2..6')
        n_absolute = TextBox(
            name='n_absolute',
            label='Absolute degree',
            knowl='lf.degree',
            example='6',
            example_span='6, or a range like 3..5')
        c_absolute = TextBox(
            name='c_absolute',
            label='Absolute disc. exponent',
            knowl='lf.discriminant_exponent',
            example='8',
            example_span='8, or a range like 2..6')
        e_absolute = TextBox(
            name='e_absolute',
            label='Absolute ram. index',
            knowl='lf.ramification_index',
            example='3',
            example_span='3, or a range like 2..6')
        f_absolute = TextBox(
            name='f_absolute',
            label='Absolute res. field degree',
            knowl='lf.residue_field_degree',
            example='3',
            example_span='3, or a range like 2..6')
        w = TextBox(
            name='w',
            label='Wild ramification exponent',
            knowl='lf.ramification_index',
            example='3',
            example_span='3, or a range like 2..6')
        base = TextBox(
            name='base',
            label='Base',
            knowl='lf.family_base',
            example='2.2.1.0a1.1')
        mass = TextBox(
            name='mass',
            label='Mass',
            knowl='lf.family_mass',
            example='255/8',
            example_span='9/2, or a range like 1-10')
        mass_missing = TextBox(
            name='mass_missing',
            label='Missing mass',
            knowl='lf.family_missing_mass',
            example='0.5-',
            example_span='0, or a range like 0.1-0.4')
        ambiguity = TextBox(
            name='ambiguity',
            label='Ambiguity',
            knowl='lf.family_ambiguity',
            example='1',
            example_span='1, or a range like 2-8')
        field_count = TextBox(
            name='field_count',
            label='Field count',
            knowl='lf.family_field_count',
            example='1',
            example_span='2, or a range like 2-8')
        wild_segments = TextBox(
            name='wild_segments',
            label='Wild segments',
            knowl='lf.wild_segments',
            example='1',
            example_span='2, or a range like 2-4')
        self.refine_array = [[qp, degree, e, f, c],
                             [base, n0, e0, f0, c0],
                             [w, n_absolute, e_absolute, f_absolute, c_absolute],
                             #[visible, slopes, rams, heights, slope_multiplicities],
                             [mass, mass_missing, ambiguity, field_count, wild_segments]]

class LFSearchArray(SearchArray):
    noun = "field"

    sorts = [("", "prime", ['p', 'n', 'e', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("n", "degree", ['n', 'e', 'p', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("c", "discriminant exponent", ['c', 'p', 'n', 'e', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("e", "ramification index", ['n', 'e', 'p', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("f", "residue degree", ['f', 'n', 'p', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("gal", "Galois group", ['n', 'galT', 'p', 'e', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("u", "Galois unramified degree", ['u', 'f', 'n', 'p', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("t", "Galois tame degree", ['t', 'e', 'n', 'p', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("s", "top slope", ['top_slope', 'p', 'n', 'e', 'c', 'ctr_family', 'ctr_subfamily', 'ctr'])]
    jump_example = "2.1.4.6a2.1"
    jump_egspan = "e.g. 2.1.4.6a2.1"
    jump_knowl = "lf.search_input"
    jump_prompt = "Label"

    def __init__(self):
        degree, qp, c, e, f, topslope, slopes, visible, ind_insep, associated_inertia, jump_set, gal, aut, u, t, inertia, wild, family, packet = common_boxes()
        results = CountBox()

        self.browse_array = [[degree, qp], [e, f], [c, topslope], [u, t],
                             [slopes, visible], [ind_insep, associated_inertia],
                             [jump_set, aut], [gal, inertia], [wild], [results]]
        self.refine_array = [[degree, qp, c, gal],
                             [e, f, t, u],
                             [aut, inertia, ind_insep, associated_inertia, jump_set],
                             [topslope, slopes, visible, wild],
                             [family, packet]]

def ramdisp(p):
    return {'cols': ['n', 'e'],
            'constraint': {'p': p, 'n': {'$lte': 15}},
            'top_title':[('degree', 'lf.degree'),
                         ('and', None),
                         ('ramification index', 'lf.ramification_index'),
                         ('for %s-adic fields' % p, None)],
            'totaler': totaler(col_counts=False),
            'proportioner': proportioners.per_row_total}

def discdisp(p):
    return {'cols': ['n', 'c'],
            'constraint': {'p': p, 'n': {'$lte': 15}},
            'top_title':[('degree', 'lf.degree'),
                         ('and', None),
                         ('discriminant exponent', 'lf.discriminant_exponent'),
                         ('for %s-adic fields' % p, None)],
            'totaler': totaler(col_counts=False),
            'proportioner': proportioners.per_row_query(lambda n: {'n':int(n)})}

def galdisp(p, n):
    return {'cols': ['galois_label'],
            'constraint': {'p': p, 'n': n},
            'top_title':[('Galois groups', 'nf.galois_group'),
                         ('for %s-adic fields of' % p, None),
                         ('degree', 'lf.degree'),
                         (str(n), None)]}

# We want to look up gap ids and names only once, rather than once for each Galois group
@cached_function
def galcache():
    return knowl_cache(db.lf_fields.distinct("galois_label"))
def galformatter(gal):
    n, t = galdata(gal)
    return '<span class="nowrap">' + group_pretty_and_nTj(n, t, True, cache=galcache()).replace("(as", '</span><br><span class="nowrap">(as') + "</span>"
class LFStats(StatsDisplay):
    table = db.lf_fields
    baseurl_func = ".index"
    short_display = {'galois_label': 'Galois group',
                     'n': 'degree',
                     'e': 'ramification index',
                     'c': 'discriminant exponent'}
    sort_keys = {'galois_label': galdata}
    formatters = {
        'galois_label': galformatter
    }
    query_formatters = {
        'galois_label': (lambda gal: r'gal=%s' % (galunformatter(gal)))
    }

    stat_list = [
        ramdisp(2),
        ramdisp(3),
        discdisp(2),
        discdisp(3),
        galdisp(2, 4),
        galdisp(2, 6),
        galdisp(2, 8),
        galdisp(2, 10),
        galdisp(2, 12),
        galdisp(2, 14),
        galdisp(3, 6),
        galdisp(3, 9),
        galdisp(3, 12),
        galdisp(3, 15),
        galdisp(5, 10),
        galdisp(5, 15),
        galdisp(7, 14)
    ]

    def __init__(self):
        self.numfields = db.lf_fields.count()

    @staticmethod
    def dynamic_parse(info, query):
        from .main import common_parse
        common_parse(info, query)

    dynamic_parent_page = "padic-refine-search.html"
    dynamic_cols = ["galois_label", "slopes"]

    @property
    def short_summary(self):
        return self.summary + '  Here are some <a href="%s">further statistics</a>.' % (url_for(".statistics"))

    @property
    def summary(self):
        return r'The database currently contains %s %s, including all with $p < 200$ and %s $n < 16$.' % (
            comma(self.numfields),
            display_knowl("lf.padic_field", r"$p$-adic fields"),
            display_knowl("lf.degree", "degree")
        )

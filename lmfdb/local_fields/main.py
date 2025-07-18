# This Blueprint is about p-adic fields (aka local number fields)
# Author: John Jones

from flask import abort, render_template, request, url_for, redirect
from sage.all import (
    PolynomialRing, ZZ, QQ, RR, latex, cached_function, Integers, euler_phi, is_prime)
from sage.plot.all import line, points, text, Graphics, polygon

from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import (
    web_latex, coeff_to_poly, teXify_pol, display_multiset, display_knowl,
    parse_inertia, parse_newton_polygon, parse_bracketed_posints, parse_floats, parse_regex_restricted,
    parse_galgrp, parse_ints, clean_input, parse_rats, parse_noop, flash_error,
    SearchArray, TextBox, TextBoxWithSelect, SubsetBox, SelectBox, SneakyTextBox,
    HiddenBox, TextBoxNoEg, CountBox, to_dict, comma,
    search_wrap, count_wrap, embed_wrap, Downloader, StatsDisplay, totaler, proportioners, encode_plot,
    EmbeddedSearchArray, integer_options,
    redirect_no_cache, raw_typeset)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, ProcessedCol, MultiProcessedCol, RationalListCol, PolynomialCol, eval_rational_list
from lmfdb.utils.search_parsing import search_parser
from lmfdb.api import datapage
from lmfdb.local_fields import local_fields_page, logger
from lmfdb.local_fields.family import pAdicSlopeFamily, FAMILY_RE, latex_content, content_unformatter
from lmfdb.groups.abstract.main import abstract_group_display_knowl
from lmfdb.galois_groups.transitive_group import (
    transitive_group_display_knowl, group_display_inertia,
    knowl_cache, galdata, galunformatter,
    group_pretty_and_nTj, WebGaloisGroup)
from lmfdb.number_fields.web_number_field import (
    WebNumberField, string2list, nf_display_knowl)

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

# Takes a string '[2,5/2]'
def artin2swan(li):
    if li is not None:
        l1 = li.replace('[', '')
        l1 = l1.replace(']', '')
        l1 = l1.replace(' ', '')
        if l1 == '':
            return []
        return '[' + ','.join([str(QQ(z)-1) for z in l1.split(',')]) + ']'

def hidden2swan(hid):
    if hid is not None:
        parts = hid.split(']')
        a = parts[0].replace('[', '')
        a = a.replace(' ', '')
        if a == '':
            return hid
        return '[' + ','.join([str(QQ(z)-1) for z in a.split(',')]) + ']' + parts[1]

def local_algebra_data(labels):
    labs = labels.split(',')
    f1 = labs[0].split('.')
    labs = sorted(labs, key=lambda u: (int(j) for j in u.split('.')), reverse=True)
    ans = '<div align="center">'
    ans += '$%s$-adic algebra' % str(f1[0])
    ans += '</div>'
    ans += '<p>'
    ans += "<table class='ntdata'><th>Label<th>Polynomial<th>$e$<th>$f$<th>$c$<th>$G$<th>Artin slopes"
    if all(OLD_LF_RE.fullmatch(lab) for lab in labs):
        fall = {rec["old_label"]: rec for rec in db.lf_fields.search({"old_label":{"$in": labs}})}
    elif all(NEW_LF_RE.fullmatch(lab) for lab in labs):
        fall = {rec["new_label"]: rec for rec in db.lf_fields.search({"new_label":{"$in": labs}})}
    else:
        fall = {}
        for lab in labs:
            if OLD_LF_RE.fullmatch(lab):
                fall[lab] = db.lf_fields.lucky({"old_label":lab})
            elif NEW_LF_RE.fullmatch(lab):
                fall[lab] = db.lf_fields.lucky({"new_label":lab})
            else:
                fall[lab] = None
    for lab in labs:
        f = fall[lab]
        if f is None:
            ans += '<tr><td>Invalid label %s</td></tr>' % lab
            continue
        if f.get('new_label'):
            l = str(f['new_label'])
        else:
            l = str(f['old_label'])
        ans += '<tr><td><a href="%s">%s</a><td>'%(url_for_label(l),l)
        ans += format_coeffs(f['coeffs'])
        ans += '<td>%d<td>%d<td>%d<td>' % (f['e'],f['f'],f['c'])
        ans += transitive_group_display_knowl(f['galois_label'])
        if f.get('slopes') and f.get('t') and f.get('u'):
            ans += '<td>$' + show_slope_content(f['slopes'],f['t'],f['u'])+'$'
    ans += '</table>'
    if len(labs) != len(set(labs)):
        ans += '<p>Fields which appear more than once occur according to their given multiplicities in the algebra'
    return ans

def local_field_data(label):
    if OLD_LF_RE.fullmatch(label):
        f = db.lf_fields.lucky({"old_label": label})
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
    if f.get('galois_label') is not None:
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

def eisensteinformlatex(pol, unram):
    # pol=coeffs,  unram =string
    R = PolynomialRing(QQ, 'y')
    Rx = PolynomialRing(R, 'x')
    unram2 = R(unram.replace('t', 'y'))
    pol = R(pol)
    if unram2.degree() == 1 or unram2.degree() == pol.degree():
        return latex(pol).replace('y', 'x')
    unram = latex(Rx(unram.replace('t', 'x')))
    l = []
    while pol != 0:
        qr = pol.quo_rem(unram2)
        l.append(qr[1])
        pol = qr[0]
    newpol = latex(Rx(l))
    newpol = newpol.replace('x', '(' + unram + ')')
    newpol = newpol.replace('y', 'x')
    return newpol

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
    #tick = xmax / 160
    nextq = p
    L = Graphics()
    if ymax > 0:
        asp_ratio = (xmax + 2*txshift) / (2 * (ymax + 2*tyshift)) # 2 comes from the fact that the actual image has width 500 and height 250.
    else:
        # Add in silly white dot
        L += points([(0,1)], color="white")
        asp_ratio = (xmax + 2*txshift) / (8 + 16*tyshift)
    for i in range(xmax+1):
        L += line([(-i, 0), (-i, ymax)], color=(0.85,0.85,0.85), thickness=0.5)
    for j in range(ymax+1):
        L += line([(0,j), (-xmax, j)], color=(0.85,0.85,0.85), thickness=0.5)
    #L += line([(0,0), (0, ymax)], color="grey")
    #L += line([(0,0), (-xmax, 0)], color="grey")
    #for i in range(1, ymax + 1):
    #    L += line([(0, i), (-tick, i)], color="grey")
    #for i in range(0, xmax + 1):
    #    L += line([(-i, 0), (-i, tick/asp_ratio)], color="grey")
    xticks = set(P[0] for P in verts)
    yticks = set(P[1] for P in verts)
    if inds is not None:
        xticks = xticks.union(p**i for i in range(len(inds)))
        yticks = yticks.union(ind for ind in inds)
    for x in xticks:
        L += text(
            f"${-x}$", (-x, -tyshift/asp_ratio),
            color="black")
    for y in yticks:
        L += text(
            f"${y}$", (txshift, y),
            horizontal_alignment="left",
            color="black")

    if polys is not None:
        R = ZZ["t"]["z"]
        polys = [R(poly) for poly in reversed(polys)]
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
                f"${slope}$", (-(P[0] + Q[0]) / 2 + txshift, (P[1] + Q[1]) / 2 - tyshift/(2*asp_ratio)),
                horizontal_alignment="left",
                color="blue")
            #for x in range(P[0], Q[0] + 1):
            #    L += line(
            #        [(-x, Q[1]), (-x, P[1] - (x - P[0]) * slope)],
            #        color="grey",
            #    )
            #for y in range(Q[1], P[1]):
            #    L += line(
            #        [(-P[0] + (y - P[1]) / slope, y), (-P[0], y)],
            #        color="grey",
            #    )
        elif polys:
            # For tame inertia, the coefficients can occur at locations other than powers of p
            for j, c in enumerate(polys[i]):
                if j and c:
                    L += restag(c, P[0] + j, P[1])
    L += line([(-x,y) for (x,y) in verts], thickness=2)
    L += polygon([(-x,y) for (x,y) in verts] + [(-xmax, ymax)], alpha=0.08)
    if inds is not None:
        # print("INDS", inds)
        L += points([(-p**i, ind) for (i, ind) in enumerate(inds)], size=30, color="black", zorder=5)
    L.axes(False)
    L.set_aspect_ratio(asp_ratio)
    return encode_plot(L, pad=0, pad_inches=0, bbox_inches="tight", figsize=(8,4), dpi=300)


@app.context_processor
def ctx_local_fields():
    return {'local_field_data': local_field_data,
            'local_algebra_data': local_algebra_data}


# Utilities for subfield display
def format_lfield(label, p):
    if OLD_LF_RE.fullmatch(label):
        data = db.lf_fields.lucky({"old_label": label}, ["n", "p", "rf", "old_label", "new_label"])
    else:
        data = db.lf_fields.lucky({"new_label": label}, ["n", "p", "rf", "old_label", "new_label"])
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
    return ('$' + sl + '$')

def show_slopes2(sl):
    # uses empty brackets with a space instead of None
    if str(sl) == "[]":
        return r'[\ ]'
    return (sl)

def show_slope_content(sl,t,u):
    if sl is None or t is None or u is None:
        return 'not computed'
    sc = str(sl)
    if t > 1:
        sc += '_{%d}' % t
    if u > 1:
        sc += '^{%d}' % u
    return latex_content(sc)

relative_columns = ["base", "n0", "e0", "f0", "c0", "label_absolute", "n_absolute", "e_absolute", "f_absolute", "c_absolute"]

@local_fields_page.route("/")
def index():
    bread = get_bread()
    info = to_dict(request.args, search_array=LFSearchArray(), stats=LFStats())
    if any(col in info for col in relative_columns):
        info["relative"] = 1
    if len(request.args) != 0:
        info["search_type"] = search_type = info.get("search_type", info.get("hst", ""))
        if search_type in ['Families', 'FamilyCounts']:
            info['search_array'] = FamiliesSearchArray(relative=("relative" in info))
        if search_type in ['Counts', 'FamilyCounts']:
            return local_field_count(info)
        elif search_type in ['Families', 'RandomFamily']:
            return families_search(info)
        elif search_type in ['List', '', 'Random']:
            return local_field_search(info)
        else:
            flash_error("Invalid search type; if you did not enter it in the URL please report")
    info["field_count"] = db.lf_fields.stats.column_counts(["n", "p"])
    info["family_count"] = db.lf_families.count({"n0":1}, groupby=["n", "p"])
    return render_template("lf-index.html", title="$p$-adic fields", titletag="p-adic fields", bread=bread, info=info, learnmore=learnmore_list())

@local_fields_page.route("/families/")
def family_redirect():
    info = to_dict(request.args)
    info["search_type"] = "Families"
    if "relative" not in info:
        # Check for the presence of any relative-only arguments
        if any(x in info for x in relative_columns):
            info["relative"] = 1
    return redirect(url_for(".index", **info))


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
    if FAMILY_RE.fullmatch(info['jump']):
        return redirect(url_for_family(info['jump']), 301)
    else:
        return redirect(url_for_label(info['jump']), 301)

def unpack_slopes(slopes, t, u):
    return eval_rational_list(slopes), t, u

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

def formatbracketcol(blist):
    if blist == []:
        return r'$[\ ]$'
    if blist == '':
        return 'not computed'
    return f'${blist}$'

def intcol(j):
    if j == '':
        return 'not computed'
    return f'${j}$'

#label_col = LinkCol("new_label", "lf.field.label", "Label", url_for_label)
label_col = MultiProcessedCol("label", "lf.field_label", "Label", ["old_label", "new_label"], (lambda old_label, new_label: f'<a href="{url_for_label(new_label)}">{new_label}</a>' if new_label else f'<a href="{url_for_label(old_label)}">{old_label}</a>'), apply_download=(lambda old_label, new_label: (new_label if new_label else old_label)))

def poly_col(relative=False):
    if relative:
        def title(info): return "Polynomial" if info['family'].n0 == 1 else r"Polynomial $/ \Q_p$"
    else:
        title = "Polynomial"
    return MultiProcessedCol("coeffs", "lf.defining_polynomial", title, ["coeffs", "unram"], eisensteinformlatex, mathmode=True, short_title="polynomial", apply_download=lambda coeffs, unram: coeffs)
p_col = MathCol("p", "lf.qp", "$p$", short_title="prime")
c_col = MathCol("c", "lf.discriminant_exponent", "$c$", short_title="discriminant exponent")
e_col = MathCol("e", "lf.ramification_index", "$e$", short_title="ramification index")
f_col = MathCol("f", "lf.residue_field_degree", "$f$", short_title="residue field degree")
def gal_col(relative=False):
    if relative:
        def title(info): return "Galois group" if info['family'].n0 == 1 else r"Galois group $/ \Q_p$"
    else:
        title = "Galois group"
    return MultiProcessedCol("gal", "nf.galois_group", title,
                             ["n", "gal", "cache"],
                             galcolresponse, short_title="Galois group",
                             apply_download=lambda n, t, cache: [n, t])
def aut_col(default):
    return MathCol("aut", "lf.automorphism_group", r"$\#\Aut(K/\Q_p)$", short_title="auts", default=default)
def slopes_col(default=True, relative=False):
    if relative:
        def title(info): return "Artin slope content" if info['family'].n0 == 1 else r"Artin slope content $/ \Q_p$"
    else:
        title = "Artin slope content"
    return MultiProcessedCol("slopes", "lf.slopes", title,
                             ["slopes", "t", "u"],
                             show_slope_content, short_title="Artin slope content",
                             apply_download=unpack_slopes, default=default)
def hidden_col(default=True, relative=False):
    if relative:
        def title(info): return "Hidden Artin slopes" if info['family'].n0 == 1 else r"Hidden Artin slopes $/ \Q_p$"
    else:
        title = "Hidden Artin slopes"
    return ProcessedCol("hidden", "lf.slopes",
                        title,
                        latex_content, short_title="hidden Artin slopes",
                        apply_download=False, default=default)

def swanslopes_col(default=False, relative=False):
    if relative:
        def title(info): return "Swan slope content" if info['family'].n0 == 1 else r"Swan slope content $/ \Q_p$"
    else:
        title = "Swan slope content"
    return MultiProcessedCol("swanslopes", "lf.slopes", title,
                             ["slopes", "t", "u", "c"],
                             (lambda slopes, t, u, c: show_slope_content(artin2swan(slopes), t, u)),
                             short_title="Swan slope content",
                             apply_download=(lambda slopes, t, u: unpack_slopes(artin2swan(slopes), t, u)),
                             default=default)

def hiddenswan_col(default=False, relative=False):
    if relative:
        def title(info): return "Hidden Swan slopes" if info['family'].n0 == 1 else r"Hidden Swan slopes $/ \Q_p$"
    else:
        title = "Hidden Swan slopes"
    return MultiProcessedCol("hiddenswan", "lf.slopes",
                             title,
                             ["hidden", "c"],
                             (lambda hidden, c: latex_content(hidden2swan(hidden))),
                             short_title="hidden Swan slopes",
                             apply_download=False,
                             default=default)

def insep_col(default=True, relative=False):
    if relative:
        def title(info): return "Ind. of Insep." if info['family'].n0 == 1 else r"Ind. of Insep. $/ \Q_p$"
    else:
        title = "Ind. of Insep."
    return ProcessedCol("ind_of_insep", "lf.indices_of_inseparability", title, formatbracketcol, default=default, short_title="ind. of insep.")
def assoc_col(default=True, relative=False):
    if relative:
        def title(info): return "Assoc. Inertia" if info['family'].n0 == 1 else r"Assoc. Inertia $/ \Q_p$"
    else:
        title = "Assoc. Inertia"
    return ProcessedCol("associated_inertia", "lf.associated_inertia", title, formatbracketcol, default=default)
def jump_col(default=True):
    return ProcessedCol("jump_set", "lf.jump_set", "Jump Set", func=lambda js: f"${js}$" if js else "undefined", default=default, mathmode=False)
def respoly_col():
    return ProcessedCol("residual_polynomials", "lf.residual_polynomials", "Resid. Poly", default=False, mathmode=True, func=lambda rp: ','.join(teXify_pol(f) for f in rp))

lf_columns = SearchColumns([
    label_col,
    MathCol("n", "lf.degree", "$n$", short_title="degree", default=False),
    poly_col(),
    p_col,
    f_col,
    e_col,
    c_col,
    gal_col(False),
    ProcessedCol("u", "lf.unramified_degree", "$u$", intcol, short_title="unramified degree", default=False),
    ProcessedCol("t", "lf.tame_degree", "$t$", intcol, short_title="tame degree", default=False),
    RationalListCol("visible", "lf.slopes", "Visible Artin slopes",
                    show_slopes2, default=lambda info: info.get("visible"), short_title="visible Artin slopes"),
    # throw in c as a trick to differentiate it from just visible
    MultiProcessedCol("visibleswan", "lf.slopes", "Visible Swan slopes",
                      ["visible","c"],
                      (lambda visible, c: latex_content(show_slopes2(artin2swan(visible)))),
                      mathmode=False, default=False,
                      short_title="visible Swan slopes",
                      apply_download=(lambda slopes: eval_rational_list(artin2swan(slopes)))),
    slopes_col(),
    swanslopes_col(),
    hidden_col(default=False),
    hiddenswan_col(),
    aut_col(lambda info:info.get("aut")),
    # want apply_download for download conversion
    PolynomialCol("unram", "lf.unramified_subfield", "Unram. Ext.", default=lambda info:info.get("visible")),
    ProcessedCol("eisen", "lf.eisenstein_polynomial", "Eisen. Poly.", default=lambda info:info.get("visible"), mathmode=True, func=format_eisen),
    insep_col(default=lambda info: info.get("ind_of_insep")),
    assoc_col(default=lambda info: info.get("associated_inertia")),
    respoly_col(),
    jump_col(default=lambda info: info.get("jump_set"))],
    db_cols=["aut", "c", "coeffs", "e", "f", "gal", "old_label", "new_label", "n", "p", "slopes", "t", "u", "visible", "hidden", "ind_of_insep", "associated_inertia", "jump_set", "unram", "eisen", "family", "residual_polynomials"])

family_columns = SearchColumns([
    label_col,
    MultiProcessedCol("packet_link", "lf.packet", "Packet size", ["packet", "packet_size"], (lambda packet, size: '' if size is None else f'<a href="{url_for_packet(packet)}">{size}</a>'), default=lambda info: info.get("one_per") == "packet", contingent=lambda info: info['family'].n0 == 1),
    poly_col(relative=True),
    gal_col(lambda info: "Galois group" if info['family'].n0 == 1 else r"Galois group $/ \Q_p$"),
    MathCol("galsize", "nf.galois_group", lambda info: "Galois degree" if info['family'].n0 == 1 else r"Galois degree $/ \Q_p$", short_title="Galois degree"),
    aut_col(True),
    slopes_col(default=False, relative=True),
    swanslopes_col(relative=True),
    hidden_col(relative=True),
    hiddenswan_col(relative=True),
    insep_col(relative=True),
    assoc_col(relative=True),
    respoly_col(),
    jump_col()],
    db_cols=["old_label", "new_label", "packet", "packet_size", "coeffs", "unram", "n", "gal", "aut", "slopes", "t", "u", "c", "hidden", "ind_of_insep", "associated_inertia", "residual_polynomials", "jump_set"])

class PercentCol(MathCol):
    def display(self, rec):
        x = self.get(rec)
        if x == 0:
            return r"$0\%$"
        elif x == 1:
            return r"$100\%$"
        return fr"${100*x:.2f}\%$"

def pretty_link(label, p, n, rf):
    if OLD_LF_RE.fullmatch(label):
        name = {"old_label": label}
    else:
        name = {"new_label": label}
    name.update({"p": p, "n": n, "rf": rf})
    name = prettyname(name)
    return f'<a href="{url_for_label(label)}">{name}</a>'

families_columns = SearchColumns([
    LinkCol("label", "lf.family_label", "Label", url_for_family),
    MathCol("p", "lf.residue_field", "$p$", short_title="prime"),
    MathCol("n", "lf.degree", "$n$", short_title="degree"),
    MathCol("n0", "lf.degree", "$n_0$", short_title="base degree", default=False, contingent=lambda info: "relative" in info),
    MathCol("n_absolute", "lf.degree", r"$n_{\mathrm{abs}}$", short_title="abs. degree", default=False, contingent=lambda info: "relative" in info),
    MathCol("f", "lf.residue_field_degree", "$f$", short_title="res. field degree"),
    MathCol("f0", "lf.residue_field_degree", "$f_0$", short_title="base res. field degree", default=False, contingent=lambda info: "relative" in info),
    MathCol("f_absolute", "lf.residue_field_degree", r"$f_{\mathrm{abs}}$", short_title="abs. residue field degree", default=False, contingent=lambda info: "relative" in info),
    MathCol("e", "lf.ramification_index", "$e$", short_title="ram. index"),
    MathCol("e0", "lf.ramification_index", "$e_0$", short_title="base ram. index", default=False, contingent=lambda info: "relative" in info),
    MathCol("e_absolute", "lf.ramification_index", r"$e_{\mathrm{abs}}$", short_title="abs. ram. index", default=False, contingent=lambda info: "relative" in info),
    MathCol("c", "lf.discriminant_exponent", "$c$", short_title="disc. exponent"),
    MathCol("c0", "lf.discriminant_exponent", "$c_0$", short_title="base disc. exponent", default=False, contingent=lambda info: "relative" in info),
    MathCol("c_absolute", "lf.discriminant_exponent", r"$c_{\mathrm{abs}}$", short_title="abs. disc. exponent", default=False, contingent=lambda info: "relative" in info),
    MultiProcessedCol("base_field", "lf.family_base", "Base",
                      ["base", "p", "n0", "rf0"],
                      pretty_link, contingent=lambda info: "relative" in info),
    RationalListCol("visible", "lf.slopes", "Abs. Artin slopes",
                    show_slopes2, default=False, short_title="abs. Artin slopes"),
    RationalListCol("slopes", "lf.slopes", "Swan slopes", short_title="Swan slopes"),
    RationalListCol("means", "lf.means", "Means", delim=[r"\langle", r"\rangle"]),
    RationalListCol("rams", "lf.rams", "Rams", delim="()"),
    ProcessedCol("poly", "lf.family_polynomial", "Generic poly", lambda pol: teXify_pol(pol, greek_vars=True, subscript_vars=True), mathmode=True, default=False),
    MathCol("ambiguity", "lf.family_ambiguity", "Ambiguity"),
    MathCol("field_count", "lf.family_field_count", "Field count"),
    MathCol("mass_relative", "lf.family_mass", "Mass", orig=["mass_relative_display"]),
    MathCol("mass_absolute", "lf.family_mass", "Mass (absolute)", orig=["mass_absolute_display"], default=False),
    MathCol("mass_stored", "lf.family_mass", "Mass stored", default=False),
    PercentCol("mass_found", "lf.family_mass", "Mass found", default=False),
    MathCol("wild_segments", "lf.wild_segments", "Wild segments", default=False),
    MathCol("packet_count", "lf.packet", "Num. Packets", contingent=lambda info: "relative" not in info),
])

def lf_postprocess(res, info, query):
    cache = knowl_cache(list({f"{rec['n']}T{rec['gal']}" for rec in res if rec.get('gal') is not None}))
    for rec in res:
        rec["cache"] = cache
        if rec.get('gal') is not None:
            gglabel = f"{rec['n']}T{rec['gal']}"
            rec["galsize"] = cache[gglabel]["order"]
        else:
            rec["galsize"] = " $not computed$ " # undo mathmode
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

slopes_re = re.compile(r"\[(\d+(/\d+)?)?(,\d+(/\d+)?)*\]")
rams_re = re.compile(r"\((\d+(/\d+)?)?(,\d+(/\d+)?)*\)")
means_re = re.compile(r"\{(\d+(/\d+)?)?(,\d+(/\d+)?)*\}") # clean_info changed "<>" to "{}" for html safety
@search_parser(default_field='herbrand', angle_to_curly=True)
def parse_herbrand(inp, query, qfield):
    # We ignore qfield, since it is determined from the delimiters of the input
    if slopes_re.fullmatch(inp):
        query["slopes"] = inp.replace(",", ", ")
    elif rams_re.fullmatch(inp):
        query["rams"] = "[" + inp[1:-1].replace(",", ", ") + "]"
    elif means_re.fullmatch(inp):
        query["means"] = "[" + inp[1:-1].replace(",", ", ") + "]"
    else:
        print("INPINPINPINP", inp, len(inp))
        raise ValueError("Improperly formatted Herbrand invariant")

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
    parse_rats(info,query,'topslope',qfield='top_slope',name='Top Artin slope', process=ratproc)
    parse_newton_polygon(info,query,"slopes", qfield="slopes_tmp", mode=info.get('slopes_quantifier'))
    parse_newton_polygon(info,query,"visible", qfield="visible_tmp", mode=info.get('visible_quantifier'))
    parse_newton_polygon(info,query,"ind_of_insep", qfield="ind_of_insep_tmp", mode=info.get('insep_quantifier'), reversed=True)
    parse_bracketed_posints(info,query,"associated_inertia")
    parse_bracketed_posints(info,query,"jump_set")
    parse_inertia(info,query,qfield=('inertia_gap','inertia'))
    parse_inertia(info,query,qfield=('wild_gap','wild_gap'), field='wild_gap')
    parse_noop(info,query,'packet')
    parse_noop(info,query,'family')
    parse_noop(info,query,'hidden')

def count_fields(p, n=None, f=None, e=None, eopts=None):
    # Implement a formula due to Monge for the number of fields with given n or e,f
    if n is None and (f is None or e is None):
        raise ValueError("Must specify n or (f and e)")
    if f is None:
        if e is None:
            if eopts is None:
                return sum(count_fields(p, e=e, f=n//e) for e in n.divisors())
            return sum(count_fields(p, e=e, f=n//e) for e in n.divisors() if e in eopts)
        elif n % e != 0:
            return 0
        f = n // e
    elif e is None:
        if n % f != 0:
            return 0
        e = n // f

    def eps(i):
        return sum(p**(-j) for j in range(1, i+1))

    def ee(i):
        return euler_phi(p**i)

    def sig(n0, e, f, s):
        nn = n0 * e * f
        return 1 + sum(p**i * (p**(eps(i) * nn) - p**(eps(i-1) * nn)) for i in range(1,s+1))

    def delta(m, s, i):
        if s == i == 0:
            return 1
        if s > i == 0:
            return (p**m - 1) * p**(m * (s-1))
        if s > i > 0:
            return (p - 1) * (p**m - 1) * p**(m * (s - 1) + i - 1)
        if s == i > 0:
            return (p - 1) * p**(m * s + s - 1)
        return 0

    def term(i, fp, ep):
        ep_val = ep.valuation(p)
        epp = e / (ee(i) * ep)
        if not epp.is_integer():
            return 0
        epp_val, epp_unit = epp.val_unit(p)
        fpp = f / fp
        a = 1 if ((p**fp - 1) / epp_unit).is_integer() else 0
        return a * euler_phi(epp_unit) * euler_phi(fpp) / ee(i) * sig(ee(i), ep, fp, ep_val) * delta(ee(i) * ep * fp, epp_val, i)

    return 1/f * sum(term(i, fp, ep) for i in range(e.valuation(p)+1) for fp in f.divisors() for ep in e.divisors())

def fix_top_slope(s):
    if isinstance(s, float):
        return QQ(s)
    elif isinstance(s, str):
        return QQ(s[12:])
    return s

def count_postprocess(res, info, query):
    # We account for two possible ways of encoding top_slope
    for key, val in list(res.items()):
        res[key[0],fix_top_slope(key[1])] = res.pop(key)
    # Fill in entries using field_count
    if info["search_type"] == "Counts" and set(query).issubset("pne"):
        groupby = info["groupby"]
        if groupby == ["p", "n"]:
            if "e" in info:
                # We need to handle the possibility that there are constraints on e
                eopts = integer_options(info["e"], upper_bound=47)
            else:
                eopts = None

            def func(p, n): return count_fields(p, n=n, eopts=eopts)
        elif groupby == ["p", "e"]:
            n = db.lf_fields.distinct("n", query)
            if len(n) != 1:
                # There were no results...
                return res
            n = ZZ(n[0])
            def func(p, e): return count_fields(p, n=n, e=e)
        elif groupby == ["n", "e"]:
            p = db.lf_fields.distinct("p", query)
            if len(p) != 1:
                # No results...
                return res
            p = ZZ(p[0])
            def func(n, e): return count_fields(p, n=n, e=e)
        else:
            return res
        for a in info["row_heads"]:
            for b in info["col_heads"]:
                if (a,b) not in res:
                    cnt = func(ZZ(a),ZZ(b))
                    if cnt:
                        info["nolink"].add((a,b))
                        res[a,b] = cnt
    return res

@count_wrap(
    template="lf-count-results.html",
    table=db.lf_fields,
    groupby=["p", "n"],
    title="Local field count results",
    err_title="Local field search input error",
    postprocess=count_postprocess,
    bread=lambda: get_bread([("Count results", " ")]),
)
def local_field_count(info, query):
    if info["search_type"] == "Counts":
        table = db.lf_fields
        common_parse(info, query)
    else:
        common_family_parse(info, query)
        table = db.lf_families
        if "base" in query:
            p = query["base"].split(".")[0]
            if not p.isdigit():
                raise ValueError(f"Invalid base {query['base']}")
            p = int(p)
            if "p" in query:
                tmp = integer_options(info["p"], contained_in=table.distinct("p"))
                if p not in tmp:
                    raise ValueError("Base prime not compatible with constraints on p")
            info["p"] = str(p)
            query["p"] = p
        if "relative" not in info:
            query["n0"] = 1
    if "gal" in info and "n" not in info:
        # parse_galgrp adds restrictions on n
        if isinstance(query["n"], int):
            info["n"] = str(query["n"])
        else:
            info["n"] = ",".join(query["n"]["$in"])
    groupby = []
    heads = []
    maxval = {"p": 200, "n": 47, "e": 47}
    for col in ["p", "n", "e", "c", "top_slope"]:
        if col in "pne" and info["search_type"] == "Counts":
            # Allow user to get virtual counts outside the specified range
            tmp = integer_options(info.get(col, f"1-{maxval[col]}"), upper_bound=maxval[col])
            if col == "p":
                tmp = [p for p in tmp if ZZ(p).is_prime()]
            elif col == "n" and "e" in info:
                # Constrain degrees to b only multiples of some e
                eopts = integer_options(info["e"], upper_bound=47)
                if 1 not in eopts:
                    emuls = set()
                    for e in eopts:
                        emuls.update([e*j for j in range(1, 47//e + 1)])
                    tmp = sorted(set(tmp).intersection(emuls))
        else:
            tmp = table.distinct(col, query)
        if len(tmp) > 1:
            if col == "top_slope":
                tmp = sorted(fix_top_slope(s) for s in tmp)
            groupby.append(col)
            heads.append(tmp)
        if len(groupby) == 2:
            break
    else:
        raise ValueError("To generate count table, you must not specify all of p, n, e, and c")
    query["__groupby__"] = info["groupby"] = groupby
    if info["search_type"] == "FamilyCounts":
        query["__table__"] = table
        query["__title__"] = "Family count results"

    info["nolink"] = set()
    urlgen_info = dict(info)
    urlgen_info.pop("hst", None)
    urlgen_info.pop("stats", None)
    if info["search_type"] == "FamilyCounts":
        urlgen_info["search_type"] = "Families"

    def url_generator(a, b):
        if (a,b) in info["nolink"]:
            return
        info_copy = dict(urlgen_info)
        info_copy.pop("search_array", None)
        if info["search_type"] == "Counts":
            info_copy.pop("search_type", None)
        info_copy.pop("nolink", None)
        info_copy.pop("groupby", None)
        info_copy[groupby[0]] = a
        info_copy[groupby[1]] = b
        return url_for(".index", **info_copy)

    info["row_heads"], info["col_heads"] = heads
    names = {"p": "Prime", "n": "Degree", "e": "Ramification index", "c": "Discriminant exponent", "top_slope": "Top Artin slope"}
    info["row_label"], info["col_label"] = [names[col] for col in groupby]
    info["url_func"] = url_generator

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
        if NEW_LF_RE.fullmatch(label):
            data = db.lf_fields.lucky({"new_label":label})
            if data is None:
                flash_error("Field %s was not found in the database.", label)
                return redirect(url_for(".index"))
        elif OLD_LF_RE.fullmatch(label):
            data = db.lf_fields.lucky({"old_label": label})
            if data is None:
                flash_error("Field %s was not found in the database.", label)
                return redirect(url_for(".index"))
            new_label = data.get("new_label")
            if new_label is not None:
                return redirect(url_for_label(label=new_label), 301)
        else:
            flash_error("%s is not a valid label for a $p$-adic field.", label)
            return redirect(url_for(".index"))
        title = '$p$-adic field ' + prettyname(data)
        titletag = 'p-adic field ' + prettyname(data)
        polynomial = coeff_to_poly(data['coeffs'])
        p = data['p']
        Qp = r'\Q_{%d}' % p
        e = data['e']
        f = data['f']
        n = data['n']
        cc = data['c']
        auttype = 'aut'
        if data.get('galois_label') is not None:
            gt = int(data['galois_label'].split('T')[1])
            the_gal = WebGaloisGroup.from_nt(n,gt)
            isgal = ' Galois' if the_gal.order() == n else ' not Galois'
            abelian = ' and abelian' if the_gal.is_abelian() else ''
            galphrase = 'This field is'+isgal+abelian+r' over $\Q_{%d}.$' % p
            if the_gal.order() == n:
                auttype = 'gal'
            info['aut_gp_knowl'] = the_gal.aut_knowl()
        # we don't know the Galois group, but maybe the Aut group is obvious
        elif data['aut'] == 1:
            info['aut_gp_knowl'] = abstract_group_display_knowl('1.1')
        elif is_prime(data['aut']):
            info['aut_gp_knowl'] = abstract_group_display_knowl(f"{data['aut']}.1")
        prop2 = [
            ('Label', label),
            ('Base', r'\(%s\)' % Qp),
            ('Degree', r'\(%s\)' % data['n']),
            ('e', r'\(%s\)' % e),
            ('f', r'\(%s\)' % f),
            ('c', r'\(%s\)' % cc),
            ('Galois group', group_pretty_and_nTj(n, gt) if data.get('galois_label') is not None else 'not computed'),
        ]
        # Look up the unram poly so we can link to it
        unramdata = db.lf_fields.lucky({'p': p, 'n': f, 'c': 0})
        if unramdata is None:
            logger.fatal("Cannot find unramified field!")
            unramfriend = ''
        else:
            ulabel = unramdata.get('new_label')
            if ulabel is None:
                ulabel = unramdata.get('old_label')
            unramfriend = url_for_label(ulabel)

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

        rflabel = db.lf_fields.lucky({'p': p, 'n': {'$in': [1, 2]}, 'rf': data['rf']}, projection=["new_label", "old_label"])
        if rflabel is None:
            logger.fatal("Cannot find discriminant root field!")
            rffriend = ''
        else:
            if rflabel.get("new_label"):
                rflabel = rflabel["new_label"]
            else:
                rflabel = rflabel["old_label"]
            rffriend = url_for_label(rflabel)
        gsm = data['gsm']
        if gsm == [0]:
            gsm = 'not computed'
        elif gsm == [-1]:
            gsm = 'Does not exist'
        else:
            gsm = lf_formatfield(','.join(str(b) for b in gsm))

        if data['wild_gap'] is not None and data['wild_gap'] != [0,0]:
            wild_inertia = abstract_group_display_knowl(f"{data['wild_gap'][0]}.{data['wild_gap'][1]}")
        else:
            wild_inertia = 'not computed'

        if data['f'] == 1 or data['e'] == 1:
            thepolynomial = raw_typeset(polynomial)
        else:
            eform = '$' + eisensteinformlatex(data['coeffs'], data['unram']) + '$'
            thepolynomial = raw_typeset(polynomial, eform)
        info.update({
            'polynomial': thepolynomial,
            'n': n,
            'p': p,
            'c': cc,
            'e': e,
            'f': f,
            'rf': lf_display_knowl( rflabel, name=printquad(data['rf'], p)),
            'base': lf_display_knowl(str(p)+'.1.0.1', name='$%s$' % Qp),
            'hw': data['hw'],
            'visible': latex_content(data['visible']),
            'visible_swan': latex_content(artin2swan(data['visible'])),
            'wild_inertia': wild_inertia,
            'unram': unramp,
            'ind_insep': latex_content(str(data['ind_of_insep'])),
            'eisen': eisenp,
            'gsm': gsm,
            'auttype': auttype,
            'subfields': format_subfields(data['subfield'],data['subfield_mult'],p),
            'aut': data['aut'],
            'ppow_roots_of_unity': data.get('ppow_roots_of_unity'),
        })
        friends = []
        if data.get("ppow_roots_of_unity") is not None:
            prou = data["ppow_roots_of_unity"]
            rou = (p**f - 1) * p**prou
            if f > 1:
                rou_expr = [f"({p}^{{ {f} }} - 1)"]
            elif p > 2:
                rou_expr = [f"({p} - 1)"]
            else:
                rou_expr = []
            if prou == 1:
                rou_expr.append(f"{p}")
            elif prou > 1:
                rou_expr.append(f"{p}^{{ {prou} }}")
            rou_expr = r" \cdot ".join(rou_expr)
            if rou_expr == "2": # only case where we don't want an = sign
                info["roots_of_unity"] = "$2$"
            else:
                info["roots_of_unity"] = f"${rou} = {rou_expr}$"
        else:
            info["roots_of_unity"] = "not computed"
        if data.get("family") is not None:
            friends.append(('Absolute family', url_for(".family_page", label=data["family"])))
            subfields = [f"{p}.1.1.0a1.1"]
            if data["subfield"]:
                if all(OLD_LF_RE.fullmatch(slabel) for slabel in data["subfield"]):
                    new_labels = list(db.lf_fields.search({"old_label":{"$in": data["subfield"]}}, "new_label"))
                    if all(slabel is not None for slabel in new_labels):
                        subfields.extend(new_labels)
                    else:
                        subfields.extend(data["subfield"])
                elif all(NEW_LF_RE.fullmatch(slabel) for slabel in data["subfield"]):
                    subfields.extend(data["subfield"])
            friends.append(('Families containing this field', url_for(".index", relative=1, search_type="Families", label_absolute=data["family"],base=",".join(subfields))))
            rec = db.lf_families.lucky({"label":data["family"]}, ["means", "rams"])
            info["means"] = latex_content(rec["means"]).replace("[", r"\langle").replace("]", r"\rangle")
            info["rams"] = latex_content(rec["rams"]).replace("[", "(").replace("]", ")")
        if n < 16 and NEW_LF_RE.fullmatch(label):
            friends.append(('Families with this base', url_for(".index", relative=1, search_type="Families", base=label)))
        if data.get('slopes') is not None:
            info['slopes'] = latex_content(data['slopes'])
            info['swanslopes'] = latex_content(artin2swan(data['slopes']))
        if data.get('inertia') is not None:
            info['inertia'] = group_display_inertia(data['inertia'])
        for k in ['gms', 't', 'u', 'galois_degree']:
            if data.get(k) is not None:
                info[k] = data[k]
        if data.get('ram_poly_vert') is not None:
            info['ram_polygon_plot'] = plot_ramification_polygon(data['ram_poly_vert'], p, data['residual_polynomials'], data['ind_of_insep'])
        if data.get('residual_polynomials') is not None:
            info['residual_polynomials'] = ",".join(f"${teXify_pol(poly)}$" for poly in data['residual_polynomials'])
        if data.get('associated_inertia') is not None:
            info['associated_inertia'] = ",".join(f"${ai}$" for ai in data['associated_inertia'])
        if data.get('galois_label') is not None:
            info.update({'gal': group_pretty_and_nTj(n, gt, True),
                         'galphrase': galphrase,
                         'gt': gt})
            friends.append(('Galois group', "/GaloisGroup/%dT%d" % (n, gt)))
        if data.get('jump_set') is not None:
            info['jump_set'] = data['jump_set']
            if info['jump_set'] == []:
                info['jump_set'] = "undefined"
            else:
                info['jump_set'] = f"${info['jump_set']}$"
        if unramfriend != '':
            friends.append(('Unramified subfield', unramfriend))
        if rffriend != '':
            friends.append(('Discriminant root field', rffriend))
        if data['is_completion']:
            # Need to check whether number fields are storing completions using new labels or old labels
            zeta3loc = db.nf_fields.lookup("2.0.3.1", "local_algs")
            if zeta3loc == ["3.2.1.2"]:
                # Old labels
                lstr = data["old_label"]
            elif zeta3loc == ["3.1.2.1a1.1"]:
                # New labels
                lstr = data["new_label"]
            else:
                # Error; fall back on old label
                print("ZETALOC", zeta3loc)
                flash_error("Incorrect local algebra for Q(zeta3)")
                lstr = data["old_label"]
            friends.append(('Number fields with this completion',
                url_for('number_fields.number_field_render_webpage')+f"?completions={lstr}"))
        downloads = [('Underlying data', url_for('.lf_data', label=label))]

        if data.get('new_label'):
            _, _, _, fam, i = data['new_label'].split(".")
            _, fama, subfam = re.split(r"(\D+)", fam)
            bread = get_bread([(str(p), url_for('.index', p=p)),
                               (f"{f}.{e}", url_for('.index', p=p, e=e, f=f)),
                               (str(cc), url_for('.index', p=p, e=e, f=f, c=cc)),
                               (fama, url_for('.family_page', label=data['family'])),
                               (f'{subfam}.{i}', ' ')])
        else:
            bread = get_bread([(str(p), url_for('.index', p=p)),
                               (str(n), url_for('.index', p=p, n=n)),
                               (str(cc), url_for('.index', p=p, n=n, c=cc)),
                               (data['label'], ' ')])
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
    if ent.get('new_label'):
        return ent['new_label']
    return ent['old_label']

@cached_function
def getu(p):
    if p == 2:
        return 5
    return int(Integers(p).quadratic_nonresidue())

def printquad(code, p):
    if code == [1, 0]:
        return (r'$\Q_{%s}$' % p)
    u = getu(p)
    if code == [1, 1]:
        return (r'$\Q_{%s}(\sqrt{%s})$' % (p,u))
    if code == [-1, 1]:
        return (r'$\Q_{%s}(\sqrt{-%s})$' % (p,u))
    s = code[0]
    if code[1] == 1:
        s = str(s) + r'\cdot '+str(u)
    return (r'$\Q_{' + str(p) + r'}(\sqrt{' + str(s) + '})$')

@local_fields_page.route("/data/<label>")
def lf_data(label):
    if NEW_LF_RE.fullmatch(label):
        title = f"Local field data - {label}"
        bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
        sorts = [["p", "n", "e", "c", "ctr_family", "ctr_subfamily", "ctr"]]
        return datapage(label, "lf_fields", title=title, bread=bread, label_cols=["new_label"], sorts=sorts)
    elif OLD_LF_RE.fullmatch(label):
        title = f"Local field data - {label}"
        bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
        sorts = [["p", "n", "c", "old_label"]]
        return datapage(label, "lf_fields", title=title, bread=bread, label_cols=["old_label"], sorts=sorts)
    elif FAMILY_RE.fullmatch(label):
        title = f"Local field family data - {label}"
        bread = get_bread([(label, url_for_family(label)), ("DATA", " ")])
        return datapage(label, "lf_families", title=title, bread=bread)
    else:
        return abort(404, f"Invalid label {label}")

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
        bread=get_bread([("Dynamic statistics", " ")]),
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
    return render_template("single.html", kid='rcs.rigor.lf',
                           title=t, titletag=ttag, bread=bread,
                           learnmore=learnmore_list_remove('Reliability'))

@local_fields_page.route("/family/<label>")
def family_page(label):
    m = FAMILY_RE.fullmatch(label)
    if m is None:
        flash_error("Invalid label %s", label)
        return redirect(url_for(".index"))
    try:
        family = pAdicSlopeFamily(label)
    except NotImplementedError:
        flash_error("No famly with label %s in the database", label)
        return redirect(url_for(".index"))
    info = to_dict(request.args, search_array=FamilySearchArray(family), family_label=label, family=family, stats=LFStats())
    p, n = family.p, family.n
    if family.n0 == 1:
        info['bread'] = get_bread([("Families", url_for(".index", search_type="Families")),
                                   (str(p), url_for(".index", search_type="Families", p=p)),
                                   (str(family.n), url_for(".index", search_type="Families", p=p, n=n)),
                                   (label, "")])
    else:
        info['bread'] = get_bread([("Families", url_for(".index", search_type="Families", relative=1)),
                                   (family.base, url_for(".index", search_type="Families", relative=1, base=family.base)),
                                   (str(family.n), url_for(".index", search_type="Families", relative=1, base=family.base, n=n)),
                                   (label, "")])
    info['title'] = f"$p$-adic family {label}"
    info['titletag'] = f"p-adic family {label}"
    info['show_count'] = True
    info['properties'] = [
        ('Label', label),
        ('Base', f'<a href="{url_for(".by_label", label=family.base)}">{family.base}</a>'), # it would be nice to pretty print the base
        ('Degree', rf'\({n}\)'),
        ('e', rf'\({family.e}\)'),
        ('f', rf'\({family.f}\)'),
        ('c', rf'\({family.c}\)'),
    ]
    info['downloads'] = [('Underlying data', url_for('.lf_data', label=label))]
    if family.n0 == 1:
        info['friends'] = [('Relative constituents', url_for(".index", relative=1, search_type="Families", label_absolute=family.label))]
    else:
        info['friends'] = [('Absolute family', url_for(".family_page", label=family.label_absolute))]
    info['latex_content'] = latex_content
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
    friends=lambda:None,
    downloads=lambda:None,
)
def render_family(info, query):
    family = info["family"]
    query["family"] = family.label_absolute
    if family.n0 > 1:
        query["subfield"] = {"$contains": family.oldbase}
    #query["p"] = family.p
    #query["visible"] = str(family.artin_slopes)
    #query["f"] = 1 # TODO: Update to allow for tame extensions
    #query["e"] = family.n

    parse_galgrp(info,query,'gal',qfield=('galois_label','n'))
    parse_rats(info,query,'topslope',qfield='top_slope',name='Top Artin slope', process=ratproc)
    parse_newton_polygon(info,query,"slopes", qfield="slopes_tmp", mode=info.get('slopes_quantifier'))
    parse_newton_polygon(info,query,"ind_of_insep", qfield="ind_of_insep_tmp", mode=info.get('insep_quantifier'), reversed=True)
    parse_bracketed_posints(info,query,"associated_inertia")
    parse_bracketed_posints(info,query,"jump_set")
    if 'one_per' in info and info['one_per'] == 'packet':
        query["__one_per__"] = "packet"
    parse_noop(info,query,"hidden")

def common_family_parse(info, query):
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
    parse_regex_restricted(info,query,'base',regex=NEW_LF_RE,errknowl='lf.field.label',errtitle='label')
    parse_noop(info,query,'label_absolute',name='Absolute label') # TODO: Add a regex here
    parse_floats(info,query,'mass_relative',name='Mass', qfield='mass_relative')
    parse_floats(info,query,'mass_absolute',name='Mass', qfield='mass_absolute')
    parse_floats(info,query,'mass_found',name='Mass found')
    parse_ints(info,query,'ambiguity',name='Ambiguity')
    parse_ints(info,query,'field_count',name='Field count')
    parse_ints(info,query,'wild_segments',name='Wild segments')
    #parse_newton_polygon(info,query,"visible", qfield="visible_tmp", mode=info.get('visible_quantifier'))
    parse_herbrand(info,query)

@search_wrap(
    table=db.lf_families,
    columns=families_columns,
    title='Absolute $p$-adic families search results',
    titletag=lambda:'p-adic families search results',
    err_title='p-adic families search input error',
    learnmore=learnmore_list,
    bread=lambda:get_bread([("Families", "")]),
    postprocess=families_postprocess,
    url_for_label=url_for_family,
)
def families_search(info, query):
    if "relative" in info:
        query["__title__"] = "Relative $p$-adic families search results"
    else:
        query["n0"] = 1
    common_family_parse(info, query)

def common_boxes():
    degree = TextBox(
        name='n',
        label='Degree',
        short_label='Degree $n$',
        knowl='lf.degree',
        example='6',
        example_span='6, or a range like 3..5')
    qp = TextBox(
        name='p',
        label=r'Residue field characteristic',
        short_label='Residue characteristic $p$',
        knowl='lf.residue_field',
        example='3',
        example_span='3, or a range like 3..7')
    c = TextBox(
        name='c',
        label='Discriminant exponent',
        short_label='Discriminant exponent $c$',
        knowl='lf.discriminant_exponent',
        example='8',
        example_span='8, or a range like 2..6')
    e = TextBox(
        name='e',
        label='Ramification index',
        short_label='Ramification index $e$',
        knowl='lf.ramification_index',
        example='3',
        example_span='3, or a range like 2..6')
    f = TextBox(
        name='f',
        label='Residue field degree',
        short_label='Residue field degree $f$',
        knowl='lf.residue_field_degree',
        example='3',
        example_span='3, or a range like 2..6')
    topslope = TextBox(
        name='topslope',
        label='Top Artin slope',
        knowl='lf.top_slope',
        example='4/3',
        example_span='4/3, or a range like 3..5')
    slopes_quantifier = SubsetBox(
        name="slopes_quantifier",
    )
    slopes = TextBoxWithSelect(
        name='slopes',
        label='Galois Artin slopes',
        short_label='Galois Artin',
        knowl='lf.hidden_slopes',
        select_box=slopes_quantifier,
        example='[2,2,3]',
        example_span='[2,2,3] or [3,7/2,4]')
    visible_quantifier = SubsetBox(
        name="visible_quantifier",
    )
    visible = TextBoxWithSelect(
        name='visible',
        label='Visible Artin slopes',
        short_label='Visible Artin',
        knowl='lf.slopes',
        select_box=visible_quantifier,
        example='[2,2,3]',
        example_span='[2,2,3] or [2,3,17/4]')
    insep_quantifier = SubsetBox(
        name="insep_quantifier",
    )
    ind_insep = TextBoxWithSelect(
        name='ind_of_insep',
        label='Indices of insep.',
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
        example_span='e.g. 8.3, C5 or 7T2')
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
        short_label='Galois unram. degree $u$',
        knowl='lf.unramified_degree',
        example='3',
        example_span='3, or a range like 1..4'
    )
    t = TextBox(
        name='t',
        label='Galois tame degree',
        short_label='Galois tame degree $t$',
        knowl='lf.tame_degree',
        example='2',
        example_span='2, or a range like 2..3'
    )
    inertia = TextBox(
        name='inertia_gap',
        label='Inertia subgroup',
        knowl='lf.inertia_group_search',
        example='3.1',
        example_span='8.3, C5 or 7T2',
    )
    wild = TextBox(
        name='wild_gap',
        label='Wild inertia subgroup',
        knowl='lf.wild_inertia_group_search',
        example='4.1',
        example_span='8.3, C5 or 7T2',
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
    hidden = SneakyTextBox(
        name="hidden",
        label="Hidden content",
        knowl="lf.slopes")
    return degree, qp, c, e, f, topslope, slopes, visible, ind_insep, associated_inertia, jump_set, gal, aut, u, t, inertia, wild, family, packet, hidden

class FamilySearchArray(EmbeddedSearchArray):
    sorts = [
        ("", "Label", ['ctr_subfamily', 'ctr']),
        ("gal", "Galois group", ['gal', 'ctr_subfamily', 'ctr']),
        ("s", "top slope", ['top_slope', 'ctr_subfamily', 'ctr']),
        ("ind_of_insep", "Index of insep", ['ind_of_insep', 'ctr_subfamily', 'ctr']),
    ]
    def __init__(self, fam):
        degree, qp, c, e, f, topslope, slopes, visible, ind_insep, associated_inertia, jump_set, gal, aut, u, t, inertia, wild, family, packet, hidden = common_boxes()
        if fam.packet_count is None:
            self.refine_array = [[gal, slopes, ind_insep, hidden], [associated_inertia, jump_set]]
        else:
            one_per = SelectBox(
                name="one_per",
                label="Fields per packet",
                knowl="lf.packet",
                options=[("", "all"),
                         ("packet", "one")])
            self.refine_array = [[gal, slopes, ind_insep, hidden], [associated_inertia, jump_set, one_per]]

class FamiliesSearchArray(SearchArray):
    def __init__(self, relative=False):
        #degree, qp, c, e, f, topslope, slopes, visible, ind_insep, associated_inertia, jump_set, gal, aut, u, t, inertia, wild, family, packet = common_boxes()
        degree = TextBox(
            name='n',
            label='Rel. degree $n$' if relative else 'Degree $n$',
            knowl='lf.degree',
            example='6',
            example_span='6, or a range like 3..5')
        qp = TextBox(
            name='p',
            label=r'Residue characteristic $p$',
            knowl='lf.residue_field',
            example='3',
            example_span='3, or a range like 3..7')
        c = TextBox(
            name='c',
            label='Rel. disc. exponent $c$' if relative else 'Discriminant exponent $c$',
            knowl='lf.discriminant_exponent',
            example='8',
            example_span='8, or a range like 2..6')
        e = TextBox(
            name='e',
            label='Rel. ram. index $e$' if relative else 'Ramification index $e$',
            knowl='lf.ramification_index',
            example='3',
            example_span='3, or a range like 2..6')
        f = TextBox(
            name='f',
            label='Rel. res. field degree $f$' if relative else 'Residue field degree $f$',
            knowl='lf.residue_field_degree',
            example='3',
            example_span='3, or a range like 2..6')
        n0 = TextBox(
            name='n0',
            label='Base degree $n_0$',
            knowl='lf.degree',
            example='6',
            example_span='6, or a range like 3..5')
        c0 = TextBox(
            name='c0',
            label='Base disc. exponent $c_0$',
            knowl='lf.discriminant_exponent',
            example='8',
            example_span='8, or a range like 2..6')
        e0 = TextBox(
            name='e0',
            label='Base ram. index $e_0$',
            knowl='lf.ramification_index',
            example='3',
            example_span='3, or a range like 2..6')
        f0 = TextBox(
            name='f0',
            label='Base res. field degree $f_0$',
            knowl='lf.residue_field_degree',
            example='3',
            example_span='3, or a range like 2..6')
        n_absolute = TextBox(
            name='n_absolute',
            label=r'Abs. degree $n_{\mathrm{abs}}$',
            knowl='lf.degree',
            example='6',
            example_span='6, or a range like 3..5')
        c_absolute = TextBox(
            name='c_absolute',
            label=r'Abs. disc. exponent $c_{\mathrm{abs}}$',
            knowl='lf.discriminant_exponent',
            example='8',
            example_span='8, or a range like 2..6')
        e_absolute = TextBox(
            name='e_absolute',
            label=r'Abs. ram. index $e_{\mathrm{abs}}$',
            knowl='lf.ramification_index',
            example='3',
            example_span='3, or a range like 2..6')
        f_absolute = TextBox(
            name='f_absolute',
            label=r'Abs. res. field degree $f_{\mathrm{abs}}$',
            knowl='lf.residue_field_degree',
            example='3',
            example_span='3, or a range like 2..6')
        #w = TextBox(
        #    name='w',
        #    label='Wild ramification exponent $w$',
        #    knowl='lf.ramification_index',
        #    example='3',
        #    example_span='3, or a range like 2..6')
        base = TextBox(
            name='base',
            label='Base',
            knowl='lf.family_base',
            example='2.2.1.0a1.1')
        mass_relative = TextBox(
            name='mass_relative',
            label='Mass',
            knowl='lf.family_mass',
            example='255',
            example_span='9/2, or a range like 1-10')
        mass_absolute = TextBox(
            name='mass_absolute',
            label='Absolute mass',
            knowl='lf.family_mass',
            example='255/8',
            example_span='9/2, or a range like 1-10')
        #mass_found = TextBox(
        #    name='mass_found',
        #    label='Mass found',
        #    knowl='lf.family_mass',
        #    example='0.5-',
        #    example_span='0, or a range like 0.1-0.4')
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
        label_absolute = SneakyTextBox(
            name='label_absolute',
            label='Absolute label',
            knowl='lf.family_label',
            example='2.1.4.6a')
        herbrand = TextBox(
            name='herbrand',
            label='Herbrand invariant',
            knowl='lf.herbrand_input',
            example='[1/3,1/3]')
        if relative:
            relbox = HiddenBox("relative", "")
            self.refine_array = [[qp, degree, e, f, c],
                                 [base, n0, e0, f0, c0],
                                 [herbrand, n_absolute, e_absolute, f_absolute, c_absolute],
                                 #[visible, slopes, rams, means, slope_multiplicities],
                                 [mass_relative, mass_absolute, ambiguity, field_count, wild_segments, relbox],
                                 [label_absolute]]
            self.sorts = [
                ("", "base", ['p', 'n0', 'e0', 'c0', 'ctr0_family', 'ctr0_subfamily', 'ctr0', 'n', 'e', 'c', 'ctr']),
                ("c", "discriminant exponent", ['c', 'p', 'n', 'e', 'n0', 'e0', 'c0', 'ctr0_family', 'ctr0_subfamily', 'ctr0', 'ctr']),
                ("top_slope", "top slope", ['top_slope', 'slopes', 'visible', 'p', 'n0', 'e0', 'c0', 'ctr0_family', 'ctr0_subfamily', 'ctr0', 'n', 'e', 'c', 'ctr']),
                ("ambiguity", "ambiguity", ['ambiguity', 'p', 'n0', 'e0', 'c0', 'ctr0_family', 'ctr0_subfamily', 'ctr0', 'n', 'e', 'c', 'ctr']),
                ("field_count", "num fields", ['field_count', 'p', 'n0', 'e0', 'c0', 'ctr0_family', 'ctr0_subfamily', 'ctr0', 'n', 'e', 'c', 'ctr']),
                ("mass", "mass", ['mass_relative', 'p', 'n0', 'e0', 'c0', 'ctr0_family', 'ctr0_subfamily', 'ctr0', 'n', 'e', 'c', 'ctr']),
                #("mass_found", "mass found", ['mass_found', 'mass_relative', 'p', 'n0', 'e0', 'c0', 'n', 'e', 'c', 'ctr']),
            ]
        else:
            self.refine_array = [[qp, degree, e, f, c],
                                 [mass_relative, ambiguity, field_count, wild_segments, herbrand]]
            self.sorts = [
                ("", "label", ['p', 'n', 'e', 'c', 'ctr']),
                ("c", "discriminant exponent", ['c', 'p', 'n', 'e', 'ctr']),
                ("top_slope", "top slope", ['top_slope', 'slopes', 'visible', 'p', 'n', 'e', 'c', 'ctr']),
                ("ambiguity", "ambiguity", ['p', 'n', 'ambiguity', 'e', 'c', 'ctr']),
                ("field_count", "num fields", ['p', 'n', 'field_count', 'e', 'c', 'ctr']),
                ("mass", "mass", ['mass_relative', 'p', 'n', 'e', 'c', 'ctr']),
                #("mass_found", "mass found", ['mass_found', 'mass_relative', 'p', 'n', 'e', 'c', 'ctr']),
            ]

    def search_types(self, info):
        return self._search_again(info, [
            ('Families', 'List of families'),
            ('FamilyCounts', 'Counts table'),
            ('RandomFamily', 'Random family')])

    def _buttons(self, info):
        if self._st(info) == "FamilyCounts":
            return []
        return super()._buttons(info)

class LFSearchArray(SearchArray):
    noun = "field"

    sorts = [("", "prime", ['p', 'n', 'e', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("n", "degree", ['n', 'e', 'p', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("c", "discriminant exponent", ['c', 'p', 'n', 'e', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("e", "ramification index", ['n', 'e', 'p', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("f", "residue degree", ['f', 'n', 'p', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("gal", "Galois group", ['n', 'gal', 'p', 'e', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("u", "Galois unramified degree", ['u', 'f', 'n', 'p', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("t", "Galois tame degree", ['t', 'e', 'n', 'p', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("s", "top slope", ['top_slope', 'p', 'n', 'e', 'c', 'ctr_family', 'ctr_subfamily', 'ctr']),
             ("jump", "jump set", ['jump_set', 'p', 'n', 'e', 'c', 'ctr_family', 'ctr_subfamily', 'ctr'])]
    jump_example = "2.1.4.6a2.1"
    jump_egspan = "e.g. 2.1.4.6a2.1"
    jump_knowl = "lf.search_input"
    jump_prompt = "Label"
    null_column_explanations = {
        'packet': False, # If a packet is stored, it's complete since we don't record packets unless all hidden info known for that subfamily
    }

    def __init__(self):
        degree, qp, c, e, f, topslope, slopes, visible, ind_insep, associated_inertia, jump_set, gal, aut, u, t, inertia, wild, family, packet, hidden = common_boxes()
        results = CountBox()

        self.browse_array = [[degree, qp], [e, f], [c, topslope], [u, t],
                             [slopes, visible], [ind_insep, associated_inertia],
                             [jump_set, aut], [gal, inertia], [wild], [results]]
        self.refine_array = [[degree, qp, c, gal],
                             [e, f, t, u],
                             [aut, inertia, ind_insep, associated_inertia, jump_set],
                             [topslope, slopes, visible, wild],
                             [family, packet, hidden]]

    def search_types(self, info):
        return self._search_again(info, [
            ('List', 'List of fields'),
            ('Counts', 'Counts table'),
            ('Random', 'Random field')])

    def _buttons(self, info):
        if self._st(info) == "Counts":
            return []
        return super()._buttons(info)

def ramdisp(p):
    return {'cols': ['n', 'e'],
            'constraint': {'p': p, 'n': {'$lte': 23}},
            'top_title':[('degree', 'lf.degree'),
                         ('and', None),
                         ('ramification index', 'lf.ramification_index'),
                         ('for %s-adic fields' % p, None)],
            'totaler': totaler(col_counts=False),
            'proportioner': proportioners.per_row_total}

def discdisp(p):
    return {'cols': ['n', 'c'],
            'constraint': {'p': p, 'n': {'$lte': 23}},
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
                     'c': 'discriminant exponent',
                     'hidden': 'hidden slopes'}
    sort_keys = {'galois_label': galdata}
    formatters = {
        'galois_label': galformatter,
        'hidden': latex_content,
    }
    query_formatters = {
        'galois_label': (lambda gal: r'gal=%s' % (galunformatter(gal))),
        'hidden': (lambda hid: r'hidden=%s' % (content_unformatter(hid))),
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
        galdisp(2, 16),
        galdisp(2, 18),
        galdisp(2, 20),
        galdisp(2, 22),
        galdisp(3, 6),
        galdisp(3, 9),
        galdisp(3, 12),
        galdisp(3, 15),
        galdisp(3, 18),
        galdisp(3, 21),
        galdisp(5, 10),
        galdisp(5, 15),
        galdisp(5, 20),
        galdisp(7, 14),
        galdisp(7, 21),
        galdisp(11, 22),
    ]

    def __init__(self):
        self.numfields = db.lf_fields.count()
        self.num_abs_families = db.lf_families.count({"n0":1})
        self.num_rel_families = db.lf_families.count({"n0":{"$gt": 1}})

    @staticmethod
    def dynamic_parse(info, query):
        from .main import common_parse
        common_parse(info, query)

    dynamic_parent_page = "padic-refine-search.html"
    dynamic_cols = ["galois_label", "slopes"]

    @property
    def short_summary(self):
        return 'The database currently contains %s %s, %s absolute %s, and %s relative families.  Here are some <a href="%s">further statistics</a>.' % (
            comma(self.numfields),
            display_knowl("lf.padic_field", r"$p$-adic fields"),
            comma(self.num_abs_families),
            display_knowl("lf.family_polynomial", "families"),
            comma(self.num_rel_families),
            url_for(".statistics"),
        )

    @property
    def summary(self):
        return r'The database currently contains %s %s, including all with $p < 200$ and %s $n < 24$.  It also contains all %s absolute %s with $p < 200$ and degree $n < 48$, as well as all %s relative families with $p < 200$, base degree $n_0 < 16$ and absolute degree $n_{\mathrm{absolute}} < 48$.' % (
            comma(self.numfields),
            display_knowl("lf.padic_field", r"$p$-adic fields"),
            display_knowl("lf.degree", "degree"),
            comma(self.num_abs_families),
            display_knowl("lf.family_polynomial", "families"),
            comma(self.num_rel_families),
        )

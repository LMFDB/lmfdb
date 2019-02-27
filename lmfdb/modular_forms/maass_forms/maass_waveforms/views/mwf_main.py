# -*- coding: utf-8 -*-
r"""

AUTHORS:

 Markus Fraczek <marekf@gmx.net> (2010)
 Fredrik Stroemberg (2011-)
 Stefan Lemurell (2014-)



 TODO:
 + show only 50 eigenvalues/coefficient pro page
 + improve search
    - show additional information in search results (group,weght,character)
    - restrict search when items are selected
 + extend database to include more informations (Artkin-Lenhe Eigenvalues)
 + implement checks on homepage of maass wave form
 + provide API (class) for users (like L-functions guys) of database


"""

import flask
from flask import render_template, url_for, request,  send_file
import StringIO
from lmfdb.modular_forms.maass_forms.maass_waveforms import MWF, mwf_logger, mwf
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.maass_forms_db import maass_db
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.mwf_utils import get_args_mwf, get_search_parameters
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.mwf_classes import WebMaassForm
from mwf_plot import paintSvgMaass
logger = mwf_logger
import json
from lmfdb.utils import rgbtohex, signtocolour

# this is a blueprint specific default for the tempate system.
# it identifies the body tag of the html website with class="wmf"
@mwf.context_processor
def body_class():
    return {'body_class': MWF}

met = ['GET', 'POST']
maxNumberOfResultsToShow = 500

@mwf.route("/", methods=met)
@mwf.route("/<int:level>/", methods=met)
@mwf.route("/<int:level>/<int:weight>/", methods=met)
@mwf.route("/<int:level>/<int:weight>/<int:character>/", methods=met)
@mwf.route("/<int:level>/<int:weight>/<int:character>/<float:r1>/", methods=met)
@mwf.route("/<int:level>/<int:weight>/<int:character>/<float:r1>/<float:r2>/", methods=met)
def render_maass_waveforms(level=0, weight=-1, character=-1, r1=0, r2=0, **kwds):
    info = get_args_mwf(level=level, weight=weight, character=character, r1=r1, r2=r2, **kwds)

    info["credit"] = ""
    info["learnmore"] = []
    mwf_logger.debug("args=%s" % request.args)
    mwf_logger.debug("method=%s" % request.method)
    mwf_logger.debug("req.form=%s" % request.form)
    mwf_logger.debug("info=%s" % info)
    mwf_logger.debug("level,weight,char={0},{1},{2}".format(level, weight, character))
    if info.get('maass_id', None) and info.get('db', None):
        return render_one_maass_waveform_wp(**info)
    if info['search'] or (info['browse'] and int(info['weight']) != 0):
        search = get_search_parameters(info)
        mwf_logger.debug("search=%s" % search)
        return render_search_results_wp(info, search)
    if info['browse']:
        mwf_logger.debug("browse info=%s" % info)
        return render_browse_all_eigenvalues(**info)

    info['cur_character'] = character
    if level > 0:
        info['maass_weight'] = maass_db.weights(int(level))
        info['cur_level'] = level

    if weight > -1:
        info['cur_weight'] = weight
        if level > 0:
            info['maass_character'] = maass_db.characters(int(level), float(weight))
    if character > - 1:
        info['cur_character'] = character

    if level > 0 or weight > -1 or character > -1:
        search = get_search_parameters(info)
        mwf_logger.debug("info=%s" % info)
        mwf_logger.debug("search=%s" % search)
        return render_search_results_wp(info, search)
    title = 'Maass Forms'
    info['list_of_levels'] = maass_db.levels()
    if info['list_of_levels']:
        info['max_level'] = max(info['list_of_levels'])
    else:
        info['max_level'] = 0
    mwf_logger.debug("info3=%s" % info)
    bread = [('Modular Forms', url_for('mf.modular_form_main_page')),
             ('Maass Forms', url_for('.render_maass_waveforms'))]
    info['bread'] = bread
    info['title'] = title
    maass_db.set_table()
    maass_db.table['ncols'] = 10
    info['DB'] = maass_db
    info['dbcount'] = maass_db.count()
    info['limit'] = maxNumberOfResultsToShow
    return render_template("mwf_navigate.html", **info)

@mwf.route("/BrowseGraph/<min_level>/<max_level>/<min_R>/<max_R>/")
def render_maass_browse_graph(min_level, max_level, min_R, max_R):
    r"""
    Render a page with a graph with clickable dots for all
    with min_R <= R <= max_R and levels in the similar range.
    """
    info = {}
    info['contents'] = [paintSvgMaass(min_level, max_level, min_R, max_R)]
    info['min_level'] = min_level
    info['max_level'] = max_level
    info['min_R'] = min_R
    info['max_R'] = max_R
    info['coloreven'] = rgbtohex(signtocolour(1))
    info['colorodd'] = rgbtohex(signtocolour(-1))
    bread = [('Modular Forms', url_for('mf.modular_form_main_page')),
             ('Maass Waveforms', url_for('.render_maass_waveforms'))]
    info['bread'] = bread

    return render_template("mwf_browse_graph.html", title='Browsing Graph of Maass Forms', **info)


@mwf.route("/<maass_id>", methods=['GET', 'POST'])
def render_one_maass_waveform(maass_id, **kwds):
    r"""
    Render the webpage of one Maass waveform by calling
    render_one_maass_waveform_wp or generates a download
    in a format that is readable by python.
    """
    info = get_args_mwf(**kwds)
    info['maass_id'] = maass_id
    mwf_logger.debug("in_render_one_maass_form: info={0}".format(info))
    if (info.get('download', '') == 'coefficients'  or
        info.get('download', '') == 'all'):
        maass_id = info['maass_id']
        try:
            f = WebMaassForm(maass_id)
        except KeyError:
            flask.abort(404)
        filename = str(f._maass_id) + '.txt'
        if info.get('download', '') == 'coefficients':
            res = f.coeffs
        else:
            res = f.download_text()

        strIO = StringIO.StringIO()
        strIO.write(res)
        strIO.seek(0)
        try:
            return send_file(strIO,
                             attachment_filename=filename,
                             as_attachment=True,
                             add_etags=False)
        except IOError:
            info['error'] = "Could not send file!"

    else:
        return render_one_maass_waveform_wp(info)



def render_one_maass_waveform_wp(info, prec=9):
    r"""
    Render the webpage of one Maass waveform.

    The precision kwarg `prec` is passed to the coefficient table, and
    indicates to round to 0 when the difference is less than 1e-`prec`.
    """
    info["check"] = []
    maass_id = info['maass_id']
    mwf_logger.debug("id1={0}".format(maass_id))
    try:
        MF = WebMaassForm(maass_id)
    except KeyError:
        return flask.abort(404)
    info['MF'] = MF
    info['title'] = "Maass Form"
    info['bread'] = [('Modular Forms', url_for('mf.modular_form_main_page')),
                     ('Maass Waveforms', url_for('.render_maass_waveforms'))]
    if hasattr(MF,'level'):
        info['bread'].append(('Level {0}'.format(MF.level), url_for('.render_maass_waveforms', level=MF.level)))
        info['title'] += " on \(\Gamma_{0}( %s )\)" % info['MF'].level
        if hasattr(MF, 'R') and MF.R:
            info['title'] += " with \(R=%s\)" % info['MF'].R

    # make sure all the expected attributes of a WebMaassForm are actually present
    missing = [attr for attr in ['level', 'dim', 'num_coeff', 'R', 'character'] if not hasattr(MF, attr)]
    if missing:
        mwf_logger.critical("Unable to render Maass form {0}; required attributes {1} missing from database record.".format(maass_id,missing))
        info['explain'] = "Unable to render Maass form {0} because the following required attributes were missing from the database record:".format(maass_id) \
                      + "<ul>" + "".join(["<li>"+attr+"</li>" for attr in missing]) + "</ul>"
        return render_template("problem.html", **info)

    level = info['MF'].level
    dim = info['MF'].dim
    # numc = info['MF'].num_coeff # never used
    if info['MF'].has_plot(): # and level == 1: # Bara level = 1 har rätt format för tillfället //Lemurell
        info['plotlink'] = maass_db.get_maassform_plot_by_id(maass_id)
    # Create the link to the L-function (put in '/L' at the beginning and '/' before '?'
    Llink = "/L" + url_for('mwf.render_one_maass_waveform', maass_id=maass_id)  # + '/?db=' + info['db']
    if dim == 1:
        info["friends"] = [("L-function", Llink)]

    # Navigation to previous and next form
    next_form_id = info['MF'].next_maassform_id()
    if next_form_id:
        next_data = ('next', r"$f_{\text next}$", url_for('mwf.render_one_maass_waveform',
                                                                maass_id = next_form_id) )
    else:
        next_data = ('','','')
    prev_form_id = info['MF'].prev_maassform_id()
    if prev_form_id:
        prev_data = ('previous', r"$f_{\text prev}$", url_for('mwf.render_one_maass_waveform',
                                                                maass_id = prev_form_id) )
    else:
        prev_data = ('','','')

    info['navi'] = ( prev_data, next_data )

    info["downloads"] = [ ('All stored data of the form',
                           url_for('mwf.render_one_maass_waveform', maass_id=maass_id,
                                   download='all')),
                          ('All coefficients of the form',
                           url_for('mwf.render_one_maass_waveform', maass_id=maass_id,
                                   download='coefficients')) ]
    mwf_logger.debug("count={0}".format(maass_db.count()))
    ch = info['MF'].character
    s = "\( \chi_{" + str(level) + "}(" + str(ch) + ",\cdot) \)"
    # Q: Is it possible to get the knowls into the properties?
    # A: Not in a nice way and this is not done elsewhere in the LMFDB; the knowls should appear on labels in the template
    # knowls = {'level': 'mf.maass.mwf.level',
    #                   'weight': 'mf.maass.mwf.weight',
    #                   'char': 'mf.maass.mwf.character',
    #                   'R': 'mf.maass.mwf.eigenvalue',
    #                   'sym': 'mf.maass.mwf.symmetry',
    #                   'prec': 'mf.maass.mwf.precision',
    #                   'mult': 'mf.maass.mwf.dimension',
    #                   'ncoeff': 'mf.maass.mwf.ncoefficients',
    #                   'fricke': 'mf.maass.mwf.fricke',
    #                   'atkinlehner': 'mf.maass.mwf.atkinlehner'}
    properties = [('Level', [info['MF'].level]),
                  ('Symmetry', [info['MF'].even_odd()]),
                  ('Weight', [info['MF'].the_weight()]),
                  ('Character', [s]),
                  ('Multiplicity', [dim]),
                  ('Precision', [info['MF'].precision()]),
                  ('Fricke Eigenvalue', [info['MF'].fricke()]),
                  ('Atkin-Lehner Eigenvalues', [info['MF'].atkinlehner()]),
                  ]
    if dim > 1 and info['MF'].the_character() == "trivial":
        properties.append(("Possibly oldform", []))
    info['properties2'] = properties

    # The precision in set_table indicates which coefficients to set to zero.
    # For instance, if the imaginary part is less than the precision in
    # absolute value, then it is set to 0 in set_table.
    # The value 1e-9 is chosen arbitrarily, as recommended in issue #2076.
    info['MF'].set_table(prec=prec)
    cols = [{"aaSorting": "asc", "sWidth": "10%", "bSortable": "true", "bSearchable": "false",
             "sType": "numeric"}]
    negc = info['MF'].table.get('negc', 0)
    for j in range(dim):
        if not negc:
            col = {"bSortable": "false", "bSearchable": "true", "sClass": "alignLeft",
                   "fnRender": "text-align:left", "sType": "numeric"}
            cols.append(col)
        else:
            col1 = {"bSortable": "false", "bSearchable": "true", "sClass": "alignLeft",
                    "fnRender": "text-align:left", "sType": "numeric"}
            col2 = {"bSortable": "false", "bSearchable": "true", "sClass": "alignLeft",
                    "fnRender": "text-align:left", "sType": "numeric"}
            cols.append(col1)
            cols.append(col2)
    info['credit'] = info['MF'].contributor_name
    info['coeff_aoColumns'] = cols  # json.dumps(cols)
    mwf_logger.debug("col={0}".format(cols))
    return render_template("mwf_one_form.html", **info)


def render_search_results_wp(info, search):
    r"""
    Render the webpage with results of a search for Maass waveform.
    """
    mwf_logger.debug("in render_search_results. info1={0}".format(info))
    mwf_logger.debug("Search:{0}".format(search))
    if not isinstance(search, dict):
        search = {}
    limit = search.pop('limit', maxNumberOfResultsToShow)
    if limit > maxNumberOfResultsToShow:
        limit = maxNumberOfResultsToShow
    offset = search.pop('skip', 0)
    bread = [('Modular Forms', url_for('mf.modular_form_main_page')),
             ('Maass Forms', url_for('.render_maass_waveforms'))]
    info['bread'] = bread
    info['evs'] = evs_table2(search, limit=limit, offset=offset)
    mwf_logger.debug("in render_search_results. info2={0}".format(info))
    if int(info.get('weight', 0)) == 1:
        info['wtis1'] = "selected"
        info['wtis0'] = ""
    else:
        info['wtis0'] = "selected"
        info['wtis1'] = ""
    if info.get('browse', None) is not None:
        info['title'] = 'Browse Maassforms'
        if int(info.get('weight', -1)) in [0, 1]:
            info['title'] += ' of Weight {0}'.format(info['weight'])
            if info.get('level', 0) > 0:
                info['title'] += ' and Level {0}'.format(info['level'])
        elif int(info.get('Level', 0)) > 0:
            info['title'] += ' of Level {0}'.format(info['level'])
    else:
        info['title'] = 'Search Results'
    mwf_logger.debug("in render_search_results. info={0}".format(info))
    return render_template("mwf_display_search_result.html", **info)


def evs_table2(search, twodarray=False, limit=50, offset=0):
    r"""
    Returns an object containing the results of a search for Maass forms.
    """
    table = []
    nrows = 0
    fs = maass_db.get_Maass_forms(search, limit=limit, offset=offset)
    mwf_logger.debug("numrec:{0}".format(len(fs)))
    for f in fs:  # indices:
        row = {}
        R = f.get('Eigenvalue', None)
        N = f.get('Level', None)
        k = f.get('Weight', None)
        if R is None or N is None or k is None:
            continue
        row['R'] = R
        row['N'] = N
        if k == 0 or k == 1:
            row['k'] = int(k)
        else:
            row['k'] = k
        ##
        chi = f.get('Character', 0)
        ## Now get the COnrey number.
        ## First the character
        if k == 0:
            url = url_for('characters.render_Dirichletwebpage', modulus=N, number=chi)
            s = "<a href={0}>{1}</a>".format(url, chi)
            row['ch'] = s
        else:
            row['ch'] = "eta"
        st = f.get('Symmetry', -1)
        if st == 1:
            st = "odd"
        elif st == 0:
            st = "even"
        else:
            st = "n/a"
        row['symmetry'] = st
        er = f.get('Error', 0)
        if er > 0:
            er = "{0:1.0e}".format(float(er))
        else:
            er = "unknown"
        row['err'] = er
        dim = f.get('Dim', 0)
        if dim is None:
            dim = 1  # "undefined"
        row['dim'] = dim
        numc = f.get('Numc', 0)
        row['numc'] = numc
        cev = f.get('Cusp_evs', [])
        row['fricke'] = 'n/a'
        row['cuspevs'] = 'n/a'
        if row['k'] == 0 and isinstance(cev, list):
            if len(cev) > 1:
                fricke = cev[1]
                row['fricke'] = fricke
                s = '{0}'.format(cev[0])
                for j in range(1, len(cev)):
                    s += ",{0}".format(cev[j])
            elif len(cev) == 1:
                s = str(cev[0])
            elif len(cev) == 0:
                s = 'n/a'
            row['cuspevs'] = s

        url = url_for('mwf.render_one_maass_waveform', maass_id=f.get('maass_id'))
        row['url'] = url
        nrows += 1
        if twodarray:
            s = '<a href="{0}">{1}</a>'.format(row['url'], row['R'])
            rowr = [row['N'], row['k'], row['ch'], s,
                    row['symmetry'], row['err'], row['dim'], row['numc'],
                    row['fricke'], row['cuspevs']]
            table.append(rowr)
        else:
            # row=row.values()
            table.append(row)
    mwf_logger.debug("nrows:".format(nrows))
    evs = {'table': {}}
    evs['table']['data'] = table
    evs['table']['nrows'] = nrows
    evs['table']['ncols'] = 10
    evs['table']['colheads'] = []
    knowls = ['mf.maass.mwf.level', 'mf.maass.mwf.weight', 'mf.maass.mwf.character',
              'mf.maass.mwf.eigenvalue', 'mf.maass.mwf.symmetry',
              'mf.maass.mwf.precision', 'mf.maass.mwf.dimension',
              'mf.maass.mwf.ncoefficients', 'mf.maass.mwf.fricke',
              'mf.maass.mwf.atkinlehner']
    titles = ['Level', 'Weight', 'Char',
              'Eigenvalue', 'Symmetry',
              'Precision', 'Mult.',
              'Coeff.', 'Fricke', 'Atkin-Lehner']
    for i in range(10):
        evs['table']['colheads'].append((knowls[i], titles[i]))
    if 'limit' in search:
        search.pop('limit')
    if 'skip' in search:
        search.pop('skip')
    evs['totalrecords'] = maass_db.count(search)
    evs['totalrecords_filtered'] = len(fs)

    return evs



#---------- Nothing below this is actually used as far as I can see, but don't
#---------- want to delete yet.


@mwf.route("/Tables", methods=met)
def render_browse_all_eigenvalues(**kwds):
    info = get_args_mwf(**kwds)
    bread = [('Modular Forms', url_for('mf.modular_form_main_page')),('Maass Forms', url_for('.render_maass_waveforms'))]
    info['bread'] = bread
    info['colheads'] = ['Level', 'Weight', 'Char',
                        'Eigenvalue', 'Symmetry',
                        'Precision', 'Mult.',
                        'Coeff.', 'Fricke', 'Atkin-Lehner']

    if int(info.get('weight', 0)) == 1:
        print "weight1=", info.get('weight', 0)
        info['wtis1'] = "selected"
        info['wtis0'] = ""
    else:
        print "weight0=", info.get('weight', 0)
        info['wtis0'] = "selected"
        info['wtis1'] = ""
    return render_template("mwf_browse_all_eigenvalues.html", **info)


@mwf.route("/Tables_get", methods=met)
def get_table():
    limit = request.form.get('iDisplayLength', 10000)
    offset = request.form.get('iDisplayStart', 0)
    evs = evs_table2({}, twodarray=True, limit=limit, offset=offset)
    res = {
        "aoColumns": evs['table']['colheads'],
        "aaData": evs['table']['data'],
        "iTotalRecords": evs['totalrecords'],
        "iTotalDisplayRecords": evs['totalrecords_filtered']}
    res = json.dumps(res)
    mwf_logger.debug("table.nrows:{0}".format(evs['table']['nrows']))
    mwf_logger.debug("totalrecords:{0}".format(evs['totalrecords']))
    # print "res=",res
    return res

def conrey_character_name(N, chi):
    return "\chi_{" + str(N) + "}(" + str(chi.number()) + ",\cdot)"

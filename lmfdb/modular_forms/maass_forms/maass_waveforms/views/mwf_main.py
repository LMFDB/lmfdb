r"""

AUTHORS:

 Markus Fraczek <marekf@gmx.net> (2010)
 Fredrik Stroemberg (2011-)



 TODO:
 + show only 50 eigenvalues/coefficient pro page
 + improve search
    - show additional information in search results (group,weght,character)
    - restrict search when items are selected
 + extend database to include more informations (Artkin-Lenhe Eigenvalues)
 + implement checks on homepage of maass wave form
 + provide API (class) for users (like L-functions guys) of database


"""
import lmfdb.base
from lmfdb.base import app
from flask import render_template, url_for, request, redirect, make_response, send_file
from lmfdb.utils import url_character
import bson
import StringIO
import pymongo
from sage.all import is_odd, is_even, dumps
# mwf = flask.Blueprint('mwf', __name__, template_folder="templates",static_folder="static")
from lmfdb.modular_forms.maass_forms.maass_waveforms import MWF, mwf_logger, mwf
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.mwf_utils import *
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.mwf_classes import MaassFormTable, WebMaassForm
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.maass_forms_db import MaassDB
from mwf_upload_data import *
logger = mwf_logger
import json
try:
    from dirichlet_conrey import *
except:
    mwf_logger.critical("Could not import dirichlet_conrey!")


# this is a blueprint specific default for the tempate system.
# it identifies the body tag of the html website with class="wmf"
@mwf.context_processor
def body_class():
    return {'body_class': MWF}

met = ['GET', 'POST']


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
    # Not using wiki links for now
    # info["learnmore"].append(["Wiki","http://wiki.lmfdb.org/ModularForms/MaassForms"])
    # if we submit a search we search the database:
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
        # for key in search:
        #    info[key]=search[key]
        # return render_browse_all_eigenvalues(**info)
        return render_search_results_wp(info, search)
    if info['browse']:
        mwf_logger.debug("browse info=%s" % info)
        return render_browse_all_eigenvalues(**info)

    DB = connect_db()
    if not info['collection'] or info['collection'] == 'all':
        md = get_collections_info()
    info['cur_character'] = character
    # info["info1"] = MakeTitle(level,weight,character)
    if level > 0:
        info['maass_weight'] = DB.weights(int(level))
        info['cur_level'] = level

    if weight > -1:
        info['cur_weight'] = weight
        if level > 0:
            info['maass_character'] = DB.characters(int(level), float(weight))
    if character > - 1:
        info['cur_character'] = character

    if level > 0 or weight > -1 or character > -1:
        search = get_search_parameters(info)
        mwf_logger.debug("info=%s" % info)
        mwf_logger.debug("search=%s" % search)
        ### TODO
        # for key in search:
        #    info[key]=search[key]
        # return render_browse_all_eigenvalues(**info)
        return render_search_results_wp(info, search)
    title = 'Maass forms'
    info['list_of_levels'] = DB.levels()
    if info['list_of_levels']:
        info['max_level'] = max(info['list_of_levels'])
    else:
        info['max_level'] = 0
    mwf_logger.debug("info3=%s" % info)
    bread = [('Modular forms', url_for('mf.modular_form_main_page')),
             ('Maass forms', url_for('.render_maass_waveforms'))]
    info['bread'] = bread
    info['title'] = title
    DB.set_table()
    DB.table['ncols'] = 10
    info['DB'] = DB
    info['dbcount'] = DB.count()
    info['limit'] = 200
    return render_template("mwf_navigate.html", **info)


def render_maass_waveform_space(level, weight, character, **kwds):
    mwf_logger.debug("in_render_maass_form_space {0},{1},{2},{3}".format(level, weight, character, kwds))
    title = "Space of Maass forms"
    skip = int(kwds.get('skip', 0))
    limit = int(kwds.get('limit', 10))
    table = MWFTable(skip=skip, limit=limit)
    table.set_table({'level': level, 'weight': weight, 'character': character})
    info = {'table': table}
    return render_template("mwf_browse.html", info=info, title=title)


@mwf.route("/<maass_id>", methods=['GET', 'POST'])
def render_one_maass_waveform(maass_id, **kwds):
    info = get_args_mwf(**kwds)
    info['maass_id'] = bson.objectid.ObjectId(maass_id)
    mwf_logger.debug("in_render_one_maass_form: info={0}".format(info))
    if info.get('download', '') == 'coefficients1':
        DB = connect_db()
        fname = ""
        f = DB.get_maassform_by_id({"_id": info['maass_id']}, filename='True')
        dim = f.get('dim', 0)
        res = DB.get_coefficients({"_id": info['maass_id']}, filename='True')
        if isinstance(res, list):
            if isinstance(res, list):
                res = res[0][0]
            else:
                res = res[0]
        try:
            C, fname = res
        except:  # ValueError:
            C = res
            mwf_logger.debug("res={0}".format(res))
        filename = fname + '.txt'
        mwf_logger.debug("filename={0}".format(filename))
        s = dumps(C)
        strIO = StringIO.StringIO()
        strIO.write(s)
        strIO.seek(0)
        try:
            return send_file(strIO,
                             attachment_filename=filename,
                             as_attachment=True)
        except IOError:
            info['error'] = "Could not send file!"

    else:

        # mwf_logger.debug("id1={0}".format(id))
        return render_one_maass_waveform_wp(info)


def render_one_maass_waveform_wp(info):
    r"""
    Render the webpage of one Maass waveform.
    """
    info["check"] = []
    DB = connect_db()
    maass_id = info['maass_id']
    mwf_logger.debug("id1={0}".format(maass_id))
    info['MF'] = WebMaassForm(DB, maass_id)
    level = info['MF'].level
    dim = info['MF'].dim
    numc = info['MF'].num_coeff
    # Create the link to the L-function (put in '/L' at the beginning and '/' before '?'
    Llink = "/L" + url_for('mwf.render_one_maass_waveform', maass_id=maass_id)  # + '/?db=' + info['db']
    if dim == 1:
        info["friends"] = [("L-function", Llink)]
    bread = [('Maass waveforms', url_for('.render_maass_waveforms')),
             ('Of Level {0}'.format(level),
             url_for('.render_maass_waveforms', level=level))]

    info["downloads"] = []
    lenc = 20
    mwf_logger.debug("count={0}".format(DB.count()))
    ch = info['MF'].character
    s = "\( \chi_{" + str(level) + "}(" + str(ch) + ",\cdot) \)"
    # is it possible to get the knowls into the properties?
    knowls = knowls = {'level': 'mf.maass.mwf.level',
                       'weight': 'mf.maass.mwf.weight',
                       'char': 'mf.maass.mwf.character',
                       'R': 'mf.maass.mwf.eigenvalue',
                       'sym': 'mf.maass.mwf.symmetry',
                       'prec': 'mf.maass.mwf.precision',
                       'mult': 'mf.maass.mwf.dimension',
                       'ncoeff': 'mf.maass.mwf.ncoefficients',
                       'fricke': 'mf.maass.mwf.fricke',
                       'atkinlehner': 'mf.maass.mwf.atkinlehner'}
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
    info['title'] = "Maass forms on \(\Gamma_{0}( %s )\)" % (info['MF'].level)
    info['bread'] = bread
    info['properties2'] = properties

    info['MF'].set_table()
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
    # coeffurl=url_for('mwf.render_one_maass_waveform',maass_id=maass_id,download='coefficients')
    #    info['downloads'] = [('Coefficients', coeffurl) ]
    return render_template("mwf_one_form.html", **info)


def render_one_maass_waveform_wp_old(info):
    r"""
    Render the webpage of one Maass waveform.
    """
    info["check"] = []
    # info["check"].append(["Hecke relation",url_for('not_yet_implemented')])
    # info["check"].append(["Ramanujan-Petersson conjecture",url_for('not_yet_implemented')])
    maass_id = info['maass_id']
    # dbname=info['db']
    info["friends"] = []
    info["friends"].append(["L-function", "L/" + url_for('.render_one_maass_waveform', maass_id=maass_id)])
    info["downloads"] = []
    # info["downloads"].append(["Maass form data",url_for('not_yet_implemented')])
    bread = [('Maass forms', url_for('.render_maass_waveforms'))]
    properties = []
    data = get_maassform_by_id(maass_id)
    lenc = 20
    if 'error' not in data:
        [title, maass_info] = set_info_for_maass_form(data)
        info["maass_data"] = maass_info
        # rint "data=",info["maass_data"]
        numc = data['num_coeffs']
        mwf_logger.debug("numc={0}".format(numc))
        if(numc > 0):
            # if numc > 10:
                # largs = [{'maass_id':maass_id,'number':k} for k in range(10,numc,50)]
                # mwf_logger.debug("largs={0}".format(largs))
            info['coefficients'] = make_table_of_coefficients(maass_id, len, offest)  # ,largs,text='more')
            # else:
            #    info['coefficients']=make_table_of_coefficients(maass_id)
        else:
            info["maass_data"].append(['Coefficients', ''])

            s = 'No coefficients in the database for this form!'
            info['coefficients'] = s
        # info['list_spaces']=ajax_once(make_table_of_spaces_fixed_level,*largs,text='more',maass_id=maass_id)
        # info["coefficients"]=table_of_coefficients(
        info["credit"] = GetNameOfPerson(data['dbname'])
        level = data['Level']
        R = data['Eigenvalue']
        title = "Maass forms on \(\Gamma_{0}(%s)\) with R=%s" % (level, R)
        ## We see if there is a plot file associated to this waveform
        if 'plot' in data:
            mwf_logger.error("file={0}".format(data['plot']))
    else:
        # print "data=",data
        title = "Could not find this Maass form in the database!"
        info['error'] = data['error']

    bread = [('Maass forms', url_for('.render_maass_waveforms'))]
    return render_template("mwf_one_maass_form.html", info=info, title=title, bread=bread, properties=properties)


def render_search_results_wp(info, search):
    # res contains a lst of Maass waveforms
    mwf_logger.debug("in render_search_results. info1={0}".format(info))
    mwf_logger.debug("Search:{0}".format(search))
    evs = {'table': {}}
    if not isinstance(search, dict):
        search = {}
    if 'limit' not in search:
        search['limit'] = 200
    else:
        search['limit'] = min(200, search['limit'])
    if 'skip' not in search:
        search['skip'] = 0
    bread = [('Modular forms', url_for('mf.modular_form_main_page')),
             ('Maass forms', url_for('.render_maass_waveforms'))]
    info['bread'] = bread
    info['evs'] = evs_table2(search)
    mwf_logger.debug("in render_search_results. info2={0}".format(info))
    # print "wt=",info.get('weight')
    if int(info.get('weight', 0)) == 1:
        # print "weight1=",info.get('weight',0)
        info['wtis1'] = "selected"
        info['wtis0'] = ""
    else:
        # print "weight0=",info.get('weight',0)
        info['wtis0'] = "selected"
        info['wtis1'] = ""
    if info.get('browse', None) is not None:
        info['title'] = 'Browse Maassforms'
        if int(info.get('weight', -1)) in [0, 1]:
            info['title'] += ' of weight {0}'.format(info['weight'])
            if info.get('level', 0) > 0:
                info['title'] += ' and level {0}'.format(info['level'])
        elif int(info.get('Level', 0)) > 0:
            info['title'] += ' of level {0}'.format(info['level'])
    else:
        info['title'] = 'Search Results'
    mwf_logger.debug("in render_search_results. info={0}".format(info))
    return render_template("mwf_display_search_result.html", **info)


def render_browse_maass_waveforms(info, title):
    r"""
    Render a page for browsing Maass forms.
    """
    ## Paging parameters
    level_range = 6
    ev_range = 20
    if info['level_skip']:
        level_skip = info['level_skip'] * level_range
    else:
        level_skip = 0
    if info['ev_skip']:
        ev_skip = info['ev_skip'] * ev_range
    else:
        ev_skip = 0
    lrange = [level_skip + 1, level_skip + level_range]
    erange = [ev_skip + 1, ev_skip + ev_range]
    weight = info.get('weight', 0)
    TT = MWFTable(mwf_dbname, collection='all', skip=[0, 0], limit=[6, 10], keys=['Level',
                  'Eigenvalue'], weight=weight)
    TT.set_table()
    TT.get_metadata()
    info['table'] = TT
    # s = print_table_of_maass_waveforms(info['collection'],lrange=lrange,erange=erange)
    # info['table']=s
    bread = [('Modular forms', url_for('mf.modular_form_main_page')), ('Maass forms', url_for(
        '.render_maass_waveforms'))]
    return render_template("mwf_browse.html", info=info, title=title, bread=bread)


def render_maass_waveforms_for_one_group(level, **kwds):
    DB = connect_db()
    res = dict()
    info = dict()
    mwf_logger.debug("collections {0}".format(DB.collection_names()))
    for collection_name in DB.collection_names():
        res[collection_name] = list()
        C = pymongo.collection.Collection(DB, collection_name)
        mwf_logger.debug("Collection {0}".format(C))
        L = C.find({'Level': level, 'Weight': 0.0})
        for F in L:
            mwf_logger.debug("F: {0}".format(F))
            try:
                id = F['_id']
                R = F['Eigenvalue']
                k = F['Weight']
                res[collection_name].append((R, k, id))
            except:
                pass
        res[collection_name].sort()
    # now we have all maass waveforms for this group
    s = "<table><tr>"
    for name in res.keys():
        if(len(res[name]) == 0):
            continue
        s += "<td valign='top'>"
        s += "<table><thead>"
        s += " <tr><td valign='top'>Collection:" + name
        s += "     </td></tr></thead>"
        s += "<tbody>"
        for (R, k, id) in res[name]:
            url = url_for('mwf.render_one_maass_waveform', maass_id=str(id), db=name)
            s += "<tr><td><a href=\"%s\">%s</a></td></tr>" % (url, R)
        s += "</tbody>"
        s += "</table>"
        s += "</td>"
    s += "</tr></table>"
    # print "S=",s
    info['table_of_eigenvalues'] = s
    title = "Maass forms for \(\Gamma_{0}(" + str(level) + ")\)"
    bread = [('Maass forms', url_for('.render_maass_waveforms'))]
    return render_template("mwf_one_group.html", info=info, title=title)


@mwf.route("/Tables", methods=met)
def render_browse_all_eigenvalues(**kwds):
    info = get_args_mwf(**kwds)
    bread = [('Maass forms', url_for('.render_maass_waveforms'))]
    # info={}
    info['bread'] = bread
    # knowls=['mf.maass.mwf.level','mf.maass.mwf.weight',
    #        'mf.maass.mwf.character',
    #        'mf.maass.mwf.eigenvalue','mf.maass.mwf.symmetry',
    #        'mf.maass.mwf.precision','mf.maass.mwf.dimension',
    #        'mf.maass.mwf.ncoefficients','mf.maass.mwf.fricke',
    #        'mf.maass.mwf.atkinlehner']
    # How to incorporate KNOWLS from here?
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
    search = get_search_parameters({})
    mwf_logger.debug("args=%s" % request.args)
    mwf_logger.debug("method=%s" % request.method)
    # mwf_logger.debug("req.form=%s"%request.form)
    if isinstance(request.form, dict):
        for key in request.form.keys():
            mwf_logger.debug("{0}:{1}".format(key, request.form[key]))
    mwf_logger.debug("search:{0}".format(search))
    if not isinstance(search, dict):
        search = {}
    # if not search.has_key('limit'):
    search['limit'] = request.form.get('iDisplayLength', 10000)
    if 'skip' not in search:
        search['skip'] = 0
    search['skip'] = request.form.get('iDisplayStart', 0)
    evs = evs_table2(search, True)
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


def evs_table(search, twodarray=False):
    DB = connect_db()

    # indices  = DB.get_Maass_forms(search)
    indices = DB.find_Maass_form_id(search)
    table = []
    nrows = 0
    for fid in indices:
        f = WebMaassForm(DB, fid, get_coeffs=False)
        row = {}
        R = f.R
        N = f.level
        k = f.weight
        if R is None or N is None or k is None:
            continue
        row['R'] = R
        row['N'] = N
        if k == 0 or k == 1:
            row['k'] = int(k)
        else:
            row['k'] = k
        # j = f.get('Character',0)
        ## Now get the COnrey number.
        ## First the character
        if k == 0:
             # s+=url_character(type='Dirichlet',modulus=level,number=ch)
            row['ch'] = f.the_character()  # conrey_character_name(N,chi)
        else:
            row['ch'] = "eta"
        st = f.symmetry
        if st == 1:
            st = "odd"
        elif st == 0:
            st = "even"
        else:
            st = "n/a"
        row['symmetry'] = st
        er = f.error
        if er > 0:
            er = "{0:1.0e}".format(er)
        else:
            er = "unknown"
        row['err'] = er
        dim = f.dim
        if dim is None:
            dim = 1  # "undefined"
        row['dim'] = dim
        numc = f.num_coeff
        row['numc'] = numc
        cev = f.cusp_evs
        row['fricke'] = 'n/a'
        row['cuspevs'] = 'n/a'
        if row['k'] == 0 and isinstance(cev, list):
            if len(cev) > 1:
                fricke = cev[1]
                row['fricke'] = fricke
            row['cuspevs'] = cev
        url = url_for('mwf.render_one_maass_waveform', maass_id=f._maassid)
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
    evs['totalrecords'] = DB.count(search)

    return evs


def conrey_character_name(N, chi):
    return "\chi_{" + str(self._N) + "}(" + strIO(chi.number()) + ",\cdot)"


def evs_table2(search, twodarray=False):
    DB = connect_db()
    table = []
    nrows = 0
    fs = DB.get_Maass_forms(search)
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
        conrey = f.get('Conrey', 0)
        if conrey == 0:  # we need to change to conrey's notation
            chi = DB.getDircharConrey(N, chi)
        ## Now get the COnrey number.
        ## First the character
        if k == 0:
            url = url_character(type='Dirichlet', modulus=N, number=chi)
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
            er = "{0:1.0e}".format(er)
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

        url = url_for('mwf.render_one_maass_waveform', maass_id=f.get('_id'))
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
    evs['totalrecords'] = DB.count(search, filtered=False)
    evs['totalrecords_filtered'] = DB.count(search, filtered=True)

    return evs

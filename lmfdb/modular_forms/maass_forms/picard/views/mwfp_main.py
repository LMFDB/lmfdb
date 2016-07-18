# -*- coding: utf-8 -*-

from flask import render_template, url_for, request
from lmfdb.modular_forms.maass_forms.picard import mwfp, mwfp_logger, mwfp_dbname
from lmfdb.modular_forms.maass_forms.picard.backend.mwfp_classes import PicardFormTable, PicardDataTable
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.mwf_utils import connect_db

# see main mwfp blueprint for details

@mwfp.context_processor
def body_class():
    return {'body_class': 'mwfp'}


@mwfp.route("/", methods=['GET', 'POST'])
def render_picard_maass_forms():
    return render_picard_test()
    htp = connect_db('HTPicard').picard  # base.getDBConnection().HTPicard.picard
    docid = request.args.get('id', None)
    test = request.args.get('test', None)
    if test:
        return render_picard_test()
    if docid is not None:
        return render_picard_maass_forms_get_one(docid)
    ds = [(_['_id'], _['ev']) for _ in htp.find({}, ['ev'], sort=[('ev', 1)])]
    data = None
    # TT= MaassformsPicardDisplay(mwfp_dbname,collection='all',skip=[0],limit=[10],keys=['Eigenvalue'])
    # TT.set_table_browsing()
    # TT.get_metadata()
    if docid:
        data = htp.find_one({'_id': docid})
    return render_template("maass_form_picard.html", title="Maass forms on \(\mathrm{PSL}(2,\mathbb{Z}[i])\)", data=data, id=docid, ds=ds)


@mwfp.route("/<docid>", methods=['GET', 'POST'])
def render_picard_maass_forms_get_one(docid):
    mwfp_logger.debug("Render one picard form!")
    PT = PicardFormTable(
        mwfp_dbname, collection='picard', skip=[0, 0], limit=[20, 20], keys=['coef'], docid=docid)
    PT.set_table(name='browsing')
    info = dict()
    title = "Maass form on \(\mathrm{PSL}(2,\mathbb{Z}[i])\)"
    bread = [('Modular forms', url_for('mf.modular_form_main_page'))]
    info['title'] = title
    info['bread'] = bread
    info['table'] = PT.table()
    info['nrows'] = PT.nrows()
    info['ncols'] = PT.ncols()
    info['col_heads'] = PT.col_heads()
    info['row_heads'] = PT.row_heads()
    info['ev'] = PT.prop('ev')
    info['sym'] = PT.prop('sym')
    info['prec'] = PT.prop('prec')
    # jl = app.jinja_loader
    # mwfp_logger.debug("Templates: {0}".format(jl.list_templates()))
    return render_template("mwfp_one_form.html", **info)


def render_picard_test():
    x = request.args.get('x', 0)
    # y = request.args.get('y', 0)
    mwfp_logger.debug("skip= {0}".format(x))
    PT = PicardDataTable(mwfp_dbname, collection='picard', skip=[x], limit=[10, 10], keys=['ev'])
    PT.set_table(name='browsing')
    info = dict()
    info['table'] = PT.table()
    info['nrows'] = PT.nrows()
    info['ncols'] = PT.ncols()
    info['title'] = "Maass forms on \(\mathrm{PSL}(2,\mathbb{Z}[i])\)"
    return render_template("mwfp_navigation.html", **info)

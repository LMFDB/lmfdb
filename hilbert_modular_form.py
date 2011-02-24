from flask import render_template, request

from base import app
import base

@app.route('/ModularForm/GL2/<field>/holomorphic/')
def render_hilbert_modular_form(field):
    args = request.args
    if len(args) == 0:
        info = { }
    else:
        info = dict(args)
    info['field_input'] = field

    db = base.getDBConnection().hmfs
    field_id_str = db.fields.find_one({'name':field})['id_str']
    info['field_id_str'] = field_id_str
    info['field_pretty'] = field_pretty(field)

    if len(args) == 0:
        info['count'] = db.modular_forms.find({'field':field_id_str}).count()
        return render_template("hilbert_modular_form_space.html", info = info)
    else:
        search_dict = {'field':field_id_str}

        if info.has_key('weight'):
            k = str(info['weight'][0])
            search_dict['weight'] = k
            info['weight'] = k

        if info.has_key('level_norm'):
            normNN = str(info['level_norm'][0])
            search_dict['level_norm'] = normNN
            info['level_norm'] = normNN

        if info.has_key('level_ideal'):
            NN = str(info['level_ideal'][0])
            search_dict['level_ideal'] = NN
            info['level_ideal'] = NN

        if info.has_key('label'):
            label = str(info['label'][0])
            search_dict['label'] = label
            info['label'] = label
        else:
            label = None

        mfs = db.modular_forms.find(search_dict)

        info['modular_forms'] = mfs
        info['count'] = mfs.count()

        if info['count'] == 1 or (info.has_key('weight') and info.has_key('level_norm') and info.has_key('level_ideal') and info.has_key('label')):
            return render_template("hilbert_modular_form.html", info = info)
        else:
            return render_template("hilbert_modular_form_space.html", info = info)

def field_pretty(field_str):
    if field_str[:5] == 'Qsqrt':
        disc = field_str[5:]
        return '\( {\mathbb Q}(\sqrt{' + str(disc) + '}) \)'
    else:
        return field_str

# -*- coding: utf-8 -*-
from lmfdb.utils.utilities import key_for_numerically_sort
#######################################################################
# Functions for interacting with web structure
#######################################################################

# TODO This needs to be able to handle any sort of object
# There should probably be a more relevant field
# in the database, instead of trying to extract this from a URL
def name_and_object_from_url(url, check_existence=False):
    # the import is here to avoid circular imports
    from lmfdb import db
    url_split = url.rstrip('/').lstrip('/').split("/")
    name = '??'
    obj_exists = False

    if url_split[0] == "EllipticCurve":
        # every EC instance was added from EC
        obj_exists = True
        if url_split[1] == 'Q':
            if len(url_split) == 4: # isogeny class
                # EllipticCurve/Q/341641/a
                label_isogeny_class = ".".join(url_split[-2:])
                if check_existence:
                    obj_exists = db.ec_curvedata.exists({"lmfdb_iso": label_isogeny_class})
            elif len(url_split) == 5: # curve
                # EllipticCurve/Q/48/a/6
                label_curve = ".".join(url_split[-3:-1]) + url_split[-1]
                if check_existence:
                    obj_exists = db.ec_curvedata.exists({"lmfdb_label": label_curve})
            else:
                raise NotImplementedError
        else:
            if len(url_split) == 4: # isogeny class
                # EllipticCurve/2.2.140.1/14.1/a
                field, cond, isog = url_split[-3:]
                label_isogeny_class =  "-".join([field, cond, isog])
                if check_existence:
                    obj_exists = db.ec_nfcurves.exists({"class_label": label_isogeny_class})
            elif len(url_split) == 5: # curve
                # EllipticCurve/2.0.4.1/1250.3/a/3
                field, cond, isog, ind = url_split[-4:]
                label_curve =  "-".join([field, cond, isog]) + ind
                if check_existence:
                    obj_exists = db.ec_nfcurves.exists({"label": label_curve})
        if len(url_split) == 4: # isogeny class
            #name = 'Isogeny class ' + label_isogeny_class
            name = 'Elliptic curve ' + label_isogeny_class
        elif len(url_split) == 5: # curve
            #name = 'Curve ' + label_curve
            name = 'Elliptic curve ' + label_curve

    elif url_split[0] == "Character":
        # Character/Dirichlet/19/8
        assert url_split[1] == "Dirichlet"
        name = r"Dirichlet character \(\chi_{%s} (%s, \cdot) \)" %  tuple(url_split[-2:])
        label = ".".join(url_split[-2:])
        obj_exists = True
        if check_existence:
            obj_exists = db.char_dir_values.exists({"label": label})

    elif url_split[0] == "Genus2Curve":
        obj_exists = True
        assert url_split[1] == 'Q'
        if len(url_split) == 4: # isog class
            # Genus2Curve/Q/310329/a
            label_isogeny_class = ".".join(url_split[-2:])
            if check_existence:
                obj_exists = db.g2c_curves.exists({"class": label_isogeny_class})
            #name = 'Isogeny class ' + label_isogeny_class
            name = 'Genus 2 curve ' + label_isogeny_class
        if len(url_split) == 6: # curve
            # Genus2Curve/Q/1728/b/442368/1
            label_curve = ".".join(url_split[-4:])
            if check_existence:
                obj_exists = db.g2c_curves.exists({"label": label_curve})
            #name = 'Curve ' + label_curve
            name = 'Genus 2 curve ' + label_curve


    elif url_split[0] == "ModularForm":
        if url_split[1] == 'GL2':
            if url_split[2] == 'Q' and url_split[3]  == 'holomorphic':
                if len(url_split) == 10:
                    # ModularForm/GL2/Q/holomorphic/24/2/f/a/11/2
                    newform_label = ".".join(url_split[-6:-2])
                    conrey_newform_label = ".".join(url_split[-6:])
                    name = 'Modular form ' + conrey_newform_label
                    obj_exists = True
                    if check_existence:
                        obj_exists = db.mf_newforms.label_exists(newform_label)
                elif len(url_split) == 8:
                    # ModularForm/GL2/Q/holomorphic/24/2/f/a
                    newform_label = ".".join(url_split[-4:])
                    name = 'Modular form ' + newform_label
                    obj_exists = True
                    if check_existence:
                        obj_exists = db.mf_newforms.label_exists(newform_label)

            elif url_split[2] == 'TotallyReal':
                # ModularForm/GL2/TotallyReal/2.2.140.1/holomorphic/2.2.140.1-14.1-a
                label = url_split[-1]
                name =  'Hilbert modular form ' + label
                obj_exists = True
                if check_existence:
                    obj_exists = db.hmf_forms.label_exists(label)

            elif url_split[2] ==  'ImaginaryQuadratic':
                # ModularForm/GL2/ImaginaryQuadratic/2.0.4.1/98.1/a
                label = '-'.join(url_split[-3:])
                name = 'Bianchi modular form ' + label
                obj_exists = 'CM' not in label
                if check_existence:
                    obj_exists = db.bmf_forms.label_exists(label)
    elif url_split[0] == "ArtinRepresentation":
        label = url_split[1]
        name =  'Artin representation ' + label
        obj_exists = True
        if check_existence:
            obj_exists = db.artin_reps.label_exists(label.split('c')[0])
    elif url_split[0] == "NumberField":
        from lmfdb.number_fields.web_number_field import field_pretty
        label = url_split[1]
        name = 'Number field ' + field_pretty(label)
        obj_exists = True
        if check_existence:
            obj_exists = db.number_fields.label_exists(label)
    elif url_split[0] == "SatoTateGroup":
        from lmfdb.sato_tate_groups.main import st_name
        name, label = st_name(url_split[1])
        if name is None:
            name = label
            obj_exists = False
        else:
            name = 'Sato Tate group $%s$' % name
            obj_exists = True
    else:
        # FIXME
        #print("unknown url", url)
        pass


    return name, obj_exists


def names_and_urls(instances, exclude={}):
    res = []
    names = set()
    urls = set()
    exclude = set(exclude)

    # remove duplicate urls
    for instance in instances:
        if not isinstance(instance, str):
            instance = instance['url']
        if instance not in exclude and '|' not in instance:
            urls.add(instance)

    for url in urls:
        name, obj_exists = name_and_object_from_url(url)
        if not name:
            name = ''
        if obj_exists:
            url = "/"+url
        else:
            # do not display unknown objects
            continue
            name = '(%s)' % (name)
            url = ""
        # avoid duplicates that might have arise from different instances
        if name not in names:
            res.append((name, url))
            names.add(name)
    # sort based on name + label
    res.sort(key=lambda x: key_for_numerically_sort(x[0]))
    return res

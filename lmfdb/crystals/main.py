# -*- coding: utf-8 -*-
# This Blueprint is about Crystals
# Author: Anne Schilling (lead), Mike Hansen, Harald Schilly

from flask import render_template, request, url_for, make_response, redirect
from lmfdb.crystals import crystals_page, logger


def get_bread(breads=[]):
    bc = [("Crystals", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc


def make_tableaux_crystal(crystal):
    from sage.all_cmdline import CrystalOfTableaux
    cartan, rank, weight = crystal.split("-")
    weight = weight.split(".")
    return CrystalOfTableaux([str(cartan), int(rank)], shape=tuple(map(int, weight)))


def make_path_crystal(crystal):
    from sage.all_cmdline import CrystalOfLSPaths
    cartan, rank, weight = crystal.split("-")
    weight = weight.split(".")
    return CrystalOfLSPaths([str(cartan), int(rank)], [int(w) for w in weight])


@crystals_page.route("/<crystal>", methods=["GET"])
def show(crystal):
    C = make_tableaux_crystal(crystal)
    bc = get_bread([(crystal, url_for('.show', crystal=crystal))])
    return render_template("crystals.html", crystal=C, crystal_string=crystal, bread=bc)


@crystals_page.route("/search")
def search():
    weight = request.args.get('weight', '')
    weight = weight.replace(',', '.')
    cartan_type = str(request.args.get('cartan_type', ''))
    rank = request.args.get('rank', '')
    logger.info("weight = %s" % weight)
    if not (cartan_type and rank and weight):
        return redirect(url_for('.index'), 301)
    crystal_string = "-".join([cartan_type, rank, weight])
    return redirect(url_for('.show', crystal=crystal_string), 301)


@crystals_page.route("/search_littelmann")
def search_littelmann():
    weight = request.args.get('weight', '')
    weight = weight.replace(',', '.')
    cartan_type = str(request.args.get('cartan_type', ''))
    logger.info("weight = %s" % weight)
    if not (cartan_type and weight):
        return redirect(url_for('.index'), 301)
    crystal_string = "-".join([cartan_type, str(2), weight])
    return redirect(url_for('.show_littelmann', crystal=crystal_string), 301)


@crystals_page.route("/<crystal>/image")
def crystal_image(crystal):
    C = make_tableaux_crystal(crystal)
    from sage.all import tmp_dir
    d = tmp_dir()

    import os
    filename = os.path.join(d, 'crystal.png')

    try:
        from sage.misc.latex import png
        png(C, filename, debug=True, pdflatex=True)

        image_data = open(filename, 'rb').read()
        response = make_response(image_data)
        response.headers['Content-Type'] = 'image/png'

        return response
    except IOError:
        return "internal error rendering graph", 500
    finally:
        # Get rid of the temporary directory
        import shutil
        shutil.rmtree(d)


@crystals_page.route("/<crystal>/littelmann")
def show_littelmann(crystal):
    C = make_path_crystal(crystal)
    max_i = str(max(C.index_set()))
    max_element = str(C.cardinality())
    bc = get_bread([(crystal, url_for('.show', crystal=crystal)),
                    ('Littelmann', url_for('.show_littelmann', crystal=crystal))])
    return render_template("littelmann-paths.html", title="Littelmann Paths",
                           crystal=crystal, C=C, max_element=max_element, max_i=max_i, bread=bc)


@crystals_page.route("/littelmann-image")
def littelmann_image():
    from sage.all_cmdline import vector, line

    def line_of_path(path):
        if path is None:
            result = []
        else:
            L = path.parent().weight.parent()
            v = vector(L.zero())
            result = [v]
            for d in path.value:
                v = v + vector(d)
                result.append(v)
        result = list(result)
        result = line(result)
        result.set_axes_range(-10, 10, -10, 10)
        return result

    crystal = request.args.get("crystal")
    C = make_path_crystal(crystal)
    element = int(request.args.get("element"))
    i = int(request.args.get("i"))
    l = int(request.args.get("l"))
    x = C[element]
    if l >= 0:
        y = x.f_string([i] * l)
    else:
        y = x.e_string([i] * -l)

    from lmfdb.utils import image_callback
    return image_callback(line_of_path(y))


@crystals_page.route("/littelmann-recenter/<crystal>")
def littelmann_recenter(crystal):
    C = make_path_crystal(crystal)
    element = int(request.args.get("element"))
    i = int(request.args.get("i"))
    l = int(request.args.get("l"))
    x = C[element]
    if l >= 0:
        y = x.f_string([i] * l)
    else:
        y = x.e_string([i] * -l)
    ret = str(C.rank(y))
    return 1 if ret == "NaN" else ret


@crystals_page.route("/")
def index():
    bread = get_bread()
    return render_template("crystals-index.html", title="Crystals", bread=bread)

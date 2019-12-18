# -*- coding: utf-8 -*-
import re
from flask import url_for

from lmfdb import db
from lmfdb.number_fields.web_number_field import (
    WebNumberField,
    nf_display_knowl,
    field_pretty,
)
from lmfdb.galois_groups.transitive_group import group_display_knowl

lmfdb_label_regex = re.compile(r"(\d+)\.(\d+)\.([a-z_]+)")

def split_label(lab):
    return lmfdb_label_regex.match(lab).groups()

def av_display_knowl(label):
    return '<a title = "[av.data]" knowl="av.fq.abvar.data" kwargs="label={0}">{1}</a>'.format(str(label), label)

def av_data(label):
    abvar = db.av_fq_isog.lookup(label)
    if abvar is None:
        return "This isogeny class is not in the database."
    inf = "<div>Dimension: " + str(abvar["g"]) + "<br />"
    if abvar["is_simple"]:
        nf = abvar["number_fields"][0]
        wnf = WebNumberField(nf)
        if not wnf.is_null():
            inf += (
                "Number field: "
                + nf_display_knowl(nf, name=field_pretty(nf))
                + "<br />"
            )
            gal = abvar["galois_groups"][0].split("T")
            inf += "Galois group: " + group_display_knowl(gal[0], gal[1]) + "<br />"
    inf += "$p$-rank: " + str(abvar["p_rank"]) + "</div>"
    inf += '<div align="right">'
    g, q, iso = split_label(label)
    url = url_for("abvarfq.abelian_varieties_by_gqi", g=g, q=q, iso=iso)
    inf += '<a href="%s">%s home page</a>' % (url, label)
    inf += "</div>"
    return inf

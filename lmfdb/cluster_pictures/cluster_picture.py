# -*- coding: utf-8 -*-

from flask import Markup

from lmfdb.app import app
from lmfdb.cluster_pictures.web_cluster_picture import (
    cp_knowl_guts)

# assert cp_logger

CP_credit = 'Alex Best, Raymond van Bommel'
Completename = 'Completeness of the data'
dnc = 'data not computed'


def cluster_picture_data(label):
    return Markup(cp_knowl_guts(label))


@app.context_processor
def ctx_cluster_pictures():
    return {'cluster_picture_data': cluster_picture_data}

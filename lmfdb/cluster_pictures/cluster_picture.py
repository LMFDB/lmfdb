# -*- coding: utf-8 -*-D

import ast
import os
import re
from six import BytesIO
import time

from flask import render_template, request, url_for, redirect, send_file, make_response, Markup

from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import (
    web_latex, to_dict, coeff_to_poly, pol_to_html, comma, format_percentage,
    flash_error, display_knowl, CountBox,
    SearchArray, TextBox, TextBoxNoEg, YesNoBox, SubsetNoExcludeBox, TextBoxWithSelect,
    clean_input, nf_string_to_label, parse_galgrp, parse_ints, parse_bool,
    parse_signed_ints, parse_primes, parse_bracketed_posints, parse_nf_string,
    parse_floats, parse_subfield, search_wrap)
from lmfdb.cluster_pictures.web_cluster_picture import (
    WebClusterPicture, cp_knowl_guts)

#assert cp_logger

CP_credit = 'Alex Best, Raymond van Bommel'
Completename = 'Completeness of the data'
dnc = 'data not computed'

def cluster_picture_data(label):
    return Markup(cp_knowl_guts(label))
    
@app.context_processor
def ctx_cluster_pictures():
    return {'cluster_picture_data': cluster_picture_data}

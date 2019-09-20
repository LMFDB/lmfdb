# -*- coding: utf-8 -*-

# make pyflakes happy, define interface for import *
__all__ = ['request', 'make_response', 'flash', 'url_for', 'render_template',
           'send_file', 'list_to_factored_poly_otherorder',
           'list_factored_to_factored_poly_otherorder',
           'key_for_numerically_sort', 'an_list', 'coeff_to_poly',
           'coeff_to_power_series', 'display_multiset', 'pair2complex',
           'round_CBF_to_half_int', 'str_to_CBF', 'to_dict', 'display_float',
           'display_complex', 'round_to_half_int', 'splitcoeff', 'comma',
           'format_percentage', 'signtocolour', 'rgbtohex', 'pol_to_html',
           'web_latex', 'web_latex_ideal_fact', 'web_latex_split_on',
           'web_latex_split_on_pm', 'web_latex_split_on_re', 'display_knowl',
           'teXify_pol', 'add_space_if_positive',
           'bigint_knowl', 'too_big', 'make_bigint', 'bigpoly_knowl',
           'factor_base_factor', 'factor_base_factorization_latex',
           'polyquo_knowl', 'web_latex_poly', 'list_to_latex_matrix',
           'code_snippet_knowl',
           'Pagination',
           'debug', 'flash_error', 'cached',
           'ajax_url',
           'image_callback', 'encode_plot',
           'KeyedDefaultDict', 'make_tuple', 'range_formatter',
           'parse_ints', 'parse_signed_ints', 'parse_floats', 'parse_rational',
           'parse_rats', 'parse_bracketed_posints', 'parse_bool',
           'parse_bool_unknown', 'parse_primes', 'parse_element_of',
           'parse_subset', 'parse_submultiset', 'parse_list',
           'parse_list_start', 'parse_string_start', 'parse_restricted',
           'parse_noop', 'parse_equality_constraints', 'parse_gap_id',
           'parse_galgrp', 'parse_nf_string', 'parse_nf_elt',
           'parse_container', 'parse_hmf_weight', 'parse_count',
           'parse_start', 'parse_ints_to_list_flash', 'integer_options',
           'nf_string_to_label', 'clean_input', 'prep_ranges',
           'search_wrap',
           'Downloader',
           'formatters', 'proportioners', 'totaler', 'StatsDisplay',
           'Configuration',
           'names_and_urls', 'name_and_object_from_url',
           'datetime_to_timestamp_in_ms', 'timestamp_in_ms_to_datetime',
           'reraise']

from flask import (request, make_response, flash, url_for,
                   render_template, send_file)

from .utilities import (
    list_to_factored_poly_otherorder,
    list_factored_to_factored_poly_otherorder,
    key_for_numerically_sort, an_list, coeff_to_poly, coeff_to_power_series,
    display_multiset, pair2complex, round_CBF_to_half_int, str_to_CBF,
    to_dict, display_float, display_complex, round_to_half_int,
    splitcoeff, comma, format_percentage, signtocolour, rgbtohex, pol_to_html,
    web_latex, web_latex_ideal_fact, web_latex_split_on, web_latex_split_on_pm,
    web_latex_split_on_re, display_knowl, bigint_knowl, too_big, make_bigint,
    teXify_pol, add_space_if_positive,
    bigpoly_knowl, factor_base_factor, factor_base_factorization_latex,
    polyquo_knowl, web_latex_poly, list_to_latex_matrix, code_snippet_knowl,
    Pagination,
    debug, flash_error, cached,
    ajax_url,  # try to eliminate?
    image_callback, encode_plot,
    KeyedDefaultDict, make_tuple, range_formatter,
    datetime_to_timestamp_in_ms, timestamp_in_ms_to_datetime)

from .search_parsing import (
    parse_ints, parse_signed_ints, parse_floats, parse_rational, parse_rats,
    parse_bracketed_posints, parse_bool, parse_bool_unknown, parse_primes,
    parse_element_of, parse_subset, parse_submultiset, parse_list,
    parse_list_start, parse_string_start, parse_restricted, parse_noop,
    parse_equality_constraints, parse_gap_id, parse_galgrp, parse_nf_string,
    parse_nf_elt, parse_container, parse_hmf_weight, parse_count, parse_start,
    parse_ints_to_list_flash, integer_options, nf_string_to_label,
    clean_input, prep_ranges)

from .search_wrapper import search_wrap
from .downloader import Downloader
from .display_stats import formatters, proportioners, totaler, StatsDisplay
from .config import Configuration
from .names_and_urls import names_and_urls, name_and_object_from_url
from .reraise import reraise

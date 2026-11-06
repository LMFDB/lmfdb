
"""
The utilities used throughout the LMFDB website.

Most of them come from lmfdb-utils (packages/lmfdb-utils), which other
websites can use too; they are re-exported here together with the ones
specific to the LMFDB, so that ``from lmfdb.utils import ...`` gives both.
"""

import sys as _sys
import importlib as _importlib

# The modules that moved to lmfdb-utils keep their old names, so that
# ``from lmfdb.utils.search_columns import LinkCol`` and the like go on
# working, in the LMFDB and in scripts using it.  The old name is the same
# module object, not a copy, so patching lmfdb.utils.search_columns.X in a
# test patches the code that runs.  (lmfdb.utils.search_parsing is only the
# generic parsers: the LMFDB's own are in lmfdb.utils.lmfdb_search_parsing.)
MOVED_TO_LMFDB_UTILS = [
    "color", "common_regex", "csrf", "datetime_utils", "display_stats",
    "downloader", "place_code", "random_wrap", "search_boxes",
    "search_columns", "search_parsing", "search_wrapper", "utilities",
    "web_display",
]
for _name in MOVED_TO_LMFDB_UTILS:
    _module = _importlib.import_module("lmfdb_utils." + _name)
    _sys.modules[__name__ + "." + _name] = _module
    globals()[_name] = _module
del _name, _module

# make pyflakes happy, define interface for import *
__all__ = ['request', 'make_response', 'flash', 'url_for', 'render_template',
           'send_file', 'list_to_factored_poly_otherorder', 'prop_int_pretty',
           'list_factored_to_factored_poly_otherorder', 'integer_squarefree_part', 'integer_is_squarefree',
           'key_for_numerically_sort', 'an_list', 'coeff_to_poly', 'coeff_to_poly_multi',
           'coeff_to_power_series', 'display_multiset', 'pair2complex',
           'round_CBF_to_half_int', 'str_to_CBF', 'to_dict', 'display_float',
           'display_complex', 'round_to_half_int', 'splitcoeff', 'comma',
           'format_percentage', 'signtocolour', 'rgbtohex',
           'web_latex', 'web_latex_factored_integer', 'web_latex_ideal_fact',
           'web_latex_split_on', 'web_latex_split_on_pm',
           'web_latex_split_on_re', 'sparse_cyclotomic_to_latex',
           'sparse_cyclotomic_to_mathml', 'integer_to_mathml',
           'display_knowl', 'teXify_pol', 'add_space_if_positive',
           'bigint_knowl', 'too_big', 'make_bigint', 'bigpoly_knowl',
           'factor_base_factor', 'factor_base_factorization_latex',
           'polyquo_knowl', 'list_to_latex_matrix',
           'code_snippet_knowl', 'integer_divisors', 'integer_prime_divisors',
           'Pagination', 'to_ordinal',
           'debug', 'flash_error', 'flash_warning', 'flash_info',
           'image_callback', 'encode_plot', 'graph_to_cytoscape_json', 'graph_to_svg',
           'make_graph', 'setup_isogeny_graph', 'GRAPH_LAYOUTS',
           'parse_ints', 'parse_posints', 'parse_signed_ints', 'parse_floats',
           'parse_mod1', 'parse_rational', 'parse_padicfields', 'parse_padicsubfields',
           'parse_rational_to_list', 'parse_inertia', 'parse_group_label_or_order',
           'parse_rats', 'parse_bracketed_posints', 'parse_bracketed_rats', 'parse_bool',
           'parse_bool_unknown', 'parse_primes', 'parse_element_of', 'parse_not_element_of',
           'parse_subset', 'parse_submultiset', 'parse_list', 'parse_kerpol_string',
           'parse_list_start', 'parse_string_start', 'parse_restricted', 'parse_regex_restricted',
           'parse_noop', 'parse_equality_constraints', 'parse_gap_id', 'parse_interval',
           'parse_galgrp', 'parse_nf_string', 'parse_subfield', 'parse_nf_elt', 'parse_nf_jinv',
           'parse_container', 'parse_hmf_weight', 'parse_count', 'parse_newton_polygon',
           'parse_start', 'parse_ints_to_list_flash', 'integer_options',
           'unparse_range',
           'nf_string_to_label', 'clean_input', 'prep_ranges',
           'search_wrap', 'count_wrap', 'embed_wrap', 'yield_wrap',
           'SearchArray', 'EmbeddedSearchArray', 'TextBox', 'TextBoxNoEg', 'TextBoxWithSelect', 'BasicSpacer',
           'SkipBox', 'CheckBox', 'CheckboxSpacer', 'DoubleSelectBox', 'HiddenBox',
           'SearchButton', 'SearchButtonWithSelect', 'RowSpacer',
           'SelectBox', 'YesNoBox', 'YesNoMaybeBox', 'ExcludeOnlyBox',
           'ParityBox', 'ParityMod', 'SubsetBox', 'SubsetNoExcludeBox', 'SelectBoxNoEg', 'CountBox',
           'SneakyTextBox', 'SneakySelectBox',
           'Downloader', 'WebObj', 'send_file_from_beta',
           'formatters', 'proportioners', 'totaler', 'StatsDisplay',
           'Configuration', 'plural_form', 'pluralize',
           'names_and_urls', 'name_and_object_from_url',
           'datetime_to_timestamp_in_ms', 'timestamp_in_ms_to_datetime',
           'TraceHash', 'TraceHashClass',
           'redirect_no_cache', 'letters2num', 'num2letters',
           'raw_typeset', 'raw_typeset_poly', 'raw_typeset_poly_factor',
           'raw_typeset_qexp', 'raw_typeset_int', 'compress_poly_Q',
           'input_string_to_poly', 'dispZmat', 'dispcyclomat',
           'compress_expression',
           'pos_int_and_factor', 'compress_polynomial', 'CodeSnippet']

from flask import (request, make_response, flash, url_for,
                   render_template, send_file)

from lmfdb_utils.utilities import (
    integer_divisors,
    integer_prime_divisors,
    integer_squarefree_part,
    integer_is_squarefree,
    Pagination,
    an_list,
    code_snippet_knowl,
    coeff_to_poly,
    coeff_to_poly_multi,
    coeff_to_power_series,
    comma,
    debug,
    display_complex,
    display_float,
    display_multiset,
    encode_plot,
    factor_base_factor,
    flash_error,
    flash_info,
    flash_warning,
    format_percentage,
    image_callback,
    key_for_numerically_sort,
    letters2num,
    list_factored_to_factored_poly_otherorder,
    list_to_factored_poly_otherorder,
    num2letters,
    pair2complex,
    prop_int_pretty,
    rgbtohex,
    round_CBF_to_half_int,
    round_to_half_int,
    signtocolour,
    splitcoeff,
    str_to_CBF,
    to_dict,
    WebObj,
    plural_form,
    pluralize,
)

from .graph_utils import (
    graph_to_cytoscape_json,
    graph_to_svg,
    make_graph,
    setup_isogeny_graph,
    GRAPH_LAYOUTS,
)

from lmfdb_utils.web_display import (
    add_space_if_positive,
    bigint_knowl,
    bigpoly_knowl,
    dispZmat,
    dispcyclomat,
    display_knowl,
    factor_base_factorization_latex,
    list_to_latex_matrix,
    make_bigint,
    polyquo_knowl,
    raw_typeset,
    raw_typeset_poly,
    compress_poly_Q,
    compress_polynomial,
    compress_expression,
    pos_int_and_factor,
    raw_typeset_poly_factor,
    raw_typeset_qexp,
    raw_typeset_int,
    sparse_cyclotomic_to_latex,
    sparse_cyclotomic_to_mathml,
    integer_to_mathml,
    teXify_pol,
    to_ordinal,
    too_big,
    web_latex,
    web_latex_factored_integer,
    web_latex_ideal_fact,
    web_latex_split_on,
    web_latex_split_on_pm,
    web_latex_split_on_re,
)

from lmfdb_utils.search_parsing import (
    parse_ints, parse_signed_ints, parse_posints, parse_floats, parse_mod1,
    parse_rational, parse_rational_to_list, parse_rats, parse_bracketed_posints,
    parse_bracketed_rats, parse_bool, parse_bool_unknown, parse_primes,
    parse_element_of, parse_not_element_of, parse_subset, parse_submultiset,
    parse_list, parse_list_start, parse_string_start, parse_restricted,
    parse_regex_restricted, parse_noop, parse_equality_constraints,
    parse_newton_polygon, parse_count, parse_start, parse_ints_to_list_flash,
    integer_options, parse_interval, unparse_range, clean_input, prep_ranges)
from .lmfdb_search_parsing import (
    parse_padicsubfields, parse_padicfields, parse_inertia, parse_kerpol_string,
    parse_group_label_or_order, parse_gap_id, parse_galgrp, parse_nf_string,
    parse_nf_elt, parse_nf_jinv, parse_container, parse_hmf_weight, nf_string_to_label,
    parse_subfield, input_string_to_poly)

from lmfdb_utils.search_wrapper import search_wrap, count_wrap, embed_wrap, yield_wrap
from lmfdb_utils.search_boxes import (
    SearchArray, EmbeddedSearchArray, TextBox, TextBoxNoEg, TextBoxWithSelect, BasicSpacer,
    SkipBox, CheckBox, CheckboxSpacer, DoubleSelectBox, HiddenBox,
    SelectBox, YesNoBox, YesNoMaybeBox, ExcludeOnlyBox,
    ParityBox, ParityMod, SubsetBox, SubsetNoExcludeBox, SelectBoxNoEg, CountBox,
    SneakyTextBox, SneakySelectBox,
    SearchButton, SearchButtonWithSelect, RowSpacer)
from lmfdb_utils.downloader import Downloader
from .beta import send_file_from_beta
from lmfdb_utils.display_stats import formatters, proportioners, totaler, StatsDisplay
from .config import Configuration
from .names_and_urls import names_and_urls, name_and_object_from_url
from .trace_hash import TraceHash, TraceHashClass
from lmfdb_utils.random_wrap import redirect_no_cache
from lmfdb_utils.place_code import CodeSnippet
from lmfdb_utils.datetime_utils import datetime_to_timestamp_in_ms, timestamp_in_ms_to_datetime

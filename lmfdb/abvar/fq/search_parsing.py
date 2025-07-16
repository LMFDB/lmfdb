from lmfdb.utils.search_parsing import (
    search_parser,
    nf_string_to_label,
    _parse_subset,
)


@search_parser  # see SearchParser.__call__ for actual arguments when calling
def parse_nf_string(inp, query, qfield):
    fields = [nf_string_to_label(field) for field in inp.split(",")]
    _parse_subset(fields, query, qfield, mode=None, radical=None, product=None, cardinality=None)


@search_parser  # (clean_info=True, default_field='galois_group', default_name='Galois group', default_qfield='galois') # see SearchParser.__call__ for actual arguments when calling
def parse_galgrp(inp, query, qfield):
    from lmfdb.galois_groups.transitive_group import complete_group_codes
    try:
        gcs = complete_group_codes(inp)
        groups = [str(n) + "T" + str(t) for n, t in gcs]
        _parse_subset(groups, query, qfield, mode=None, radical=None, product=None, cardinality=None)
    except NameError:
        raise ValueError("It needs to be a <a title = 'Galois group labels' knowl='nf.galois_group.name'>group label</a>, such as C5 or 5T1, or a comma separated list of such labels.")

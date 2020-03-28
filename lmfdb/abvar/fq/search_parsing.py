import re
from sage.all import QQ
from lmfdb.utils.search_parsing import (
    BRACKETING_RE,
    QQ_RE,
    _multiset_encode,
    search_parser,
    nf_string_to_label,
    _parse_subset,
)

PAREN_RE = re.compile(r"(\([^\)]*\))")
# won't work for iterated parentheses ((a,b),(c,d))

@search_parser
def parse_newton_polygon(inp, query, qfield):
    polygons = []
    for polygon in BRACKETING_RE.finditer(inp):
        polygon = polygon.groups()[0][1:-1]
        if "[" in polygon or "]" in polygon:
            raise ValueError("Mismatched brackets")
        slopes = []
        lastslope = None
        for slope in polygon.split(","):
            if not QQ_RE.match(slope):
                raise ValueError("%s is not a rational slope" % slope)
            qslope = QQ(slope)
            if lastslope is not None and qslope < lastslope:
                raise ValueError("Slopes must be increasing: %s, %s" % (lastslope, slope))
            lastslope = qslope
            slopes.append(slope)
        polygons.append(slopes)
    replaced = BRACKETING_RE.sub("#", inp)
    if "[" in replaced or "]" in replaced:
        raise ValueError("Mismatched brackets")
    for slope in replaced.split(","):
        if slope == "#":
            continue
        if not QQ_RE.match(slope):
            raise ValueError("%s is not a rational slope" % slope)
        raise ValueError("You cannot specify slopes on their own")
    polygons = [_multiset_encode(poly) for poly in polygons]
    if len(polygons) == 1:
        query[qfield] = {"$contains": polygons[0]}
    else:
        query[qfield] = {"$or": [{"$contains": poly} for poly in polygons]}

@search_parser  # see SearchParser.__call__ for actual arguments when calling
def parse_nf_string(inp, query, qfield):
    fields = [nf_string_to_label(field) for field in inp.split(",")]
    _parse_subset(fields, query, qfield, radical=None, product=None)

@search_parser  # (clean_info=True, default_field='galois_group', default_name='Galois group', default_qfield='galois') # see SearchParser.__call__ for actual arguments when calling
def parse_galgrp(inp, query, qfield):
    from lmfdb.galois_groups.transitive_group import complete_group_codes
    try:
        gcs = complete_group_codes(inp)
        groups = [str(n) + "T" + str(t) for n, t in gcs]
        _parse_subset(groups, query, qfield, radical=None, product=None)
    except NameError:
        raise ValueError("It needs to be a <a title = 'Galois group labels' knowl='nf.galois_group.name'>group label</a>, such as C5 or 5T1, or a comma separated list of such labels.")

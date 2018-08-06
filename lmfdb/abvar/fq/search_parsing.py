import re
from sage.all import QQ
from lmfdb.search_parsing import BRACKETING_RE, QQ_RE, _multiset_encode, search_parser
PAREN_RE = re.compile(r'(\([^\)]*\))') # won't work for iterated parentheses ((a,b),(c,d))

@search_parser
def parse_newton_polygon(inp, query, qfield):
    polygons = []
    for polygon in BRACKETING_RE.finditer(inp):
        polygon = polygon.groups()[0][1:-1]
        if '[' in polygon or ']' in polygon:
            raise ValueError("Mismatched brackets")
        slopes = []
        lastslope = None
        for slope in polygon.split(','):
            if not QQ_RE.match(slope):
                raise ValueError("%s is not a rational slope"%slope)
            qslope = QQ(slope)
            if lastslope is not None and qslope < lastslope:
                raise ValueError("Slopes must be increasing: %s, %s"%(lastslope, slope))
            lastslope = qslope
            slopes.append(slope)
        polygons.append(slopes)
    replaced = BRACKETING_RE.sub('#',inp)
    if '[' in replaced or ']' in replaced:
        raise ValueError("Mismatched brackets")
    for slope in replaced.split(','):
        if slope == '#':
            continue
        if not QQ_RE.match(slope):
            raise ValueError("%s is not a rational slope"%slope)
        raise ValueError("You cannot specify slopes on their own")
    polygons = [_multiset_encode(poly) for poly in polygons]
    if len(polygons) == 1:
        query[qfield] = {'$contains':polygons[0]}
    else:
        query[qfield] = {'$or':[{'$contains':poly} for poly in polygons]}

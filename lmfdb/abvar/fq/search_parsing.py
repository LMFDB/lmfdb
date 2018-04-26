import re
from sage.all import ZZ, QQ, UniqueRepresentation, Partitions, Compositions, Arrangements, cartesian_product_iterator, cached_method
from sage.databases.cremona import class_to_int
from collections import defaultdict
from lmfdb.search_parsing import BRACKETING_RE, QQ_RE, collapse_ors, search_parser
PAREN_RE = re.compile(r'(\([^\)]*\))') # won't work for iterated parentheses ((a,b),(c,d))

@search_parser
def parse_newton_polygon(inp, query, qfield):
    polygons = []
    for polygon in BRACKETING_RE.finditer(inp):
        polygon = polygon.groups()[0][1:-1]
        if '[' in polygon or ']' in polygon:
            raise ValueError("Mismatched brackets")
        if '(' in polygon or ')' in polygon:
            # user is specifying break points
            if PAREN_RE.sub('',polygon).replace(',',''):
                raise ValueError("Mismatched parentheses: %s"%polygon)
            lastx = ZZ(0)
            lasty = QQ(0)
            lastslope = None
            slopes = []
            for point in PAREN_RE.finditer(polygon):
                point = point.groups()[0]
                xy = point[1:-1].split(',')
                if len(xy) != 2:
                    raise ValueError("Malformed break point: %s"%point)
                try:
                    x = ZZ(xy[0])
                    y = QQ(xy[1])
                except TypeError as err:
                    raise ValueError(str(err))
                if x <= lastx:
                    raise ValueError("Break points must be sorted by x-coordinate: %s"%point)
                slope = (y - lasty) / (x - lastx)
                if lastslope is not None and slope <= lastslope:
                    raise ValueError("Slopes specified by break points must be increasing: %s"%point)
                slopes.extend([str(slope)] * (x - lastx))
                lastx = x
                lasty = y
                lastslope = slope
        else:
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
    extra_slopes = []
    for slope in replaced.split(','):
        if slope == '#':
            continue
        if not QQ_RE.match(slope):
            raise ValueError("%s is not a rational slope"%slope)
        #extra_slopes.append(slope)
        raise ValueError("You cannot specify slopes on their own")
    if len(polygons) + len(extra_slopes) == 1:
        if polygons:
            query[qfield] = {'$regex':'^'+' '.join(polygons[0])}
        else: # won't occur because of the ValueError("You cannot specify slopes on their own") above
            query[qfield] = extra_slopes[0]
    else:
        collapse_ors(['$or',([{qfield:{'$regex':'^'+' '.join(poly)}}
                              for poly in polygons])], query) # +
                             #[{qfield:slope} for slope in extra_slopes])], query)

class DecompList(object):
    def __init__(self, pieces, maxdim, external_q, external_g, qfield, OC):
        self.L = pieces
        self.maxdim = maxdim # dictionary with keys q and values maxg
        self.external_q = external_q
        self.external_g = external_g
        self.qfield = qfield
        self.OC = OC
    def __repr__(self):
        return str(self.L)
    def is_valid(self):
        if self.q() == -1:
            raise ValueError("Only a single value of q possible within a decomposition.")
        ed = self.extra_dim()
        eg = self.external_g
        if ed[1] < 0:
            if eg[1] is None:
                raise ValueError("Total dimension is larger than any isogeny class in database.")
            else:
                raise ValueError("Total dimension of decomposition is incompatible with requested g.")
        if ed[1] > 0:
            if not (eg[1] is None or any(piece.is_star() for piece in self.L)):
                raise ValueError("Total dimension of decomposition is incompatible with requested g.")
    @cached_method
    def q(self):
        qset = [piece.q for piece in self.L if piece.q is not None]
        if self.external_q:
            qset.append(self.external_q)
        qset = set(qset)
        if len(qset) == 0:
            return None
        elif len(qset) == 1:
            return qset.pop()
        else:
            return -1 # invalid
    def extra_dim(self):
        maxg = self.external_g[1]
        if maxg is None:
            maxg = self.maxdim.get(self.q(), 0)
        else:
            maxg = min(self.maxdim.get(self.q(), 0), maxg)
        ming = self.external_g[0]
        if ming is None:
            ming = 1
        allocatedg = sum(piece.mindim() for piece in self.L)
        return (max(ming - allocatedg, 0), maxg - allocatedg)
    def collapse_stars(self):
        star_locations = []
        for i, piece in enumerate(self.L):
            if piece.is_star():
                star_locations.append(i)
        numstars = len(star_locations)
        ed = self.extra_dim()
        for total in range(numstars + ed[0], numstars + ed[1] + 1):
            for partition in Partitions(total, length=numstars):
                newL = list(self.L)
                for i, loc in enumerate(star_locations):
                    newL[loc] = DecompPiece("%s"%(partition[i]))
                yield DecompList(newL, self.maxdim, self.external_q, self.external_g, self.qfield, self.OC)
    def collapse_to_labels_and_exps(self):
        # before calling this function, must collapse stars
        # only exponent None is collapsable
        collapsable_labels = defaultdict(lambda:defaultdict(int))
        collapsable_dims = defaultdict(int) # label unspecified
        # the following lists will store pieces with specified exponent
        fixed_labels = defaultdict(lambda:defaultdict(int))
        fixed_dims = defaultdict(list)
        for piece in self.L:
            if piece.e is None:
                if piece.label is None:
                    collapsable_dims[piece.dim] += 1
                else:
                    collapsable_labels[piece.dim][piece.label] += 1 # allow for repeated labels
            else:
                if piece.label is None:
                    fixed_dims[piece.dim].append(piece.e)
                else:
                    fixed_labels[piece.dim][piece.label] += piece.e # allow for repeated labels
        dims = sorted(list(set(piece.dim for piece in self.L)))
        iterator_list = [CollapsedLabelIterator_onedim(collapsable_labels[dim], collapsable_dims[dim],
                                                       fixed_labels[dim], fixed_dims[dim], dim, self.q()) for dim in dims]
        for stretches in cartesian_product_iterator(iterator_list):
            subquery = {}
            self.OC.inc()
            overall = sum(stretches, [])
            for i, (base, exp) in enumerate(overall):
                subquery['%s.%s.0'%(self.qfield, i)] = base
                subquery['%s.%s.1'%(self.qfield, i)] = int(exp)
            subquery[self.qfield] = {'$size': len(overall)}
            yield subquery

def extended_class_to_int(k):
    if k == 'a':
        return 0
    elif k[0] == 'a':
        return -class_to_int(k[1:])
    else:
        return class_to_int(k)

class Insertions(object):
    def __init__(self, labels, extra_exps, dim, q):
        self.labels = labels
        self.extra_exps = sorted(extra_exps)
        self.total_exp = len(extra_exps)
        self.dim_re = {'$regex':'^%s'%(dim)}
        self.q = q
    def __iter__(self):
        # same subtraction trick from CollapsedLabelIterator_onedim.__iter__
        for comp in Compositions(len(self.labels) + 1 + self.total_exp, length = len(self.labels) + 1):
            for arr in Arrangements(self.extra_exps, len(self.extra_exps)):
                stretch = []
                arr_pos = 0
                for label_pos in range(len(self.labels) + 1):
                    stretch.extend((self.dim_re, a) for a in arr[arr_pos:arr_pos+(comp[label_pos]-1)])
                    arr_pos += comp[label_pos] - 1
                    if label_pos < len(self.labels):
                        stretch.append(self.labels[label_pos])
                yield stretch

class CollapsedLabelIterator_onedim(object):
    def __init__(self, collapsable_labels, extrafactors, fixed_labels, fixed_dims, dim, q):
        self.clabels = collapsable_labels
        self.flabels = fixed_labels
        self.fdims = fixed_dims
        self.sorted_labels = sorted(list(set(collapsable_labels.keys() + fixed_labels.keys())),
                                   key=lambda x: tuple(extended_class_to_int(k) for k in x.split('_')))
        self.extrafactors = extrafactors
        self.dim = dim
        self.q = q
    def __iter__(self):
        # compositions are an ordered decomposition as a sum of positive integers.
        # since we want to allow zeros and want to allow some dimension to be unallocated to clabels,
        # we add len(self.clabels) + 1 to the total, then subtract 1 from each summand in the composition.
        for comp in Compositions(len(self.clabels) + 1 + self.extrafactors, length=len(self.clabels)+1):
            labels = []
            i = 0
            for label in self.sorted_labels:
                if label in self.clabels:
                    labels.append(('%s.%s.%s'%(self.dim,self.q,label), self.clabels[label] + self.flabels[label] + comp[i] - 1))
                    i += 1
                else:
                    labels.append(('%s.%s.%s'%(self.dim,self.q,label), self.flabels[label]))
            for part in Partitions(comp[-1] - 1):
                for stretch in Insertions(labels, self.fdims + list(part), self.dim, self.q):
                    yield stretch

abvar_label_matcher = re.compile(r"(\d+)\.(\d+)(\.([a-z_]+))?")
class DecompPiece(UniqueRepresentation):
    def __init__(self, desc):
        self.desc = desc
        c = desc.count("^")
        if c > 1:
            raise ValueError("Too many ^ in %s"%desc)
        if c == 1:
            base, e = desc.split("^")
            self.e = int(e)
        else:
            base = desc
            self.e = None
        if base == '*':
            if self.e is not None:
                raise ValueError("Exponents on stars not allowed")
            self.dim = self.q = self.label = None
        elif base.isdigit():
            self.dim = int(base)
            self.q = self.label = None
        else:
            match = abvar_label_matcher.match(base)
            if match:
                dim, q, _, isog = match.groups()
                self.dim = int(dim)
                self.q = int(q)
                self.label = isog
            else:
                raise ValueError("Invalid descriptor %s: must be integer, label or *"%base)
    def mindim(self):
        if self.dim is None:
            return 1 # we don't allow exponents on stars
        elif self.e is None:
            return self.dim
        else:
            return self.dim*self.e
    def is_star(self):
        return self.dim is None
    def __repr__(self):
        return self.desc

class OverflowCatcher(object):
    def __init__(self, error_on=100):
        self.error_on = error_on
        self.curr = 0
    def inc(self):
        self.curr += 1
        if self.curr == self.error_on:
            raise ValueError("Query resulted in more than %s possible decomposition types."%self.curr)

@search_parser
def parse_abvar_decomp(inp, query, qfield, av_stats):
    external_q = query.get('q')
    if isinstance(external_q, dict):
        external_q = None
    external_g = query.get('g')
    if isinstance(external_g, dict):
        external_g = (external_g.get('$gte'), external_g.get('$lte'))
    else:
        external_g = (external_g, external_g)
    maxdim = av_stats.maxg
    for decomp in BRACKETING_RE.finditer(inp):
        decomp = decomp.groups()[0][1:-1]
        pieces = [DecompPiece(piece) for piece in decomp.split(',')]
        OC = OverflowCatcher()
        decompL = DecompList(pieces, maxdim, external_q, external_g, qfield, OC)
        decompL.is_valid() # raises a ValueError if invalid
        subqueries = []
        for dL in decompL.collapse_stars():
            subqueries += [subquery for subquery in dL.collapse_to_labels_and_exps()]
        collapse_ors(['$or', subqueries], query)

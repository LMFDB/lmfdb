import re
import string

from lmfdb.db_backend import db

from sage.all import ZZ, gap

from lmfdb.utils import list_to_latex_matrix, display_multiset

MAX_GROUP_DEGREE = 23

def small_group_display_knowl(n, k, name=None):
    group = db.gps_small.lookup('%s.%s'%(n,k))
    if group is None:
        return '$[%d, %d]$'%(n,k)
    if not name:
        name = '$%s$'%group['pretty']
    return '<a title = "' + name + ' [group.small.data]" knowl="group.small.data" kwargs="gapid=' + str(n) + '.' + str(k) + '">' + name + '</a>'

def small_group_label_display_knowl(label, name=None):
    if not name:
        group = db.gps_small.lookup(label)
        name = '$%s$'%group['pretty']
    return '<a title = "' + name + ' [group.small.data]" knowl="group.small.data" kwargs="gapid=' + label + '">' + name + '</a>'


def small_group_data(gapid):
    parts = gapid.split('.')
    n = int(parts[0])
    k = int(parts[1])
    group = db.gps_small.lookup(str(gapid))
    inf = "Group $%s$" % str(group['pretty'])
    inf += " &nbsp; &nbsp; &mdash; &nbsp; &nbsp;  "
    inf += ('' if group['cyclic'] else 'not')+' cyclic, '
    inf += ('' if group['abelian'] else 'non-')+'abelian, '
    inf += ('' if group['solvable'] else 'not')+' solvable'
    inf += '<p>Order: '+str(n)
    inf += '<br>GAP small group number: '+str(k)
    inf += '<br>Exponent: '+str(group['exponent'])
    inf += '<br>Perfect: '+str(group['perfect'])
    inf += '<br>Simple: '+str(group['simple'])
    inf += '<br>Normal subgroups: '+display_multiset(group['normal_subgroups'],small_group_label_display_knowl)
    inf += '<br>Maximal subgroups: '+display_multiset(group['maximal_subgroups'], small_group_label_display_knowl)
    inf += '<br>Center: '+small_group_label_display_knowl(str(group['center']))
    inf += '<br>Derived subgroup: '+small_group_label_display_knowl(str(group['derived_group']))
    inf += '<br>Abelianization: '+small_group_label_display_knowl(str(group['abelian_quotient']))
    inf += '<br>Conjugacy class information: <table style="text-align: center;"><tr><th>Element Order<th>Size<th>Multiplicity'
    for row in group['clases']:
        inf += '<tr><td>%d<td>%d<td>%d'%(row[0],row[1],row[2])
    inf += '</table></p>'
    return inf


############  Galois group object


class WebGaloisGroup:
    """
      Class for retrieving transitive group information from the database
    """
    def __init__(self, label, data=None):
        self.label = label
        if data is None:
            self._data = self._get_dbdata()
        else:
            self._data = data

    @classmethod
    def from_nt(cls, n, t):
        return cls(base_label(n, t))

    @classmethod
    def from_data(cls, data):
        return cls(data['label'], data)

    def _get_dbdata(self):
        return db.gps_transitive.lookup(self.label)

    def n(self):
        return self._data['n']

    def t(self):
        return self._data['t']

    def is_abelian(self):
        if self._data['ab'] == 1:
            return True
        return False

    def arith_equivalent(self):
        if 'arith_equiv' in self._data:
          return self._data['arith_equiv']
        return 0

    def order(self):
        return int(self._data['order'])

    def display_short(self):
        if self._data.get('pretty',None) is not None:
            return self._data['pretty']
        return self._data['name']

    def otherrep_list(self):
        reps = [(j[0], j[1]) for j in self._data['repns']]
        me = (self.n(), self.t())
        difreps = list(set(reps))
        difreps.sort()
        ans = ''
        for k in difreps:
            if ans != '':
                ans += ', '
            cnt = reps.count(k)
            start = 'a'
            if k == me:
                start = nextchr(start)
            if cnt == 1:
                ans += tryknowl(k[0], k[1])
                if k == me:
                    ans += 'b'
            else:
                for j in range(cnt):
                    if j > 0:
                        ans += ', '
                    ans += "%s%s" % (tryknowl(k[0], k[1]), start)
                    start = nextchr(start)
        return ans

    def subfields(self):
        ans = ''
        for k in self._data['subs']:
            if ans != '':
                ans += ', '
            ans += tryknowl(k[0], k[1])
        return ans

############  Misc Functions

def base_label(n, t):
    return str(n) + "T" + str(t)

# When labeling other rep'ns, we go successively through characters
# This can exhaust the alphabet.  So, c could be a longer string!


def nextchr(c):
    s = ord('a') - 1  # really 96
    l = [ZZ(ord(j) - s) for j in list(c)]
    l.reverse()
    tot = ZZ(l, 27) + 1
    newl = tot.digits(27)
    newl.reverse()
    newl = map(lambda x: x + 1 if x == 0 else x, newl)
    return ''.join([chr(j + s) for j in newl])


def trylink(n, t):
    if n <= MAX_GROUP_DEGREE:
        return '<a href="/GaloisGroup/%dT%d">%dT%d</a>' % (n, t, n, t)
    return '%dT%d' % (n, t)


def tryknowl(n, t):
    if n <= MAX_GROUP_DEGREE:
        return group_display_knowl(n, t, '%dT%d' % (n, t))
    return '%dT%d' % (n, t)


def group_display_short(n, t):
    label = base_label(n, t)
    group = db.gps_transitive.lookup(label)
    if group is not None and group.get('pretty',None) is not None:
        return group['pretty']
    return "%dT%d"%(n,t)

# Returns the empty string if there is no pretty name
def group_display_pretty(n, t):
    label = base_label(n, t)
    group = db.gps_transitive.lookup(label)
    if group.get('pretty', None) is not None:
        return group['pretty']
    return ""

def group_display_knowl(n, t, name=None):
    label = base_label(n, t)
    group = db.gps_transitive.lookup(label)
    if not name:
        if group is not None and group.get('pretty',None) is not None:
            name = group['pretty']
        else:
            name = "%dT%d"%(n,t)
    if group is None:
        return name
    return '<a title = "' + name + ' [nf.galois_group.data]" knowl="nf.galois_group.data" kwargs="n=' + str(n) + '&t=' + str(t) + '">' + name + '</a>'


def galois_module_knowl(n, t, index):
    name = db.gps_gmodules.lucky({'n': n, 't': t, 'index': index}, 'name')
    if name is None:
        return 'Error'
    return '<a title = "%s [nf.galois_group.gmodule]" knowl="nf.galois_group.gmodule" kwargs="n=%d&t=%d&ind=%d">%s</a>'%(name, n, t, index, name)


def cclasses_display_knowl(n, t, name=None):
    if not name:
        name = 'Conjugacy class representatives for '
        name += group_display_short(n, t)
    return '<a title = "' + name + ' [gg.conjugacy_classes.data]" knowl="gg.conjugacy_classes.data" kwargs="n=' + str(n) + '&t=' + str(t) + '">' + name + '</a>'


def character_table_display_knowl(n, t, name=None):
    if not name:
        name = 'Character table for '
        name += group_display_short(n, t)
    return '<a title = "' + name + ' [gg.character_table.data]" knowl="gg.character_table.data" kwargs="n=' + str(n) + '&t=' + str(t) + '">' + name + '</a>'


def group_phrase(n, t):
    label = base_label(n, t)
    group = db.gps_transitive.lookup(label)
    inf = ''
    if group['cyc'] == 1:
        inf += "A cyclic"
    elif group['ab'] == 1:
        inf += "An abelian"
    elif group['solv'] == 1:
        inf += "A solvable"
    else:
        inf += "A non-solvable"
    inf += ' group of order '
    inf += str(group['order'])
    return(inf)


def group_display_long(n, t):
    label = base_label(n, t)
    group = db.gps_transitive.lookup(label)
    inf = "Group %sT%s, order %s, parity %s" % (group['n'], group['t'], group['order'], group['parity'])
    if group['cyc'] == 1:
        inf += ", cyclic"
    elif group['ab'] == 1:
        inf += ", abelian"
    elif group['solv'] == 1:
        inf += ", non-abelian, solvable"
    else:
        inf += ", non-solvable"
    if group['prim'] == 1:
        inf += ", primitive"
    else:
        inf += ", imprimitive"

    inf = "  (%s)" % inf
    if group.get('pretty', None) is not None:
        return group['pretty'] + inf
    return group['name'] + inf


def galois_group_data(n, t):
    label = base_label(n, t)
    group = db.gps_transitive.lookup(label)
    inf = "Transitive group " + str(group['n']) + "T" + str(group['t'])
    inf += ", order " + str(group['order'])
    inf += ", parity " + str(group['parity'])
    if group['cyc'] == 1:
        inf += ", cyclic"
    elif group['ab'] == 1:
        inf += ", abelian"
    elif group['solv'] == 1:
        inf += ", non-abelian solvable"
    else:
        inf += ", non-solvable"
    if group['prim'] == 1:
        inf += ", primitive"
    else:
        inf += ", imprimitive"
    inf += '<div>'
    inf += '<a title="%s [gg.conway_name]" knowl="gg.conway_name" kwarts="n=%s&t=%s">%s</a>: '%('CHM label',str(n),str(t),'CHM label')
    inf += '%s</div>'%(group['name'])

    rest = '<div><h3>Generators</h3><blockquote>'
    rest += generators(n, t)
    rest += '</blockquote></div>'

    rest += '<div><h3>Subfields</h3><blockquote>'
    rest += subfield_display(n, group['subs'])
    rest += '</blockquote></div>'
    rest += '<div><h3>Other low-degree representations</h3><blockquote>'
    rest += otherrep_display(n, t, group['repns'])
    rest += '</blockquote></div>'
    rest += '<div align="right">'
    rest += '<a href="/GaloisGroup/%s">%sT%s home page</a>' % (label, str(n), str(t))
    rest += '</div>'

    if group.get('pretty', None) is not None:
        return group['pretty'] + "&nbsp;&nbsp;&mdash;&nbsp;&nbsp;  "+ inf + rest
    return inf + rest



def group_cclasses_knowl_guts(n, t):
    label = base_label(n, t)
    group = db.gps_transitive.lookup(label)
    gname = group['name']
    if group.get('pretty', None) is not None:
        gname = group['pretty']
    else:
        gname = gname.replace('=', ' = ')
    rest = '<div>Conjugacy class representatives for '
    rest += gname
    rest += '<blockquote>'
    rest += cclasses(n, t)
    rest += '</blockquote></div>'
    return rest


def group_character_table_knowl_guts(n, t):
    label = base_label(n, t)
    group = db.gps_transitive.lookup(label)
    gname = group['name']
    gname = gname.replace('=', ' = ')
    if group.get('pretty', None) is not None:
        gname = group['pretty']
    inf = '<div>Character table for '
    inf += gname
    inf += '<blockquote>'
    inf += '<pre>'
    inf += chartable(n, t)
    inf += '</pre>'
    inf += '</blockquote></div>'
    return(inf)


def galois_module_knowl_guts(n, t, index):
    mymod = db.gps_gmodules.lucky({'n': int(n), 't': int(t), 'index': int(index)}, ['name','dim','gens'])
    if mymod is None:
        return 'Database call failed'
    name = mymod['name']
    out = "$\\Z[G]$ module %s with $G=$ " % str(name)
    out += group_display_knowl(n, t)
    out += " = %sT%s " %(n, t)
    out += "<blockquote>"
    out += "Dimension: %s" % str(mymod['dim'])
    out += r"<br>Action: $$\begin{align*}"
    for g in mymod['gens']:
        matg = list_to_latex_matrix(g[1])
        out += "%s &\\mapsto %s \\\\" %(str(g[0]), matg)
    out = out[:-2]
    out += r"\end{align*}$$"
    out += "</blockquote>"
    return out


def subfield_display(n, subs):
    if n == 1:
        return 'Degree 1 - None'
    degs = ZZ(str(n)).divisors()[1:-1]
    if len(degs) == 0:
        return 'Prime degree - none'
    ans = ''
    substrs = {}
    for deg in degs:
        substrs[deg] = ''
    for k in subs:
        if substrs[k[0]] != '':
            substrs[k[0]] += ', '
        if k[0] <= MAX_GROUP_DEGREE:
            substrs[k[0]] += group_display_knowl(k[0], k[1])
        else:
            substrs[k[0]] += str(k[0]) + 'T' + str(k[1])
    for deg in degs:
        ans += '<p>Degree ' + str(deg) + ': '
        if substrs[deg] == '':
            substrs[deg] = 'None'
        ans += substrs[deg] + '</p>'
    return ans


def otherrep_display(n, t, reps):
    reps = [(j[0], j[1]) for j in reps]
    me = (n, t)
    difreps = list(set(reps))
    difreps.sort()
    ans = ''
    for k in difreps:
        if ans != '':
            ans += ', '
        cnt = reps.count(k)
        start = 'a'
        name = "%dT%d" % (k[0], k[1])
        if k == me:
            start = chr(ord(start) + 1)
        if cnt == 1:
            if k[0] <= MAX_GROUP_DEGREE:
                ans += group_display_knowl(k[0], k[1], name)
            else:
                ans += name
            if k == me:
                ans += 'b'
        else:
            for j in range(cnt):
                if j > 0:
                    ans += ', '
                if k[0] <= MAX_GROUP_DEGREE:
                    ans += "%s%s" % (group_display_knowl(k[0], k[1], name), start)
                else:
                    ans += "%s%s" % (name, start)
                start = chr(ord(start) + 1)

    if ans == '':
        ans = 'None'
    return ans


def resolve_display(resolves):
    ans = ''
    old_deg = -1
    for j in resolves:
        if j[0] != old_deg:
            if old_deg < 0:
                ans += '<table>'
            else:
                ans += '</td></tr>'
            old_deg = j[0]
            ans += '<tr><td>' + str(j[0]) + ': </td><td>'
        else:
            ans += ', '
        k = j[1]
        name = str(k[0]) + 'T' + str(k[1])
        if k[0] <= MAX_GROUP_DEGREE:
            ans += group_display_knowl(k[0], k[1], name)
        else:
            if k[1] == -1:
                name = '%dT?' % k[0]
            ans += name
    if ans != '':
        ans += '</td></tr></table>'
    else:
        ans = 'None'
    return ans

def group_display_inertia(code):
    if str(code[0]) == "t":
        return group_display_knowl(code[1][0], code[1][1])
    if code[1] == [1,1]:
        return "Trivial"
    ans = "Intransitive group isomorphic to "+small_group_display_knowl(code[1][0],code[1][1])
    return ans

def conjclasses(g, n):
    gap.set('cycletype', 'function(el, n) local ct; ct := CycleLengths(el, [1..n]); ct := ShallowCopy(ct); Sort(ct); ct := Reversed(ct); return(ct); end;')
    cc = g.ConjugacyClasses()
    ccn = [x.Size() for x in cc]
    ccc = [x.Representative() for x in cc]
    if int(n) == 1:
        cc2 = [[1]]
        cc = ['()']
    else:
        cc = ccc
        cc2 = [x.cycletype(n) for x in cc]
    cc2 = [str(x) for x in cc2]
    cc2 = map(lambda x: re.sub("\[", '', x), cc2)
    cc2 = map(lambda x: re.sub("\]", '', x), cc2)
    ans = [[cc[j], ccc[j].Order(), ccn[j], cc2[j]] for j in range(len(ccn))]
    return(ans)


def cclasses(n, t):
    if int(n) == 1:
        G = gap.SmallGroup(1, 1)
    else:
        G = gap.TransitiveGroup(n, t)
    cc = conjclasses(G, n)
    html = """<div>
            <table class="ntdata">
            <thead><tr><td>Cycle Type</td><td>Size</td><td>Order</td><td>Representative</td></tr></thead>
            <tbody>
         """
    for c in cc:
        html += '<tr><td>' + str(c[3]) + '</td>'
        html += '<td>' + str(c[2]) + '</td>'
        html += '<td>' + str(c[1]) + '</td>'
        html += '<td>' + str(c[0]) + '</td>'
    html += """</tr></tbody>
             </table>
          """
    return html


def chartable(n, t):
    if int(n) == 1:
        G = gap.SmallGroup(n, t)
    else:
        G = gap.TransitiveGroup(n, t)
    ctable = str(G.CharacterTable().Display())
    ctable = re.sub("^.*\n", '', ctable)
    ctable = re.sub("^.*\n", '', ctable)
    return ctable


def generators(n, t):
    if str(n) == "1":
        return "None needed"
    else:
        G = gap.TransitiveGroup(n, t)
    gens = G.SmallGeneratingSet()
    gens = str(gens)
    gens = re.sub("[\[\]]", '', gens)
    return gens


def group_alias_table():
    akeys = aliases.keys()
    akeys.sort(key=lambda x: aliases[x][0][0] * 10000 + aliases[x][0][1])
    ans = '<table border=1 cellpadding=5 class="right_align_table"><thead><tr><th>Alias</th><th>Group</th><th>\(n\)T\(t\)</th></tr></thead>'
    ans += '<tbody>'
    for j in akeys:
        name = group_display_short(aliases[j][0][0], aliases[j][0][1])
        ntlist = aliases[j]
        #ntlist = filter(lambda x: x[0] < 12, ntlist)
        ntstrings = [str(x[0]) + "T" + str(x[1]) for x in ntlist]
        ntstring = string.join(ntstrings, ", ")
        ans += "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (j, name, ntstring)
    ans += '</tbody></table>'
    return ans




def complete_group_code(code):
    if code in aliases:
        return aliases[code]
    rematch = re.match(r"^(\d+)T(\d+)$", code)
    if rematch:
        n = int(rematch.group(1))
        t = int(rematch.group(2))
        return [[n, t]]
    else:
        raise NameError(code)
    return []

# Takes a list of codes


def complete_group_codes(codes):
    codes = codes.upper()
    ans = []
    # after upper casing, we can replace commas we want to keep with "z"
    codes = re.sub(r'\((\d+),(\d+)\)', r'(\1z\2)', codes)
    codelist = codes.split(',')
    # now turn the z's back into commas
    codelist = [re.sub('z', ',', x) for x in codelist]
    for code in codelist:
        ans.extend(complete_group_code(code))
    return ans


aliases = {}

# Do all cyclic groups as once
for j in range(1,24):
    aliases['C'+str(j)] = [(j,1)]

aliases['S1'] = [(1, 1)]
aliases['A1'] = [(1, 1)]
aliases['A2'] = [(1, 1)]
aliases['S2'] = [(2, 1)]
aliases['D1'] = [(2, 1)]
aliases['A3'] = [(3, 1)]
aliases['S3'] = [(3, 2), (6, 2)]
aliases['D3'] = [(3, 2), (6, 2)]
aliases['V4'] = [(4, 2)]
aliases['D2'] = [(4, 2)]
aliases['D4'] = [(4, 3), (8, 4)]
aliases['C2XC2'] = [(4, 2)]
aliases['A4'] = [(4, 4), (6, 4), (12, 4)]
aliases['S4'] = [(4, 5), (6, 7), (6, 8), (8, 14), (12, 8), (12, 9)]
aliases['D5'] = [(5, 2), (10, 2)]
aliases['F5'] = [(5, 3), (10, 4)]
aliases['A5'] = [(5, 4), (6, 12), (10, 7), (12, 33)]
aliases['S5'] = [(5, 5), (6, 14), (10, 12), (10, 13), (12, 74)]
aliases['D6'] = [(6, 3), (12, 3)]
aliases['PSL(2,5)'] = aliases['A5']
aliases['PGL(2,5)'] = aliases['S5']
aliases['A6'] = [(6, 15), (10, 26)]
aliases['S6'] = [(6, 16), (10, 32), (12, 183), (12, 183)]
aliases['D7'] = [(7, 2),(14, 2)]
aliases['F7'] = [(7, 4),(14,4),(21,4)]
aliases['GL(3,2)'] = [(7, 5), (8, 37)]
aliases['A7'] = [(7, 6)]
aliases['S7'] = [(7, 7)]
aliases['C4XC2'] = [(8, 2)]
aliases['C2XC4'] = [(8, 2)]
aliases['C2XC2XC2'] = [(8, 3)]
aliases['Q8'] = [(8, 5)]
aliases['D8'] = [(8, 6),(16,7)]
aliases['SL(2,3)'] = [(8, 12)]
aliases['GL(2,3)'] = [(8, 23)]
aliases['PSL(2,7)'] = aliases['GL(3,2)']
aliases['PGL(2,7)'] = [(8, 43)]
aliases['A8'] = [(8, 49)]
aliases['S8'] = [(8, 50)]
aliases['C3XC3'] = [(9, 2)]
aliases['D9'] = [(9, 3)]
aliases['S3XC3'] = [(6, 5), (9, 4)]
aliases['C3XS3'] = [(6, 5), (9, 4)]
aliases['S3XS3'] = [(6, 9), (9, 8), (12, 16)]
aliases['M9'] = [(9, 14), (12, 47)]
aliases['PSL(2,8)'] = [(9, 27)]
aliases['A9'] = [(9, 33)]
aliases['S9'] = [(9, 34)]
aliases['D10'] = [(10, 3)]
aliases['PSL(2,9)'] = aliases['A6']
aliases['PGL(2,9)'] = [(10, 30), (12, 182)]
aliases['M10'] = [(10, 31), (12, 181)]
aliases['A10'] = [(10, 44)]
aliases['S10'] = [(10, 45)]
aliases['D11'] = [(11, 2),(22,2)]
aliases['F11'] = [(11, 4),(22,4)]
aliases['PSL(2,11)'] = [(11, 5), (12, 272)]
aliases['M11'] = [(11, 6)]
aliases['A11'] = [(11, 7)]
aliases['S11'] = [(11, 8)]
aliases['C6XC2'] = [(12, 2)]
aliases['C2XC6'] = [(12, 2)]
aliases['A12'] = [(12, 300)]
aliases['S12'] = [(12, 301)]
aliases['D13'] = [(13, 2)]
aliases['F13'] = [(13, 6)]
aliases['A13'] = [(13, 8)]
aliases['S13'] = [(13, 9)]
aliases['D14'] = [(14, 3)]
aliases['PGL(2,13)'] = [(14, 39)]
aliases['A14'] = [(14, 62)]
aliases['S14'] = [(14, 63)]
aliases['A15'] = [(15, 103)]
aliases['S15'] = [(15, 104)]
aliases['Q16'] = [(16, 14)]
aliases['A16'] = [(16, 1953)]
aliases['S16'] = [(16, 1954)]
aliases['D17'] = [(17, 2)]
aliases['F17'] = [(17, 5)]
aliases['PSL(2,17)'] = [(17, 6)]
aliases['A17'] = [(17, 9)]
aliases['S17'] = [(17, 10)]
aliases['PGL(2,17)'] = [(18, 468)]
aliases['A18'] = [(18, 982)]
aliases['S18'] = [(18, 983)]
aliases['A19'] = [(19, 7)]
aliases['S19'] = [(19, 8)]
aliases['PGL(2,19)'] = [(20, 362)]
aliases['A20'] = [(20, 1116)]
aliases['S20'] = [(20, 1117)]
aliases['A21'] = [(21, 163)]
aliases['S21'] = [(21, 164)]
aliases['D22'] = [(22, 3)]
aliases['A22'] = [(22, 58)]
aliases['S22'] = [(22, 59)]
aliases['D23'] = [(23, 2)]
aliases['F23'] = [(23, 3)]
aliases['M23'] = [(23, 5)]
aliases['A23'] = [(23, 6)]
aliases['S23'] = [(23, 7)]


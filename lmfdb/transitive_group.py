import re
import pymongo
import string
import bson

from lmfdb.base import app, getDBConnection
from flask import Flask, session, g, render_template, url_for, request, redirect

import sage.all
from sage.all import ZZ, latex, AbelianGroup, pari, gap

from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, parse_range

from pymongo.connection import Connection

MAX_GROUP_DEGREE = 23

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
        tgdb = getDBConnection().transitivegroups.groups
        return tgdb.find_one({'label': self.label})

    def n(self):
        return self._data['n']

    def t(self):
        return self._data['t']

    def is_abelian(self):
        if self._data['ab'] == 1:
            return True
        return False

    def order(self):
        return self._data['order']

    def display_short(self):
        if self._data['pretty']:
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
        C = getDBConnection()
        return group_display_knowl(n, t, C, '%dT%d' % (n, t))
    return '%dT%d' % (n, t)


def group_display_short(n, t, C):
    label = base_label(n, t)
    group = C.transitivegroups.groups.find_one({'label': label})
    if group['pretty']:
        return group['pretty']
    return group['name']


def group_display_knowl(n, t, C, name=None):
    if not name:
        name = group_display_short(n, t, C)
    return '<a title = "' + name + ' [nf.galois_group.data]" knowl="nf.galois_group.data" kwargs="n=' + str(n) + '&t=' + str(t) + '">' + name + '</a>'


def cclasses_display_knowl(n, t, C, name=None):
    if not name:
        name = 'Conjugacy class representatives for '
        name += group_display_short(n, t, C)
    return '<a title = "' + name + ' [gg.conjugacy_classes.data]" knowl="gg.conjugacy_classes.data" kwargs="n=' + str(n) + '&t=' + str(t) + '">' + name + '</a>'


def character_table_display_knowl(n, t, C, name=None):
    if not name:
        name = 'Character table for '
        name += group_display_short(n, t, C)
    return '<a title = "' + name + ' [gg.character_table.data]" knowl="gg.character_table.data" kwargs="n=' + str(n) + '&t=' + str(t) + '">' + name + '</a>'

## For storage in the database by other modules


def make_galois_pair(n, t):
    return bson.SON([('n', n), ('t', t)])


def group_phrase(n, t, C):
    label = base_label(n, t)
    group = C.transitivegroups.groups.find_one({'label': label})
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


def group_display_long(n, t, C):
    label = base_label(n, t)
    group = C.transitivegroups.groups.find_one({'label': label})
    inf = "Group %sT%s, order %s, parity %s" % (group['n'], group['t'], group['order'], group['parity'])
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

    inf = "  (%s)" % inf
    if group['pretty']:
        return group['pretty'] + inf
    return group['name'] + inf


def group_knowl_guts(n, t, C):
    label = base_label(n, t)
    group = C.transitivegroups.groups.find_one({'label': label})
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

    inf = "&nbsp;&nbsp;&mdash;&nbsp;&nbsp;  " + inf + ""
    rest = '<div><h3>Generators</h3><blockquote>'
    rest += generators(n, t)
    rest += '</blockquote></div>'

    rest += '<div><h3>Subfields</h3><blockquote>'
    rest += subfield_display(C, n, group['subs'])
    rest += '</blockquote></div>'
    rest += '<div><h3>Other low-degree representations</h3><blockquote>'
    rest += otherrep_display(n, t, C, group['repns'])
    rest += '</blockquote></div>'
    rest += '<div align="right">'
    rest += '<a href="/GaloisGroup/%s">%sT%s home page</a>' % (label, str(n), str(t))
    rest += '</div>'

    if group['pretty']:
        return group['pretty'] + inf + rest
    return group['name'] + inf + rest


def group_cclasses_knowl_guts(n, t, C):
    label = base_label(n, t)
    group = C.transitivegroups.groups.find_one({'label': label})
    gname = group['name']
    if group['pretty']:
        gname = group['pretty']
    rest = '<div>Conjugacy class representatives for '
    rest += gname
    rest += '<blockquote>'
    rest += cclasses(n, t)
    rest += '</blockquote></div>'
    return(rest)


def group_character_table_knowl_guts(n, t, C):
    label = base_label(n, t)
    group = C.transitivegroups.groups.find_one({'label': label})
    gname = group['name']
    if group['pretty']:
        gname = group['pretty']
    inf = '<div>Character table for '
    inf += gname
    inf += '<blockquote>'
    inf += '<pre>'
    inf += chartable(n, t)
    inf += '</pre>'
    inf += '</blockquote></div>'
    return(inf)


def subfield_display(C, n, subs):
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
            substrs[k[0]] += group_display_knowl(k[0], k[1], C)
        else:
            substrs[k[0]] += str(k[0]) + 'T' + str(k[1])
    for deg in degs:
        ans += '<p>Degree ' + str(deg) + ': '
        if substrs[deg] == '':
            substrs[deg] = 'None'
        ans += substrs[deg] + '</p>'
    return ans


def otherrep_display(n, t, C, reps):
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
                ans += group_display_knowl(k[0], k[1], C, name)
            else:
                ans += name
            if k == me:
                ans += 'b'
        else:
            for j in range(cnt):
                if j > 0:
                    ans += ', '
                if k[0] <= MAX_GROUP_DEGREE:
                    ans += "%s%s" % (group_display_knowl(k[0], k[1], C, name), start)
                else:
                    ans += "%s%s" % (name, start)
                start = chr(ord(start) + 1)

    if ans == '':
        ans = 'None'
    return ans


def resolve_display(C, resolves):
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
            ans += group_display_knowl(k[0], k[1], C, name)
        else:
            if k[1] == -1:
                name = '%dT?' % k[0]
            ans += name
    if ans != '':
        ans += '</td></tr></table>'
    else:
        ans = 'None'
    return ans


def group_display_inertia(code, C):
    if str(code[1]) == "t":
        return group_display_knowl(code[2][0], code[2][1], C)
    ans = "Intransitive group isomorphic to "
    if len(code[2]) > 1:
        ans += group_display_short(code[2][0], code[2][1], C)
        return ans
    ans += code[3]
    return ans

    label = base_label(n, t)
    group = C.transitivegroups.groups.find_one({'label': label})
    if group['pretty']:
        return group['pretty']
    return group['name']


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
    CT = G.CharacterTable()
    ctable = gap.eval("Display(%s)" % CT.name())
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


def aliastable(C):
    akeys = aliases.keys()
    akeys.sort(key=lambda x: aliases[x][0][0] * 10000 + aliases[x][0][1])
    ans = '<table border=1 cellpadding=5 class="right_align_table"><thead><tr><th>Alias</th><th>Group</th><th>\(n\)T\(t\)</th></tr></thead>'
    ans += '<tbody>'
    for j in akeys:
        name = group_display_short(aliases[j][0][0], aliases[j][0][1], C)
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

# for j in group_names.keys():
#  for k in group_names[j]:
#    if re.search('^\s*\d+T\d+\s*$', k) == None and re.search('^\s*\d+\s*$',k) ==  None:
#      newv = (j[0], j[3])
#      print "aliases['"+str(k)+"'] = ", newv

aliases = {}

aliases['S1'] = [(1, 1)]
aliases['C1'] = [(1, 1)]
aliases['A1'] = [(1, 1)]
aliases['A2'] = [(1, 1)]
aliases['S2'] = [(2, 1)]
aliases['C2'] = [(2, 1)]
aliases['D1'] = [(2, 1)]
aliases['A3'] = [(3, 1)]
aliases['C3'] = [(3, 1)]
aliases['S3'] = [(3, 2), (6, 2)]
aliases['D3'] = [(3, 2), (6, 2)]
aliases['C4'] = [(4, 1)]
aliases['V4'] = [(4, 2)]
aliases['D2'] = [(4, 2)]
aliases['D4'] = [(4, 3), (8, 4)]
aliases['C2XC2'] = [(4, 2)]
aliases['A4'] = [(4, 4), (6, 4), (12, 4)]
aliases['S4'] = [(4, 5), (6, 7), (6, 8), (8, 14), (12, 8), (12, 9)]
aliases['C5'] = [(5, 1)]
aliases['D5'] = [(5, 2), (10, 2)]
aliases['F5'] = [(5, 3), (10, 4)]
aliases['A5'] = [(5, 4), (6, 12), (10, 7), (12, 33)]
aliases['S5'] = [(5, 5), (6, 14), (10, 12), (10, 13), (12, 74)]
aliases['C6'] = [(6, 1)]
aliases['D6'] = [(6, 3), (12, 3)]
aliases['PSL(2,5)'] = aliases['A5']
aliases['PGL(2,5)'] = aliases['S5']
aliases['A6'] = [(6, 15), (10, 26)]
aliases['S6'] = [(6, 16), (10, 32), (12, 183), (12, 183)]
aliases['C7'] = [(7, 1)]
aliases['D7'] = [(7, 2)]
aliases['F7'] = [(7, 4)]
aliases['GL(3,2)'] = [(7, 5), (8, 37)]
aliases['A7'] = [(7, 6)]
aliases['S7'] = [(7, 7)]
aliases['C8'] = [(8, 1)]
aliases['C4XC2'] = [(8, 2)]
aliases['C2XC2XC2'] = [(8, 3)]
aliases['Q8'] = [(8, 5)]
aliases['D8'] = [(8, 6)]
aliases['SL(2,3)'] = [(8, 12)]
aliases['GL(2,3)'] = [(8, 23)]
aliases['PSL(2,7)'] = aliases['GL(3,2)']
aliases['PGL(2,7)'] = [(8, 43)]
aliases['A8'] = [(8, 49)]
aliases['S8'] = [(8, 50)]
aliases['C9'] = [(9, 1)]
aliases['C3XC3'] = [(9, 2)]
aliases['D9'] = [(9, 3)]
aliases['S3XC3'] = [(6, 5), (9, 4)]
aliases['S3XS3'] = [(6, 9), (9, 8), (12, 16)]
aliases['M9'] = [(9, 14), (12, 47)]
aliases['PSL(2,8)'] = [(9, 27)]
aliases['A9'] = [(9, 33)]
aliases['S9'] = [(9, 34)]
aliases['C10'] = [(10, 1)]
aliases['D10'] = [(10, 3)]
aliases['PSL(2,9)'] = aliases['A6']
aliases['PGL(2,9)'] = [(10, 30), (12, 182)]
aliases['M10'] = [(10, 31), (12, 181)]
aliases['A10'] = [(10, 44)]
aliases['S10'] = [(10, 45)]
aliases['C11'] = [(11, 1)]
aliases['D11'] = [(11, 2)]
aliases['F11'] = [(11, 4)]
aliases['PSL(2,11)'] = [(11, 5), (12, 272)]
aliases['M11'] = [(11, 6)]
aliases['A11'] = [(11, 7)]
aliases['S11'] = [(11, 8)]
aliases['C12'] = [(12, 1)]
aliases['C6XC2'] = [(12, 2)]
aliases['C13'] = [(13, 1)]
aliases['C14'] = [(14, 1)]
aliases['D7'] = [(14, 2)]
aliases['D14'] = [(14, 3)]
aliases['C15'] = [(15, 1)]

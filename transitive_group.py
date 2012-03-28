import re
import pymongo

from base import app, getDBConnection
from flask import Flask, session, g, render_template, url_for, request, redirect

import sage.all
from sage.all import ZZ, latex, AbelianGroup, pari, gap

from utils import ajax_more, image_src, web_latex, to_dict, parse_range

from pymongo.connection import Connection

MAX_GROUP_DEGREE = 13

def base_label(n,t):
  return str(n)+"T"+str(t)

def group_display_short(n, t, C):
  label = base_label(n,t)
  group = C.transitivegroups.groups.find_one({'label': label})
  if group['pretty']:
    return group['pretty']
  return group['name']

def group_display_knowl(n, t, C, name=None):
  if not name:
    name = group_display_short(n, t, C)
  return '<a title = "'+ name + ' [nf.galois_group.data]" knowl="nf.galois_group.data" kwargs="n='+ str(n) + '&t='+ str(t) +'">'+name+'</a>'

def cclasses_display_knowl(n, t, C, name=None):
  if not name:
    name = 'Conjugacy class representatives for '
    name += group_display_short(n, t, C)
  return '<a title = "'+ name + ' [gg.conjugacy_classes.data]" knowl="gg.conjugacy_classes.data" kwargs="n='+ str(n) + '&t='+ str(t) +'">'+name+'</a>'

def character_table_display_knowl(n, t, C, name=None):
  if not name:
    name = 'Character table for '
    name += group_display_short(n, t, C)
  return '<a title = "'+ name + ' [gg.character_table.data]" knowl="gg.character_table.data" kwargs="n='+ str(n) + '&t='+ str(t) +'">'+name+'</a>'

def group_phrase(n,t,C):
  label = base_label(n,t)
  group = C.transitivegroups.groups.find_one({'label': label})
  inf = ''
  if group['cyc']==1:
    inf += "A cyclic"
  elif group['ab']==1:
    inf += "An abelian"
  elif group['solv']==1:
    inf += "A solvable"
  else:
    inf += "A non-solvable"
  inf += ' group of order '
  inf += str(group['order'])
  return(inf)

def group_display_long(n, t, C):
  label = base_label(n,t)
  group = C.transitivegroups.groups.find_one({'label': label})
  inf = "Group %sT%s, order %s, parity %s" % (group['n'], group['t'], group['order'], group['parity'])
  if group['cyc']==1:
    inf += ", cyclic"
  elif group['ab']==1:
    inf += ", abelian"
  elif group['solv']==1:
    inf += ", non-abelian solvable"
  else:
    inf += ", non-solvable"
  if group['prim']==1:
    inf += ", primitive"
  else:
    inf += ", imprimitive"

  inf = "  (%s)" % inf
  if group['pretty']:
    return group['pretty']+inf
  return group['name']+inf

def group_knowl_guts(n,t, C):
  label = base_label(n,t)
  group = C.transitivegroups.groups.find_one({'label': label})
  inf = "Group "+str(group['n'])+"T"+str(group['t'])
  inf += ", order "+str(group['order'])
  inf += ", parity "+str(group['parity'])
  if group['cyc']==1:
    inf += ", cyclic"
  elif group['ab']==1:
    inf += ", abelian"
  elif group['solv']==1:
    inf += ", non-abelian solvable"
  else:
    inf += ", non-solvable"
  if group['prim']==1:
    inf += ", primitive"
  else:
    inf += ", imprimitive"

  inf = "  ("+inf+")"
  rest = '<div><h3>Generators</h3><blockquote>'
  rest += generators(n, t)
  rest += '</blockquote></div>'
  
  rest += '<div><h3>Subfields</h3><blockquote>'
  rest += subfield_display(C, n, group['subs'])
  rest += '</blockquote></div>'
  rest += '<div><h3>Other representations</h3><blockquote>'
  rest += otherrep_display(C, group['repns'])
  rest += '</blockquote></div>'

  if group['pretty']:
    return group['pretty']+inf+rest
  return group['name']+inf+rest

def group_cclasses_knowl_guts(n,t, C):
  label = base_label(n,t)
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
  
def group_character_table_knowl_guts(n,t, C):
  label = base_label(n,t)
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
  if n==1:
    return 'Degree 1 - None'
  degs = ZZ(str(n)).divisors()[1:-1]
  if len(degs)==0:
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
      substrs[k[0]] += str(k[0])+'T'+str(k[1])
  for deg in degs:
    ans += '<p>Degree '+str(deg)+': '
    if substrs[deg] == '':
      substrs[deg] = 'None'
    ans += substrs[deg]+'</p>'
  return ans

def otherrep_display(C, reps):
  ans = ''
  for k in reps:
    if ans != '':
      ans += ', '
    name = str(k[0])+'T'+str(k[1])
    if k[0] <= MAX_GROUP_DEGREE:
      ans += group_display_knowl(k[0], k[1], C, name)
    else:
      ans += name
  if ans == '':
    ans = 'None'
  return ans

def resolve_display(C, resolves):
  ans = ''
  old_deg = -1
  for j in resolves:
    if j[0] != old_deg:
      if old_deg<0:
        ans += '<table>'
      else: 
        ans += '</td></tr>'
      old_deg = j[0]
      ans += '<tr><td>'+str(j[0])+': </td><td>'
    else: ans += ', '
    k = j[1]
    name = str(k[0])+'T'+str(k[1])
    if k[0] <= MAX_GROUP_DEGREE:
      ans += group_display_knowl(k[0], k[1], C, name)
    else:
      ans += name
  if ans != '': ans += '</td></tr></table>'
  else:         ans = 'None'
  return ans

def group_display_inertia(code, C):
  if str(code[1]) == "t":
    return group_display_knowl(code[2][0], code[2][1], C)
  ans = "Intransitive group isomorphic to "
  if len(code[2])>1:
    ans += group_display_short(code[2][0], code[2][1], C)
    return ans
  ans += code[3]
  return ans

  label = base_label(n,t)
  group = C.transitivegroups.groups.find_one({'label': label})
  if group['pretty']:
    return group['pretty']
  return group['name']

def conjclasses(g, n):
  gap.set('cycletype', 'function(el, n) local ct; ct := CycleLengths(el, [1..n]); ct := ShallowCopy(ct); Sort(ct); ct := Reversed(ct); return(ct); end;')
  cc = g.ConjugacyClasses()
  ccn = [x.Size() for x in cc]
  cc = [x.Representative() for x in cc]
  cc2 = [x.cycletype(n) for x in cc]
  cc2 = [str(x) for x in cc2]
  cc2 = map(lambda x: re.sub("\[",'', x),  cc2)
  cc2 = map(lambda x: re.sub("\]",'', x),  cc2)
  ans = [[cc[j], cc[j].Order(), ccn[j], cc2[j]] for j in range(len(ccn))]
  return(ans)

def cclasses (n, t):
  G = gap.TransitiveGroup(n,t)
  cc = conjclasses(G, n)
  html = """<div>
            <table class="ntdata">
            <thead><tr><td>Cycle Type</td><td>Size</td><td>Order</td><td>Representative</td></tr></thead>
            <tbody>
         """
  for c in cc:
    html += '<tr><td>' + str(c[3]) +'</td>'
    html += '<td>' + str(c[2]) +'</td>'
    html += '<td>' + str(c[1]) +'</td>'
    html += '<td>' + str(c[0]) +'</td>'
  html += """</tr></tbody>
             </table>
          """
  return html

def chartable (n, t):
  G = gap.TransitiveGroup(n,t)
  CT = G.CharacterTable()
  ctable = gap.eval("Display(%s)"%CT.name())
  ctable = re.sub("^.*\n", '', ctable)
  ctable = re.sub("^.*\n", '', ctable)
  return ctable


def generators (n, t):
  G = gap.TransitiveGroup(n,t)
  gens = G.SmallGeneratingSet()
  gens = str(gens)
  gens = re.sub("[\[\]]", '', gens)
  return gens

group_names = {}
group_names[(1, 1, 1, 1)] = ('S1','S1','C1','A1','A2','1T1')

group_names[(2, 2, -1, 1)] = ('S2','S2','C2','D1','2','2T1')

group_names[(3, 6, -1, 1)] = ('S3','S3','D3', '3T2')
group_names[(3, 3, 1, 2)] = ('A3','A3','C3','3', '3T1')

group_names[(4, 4, -1, 1)] = ('C(4) = 4','C4','4', '4T1')
group_names[(4, 4, 1, 2)] = ('E(4) = 2[x]2','V4', 'D2', 'C2xC2', '4T2')
group_names[(4, 8, -1, 3)] = ('D(4)','D4', '4T3')
group_names[(4, 12, 1, 4)] = ('A4','A4', '4T4')
group_names[(4, 24, -1, 5)] = ('S4','S4', '4T5')

group_names[(5, 5, 1, 1)] = ('C(5) = 5','C5','5','5T1')
group_names[(5, 10, 1, 2)] = ('D(5) = 5:2','D5','5T2')
group_names[(5, 20, -1, 3)] = ('F(5) = 5:4','F5','5T3')
group_names[(5, 60, 1, 4)] = ('A5','A5','5T4')
group_names[(5, 120, -1, 5)] = ('S5','S5','5T5')

group_names[(6, 6, -1, 1)] = ('C(6) = 6 = 3[x]2','C6','6','6T1')
group_names[(6, 6, -1, 2)] = ('D_6(6) = [3]2','S3gal','6T2')
group_names[(6, 12, -1, 3)] = ('D(6) = S(3)[x]2','D6','6T3')
group_names[(6, 12, 1, 4)] = ('A_4(6) = [2^2]3','A4(6)','6T4')
group_names[(6, 18, -1, 5)] = ('F_18(6) = [3^2]2 = 3 wr 2','(C3xS3)(6)', '3 wr 2', '6T5')
group_names[(6, 24, -1, 6)] = ('2A_4(6) = [2^3]3 = 2 wr 3','(A4xC2)(6)','6T6')
group_names[(6, 24, 1, 7)] = ('S_4(6d) = [2^2]S(3)','S4+','6T7')
group_names[(6, 24, -1, 8)] = ('S_4(6c) = 1/2[2^3]S(3)','S4(6)','6T8')
group_names[(6, 36, -1, 9)] = ('F_18(6):2 = [1/2.S(3)^2]2','(S3xS3)(6)','6T9')
group_names[(6, 36, 1, 10)] = ('F_36(6) = 1/2[S(3)^2]2','3^2:4','6T10')
group_names[(6, 48, -1, 11)] = ('2S_4(6) = [2^3]S(3) = 2 wr S(3)','(S4xC2)(6)','6T11')
group_names[(6, 60, 1, 12)] = ('L(6) = PSL(2,5) = A_5(6)','PSL(2,5)','6T12')
group_names[(6, 72, -1, 13)] = ('F_36(6):2 = [S(3)^2]2 = S(3) wr 2','(C3xC3):D4', '3^2:D4','6T13')
group_names[(6, 120, -1, 14)] = ('L(6):2 = PGL(2,5) = S_5(6)','S5(6)', 'PGL(2,5)','6T14')
group_names[(6, 360, 1, 15)] = ('A6','A6', '6T15')
group_names[(6, 720, -1, 16)] = ('S6','S6','6T16')

group_names[(7, 7, 1, 1)] = ('C(7) = 7','C7','7T1')
group_names[(7, 14, -1, 2)] = ('D(7) = 7:2','D7','7T2')
group_names[(7, 21, 1, 3)] = ('F_21(7) = 7:3','7:3','7T3')
group_names[(7, 42, -1, 4)] = ('F_42(7) = 7:6','7:6','7T4')
group_names[(7, 168, 1, 5)] = ('L(7) = L(3,2)','GL(3,2)','7T5')
group_names[(7, 2520, 1, 6)] = ('A7','A7','7T6')
group_names[(7, 5040, -1, 7)] = ('S7','S7','7T7')
# We converted [14, -1, 2, 'D(7) = 7:2'] and [5040, -1, 7, 'S7'] on import


group_names[(8, 8, -1, 1)] = ('C(8)=8', 'C8', '8', '8T1')
group_names[(8, 8, 1, 2)] = ('4[x]2', '8T2')
group_names[(8, 8, 1, 3)] = ('E(8)=2[x]2[x]2', '8T3')
group_names[(8, 8, 1, 4)] = ('D_8(8)=[4]2', 'D8','8T4')
group_names[(8, 8, 1, 5)] = ('Q_8(8)', '8T5')
group_names[(8, 16, -1, 6)] = ('D(8)', '8T6')
group_names[(8, 16, -1, 7)] = ('1/2[2^3]4', '8T7')
group_names[(8, 16, -1, 8)] = ('2D_8(8)=[D(4)]2', '8T8')
group_names[(8, 16, 1, 9)] = ('E(8):2=D(4)[x]2', '8T9')
group_names[(8, 16, 1, 10)] = ('[2^2]4', '8T10')
group_names[(8, 16, 1, 11)] = ('1/2[2^3]E(4)=Q_8:2', '8T11')
group_names[(8, 24, 1, 12)] = ('2A_4(8)=[2]A(4)=SL(2,3)', '8T12')
group_names[(8, 24, 1, 13)] = ('E(8):3=A(4)[x]2', '8T13')
group_names[(8, 24, 1, 14)] = ('S(4)[1/2]2=1/2(S_4[x]2)', '8T14')
group_names[(8, 32, -1, 15)] = ('[1/4.cD(4)^2]2', '8T15')
group_names[(8, 32, -1, 16)] = ('1/2[2^4]4', '8T16')
group_names[(8, 32, -1, 17)] = ('[4^2]2', '8T17')
group_names[(8, 32, 1, 18)] = ('E(8):E_4=[2^2]D(4)', '8T18')
group_names[(8, 32, 1, 19)] = ('E(8):4=[1/4.eD(4)^2]2', '8T19')
group_names[(8, 32, 1, 20)] = ('[2^3]4', '8T20')
group_names[(8, 32, -1, 21)] = ('1/2[2^4]E(4)=[1/4.dD(4)^2]2', '8T21')
group_names[(8, 32, 1, 22)] = ('E(8):D_4=[2^3]2^2', '8T22')
group_names[(8, 48, -1, 23)] = ('2S_4(8)=GL(2,3)', 'GL(2,3)', '8T23')
group_names[(8, 48, 1, 24)] = ('E(8):D_6=S(4)[x]2', '8T24')
group_names[(8, 56, 1, 25)] = ('E(8):7=F_56(8)', '8T25')
group_names[(8, 64, -1, 26)] = ('1/2[2^4]eD(4)', '8T26')
group_names[(8, 64, -1, 27)] = ('[2^4]4', '8T27')
group_names[(8, 64, -1, 28)] = ('1/2[2^4]dD(4)', '8T28')
group_names[(8, 64, 1, 29)] = ('E(8):D_8=[2^3]D(4)', '8T29')
group_names[(8, 64, -1, 30)] = ('1/2[2^4]cD(4)', '8T30')
group_names[(8, 64, -1, 31)] = ('[2^4]E(4)', '8T31')
group_names[(8, 96, 1, 32)] = ('[2^3]A(4)', '8T32')
group_names[(8, 96, 1, 33)] = ('E(8):A_4=[1/3.A(4)^2]2=E(4):6', '8T33')
group_names[(8, 96, 1, 34)] = ('1/2[E(4)^2:S_3]2=E(4)^2:D_6', '8T34')
group_names[(8, 128, -1, 35)] = ('[2^4]D(4)', '8T35')
group_names[(8, 168, 1, 36)] = ('E(8):F_21', '8T36')
group_names[(8, 168, 1, 37)] = ('L(8)=PSL(2,7)', 'PSL(2,7)', '8T37')
group_names[(8, 192, -1, 38)] = ('[2^4]A(4)', '8T38')
group_names[(8, 192, 1, 39)] = ('[2^3]S(4)', '8T39')
group_names[(8, 192, -1, 40)] = ('1/2[2^4]S(4)', '8T40')
group_names[(8, 192, 1, 41)] = ('E(8):S_4=[E(4)^2:S_3]2=E(4)^2:D_12', '8T41')
group_names[(8, 288, 1, 42)] = ('[A(4)^2]2', '8T42')
group_names[(8, 336, -1, 43)] = ('L(8):2=PGL(2,7)', 'PGL(2,7)', '8T43')
group_names[(8, 384, -1, 44)] = ('[2^4]S(4)', '8T44')
group_names[(8, 576, 1, 45)] = ('[1/2.S(4)^2]2', '8T45')
group_names[(8, 576, -1, 46)] = ('1/2[S(4)^2]2', '8T46')
group_names[(8, 1152, -1, 47)] = ('[S(4)^2]2', '8T47')
group_names[(8, 1344, 1, 48)] = ('E(8):L_7=AL(8)', '8T48')
group_names[(8, 20160, 1, 49)] = ('A8', 'A8', '8T49')
group_names[(8, 40320, -1, 50)] = ('S8', 'S8', '8T50')



# Degree 9: 
group_names[(9, 9, 1, 1)] = ('C(9)=9', 'C9', '9', '9T1')
group_names[(9, 9, 1, 2)] = ('E(9)=3[x]3', 'C3xC3', '9T2')
group_names[(9, 18, 1, 3)] = ('D(9)=9:2', 'D9', '9T3')
group_names[(9, 18, -1, 4)] = ('S(3)[x]3', 'S3xC3', '9T4')
group_names[(9, 18, 1, 5)] = ('S(3)[1/2]S(3)=3^2:2', '9T5')
group_names[(9, 27, 1, 6)] = ('1/3[3^3]3', '9T6')
group_names[(9, 27, 1, 7)] = ('E(9):3=[3^2]3', '9T7')
group_names[(9, 36, -1, 8)] = ('S(3)[x]S(3)=E(9):D_4', '9T8')
group_names[(9, 36, 1, 9)] = ('E(9):4', '9T9')
group_names[(9, 54, 1, 10)] = ('[3^2]S(3)_6', '9T10')
group_names[(9, 54, 1, 11)] = ('E(9):6=1/2[3^2:2]S(3)', '9T11')
group_names[(9, 54, -1, 12)] = ('[3^2]S(3)', '9T12')
group_names[(9, 54, -1, 13)] = ('E(9):D_6=[3^2:2]3=[1/2.S(3)^2]3', '9T13')
group_names[(9, 72, 1, 14)] = ('M(9)=E(9):Q_8', 'M9', '9T14')
group_names[(9, 72, -1, 15)] = ('E(9):8', '9T15')
group_names[(9, 72, -1, 16)] = ('E(9):D_8', '9T16')
group_names[(9, 81, 1, 17)] = ('[3^3]3=3wr3', '9T17')
group_names[(9, 108, -1, 18)] = ('E(9):D_12=[3^2:2]S(3)=[1/2.S(3)^2]S(3)', '9T18')
group_names[(9, 144, -1, 19)] = ('E(9):2D_8', '9T19')
group_names[(9, 162, -1, 20)] = ('[3^3]S(3)=3wrS(3)', '9T20')
group_names[(9, 162, 1, 21)] = ('1/2.[3^3:2]S(3)', '9T21')
group_names[(9, 162, -1, 22)] = ('[3^3:2]3', '9T22')
group_names[(9, 216, 1, 23)] = ('E(9):2A_4', '9T23')
group_names[(9, 324, -1, 24)] = ('[3^3:2]S(3)', '9T24')
group_names[(9, 324, 1, 25)] = ('[1/2.S(3)^3]3', '9T25')
group_names[(9, 432, -1, 26)] = ('E(9):2S_4', '9T26')
group_names[(9, 504, 1, 27)] = ('L(9)=PSL(2,8)', 'PSL(2,8)', '9T27')
group_names[(9, 648, -1, 28)] = ('[S(3)^3]3=S(3)wr3', '9T28')
group_names[(9, 648, -1, 29)] = ('[1/2.S(3)^3]S(3)', '9T29')
group_names[(9, 648, 1, 30)] = ('1/2[S(3)^3]S(3)', '9T30')
group_names[(9, 1296, -1, 31)] = ('[S(3)^3]S(3)=S(3)wrS(3)', '9T31')
group_names[(9, 1512, 1, 32)] = ('L(9):3=P|L(2,8)', '9T32')
group_names[(9, 181440, 1, 33)] = ('A9', 'A9', '9T33')
group_names[(9, 362880, -1, 34)] = ('S9', 'S9', '9T34')


# Degree 10:
group_names[(10, 10, -1, 1)] = ('C(10)=5[x]2', 'C10', '10', '10T1')
group_names[(10, 10, -1, 2)] = ('D(10)=5:2', '10T2')
group_names[(10, 20, -1, 3)] = ('D_10(10)=[D(5)]2', 'D10', '10T3')
group_names[(10, 20, -1, 4)] = ('1/2[F(5)]2', '10T4')
group_names[(10, 40, -1, 5)] = ('F(5)[x]2', '10T5')
group_names[(10, 50, -1, 6)] = ('[5^2]2', '10T6')
group_names[(10, 60, 1, 7)] = ('A_5(10)', '10T7')
group_names[(10, 80, 1, 8)] = ('[2^4]5', '10T8')
group_names[(10, 100, -1, 9)] = ('[1/2.D(5)^2]2', '10T9')
group_names[(10, 100, -1, 10)] = ('1/2[D(5)^2]2', '10T10')
group_names[(10, 120, -1, 11)] = ('A(5)[x]2', '10T11')
group_names[(10, 120, -1, 12)] = ('1/2[S(5)]2=S_5(10a)', '10T12')
group_names[(10, 120, -1, 13)] = ('S_5(10d)', '10T13')
group_names[(10, 160, -1, 14)] = ('[2^5]5', '10T14')
group_names[(10, 160, 1, 15)] = ('[2^4]D(5)', '10T15')
group_names[(10, 160, -1, 16)] = ('1/2[2^5]D(5)', '10T16')
group_names[(10, 200, -1, 17)] = ('[5^2:4]2', '10T17')
group_names[(10, 200, 1, 18)] = ('[5^2:4]2_2', '10T18')
group_names[(10, 200, -1, 19)] = ('[5^2:4_2]2', '10T19')
group_names[(10, 200, -1, 20)] = ('[5^2:4_2]2_2', '10T20')
group_names[(10, 200, -1, 21)] = ('[D(5)^2]2', '10T21')
group_names[(10, 240, -1, 22)] = ('S(5)[x]2', '10T22')
group_names[(10, 320, -1, 23)] = ('[2^5]D(5)', '10T23')
group_names[(10, 320, 1, 24)] = ('[2^4]F(5)', '10T24')
group_names[(10, 320, -1, 25)] = ('1/2[2^5]F(5)', '10T25')
group_names[(10, 360, 1, 26)] = ('L(10)=PSL(2,9)', 'PSL(2,9)', '10T26')
group_names[(10, 400, -1, 27)] = ('[1/2.F(5)^2]2', '10T27')
group_names[(10, 400, 1, 28)] = ('1/2[F(5)^2]2', '10T28')
group_names[(10, 640, -1, 29)] = ('[2^5]F(5)', '10T29')
group_names[(10, 720, -1, 30)] = ('L(10):2=PGL(2,9)', 'PGL(2,9)','10T30')
group_names[(10, 720, 1, 31)] = ("M(10)=L(10)'2", 'M10', '10T31')
group_names[(10, 720, -1, 32)] = ('S_6(10)=L(10):2', '10T32')
group_names[(10, 800, -1, 33)] = ('[F(5)^2]2', '10T33')
group_names[(10, 960, 1, 34)] = ('[2^4]A(5)', '10T34')
group_names[(10, 1440, -1, 35)] = ('L(10).2^2=P|L(2,9)', '10T35')
group_names[(10, 1920, -1, 36)] = ('[2^5]A(5)', '10T36')
group_names[(10, 1920, 1, 37)] = ('[2^4]S(5)', '10T37')
group_names[(10, 1920, -1, 38)] = ('1/2[2^5]S(5)', '10T38')
group_names[(10, 3840, -1, 39)] = ('[2^5]S(5)', '10T39')
group_names[(10, 7200, -1, 40)] = ('[A(5)^2]2', '10T40')
group_names[(10, 14400, -1, 41)] = ('[1/2.S(5)^2]2=[A(5):2]2', '10T41')
group_names[(10, 14400, 1, 42)] = ('1/2[S(5)^2]2', '10T42')
group_names[(10, 28800, -1, 43)] = ('[S(5)^2]2', '10T43')
group_names[(10, 1814400, 1, 44)] = ('A10', 'A10', '10T44')
group_names[(10, 3628800, -1, 45)] = ('S10', 'S10', '10T45')

# Degree 11:
group_names[(11, 11, 1, 1)] = ('C(11)=11', 'C11', '11T1')
group_names[(11, 22, -1, 2)] = ('D(11)=11:2', 'D11', '11T2')
group_names[(11, 55, 1, 3)] = ('F_55(11)=11:5', '11:5','11T3')
group_names[(11, 110, -1, 4)] = ('F_110(11)=11:10', 'F11','11:10', '11T4')
group_names[(11, 660, 1, 5)] = ('L(11)=PSL(2,11)(11)', 'PSL(2,11)', '11T5')
group_names[(11, 7920, 1, 6)] = ('M(11)', 'M11', '11T6')
group_names[(11, 19958400, 1, 7)] = ('A11', 'A11', '11T7')
group_names[(11, 39916800, -1, 8)] = ('S11', 'S11', '11T8')


groups = [{'label':list(g),'gap_name':group_names[g][0],'human_name':', '.join(group_names[g][1:])} for g in group_names.keys()]

abelian_group_names = ('S1','C1','D1','A1','A2') + ('S2','C2') + ('A3','C3') + ('C(4) = 4','C4') + ('C(5) = 5','C5') + ('C(6) = 6 = 3[x]2','C6') + ('C(7) = 7','C7') + ('C(8)=8','C8') + ('4[x]2',) + ('C(9)=9','C9') + ('C3xC3',) + ('C10',) + ('C11',)

def complete_group_code(c):
    for g in group_names.keys():
        if c in group_names[g]:
            return list(g)[1:]+[group_names[g][0]]
    try:
        if (c[0]=='[' and c[-1]==']') or (c[0]=='(' and c[-1]==')'):
            c = parse_list(c)
            return c[1:]+[group_names[tuple(c)][0]]
    except (KeyError, NameError, ValueError):
        return 0

def GG_data(GGlabel):
    GG = complete_group_code(GGlabel)
    order = GG[0]
    sign = GG[1]
    ab = GGlabel in abelian_group_names
    return order,sign,ab
 
#    data['galois_group'] = str(data['galois_group'][3])
#    Gorder,Gsign,Gab = GG_data(data['galois_group'])
#    if Gab:
#        Gab='abelian'
#    else:
#        Gab='non-abelian'

#for j in group_names.keys():
#  for k in group_names[j]:
#    if re.search('^\s*\d+T\d+\s*$', k) == None and re.search('^\s*\d+\s*$',k) ==  None:
#      newv = (j[0], j[3])
#      print "aliases['"+str(k)+"'] = ", newv



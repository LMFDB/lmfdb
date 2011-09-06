import re
import pymongo

from base import app
from flask import Flask, session, g, render_template, url_for, request, redirect

import sage.all
from sage.all import ZZ, QQ, PolynomialRing, NumberField, CyclotomicField, latex, AbelianGroup, euler_phi, pari

from utils import ajax_more, image_src, web_latex, to_dict, parse_range, coeff_to_poly, pol_to_html

NF_credit = 'the PARI group,  J. Voight and J. Jones'

def field_pretty(field_str):
    d,r,D,i = field_str.split('.')
    if d == '1':  # Q
        return '\( {\mathbb Q} \)'
    if d == '2':  # quadratic field
        D = ZZ(D).squarefree_part()
        if r=='0': D = -D
        return '\( {\mathbb Q}(\sqrt{' + str(D) + '}) \)'
    for n in [5,7,8,9,10]: 
        if field_str==parse_field_string('Qzeta'+str(n)):
            return '\( {\mathbb Q}(\zeta_%s) \)'%n
    return field_str
#    TODO:  pretty-printing of more fields of higher degree

def poly_to_field_label(pol):
    try:
        pol=PolynomialRing(QQ,'x')(str(pol))
        pol *= pol.denominator()
        R = pol.parent()
        pol = R(pari(pol).polredabs())
    except:
        return None
    coeffs = [int(c) for c in pol.coeffs()]
    d = int(pol.degree())
    query = {'degree': d, 'coefficients': coeffs}
    import base
    C = base.getDBConnection()
    one = C.numberfields.fields.find_one(query)
    if one:
        return one['label']
    return None

    
def parse_field_string(F): # parse Q, Qsqrt2, Qsqrt-4, Qzeta5, etc
    if F=='Q': return '1.1.1.1'
    fail_string = str(F + ' is not a valid field label or name or polynomial, or is not ')
    if F[0]=='Q':
        if F[1:5] in ['sqrt','root']:
            try:
                d=ZZ(str(F[5:])).squarefree_part()
            except ValueError:
                return fail_string
            if d%4 in [2,3]:
                D=4*d
            else:
                D=d
            absD = D.abs()
            s=0 if D<0 else 2
            return '2.%s.%s.1'%(s,str(absD))
        if F[1:5]=='zeta':
            try:
                d=ZZ(str(F[5:]))
            except ValueError:
                return fail_string
            if d<1: return fail_string
            if d%4==2: d/=2  # Q(zeta_6)=Q(zeta_3), etc)
            if d==1: return '1.1.1.1'
            deg = euler_phi(d)
            if deg>20:
                return fail_string
            adisc = CyclotomicField(d).discriminant().abs() # uses formula!
            return '%s.0.%s.1'%(deg,adisc)
        return fail_string
    # check if a polynomial was entered
    F=F.replace('X','x')
    if 'x' in F:
        F=F.replace('^','**')
        print F
        F = poly_to_field_label(F)
        if F:
            return F
        return fail_string
    return F

@app.route("/NF")
def NF_redirect():
    return redirect(url_for("number_field_render_webpage", **request.args))

# function copied from classical_modular_form.py
def set_sidebar(l):
        res=list()
#       print "l=",l
        for ll in l:
                if(len(ll)>1):
                        content=list()
                        for n in range(1,len(ll)):
                                content.append(ll[n])
                        res.append([ll[0],content])
#       print "res=",res
        return res


@app.route("/NumberField/GaloisGroups")
def render_groups_page():
    info = {}
    info['learnmore'] = [('Number Field labels', url_for("render_labels_page")), ('Galois group labels',url_for("render_groups_page")), ('Discriminant ranges',url_for("render_discriminants_page"))]
    def gcmp(x,y):
        a = cmp(x['label'][0],y['label'][0])
        if a: return a
        a = cmp(x['label'][1],y['label'][1])
        return a
    groups.sort(cmp=gcmp)
    t = 'Galois group labels'
    bread = [('Number Fields', url_for("number_field_render_webpage")),('Galois group labels',' ')]
    return render_template("number_field/galois_groups.html", groups=groups, info=info, credit=NF_credit, title=t, bread=bread)

@app.route("/NumberField/FieldLabels")
def render_labels_page():
    info = {}
    info['learnmore'] = [('Number Field labels', url_for("render_labels_page")), ('Galois group labels',url_for("render_groups_page")), ('Discriminant ranges',url_for("render_discriminants_page"))]
    t = 'Number field labels'
    bread = [('Number Fields', url_for("number_field_render_webpage")),('Number field labels','')]
    return render_template("number_field/number_field_labels.html", info=info, credit=NF_credit, title=t, bread=bread)

@app.route("/NumberField/Discriminants")
def render_discriminants_page():
    info = {}
    info['learnmore'] = [('Number Field labels', url_for("render_labels_page")), ('Galois group labels',url_for("render_groups_page")), ('Discriminant ranges',url_for("render_discriminants_page"))]
    t = 'Number Field Discriminant Ranges'
    bread = [('Number Fields', url_for("number_field_render_webpage")),('Discriminant ranges',' ')]
    return render_template("number_field/discriminant_ranges.html", info=info, credit=NF_credit, title=t, bread=bread)

@app.route("/NumberField")
def number_field_render_webpage():
    args = request.args
    sig_list = sum([[[d-2*r2,r2] for r2 in range(1+(d//2))] for d in range(1,7)],[]) + sum([[[d,0]] for d in range(7,11)],[])
    sig_list = sig_list[:10]
    if len(args) == 0:      
        discriminant_list_endpoints = [-10000,-1000,-100,0,100,1000,10000]
        discriminant_list = ["%s..%s" % (start,end-1) for start, end in zip(discriminant_list_endpoints[:-1], discriminant_list_endpoints[1:])]
        info = {
        'degree_list': range(1,11),
        'signature_list': sig_list, 
        'class_number_list': range(1,6)+['6..10'],
        'discriminant_list': discriminant_list
    }
        t = 'Number Fields'
        bread = [('Number Fields', url_for("number_field_render_webpage"))]
        info['learnmore'] = [('Number Field labels', url_for("render_labels_page")), ('Galois group labels',url_for("render_groups_page")), ('Discriminant ranges',url_for("render_discriminants_page"))]

        return render_template("number_field/number_field_all.html", info = info, credit=NF_credit, title=t, bread=bread)
    else:
        return number_field_search(**args)

def coeff_to_nf(c):
    return NumberField(coeff_to_poly(c), 'a')

def sig2sign(sig):
    return [1,-1][sig[1]%2]

group_names = {}
group_names[(1, 1, 1, 1)] = ('S1','S1','C1','A1','A2','1T1')

group_names[(2, 2, -1, 1)] = ('S2','S2','C2','D1','2','2T1')

group_names[(3, 6, -1, 1)] = ('S3','S3','D3', '3T2')
group_names[(3, 3, 1, 2)] = ('A3','A3','C3','3', '3T1')

group_names[(4, 4, -1, 1)] = ('C(4) = 4','C4','4', '4T1')
group_names[(4, 4, 1, 1)] = ('E(4) = 2[x]2','V4', 'D2', 'C2xC2', '4T2')
group_names[(4, 8, -1, 1)] = ('D(4)','D4', '4T3')
group_names[(4, 12, 1, 1)] = ('A4','A4', '4T4')
group_names[(4, 24, -1, 1)] = ('S4','S4', '4T5')

group_names[(5, 5, 1, 1)] = ('C(5) = 5','C5','5','5T1')
group_names[(5, 10, 1, 1)] = ('D(5) = 5:2','D5','5T2')
group_names[(5, 20, -1, 1)] = ('F(5) = 5:4','F5','5T3')
group_names[(5, 60, 1, 1)] = ('A5','A5','5T4')
group_names[(5, 120, -1, 1)] = ('S5','S5','5T5')

group_names[(6, 6, -1, 1)] = ('C(6) = 6 = 3[x]2','C6','6','6T1')
group_names[(6, 6, -1, 2)] = ('D_6(6) = [3]2','S3gal','6T2')
group_names[(6, 12, -1, 1)] = ('D(6) = S(3)[x]2','D6','6T3')
group_names[(6, 12, 1, 1)] = ('A_4(6) = [2^2]3','A4(6)','6T4')
group_names[(6, 18, -1, 1)] = ('F_18(6) = [3^2]2 = 3 wr 2','(C3xS3)(6)', '3 wr 2', '6T5')
group_names[(6, 24, -1, 2)] = ('2A_4(6) = [2^3]3 = 2 wr 3','(A4xC2)(6)','6T6')
group_names[(6, 24, 1, 1)] = ('S_4(6d) = [2^2]S(3)','S4+','6T7')
group_names[(6, 24, -1, 1)] = ('S_4(6c) = 1/2[2^3]S(3)','S4(6)','6T8')
group_names[(6, 36, -1, 1)] = ('F_18(6):2 = [1/2.S(3)^2]2','(S3xS3)(6)','6T9')
group_names[(6, 36, 1, 1)] = ('F_36(6) = 1/2[S(3)^2]2','3^2:4','6T10')
group_names[(6, 48, -1, 1)] = ('2S_4(6) = [2^3]S(3) = 2 wr S(3)','(S4xC2)(6)','6T11')
group_names[(6, 60, 1, 1)] = ('L(6) = PSL(2,5) = A_5(6)','PSL(2,5)','6T12')
group_names[(6, 72, -1, 1)] = ('F_36(6):2 = [S(3)^2]2 = S(3) wr 2','(C3xC3):D4', '3^2:D4','6T13')
group_names[(6, 120, -1, 1)] = ('L(6):2 = PGL(2,5) = S_5(6)','S5(6)', 'PGL(2,5)','6T14')
group_names[(6, 360, 1, 1)] = ('A6','A6', '6T15')
group_names[(6, 720, -1, 1)] = ('S6','S6','6T16')

group_names[(7, 7, 1, 1)] = ('C(7) = 7','C7','7T1')
group_names[(7, 14, -1, 1)] = ('D(7) = 7:2','D7','7T2')
group_names[(7, 21, 1, 1)] = ('F_21(7) = 7:3','7:3','7T3')
group_names[(7, 42, -1, 1)] = ('F_42(7) = 7:6','7:6','7T4')
group_names[(7, 168, 1, 1)] = ('L(7) = L(3,2)','GL(3,2)','7T5')
group_names[(7, 2520, 1, 1)] = ('A7','A7','7T6')
group_names[(7, 5040, -1, 1)] = ('S7','S7','7T7')
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
group_names[(11, 11, 1, 1)] = ('C(11)=11', 'C11', '11', '11T1')
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
 
def render_field_webpage(args):
    data = None
    if 'label' in args:
        label = str(args['label'])
        import base
        C = base.getDBConnection()
        data = C.numberfields.fields.find_one({'label': label})
    if data is None:
        return "No such field: " + label + " in the database"  
    info = {}

    try:
        info['count'] = args['count']
    except KeyError:
        info['count'] = 10
    K = coeff_to_nf(data['coefficients'])
    D = data['discriminant']
    h = data['class_number']
    data['galois_group'] = str(data['galois_group'][3])
    data['class_group_invs'] = data['class_group']
    if data['class_group_invs']==[]:
        data['class_group_invs']='Trivial'
    data['class_group'] = str(AbelianGroup(data['class_group']))
    sig = data['signature']
    D = ZZ(data['discriminant'])
    ram_primes = D.prime_factors()
    npr = len(ram_primes)
    ram_primes = str(ram_primes)[1:-1]
    Gorder,Gsign,Gab = GG_data(data['galois_group'])
    if Gab:
        Gab='abelian'
    else:
        Gab='non-abelian'
    unit_rank = sig[0]+sig[1]-1
    if unit_rank==0:
        reg = 1
    else:
        reg = K.regulator()
    UK = K.unit_group()
    
    info.update(data)
    info.update({
        'label': field_pretty(label),
        'polynomial': web_latex(K.defining_polynomial()),
        'ram_primes': ram_primes,
        'integral_basis': web_latex(K.integral_basis()),
        'regulator': web_latex(reg),
        'unit_rank': unit_rank,
        'root_of_unity': web_latex(UK.torsion_generator()),
        'fund_units': ',&nbsp; '.join([web_latex(u) for u in UK.fundamental_units()]),
        'Gorder': Gorder, 'Gsign': Gsign, 'Gab': Gab
        })
    info['downloads_visible'] = True
    info['downloads'] = [('worksheet', '/')]
#    info['friends'] = [('L-function', '/')]
    info['friends'] = [('L-function', "/L/NumberField/%s" % label)]
    info['learnmore'] = [('Number Field labels', url_for("render_labels_page")), ('Galois group labels',url_for("render_groups_page")), ('Discriminant ranges',url_for("render_discriminants_page"))]
    bread = [('Number Fields', url_for("number_field_render_webpage")),('%s'%info['label'],' ')]
    t = "Number Field %s" % info['label']

    properties = ['<br>']
    properties.extend('<table>')
    properties.extend('<tr><td align=left><b>Degree:</b><td align=left> %s</td>'%data['degree'])
    properties.extend('<tr><td align=left><b>Signature:</b><td align=left>%s</td>'%data['signature'])
    properties.extend('<tr><td align=left><b>Discriminant:</b><td align=left>%s</td>'%data['discriminant'])
    if npr==1:
        properties.extend('<tr><td align=left><b>Ramified prime:</b><td align=left>%s</td>'%ram_primes)
    else:
        if npr==0:
            properties.extend('<tr><td align=left><b>Ramified primes:</b><td align=left>%s</td>'%"None")
        else:
            properties.extend('<tr><td align=left><b>Ramified primes:</b><td align=left>%s</td>'%ram_primes)
    properties.extend('<tr><td align=left><b>Class number:</b><td align=left>%s</td>'%data['class_number'])
    properties.extend('<tr><td align=left><b>Class group:</b><td align=left>%s</td>'%data['class_group_invs'])
    properties.extend('<tr><td align=left><b>Galois group:</b><td align=left>%s</td>'%data['galois_group'])
    properties.extend('</table>')
    del info['_id']
    return render_template("number_field/number_field.html", properties=properties, credit=NF_credit, title = t, bread=bread, friends=info.pop('friends'), info=info )

def format_coeffs(coeffs):
    return pol_to_html(str(coeff_to_poly(coeffs)))
#    return web_latex(coeff_to_poly(coeffs))


@app.route("/NumberField")
def number_fields():
    if len(request.args) != 0:
        return number_field_search(**request.args)
    info['learnmore'] = [('Number Field labels', url_for("render_labels_page")), ('Galois group labels',url_for("render_groups_page")), ('Discriminant ranges',url_for("render_discriminants_page"))]
    return render_template("number_field/number_field_all.html", info = info)
    

@app.route("/NumberField/<label>")
def by_label(label):
    return render_field_webpage({'label' : label})

def parse_list(L):  
    return [int(a) for a in str(L)[1:-1].split(',')]
    # return eval(str(L)) works but using eval() is insecure

def number_field_search(**args):
    info = to_dict(args)
    if 'natural' in info:
        field_id = info['natural']
        field_id = parse_field_string(info['natural'])
        return render_field_webpage({'label' : field_id})
    query = {}
    for field in ['degree', 'signature', 'discriminant', 'class_number', 'class_group', 'galois_group']:
        if info.get(field):
            if field in ['class_group', 'signature']:
                query[field] = parse_list(info[field])
            else:
                if field == 'galois_group':
                    query[field] = complete_group_code(info[field])
                else:
                    ran = info[field]
                    ran = ran.replace('..','-')
                    query[field] = parse_range(ran)
    if info.get('ur_primes'):
        ur_primes = [int(a) for a in str(info['ur_primes']).split(',')]
    else:
        ur_primes = []

    if info.get('count'):        
        try:
            count = int(info['count'])
        except:
            count = 10
    else:
        info['count'] = 10
        count = 10

    if info.get('start'):
        try:
            start = int(info['start'])
            if(start < 0): start += (1-(start+1)/count)*count
        except:
            start = 0
    else:
        start = 0



    info['query'] = dict(query)
    if 'lucky' in args:
        import base
        C = base.getDBConnection()
        one = C.numberfields.fields.find_one(query)
        if one:
            label = one['label']
            return render_field_webpage({'label': label})

    if 'discriminant' in query:
        import base
        C = base.getDBConnection()
        res = C.numberfields.fields.find(query).sort([('degree',pymongo.ASCENDING),('signature',pymongo.DESCENDING),('discriminant',pymongo.ASCENDING)]) # TODO: pages
        nres = res.count()
    else:
        # find matches with negative discriminant:
        neg_query = dict(query)
        neg_query['discriminant'] = {'$lt':0}
        import base
        C = base.getDBConnection()
        res_neg = C.numberfields.fields.find(neg_query).sort([('degree',pymongo.ASCENDING),('discriminant',pymongo.DESCENDING)])
        nres_neg = res_neg.count()
        # TODO: pages

        # find matches with positive discriminant:
        pos_query = dict(query)
        pos_query['discriminant'] = {'$gt':0}
        import base
        C = base.getDBConnection()
        res_pos = C.numberfields.fields.find(pos_query).sort([('degree',pymongo.ASCENDING),('discriminant',pymongo.ASCENDING)])
        nres_pos = res_pos.count()
        # TODO: pages

        res = merge_sort(iter(res_neg),iter(res_pos))
        nres = nres_pos+nres_neg
        
    if ur_primes:
        res = filter_ur_primes(res, ur_primes)

    if(start>=nres): start-=(1+(start-nres)/count)*count
    if(start<0): start=0

    res = iter_limit(res,count,start)
        
    info['fields'] = res
    info['number'] = nres
    info['start'] = start
    if nres==1:
        info['report'] = 'unique match'
    else:
        if nres>count or start!=0:
            info['report'] = 'displaying matches %s-%s of %s'%(start+1,min(nres,start+count),nres)
        else:
            info['report'] = 'displaying all %s matches'%nres
    info['format_coeffs'] = format_coeffs
    info['learnmore'] = [('Number Field labels', url_for("render_labels_page")), ('Galois group labels',url_for("render_groups_page")), ('Discriminant ranges',url_for("render_discriminants_page"))]
    t = 'Number Field search results'
    bread = [('Number Fields', url_for("number_field_render_webpage")),('Search results',' ')]
    properties = []
    return render_template("number_field/number_field_search.html", info = info, title=t, properties=properties, bread=bread)


def iter_limit(it,lim,skip):
    count = 0
    while count<skip:
        it.next()
        count += 1
    count = 0
    while count<lim:
        yield it.next()
        count += 1
    return

                   
def merge_sort(it1,it2):
    try:
        a = it1.next()
    except StopIteration:
        b = it2.next()
        while True:
            yield b
            b = it2.next()
        return
    
    try:
        b = it2.next()
    except StopIteration:
        a = it1.next()
        while True:
            yield a
            a = it1.next()
        return
                
    while True:
        if abs(a['discriminant'])<abs(b['discriminant']):
            yield a
            try:
                a = it1.next()
            except StopIteration:
                b = it2.next()
                while True:
                    yield b
                    b = it2.next()
                return
        else:
            yield b
            try:
                b = it2.next()
            except StopIteration:
                a = it1.next()
                while True:
                    yield a
                    a = it1.next()
                return
    return

def support_is_disjoint(D,plist):
    D = ZZ(D)
    for p in plist:
        if ZZ(p).divides(D):
            return False
    return True

def filter_ur_primes(it, ur_primes):
    a = it.next()
    D = a['discriminant']
    while True:
        if support_is_disjoint(D,ur_primes):
            yield a
        a = it.next()
        D = a['discriminant']
    return
    
# obsolete old function:                    
def old_merge(it1,it2,lim):
    count=0
    try:
        a = it1.next()
    except StopIteration:
        for b in it2:
            if count==lim:
                return
            yield b
            count += 1
        return
    try:
        b = it2.next()
    except StopIteration:
        for a in it1:
            if count==lim:
                return
            yield a
            count += 1
        return

    while count<lim:
        if abs(a['discriminant'])<abs(b['discriminant']):
            yield a
            count += 1
            try:
                a = it1.next()
            except StopIteration:
                for b in it2:
                    if count==lim:
                        return
                    yield b
                    count += 1
                return
        else:
            yield b
            count += 1
            try:
                b = it2.next()
            except StopIteration:
                for a in it1:
                    if count==lim:
                        return
                    yield a
                    count += 1
                return

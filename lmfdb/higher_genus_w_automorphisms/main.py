# -*- coding: utf-8 -*-
# This Blueprint is about Higher Genus Curves
# Author: Jen Paulhus (copied from John Jones Local Fields)

import re
import pymongo
import ast
ASC = pymongo.ASCENDING
import yaml
import os
from lmfdb import base
from flask import render_template, request, url_for, make_response, redirect
from lmfdb.utils import to_dict, random_value_from_collection, flash_error
from lmfdb.search_parsing import search_parser, parse_ints, parse_count, parse_start, clean_input
BRACKETED_POSINT_RE = re.compile(r'^\[\]|\[\d+(,\d+)*\]$')

from sage.all import Permutation
from lmfdb.higher_genus_w_automorphisms import higher_genus_w_automorphisms_page
from lmfdb.sato_tate_groups.main import sg_pretty


# Determining what kind of label
family_label_regex = re.compile(r'(\d+)\.(\d+-\d+)\.(\d+\.\d+-[^\.]*$)')
passport_label_regex = re.compile(r'((\d+)\.(\d+-\d+)\.(\d+\.\d+.*))\.(\d+)')
cc_label_regex = re.compile(r'((\d+)\.(\d+-\d+)\.(\d+)\.(\d+.*))\.(\d+)')

def label_is_one_family(lab):
    return family_label_regex.match(lab)

def label_is_one_passport(lab):
    return passport_label_regex.match(lab)


def split_family_label(lab):
    return family_label_regex.match(lab).groups()


def split_passport_label(lab):
    return passport_label_regex.match(lab).groups()



def get_bread(breads=[]):
    bc = [("Higher Genus", url_for(".index")),("C", url_for(".index")),("Aut", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def tfTOyn(bool):
    if bool:
        return "Yes"
    else:
        return "No"
    
        
def sign_display(L):
    sizeL = len(L)                
    signL = "[ " + str(L[0]) + "; "
    for i in range(1,sizeL-1):
        signL= signL + str(L[i]) + ", "                    
     
    signL=signL + str(L[sizeL-1]) + " ]"                  
    return signL                

def cc_display(L):
    sizeL = len(L)
    stg = str(L[0])+ ", "
    for i in range(1,sizeL-1):
        stg =stg + str(L[i])+", "
    stg=stg+ str(L[sizeL-1])
    return stg


#for splitting permutations cycles
sep=' ' 

def split_perm(strg):
    startpoint = 0
    for i in range(0,len(strg)):
        if strg[i] == ")":
            yield strg[startpoint:i+1]
            startpoint = i+1

def signature_to_list(L):
    for i in range(0,len(L)):
        if L[i] == ';':
            newsig = L[:i] + "," + L[i+1:]
            return newsig
    return L


def sort_sign(L):
    L1 = L[1:]
    L1.sort()
    return [L[0]] +L1

def label_to_breadcrumbs(L):
    newsig = '['
    for i in range(0,len(L)):
        if (L[i] == '-'):
            newsig += ","
        elif (L[i] == '.'):
            newsig += ';'
        else:    
            newsig += L[i]
            
    newsig += ']'    
    return newsig



#copied from parse_bracketed_posints,  but keeps outside brackets in string
@search_parser(clean_info=True) # see SearchParser.__call__ for actual arguments when calling
def parse_bracketed_posints2(inp, query, qfield, maxlength=None, exactlength=None, split=True, process=None, check_divisibility=None):
    if process is None: process = lambda x: x
    if (not BRACKETED_POSINT_RE.match(inp) or
        (maxlength is not None and inp.count(',') > maxlength - 1) or
        (exactlength is not None and inp.count(',') != exactlength - 1) or
        (exactlength is not None and inp == '[]' and exactlength > 0)):
        if exactlength == 2:
            lstr = "pair of integers"
            example = "[2,3] or [3,3]"
        elif exactlength == 1:
            lstr = "list of 1 integer"
            example = "[2]"
        elif exactlength is not None:
            lstr = "list of %s integers" % exactlength
            example = str(range(2,exactlength+2)).replace(" ","") + " or " + str([3]*exactlength).replace(" ","")
        elif maxlength is not None:
            lstr = "list of at most %s integers" % maxlength
            example = str(range(2,maxlength+2)).replace(" ","") + " or " + str([2]*max(1, maxlength-2)).replace(" ","")
        else:
            lstr = "list of integers"
            example = "[1,2,3] or [5,6]"
        raise ValueError("It needs to be a %s in square brackets, such as %s." % (lstr, example))
    else:
        if inp == '[]': # fixes bug in the code below (split never returns an empty list)
            query[qfield] = []
            return
        if check_divisibility == 'decreasing':
            # Check that each entry divides the previous
            L = [int(a) for a in inp[1:-1].split(',')]
            for i in range(len(L)-1):
                if L[i] % L[i+1] != 0:
                    raise ValueError("Each entry must divide the previous, such as [4,2].")
        elif check_divisibility == 'increasing':
            # Check that each entry divides the previous
            L = [int(a) for a in inp[1:-1].split(',')]
            for i in range(len(L)-1):
                if L[i+1] % L[i] != 0:
                    raise ValueError("Each entry must divide the next, such as [2,4].")
        if split:
#            query[qfield] = [process(int(a)) for a in inp[1:-1].split(',')]
            query[qfield] = [process(int(a)) for a in inp.split(',')]
        else:
#            query[qfield] = inp[1:-1]
            query[qfield] = inp

    
@higher_genus_w_automorphisms_page.route("/")
def index():
    bread = get_bread()
    if request.args:
        return higher_genus_w_automorphisms_search(**request.args)

    C = base.getDBConnection()
    genus_max = C.curve_automorphisms.passports.find().sort('genus', pymongo.DESCENDING).limit(1)[0]['genus']  + 1
    genus_list = range(2,genus_max)
    info = {'count': 20,'genus_list': genus_list}
    

    learnmore = [('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]
    
    return render_template("hgcwa-index.html", title="Families of Higher Genus Curves with Automorphisms", bread=bread, info=info, learnmore=learnmore)




@higher_genus_w_automorphisms_page.route("/random")
def random_passport():
    C = base.getDBConnection()
    label = random_value_from_collection(C.curve_automorphisms.passports,'passport_label')
    return redirect(url_for(".by_passport_label", passport_label=label))



@higher_genus_w_automorphisms_page.route("/<label>")
def by_label(label):

    if label_is_one_passport(label):
        return render_passport({'passport_label': label})
    elif label_is_one_family(label):
        return render_family({'label': label})    
    else:
        flash_error( "No family with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    

@higher_genus_w_automorphisms_page.route("/<passport_label>")
def by_passport_label(label):
    return render_passport({'passport_label': label})


def higher_genus_w_automorphisms_search(**args):
    info = to_dict(args)
    bread = get_bread([("Search results",'')])
    C = base.getDBConnection()
    query = {}
    if 'jump_to' in info:
        labs = info['jump_to']
        if label_is_one_passport(labs):
            return render_passport({'passport_label': labs})
        elif label_is_one_family(labs):
            return render_family({'label': labs})
        else:
            flash_error ("The label %s is not a legitimate label for this data.",labs)
            return redirect(url_for(".index"))


#allows for ; in signature
    if 'signature' in info and info['signature'] != '':
        sig_list = ast.literal_eval(signature_to_list(info['signature']))
        sig =  sort_sign(sig_list)
        info.update({'signature': str(sig)})
            
    try:
        parse_bracketed_posints2(info,query,'group', split=False, exactlength=2, name='Group')
        parse_ints(info,query,'genus',name='Genus')
        parse_bracketed_posints2(info,query,'signature',split=False,name='Signature')
        parse_ints(info,query,'dim',name='Dimension of the family')
        if 'inc_hyper' in info:
            if info['inc_hyper'] == 'exclude':
                query['hyperelliptic'] = False
            elif info['inc_hyper'] == 'only':
                query['hyperelliptic'] = True

        query['cc.1'] = 1       

    except ValueError:
        return search_input_error(info, bread)
    count = parse_count(info)
    start = parse_start(info)
    
    res = C.curve_automorphisms.passports.find(query).sort([(
         'genus', pymongo.ASCENDING), ('dim', pymongo.ASCENDING),
        ('cc'[0],pymongo.ASCENDING)])
    nres = res.count()
    res = res.skip(start).limit(count)

    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0

        
    L = [ ]    
    for field in res:
        field['signature'] = ast.literal_eval(field['signature'])    
        L.append(field)
        
    info['fields'] = L    
    info['number'] = nres
    info['group_display'] = sg_pretty

    info['sign_display'] = sign_display
    info['start'] = start
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(
                               nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres

    return render_template("hgcwa-search.html", info=info, title="Families of Higher Genus Curves with Automorphisms Search Result", bread=bread)



def render_family(args):
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        C = base.getDBConnection()
        dataz = C.curve_automorphisms.passports.find({'label': label})
        if dataz.count() is 0:
            flash_error( "No family with label %s was found in the database.", label)
            return redirect(url_for(".index"))
        data=dataz[0]
        g = data['genus']
        GG = ast.literal_eval(data['group'])
        gn = GG[0]
        gt = GG[1]

        gp_string=str(gn) + '.' + str(gt)
        pretty_group=sg_pretty(gp_string)

        if gp_string == pretty_group:
            spname=False
        else:
            spname=True
        title = 'Family of genus ' + str(g) + ' curves with automorphism group $' + pretty_group +'$'
        smallgroup="[" + str(gn) + "," +str(gt) +"]"   

        prop2 = [
            ('Genus', '\(%d\)' % g),
            ('Group', '\(%s\)' %  pretty_group),
            ('Signature', '\(%s\)' % sign_display(ast.literal_eval(data['signature'])))
        ]
        info.update({'genus': data['genus'],
                    'sign': sign_display(ast.literal_eval(data['signature'])),   
                     'group': pretty_group,
                    'g0':data['g0'],
                    'dim':data['dim'],
                    'r':data['r'],
                    'gpid': smallgroup
                   })

        if spname:
            info.update({'specialname': True})

        Lcc=[]
        Lall=[]
        i=1
        for dat in dataz:
            if ast.literal_eval(dat['con']) not in Lcc:
                urlstrng=dat['passport_label']
                Lcc.append(ast.literal_eval(dat['con']))
                Lall.append([cc_display(ast.literal_eval(dat['con'])),dat['passport_label'],
                             urlstrng])
                i=i+1
            
        info.update({'passport': Lall})


        g2List = ['[2,1]','[4,2]','[8,3]','[10,2]','[12,4]','[24,8]','[48,29]']
        if g  == 2 and data['group'] in g2List:
            g2url = "/Genus2Curve/Q/?geom_aut_grp_id=" + data['group']
            friends = [("Genus 2 curves over $\Q$", g2url ) ]
        else:    
            friends = [ ]
        

        br_g, br_gp, br_sign = split_family_label(label)
        
        bread_sign = label_to_breadcrumbs(br_sign)
        bread_gp = label_to_breadcrumbs(br_gp)
       
        bread = get_bread([(br_g, './?genus='+br_g),('$'+pretty_group+'$','./?genus='+br_g + '&group='+bread_gp), (bread_sign,' ')])
        learnmore =[('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]
        
        downloads = [('Download Magma code', url_for(".hgcwa_code_download",  label=label, download_type='magma')),
                     ('Download Gap code', url_for(".hgcwa_code_download", label=label, download_type='gap'))]
        
        return render_template("hgcwa-show-family.html", 
                               title=title, bread=bread, info=info,
                               properties2=prop2, friends=friends,
                               learnmore=learnmore, downloads=downloads)


def render_passport(args):
    info = {}
    if 'passport_label' in args:
        label =clean_input(args['passport_label'])
        
        C = base.getDBConnection()
        
        dataz = C.curve_automorphisms.passports.find({'passport_label': label})
        if dataz.count() is 0:
            bread = get_bread([("Search error", url_for('.search'))])
            flash_error( "No refined passport with label %s was found in the database.", label)
            return redirect(url_for(".index"))
        data=dataz[0]
        g = data['genus']
        GG = ast.literal_eval(data['group'])
        gn = GG[0]
        gt = GG[1]

        gp_string=str(gn) + '.' + str(gt)
        pretty_group=sg_pretty(gp_string)

        if gp_string == pretty_group:
            spname=False
        else:
            spname=True

        numb = dataz.count()

        title = 'One refined passport of genus ' + str(g) + ' with automorphism group $' + pretty_group +'$'
        smallgroup="[" + str(gn) + "," +str(gt) +"]"   

        prop2 = [
            ('Genus', '\(%d\)' % g),
            ('Small Group', '\(%s\)' %  pretty_group),
            ('Signature', '\(%s\)' % sign_display(ast.literal_eval(data['signature']))),
            ('Generating Vectors','\(%d\)' % numb)
        ]
        info.update({'genus': data['genus'],
                    'cc': cc_display(data['con']), 
                    'sign': sign_display(ast.literal_eval(data['signature'])),   
                     'group': pretty_group,
                     'gpid': smallgroup
                   })

        if spname:
            info.update({'specialname': True})

        Ldata=[]
        HypColumn = False
        Lfriends=[]
        for dat in dataz:
            x1=dat['total_label']
            if 'full_auto' in dat:
                x2='No'
                if dat['full_label'] not in Lfriends:
                    Lfriends.append(dat['full_label'])
            else:
                x2='Yes'
                
            if 'hyperelliptic' in dat:
                x3=tfTOyn(dat['hyperelliptic'])
                HypColumn= True
            else:
                x3=' '

            x4=[]
            for perm in dat['gen_vectors']:
                cycperm=Permutation(perm).cycle_string()
                
                x4.append(sep.join(split_perm(cycperm)))
                    
            Ldata.append([x1,x2,x3,x4])

            
                
        info.update({'genvects': Ldata, 'HypColumn' : HypColumn})

        info.update({'passport_cc': cc_display(ast.literal_eval(dat['con']))})
        

        if 'hyperelliptic' in data:
            info.update({'ishyp':  tfTOyn(data['hyperelliptic'])})
            
        if 'hyp_involution' in data:
            inv=Permutation(data['hyp_involution']).cycle_string()
            info.update({'hypinv': sep.join(split_perm(inv))})
            

        if 'full_auto' in data:
            full_G=ast.literal_eval(data['full_auto'])
            full_gn = full_G[0]
            full_gt = full_G[1]

            full_gp_string=str(full_gn) + '.' + str(full_gt)
            full_pretty_group=sg_pretty(full_gp_string)
            info.update({'fullauto': full_pretty_group,
                         'signH':sign_display(ast.literal_eval(data['signH'])),
                         'higgenlabel' : data['full_label'] })


        urlstrng,br_g, br_gp, br_sign, refined_p = split_passport_label(label)
       
      
        if Lfriends:
           for Lf in Lfriends:
              friends = [("Full automorphism " + Lf, Lf),("Family containing this refined passport ",  urlstrng) ]
  
        else:    
            friends = [("Family containing this refined passport",  urlstrng) ]    
         
        
        bread_sign = label_to_breadcrumbs(br_sign)
        bread_gp = label_to_breadcrumbs(br_gp)
       
        bread = get_bread([(br_g, './?genus='+br_g),('$'+pretty_group+'$','./?genus='+br_g + '&group='+bread_gp), (bread_sign, urlstrng),(data['cc'][0],' ')])

        learnmore =[('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]

        downloads = [('Download Magma code', url_for(".hgcwa_code_download",  label=label, download_type='magma')),
                     ('Download Gap code', url_for(".hgcwa_code_download", label=label, download_type='gap'))]
            
        return render_template("hgcwa-show-passport.html", 
                               title=title, bread=bread, info=info,
                               properties2=prop2, friends=friends,
                               learnmore=learnmore, downloads=downloads)


    
def search_input_error(info, bread):
    return render_template("hgcwa-search.html", info=info, title='Families of Higher Genus Curve Search Input Error', bread=bread)


 
@higher_genus_w_automorphisms_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the automorphisms of curves data'
    bread = get_bread([("Completeness", )])
    learnmore = [('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.curve.highergenus.aut.extent',
                            title=t, bread=bread,learnmore=learnmore)


@higher_genus_w_automorphisms_page.route("/Labels")
def labels_page():
    t = 'Label scheme for the data'
    bread = get_bread([("Labels", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page"))]
    return render_template("single.html", kid='dq.curve.highergenus.aut.label',
                           learnmore=learnmore, title=t, bread=bread)

@higher_genus_w_automorphisms_page.route("/Source")
def how_computed_page():
    t = 'Source of the automorphisms of curve data'
    bread = get_bread([("Source", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Labeling convention', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.curve.highergenus.aut.source',
                           title=t, bread=bread, learnmore=learnmore)




_curdir = os.path.dirname(os.path.abspath(__file__))
code_list =  yaml.load(open(os.path.join(_curdir, "code.yaml")))

@higher_genus_w_automorphisms_page.route("/<label>/download/<download_type>")
def hgcwa_code_download(**args):
    response = make_response(hgcwa_code(**args))
    response.headers['Content-type'] = 'text/plain'
    return response


same_for_all =  ['signature', 'genus']
other_same_for_all = [ 'r', 'g0', 'dim','sym']
depends_on_action = ['gen_vectors']


Fullname = {'magma': 'Magma', 'gap': 'GAP'}
Comment = {'magma': '//', 'gap': '#'}

def hgcwa_code(**args):
    label = args['label']
    C = base.getDBConnection()
    lang = args['download_type']
    code = "%s %s code for the lmfdb family of higher genus curves %s\n" % (Comment[lang],Fullname[lang],label)
    code +="%s The results are stored in a list of records called 'result_record'\n\n" % (Comment[lang]) 
    code +=code_list['top_matter'][lang] + '\n' +'\n'
    code +="result_record:=[];" + '\n' +'\n'


    if label_is_one_passport(label):
        data = C.curve_automorphisms.passports.find({"passport_label" : label})

    elif label_is_one_family(label):
        data = C.curve_automorphisms.passports.find({"label" : label})



    code += Comment[lang] + code_list['gp_comment'][lang] +'\n'
    code += code_list['group'][lang] + str(data[0]['group'])+ ';\n'

    if lang == 'magma':
        code += code_list['group_construct'][lang] + '\n'

    for k in same_for_all:
        code += code_list[k][lang] + str(data[0][k])+ ';\n'
        
    for k in other_same_for_all:
        code += code_list[k][lang] + '\n'

    code += '\n'

    for dataz in data:
        code += Comment[lang] + " Here we add an action to result_record." + '\n'
        for k in depends_on_action:
            code += code_list[k][lang] + str(dataz[k])+ ';\n'

        if lang == 'magma':
            code += code_list['con'][lang] + str(dataz['con'])+ ';\n' 
             
        code += code_list['gen_gp'][lang]+ '\n'
        code += code_list['passport_label'][lang] + str(dataz['cc'][0]) + ';\n'
        code += code_list['gen_vect_label'][lang] + str(dataz['cc'][1]) + ';\n'
        
#cannot have full auto + hyperelliptic in data
        if 'signH' in dataz:
            code += code_list['full_auto'][lang]+str(dataz['full_auto']) + ';\n'
            code += code_list['full_sign'][lang]+str(dataz['signH']) + ';\n'        
            code+=code_list['add_to_total_full'][lang]+'\n'

        if 'hyperelliptic' in dataz:            
                                               
            if dataz['hyperelliptic']:
                code +=code_list['hyp'][lang]+ code_list['tr'][lang] + ';\n'
                code += code_list['hyp_inv'][lang]+str(dataz['hyp_involution']) + code_list['hyp_inv_last'][lang]
                code +=code_list['add_to_total_hyp'][lang]+'\n'

            else:
                code +=code_list['hyp'][lang]+ code_list['fal'][lang] + ';\n'
                code +=code_list['add_to_total_basic'][lang]+'\n'

        code += '\n'

    return code



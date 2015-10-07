r"""

Routines for helping with the download of modular forms data.

"""
import StringIO
from flask import send_file
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_newforms import WebNewForm
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modform_space import WebModFormSpace
from lmfdb.modular_forms.backend.mf_utils import my_get
from sage.all import latex,dumps

def get_coefficients(info):
    r"""
    Return a file with the Fourier coefficients in desired format.
    """
    emf_logger.debug("IN GET_COEFFICIENTS!!!")
    level = my_get(info, 'level', -1, int)
    weight = my_get(info, 'weight', -1, int)
    character = my_get(info, 'character', '', str)  # int(info.get('weight',0))
    emf_logger.debug("info={0}".format(info))
    if character == '':
        character = 0
    label = info.get('label', '')
    # we only want one form or one embedding
    s = print_list_of_coefficients(info)
    print "s=",s
    if info['format']=="sage":
        ending = "sobj"
    else:
        ending = "txt"
    info['filename'] = str(weight) + '-' + str(
        level) + '-' + str(character) + '-' + label + 'coefficients-0to' + info['number'] + "."+ending
    # return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
    
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO,
                     attachment_filename=info["filename"],
                     as_attachment=True)


def download_web_modform(info):
    r"""
    Return a dump of a WebNewForm object.

    """
    emf_logger.debug("IN GET_WEB_MODFORM!!! info={0}".format(info))
    level = my_get(info, 'level', -1, int)
    weight = my_get(info, 'weight', -1, int)
    character = my_get(info, 'character',0, int)  # int(info.get('weight',0))
    emf_logger.debug("info={0}".format(info))
    if character == '':
        character = 0
    label = info.get('label', '')
    # we only want one form or one embedding
    if label != '':
        if format == 'sage':
            if character != 0:
                D = DirichletGroup(level)
                x = D[character]
                X = Newforms(x, weight, names='a')
            else:
                X = Newforms(level, weight, names='a')
        else:  # format=='web_new':
            X = WebNewForm(level=level, weight=weight, character=character, label=label)
    s = dumps(X)
    name = "{0}-{1}-{2}-{3}-web_newform.sobj".format(weight, level, character, label)
    emf_logger.debug("name={0}".format(name))
    info['filename'] = name
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    try:
        return send_file(strIO,
                         attachment_filename=info["filename"],
                         as_attachment=True)
    except IOError:
        info['error'] = "Could not send file!"



def print_list_of_coefficients(info):
    r"""
    Print a table of Fourier coefficients in the requested format
    """
    level = my_get(info, 'level', -1, int)
    weight = my_get(info, 'weight', -1, int)
    prec = my_get(info, 'prec', 12, int)  # number of digits
    bitprec = my_get(info, 'bitprec', 12, int)  # number of digits                
    character = my_get(info, 'character', '', str)  # int(info.get('weight',0))
    fmt = info.get("format","q_expansion")
    if character == '':
        character = '1'
    label = info.get('label', '')
    if character.isalnum():
        character = int(character)
    else:
        return "The character '{0}' is not well-defined!".format(character)
    print "--------------"
    if label == '' or level == -1 or weight == -1:
        return "Need to specify a modular form completely!!"

    WMFS = WebModFormSpace(level= level, weight = weight, cuspidal=True,character = character)
    if not WMFS:
        return ""
    if('number' in info):
        number = int(info['number'])
    else:
        number = max(WMFS.sturm_bound() + 1, 20)
    FS = list()
    f  = WMFS.hecke_orbits.get(label)
    if f is not None:
        FS.append(f)
    else:
        for label in WMFS.hecke_orbits:
            FS.append(WMFS.f(label))
    shead = "Cusp forms of weight " + str(weight) + "on \(" + latex(WMFS.group) + "\)"
    s = ""
    if((character is not None) and (character > 0)):
        shead = shead + " and character \( \chi_{" + str(character) + "}\)"
        # s="<table><tr><td>"
    coefs = ""
    if fmt == "sage":
        res = []
    for F in FS:
        if len(FS) > 1:
            if info['format'] == 'html':
                coefs += F.label()
            else:
                coefs += F.label()
        if fmt == "sage":
            qe = F.coefficients(range(number))
            res.append(qe)
        else:
            coefs += print_coefficients_for_one_form(F, number, info['format'],bitprec=bitprec)
    if not fmt == "sage":
        return s+"\n"+coefs
    else:
        if len(res)==1:
            res = res[0]
        print "res=",res
        return dumps(res)



def print_coefficients_for_one_form(F, number, fmt="q_expansion",bitprec=53):
    emf_logger.debug("in print {2} coefs for 1 form: format={0} bitprec={1}, F={3}".format(fmt,bitprec,number,F))
    # Start with some meta-data 
    s = "## level={N}, weight={k}, character={ch},label={label} \n".format(N=F.level,k=F.weight,ch=F.character.number,label=F.label)
    #max_cn = F.max_cn()
    #emf_logger.debug("evs={0}".format(F.eigenvalues))
    #emf_logger.debug("primes={0}".format(F.eigenvalues.primes()))
    #if number > max_cn:
    #    number = max_cn
    ## TODO: add check that we have sufficiently many coefficients!
    if fmt == "q_expansion":
        s += str(F.q_expansion.truncate_powerseries(number))
    if fmt == "coefficients":
        qe = F.coefficients(range(number))
        #emf_logger.debug("F={0}".format(F))
        #deg=0 [emf_download_utils.py:147
        deg = F.coefficient_field.degree()
        #emf_logger.debug("deg={0}".format(deg))        
        if deg > 1:
            pol = F.coefficient_field.polynomial()
            s += "## coefficient field : "+str(pol)+"=0"
            s += "\n"
        else:
            s += "## coefficient field : Rational Field"
            s += "\n"            
        for n in range(len(qe)):
            c=qe[n]
            s += "{n} \t {c} \n".format(n=n,c=c)
        emf_logger.debug("qe={0}".format(qe))
         
    if fmt == "embeddings":
        #embeddings = F.q_expansion_embeddings(number,bitprec=bitprec,format='numeric')
        deg = F.coefficient_field.degree()
        for j in range(deg):
            if deg > 1:
                s+="# Embedding nr. {j} \n".format(j=j)            
            for n in range(number):
                s += str(n) + "\t" + str(F.coefficient_embedding(n,j)) + "\n"
        
    emf_logger.debug("s={0}".format(s))
    return s

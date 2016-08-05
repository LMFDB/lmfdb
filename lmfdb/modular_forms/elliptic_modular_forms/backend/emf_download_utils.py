r"""

Routines for helping with the download of modular forms data.

"""
import StringIO
import flask
from flask import send_file,redirect,url_for
from lmfdb.modular_forms.elliptic_modular_forms import emf_logger
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_newforms import WebNewForm
from lmfdb.modular_forms.backend.mf_utils import my_get
from sage.all import latex,dumps

def get_coefficients(info):
    r"""
    Return a file with the Fourier coefficients in desired format.
    """
    emf_logger.debug("IN GET_COEFFICIENTS!!!")
    level = my_get(info, 'level', -1, int)
    weight = my_get(info, 'weight', -1, int)
    character = my_get(info, 'character', '', int)  # int(info.get('weight',0))
    number=my_get(info,'number',100,int)
    label=my_get(info,'label','',str)
    emf_logger.debug("info={0}".format(info))
    if character == '':
        character = 1
    label = info.get('label', '')
    if info['format']=="sage":
        ending = "sage"
        f = WebNewForm(level, weight, character, label, prec=number)
        s = f.download_to_sage(number)
    elif info['format']=="sobj":
        ending = "sobj"
        f = WebNewForm(level, weight, character, label, prec=number)
        s = f.dump_coefficients(number)
    else:
        # we only want one form or one embedding
        try:
            s = print_list_of_coefficients(info)
        except IndexError as e:
            info['error']=str(e)
            flask.flash(str(e))
            return redirect(url_for("emf.render_elliptic_modular_forms", level=level,weight=weight,character=character,label=label), code=301)
        ending = "txt"
    if info['format'] == 'q_expansion':
        fmt = '-qexp'
    elif info['format'] == "coefficients" or info['format'] == "sobj":
        fmt = '-coef'
    elif info['format'] == "embeddings":
        fmt = '-emb'
    else:
        fmt=''
    info['filename'] = "{0}-{1}-{2}-{3}-coefficients-0-to-{4}{5}.{6}".format(level,weight,character,label,number,fmt,ending)
    # return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'], add_etags=False)

    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO,
                     attachment_filename=info["filename"],
                     as_attachment=True,
                     add_etags=False)

def print_list_of_coefficients(info):
    r"""
    Print a table of Fourier coefficients in the requested format
    """
    level = my_get(info, 'level', -1, int)
    weight = my_get(info, 'weight', -1, int)
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

    number = int(info['number'])+1 if 'number' in info else 20
    emf_logger.debug("number = {}".format(number))
    F = WebNewForm(level= level, weight = weight, character = character, label = label, prec=number)
    if not F.has_updated():
        return ""
    if not 'number' in info:
        F.prec = number = max(F.parent.sturm_bound + 1, 20)
        F.update_from_db()
    shead = "Cusp forms of weight " + str(weight) + "on \(" + latex(F.parent.group) + "\)"
    s = ""
    if((character is not None) and (character > 0)):
        shead = shead + " and character \( \chi_{" + str(character) + "}\)"
        # s="<table><tr><td>"
    coefs = ""
    if fmt == "sage":
        res = []
    if number > F.max_available_prec():
        raise IndexError,"The database does not contain this many ({0}) coefficients for this modular form! We only have {1}".format(number,F.max_available_prec())
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
        #print "res=",res
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
    deg = F.coefficient_field.absolute_degree() # OK for QQ too
    if deg > 1:
        pol = F.coefficient_field.relative_polynomial()
    #emf_logger.debug("deg={0}".format(deg))
    if fmt == "q_expansion":
        if deg > 1:
            s += "\n## coefficient field : "+str(pol)+"=0"
        else:
            s += "## coefficient field : Rational Field"
        s += "\n\n"
        s += str(F.q_expansion.truncate_powerseries(number))
    if fmt == "coefficients":
        qe = F.coefficients(range(number))
        #emf_logger.debug("F={0}".format(F))
        #deg=0 [emf_download_utils.py:147
        if deg > 1:
            s += "\n## coefficient field : "+str(pol)+"=0"
        else:
            s += "\n## coefficient field : Rational Field"
        s += "\n\n"
        for n in range(len(qe)):
            c=qe[n]
            s += "{n} \t {c} \n".format(n=n,c=c)
        #emf_logger.debug("qe={0}".format(qe))

    if fmt == "embeddings":
        #embeddings = F.q_expansion_embeddings(number,bitprec=bitprec,format='numeric')
        deg = F.coefficient_field.absolute_degree()
        for j in range(deg):
            if deg > 1:
                s+="# Embedding nr. {j} \n".format(j=j)
            for n in range(number):
                s += str(n) + "\t" + str(F.coefficient_embedding(n,j)) + "\n"

    #emf_logger.debug("s={0}".format(s))
    return s

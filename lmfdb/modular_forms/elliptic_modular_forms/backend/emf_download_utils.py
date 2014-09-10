r"""

Routines for helping with the download of modular forms data.

"""



def get_coefficients(info):
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
    info['filename'] = str(weight) + '-' + str(
        level) + '-' + str(character) + '-' + label + 'coefficients-0to' + info['number'] + '.txt'
    # return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO,
                     attachment_filename=info["filename"],
                     as_attachment=True)


def download_web_modform(info):
    emf_logger.debug("IN GET_WEB_MODFORM!!! info={0}".format(info))
    level = my_get(info, 'level', -1, int)
    weight = my_get(info, 'weight', -1, int)
    character = my_get(info, 'character', '', str)  # int(info.get('weight',0))
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
            X = WebNewForm(N=level, k=weight, chi=character, label=label)
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
    if character == '':
        character = 0
    label = info.get('label', '')
    print "--------------"
    if label == '' or level == -1 or weight == -1:
        return "Need to specify a modular form completely!!"

    WMFS = WebModFormSpace(N = level, k = weight, chi = character)
    if not WMFS:
        return ""
    if('number' in info):
        number = int(info['number'])
    else:
        number = max(WMFS.sturm_bound() + 1, 20)
    FS = list()
    if(label is not None):
        FS.append(WMFS.f(label))
    else:
        for a in WMFS.labels():
            FS.append(WMFS.f(a))
    shead = "Cusp forms of weight " + str(weight) + "on \(" + latex(WMFS.group()) + "\)"
    s = ""
    if((character is not None) and (character > 0)):
        s = s + " and character \( \chi_{" + str(character) + "}\)"
        # s="<table><tr><td>"
    coefs = ""
    for F in FS:
        if len(FS) > 1:
            if info['format'] == 'html':
                coefs += F.label()
            else:
                coefs += F.label()
        coefs += print_coefficients_for_one_form(F, number, info['format'],bitprec=bitprec)
    ss = coefs
    return ss



def print_coefficients_for_one_form(F, number, fmt,bitprec=53):
    emf_logger.debug("in print {2} coefs for 1 form: format={0} bitprec={1}".format(fmt,bitprec,number))
    # Start with some meta-data 
    s = "## level={N}, weight={k}, character={ch},label={label} \n".format(N=F.level(),k=F.weight(),ch=F.chi(),label=F.label())
    max_cn = F.max_cn()
    if number > max_cn:
        number = max_cn
    if fmt == "q_expansion":
        s += F.print_q_expansion(number)
    if fmt == "coefficients":
        qe = F.coefficients(range(number))
        if F.degree() > 1:
            s += "## "+str(F.polynomial(type='coefficient_field'))+"=0"
        s += "\n"
        for n in range(len(qe)):
            c=qe[n]
            s += "{n} \t {c} \n".format(n=n,c=c)
    if fmt == "embeddings":
        embeddings = F.q_expansion_embeddings(number,bitprec=bitprec,format='numeric')
        if F.degree() > 1:
            for j in range(F.degree()):
                s+="# Embedding nr. {j} \n".format(j=j)
                for n in range(number):
                    s += str(n) + "\t" + str(embeddings[n][j]) + "\n"
        else:
            for n in range(number):
                s += str(n) + "\t" + str(embeddings[n]) + "\n"
    emf_logger.debug("s={0}".format(s))
    return s

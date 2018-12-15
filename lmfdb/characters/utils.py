import re

#############################################################################
###
###    small utilities to be removed one day
###
#############################################################################

def evalpolelt(label,gen,genlabel='a'):
    """ label is a compact polynomial expression in genlabel
        ( '*' and '**' are removed )
    """
    res = 0
    regexp = r'([+-]?)([+-]?\d*o?\d*)(%s\d*)?'%genlabel
    for m in re.finditer(regexp,label):
        s,c,e = m.groups()
        if c == '' and e == None: break
        if c == '':
            c = 1
        else:
            """ c may be an int or a rational a/b """
            from sage.rings.rational import Rational
            c = str(c).replace('o','/')
            c = Rational(c)
        if s == '-': c = -c
        if e == None:
            e = 0
        elif e == genlabel:
            e = 1
        else:
            e = int(e[1:])
        res += c*gen**e
    return res

def complex2str(g, digits=10):
    real = round(g.real(), digits)
    imag = round(g.imag(), digits)
    if imag == 0.:
        return str(real)
    elif real == 0.:
        return str(imag) + 'i'
    else:
        return str(real) + '+' + str(imag) + 'i'

###############################################################################
## url_for modified for characters
from flask import url_for
def url_character(**kwargs):
    if 'type' not in kwargs:
        return url_for('characters.render_characterNavigation')
    elif kwargs['type'] == 'Dirichlet':
        del kwargs['type']
        if kwargs.get('calc',None):
            return url_for('characters.dc_calc',**kwargs)
        else:
            return url_for('characters.render_Dirichletwebpage',**kwargs)
    elif kwargs['type'] == 'Hecke':
        del kwargs['type']
        if kwargs.get('calc',None):
            return url_for('characters.hc_calc',**kwargs)
        else:
            return url_for('characters.render_Heckewebpage',**kwargs)


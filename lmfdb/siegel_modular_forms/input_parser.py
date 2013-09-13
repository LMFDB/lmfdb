# -*- coding: utf-8 -*-

import re
from sage.rings.integer import Integer


def kj_parser( s):
    """
    Parse the string s for being a vaild $(k,j)$-input
    for a space of Siegel modular forms.
    """
    # default values if only parts are set
    kmin = None
    kmax = None
    j = None

    # split the input string into tokens
    pattern = re.compile(r'\s+')
    s1 = re.sub(pattern, '', s)
    lot = [i for i in re.split(r'(\d+|\W+)', s1) if i]

    def get_int( t):
        return Integer(t)

    # parse the input
    state = 'S'
    for t in lot:

        if 'S' == state:
            kmin = get_int( t)
            state = '#'

        elif '#' == state:
            if '-' == t:
                state = '#-'
            elif ',' == t:
                state = '#,'
            else:
                raise SyntaxError( '%s: - or , expected' % t)

        elif '#-' == state:
            kmax = get_int( t)
            state = '#-#'

        elif '#,' == state:
            j = get_int( t)
            state = '#[-#],#'

        elif '#-#' == state:
            if ',' == t:
                state = '#,'
            else:
                raise SyntaxError( '%s: , expected' % t)

        else:
            raise SyntaxError( '%s: I am messed up' %s )

    return kmin,kmax,j

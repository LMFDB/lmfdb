import re
from urllib.parse import urlencode
from markupsafe import escape
from sage.all import (
    Factorization,
    latex,
    ZZ,
    QQ,
    factor,
    PolynomialRing,
    TermOrder,
)
from . import coeff_to_poly
################################################################################
#  latex/math rendering utilities
################################################################################


def raw_typeset(raw, typeset='', extra='', compressed=False):
    r"""
    Return a span with typeset material which will toggle to raw material
    when an icon is clicked on.

    The raw version can be a string, or a sage object which will stringify
    properly.

    If the typeset version can be gotten by just applying latex to the raw
    version, the typeset version can be omitted.

    If there is a string to appear between the toggled text and the icon,
    it can be given in the argument extra

    If one of these appear on a page, then the icon to toggle all of them
    on the page will appear in the upper right corner of the body of the
    page.
    """
    if not typeset:
        typeset = r'\({}\)'.format(latex(raw))

    typeset = f'<span class="tset-container">{typeset}</span>'
    # clean white space
    raw = re.sub(r'\s+', ' ', str(raw).strip())
    raw = f'<textarea rows="1" cols="{len(raw)}" class="raw-container">{raw}</textarea>'


    # the doublesclick behavior is set on load in javascript
    out = f"""
<span class="raw-tset-container tset {"compressed" if compressed else ""}">
    {typeset}
    {raw}
    {extra}
    <span class="raw-tset-copy-btn" onclick="copyrawcontainer(this)">
        <img alt="Copy content"
        class="tset-icon">
    </span>
    <span class="raw-tset-toggle" onclick="iconrawtset(this)">
        <img alt="Toggle raw display"
        class="tset-icon"
    </span>
</span>"""
    return out

def display_knowl(kid, title=None, kwargs={}):
    """
    Allows for the construction of knowls from python code
    (to be displayed using the ``safe`` flag in jinja);
    the only difference with the KNOWL macro is that
    there will be no edit link for authenticated users.
    """
    from lmfdb.knowledge.knowl import knowl_title
    ktitle = knowl_title(kid)
    if ktitle is None:
        # Knowl not found
        if title is None:
            return """<span class="knowl knowl-error">'%s'</span>""" % kid
        else:
            return title
    else:
        if title is None:
            if len(ktitle) == 0:
                title = kid
            else:
                title = ktitle
        if len(title) > 0:
            return '<a title="{0} [{1}]" knowl="{1}" kwargs="{2}">{3}</a>'.format(ktitle, kid, urlencode(kwargs), title)
        else:
            return ''

def web_latex(x, enclose=True):
    r"""
    Convert input to latex string unless it's a string or unicode. The key word
    argument `enclose` indicates whether to surround the string with
    `\(` and `\)` to tag it as an equation in html.

    Note:
    if input is a factored ideal, use web_latex_ideal_fact instead.

    Example:
    >>> x = var('x')
    >>> web_latex(x**23 + 2*x + 1)
    '\\( x^{23} + 2 \\, x + 1 \\)'
    """
    if isinstance(x, str):
        return x
    return rf"\( {latex(x)} \)" if enclose else f" {latex(x)} "


def compress_int(n, cutoff=15, sides=2):
    res = str(n)
    if abs(n) >= 10**cutoff:
        short = res[:sides + (1 if n < 0 else 0)] + r'\!\cdots\!' + res[-sides:]
        return short, True
    else:
        return res, False


def bigint_knowl(n, cutoff=20, max_width=70, sides=2):
    short, shortened = compress_int(n, cutoff=cutoff, sides=sides)
    if shortened:
        lng = r"<div style='word-break: break-all'>%s</div>" % n
        return r'<a title="[bigint]" knowl="dynamic_show" kwargs="%s">\(%s\)</a>'%(lng, short)
    else:
        return r'\(%s\)' % n

def too_big(L, threshold):
    r"""
    INPUT:

    - ``L`` -- nested lists of integers
    - ``threshold`` -- an integer

    OUTPUT:

    Whether any integer in ``L`` is at least ``threshold``
    """
    if isinstance(L, (list, tuple)):
        return any(too_big(x, threshold) for x in L)
    return L >= threshold

def make_bigint(s, cutoff=20, max_width=70):
    r"""
    INPUT:

    - ``s`` -- A string, the latex representation of an integer or polynomial.
      It should include outer \( and \).
    - ``cutoff`` -- an integer

    OUTPUT:

    The string ``s`` with integers at least 10^cutoff replaced by bigint_knowls.
    """
    Zmatcher = re.compile(r'([0-9]{%s,})' % (cutoff+1))
    def knowl_replacer(M):
        a = bigint_knowl(int(M.group(1)), cutoff, max_width=max_width)
        if a[0:2] == r'<a':
            return r'\)' + a + r'\('
        else:
            return a
    return Zmatcher.sub(knowl_replacer, s)


def bigpoly_knowl(f, nterms_cutoff=8, bigint_cutoff=12, var='x'):
    lng = web_latex(coeff_to_poly(f, var))
    if bigint_cutoff:
        lng = make_bigint(lng, bigint_cutoff, max_width=70)
    if len([c for c in f if c != 0]) > nterms_cutoff:
        short = "%s^{%s}" % (latex(coeff_to_poly([0,1], var)), len(f) - 1)
        i = len(f) - 2
        while i >= 0 and f[i] == 0:
            i -= 1
        if i >= 0: # nonzero terms
            if f[i] > 0:
                short += r" + \cdots"
            else:
                short += r" - \cdots"
#        return r'<a title="[poly]" knowl="dynamic_show" kwargs="%s">\(%s\)</a>'%(lng, short)
        return r'<a title=&quot;[poly]&quot; knowl=&quot;dynamic_show&quot; kwargs=&quot;%s&quot;>\(%s\)</a>'%(lng,short)
    else:
        return lng

def factor_base_factorization_latex(fbf, cutoff=0):
    """
    cutoff is the threshold for compressing large integers
    cutoff = 0 means we do not compress them
    """
    if len(fbf) == 0:
        return '1'
    ans = ''
    sign = 1
    for p, e in fbf:
        pdisp = str(p)
        if cutoff:
            pdisp = compress_int(p, cutoff)[0]
        if p == -1:
            if (e % 2) == 1:
                sign *= -1
        elif e == 1:
            ans += r'\cdot %s' % pdisp
        elif e != 0:
            ans += r'\cdot %s^{%d}' % (pdisp, e)
    # get rid of the initial '\cdot '
    ans = ans[6:]
    return '- ' + ans if sign == -1 else ans

def polyquo_knowl(f, disc=None, unit=1, cutoff=None):
    quo = "x^{%s}" % (len(f) - 1)
    i = len(f) - 2
    while i >= 0 and f[i] == 0:
        i -= 1
    if i >= 0: # nonzero terms
        if f[i] > 0:
            quo += r" + \cdots"
        else:
            quo += r" - \cdots"
    short = r'\mathbb{Q}[x]/(%s)'%(quo)
    long = r'Defining polynomial: %s' % escape(raw_typeset_poly(f))
    if disc is not None:
        if isinstance(disc, list):
            long += '\n<br>\nDiscriminant: \\(%s\\)' % (factor_base_factorization_latex(disc))
        else:
            long += '\n<br>\nDiscriminant: \\(%s\\)' % (Factorization(disc, unit=unit)._latex_())
    return r'<a title="[poly]" knowl="dynamic_show" kwargs="%s">\(%s\)</a>'%(long, short)





def web_latex_factored_integer(x, enclose=True, equals=False):
    r"""
    Given any x that can be converted to a ZZ, creates latex string representing x in factored form
    Returns 0 for 0, replaces -1\cdot with -.

    If equals=true returns latex string for x = factorization but omits "= factorization" if abs(x)=0,1,prime
    """
    x = ZZ(x)
    if abs(x) in [0,1] or abs(x).is_prime():
        return web_latex(x, enclose=enclose)
    if equals:
        s = web_latex(factor(x), enclose=False).replace(r"-1 \cdot","-")
        s = " %s = %s " % (x, s)
    else:
        s = web_latex(factor(x), enclose=False).replace(r"-1 \cdot","-")
    return r"\( %s \)" % s if enclose else s

def web_latex_ideal_fact(x, enclose=True):
    r"""
    Convert input factored ideal to latex string.  The key word argument
    `enclose` indicates whether to surround the string with `\(` and
    `\)` to tag it as an equation in html.

    sage puts many parentheses around latex representations of factored ideals.
    This function removes excessive parentheses.

    Example:
    >>> x = var('x')
    >>> K = NumberField(x**2 - 5, 'a')
    >>> a = K.gen()
    >>> I = K.ideal(2/(5+a)).factor()
    >>> print(latex(I))
    (\left(-a\right))^{-1}
    >>> web_latex_ideal_fact(I)
    '\\( \\left(-a\\right)^{-1} \\)'
    """
    y = web_latex(x, enclose=enclose)
    y = y.replace(r"(\left(", r"\left(")
    y = y.replace(r"\right))", r"\right)")
    return y


def web_latex_split_on(x, on=['+', '-']):
    r"""
    Convert input into a latex string. A different latex surround `\(` `\)` is
    used, with splits occurring at `on` (+ - by default).

    Example:
    >>> x = var('x')
    >>> web_latex_split_on(x**2 + 1)
    '\\( x^{2} \\) + \\(  1 \\)'
    """
    if isinstance(x, str):
        return x
    else:
        A = rf"\( {latex(x)} \)"
        for s in on:
            A = A.replace(s, r'\) ' + s + r' \( ')
    return A


# web_latex_split_on was not splitting polynomials, so we make an expanded version
def web_latex_split_on_pm(x):
    r"""
    Convert input into a latex string, with specific handling of expressions
    including `+` and `-`.

    Example:
    >>> x = var('x')
    >>> web_latex_split_on_pm(x**2 + 1)
    '\\(x^{2} \\) \\(\\mathstrut +\\mathstrut  1 \\)'
    """
    on = ['+', '-']
    try:
        A = r"\(" + x + r"\)"  # assume we are given LaTeX to split on
    except Exception:
        A = r"\( %s \)" % latex(x)

       # need a more clever split_on_pm that inserts left and right properly
    A = A.replace(r"\left","")
    A = A.replace(r"\right","")
    for s in on:
  #      A = A.replace(s, r'\) ' + s + r' \( ')
   #     A = A.replace(s, r'\) ' + r' \( \mathstrut ' + s )
        A = A.replace(s, r'\)' + r' \(\mathstrut ' + s + r'\mathstrut ')
    # the above will be re-done using a more sophisticated method involving
    # regular expressions.  Below fixes bad spacing when the current approach
    # encounters terms like (-3+x)
    for s in on:
        A = A.replace(r'(\) \(\mathstrut ' + s, '(' + s)
    A = A.replace(r'( {}', r'(')
    A = A.replace(r'(\) \(', r'(')
    A = A.replace(r'\(+', r'\(\mathstrut+')
    A = A.replace(r'\(-', r'\(\mathstrut-')
    A = A.replace(r'(  ', r'(')
    A = A.replace(r'( ', r'(')

    return A
    # return web_latex_split_on(x)

def web_latex_split_on_re(x, r = '(q[^+-]*[+-])'):
    r"""
    Convert input into a latex string, with splits into separate latex strings
    occurring on given regex `r`.
    CAUTION: this gives a different result than web_latex_split_on_pm

    Example:
    >>> x = var('x')
    >>> web_latex_split_on_re(x**2 + 1)
    '\\(x^{2} \\) \\(\\mathstrut+  1 \\)'
    """

    def insert_latex(s):
        return s.group(1) + r'\) \('

    if isinstance(x, str):
        return x
    else:
        A = r"\( %s \)" % latex(x)
        c = re.compile(r)
        A = A.replace(r'+', r'\) \( {}+ ')
        A = A.replace(r'-', r'\) \( {}- ')
#        A = A.replace('\left(','\left( {}\\right.') # parentheses needs to be balanced
#        A = A.replace('\\right)','\left.\\right)')
        A = A.replace(r'\left(',r'\bigl(')
        A = A.replace(r'\right)',r'\bigr)')
        A = c.sub(insert_latex, A)

    # the above will be re-done using a more sophisticated method involving
    # regular expressions.  Below fixes bad spacing when the current approach
    # encounters terms like (-3+x)
    A = A.replace(r'( {}', r'(')
    A = A.replace(r'(\) \(', r'(')
    A = A.replace(r'\(+', r'\(\mathstrut+')
    A = A.replace(r'\(-', r'\(\mathstrut-')
    A = A.replace(r'(  ', r'(')
    A = A.replace(r'( ', r'(')
    A = A.replace(r'+\) \(O', r'+O')
    return A



def compress_polynomial(poly, threshold, decreasing=True):
    if poly == 0:
        return '0'
    plus = r" + "
    minus = r" - "
    var = poly.parent().gen()

    d = 0 if decreasing else poly.degree()
    assert poly[d] != 0 or decreasing
    while poly[d]  == 0: # we only enter the loop if decreasing=True
        d += 1
    lastc = poly[d]
    cdots = r" + \cdots "
    tsetend = plus if lastc > 0 else minus
    short, shortened = compress_int(abs(lastc))
    if abs(lastc) != 1 or d == 0:
        tsetend += short

    monomial_length = 0
    if d > 0:
        monomial = latex(var**d)
        tsetend += monomial
        monomial_length += len(monomial)

    tset = ""
    for n in (reversed(range(d + 1, poly.degree() + 1)) if decreasing else range(d)):
        c = poly[n]
        if tset and len(tset) + len(tsetend) - monomial_length > threshold:
            tset += cdots
            break

        short, shortened = compress_int(abs(c))
        if shortened and tset:
            tset += cdots
            break

        if c > 0:
            if tset: # don't need the + for the leading coefficient
                tset += plus
        elif c < 0:
            tset += minus
        else:
            continue

        if abs(c) != 1:
            tset += compress_int(abs(c))[0] + " "

        if n >= 1:
            monomial = latex(var**n)
        else:
            monomial = "1" if abs(c) == 1 else ""
        monomial_length += len(monomial)
        tset += monomial

    tset += tsetend
    if tset.startswith(plus): # single monomial polynomials
        tset = tset[len(plus):]
    return tset

def raw_typeset_int(n, cutoff=80, sides=3, extra=''):
    """
    Raw/typeset for integers with configurable parameters
    """
    compv, compb = compress_int(n, cutoff=cutoff, sides=sides)
    return raw_typeset(n, rf'\({compv}\)', extra=extra, compressed=compb)


def raw_typeset_poly(coeffs,
                     denominator=1,
                     var='x',
                     superscript=True,
                     compress_threshold=100,
                     decreasing=True,
                     final_rawvar=None,
                     **kwargs):
    """
    Generate a raw_typeset string a given integral polynomial, or a linear combination
    (using subscripts instead of exponents).  In either case, the constant term is printed
    without a variable.
    It compresses the typeset latex if raw string is too  long.

    INPUT:

    - ``coeffs`` -- a list of integers
    - ``denominator`` -- a integer
    - ``var`` -- a variable name, we count on sage to properly convert it to latex
    - ``superscript`` -- whether to use superscripts (as opposed to subscripts)
    - ``compress_threshold`` -- the number of characters by which we would need to reduce the output of the typeset"""
    if denominator == 1:
        denominatorraw = denominatortset = ""
    else:
        denominatortset = denominatorraw = f"/ {denominator}"

    R = PolynomialRing(ZZ, var)
    tset_var = latex(R.gen())
    raw_var = var
    poly = R(coeffs)
    if poly == 0:
        return r"\(0\)"
    raw = str(poly)

    # figure out if we will compress the polynomial
    compress_poly = len(raw) + len(denominatorraw) > compress_threshold
    if compress_poly:
        denominatortset = f"/ {compress_int(denominator)[0]}"

    if compress_poly:
            tset = compress_polynomial(
                poly,
                compress_threshold - len(denominatortset),
                decreasing)
    else:
        if decreasing:
            tset = latex(poly)
        else:
            # to lazy to reverse it by hand
            Rfake = PolynomialRing(ZZ, [f'{raw_var}fake', raw_var], order=TermOrder('M(0,-1,0,-1)'))
            polytoprint = Rfake({(0, i): c for i, c in enumerate(poly)})
            tset = latex(polytoprint)

    if not superscript:
        raw = raw.replace('^', '').replace(raw_var + " ", raw_var + "1 ")
        tset = tset.replace('^', '_').replace(tset_var + " ", tset_var + "_1 ")
        # in case the last replace doesn't trigger because is at the end
        if raw.endswith(raw_var):
            raw += "1"
        if tset.endswith(tset_var):
            tset += "_1"

    if denominator != 1:
        tset = f"( {tset} ) {denominatortset}"
        raw = f"({raw}) {denominatorraw}"

    if final_rawvar:
        raw = raw.replace(var, final_rawvar)


    return raw_typeset(raw, rf'\( {tset} \)', compressed=r'\cdots' in tset, **kwargs)

def raw_typeset_poly_factor(factors, # list of pairs (f,e)
                            compress_threshold=20, # this is per factor
                            decreasing=True,
                            **kwargs):
    if len(factors) == 0:
        return r"\( 1 \)"
    if len(factors) == 1 and factors[0][1] == 1:
        coeffs = factors[0][0].list()
        var = str(factors[0][0].parent().gen())
        return raw_typeset_poly(
            coeffs,
            var=var,
            compress_threshold=compress_threshold,
            decreasing=decreasing,
            **kwargs)
    raw = []
    tset = []
    for f, e in factors:
        rawf = str(f)
        tsetf = compress_polynomial(f, compress_threshold, decreasing)
        if '+' in rawf or '-' in rawf:
            raw.append(f'({rawf})^{e}')
            tset.append(f'({tsetf})^{{{e}}}')
        else:
            raw.append(f'{rawf}^{e}')
            tset.append(f'{tsetf}^{{{e}}}')

    tset = " ".join(tset)
    raw = " ".join(raw)
    return raw_typeset(raw, rf'\( {tset} \)', compressed=r'\cdots' in tset, **kwargs)


def raw_typeset_qexp(coeffs_list,
                     compress_threshold=100,
                     coeff_compress_threshold=30,
                     var=r"\beta",
                     final_rawvar='b',
                     superscript=False,
                     **kwargs):
    plus = r" + "
    minus = r" - "

    rawvar = var.lstrip("\\")
    R = PolynomialRing(ZZ, rawvar)


    def rawtset_coeff(i, coeffs):
        poly = R(coeffs)
        if poly == 0:
            return "", ""
        rawq = f" * q^{i}" if i > 1 else " * q"
        tsetq = f" q^{{{i}}}" if i > 1 else " q"
        raw = str(poly)
        if poly in [1, -1]:
            rawq = f"q^{i}" if i > 1 else "q"
            if poly == -1:
                return minus + rawq, minus + tsetq
            elif i > 1:
                return plus + rawq, plus + tsetq
            else:
                return rawq, tsetq
        else:
            tset = compress_polynomial(
                poly,
                coeff_compress_threshold,
                decreasing=True)
        if not superscript:
            raw = raw.replace('^', '').replace(rawvar + " ", rawvar + "1 ")
            tset = tset.replace('^', '_').replace(var + " ", var + "_1 ")
            # in case the last replace doesn't trigger because is at the end
            if raw.endswith(rawvar):
                raw += "1"
            if tset.endswith(var):
                tset += "_1"
        if poly.number_of_terms() == 1:
            if i > 1:
                if raw.startswith('-'):
                    raw = minus + raw[1:]
                else:
                    raw = plus + raw
                    tset = plus + tset
        else:
            tset = f"({tset})"
            raw = f"({raw})"
            if i > 1:
                raw = plus + raw
                tset = plus + tset
        raw += rawq
        tset += tsetq
        return raw, tset

    tset = ''
    raw = ''
    add_to_tset = True
    lastt = None
    for i, coeffs in enumerate(coeffs_list):
        r, t = rawtset_coeff(i, coeffs)
        if t:
            lastt = t
        raw += r
        if add_to_tset:
            tset += t
        if add_to_tset and "cdots" in tset:
            add_to_tset = False
            lastt = None
    else:
        if lastt and not add_to_tset:
            tset += r"+ \cdots "
            tset += lastt

    tset += rf'+O(q^{{{len(coeffs_list)}}})'
    raw = raw.lstrip(" ")
    # use final_rawvar
    raw = raw.replace(rawvar, final_rawvar)

    return raw_typeset(raw, rf'\( {tset} \)', compressed=r'\cdots' in tset, **kwargs)

def compress_poly_Q(rawpoly,
                     var='x',
                     compress_threshold=100):
    """
    Generate a raw_typeset string a polynomial over Q
    The typeset compresses each numerator and denominator
    """
    R = PolynomialRing(QQ, var)
    sagepol = R(rawpoly)
    coefflist = sagepol.coefficients(sparse=False)
    d = len(coefflist)

    def frac_string(frac):
        if frac.denominator()==1:
            return compress_int(frac.numerator())[0]
        return r'\frac{%s}{%s}'%(compress_int(frac.numerator())[0], compress_int(frac.denominator())[0])

    tset = ''
    for j in range(1,d+1):
        csign = coefflist[d-j].sign()
        if csign:
            cabs = coefflist[d-j].abs()
            if csign>0:
                tset += '+'
            else:
                tset += '-'
            if cabs != 1 or d-j==0:
                tset += frac_string(cabs)
            if d-j>0:
                if d-j == 1:
                    tset += var
                else:
                    tset += r'%s^{%s}'%(var,d-j)
    return tset[1:]



# copied here from hilbert_modular_forms.hilbert_modular_form as it
# started to cause circular imports:
def teXify_pol(pol_str):  # TeXify a polynomial (or other string containing polynomials)
    if not isinstance(pol_str, str):
        pol_str = str(pol_str)
    o_str = pol_str.replace('*', '')
    ind_mid = o_str.find('/')
    while ind_mid != -1:
        ind_start = ind_mid - 1
        while ind_start >= 0 and o_str[ind_start] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ind_start -= 1
        ind_end = ind_mid + 1
        while ind_end < len(o_str) and o_str[ind_end] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ind_end += 1
        o_str = o_str[:ind_start + 1] + '\\frac{' + o_str[ind_start + 1:ind_mid] + '}{' + o_str[
            ind_mid + 1:ind_end] + '}' + o_str[ind_end:]
        ind_mid = o_str.find('/')

    ind_start = o_str.find('^')
    while ind_start != -1:
        ind_end = ind_start + 1
        while ind_end < len(o_str) and o_str[ind_end] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ind_end += 1
        o_str = o_str[:ind_start + 1] + '{' + o_str[ind_start + 1:ind_end] + '}' + o_str[ind_end:]
        ind_start = o_str.find('^', ind_end)

    return o_str





def to_ordinal(n):
    a = (n % 100) // 10
    if a == 1:
        return '%sth' % n
    b = n % 10
    if b == 1:
        return '%sst' % n
    elif b == 2:
        return '%snd' % n
    elif b == 3:
        return '%srd' % n
    else:
        return '%sth' % n



def add_space_if_positive(texified_pol):
    r"""
    Add a space if texified_pol is positive to match alignment of positive and
    negative coefficients.

    Examples:
    >>> add_space_if_positive('1')
    '\phantom{-}1'
    >>> add_space_if_positive('-1')
    '-1'
    """
    if texified_pol[0] == '-':
        return texified_pol
    return r"\phantom{-}" + texified_pol


def sparse_cyclotomic_to_latex(n, dat):
    r"""
    Take an element of Q(zeta_n) given in the form [[c1,e1],[c2,e2],...]
    and return sum_{j=1}^k cj zeta_n^ej in latex form as it is given
    (converting to sage will rewrite the element in terms of a basis)
    """

    dat.sort(key=lambda p: p[1])
    ans=''
    z = r'\zeta_{%d}' % n
    for p in dat:
        if p[0] == 0:
            continue
        if p[1]==0:
            if p[0] == 1 or p[0] == -1:
                zpart = '1'
            else:
                zpart = ''
        elif p[1]==1:
            zpart = z
        else:
            zpart = z+r'^{'+str(p[1])+'}'
        # Now the coefficient

        if p[0] == 1:
            ans += '+'  + zpart
        elif p[0] == -1:
            ans += '-'  + zpart
        else:
            ans += '{:+d}'.format(p[0])  + zpart
    ans= re.compile(r'^\+').sub('', ans)
    if ans == '':
        return '0'
    return ans


def dispZmat(mat):
    r""" Display a matrix with integer entries
    """
    s = r'\begin{pmatrix}'
    for row in mat:
        rw = '& '.join([str(z) for z in row])
        s += rw + '\\\\'
    s += r'\end{pmatrix}'
    return s


def dispcyclomat(n, mat):
    s = r'\begin{pmatrix}'
    for row in mat:
        rw = '& '.join(sparse_cyclotomic_to_latex(n, z) for z in row)
        s += rw + '\\\\'
    s += r'\end{pmatrix}'
    return s


def list_to_latex_matrix(li):
    """
    Given a list of lists representing a matrix, output a latex representation
    of that matrix as a string.

    Example:
    >>> list_to_latex_matrix([[1,0],[0,1]])
    '\\left(\\begin{array}{rr}1 & 0\\\\0 & 1\\end{array}\\right)'
    """
    dim = len(li[0])
    mm = r"\left(\begin{array}{"+dim*"r" +"}"
    mm += r"\\".join([" & ".join([str(a) for a in row]) for row in li])
    mm += r'\end{array}\right)'
    return mm

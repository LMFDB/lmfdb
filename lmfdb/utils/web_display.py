import re
from urllib.parse import urlencode
from markupsafe import escape
from flask import url_for
from sage.all import (
    Factorization,
    latex,
    ZZ,
    factor,
    RR,
    floor,
    PolynomialRing
)
from . import coeff_to_poly
################################################################################
#  latex/math rendering utilities
################################################################################


raw_count = 0
def raw_typeset(raw, typeset='', extra='', text_area=True, text_area_threshold=150):
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
    global raw_count
    raw_count += 1
    if not typeset:
        typeset = r'\({}\)'.format(latex(raw))

    srcloc = url_for('static', filename='images/t2r.png')

    # FIXME: fix javascript to resize textarea
    text_area = text_area and len(str(raw)) > text_area_threshold
    if text_area and len(str(raw)) > text_area_threshold:
        raw = f"""
        <textarea
        readonly=""
        rows="1"
        cols="60"
        style="line-height: 1; height: 13px";
        id="tset-raw-textarea-{raw_count}"
        >{raw}</textarea><span>
            <img
            class="copy"
            onclick="copyuncle(this)"
            ></span>
        """

    raw=escape(raw)
    out = f"""
<span class="tset-container">
    <span class="tset-raw tset" raw="{raw}" ondblclick="ondouble(this)">
    {typeset}
    </span>
    {extra}
    {"" if text_area else "&nbsp;&nbsp"}
    <span class="tset" onclick="iconrawtset(this)">
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
    latex_str =" %s " % latex(x) 
    return rf"\( {latex_str} \)" if enclose else latex_str

def bigint_knowl(n, cutoff=20, max_width=70, sides=2):
    if abs(n) >= 10**cutoff:
        short = str(n)
        short = short[:sides] + r'\!\cdots\!' + short[-sides:]
        lng = r"<div style='word-break: break-all'>%s</div>" % n
        return r'<a title="[bigint]" knowl="dynamic_show" kwargs="%s">\(%s\)</a>'%(lng, short)
    else:
        return r'\(%s\)'%n

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

def factor_base_factorization_latex(fbf):
    if len(fbf) == 0:
        return '1'
    ans = ''
    sign = 1
    for p, e in fbf:
        if p == -1:
            if (e % 2) == 1:
                sign *= -1
        elif e == 1:
            ans += r'\cdot %d' % p
        elif e != 0:
            ans += r'\cdot %d^{%d}' % (p, e)
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
    long = r'Defining polynomial: %s' % (web_latex(coeff_to_poly(f)))
    if cutoff:
        long = make_bigint(long, cutoff, max_width=70).replace('"',"'")
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
        A = r"\( %s \)" % latex(x)
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
 #   A = "\( %s \)" % latex(x)
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


def web_latex_poly(coeffs, var='x', superscript=True, bigint_cutoff=20,  bigint_overallmin=400):
    """
    Generate a web latex string for a given integral polynomial, or a linear combination
    (using subscripts instead of exponents).  In either case, the constant term is printed
    without a variable and bigint knowls are used if the coefficients are large enough.

    INPUT:

    - ``coeffs`` -- a list of integers
    - ``var`` -- a variable name
    - ``superscript`` -- whether to use superscripts (as opposed to subscripts)
    - ``bigint_cutoff`` -- the string length above which a knowl is used for a coefficient
    - ``bigint_overallmin`` -- the number of characters by which we would need to reduce the output to replace the large ints by knowls
    """
    plus = r" + "
    minus = r" - "
    m = len(coeffs)
    while m and coeffs[m-1] == 0:
        m -= 1
    if m == 0:
        return r"\(0\)"
    s = ""
    # we will have under/overflows if we try to use floats
    def cutout_digits(elt):
        digits = 1 if elt == 0 else floor(RR(abs(elt)).log(10)) + 1
        if digits > bigint_cutoff:
            # a large number would be replaced by ab...cd
            return digits - 7
        else:
            return 0

    if sum(cutout_digits(elt) for elt in coeffs) < bigint_overallmin:
        # this effectively disables the bigint
        bigint_cutoff = bigint_overallmin + 7

    for n in reversed(range(m)):
        c = coeffs[n]
        if n == 1:
            if superscript:
                varpow = "" + var
            else:
                varpow = r"%s_{1}"%var
        elif n > 1:
            if superscript:
                varpow = r"%s^{%s}"%(var, n)
            else:
                varpow = r"%s_{%s}"%(var, n)
        else:
            if c > 0:
                s += plus + str(c)
            elif c < 0:
                s += minus + str(-c)
            break
        if c > 0:
            s += plus
        elif c < 0:
            s += minus
        else:
            continue
        if abs(c) != 1:
            s += str(abs(c)) + " "
        s += varpow
    s += r"\)"
    if s.startswith(plus):
        res =  r"\(" + make_bigint(s[len(plus):], bigint_cutoff)
    else:
        res = r"\(-" + make_bigint(s[len(minus):], bigint_cutoff)
    return raw_typeset(PolynomialRing(ZZ, var.lstrip("\\"))(coeffs), res, text_area_threshold=100)


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

def dispcyclomat(n,mat):
    s = r'\begin{pmatrix}'
    for row in mat:
      rw = '& '.join([sparse_cyclotomic_to_latex(n,z) for z in row])
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

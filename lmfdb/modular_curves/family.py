
from sage.misc.lazy_attribute import lazy_attribute
from lmfdb.modular_curves.web_curve import get_bread

def ModCurveFamily(name):
    return get_family(name)

def get_family(name):
    try:
        return ALL_FAMILIES[name]
    except KeyError:
        raise ValueError(f"Invalid name '{name}'. Valid names: {list(ALL_FAMILIES.keys())}")

class ModCurveFamily_base():

    def __init__(self, famname=None, name=None, psl2index=None, nu2=None, nu3=None, cusps=None, genus_formula=None, hypell_level=None, biell_level=None, biell_nonhypell_level=None, hypell_description_text=None, biell_description_text=None, knowl_ID=None, notation=None):
        self.famname = famname
        self.name = name
        self.psl2index = psl2index
        self.nu2 = nu2
        self.nu3 = nu3
        self.cusps = cusps
        self.genus_formula = genus_formula
        self.hypell_level = hypell_level
        self.biell_level = biell_level
        self.biell_nonhypell_level = biell_nonhypell_level
        self.hypell_description_text = hypell_description_text
        self.biell_description_text = biell_description_text
        self.notation = notation
        self.knowl_ID = knowl_ID

    @lazy_attribute
    def bread(self):
        return get_bread([(f"${self.name}$", " ")])

    @lazy_attribute
    def title(self):
        return f"Modular curve family ${self.name}$"
    
    @lazy_attribute
    def cusps_display(self):
        return self.cusps

    @lazy_attribute
    def hypell_description(self):
        if self.hypell_description_text:
            return self.hypell_description_text.replace('NAME', self.name)
        return None

    @lazy_attribute
    def biell_description(self):
        if self.biell_description_text:
            return self.biell_description_text.replace('NAME', self.name)
        return None

X0 = ModCurveFamily_base(
    famname="X0",
    name="X_0(N)",
    psl2index=r"i = N\cdot \prod\limits_{p|N, \text{ prime}} \left(1 + \frac{1}{p}\right)",
    nu2=r"$\nu_2 = \begin{cases} 0, & \text{ if } N \equiv 0 \pmod{4}, \\ \prod\limits_{p|N, \text{prime}} \big( 1 + \big( \frac{-1}{p} \big) \big), & \text{otherwise.} \end{cases}$",
    nu3=r"$\nu_3 = \begin{cases} 0, & \text{ if } N \equiv 0 \pmod{9}, \\ \prod\limits_{p|N, \text{ prime}} \big( 1 + \big( \frac{-3}{p} \big) \big), & \text{otherwise.} \end{cases}$",
    cusps=r"$\nu_\infty = \sum\limits_{d|N, d>0} \varphi\left(\left(d,\frac{N}{d}\right)\right)$",
    knowl_ID = "modcurve.x0",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$",
    hypell_level="?level=22%2C+23%2C+26%2C+28%2C+29%2C+30%2C+31%2C+33%2C+35%2C+37%2C+39%2C+40%2C+41%2C+46%2C+47%2C+48%2C+50%2C+59%2C+71&family=X0",
    biell_level="?level=22%2C+26%2C+28%2C+30%2C+33%2C+34%2C+35%2C+37%2C+38%2C+39%2C+40%2C+42%2C+43%2C+44%2C+45%2C+48%2C+50%2C+51%2C+53%2C+54%2C+55%2C+56%2C+60%2C+61%2C+62%2C+63%2C+64%2C+65%2C+69%2C+72%2C+75%2C+79%2C+81%2C+83%2C+89%2C+92%2C+94%2C+95%2C+101%2C+119%2C+131&family=X0",
    biell_nonhypell_level="?level=34%2C+38%2C+42%2C+43%2C+44%2C+45%2C+51%2C+53%2C+54%2C+55%2C+56%2C+60%2C+61%2C+62%2C+63%2C+64%2C+65%2C+69%2C+72%2C+75%2C+79%2C+81%2C+83%2C+89%2C+92%2C+94%2C+95%2C+102%2C+119%2C+131&family=X0",
    hypell_description_text=r"""[<a href="https://mathscinet.ams.org/mathscinet/article?mr=364259">MR:364259</a>] showed that there are only 19 hyperellipic curves
                         in this family and [<a href="https://mathscinet.ams.org/mathscinet/article?mr=1150566">MR:1150566</a>] provided equations for these curves.
                         See the [<a href="https://beta.lmfdb.org/ModularCurve/Q/?level=22%2C+23%2C+26%2C+28%2C+29%2C+30%2C+31%2C+33%2C+35%2C+37%2C+39%2C+40%2C+41%2C+46%2C+47%2C+48%2C+50%2C+59%2C+71&family=X0">following table</a>] for the full list.""",
    biell_description_text=r"""[<a href="https://mathscinet.ams.org/mathscinet/article?mr=1688168">MR:1688168</a>] showed that there are only 41 biellipic curves
                       in this family and [<a href="https://mathscinet.ams.org/mathscinet/article?mr=3086199">MR:3086199</a>] provided equations for these curves.
                       Among them, there are 30 values for which they are non-hyperelliptic. See the
                       [<a href="https://beta.lmfdb.org/ModularCurve/Q/?level=22%2C+26%2C+28%2C+30%2C+33%2C+34%2C+35%2C+37%2C+38%2C+39%2C+40%2C+42%2C+43%2C+44%2C+45%2C+48%2C+50%2C+51%2C+53%2C+54%2C+55%2C+56%2C+60%2C+61%2C+62%2C+63%2C+64%2C+65%2C+69%2C+72%2C+75%2C+79%2C+81%2C+83%2C+89%2C+92%2C+94%2C+95%2C+101%2C+119%2C+131&family=X0">following table</a>]
                       for the full list and the [<a href="https://beta.lmfdb.org/ModularCurve/Q/?level=34%2C+38%2C+42%2C+43%2C+44%2C+45%2C+51%2C+53%2C+54%2C+55%2C+56%2C+60%2C+61%2C+62%2C+63%2C+64%2C+65%2C+69%2C+72%2C+75%2C+79%2C+81%2C+83%2C+89%2C+92%2C+94%2C+95%2C+102%2C+119%2C+131&family=X0">following table</a>] for the non-hyperelliptic list."""
)

X1 = ModCurveFamily_base(
    famname="X1",
    name="X_1(N)",
    psl2index=r"i = \begin{cases} 1, & \text{ if } N = 1, \\ 3, & \text{ if } N = 2, \\ \frac{N^2}{2}\cdot \prod\limits_{p|N, \text{ prime}} \left( 1 - \frac{1}{p^2} \right), & \text{ otherwise.}\end{cases}",
    nu2=r"$\nu_2 = \begin{cases} 1, & \text{ if } N =1,2, \\ 0, & \text{ otherwise.}\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases} 1, & \text{ if } N =1,3, \\ 0, & \text{ otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases} 1, & \text{ if } N =1, \\ 2, & \text{ if } N = 2, \\ 3, & \text{ if } N = 4, \\ \frac{1}{2} \cdot \sum\limits_{d|N,d>0} \varphi(d)\varphi\left(\frac{N}{d}\right), & \text{ otherwise.} \end{cases}$",
    knowl_ID = "modcurve.x1",
    genus_formula=r"$$g = 1 + \frac{i}{12} - \frac{\nu_2}{4} - \frac{\nu_3}{3} - \frac{\nu_\infty}{2}$$",
    hypell_level="?level=13%2C16%2C18&family=X1",
    biell_level="?level=13%2C16%2C17%2C18%2C20%2C21%2C22%2C24&family=X1",
    hypell_description_text=r"""[<a href="https://mathscinet.ams.org/mathscinet/article?mr=1138196">MR:1138196</a>] showed that there are only 3 hyperelliptic
                        curves in this family. See the [<a href="https://beta.lmfdb.org/ModularCurve/Q/?level=13%2C16%2C18&family=X1">following table</a>] for the full list.""",
    biell_description_text=r"""[<a href="https://mathscinet.ams.org/mathscinet/article?mr=2040593">MR:2040593</a>] showed that there are only 8 bielliptic
                       curves in this family. See the [<a href="https://beta.lmfdb.org/ModularCurve/Q/?level=13%2C16%2C17%2C18%2C20%2C21%2C22%2C24&family=X1">following table</a>] for the full list."""
)

X = ModCurveFamily_base(
    famname="X",
    name="X(N)",
    psl2index=r"i = \begin{cases} 6, & \text{ if } N = 2, \\ \frac{N^3}{2}\cdot \prod\limits_{p|N, \text{ prime}} \left( 1 - \frac{1}{p^2} \right), & \text{ if } N >2. \end{cases}",
    nu2=r"$\nu_2 = \begin{cases} 1, & \text{ if } N = 1, \\ 0, & \text{ if } N >1.\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases} 1, & \text{ if } N = 1, \\ 0, & \text{ if } N >1.\end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases} 1, & \text{ if } N = 1, \\ i/N, & \text{ if } N > 1. \end{cases}$",
    knowl_ID = "modcurve.xfull",
    genus_formula=r"$$g = 1 + \frac{i}{12} - \frac{\nu_2}{4} - \frac{\nu_3}{3} - \frac{\nu_\infty}{2}$$",
    hypell_description_text="None.",
    biell_description_text="None."
)

Xpm1 = ModCurveFamily_base(
    famname="Xpm1",
    name=r"X_{\pm 1}(N)",
    psl2index=r"i = \begin{cases} 1, & \text{ if } N = 1, \\ 3, & \text{ if } N = 2, \\ \frac{N^2}{2}\cdot \prod\limits_{p|N, \text{ prime}} \left( 1 - \frac{1}{p^2} \right), & \text{ otherwise.}\end{cases}",
    nu2=r"$\nu_2 = \begin{cases} 1, & \text{ if } N =1,2, \\ 0, & \text{ otherwise.}\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases} 1, & \text{ if } N =1,3, \\ 0, & \text{ otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases} 1, & \text{ if } N =1, \\ 2, & \text{ if } N = 2, \\ 3, & \text{ if } N = 4, \\ \frac{1}{2} \cdot \sum\limits_{d|N,d>0} \varphi(d)\varphi\left(\frac{N}{d}\right), & \text{ otherwise.} \end{cases}$",
    knowl_ID = "modcurve.xpm1",
    genus_formula=r"$$g = 1 + \frac{i}{12} - \frac{\nu_2}{4} - \frac{\nu_3}{3} - \frac{\nu_\infty}{2}$$"
)

Xarith1 = ModCurveFamily_base(
    famname="Xarith1",
    name=r"X_{\mathrm{arith},1}(M,MN)",
    psl2index=r"i = \begin{cases}1 & \text{if } M,N=1, \\ 3 & \text{if } M=1, \ N=2, \\ 6 & \text{if } M=2, \ N=1, \\ \frac{M^3N^2}{2} \cdot \prod\limits_{p|MN} \left(1 - \frac{1}{p^2}\right) & \text{otherwise.}\end{cases}",
    nu2=r"$\nu_2 = \begin{cases}1 & \text{if } M,N=1, \\ 1 & \text{if } M=2, \ N=1, \\ 0 & \text{otherwise.}\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases}1 & \text{if } M=1 \text{ and } N=1,3, \\ 0 & \text{otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases}1 & \text{if } M,N=1, \\ 2 & \text{if } M=1, \ N=2, \\ 3 & \text{if } M=1, \ N=4, \\ \frac{1}{2}\cdot \sum\limits_{d \mid MN } \varphi \left(\frac{MN}{d}\right) \varphi(d) \gcd \left(M,\frac{MN}{d}\right) & \text{otherwise.}\end{cases}$",
    knowl_ID = "modcurve.x1mn",
    genus_formula=r"$$g = 1 + \frac{i}{12} - \frac{\nu_2}{4} - \frac{\nu_3}{3} - \frac{\nu_\infty}{2}$$"
)

Xarithpm1 = ModCurveFamily_base(
    famname="Xarithpm1",
    name=r"X_{\mathrm{arith},\pm 1}(M,MN)",
    psl2index=r"i = \begin{cases}1 & \text{if } M,N=1, \\ 3 & \text{if } M=1, \ N=2, \\ 6 & \text{if } M=2, \ N=1, \\ \frac{M^3N^2}{2} \cdot \prod\limits_{p|MN} \left(1 - \frac{1}{p^2}\right) & \text{otherwise.}\end{cases}",
    nu2=r"$\nu_2 = \begin{cases}1 & \text{if } M,N=1, \\ 1 & \text{if } M=2, \ N=1, \\ 0 & \text{otherwise.}\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases}1 & \text{if } M=1 \text{ and } N=1,3, \\ 0 & \text{otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases}1 & \text{if } M,N=1, \\ 2 & \text{if } M=1, \ N=2, \\ 3 & \text{if } M=1, \ N=4, \\ \frac{1}{2}\cdot \sum\limits_{d \mid MN } \varphi \left(\frac{MN}{d}\right) \varphi(d) \gcd \left(M,\frac{MN}{d}\right) & \text{otherwise.}\end{cases}$",
    knowl_ID = "modcurve.xpm1mn",
    genus_formula=r"$$g = 1 + \frac{i}{12} - \frac{\nu_2}{4} - \frac{\nu_3}{3} - \frac{\nu_\infty}{2}$$"
)

Xsp = ModCurveFamily_base(
    famname="Xsp",
    name=r"X_{\mathrm{sp}}(N)",
    psl2index=r"i = N^2\cdot \prod\limits_{p|N, \text{ prime}} \left(1 + \frac{1}{p}\right)",
    nu2=r"$\nu_2 = \begin{cases}0 & \text{if $2\mid N$,} \\ \prod\limits_{p|N} \left( 1 + \left(\frac{-1}{p}\right) \right) & \text{otherwise.}\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases}0 & \text{if $2\mid N$ or $3\mid N$,} \\ \prod\limits_{p|N} \left(1 + \left(\frac{-3}{p}\right) \right) & \text{otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = N\cdot \prod\limits_{p|N, \text{ prime}} \left(1 + \frac{1}{p}\right)$",
    knowl_ID = "modcurve.xsp",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$"
)

Xspplus = ModCurveFamily_base(
    famname="Xspplus",
    name=r"X_{\mathrm{sp}}^+(N)",
    psl2index=r"i = \frac{N^2}{2}\cdot \prod\limits_{p|N, \text{ prime}} \left(1 + \frac{1}{p}\right)",
    nu2=r"$\nu_2 =  \left( \frac{N}{2}\cdot \prod\limits_{p\mid N, p \equiv 1 \bmod 4}\left( 1 - \frac{1}{p}\right) \cdot \prod\limits_{p\mid N, p \equiv 3 \bmod 4}\left(1 + \frac{1}{p}\right)\right) + \begin{cases}0 & \text{if $2\mid N$, } \\ \frac{1}{2}\cdot \prod\limits_{p|N} \left( 1 + \left(\frac{-1}{p}\right) \right) & \text{otherwise.}\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases}0 & \text{if $2\mid N$ or $3\mid N$,} \\ \frac{1}{2}\cdot \prod\limits_{p|N} \left(1 + \left(\frac{-3}{p}\right) \right) & \text{otherwise.}\end{cases} $",
    cusps=r"$\nu_\infty = \frac{N}{2}\cdot \prod\limits_{p|N, \text{ prime}} \left(1 + \frac{1}{p}\right)$",
    knowl_ID = "modcurve.xsp_plus",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$"
)

Xns = ModCurveFamily_base(
    famname="Xns",
    name=r"X_{\mathrm{ns}}(N)",
    psl2index=r"i = N \cdot \varphi(N)",
    nu2=r"$\nu_2 = \prod\limits_{p\mid N, p \text{ prime}} \left( 1 - \left(\frac{-1}{p}\right)\right)$",
    nu3=r"$\nu_3 = \begin{cases}2^{\omega(N)} & \text{if } p \equiv 2 \bmod 3 \text{ for all } p \mid N, \\ 0 & \text{otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = \varphi(N)$",
    knowl_ID = "modcurve.xns",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$",
    notation=r"<ul> <li>$\omega(N)$ is the number of primes dividing $N$.</li> </ul>"
)

Xnsplus = ModCurveFamily_base(
    famname="Xnsplus",
    name=r"X_{\mathrm{ns}}^+(N)",
    psl2index=r"i = \frac{N}{2} \cdot \varphi(N)",
    nu2=r"$\nu_2 = \sum\limits_{p\mid N} \frac{1- \left( \frac{-1}{p} \right)}{2} \ + \ \left(\frac{1}{2}N \cdot \prod\limits_{p|N}\left(1 + \frac{1}{p}\right) -\#S\right)$",
    nu3=r"$\nu_3 = \begin{cases}2^{\omega(N)-1} & \text{if } p \equiv 2 \bmod 3 \text{ for all } p \mid N, \\ 0 & \text{otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases}1 & \text{if } N=2, \\ \frac{1}{2}\cdot \varphi(N) & \text{otherwise.}\end{cases}$",
    knowl_ID = "modcurve.xns_plus",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$",
    notation=r"<ul> <li>$\omega(N)$ is the number of primes dividing $N$.</li> <li>$S = \{a+b\alpha \in (\mathbb{Z}/N\mathbb{Z})[\alpha]^\times/\pm 1 : N(a+b\alpha) = -1, \operatorname{gcd}(b,N) >1\}.$ </li> </ul>"
)

XS4 = ModCurveFamily_base(
    famname="XS4",
    name=r"X_{S_4}(\ell)",
    psl2index=r"i = \frac{1}{24}\cdot \ell\cdot (\ell^2 - 1)",
    nu2=r"$\nu_2 = \frac{1}{4}\cdot \left(\ell - \left(\frac{-1}{\ell}\right)\right)$",
    nu3=r"$\nu_3 = \frac{1}{3}\cdot \left(\ell - \left(\frac{-3}{\ell}\right)\right)$",
    cusps=r"$\nu_\infty = \frac{1}{24}\cdot (\ell^2 - 1)$",
    knowl_ID = "modcurve.xs4",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$"
)

Xarith = ModCurveFamily_base(
    famname="Xarith",
    name=r"X_{\mathrm{arith}}(N)",
    psl2index=r"i = \begin{cases}6, & \text{if } N=1, \\ \frac{N^3}{2}\cdot \prod\limits_{p\mid N, \text{prime}}\left(1-\frac{1}{p^2}\right), & \text{if } N>2. \end{cases}",
    nu2=r"$\nu_2 = \begin{cases}1, & \text{if } N=1, \\ 0, & \text{if } N>1. \end{cases}$",
    nu3=r"$\nu_3 = \begin{cases}1, & \text{if } N=1, \\ 0, & \text{if } N>1. \end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases}1, & \text{if } N=1,\\ i/N, & \text{if } N>1.\end{cases}$",
    knowl_ID = "modcurvexarith",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$",
    biell_level="?level=7%2C8&family=Xarith",
    hypell_description_text=r"""[<a href="https://mathscinet.ams.org/mathscinet/article?mr=3145452">MR:3145452</a>] showed that
                        there are no hyperelliptic curves in this family.""",
    biell_description_text=r"""[<a href="https://mathscinet.ams.org/mathscinet/article?mr=3145452">MR:3145452</a>] showed that there are only 2 bielliptic
                       curves in this family. $X_{\textup{arith}}(7)$ is isomorphic to the Klein quartic and $X_{\textup{arith}}(8)$
                       is isomorphic to the Wiman curve. See the [<a href="https://beta.lmfdb.org/ModularCurve/Q/?level=7%2C8&family=Xarith">following table</a>] for the full list."""
)

ALL_FAMILIES = {
    "X0": X0,
    "X1": X1,
    "X": X,
    "Xpm1": Xpm1,
    "Xarith1": Xarith1,
    "Xarithpm1": Xarithpm1,
    "Xsp": Xsp,
    "Xspplus": Xspplus,
    "Xns": Xns,
    "Xnsplus": Xnsplus,
    "XS4": XS4,
    "Xarith": Xarith,
}


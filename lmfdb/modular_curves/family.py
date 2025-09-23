from sage.misc.lazy_attribute import lazy_attribute
from lmfdb.modular_curves.web_curve import get_bread


def ModCurveFamily(name):
    try:
        return ALL_FAMILIES[name]
    except KeyError:
        raise ValueError(
            f"Invalid name '{name}'. Valid names: {list(ALL_FAMILIES)}"
        )

class ModCurveFamily_base:

    def __init__(
        self,
        famname=None,
        name=None,
        psl2index=None,
        nu2=None,
        nu3=None,
        cusps=None,
        genus_formula=None,
        knowl_ID=None,
        notation=None,
    ):
        self.famname = famname
        self.name = name
        self.psl2index = psl2index
        self.nu2 = nu2
        self.nu3 = nu3
        self.cusps = cusps
        self.genus_formula = genus_formula
        self.notation = notation
        self.knowl_ID = knowl_ID
        self.knowl_ID_remarks = self.knowl_ID + ".remarks"

    @lazy_attribute
    def bread(self):
        return get_bread([(f"${self.name}$", " ")])

    @lazy_attribute
    def title(self):
        return f"Modular curve family ${self.name}$"


X0 = ModCurveFamily_base(
    famname="X0",
    name="X_0(N)",
    psl2index=r"i = N\cdot \prod\limits_{p|N, \text{ prime}} \left(1 + \frac{1}{p}\right)",
    nu2=r"$\nu_2 = \begin{cases} 0, & \text{ if } N \equiv 0 \pmod{4}, \\ \prod\limits_{p|N, \text{prime}} \big( 1 + \big( \frac{-1}{p} \big) \big), & \text{otherwise.} \end{cases}$",
    nu3=r"$\nu_3 = \begin{cases} 0, & \text{ if } N \equiv 0 \pmod{9}, \\ \prod\limits_{p|N, \text{ prime}} \big( 1 + \big( \frac{-3}{p} \big) \big), & \text{otherwise.} \end{cases}$",
    cusps=r"$\nu_\infty = \sum\limits_{d|N, d>0} \varphi\left(\gcd\left(d,\frac{N}{d}\right)\right)$",
    knowl_ID="modcurve.x0",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$",
    notation=r'''<ul> <li>$\varphi(d)$ is the Euler totient function </li></ul>''',
)

X1 = ModCurveFamily_base(
    famname="X1",
    name="X_1(N)",
    psl2index=r"i = \begin{cases} 1, & \text{ if } N = 1, \\ 3, & \text{ if } N = 2, \\ \frac{N^2}{2}\cdot \prod\limits_{p|N, \text{ prime}} \left( 1 - \frac{1}{p^2} \right), & \text{ otherwise.}\end{cases}",
    nu2=r"$\nu_2 = \begin{cases} 1, & \text{ if } N =1,2, \\ 0, & \text{ otherwise.}\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases} 1, & \text{ if } N =1,3, \\ 0, & \text{ otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases} 1, & \text{ if } N =1, \\ 2, & \text{ if } N = 2, \\ 3, & \text{ if } N = 4, \\ \frac{1}{2} \cdot \sum\limits_{d|N,d>0} \varphi(d)\varphi\left(\frac{N}{d}\right), & \text{ otherwise.} \end{cases}$",
    knowl_ID="modcurve.x1",
    genus_formula=r"$$g = 1 + \frac{i}{12} - \frac{\nu_2}{4} - \frac{\nu_3}{3} - \frac{\nu_\infty}{2}$$",
)

X = ModCurveFamily_base(
    famname="X",
    name="X(N)",
    psl2index=r"i = \begin{cases} 6, & \text{ if } N = 2, \\ \frac{N^3}{2}\cdot \prod\limits_{p|N, \text{ prime}} \left( 1 - \frac{1}{p^2} \right), & \text{ if } N >2. \end{cases}",
    nu2=r"$\nu_2 = \begin{cases} 1, & \text{ if } N = 1, \\ 0, & \text{ if } N >1.\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases} 1, & \text{ if } N = 1, \\ 0, & \text{ if } N >1.\end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases} 1, & \text{ if } N = 1, \\ i/N, & \text{ if } N > 1. \end{cases}$",
    knowl_ID="modcurve.xfull",
    genus_formula=r"$$g = 1 + \frac{i}{12} - \frac{\nu_2}{4} - \frac{\nu_3}{3} - \frac{\nu_\infty}{2}$$",
)

Xpm1 = ModCurveFamily_base(
    famname="Xpm1",
    name=r"X_{\pm 1}(N)",
    psl2index=r"i = \begin{cases} 1, & \text{ if } N = 1, \\ 3, & \text{ if } N = 2, \\ \frac{N^2}{2}\cdot \prod\limits_{p|N, \text{ prime}} \left( 1 - \frac{1}{p^2} \right), & \text{ otherwise.}\end{cases}",
    nu2=r"$\nu_2 = \begin{cases} 1, & \text{ if } N =1,2, \\ 0, & \text{ otherwise.}\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases} 1, & \text{ if } N =1,3, \\ 0, & \text{ otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases} 1, & \text{ if } N =1, \\ 2, & \text{ if } N = 2, \\ 3, & \text{ if } N = 4, \\ \frac{1}{2} \cdot \sum\limits_{d|N,d>0} \varphi(d)\varphi\left(\frac{N}{d}\right), & \text{ otherwise.} \end{cases}$",
    knowl_ID="modcurve.xpm1",
    genus_formula=r"$$g = 1 + \frac{i}{12} - \frac{\nu_2}{4} - \frac{\nu_3}{3} - \frac{\nu_\infty}{2}$$",
    notation=r'''<ul> <li>$\varphi(d)$ is the Euler totient function </li>  </ul>''',
)

Xarith1 = ModCurveFamily_base(
    famname="Xarith1",
    name=r"X_{\mathrm{arith},1}(M,MN)",
    psl2index=r"i = \begin{cases}1 & \text{if } M,N=1, \\ 3 & \text{if } M=1, \ N=2, \\ 6 & \text{if } M=2, \ N=1, \\ \frac{M^3N^2}{2} \cdot \prod\limits_{p|MN} \left(1 - \frac{1}{p^2}\right) & \text{otherwise.}\end{cases}",
    nu2=r"$\nu_2 = \begin{cases}1 & \text{if } M,N=1, \\ 1 & \text{if } M=2, \ N=1, \\ 0 & \text{otherwise.}\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases}1 & \text{if } M=1 \text{ and } N=1,3, \\ 0 & \text{otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases}1 & \text{if } M,N=1, \\ 2 & \text{if } M=1, \ N=2, \\ 3 & \text{if } M=1, \ N=4, \\ \frac{1}{2}\cdot \sum\limits_{d \mid MN } \varphi \left(\frac{MN}{d}\right) \varphi(d) \gcd \left(M,\frac{MN}{d}\right) & \text{otherwise.}\end{cases}$",
    knowl_ID="modcurve.x1mn",
    genus_formula=r"$$g = 1 + \frac{i}{12} - \frac{\nu_2}{4} - \frac{\nu_3}{3} - \frac{\nu_\infty}{2}$$",
)

Xarithpm1 = ModCurveFamily_base(
    famname="Xarithpm1",
    name=r"X_{\mathrm{arith},\pm 1}(M,MN)",
    psl2index=r"i = \begin{cases}1 & \text{if } M,N=1, \\ 3 & \text{if } M=1, \ N=2, \\ 6 & \text{if } M=2, \ N=1, \\ \frac{M^3N^2}{2} \cdot \prod\limits_{p|MN} \left(1 - \frac{1}{p^2}\right) & \text{otherwise.}\end{cases}",
    nu2=r"$\nu_2 = \begin{cases}1 & \text{if } M,N=1, \\ 1 & \text{if } M=2, \ N=1, \\ 0 & \text{otherwise.}\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases}1 & \text{if } M=1 \text{ and } N=1,3, \\ 0 & \text{otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases}1 & \text{if } M,N=1, \\ 2 & \text{if } M=1, \ N=2, \\ 3 & \text{if } M=1, \ N=4, \\ \frac{1}{2}\cdot \sum\limits_{d \mid MN } \varphi \left(\frac{MN}{d}\right) \varphi(d) \gcd \left(M,\frac{MN}{d}\right) & \text{otherwise.}\end{cases}$",
    knowl_ID="modcurve.xpm1mn",
    genus_formula=r"$$g = 1 + \frac{i}{12} - \frac{\nu_2}{4} - \frac{\nu_3}{3} - \frac{\nu_\infty}{2}$$",
    notation=r'''<ul>    <li>$\varphi(d)$ is the Euler totient function </li>    </ul>''',
)

Xsp = ModCurveFamily_base(
    famname="Xsp",
    name=r"X_{\mathrm{sp}}(N)",
    psl2index=r"i = N^2\cdot \prod\limits_{p|N, \text{ prime}} \left(1 + \frac{1}{p}\right)",
    nu2=r"$\nu_2 = \begin{cases}0 & \text{if $2\mid N$,} \\ \prod\limits_{p|N} \left( 1 + \left(\frac{-1}{p}\right) \right) & \text{otherwise.}\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases}0 & \text{if $2\mid N$ or $3\mid N$,} \\ \prod\limits_{p|N} \left(1 + \left(\frac{-3}{p}\right) \right) & \text{otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = N\cdot \prod\limits_{p|N, \text{ prime}} \left(1 + \frac{1}{p}\right)$",
    knowl_ID="modcurve.xsp",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$",
)

Xspplus = ModCurveFamily_base(
    famname="Xspplus",
    name=r"X_{\mathrm{sp}}^+(N)",
    psl2index=r"i = \frac{N^2}{2}\cdot \prod\limits_{p|N, \text{ prime}} \left(1 + \frac{1}{p}\right)",
    nu2=r"$\nu_2 =  \left( \frac{N}{2}\cdot \prod\limits_{p\mid N, p \equiv 1 \bmod 4}\left( 1 - \frac{1}{p}\right) \cdot \prod\limits_{p\mid N, p \equiv 3 \bmod 4}\left(1 + \frac{1}{p}\right)\right) + \begin{cases}0 & \text{if $2\mid N$, } \\ \frac{1}{2}\cdot \prod\limits_{p|N} \left( 1 + \left(\frac{-1}{p}\right) \right) & \text{otherwise.}\end{cases}$",
    nu3=r"$\nu_3 = \begin{cases}0 & \text{if $2\mid N$ or $3\mid N$,} \\ \frac{1}{2}\cdot \prod\limits_{p|N} \left(1 + \left(\frac{-3}{p}\right) \right) & \text{otherwise.}\end{cases} $",
    cusps=r"$\nu_\infty = \frac{N}{2}\cdot \prod\limits_{p|N, \text{ prime}} \left(1 + \frac{1}{p}\right)$",
    knowl_ID="modcurve.xsp_plus",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$",
)

Xns = ModCurveFamily_base(
    famname="Xns",
    name=r"X_{\mathrm{ns}}(N)",
    psl2index=r"i = N \cdot \varphi(N)",
    nu2=r"$\nu_2 = \prod\limits_{p\mid N, p \text{ prime}} \left( 1 - \left(\frac{-1}{p}\right)\right)$",
    nu3=r"$\nu_3 = \begin{cases}2^{\omega(N)} & \text{if } p \equiv 2 \bmod 3 \text{ for all } p \mid N, \\ 0 & \text{otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = \varphi(N)$",
    knowl_ID="modcurve.xns",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$",
    notation=r'''<ul> <li>$\omega(N)$ is the number of primes dividing $N$.</li>
    <li>$\varphi(N)$ is the Euler totient function </li>
    </ul>''',
)

Xnsplus = ModCurveFamily_base(
    famname="Xnsplus",
    name=r"X_{\mathrm{ns}}^+(N)",
    psl2index=r"i = \frac{N}{2} \cdot \varphi(N)",
    nu2=r"$\nu_2 = \sum\limits_{p\mid N} \frac{1- \left( \frac{-1}{p} \right)}{2} \ + \ \left(\frac{1}{2}N \cdot \prod\limits_{p|N}\left(1 + \frac{1}{p}\right) -\#S\right)$",
    nu3=r"$\nu_3 = \begin{cases}2^{\omega(N)-1} & \text{if } p \equiv 2 \bmod 3 \text{ for all } p \mid N, \\ 0 & \text{otherwise.}\end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases}1 & \text{if } N=2, \\ \frac{1}{2}\cdot \varphi(N) & \text{otherwise.}\end{cases}$",
    knowl_ID="modcurve.xns_plus",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$",
    notation=r'''<ul> <li>$\omega(N)$ is the number of primes dividing $N$.</li>
    <li>$S = \{a+b\alpha \in (\mathbb{Z}/N\mathbb{Z})[\alpha]^\times/\pm 1 : N(a+b\alpha) = -1, \operatorname{gcd}(b,N) >1\}.$ </li>
    <li>$\varphi(N)$ is the Euler totient function </li>
    </ul>''',
)

XS4 = ModCurveFamily_base(
    famname="XS4",
    name=r"X_{S_4}(\ell)",
    psl2index=r"i = \frac{1}{24}\cdot \ell\cdot (\ell^2 - 1)",
    nu2=r"$\nu_2 = \frac{1}{4}\cdot \left(\ell - \left(\frac{-1}{\ell}\right)\right)$",
    nu3=r"$\nu_3 = \frac{1}{3}\cdot \left(\ell - \left(\frac{-3}{\ell}\right)\right)$",
    cusps=r"$\nu_\infty = \frac{1}{24}\cdot (\ell^2 - 1)$",
    knowl_ID="modcurve.xs4",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$",
)

Xarith = ModCurveFamily_base(
    famname="Xarith",
    name=r"X_{\mathrm{arith}}(N)",
    psl2index=r"i = \begin{cases}6, & \text{if } N=1, \\ \frac{N^3}{2}\cdot \prod\limits_{p\mid N, \text{prime}}\left(1-\frac{1}{p^2}\right), & \text{if } N>2. \end{cases}",
    nu2=r"$\nu_2 = \begin{cases}1, & \text{if } N=1, \\ 0, & \text{if } N>1. \end{cases}$",
    nu3=r"$\nu_3 = \begin{cases}1, & \text{if } N=1, \\ 0, & \text{if } N>1. \end{cases}$",
    cusps=r"$\nu_\infty = \begin{cases}1, & \text{if } N=1,\\ i/N, & \text{if } N>1.\end{cases}$",
    knowl_ID="modcurve.xarith",
    genus_formula=r"$$ g = 1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$$",
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

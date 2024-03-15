
from sage.misc.lazy_attribute import lazy_attribute
from lmfdb.modular_curves.web_curve import get_bread

def ModCurveFamily(name):
    if name == "X0N":
        return X0N()
    elif name == "X1N":
        return X1N()
    elif name == "XN":
        return XN()
    elif name == "XspN":
        return XspN()
    elif name == "XspplusN":
        return XspplusN()
    elif name == "XnsN":
        return XnsN()
    elif name == "XnsplusN":
        return XnsplusN()
    elif name == "XS4p":
        return XS4p()
    elif name == "XsymN":
        return XsymN()
    raise ValueError("Invalid name")

class ModCurveFamily_base():
    @lazy_attribute
    def bread(self):
        return get_bread([(f"${self.name}$", " ")])

    @lazy_attribute
    def title(self):
        return f"Modular curve family ${self.name}$"

class X0N(ModCurveFamily_base):
    name = "X_0(N)"
    sl2level = "N"
    index = "N+1"
    psl2index = r"i = N\cdot \prod_{p|N, \text{ prime}} (1 + p^{-1})"
    genus = "g"
    nu2 = r"$\nu_2 = \begin{cases} 0, & \text{ if } N \equiv 0 \pmod{4}, \\ \prod_{p|N, \text{prime}} \big( 1 + \big( \frac{-1}{p} \big) \big), & \text{otherwise.} \end{cases}$"
    nu3 = r"$\nu_3 = \begin{cases} 0, & \text{ if } N \equiv 0 \pmod{9}, \\ \prod_{p|N, \text{ prime}} \big( 1 + \big( \frac{-3}{p} \big) \big), & \text{otherwise.} \end{cases}$"
    cusps = r"$\nu_\infty = \sum_{d|N, d>0} \varphi((d,N/d))$"
    rational_cusps = "1"
    moduli_description = r"$X_0(N)$ is the modular curve $X_H$ for $H\le \GL_2(\widehat\Z)$ the inverse image of $\begin{pmatrix} \ast & \ast \\ 0 & \ast \end{pmatrix} \subset \GL_2(\Z/N\Z)$. As a moduli space it parameterizes pairs $(E,C)$, where $E$ is an elliptic curve over $k$, and $C$ is a $\Gal_k$-stable cyclic subgroup of $E[N](\overline{k})$ of order $N$ that is the kernel of a rational isogeny $E\to E'$ of degree $N$."
    genus_formula = r"The genus of $X_0(N)$ is $1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2}$."
    hypell_level = "?level=22%2C+23%2C+26%2C+28%2C+29%2C+30%2C+31%2C+33%2C+35%2C+37%2C+39%2C+40%2C+41%2C+46%2C+47%2C+48%2C+50%2C+59%2C+71&family=X0"
    biell_level = "?level=22%2C+26%2C+28%2C+30%2C+33%2C+34%2C+35%2C+37%2C+38%2C+39%2C+40%2C+42%2C+43%2C+44%2C+45%2C+48%2C+50%2C+51%2C+53%2C+54%2C+55%2C+56%2C+60%2C+61%2C+62%2C+63%2C+64%2C+65%2C+69%2C+72%2C+75%2C+79%2C+81%2C+83%2C+89%2C+92%2C+94%2C+95%2C+101%2C+119%2C+131&family=X0"
    biell_nonhypell_level = "?level=34%2C+38%2C+42%2C+43%2C+44%2C+45%2C+51%2C+53%2C+54%2C+55%2C+56%2C+60%2C+61%2C+62%2C+63%2C+64%2C+65%2C+69%2C+72%2C+75%2C+79%2C+81%2C+83%2C+89%2C+92%2C+94%2C+95%2C+102%2C+119%2C+131&family=X0"
    hypell_description = r'[<a href="https://mathscinet.ams.org/mathscinet/article?mr=364259">MR:364259</a>] showed that there are only 19 hyperellipic curves and [<a href="https://mathscinet.ams.org/mathscinet/article?mr=1150566">MR:1150566</a>] provided equations for these curves. See the [<a href="https://beta.lmfdb.org/ModularCurve/Q/?level=22%2C+23%2C+26%2C+28%2C+29%2C+30%2C+31%2C+33%2C+35%2C+37%2C+39%2C+40%2C+41%2C+46%2C+47%2C+48%2C+50%2C+59%2C+71&family=X0">following table</a>] for an explicit list.'
    biell_description = r'[<a href="https://mathscinet.ams.org/mathscinet/article?mr=1688168">MR:1688168</a>] showed that there are only 41 biellipic curves and [<a href="https://mathscinet.ams.org/mathscinet/article?mr=3086199">MR:3086199</a>] provided equations for these curves. Among them, there are 30 values for which they are non-hyperelliptic. See the [<a href="https://beta.lmfdb.org/ModularCurve/Q/?level=22%2C+26%2C+28%2C+30%2C+33%2C+34%2C+35%2C+37%2C+38%2C+39%2C+40%2C+42%2C+43%2C+44%2C+45%2C+48%2C+50%2C+51%2C+53%2C+54%2C+55%2C+56%2C+60%2C+61%2C+62%2C+63%2C+64%2C+65%2C+69%2C+72%2C+75%2C+79%2C+81%2C+83%2C+89%2C+92%2C+94%2C+95%2C+101%2C+119%2C+131&family=X0">following table</a>] for the full list and the [<a href="https://beta.lmfdb.org/ModularCurve/Q/?level=34%2C+38%2C+42%2C+43%2C+44%2C+45%2C+51%2C+53%2C+54%2C+55%2C+56%2C+60%2C+61%2C+62%2C+63%2C+64%2C+65%2C+69%2C+72%2C+75%2C+79%2C+81%2C+83%2C+89%2C+92%2C+94%2C+95%2C+102%2C+119%2C+131&family=X0">following table</a>] for the non-hyperelliptic list.'

    @lazy_attribute
    def cusps_display(self):
        return self.cusps

    @lazy_attribute
    def cusps_width_display(self):
        return "unknown"

    @lazy_attribute
    def cusps_orbits_display(self):
        return "one is rational"

    elliptic_points = "There are no elliptic points, unless N=1, in which case there are 2"

    @lazy_attribute
    def properties(self):
        return [("Level", "$N$"),
                (r"$SL_2$-level", str(self.sl2level)),
                ("Index", str(self.index)),
                ("Genus", str(self.genus))]

class X1N(ModCurveFamily_base):
    name = "X_1(N)"
    sl2level = "N"
    index = "N+1"
    psl2index = r"i = \begin{cases} 1, & \text{ if } N = 1, \\ 3, & \text{ if } N = 3, \\ \frac{N^2}{2}\prod_{p|N, \text{ prime}} \big( 1 - p^{-2} \big), & \text{ otherwise.}\end{cases}"
    genus = "g"
    nu2 = r"$\nu_2 = \begin{cases} 1, & \text{ if } N =1,2, \\ 0, & \text{ otherwise.}\end{cases}$"
    nu3 = r"$\nu_3 = \begin{cases} 1, & \text{ if } N =1,3, \\ 0, & \text{ otherwise.}\end{cases}$"
    cusps = r"$\nu_\infty = \begin{cases} 1, & \text{ if } N =1, \\ 2, & \text{ if } N = 2, \\ 3, & \text{ if } N = 4, \\ \frac{1}{2} \sum_{d|N,d>0} \varphi(d)\varphi(N/d), & \text{ otherwise.} \end{cases}$"
    rational_cusps = "1"
    moduli_description = r"$X_1(N)$ is the modular curve $X_H$ for $H\le \GL_2(\widehat\Z)$ the inverse image of $\begin{pmatrix} 1 & * \\ 0 & * \end{pmatrix} < \GL_2(\Z/N\Z)$. As a moduli space it parameterizes pairs $(E,P)$, where $E$ is an elliptic curve over $k$, and $P \in EN$ is a point of exact order $N$."
    genus_formula = r"The genus of $X_1(N)$ is $1 + \frac{ i }{12} - \frac{ \nu_2 }{4} - \frac{ \nu_3}{3} - \frac{ \nu_\infty}{2} = \begin{cases} 0, & \text{ if } N = 1,\ldots,5, \\ 1 + \frac{N^2}{24} \prod_{p|N, \text{ prime}} \big( 1 - p^{-2}\big) - \frac{1}{4} \sum_{d|N, d>0} \varphi(d)\varphi(N/d), & N \geq 5 \end{cases}$"

    @lazy_attribute
    def cusps_display(self):
        return self.cusps

    @lazy_attribute
    def cusps_width_display(self):
        return "unknown"

    @lazy_attribute
    def cusps_orbits_display(self):
        return "one is rational"

    elliptic_points = "There are no elliptic points, unless N=1, in which case there are 2"

    @lazy_attribute
    def properties(self):
        return [("Level", "$N$"),
                (r"$SL_2$-level", str(self.sl2level)),
                ("Index", str(self.index)),
                ("Genus", str(self.genus))]


class XN(ModCurveFamily_base):
    name = "X(N)"
    sl2level = "N"
    index = "N+1"
    psl2index = r"i = \begin{cases} 6, & \text{ if } N = 2, \\ \frac{N^3}{2}\prod_{p|N, \text{ prime}} \big( 1 - p^{-2} \big), & \text{ if } N >2. \end{cases}"
    genus = "g"
    nu2 = r"$\nu_2 = \begin{cases} 1, & \text{ if } N = 1, \\ 0, & \text{ if } N >1.\end{cases}$"
    nu3 = r"$\nu_3 = \begin{cases} 1, & \text{ if } N = 1, \\ 0, & \text{ if } N >1.\end{cases}$"
    cusps = r"$\nu_\infty = \begin{cases} 1, & \text{ if } N = 1, \\ i/2, & \text{ if } N > 1. \end{cases}$"
    rational_cusps = r"\nu_\infty = \begin{cases} 1, & \text{ if } N = 1, \\ i/2, & \text{ if } N > 1. \end{cases}"
    moduli_description = r"$X(N)$ is the modular curve $X_H$ for $H\le \GL_2(\widehat\Z)$ the inverse image of the trivial subgroup of $\GL_2(\Z/N\Z)$. As a moduli space it parameterizes triples $(E,P,Q)$, where $E$ is an elliptic curve over $k$, and $P,Q \in E(k)$ form a basis for $EN$. There are other variants. The canonical field of definition of $X(N)$ is $\Q(\zeta_N)$, which means that the database of modular curves $X_H/\Q$ only includes $X(N)$ for $N\le 2$."
    genus_formula = r"The genus of $X(N)$ is $g = \begin{cases} 0, & \text{ if } N = 1,2, \\ 1 + \frac{N^2 (N-6)}{24} \prod_{p|N, \text{ prime}} \big( 1 - p^{-2}\big), & N \geq 3 \end{cases}$."

    @lazy_attribute
    def cusps_display(self):
        return self.cusps

    @lazy_attribute
    def cusps_width_display(self):
        return "unknown"

    @lazy_attribute
    def cusps_orbits_display(self):
        return "one is rational"

    elliptic_points = "There are no elliptic points, unless N=1, in which case there are 2"

    @lazy_attribute
    def properties(self):
        return [("Level", "$N$"),
                (r"$SL_2$-level", str(self.sl2level)),
                ("Index", str(self.index)),
                ("Genus", str(self.genus))]


class XspN(ModCurveFamily_base):
    name = "X_{\mathrm{sp}}(N)"
    sl2level = "N"
    index = "N+1"
    psl2index = "N^2+1"
    genus = "g"
    nu2 = "0"
    nu3 = "0"
    cusps = "N/2"
    rational_cusps = "1"
    moduli_description = r"$X_{\text{sp}}(N)$ is the {{ KNOWL('modcurve','modular curve') }} for the subgroup $H\le \GL_2(\widehat\Z)$ given by the inverse image of a {{KNOWL('gl2.cartan', 'Cartan subgroup')}} $\begin{pmatrix} * & 0\\ 0& * \end{pmatrix}$ that is split at every prime dividing $N$. As a moduli space it parameterizes triples $(E,C,D)$ where $E$ is an elliptic curve over $k$, and $C$ and $D$ are $\Gal_k$-stable cyclic subgroups such that $EN\simeq C \oplus D$."
    genus_formula = r"The genus of $X_{\text{sp}}(N)$ is $g$."

    @lazy_attribute
    def cusps_display(self):
        return self.cusps

    @lazy_attribute
    def cusps_width_display(self):
        return "unknown"

    @lazy_attribute
    def cusps_orbits_display(self):
        return "one is rational"

    elliptic_points = "There are no elliptic points, unless N=1, in which case there are 2"

    @lazy_attribute
    def properties(self):
        return [("Level", "$N$"),
                (r"$SL_2$-level", str(self.sl2level)),
                ("Index", str(self.index)),
                ("Genus", str(self.genus))]


class XspplusN(ModCurveFamily_base):
    name = "X_{\mathrm{sp}}^+(N)"
    sl2level = "N"
    index = "N+1"
    psl2index = "N^2+1"
    genus = "g"
    nu2 = "0"
    nu3 = "0"
    cusps = "N/2"
    rational_cusps = "1"
    moduli_description = r"$X_{\text{sp}}^+(N)$ is the {{ KNOWL('modcurve','modular curve') }} $X_H$ for $H\le \GL_2(\widehat\Z)$ the inverse image of an {{KNOWL('gl2.cartan', 'extended Cartan subgroup')}} $\begin{pmatrix} * & 0 \\ 0 & * \end{pmatrix} \cup \begin{pmatrix} 0 & * \\ * & 0 \end{pmatrix}\subseteq \GL_2(\Z/N\Z)$ that is split at every prime dividing $N$. As a moduli space it parameterizes pairs $(E,\{C,D\})$ where $E$ is an elliptic curve over $k$, and $\{C,D\}$ is a $\Gal_k$-stable pair of cyclic subgroups such that $EN\simeq C \oplus D$. (Neither $C$ nor $D$ need be $\Gal_k$-stable.)"
    genus_formula = r"The genus of $X_{\text{sp}}^+(N)$ is $g$."

    @lazy_attribute
    def cusps_display(self):
        return self.cusps

    @lazy_attribute
    def cusps_width_display(self):
        return "unknown"

    @lazy_attribute
    def cusps_orbits_display(self):
        return "one is rational"

    elliptic_points = "There are no elliptic points, unless N=1, in which case there are 2"

    @lazy_attribute
    def properties(self):
        return [("Level", "$N$"),
                (r"$SL_2$-level", str(self.sl2level)),
                ("Index", str(self.index)),
                ("Genus", str(self.genus))]


class XnsN(ModCurveFamily_base):
    name = "X_{\mathrm{ns}}(N)"
    sl2level = "N"
    index = "N+1"
    psl2index = "N^2+1"
    genus = "g"
    nu2 = "0"
    nu3 = "0"
    cusps = "N/2"
    rational_cusps = "1"
    moduli_description = r"$X_{\text{ns}}(N)$ is $X_H$ for $H\le \GL_2(\widehat\Z)$ the inverse image of a {{KNOWL('gl2.cartan', 'Cartan subgroup')}} of $\GL_2(\Z/N\Z)$ that is nonsplit at every prime dividing $N$."
    genus_formula = r"The genus of $X_{\text{ns}}(N)$ is $g$."

    @lazy_attribute
    def cusps_display(self):
        return self.cusps

    @lazy_attribute
    def cusps_width_display(self):
        return "unknown"

    @lazy_attribute
    def cusps_orbits_display(self):
        return "one is rational"

    elliptic_points = "There are no elliptic points, unless N=1, in which case there are 2"

    @lazy_attribute
    def properties(self):
        return [("Level", "$N$"),
                (r"$SL_2$-level", str(self.sl2level)),
                ("Index", str(self.index)),
                ("Genus", str(self.genus))]


class XnsplusN(ModCurveFamily_base):
    name = "X_{\mathrm{ns}}^+(N)"
    sl2level = "N"
    index = "N+1"
    psl2index = "N^2+1"
    genus = "g"
    nu2 = "0"
    nu3 = "0"
    cusps = "N/2"
    rational_cusps = "1"
    moduli_description = r"$X_{\text{ns}}^+(N)$ is $X_H$ for $H\le \GL_2(\widehat\Z)$ the inverse image of an {{KNOWL('gl2.cartan', 'extended Cartan subgroup')}} of $\GL_2(\Z/N\Z)$ that is nonsplit at every prime dividing $N$."
    genus_formula = r"The genus of $X_{\text{ns}}^+(N)$ is $g$."

    @lazy_attribute
    def cusps_display(self):
        return self.cusps

    @lazy_attribute
    def cusps_width_display(self):
        return "unknown"

    @lazy_attribute
    def cusps_orbits_display(self):
        return "one is rational"

    elliptic_points = "There are no elliptic points, unless N=1, in which case there are 2"

    @lazy_attribute
    def properties(self):
        return [("Level", "$N$"),
                (r"$SL_2$-level", str(self.sl2level)),
                ("Index", str(self.index)),
                ("Genus", str(self.genus))]


class XS4p(ModCurveFamily_base):
    name = "X_{S_4}(p)"
    sl2level = "N"
    index = "N+1"
    psl2index = "N^2+1"
    genus = "g"
    nu2 = "0"
    nu3 = "0"
    cusps = "N/2"
    rational_cusps = "1"
    moduli_description = r"For $\ell$ an odd prime, $X_{S_4}(p)$ is the {{ KNOWL('modcurve','modular curve') }} $X_H$ for $H\le \GL_2(\widehat\Z)$ the inverse image of the subgroup of $\PGL_2(\Z/p\Z)$ isomorphic to $S_4$ (which is unique up to conjugacy). It parameterizes elliptic curves whose {{KNOWL('ec.galois_rep_modell_image','mod-$p$ Galois representation')}} has projective image $S_4$, one of the three exceptional groups $A_4$, $A_5$, $S_4$ of $\PGL_2(p)$ that can arise as projective mod-$p$ images, and the only one that can arise for elliptic curves over $\Q$. The subgroup $H$ contains $-I$ and has surjective determinant when $p \equiv \pm 3\bmod 8$, but not otherwise."
    genus_formula = r"The genus of $X_{S_4}(p)$ is $g$."

    @lazy_attribute
    def cusps_display(self):
        return self.cusps

    @lazy_attribute
    def cusps_width_display(self):
        return "unknown"

    @lazy_attribute
    def cusps_orbits_display(self):
        return "one is rational"

    elliptic_points = "There are no elliptic points, unless N=1, in which case there are 2"

    @lazy_attribute
    def properties(self):
        return [("Level", "$N$"),
                (r"$SL_2$-level", str(self.sl2level)),
                ("Index", str(self.index)),
                ("Genus", str(self.genus))]


class XsymN(ModCurveFamily_base):
    name = "X_{\mathrm{sym}}(N)"
    sl2level = "N"
    index = "N+1"
    psl2index = "N^2+1"
    genus = "g"
    nu2 = "0"
    nu3 = "0"
    cusps = "N/2"
    rational_cusps = "1"
    moduli_description = r"$X_{\mathrm{sym}}(N)$ is the modular curve $X_H$ for $H\leq \GL_2(\widehat{\Z})$ the inverse image of $\begin{pmatrix}1&0\\0&*\end{pmatrix}\leq \GL_2(\Z/N\Z)$. As a moduli space, $X_{\mathrm{sym}}$ parametrizes isomorphism classes of triples $(E,\phi,P)$, where $E$ is a generalized elliptic curve, $P$ is a point of exact order $N$, and $\phi \colon E \to E'$ is a cyclic $N$-isogeny such that $E[N]$ is generated by $P$ and $\ker\phi$. Alternatively, it parametrizes isomorphism classes of pairs $(E,\psi)$ where $E$ is a generalized elliptic curve and $\psi \colon \mu_N\times \Z/N\Z\xrightarrow{\sim} E[N]$ is a symplectic isomorphism."
    genus_formula = r"The genus of $X_{\mathrm{sym}}(N)$ is $g$."

    @lazy_attribute
    def cusps_display(self):
        return self.cusps

    @lazy_attribute
    def cusps_width_display(self):
        return "unknown"

    @lazy_attribute
    def cusps_orbits_display(self):
        return "one is rational"

    elliptic_points = "There are no elliptic points, unless N=1, in which case there are 2"

    @lazy_attribute
    def properties(self):
        return [("Level", "$N$"),
                (r"$SL_2$-level", str(self.sl2level)),
                ("Index", str(self.index)),
                ("Genus", str(self.genus))]

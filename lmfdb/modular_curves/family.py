
from sage.misc.lazy_attribute import lazy_attribute
from lmfdb.modular_curves.web_curve import get_bread

def ModCurveFamily(name):
    if name == "X0N":
        return X0N()
    elif name == "X1N":
        return X1N()
    elif name == "XN":
        return XN()
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
    psl2index = r"i\Gamma_0(N) = N\cdot \prod_{p|N, \text{ prime}} (1 + p^{-1})"
    genus = "g"
    nu2 = r"$\nu_2(\Gamma_0(N)) = \begin{cases} 0, & if N \equiv 0 \pmod{4}, \\ \prod_{p|N, \text{prime}} \big( 1 + \big( \frac{-1}{p} \big) \big), & \text{otherwise.} \end{cases}$"
    nu3 = r"$\nu_3(\Gamma_0(N)) = \begin{cases} 0, & if N \equiv 0 \pmod{9}, \\ \prod_{p|N, \text{ prime}} \big( 1 + \big( \frac{-3}{p} \big) \big), & \text{otherwise.} \end{cases}$"
    cusps = r"$\nu_\infty(\Gamma_0(N)) = \sum_{d|N, d>0} \varphi((d,N/d))$"
    rational_cusps = "1"
    moduli_description = r"$X_0(N)$ is the modular curve $X_H$ for $H\le \GL_2(\widehat\Z)$ the inverse image of $\begin{pmatrix} \ast & \ast \\ 0 & \ast \end{pmatrix} \subset \GL_2(\Z/N\Z)$. As a moduli space it parameterizes pairs $(E,C)$, where $E$ is an elliptic curve over $k$, and $C$ is a $\Gal_k$-stable cyclic subgroup of $E[N](\overline{k})$ of order $N$ that is the kernel of a rational isogeny $E\to E'$ of degree $N$."
    genus_formula = r"The genus of $X_0(N)$ is $1 + \frac{ i(\Gamma_0(N)) }{12} - \frac{ \nu_2(\Gamma_0(N)) }{4} - \frac{ \nu_3(\Gamma_0(N))}{3} - \frac{ \nu_\infty(\Gamma_0(N))}{2}$."
    
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
                ("Index", str(self.index)),
                ("Genus", str(self.genus))]

class X1N(ModCurveFamily_base):
    name = "X_1(N)"
    sl2level = "N"
    index = "N+1"
    psl2index = "i\Gamma_1(N) ="
    genus = "g"
    nu2 = "0"
    nu3 = "0"
    cusps = "N/2"
    rational_cusps = "1"
    moduli_description = r"$X_1(N)$ is the modular curve $X_H$ for $H\le \GL_2(\widehat\Z)$ the inverse image of $\begin{pmatrix} 1 & * \\ 0 & * \end{pmatrix} < \GL_2(\Z/N\Z)$. As a moduli space it parameterizes pairs $(E,P)$, where $E$ is an elliptic curve over $k$, and $P \in EN$ is a point of exact order $N$."
    genus_formula = r"The genus of $X_1(N)$ is $1 + \frac{ i(\Gamma_0(N)) }{12} - \frac{ \nu_2(\Gamma_0(N)) }{4} - \frac{ \nu_3(\Gamma_0(N))}{3} - \frac{ \nu_\infty(\Gamma_0(N))}{2} = \begin{cases} 0, & \text{ if } N = 1,\ldots,5, \\ 1 + \frac{N^2}{24} \prod_{p|N, \text{ prime}} \big( 1 - p^{-2}\big) - \frac{1}{4} \sum_{d|N, d>0} \varphi(d)\varphi(N/d), & N \geq 5 \end{cases}$, where $\varphi$ is the Euler totient function and \begin{itemize} \item $i(\Gamma_1(N)) = \begin{cases} 1, & \text{ if } N = 1, \\ 3, & \text{ if } N = 3, \\ \frac{N^2}{2}\prod_{p|N, \text{ prime}} \big( 1 - p^{-2} \big), & \text{ otherwise.}\end{cases}$ \item $\nu_2 = \begin{cases} 1, & \text{ if } N =1,2, \\ 0, & \text{ otherwise.}\end{cases}$  \item $\nu_3 = \begin{cases} 1, & \text{ if } N =1,3, \\ 0, & \text{ otherwise.}\end{cases}$  \item $\nu_\infty \begin{cases} 1, & \text{ if } N =1, \\ 2, & \text{ if } N = 2, \\ 3, & \text{ if } N = 4, \\ \frac{1}{2} \sum_{d|N,d>0} \varphi(d)\varphi(N/d), & \text{ otherwise.} \end{cases}$ \end{itemize}"

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
                ("Index", str(self.index)),
                ("Genus", str(self.genus))]


class XN(ModCurveFamily_base):
    name = "X(N)"
    sl2level = "N"
    index = "N+1"
    psl2index = "N^2+1"
    genus = "g"
    nu2 = "0"
    nu3 = "0"
    cusps = "N/2"
    rational_cusps = "1"
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
                ("Index", str(self.index)),
                ("Genus", str(self.genus))]

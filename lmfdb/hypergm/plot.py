from sage.all import lcm, gcd, I
from sage.plot.graphics import Graphics
from sage.plot.line import line
from sage.plot.circle import circle
from sage.plot.text import text
from sage.rings.rational import Rational
from sage.rings.complex_field import ComplexField
from sage.functions.log import exp
#from sage.symbolic.pynac import I

def circle_drops(A,B):
    # Drops going around the unit circle for those A and B.
    # See http://user.math.uzh.ch/dehaye/thesis_students/Nicolas_Wider-Integrality_of_factorial_ratios.pdf
    # for longer description (not original, better references exist)    
    marks = lcm(lcm(A),lcm(B))    
    tmp = [0 for i in range(marks)]
    for a in A:
#        print tmp
        for i in range(a):
            if gcd(i, a) == 1:
                tmp[i*marks/a] -= 1
    for b in B:
#        print tmp
        for i in range(b):
            if gcd(i, b) == 1:
                tmp[i*marks/b] += 1
#    print tmp
    return [sum(tmp[:j]) for j in range(marks)]
    
def piecewise_constant_image(A,B):
    # Jumps up and down going around circle, not used
    v = circle_drops(A,B)
    G = Graphics()
    w = [(Rational(i)/len(v), j) for i,j in enumerate(v)]
    for pt in w:
        G += line([(pt[0],pt[1]),(pt[0]+Rational(1)/len(w),pt[1])])
    return G

def piecewise_linear_image(A,B):
    # Jumps up and down going around circle, not used
    v = circle_drops(A,B)
    G = Graphics()
    w = [(Rational(i)/len(v), j) for i,j in enumerate(v)]
    for pt in w:
        G += line([(pt[0],pt[1]),(pt[0]+Rational(1)/len(w),pt[1])])
    return G
    
def circle_image(A,B):
    G = Graphics()
    G += circle((0,0), 1 , color = 'grey')
    from collections import defaultdict
    tmp = defaultdict(int)
    for a in A:
        for j in range(a):
            if gcd(j,a) == 1:
                rational = Rational(j)/Rational(a)
                tmp[(rational.numerator(),rational.denominator())] += 1
    
    for b in B:
        for j in range(b):
            if gcd(j,b) == 1:
                rational = Rational(j)/Rational(b)
                tmp[(rational.numerator(),rational.denominator())] -= 1
    C = ComplexField()
    for val in tmp:
        if tmp[val] > 0:
            G += text(str(tmp[val]),exp(C(-.2+2*3.14159*I*val[0]/val[1])), fontsize = 30, axes = False, color = "green")
        if tmp[val] < 0:
            G += text(str(abs(tmp[val])),exp(C(.2+2*3.14159*I*val[0]/val[1])), fontsize = 30, axes = False, color = "blue")
    return G

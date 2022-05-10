# This file is used to determine positions for discs in the image associated to a group

from collections import defaultdict, Counter
from colorsys import hsv_to_rgb
from sage.all import RR, ZZ, QQ
from sage.misc.lazy_attribute import lazy_attribute
from sage.misc.cachefunc import cached_function
from itertools import combinations
import heapq

eps = RR(0.00001) # tolerance
pi = RR.pi()

def distxy(P, Q):
    return ((P[0] - Q[0])**2 + (P[1] - Q[1])**2).sqrt()

def distrt(P, Q):
    return (P[0]**2 + Q[0]**2 - 2*P[0]*Q[0]*(P[1] - Q[1]).cos()).sqrt()

def distray(P, Q):
    # Distance to the ray starting at Q and going out
    R0, theta = Q
    if P[0] * (P[1] - theta).cos() >= R0:
        # The minimum distance to the theta line occurs on the ray, so we can just use the right triangle
        return P[0] * (P[1] - theta).sin().abs()
    else:
    # The minimum distance occurs at the inner radius
        return distrt(P, Q)

class ThetaRay:
    def __init__(self, R0, R1, theta):
        self.R0 = R0
        self.R1 = R1
        self.theta = theta

    @lazy_attribute
    def max_theta_span(self):
        # This is the largest difference between thetas for two touching circles in the annulus
        R0, R1 = self.R0, self.R1
        return (1 - 2*(R0 - R1)**2 / (R0 + R1)**2).arccos()

class Outside:
    def __init__(self, r):
        self.r = r
        self.x = RR(0)
        self.y = RR(0)
        self.R = RR(0)
        self.theta = RR(0)

    def distance(self, C):
        return self.r - C.R - C.r

class Circle:
    def __init__(self, r, o, x=None, y=None, R=None, theta=None, touching=[]):
        self.r = r # radius of circle
        self.o = o # order of corresponding conjugacy classe (for eventually determining color)
        self.touching = touching # the touching objects used to construct the center
        assert (x is not None and y is not None) or (R is not None and theta is not None)
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        if R is not None:
            self.R = R  # distance of center from origin
        if theta is not None:
            self.theta = theta

    @lazy_attribute
    def x(self):
        return self.R * self.theta.cos()

    @lazy_attribute
    def y(self):
        return self.R * self.theta.sin()

    @lazy_attribute
    def R(self):
        return (self.x**2 + self.y**2).sqrt()

    @lazy_attribute
    def theta(self):
        if self.x.abs() < eps**4:
            if self.y > 0:
                return pi / 2
            else:
                return 3*pi / 2
        elif self.y.abs() < eps**4:
            if self.x > 0:
                return RR(0)
            else:
                return pi
        at = (self.y / self.x).arctan()
        if self.x > 0:
            if self.y > 0:
                return at
            else:
                return at + 2*pi
        else:
            return at + pi

    def __hash__(self):
        return hash((self.R, self.theta, self.o))

    def __eq__(self, C):
        #### Better to use R,theta or x,y?
        #### Probably need to set a threshold since these are floats
        return (self.R, self.theta, self.r, self.o) == (C.R, C.theta, C.r, C.o)

    def in_annulus(self, R0, R1):
        return R0 + self.r <= self.R <= R1 - self.r

    def center_distance(self, C):
        if 'x' in self.__dict__ and 'x' in C.__dict__:
            return distxy((self.x, self.y), (C.x, C.y))
        elif 'R' in self.__dict__ and 'R' in C.__dict__:
            return distrt((self.R, self.theta), (C.R, C.theta))
        else:
            return distxy((self.x, self.y), (C.x, C.y))

    def distance(self, C):
        if isinstance(C, ThetaRay):
            # Unlike the other two cases, this is unsigned
            # Also note that this ignores the radius of the circle: we only use the center
            return distray((self.R, self.theta), (C.R0, C.theta))
        elif isinstance(C, Outside):
            return C.r - self.R - self.r
        else:
            return self.center_distance(C) - self.r - C.r

    def overlaps(self, C):
        # Note that you can't overlap a ThetaRay
        return self.distance(C) < 0

    def ok(self, others, thetaray):
        if self.R < thetaray.R0 + self.r - eps or self.R > thetaray.R1 - self.r + eps:
            return False
        # We need to worry near the beginning, since if thetaray.theta=0 then every theta works
        othetas = [C.theta for C in others if isinstance(C, Circle)]
        M = max(othetas) if othetas else 0
        if self.theta > M + thetaray.max_theta_span + eps:
            return False
        self.hd = self.hole_degree(others)
        return self.theta > thetaray.theta - eps and self.hd < 1 + eps

    def hole_degree(self, others):
        # We will want to use a manual cache so that we don't have to hash the inputs and can control when it gets updated
        dmin = None
        for C in others:
            if any(C is A for A in self.touching):
                continue
            d = self.distance(C)
            dmin = d if dmin is None else min(d, dmin)
            if dmin < -eps: # short circuit since we'll be throwing this circle away
                return 2 # anything bigger than 1 will delete the circle
        return 1 - dmin / self.r

# Most common orders below 512: 4 (2384226 ccs), 2, 8, 12, 6, 24, 1, 16, 20, 28, 3, 10, 14, 56, 30, 18, 40, 9, 48, 60, 5, 36, 15, 7, 26, 52, 32, 22, 44, 42, 21, 120, 27 (5046 ccs)
# We color based on 2-adic valuation and odd part.  Generally, a higher valuation is coded as darker, and we use the odd part to select a hue.
# The HSV color coordiantes are obtained from the following dictionary: the odd part gives the key, and the valuation is used to index into each list.
hsv = {
    1: (0, 95, [None, 100, 82, 66, 52, 40, 30, 22, 16]), # red; 1 is handled separately
    3: (220, 90, [90, 80, 70, 60, 50, 40, 30, 20]), # blue
    5: (30, 100, [100, 90, 80, 70, 60, 50, 40]), # orange
    7: (150, 65, [90, 80, 70, 60, 50, 40, 30]), # muddy green
    9: (280, 90, [90, 80, 70, 60, 50, 40, 30]), # violet
    11: (320, 90, [100, 82, 66, 52, 40, 30]), # purple
    13: (60, 80, [80, 70, 60, 50, 40, 30]), # yellow
    15: (175, 90, [90, 80, 70, 60, 50, 40]), # teal
    21: (90, 50, [80, 70, 60, 50, 40]), # chartreuse
}

@cached_function
def get_color(order):
    """
    Associate a rgb triple to a given order
    """
    if order == 1:
        return 255, 255, 255
    k, odd = order.val_unit(2)
    if odd in hsv:
        h, s, v = hsv[odd]
    else:
        h = (43*odd) % 360
        s = 60 + ((odd * 17) % 31)
        v = [90, 80, 70, 60, 50, 40, 30]
    def delist(comp):
        if isinstance(comp, list):
            i = k if k < len(comp) else -1
            comp = comp[i]
        return comp
    h, s, v = delist(h), delist(s), delist(v)
    rgb = hsv_to_rgb(h / 360.0, s / 100.0, v / 100.0)
    return round(255*rgb[0]), round(255*rgb[1]), round(255*rgb[2])

def get_radius(n):
    # For now we use a simple method
    return RR(n).sqrt()

def find_touching_centers(C1, C2, r, o):
    """
    Find the centers of the 0, 1 or 2 circles of radius r that simultaneously touch the circle of radius r1 and center c1, and the circle of radius r2 and center c2.  c1 and c2 are given in polar coordinates.
    """
    if isinstance(C1, Outside):
        C2, C1 = C1, C2
    if isinstance(C2, Outside) and isinstance(C1, ThetaRay):
        return [Circle(r, o, R=C2.r - r, theta=C1.theta, touching=[C1, C2])]
    if isinstance(C1, ThetaRay):
        C2, C1 = C1, C2
    if isinstance(C2, ThetaRay):
        # We solve for radii R so that (R, theta) has distance C1.r + r from the center of C1
        # (R^2 + C1.R^2 - 2 * C1.R * R * cos(theta - C1.theta)) = (C1.R + r)^2
        theta = C2.theta
        b = -2 * C1.R * (theta - C1.theta).cos()
        c = C1.R**2 - (C1.R + r)**2
        D = b**2 - 4*c
        if D < 0:
            return []
        if D == 0:
            R = -b / 2
            if R < 0:
                return []
            return [Circle(r, o, R=R, theta=theta, touching=[C1, C2])]
        RA = (-b + D.sqrt()) / 2
        RB = (-b - D.sqrt()) / 2
        if RA < 0:
            return []
        if RB < 0:
            return [Circle(r, o, R=RA, theta=theta, touching=[C1, C2])]
        return [Circle(r, o, R=RB, theta=theta, touching=[C1, C2]),
                Circle(r, o, R=RA, theta=theta, touching=[C1, C2])]
    if isinstance(C2, Outside):
        d = C1.R
        r1S = C1.r + r
        r2S = C2.r - r
        rS = r2S - r1S
        if d < rS - eps:
            return []
    else:
        d = C1.center_distance(C2)
        r1S = C1.r + r
        r2S = C2.r + r
        rS = r1S + r2S
        if d > rS + eps:
            return []
    # we solve for a point c3 that has distance r1S from the center of C1 and r2S from the center of C2
    if (d - rS).abs() < eps:
        x = C1.x * r2S / rS + C2.x * r1S / rS
        y = C1.y * r2S / rS + C2.y * r1S / rS
        return [Circle(r, o, x=x, y=y, touching=[C1, C2])]
    # (x - x1)^2 + (y - y1)^2 = (r1S)^2
    # (x - x2)^2 + (y - y2)^2 = (r2S)^2
    # change variables x' = x - x2, y' = y - y2 then
    # (x' + x2-x1)^2 + (y' + y2-y1)^2 = (r1S)^2
    # x'^2 + y'^2 = (r2S)^2
    # subtract/2: x'(x2 - x1) + y'(y2-y1) = ((r1S)^2 - (r2S)^2 - (x2-x1)^2 - (y2-y1)^2)/2 =: E
    # substitute into the second and scale by (y2-y1)^2: (y2-y1)^2 x'^2 + (E - x'(x2-x1))^2 = (r2S)^2 (y2-y1)^2
    # Expand for quadratic formula: ((y2-y1)^2 + (x2-x1)^2)x'^2 - 2E(x2-x1) x' + E^2 - (r2S)^2 (y2-y1)^2 = 0
    xD = C2.x - C1.x
    yD = C2.y - C1.y
    E = (r1S**2 - r2S**2 - xD**2 - yD**2) / 2
    a = yD**2 + xD**2
    if xD.abs() < yD.abs():
        b = -2*E*xD
        c = E**2 - (r2S*yD)**2
        D = b**2 - 4*a*c
        assert D > -eps
        if D < 0:
            D = RR(0)
        D = D.sqrt()
        xprimeA = -(b+D)/(2*a)
        xprimeB = -(b-D)/(2*a)
        xA = C2.x + xprimeA
        xB = C2.x + xprimeB
        yA = C2.y + (E - xprimeA*xD) / yD
        yB = C2.y + (E - xprimeB*xD) / yD
    else:
        b = -2*E*yD
        c = E**2 - (r2S*xD)**2
        D = b**2 - 4*a*c
        assert D > -eps
        if D < 0:
            D = RR(0)
        D = D.sqrt()
        yprimeA = -(b+D)/(2*a)
        yprimeB = -(b-D)/(2*a)
        yA = C2.y + yprimeA
        yB = C2.y + yprimeB
        xA = C2.x + (E - yprimeA*yD) / xD
        xB = C2.x + (E - yprimeB*yD) / xD
    ans = [Circle(r, o, x=xA, y=yA, touching=[C1, C2]),
           Circle(r, o, x=xB, y=yB, touching=[C1, C2])]
    for C, d in [(C1, r1S), (C2, r2S)]:
        for Ca in ans:
            assert C.distance(Ca).abs() < eps
    return ans

def find_touching_ontheta(C1, theta, r, o):
    """
    Find the centers of the 0, 1, or 2 circles of radius r that have center on the theta ray and touches the circle of radius r1 and center c1.  c1 is given in polar coordinates.

    Unlike find_touching_centers, we don't allow being inside a circle (since this case is easily handled in our application)
    """

def place_segment(segment, R0, R1, thetamin, placed, last):
    o, radii = segment
    #print("place_segment", R0, R1, radii)
    zero = RR(0)
    # Make a copy of radii since we'll be modifying it
    radii = Counter(radii)
    rmax = max(radii)
    inner = Circle(R0, None, zero, zero, zero, zero)
    outer = Outside(R1)
    thetaray = ThetaRay(R0, R1, thetamin)
    endray = ThetaRay(R0, R1, zero)
    constructive = [inner, thetaray, outer]
    to_check = []
    # We filter the placed circles to eliminate ones that can't possibly interfere with this segment.
    for C in placed:
        d = C.distance(thetaray)
        if d < C.r + rmax:
            constructive.append(C)
        else:
            # We still may want to include C if it's near theta=0
            d = C.distance(endray)
            if d < C.r + rmax:
                if last:
                    constructive.append(C)
                else:
                    to_check.append(C)
    # We start by constructing corner placements from the circles in constructive, together with the thetamin ray and the outside of the annulus
    corners = []
    avoid = constructive + to_check
    for A, B in combinations(constructive, 2):
        for r in radii:
            for C in find_touching_centers(A, B, r, o):
                if C.ok(avoid, thetaray):
                    assert C.R > R0
                    corners.append(C)
    fixed = [] # this list stores the placements that have been made
    while corners:
        tophd = None
        for C in corners:
            if tophd is None or C.hd > tophd + eps:
                tophd = C.hd
                best = C
        #print(f"Placed at R={best.R}, theta={best.theta}")
        fixed.append(best)
        constructive.append(best)
        avoid.append(best)
        if radii[best.r] == 1:
            del radii[best.r]
            corners = [C for C in corners if C.r != best.r]
        else:
            radii[best.r] -= 1
            corners = [C for C in corners if C is not best]
        i = 0
        while i < len(corners):
            C = corners[i]
            d = C.distance(best)
            if d < 0:
                # C no longer valid
                corners.pop(i)
            else:
                C.hd = max(C.hd, 1 - d/C.r)
                i += 1
        for A in constructive:
            if A is best:
                continue
            for r in radii:
                for C in find_touching_centers(A, best, r, o):
                    if C.ok(avoid, thetaray):
                        corners.append(C)
    return not radii, fixed

def pack(rdata, R0, rmax):
    """
    INPUT:

    - ``rdata`` -- a list of pairs `(r, o)` to be packed into an annulus
    - ``R0`` -- the inner radius of the annulus
    - ``rmax`` -- the maximum radius of any circle to be packed

    OUTPUT:

    - a list of tuples `(x, y, r, rgb)` as in the output of find_packing
    - the incremental radius of the annulus used
    """
    # If there are few enough circles, we space them out around the annulus with uniform gaps
    # We approximate the intersections as happening at radius R0+rmax, then check that this doesn't cause problems
    rdata = sorted(rdata, key=lambda pair: (-pair[1].valuation(2), -pair[1].valuation(3), pair[1], -pair[0]))
    #print("Packing", R0, rmax, rdata)
    radii = [r for (r, o) in rdata]
    Rc = R0 + rmax
    thetasum = sum(2*r / Rc for r in radii)
    if thetasum < 2*pi:
        thetaspace = (2*pi - thetasum) / len(rdata)
        thetas = [RR(0)]
        for i in range(len(rdata) - 1):
            thetas.append(thetas[i] + (radii[i] + radii[i+1])/Rc + thetaspace)
        pos = [(Rc * theta.cos(), Rc * theta.sin()) for theta in thetas]
        if all(distxy(pos[i], pos[(i+1) % len(pos)]) >= radii[i] + radii[(i+1) % len(pos)] for i in range(len(pos))):
            return [(x, y, r, get_color(o)) for ((r, o), (x, y)) in zip(rdata, pos)], R0 + 2*rmax
    area = sum(r**2 for r in radii) # actually area/pi
    density = 0.86
    segments = []
    for i, (r, o) in enumerate(rdata):
        if i != 0 and o == rdata[i-1][1]:
            segments[-1][1][r] += 1
        else:
            segments.append((o, Counter({r: 1})))
    while True:
        R1 = (R0**2 + area / density).sqrt()
        squeezed = (R1 < R0 + 2*rmax)
        if squeezed:
            R1 = R0 + 2*rmax # 4*R0*rmax + 4*rmax^2 = area/density
        #print("Looping", density, R1, R0+2*rmax)
        placed = []
        thetamin = RR(0)
        for sctr, segment in enumerate(segments):
            ok, placements = place_segment(segment, R0, R1, thetamin, placed, sctr == len(segments) - 1)
            if not ok:
                break
            thetamin = max(C.theta for C in placements)
            placed.extend(placements)
        else:
            return [(C.x, C.y, C.r, get_color(C.o)) for C in placed], R1
        if squeezed:
            density = area / (4 * rmax * (R0 + rmax))
        density -= 0.01

def clear_zeros(D):
    """
    Removes 0 values from the dictionary
    """
    for k, v in list(D.items()):
        if v == 0:
            del D[k]

def arrange_ring(radii, colors, R0, rmax):
    clear_zeros(radii)
    for D in colors.values():
        clear_zeros(D)
    Rc = R0 + rmax
    thetasum = sum(2*r*cnt / Rc for r, cnt in radii.items())
    if thetasum > 2*pi:
        return False, None
    # Probably possible to put all the discs in one ring
    # First attempt: arrange the discs with equally spaced centers
    n = sum(radii.values())
    thetadiff = (2*pi / n)
    dist = Rc*(2 - 2*thetadiff.cos()).sqrt() # distance between centers in equal space case
    if len(radii) == 1:
        r = next(iter(radii))
        placed = [r for i in range(n)]
    else:
        invcnt = {r: QQ(1) / radii[r] for r in radii}
        # We assign radii greedily, by keeping track of the radius with the highest
        # proportion not yet placed.  We start by alternating between big and small
        # and smaller circles.
        srad = sorted(radii, reverse=True)
        srad = [srad[(-1)**i * ((i+1)//2)] for i in range(len(srad))]
        placed = list(srad)
        remaining = [(QQ(-1) + invcnt[srad[i]], i) for i in range(len(srad))]
        #print("Initial", remaining)
        heapq.heapify(remaining)
        cur = heapq.heappop(remaining)
        while len(placed) < n:
            #print(cur, remaining)
            placed.append(srad[cur[1]])
            cur = heapq.heappushpop(remaining, (cur[0] + invcnt[srad[cur[1]]], cur[1]))
    #print("radii", radii)
    #print("colors", colors)
    #print(placed)
    # Now assign colors in a similar way
    color_placed = {}
    for r in radii:
        col = next(iter(colors[r]))
        if len(colors[r]) == 1:
            color_placed[r] = [col for i in range(radii[r])]
        else:
            invcnt = {c: QQ(1) / colors[r][c] for c in colors[r]}
            color_placed[r] = [col]
            remaining = [(QQ(-1), c) for c in colors[r] if c != col]
            cur = (QQ(-1), col)
            heapq.heapify(remaining)
            while len(color_placed[r]) < radii[r]:
                cur = heapq.heappushpop(remaining, (cur[0] + invcnt[cur[1]], cur[1]))
                color_placed[r].append(cur[1])
    #print(color_placed)
    if len(radii) == 1 or len(radii) == 2 and len(set(radii.values())) == 2:
        # There will be two circles of max radii adjacent
        equal_centers = (2*rmax < dist + eps)
    else:
        equal_centers = True
        for i in range(len(placed)):
            if placed[i] + placed[(i+1)%len(placed)] > dist + eps:
                equal_centers = False
                break
    if not equal_centers:
        theta_diffs = []
        for i, r in enumerate(placed):
            nextr = placed[(i+1)%len(placed)]
            theta_diffs.append((1 - (r + nextr)**2 / (2*Rc**2)).arccos())
        thetasum = sum(theta_diffs)
        if thetasum > 2*pi + eps:
            return False, None
        thetaspace = (2*pi - thetasum) / n
    theta = RR(0)
    circles = []
    for i, r in enumerate(placed):
        c = color_placed[r].pop(0)
        circles.append((Rc * theta.cos(), Rc * theta.sin(), r, c))
        if not equal_centers:
            thetadiff = theta_diffs[i] + thetaspace
            #nextr = placed[(i+1)%len(placed)]
            #thetadiff = (r + nextr)/Rc + thetaspace
            ## d^2 = 2Rc^2(1-cos(thetadiff))
            #if 2 * Rc**2 * (1 - thetadiff.cos()) > (r + nextr)**2 + eps:
            #    # need to use more than one ring
            #    print(f"{i}/{len(placed)}", thetaspace, thetadiff, 2 * Rc**2 * (1 - thetadiff.cos()), (r + nextr)**2)
            #    return False, None
        theta += thetadiff
    return circles, Rc + rmax

def arrange_rings(radii, colors, R0, rmax):
    Rc = R0 + rmax
    rmax0 = rmax
    num_rings = 1
    thetaleft = 2*pi
    # We first need to get a count of how many rings to use.  We greedily assign discs to annuli
    for r, cnt in sorted(radii.items(), reverse=True):
        # (2*r)^2 = 2*R^2*(1-cos(theta))
        thetaneeded = (1 - 2*r**2 / Rc**2).arccos()
        while thetaneeded * cnt > thetaleft:
            cnt -= (thetaleft / thetaneeded).floor()
            num_rings += 1
            thetaleft = 2*pi
            Rc += rmax + r
            rmax = r
            thetaneeded = (1 - 2*r**2 / Rc**2).arccos()
        thetaleft -= thetaneeded * cnt
    utilization = min((num_rings - thetaleft/(2*pi)) / num_rings, 1)
    while True:
        rmax = rmax0
        rings = [(Counter(), defaultdict(Counter), R0, rmax)]
        Rc = R0 + rmax
        thetaleft = 2*pi * utilization
        for r, cnt in sorted(radii.items(), reverse=True):
            thetaneeded = (1 - 2*r**2 / Rc**2).arccos()
            rcolors = Counter(colors[r])
            #orderlist = [o for (o, ocnt) in sorted(orders.items(), reverse=True) for j in range(ocnt)]
            while thetaneeded * cnt > thetaleft:
                this_ring = (thetaleft / thetaneeded).floor()
                if this_ring > 0:
                    cnt -= this_ring
                    rings[-1][0][r] += this_ring
                    for c, ccnt in sorted(rcolors.items(), reverse=True):
                        if ccnt <= this_ring:
                            rings[-1][1][r][c] += ccnt
                            rcolors.pop(c)
                        else:
                            rings[-1][1][r][c] += this_ring
                            rcolors[c] -= this_ring
                            break
                        this_ring -= ccnt
                R0 += 2*rmax
                rings.append((Counter(), defaultdict(Counter), R0, r))
                thetaleft = 2*pi * (1 if len(rings) == num_rings else utilization)
                Rc += rmax + r
                rmax = r
                thetaneeded = (1 - 2*r**2 / Rc**2).arccos()
            rings[-1][0][r] += cnt
            rings[-1][1][r].update(rcolors)
            thetaleft -= thetaneeded * cnt
        #print("rings", num_rings, utilization, rings)
        if len(rings) == num_rings or utilization == 1:
            rings = [arrange_ring(*ring)[0] for ring in rings]
            #print("rings2", rings)
            if all(isinstance(ring, list) for ring in rings): # all succeeded
                return sum(rings, []), Rc + rmax
        # If we require inner rings to not be fully utilized,
        # that might not leave enough space in outer rings
        #print("num_rings", num_rings, utilization)
        if utilization == 1:
            # This can happen because we were packing equal size circles together in estimating
            # utilization, but when calling arrange_ring we alternate which is less space
            # efficient.
            num_rings += 1
            utilization = 0.7
        elif utilization > 0.9:
            # just use all the space we have
            utilization = 1
        else:
            utilization += 0.1

def arrange(rdata, R0, rmax):
    radii = Counter([r for (r, o) in rdata])
    colors = {r: Counter() for r in radii}
    for (r, o) in rdata:
        colors[r][get_color(o)] += 1
    circles, R1 = arrange_ring(radii, colors, R0, rmax)
    if circles:
        return circles, R1
    #rmin = min(radii)
    if True: #rmax < 3 * rmin:
        # the circles are close to the same size.  We divide them up into concentric rings greedily
        return arrange_rings(radii, colors, R0, rmax)
    # Fall back for now; look at 310.4 for an example
    return pack(rdata, R0, rmax)

def find_packing(ccdata):
    """
    INPUT:

    - ``ccdata`` -- a list of pairs `(n, o)` of Integers, one for each conjugacy class, giving the size `n` and order `o`

    OUTPUT:

    - a list of tuples `(x, y, r, rgb)` giving centers `(x, y)`, radii `r` and color triple `rgb` for the image associated to this conjugacy class data
    - a real number `R` so that all circles will be contained within the box [-R, R] x [-R, R]
    """
    by_pcount = defaultdict(list)
    for (n, o) in ccdata:
        n, o = ZZ(n), ZZ(o)
        if o != 1:
            by_pcount[sum(e for (p, e) in o.factor())].append((get_radius(n), o))
    r0 = R = get_radius(1)
    circles = [(RR(0), RR(0), r0, get_color(ZZ(1)))]
    for pcnt in sorted(by_pcount):
        # Add a gap between annuli
        annulus = by_pcount[pcnt]
        r1 = max(r for (r, o) in annulus)
        R += max(r0, r1)
        r0 = r1
        new_circles, R = arrange(annulus, R, r0)
        circles.extend(new_circles)
    return circles, R

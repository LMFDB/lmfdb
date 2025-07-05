import svg
from sage.all import (floor, round)

class Point:
    """
    Point in (x,y)-plane adapted for drawing to svg canvas
    """
    def __init__(self,
                 x: float,
                 y: float,
                 girth: float = 1,
                 color: str = "black"):
        self.x = round(x,3)
        self.y = round(y,3)
        self.girth = girth
        self.color = color

    def __iter__(self):
        return iter((self.x, self.y))

    def __str__(self):          # for debugging
        return f"Point ({self.x}, {self.y}) of girth {self.girth} and color {self.color}"

    def __add__(self,other):
        return Point(self.x + other.x, self.y + other.y)

    def draw(self, radius):
        return svg.Circle(
            cx=self.x,
            cy=self.y,
            r=radius,
            fill=self.color,
            stroke='black',
            stroke_width=.75)

def draw_spec(frobs, local_alg_dict, colors=True, rings=False, num_primes=100, gaga=False) -> svg.SVG:
    """ Draw the spectrum of the ring of integers of a number field,
    from data in the lmfdb.
    `frobs` is a list of lists [[p, [frob_cycle1,...,frob_cycleN]]]
    `local_algs` is a list of strings describing ramification behaviour ['p.deg.(other stuff)', ..., ]
    If `colors` is `True`, color classes which lie in the same Frobenius cycle
    """
    num_primes = min(len(frobs), num_primes)
    frobs = frobs[:num_primes]

    ### Options:
    # I've hardcoded these values instead of providing them
    # as optional arguments; feel free to change this

    # (absolute) height of svg
    height = 80 if gaga else 150

    # (absolute) width of svg
    width = 200 if gaga else (num_primes+3)*50

    # distance between two primes along x-axis
    x_spread = floor(width/(num_primes+1)) if gaga else 50

    # distance between prime ideals in same fibre
    # = total distance from top to bottom
    y_spread = 30

    # y-coordinate of Spec Z
    bottom_line = round((3/4)*height)

    # fraction of height of centre line around which the primes in spec are centred
    centre_ratio = 1/2 if gaga else 1/4
    # y-coordinate of Spec O_K
    y_centre = round(centre_ratio*height)

    line_thickness = .75

    # increase or decrease girth of inert primes based on size of residue field
    residue_factor = .7

    # radius of (unramified) points
    dot_radius = 2.5
    # parameter to control the cubic bezier curves.
    # Should probably be between 0 and 2, with 1 being "reasonable"
    curviness = 0.9

    elements = []
    # NB: svg y-coords start from top! eg (0,1) is 1 unit down from top left corner

    # list of coordinates, where the n-th member is a
    # list of Points in the n-th fibre
    coords = []
    for n, [p, l] in enumerate(frobs):
        x_coord = (n+1)*x_spread
        if l == [0]:
            coords.append(ram_coords(
                local_alg_dict, p, x_coord, y_centre, y_spread))
        else:
            coords.append(unram_coords(
                l, x_coord, y_centre, y_spread))

    # draw Spec Z line at the bottom
    if not gaga:
        elements.append(
            svg.Line(
                stroke="black",
                stroke_width=line_thickness,
                x1=coords[0][0].x, # get starting point of line
                y1=bottom_line,
                x2=coords[-1][0].x + x_spread,
                y2=bottom_line))

        # a dashed line afterwards to signify generic fibre
        for y in (bottom_line, y_centre):
            elements.append(
                svg.Line(
                    stroke="black",
                    stroke_width=line_thickness,
                    stroke_dasharray="5",
                    x1=coords[-1][0].x + x_spread,
                    y1=y,
                    x2=coords[-1][0].x + 2*x_spread,
                    y2=y
                )
            )
            elements.append(svg.Text(
                x=width - x_spread,
                y=y,
                dx=16,
                dy=4,
                text='(0)',
                text_anchor="middle"))

    # draw curves between primes - do this first so points drawn over curve
    nextpts = coords if gaga else coords + [[Point(width-2*x_spread, y_centre)]]
    for n in range(len(nextpts)-1):
        for pt_this in coords[n]:
            for pt_next in nextpts[n + 1]:
                # we control the angle of the curve by adding a control point
                dx = curviness*round((pt_next.x - pt_this.x)/2)
                elements.append(
                    svg.Path(
                        stroke="black",
                        stroke_width=line_thickness,
                        fill="none",
                        d=[
                            svg.M( x=pt_this.x, y=pt_this.y),
                            svg.CubicBezier(
                                x1=pt_next.x-dx,
                                y1=pt_this.y,
                                x2=pt_this.x+dx,
                                y2=pt_next.y,
                                x=pt_next.x,
                                y=pt_next.y )]))

    for n, pts in enumerate(coords):
        if not gaga:
            # dots on Spec Z
            elements.append(Point(pts[0].x, bottom_line).draw(dot_radius))
            elements.append(
                svg.Text(
                    x=pts[0].x,
                    y=bottom_line,
                    dy=20,
                    text=f'({frobs[n][0]})',
                    text_anchor="middle"))

        # fibre above prime
        for pt in pts:
            radius = min(dot_radius
                         + residue_factor*(pt.girth-1), y_spread/5, x_spread/5)
            elements.append(pt.draw(radius))

    return svg.SVG(
        viewBox=svg.ViewBoxSpec(0, 0, width, height),
        elements=elements)


def draw_gaga(frobs, local_alg_dict, colors=True) -> svg.SVG:
    """ Draw the spectrum of the ring of integers of a number field,
    from data in the lmfdb.
    `frobs` is a list of lists [[p, [frob_cycle1,...,frob_cycleN]]]
    `local_algs` is a list of strings describing ramification behaviour ['p.deg.(other stuff)', ..., ]
    If `colors` is `True`, color classes which lie in the same Frobenius cycle
    """
    return draw_spec(frobs, local_alg_dict, colors=colors, gaga=True)

def unram_coords(frob_cycle_list, x_coord, y_centre, spread):
    """
    Given list of frobenius cycle describing a fixed fibre with no ramification, evenly spread points. Returns list of `Point`s.
    """
    # number of points
    N = sum(l[1] for l in frob_cycle_list)
    if N == 1:
        cyc_len = frob_cycle_list[0][0]
        return [Point(x_coord, y_centre, cyc_len)]
    point_list = []
    point_index = 0         # total index of point
    for cyc_len, num_repeats in frob_cycle_list:
        for _ in range(num_repeats):
            y_offset = round(spread * (2 * point_index / (N - 1) - 1))
            point = Point(x_coord, y_centre - y_offset, cyc_len)
            point_list.append(point)
            point_index += 1
    return point_list


def ram_coords(local_alg_dict, p, x_coord, y_centre, spread, deg=1):
    """ Given `local_alg_dict` as defined in web_number_field.py, and a prime `p`,
    extract the points in the ramified fibre
    """
    # list of lists [e,f]
    algs = local_alg_dict[str(p)]
    N = len(algs)
    assert algs != [], f"Ramified prime {p} has no local data!"

    max_ram_index = max(e for e, _ in algs)
    point_list = []

    for i, alg in enumerate(algs):
        ram_index, residue_deg = alg
        if N != 1:
            y_offset = round(spread * (2 * i / (N - 1) - 1))
        else:
            y_offset = 0
        point = Point(x_coord, y_centre - y_offset, residue_deg, hsl_color(ram_index, max_ram_index))
        point_list.append(point)

    return point_list


def hsl_color(n, n_max, sec=[0,45]):
    """
    Vary hue in hsl color between 0 and n_max within sector sec
    """
    if n_max == 0:
        return "black"
    s = 70
    l = 50
    h = sec[0] + floor(n*(sec[1]-sec[0])/n_max)
    # h = 300
    # l = round(n/n_max*l_max)

    return f"hsl({h},{s}%,{l}%)"


### Testing
def test_drawspec(n=1, gaga=False):
    if n == 1:
        frobs = [[2, [[3, 2], [1, 1]]], [3, [[6, 1], [1, 1]]], [5, [[6, 1], [1, 1]]], [7, [0]], [11, [[3, 2], [1, 1]]], [13, [[2, 3], [1, 1]]], [17, [[6, 1], [1, 1]]], [19, [[6, 1], [1, 1]]], [23, [[3, 2], [1, 1]]], [29, [[1, 7]]], [31, [[6, 1], [1, 1]]], [37, [[3, 2], [1, 1]]], [41, [0]], [43, [[7, 1]]], [47, [[6, 1], [1, 1]]], [53, [[3, 2], [1, 1]]], [59, [[6, 1], [1, 1]]]]

        local_algs = {"7": [[7,1]], "41": [[7,1]]}
    elif n == 2:
        frobs = [[2, [[3, 1]]], [3, [[3, 1]]], [5, [[3, 1]]], [7, [0]], [11, [[3, 1]]], [13, [[1, 3]]], [17, [[3, 1]]], [19, [[3, 1]]], [23, [[3, 1]]], [29, [[1, 3]]], [31, [[3, 1]]], [37, [[3, 1]]], [41, [[1, 3]]], [43, [[1, 3]]], [47, [[3, 1]]], [53, [[3, 1]]], [59, [[3, 1]]]]
        local_algs = {"7": [[3,1]]}

    num_primes = 7 if gaga else 100
    canvas = draw_spec(frobs, local_algs, True,
                       gaga=gaga,num_primes=num_primes)
    import tempfile
    filename = tempfile.gettempdir() + ('/gaga' if gaga else '/spec') + ".svg"
    with open(filename, mode='w') as f:
        f.write(canvas.as_str())

    print(f"Saved spectrum to {filename}")

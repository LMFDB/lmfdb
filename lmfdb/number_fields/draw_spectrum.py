import svg

from sage.all import (sin, cos, arctan2, floor, round)
# from utils/color import StandardColors
# TODO: bound dot size absolutely and distribute radii evenly
# TODO: increase height of gaga box

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
            cx = self.x,
            cy = self.y,
            r = radius,
            fill = self.color,
            stroke = 'black',
            stroke_width = .75)

def draw_spec(frobs, local_alg_dict, colors=True, rings=False, num_primes=100) -> svg.SVG:
    """ Draw the spectrum of the ring of integers of a number field,
    from data in the lmfdb.
    `frobs` is a list of lists [[p, [frob_cycle1,...,frob_cycleN]]]
    `local_algs` is a list of strings describing ramification behaviour ['p.deg.(other stuff)', ..., ]
    If `colors` is `True`, color classes which lie in the same Frobenius cycle
    """
    num_primes = min(len(frobs), num_primes)
    num_colors = max(len(l) for _, l in frobs)
    if colors:
        col_max = max(i[0] for [p,l] in frobs for i in l if l != [0])
    else:
        col_max = 0
    
    ### Options:
    # I've hardcoded these values instead of providing them
    # as optional arguments; feel free to change this
    
    # distance between two primes along x-axis
    x_spread = 50
    
    # distance between prime ideals in same fibre
    # = total distance from top to bottom
    y_spread = 30

    # (absolute) height of svg
    height = 200

    # (absolute) width of svg
    width = (num_primes+3)*x_spread

    # y-coordinate of Spec Z
    bottom_line = round((7/8)*height)

    # fraction of height of centre line around which the primes in spec are centred
    centre_ratio = 3.5/8
    # y-coordinate of Spec O_K
    y_centre = round(centre_ratio*height)
    
    line_thickness = .75

    # increase or decrease girth of inert primes based on size of residue field
    inertia_factor = .7
    ram_idx_factor = 2.5

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
                l, x_coord, y_centre, y_spread, col_max))

    # draw Spec Z line at the bottom
    elements.append(
        svg.Line(
            stroke = "black",
            stroke_width = line_thickness,
            x1 = coords[0][0].x, # get starting point of line
            y1 = bottom_line,
            x2 = coords[-1][0].x + x_spread, 
            y2 = bottom_line))

    # a dashed line afterwards to signify generic fibre
    for y in (bottom_line, y_centre):
        elements.append(
            svg.Line(
                stroke = "black",
                stroke_width = line_thickness,
                stroke_dasharray = "5",
                x1 = coords[-1][0].x + x_spread,
                y1 = y,
                x2 = coords[-1][0].x + 2*x_spread,
                y2 = y
            )
        )
        elements.append(svg.Text(
            x = width - x_spread,
            y = y,
            dx = 16,
            dy = 4,
            text = '(0)',
            text_anchor = "middle"))

    # draw curves between primes - do this first so points drawn over curve
    for n in range(num_primes):
        for pt_this in coords[n]:
            for pt_next in (coords + [[Point(width-2*x_spread, y_centre)] ])[n + 1]:
                # we control the angle of the curve by adding a control point
                dx = curviness*round((pt_next.x - pt_this.x)/2) 
                elements.append(
                    svg.Path(
                        stroke = "black",
                        stroke_width = line_thickness,
                        fill = "none",
                        d = [
                            svg.M( x = pt_this.x, y = pt_this.y),
                            svg.CubicBezier(
                                x1 = pt_next.x-dx,
                                y1 = pt_this.y,
                                x2 = pt_this.x+dx,
                                y2 = pt_next.y,
                                x = pt_next.x,
                                y = pt_next.y )]))

    for n, pts in enumerate(coords):
        # dots on Spec Z
        elements.append(Point(pts[0].x, bottom_line).draw(dot_radius))
        elements.append(
            svg.Text(
                x = pts[0].x,
                y = bottom_line,
                dy = 20,
                text = f'({frobs[n][0]})',
                text_anchor = "middle"))

        # fibre above prime
        for pt in pts:
            radius = min(dot_radius + residue_factor*(pt.girth-1), x_spread/3)
            elements.append(pt.draw(radius))

    return svg.SVG(
        width=width,
        height=height,
        elements=elements)


def draw_gaga(frobs, local_alg_dict, colors=True) -> svg.SVG:
    """ Draw the spectrum of the ring of integers of a number field,
    from data in the lmfdb.
    `frobs` is a list of lists [[p, [frob_cycle1,...,frob_cycleN]]]
    `local_algs` is a list of strings describing ramification behaviour ['p.deg.(other stuff)', ..., ]
    If `colors` is `True`, color classes which lie in the same Frobenius cycle
    """

    num_primes = len(frobs)
    num_colors = max(len(l) for _, l in frobs)
    if colors:
        col_max = max(i[0] for [p,l] in frobs for i in l if l != [0])
    else:
        col_max = 0
    ### Options:
    # I've hardcoded these values instead of providing them
    # as optional arguments; feel free to change this
    
    
    # distance between prime ideals in same fibre
    # = total distance from top to bottom
    y_spread = 30

    # (absolute) height of svg
    height = 150

    # (absolute) width of svg
    width = 200

    # distance between two primes along x-axis
    x_spread = floor(width/(num_primes+1))

    # fraction of height where we put centre line
    # around which the primes in spec are centred  
    centre_ratio = 1/2
    y_centre = round(centre_ratio*height)
    
    line_thickness = .75

    residue_factor = .7

    # radius of (unramified) points
    dot_radius = 2.5
    # parameter to control the cubic bezier curves.
    # Should probably be between 0 and 2, with 1 being "reasonable"
    curviness = 0.9

    elements = []
    # list of coordinates, where the n-th member is a
    # list of Points in the n-th fibre
    coords = []
    
    for n, [p, l] in enumerate(frobs):
        x_coord = (n+1)*x_spread
        if l == [0]:
            coords.append(ram_coords(
                local_alg_dict, p, x_coord, y_centre, y_spread, num_colors))
        else:
            coords.append(unram_coords(
                l, x_coord, y_centre, y_spread, num_colors))
    # draw lines
    for n in range(num_primes-1):
        for pt_this in coords[n]:
            for pt_next in coords[n + 1]:
                # we control the angle of the curve by adding a control point
                dx = curviness*round((pt_next.x - pt_this.x)/2) 
                elements.append(
                    svg.Path(
                        stroke = "black",
                        stroke_width = line_thickness,
                        fill = "none",
                        d = [
                            svg.M( x = pt_this.x, y = pt_this.y),
                            svg.CubicBezier(
                                x1 = pt_next.x-dx,
                                y1 = pt_this.y,
                                x2 = pt_this.x+dx,
                                y2 = pt_next.y,
                                x = pt_next.x,
                                y = pt_next.y )]))
    # draw fibre
    for n, pts in enumerate(coords):
        for pt in pts:
            radius = min(dot_radius + floor(residue_factor*(pt.girth-1)), round(x_spread/5))
            elements.append(pt.draw(radius))

    return svg.SVG(
        viewBox=svg.ViewBoxSpec(0, 0, width, height),
        # preserveAspectRatio="none",
        elements=elements)
        

def unram_coords(frob_cycle_list, x_coord, y_centre, spread, col_max):
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
            y_offset = round(spread*(2*point_index /(N-1) -1))
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

    max_ram_index = max(e for e,_ in algs)
    point_list = []

    for i, alg in enumerate(algs):
        ram_index, residue_deg = alg
        if N != 1:
            y_offset = round(spread*(2*i /(N-1) -1))
        else:
            y_offset = 0
        point = Point(x_coord, y_centre - y_offset, residue_deg, hsl_color(ram_index, max_ram_index))
        point_list.append(point)
        
    return point_list

    
def hsl_color(n, n_max, sec = [0,45]):
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

def test_drawspec(n=1):
    if n == 1: 
        frobs = [[2, [[3, 2], [1, 1]]], [3, [[6, 1], [1, 1]]], [5, [[6, 1], [1, 1]]], [7, [0]], [11, [[3, 2], [1, 1]]], [13, [[2, 3], [1, 1]]], [17, [[6, 1], [1, 1]]], [19, [[6, 1], [1, 1]]], [23, [[3, 2], [1, 1]]], [29, [[1, 7]]], [31, [[6, 1], [1, 1]]], [37, [[3, 2], [1, 1]]], [41, [0]], [43, [[7, 1]]], [47, [[6, 1], [1, 1]]], [53, [[3, 2], [1, 1]]], [59, [[6, 1], [1, 1]]]]

        signature = [1,3]
        local_algs = {"7": [[7,1]], "41": [[7,1]]}
    elif n == 2:
        frobs = [[2, [[3, 1]]], [3, [[3, 1]]], [5, [[3, 1]]], [7, [0]], [11, [[3, 1]]], [13, [[1, 3]]], [17, [[3, 1]]], [19, [[3, 1]]], [23, [[3, 1]]], [29, [[1, 3]]], [31, [[3, 1]]], [37, [[3, 1]]], [41, [[1, 3]]], [43, [[1, 3]]], [47, [[3, 1]]], [53, [[3, 1]]], [59, [[3, 1]]]]
        signature = [3,0]
        local_algs = {"7": [[3,1]]}
    
    canvas = draw_spec(frobs, local_algs, True)
    filename = "/tmp/test.svg"
    with open(filename, mode='w') as f:		
        f.write(canvas.as_str())

    print("Saved spectrum to /tmp/test.svg")
    return 0

def test_lady_gaga(n=1, spiral=False):
    # spectrum of integers of splitting field of x^7 + 41
    if n == 1: 
        frobs = [[2, [[3, 2], [1, 1]]], [3, [[6, 1], [1, 1]]], [5, [[6, 1], [1, 1]]], [7, [0]], [11, [[3, 2], [1, 1]]], [13, [[2, 3], [1, 1]]], [17, [[6, 1], [1, 1]]], [19, [[6, 1], [1, 1]]], [23, [[3, 2], [1, 1]]], [29, [[1, 7]]], [31, [[6, 1], [1, 1]]], [37, [[3, 2], [1, 1]]], [41, [0]], [43, [[7, 1]]], [47, [[6, 1], [1, 1]]], [53, [[3, 2], [1, 1]]], [59, [[6, 1], [1, 1]]]]

        signature = [1,3]
        local_algs = {"7": [[7,1]], "41": [[7,1]]}
    elif n == 2:
        frobs = [[2, [[3, 1]]], [3, [[3, 1]]], [5, [[3, 1]]], [7, [0]], [11, [[3, 1]]], [13, [[1, 3]]], [17, [[3, 1]]], [19, [[3, 1]]], [23, [[3, 1]]], [29, [[1, 3]]], [31, [[3, 1]]], [37, [[3, 1]]], [41, [[1, 3]]], [43, [[1, 3]]], [47, [[3, 1]]], [53, [[3, 1]]], [59, [[3, 1]]]]
        signature = [3,0]
        local_algs = {"7": [[3,1]]}
        
    if spiral: 
        canvas = draw_gaga_spiral(frobs[:14], local_algs, signature, True)
        filename = "/tmp/gaga-spiral.svg"
        with open(filename, mode='w') as f:		
            f.write(canvas.as_str())
        print("Saved to /tmp/gaga-spiral.svg")
    else:
        canvas = draw_gaga(frobs[:7], local_algs, True)
        filename = "/tmp/gaga.svg"
        with open(filename, mode='w') as f:		
            f.write(canvas.as_str())
        print("Saved to /tmp/gaga.svg")
        
    return 0

def test_barcode(n=1, separator="bar"):
    # spectrum of integers of splitting field of x^7 + 41
    frobs = []
    local_algs = []
    
    if n == 1: 
        frobs = [[2, [[3, 2], [1, 1]]], [3, [[6, 1], [1, 1]]], [5, [[6, 1], [1, 1]]], [7, [0]], [11, [[3, 2], [1, 1]]], [13, [[2, 3], [1, 1]]], [17, [[6, 1], [1, 1]]], [19, [[6, 1], [1, 1]]], [23, [[3, 2], [1, 1]]], [29, [[1, 7]]], [31, [[6, 1], [1, 1]]], [37, [[3, 2], [1, 1]]], [41, [0]], [43, [[7, 1]]], [47, [[6, 1], [1, 1]]], [53, [[3, 2], [1, 1]]], [59, [[6, 1], [1, 1]]]]

        signature = [1,3]
        local_algs = {"7": [[7,1]], "41": [[7,1]]}
    elif n == 2:
        frobs = [[2, [[3, 1]]], [3, [[3, 1]]], [5, [[3, 1]]], [7, [0]], [11, [[3, 1]]], [13, [[1, 3]]], [17, [[3, 1]]], [19, [[3, 1]]], [23, [[3, 1]]], [29, [[1, 3]]], [31, [[3, 1]]], [37, [[3, 1]]], [41, [[1, 3]]], [43, [[1, 3]]], [47, [[3, 1]]], [53, [[3, 1]]], [59, [[3, 1]]]]
        signature = [3,0]
        local_algs = {"7": [[3,1]]}

    canvas = draw_barcode(frobs[:20], local_algs, signature, separator=separator)
    filename = "/tmp/barcode.svg"
    with open(filename, mode='w') as f:		
        f.write(canvas.as_str())
        print("Saved to /tmp/barcode.svg")
        
    return 0

def generate_test_data():
    from lmf import db

    # uses https://github.com/roed314/lmfdb-lite
    ids = [
        "1.1.1.1",
        "2.0.3.1",
        "7.1.3911915096945863.1",
        "10.2.160801029712.1",
"45.1.246012870627780535441003976786240313709044401656133556774425683161984460829.1"
    ]

    for n,id in enumerate(ids):
        frobs = db.nf_fields.lookup(id, 'frobs')
        local_algs = db.nf_fields.lookup(id, 'local_algs')
        r2 = db.nf_fields.lookup(id, 'r2')
        deg = db.nf_fields.lookup(id, 'degree')
        signature = [deg-2*r2,r2]
        if local_algs is None:
            return None
        local_algebra_dict = {}
        R = PolynomialRing(QQ, 'x')
        for lab in local_algs:
            if lab[0] == 'm': # signals data about field not in lf db
                lab1 = lab[1:] # deletes marker m
                p, e, f, c = [int(z) for z in lab1.split('.')]
                if str(p) not in local_algebra_dict:
                    local_algebra_dict[str(p)] = [[e,f]]
                else:
                    local_algebra_dict[str(p)].append([e,f])
            else:
                LF = db.lf_fields.lookup(lab)
                p = LF['p']
                thisdat = [LF['e'], LF['f']]
                if str(p) not in local_algebra_dict:
                    local_algebra_dict[str(p)] = [thisdat]
                else:
                    local_algebra_dict[str(p)].append(thisdat)

        local_algs = local_algebra_dict
        # barcode
        canvas = draw_barcode(frobs[:20], local_algs, signature, separator="bar")
        filename = f"/tmp/barcode{n+1}.svg"
        with open(filename, mode='w') as f:		
            f.write(canvas.as_str())
        # spiral
        canvas = draw_gaga_spiral(frobs[:14], local_algs, True)
        filename = f"/tmp/spiral{n+1}.svg"
        with open(filename, mode='w') as f:		
            f.write(canvas.as_str())
        # boring
        canvas = draw_gaga(frobs[:5], local_algs, True)
        filename = f"/tmp/boring{n+1}.svg"
        with open(filename, mode='w') as f:		
            f.write(canvas.as_str())
        # cutoff
        canvas = draw_gaga(frobs[:5], local_algs, True)
        filename = f"/tmp/cutoff{n+1}.svg"
        with open(filename, mode='w') as f:		
            f.write(canvas.as_str())

    return 0

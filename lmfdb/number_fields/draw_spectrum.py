import svg
import random

from dataclasses import dataclass
from sage.all import (sin, cos, arctan2, floor)
# from utils/color import StandardColors

class Point:
    def __init__(self,
                 x: float,
                 y: float,
                 girth:float = 1,
                 color: str = "black",
                 ram_index: int = 1):
        self.x = round(x,3)
        self.y = round(y,3)
        self.girth = girth
        self.color = color
        self.ram_index = ram_index

    def __iter__(self):
        return iter((self.x, self.y))

    def __str__(self):
        return f"Point ({self.x}, {self.y}) of girth {self.girth} and color {self.color}"

    def __add__(self,other):
        return Point(self.x + other.x, self.y + other.y)

    def polar_coords(self) -> (float,float):
        r = round((self.x**2 + self.y**2)**0.5, 3)
        theta = arctan2(self.y,self.x)
        return (r,theta)


def draw_spec(frobs, local_alg_dict, colors=True, rings=False) -> svg.SVG:
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
    
    line_thickness = 1

    # increase or decrease girth of ramified primes
    ramify_factor = .7
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

    for n, pts in enumerate(coords):
        # dots on Spec Z
        elements.append(
            svg.Circle(
                cx = pts[0].x,
                cy = bottom_line,
                r = dot_radius,
                fill="black"))

        elements.append(
            svg.Text(
                x = pts[0].x,
                y = bottom_line,
                dy = 20,
                text = f'({frobs[n][0]})',
                text_anchor = "middle"))

        # draw fibre
        for pt in pts:
            radius = min(dot_radius + ramify_factor*(pt.girth-1), x_spread/3)
            elements.append(
                svg.Circle(
                    cx = pt.x,
                    cy = pt.y,
                    r = radius,
                    fill = pt.color,
                    stroke="black"))
            if rings: 
                for i in range(1,pt.ram_index):
                    new_radius = radius + ram_idx_factor*i**(2/3)
                    elements.append(
                        svg.Circle(
                            cx = pt.x,
                            cy = pt.y,
                            r = new_radius,
                            fill = "none",
                            stroke = "black",
                            stroke_width = .7))

    # now draw lines
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
    return svg.SVG(
        width=width,
        height=height,
        elements=elements)
        

def unram_coords(frob_cycle_list, x_coord, y_centre, spread, col_max):
    """
    Given list of frobenius cycle describing a fixed fibre with no ramification, evenly spread points with associated colors. Returns list of `Point`s.
    """
    # number of points 
    N = sum(l[1] for l in frob_cycle_list)
    if N == 1:
        return [Point(x_coord, y_centre, 1, hsl_color(frob_cycle_list[0][0], col_max))]
    point_list = []
    point_index = 0         # total index of point
    for cyc_len, num_repeats in frob_cycle_list:
        for _ in range(num_repeats):
            y_offset = round(spread*(2*point_index /(N-1) -1))
            point = Point(x_coord, y_centre - y_offset, 1, hsl_color(cyc_len,col_max))
            point_list.append(point)
            point_index += 1
    return point_list


def ram_coords(local_alg_dict, p, x_coord, y_centre, spread):
    """ Given `local_alg_dict` as defined in web_number_field.py, and a prime `p`,
    extract the points in the ramified fibre
    """
    # list of lists [e,f]
    algs = local_alg_dict[str(p)]

    assert algs != [], f"Ramified prime {p} has no local data!"
    N = len(algs)
    point_list = []
    if N == 1:
        ram_index, residue_deg = algs[0]
        return [Point(x_coord, y_centre, residue_deg, "black", ram_index)]
    
    for point_index, data in enumerate(algs):
        ram_index, residue_deg = data
        y_offset = round(spread*(2*point_index /(N-1) -1))
        point = Point(x_coord, y_centre - y_offset, residue_deg, "black", ram_index)
        point_list.append(point)
    return point_list

    
def hsl_color(n, n_max):
    """
    Closer to a hard-coded color (teal) from black
    as n gets closer to n_max
    """
    if n_max == 0:
        return "black"
    s_max = 90
    l_max = 90
    s = round(n/n_max*s_max)
    l = round(n/n_max*l_max)

    return f"hsl(180,{s}%,{l}%)"


def draw_gaga(frobs, local_alg_dict, signature, colors=True, rings=False) -> svg.SVG:
    """ Draw the spectrum of the ring of integers of a number field,
    from data in the lmfdb.
    `frobs` is a list of lists [[p, [frob_cycle1,...,frob_cycleN]]]
    `local_algs` is a list of strings describing ramification behaviour ['p.deg.(other stuff)', ..., ]
    If `colors` is `True`, color classes which lie in the same Frobenius cycle
    """

    frobs = frobs[:7]

    num_primes = len(frobs)
    num_colors = max(len(l) for _, l in frobs)
    if colors:
        col_max = max(i[0] for [p,l] in frobs for i in l if l != [0])
    else:
        col_max = 0
    ### Options:
    # I've hardcoded these values instead of providing them
    # as optional arguments; feel free to change this
    
    # distance between two primes along x-axis
    x_spread = 30
    
    # distance between prime ideals in same fibre
    # = total distance from top to bottom
    y_spread = 30

    # (absolute) height of svg
    height = 200

    # (absolute) width of svg
    width = 200

    # fraction of height of centre line around which the primes in spec are centred
    centre_ratio = 1/2
    y_centre = round(centre_ratio*height)
    
    line_thickness = .75

    # increase or decrease girth of ramified primes
    ramify_factor = .7
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

    for n, pts in enumerate(coords):
        # draw fibre
        for pt in pts:
            radius = min(dot_radius + ramify_factor*(pt.girth-1), x_spread/5)
            elements.append(
                svg.Circle(
                    cx = pt.x,
                    cy = pt.y,
                    r = radius,
                    fill = pt.color,
                    stroke="black"))
            if rings: 
                for i in range(1,pt.ram_index):
                    new_radius = radius + ram_idx_factor*i**(2/3)
                    elements.append(
                        svg.Circle(
                            cx = pt.x,
                            cy = pt.y,
                            r = new_radius,
                            fill = "none",
                            stroke = "black",
                            stroke_width = .7))

    # now draw lines
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
    if signature != []:
        for n, sign in enumerate(signature):
            x = 100
            y = 30 + n*140
            elements.append(
                svg.Circle(
                    stroke = "black",
                    fill = "none",
                    cx = x,
                    cy = y,
                    r = 20,
                    stroke_width = 1.5))
            if sign == 1:
                elements.append(
                    svg.Circle(
                        stroke = "black",
                        fill = "black",
                        cx = x,
                        cy = y,
                        r = 2))
            else:
                for m in range(1,sign+1):
                    x_new = round(x + 12*cos(2*m*3.1415/sign),3)
                    y_new = round(y + 12*sin(2*m*3.1415/sign),3)
                    elements.append(
                        svg.Circle(
                            stroke = "black",
                            fill = "black",
                            cx = x_new,
                            cy = y_new,
                            r = 2))

    return svg.SVG(
        viewBox=svg.ViewBoxSpec(0, 0, height, width),
        preserveAspectRatio="none",
        elements=elements)

def draw_gaga_spiral(frobs, local_alg_dict, colors=True) -> svg.SVG:

    # NB in this function viewbox is centered at (0,0)!
    num_primes = len(frobs)
    num_colors = max(len(l) for _, l in frobs)
    if colors:
        col_max = max(i[0] for [p,l] in frobs for i in l if l != [0])
    else:
        col_max = 0

    # (absolute) height of svg
    height = 200

    # (absolute) width of svg
    width = 200

    line_thickness = 1

    # increase or decrease girth of ramified primes
    ramify_factor = .7
    ram_idx_factor = 2.5

    # radius of (unramified) points
    dot_radius = 2.5

    coords = []

    pi = 3.1415
    y_spread = 10
    for n, [p, l] in enumerate(frobs):
        if l == [0]:
            coords.append(ram_coords(
                local_alg_dict, p, 0, 0, y_spread))
        else:
            coords.append(unram_coords(
                l, 0, 0, y_spread, col_max))

    elements = []

    # for n, pts in enumerate(coords):
    #     # draw fibre
    #     for pt in pts:
    #         radius = dot_radius + ramify_factor*(pt.girth-1)
    #         x,y = compute_helix_coords(pt, n)
    #         elements.append(
    #             svg.Circle(
    #                 cx = x,
    #                 cy = y,
    #                 r = radius,
    #                 fill = pt.color,
    #                 stroke="black"))

        
    helix_pts = []
    num_pts = 1000
    num_twists = 3
    interpol = lambda x: x**(0.1) # interpolates between 0 and 1
    interpol2 = lambda x: x
    rad_bd = height/2 - 5

    for step in range(num_pts):
        theta = 2*pi*num_twists*step/num_pts

        # will range between 0 and rad_bd
        r = interpol(step/num_pts)*step*rad_bd/num_pts
        assert r < rad_bd
        x = r*cos(theta)
        y = r*sin(theta)
        helix_pts.append(Point(x,y))

    start_idx = floor(num_pts/5)
    subdiv = floor((num_pts-start_idx)/len(coords))
    fib_spread = 7
    for n, fibre in enumerate(coords):
        ind = n*subdiv + start_idx

        ind_next = floor(ind + subdiv/2)
        ind_prev = floor(ind - subdiv/2)

        pt_next = helix_pts[ind_next]
        pt_prev = helix_pts[ind_prev]
        r_next,_ = pt_next.polar_coords()
        r_prev,_ = pt_prev.polar_coords()
        
        # for testing purposes
        # elements.append(
        #     svg.Circle(
        #         cx = pt_next.x,
        #         cy = pt_next.y,
        #         r = 3,
        #         fill = "teal",
        #         stroke="black"))

        r, theta = helix_pts[ind].polar_coords()
        # r_next, theta_next = 
        for i in range(len(fibre)):
            girth = min(dot_radius + ramify_factor*(fibre[i].girth-1), 5)
            r_fib = r if len(fibre) == 1 else r + fib_spread*(2*i/(len(fibre)-1)-1)
            pt_fib = [r_fib*cos(theta), r_fib*sin(theta)]
            elements.append(
                svg.Circle(
                    cx = pt_fib[0],
                    cy = pt_fib[1],
                    r = girth,
                    fill = fibre[i].color,
                    stroke="black"))
            # draw line from point to half-way to next fibre
            # for pt in [pt_prev,pt_next]:
            curve = []
            for j in range(ind_next-ind+1):
                _, theta_ip = helix_pts[ind + j].polar_coords()
                alpha = j/(ind_next-ind)
                assert 0 <= alpha <= 1
                r_ip = r_fib *(1-interpol2(alpha)) + r_next*interpol2(alpha)
                curve.append([r_ip*cos(theta_ip), r_ip*sin(theta_ip)])

            elements.append(
                svg.Polyline(
                    stroke= "black",
                    stroke_width=line_thickness,
                    fill= "none",
                    points= curve
                )
            )
            curve = []
            for j in range(ind-ind_prev+1):
                _, theta_ip = helix_pts[ind_prev + j].polar_coords()
                alpha = j/(ind-ind_prev)
                assert 0 <= alpha <= 1
                r_ip = r_fib *interpol2(alpha) + r_prev*(1-interpol2(alpha))
                curve.append([r_ip*cos(theta_ip), r_ip*sin(theta_ip)])

            elements.append(
                svg.Polyline(
                    stroke= "black",
                    stroke_width=line_thickness,
                    fill= "none",
                    points= curve
                )
            )
            

            
                # elements.append(
                #     svg.Line(
                #         stroke = "gray",
                #         stroke_width = line_thickness,
                #         stroke_dasharray = "1",
                #         x1 = pt_new[0],
                #         y1 = pt_new[1],
                #         x2 = pt_next[0],
                #         y2 = pt_next[1]
                #     )
                # )

    # elements.append(
    #     svg.Polyline(
    #         stroke= "red",
    #         fill= "none",
    #         points= [[P.x,P.y] for P in helix_pts]
    #     )
    # )
    return svg.SVG(
        viewBox=svg.ViewBoxSpec(-height/2, -width/2, height, width),
        elements=elements)

def draw_barcode(frobs, local_alg_dict, signature, colors=True, separator="bar"):
    num_primes = len(frobs)
    num_colors = max(len(l) for _, l in frobs)
    if colors:
        col_max = max(i[0] for [p,l] in frobs for i in l if l != [0])
    else:
        col_max = 0
    
    ### Options:
    # I've hardcoded these values instead of providing them
    # as optional arguments; feel free to change this
    
    # distance between two primes along x-axis
    x_spread = 10
    
    # distance between prime ideals in same fibre
    # = total distance from top to bottom
    y_spread = 50

    # (absolute) height of svg
    height = 200
    # (absolute) width of svg
    width = 200

    # fraction of height of centre line around which the primes in spec are centred
    centre_ratio = 1/2
    y_centre = round(centre_ratio*height)
    
    line_thickness = .5

    # increase or decrease girth of ramified primes
    ramify_factor = .7
    ram_idx_factor = 2.5

    # radius of (unramified) points
    dot_radius = 1.5
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

    for n, pts in enumerate(coords):
        # draw fibre
        for pt in pts:
            radius = min(dot_radius + ramify_factor*(pt.girth-1), x_spread/3)
            elements.append(
                svg.Circle(
                    cx = pt.x,
                    cy = pt.y,
                    r = radius,
                    fill = pt.color,
                    stroke="black"))

    if separator == "dash":
        elements.append(svg.Line(
            stroke = "black",
            stroke_width = line_thickness,
            stroke_dasharray = "1",
            x1 = 175,
            y1 = 100,
            x2 = 185,
            y2 = 100
        ))
    elif separator == "bar":
        elements.append(svg.Line(
            stroke = "gray",
            stroke_width = line_thickness,
            # stroke_dasharray = "5",
            x1 = 180,
            y1 = 25,
            x2 = 180,
            y2 = 175
        ))
            
    for n, no_embs in enumerate(signature):
        radius = min(dot_radius + ramify_factor*(pt.girth-1), x_spread/3)
        for k in range(no_embs):
            y_offset = 0 if no_embs == 1 else round(y_spread/2*(2*k/(no_embs-1) -1))
            pt = Point(190, 50 + 100*n - y_offset, 1)
            elements.append(
                svg.Circle(
                    cx = pt.x,
                    cy = pt.y,
                    r = radius,
                    fill = pt.color,
                    stroke="black"))
    
    return svg.SVG(
        viewBox=svg.ViewBoxSpec(0, 0, height, width),
        preserveAspectRatio="none",
        elements=elements)
    

def compute_helix_coords(pt, n, shift=False):
    pi = 3.1415
    k = 5
    theta = (2*pi* ( (n % k)))/k
        
    if shift:
        theta += pi/k

    r = 7*n + pt.y+20
        

    x = r*cos(theta)
    y = r*sin(theta)
    return Point(x,y)

def control_pts(pt_this, pt_next, before=False):
    r_this, theta_this = pt_this.polar_coords()
    r_next, theta_next = pt_next.polar_coords()
    _, theta = (pt_next + pt_this).polar_coords()
    # if theta > 3.1415:
    #     theta = 3.1415 - theta
    eps = 1.1
    r_this *= eps
    r_next *= eps
    return (Point(r_this*cos(theta), r_this*sin(theta)),
            Point(r_next*cos(theta), r_next*sin(theta)))

### Testing

def test_drawspec():
    # spectrum of integers of splitting field of x^7 + 41
    frobs = [[2, [[3, 2], [1, 1]]], [3, [[6, 1], [1, 1]]], [5, [[6, 1], [1, 1]]], [7, [0]], [11, [[3, 2], [1, 1]]], [13, [[2, 3], [1, 1]]], [17, [[6, 1], [1, 1]]], [19, [[6, 1], [1, 1]]], [23, [[3, 2], [1, 1]]], [29, [[1, 7]]], [31, [[6, 1], [1, 1]]], [37, [[3, 2], [1, 1]]], [41, [0]], [43, [[7, 1]]], [47, [[6, 1], [1, 1]]], [53, [[3, 2], [1, 1]]], [59, [[6, 1], [1, 1]]]]
    
    local_algs = {"7": [[7,1]], "41": [[7,1]]}
    
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
        canvas = draw_gaga(frobs[:5], local_algs, signature, True)
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
        canvas = draw_gaga(frobs[:5], local_algs, signature, True)
        filename = f"/tmp/boring{n+1}.svg"
        with open(filename, mode='w') as f:		
            f.write(canvas.as_str())
        # cutoff
        canvas = draw_gaga(frobs[:5], local_algs, [], True)
        filename = f"/tmp/cutoff{n+1}.svg"
        with open(filename, mode='w') as f:		
            f.write(canvas.as_str())

    return 0
        
            
        

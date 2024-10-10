# requires svg.pip
# run `sage -pip install svg.py` or something equivalent to install
# TODO: tweak to make prettier
# TODO: edit knowl
# DONE: fix alignment of text
# TODO: consider making it toggle-able?

import svg
import random
from sage.all import (
    NumberField,
    primes_first_n,
    round,
    Integers,
    PolynomialRing
)
def draw_spec(F,
              nprimes,
              # fat_factor=1,
              curve=False,
              color_classes=False) -> svg.SVG:
    prime_list = primes_first_n(nprimes)

    d = F.degree()
    
    elements = []
    # fraction of height of centre line around which the primes in spec are centred
    centre_ratio = 3/8
    # NB: svg y-coords start from top! eg (0,1) is 1 unit down from top left corner

    # distance between different primes 
    x_spread = 50
    # distance between prime ideals in same fibre
    # = total distance from top to bottom
    y_spread = 30
    
    # should make dims absolute!
    height = 200
    width = (nprimes+2)*x_spread


    # y-coordinate of Spec Z
    bottom_line = round((6/8)*height)
    line_thickness = 1
    dot_radius = 2.5

    prime_ideals = [F.ideal(p).factor() for p in prime_list]

    if color_classes:
        G = F.class_group()
        colors = []
        for i in range(G.order()):
            colors.append(generate_new_color(colors, pastel_factor=0.3))
        color_dict = dict(zip(list(G), map(rgb_nums_to_hex, colors)))
        color_dict[G.identity()] = rgb_nums_to_hex([.3, .3, .3])
        
    # print(color_dict)
    coord_list = [
        fp_coords(fplist,
                  (n+1)*x_spread,
                  round(centre_ratio*height),
                  y_spread) for n, fplist in enumerate(prime_ideals)
    ]

    elements.append(
        svg.Line(
            stroke = "black",
            stroke_width = line_thickness,
            x1 = coord_list[0][0][0],
            y1 = bottom_line,
            x2 = coord_list[-1][0][0],
            y2 = bottom_line
        )
    )
    for n, fplist in enumerate(prime_ideals):
        pts = coord_list[n]
        elements.append(
            svg.Circle(
                cx = pts[0][0],
                cy = bottom_line,
                r = dot_radius,
                fill="black")
        )
        # TODO: get font etc, make size variable?
        elements.append(
            svg.Text(
                x = pts[0][0],
                y = bottom_line,
                dy = 12,
                text = f'({prime_list[n]})',
                font_size = '8',
                text_anchor = "middle",
            )
        )
        
        for i, (fp, mult) in enumerate(fplist):
            elements.append(
                svg.Circle(
                    cx = pts[i][0],
                    cy = pts[i][1],
                    r = dot_radius,
                    fill = color_dict[G(fp)] if color_classes else "black",
                    stroke="black")
            )
    if curve:
        for n in range(nprimes-1):
            for coord_this in coord_list[n]:
                for coord_next in (coord_list + [[(nprimes, round(1/3*height))]])[n + 1]:
                    dx = round((coord_next[0] - coord_this[0])/2)
                    elements.append(
                        svg.Path(
                            stroke = "black",
                            stroke_width = line_thickness,
                            fill = "none",
                            d = [
                                svg.M(x=coord_this[0], y = coord_this[1]),
                                svg.CubicBezier(
                                    x1 = coord_next[0]-dx,
                                    y1 = coord_this[1],
                                    x2 = coord_this[0]+dx,
                                    y2 = coord_next[1],
                                    x = coord_next[0],
                                    y = coord_next[1]
                                )
                            ]
                            )
                        )
    return svg.SVG(
        width=width,
        height=height,
        elements=elements)
    
def fp_coords(fplist, x_coord, y_centre, spread):
    N = len(fplist)
    if N == 1:
        return [(x_coord, y_centre)]
    else:
        return [(x_coord, y_centre -round(spread*(2* i /(N-1) -1))) for i in range(N)]


# from https://gist.github.com/adewes/5884820:


def get_random_color(pastel_factor=0.5):
    return [(x + pastel_factor) / (1.0 + pastel_factor)
            for x in [random.uniform(0, 1.0) for i in [1, 2, 3]]]


def color_distance(c1, c2):
    return sum([abs(x[0] - x[1]) for x in zip(c1, c2)])


def generate_new_color(existing_colors, pastel_factor=0.5):
    max_distance = None
    best_color = None
    for i in range(0, 100):
        color = get_random_color(pastel_factor=pastel_factor)
        if not existing_colors:
            return color
        best_distance = min(
            [color_distance(color, c) for c in existing_colors])
        if not max_distance or best_distance > max_distance:
            max_distance = best_distance
            best_color = color
    return best_color

def save_svg(filename, svg):
    with open(filename, mode='w') as f:		
        f.write(svg.as_str())

def rgb_nums_to_hex(L):
    Lhex = [round(hex((l*256)))[2:] for l in L]
    return "#" + "".join(Lhex)

def test_draw():
    R = PolynomialRing(Integers(), names="x"); x = R.gens()[0]
    F = NumberField(x**7 +41, names="a")
    # F = NumberField(P, names="a")
    # F.<a> = CyclotomicField(29)
    # F = QuadraticField(-1)
    draw_spec(F,nprimes = 15, curve = True)
    # dunno if this works!
    canvas = draw_spec(
            F,
            nprimes=15,
            curve=True,
            color_classes=False)
    save_svg("test.svg", canvas)
    return 1

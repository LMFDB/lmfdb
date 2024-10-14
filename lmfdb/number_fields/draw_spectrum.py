import svg
from sage.all import (
    NumberField,
    primes_first_n,
    round,
    Integers,
    PolynomialRing,
    QuadraticField,
    CyclotomicField
)

def draw_spec(F,
              nprimes) -> svg.SVG:

    prime_list = primes_first_n(nprimes)
    deg = F.degree()
    
    elements = []
    # NB: svg y-coords start from top! eg (0,1) is 1 unit down from top left corner

    # distance between different primes 
    x_spread = 50
    # distance between prime ideals in same fibre
    # = total distance from top to bottom
    y_spread = 30
    
    height = 200
    width = (nprimes+3)*x_spread


    # y-coordinate of Spec Z
    bottom_line = round((6/8)*height)

    # fraction of height of centre line around which the primes in spec are centred
    centre_ratio = 3/8
    # y-coordinate of Spec O_K
    centre_line = round(centre_ratio*height)

    # fatness of ramified primes
    ramify_factor = 4/deg
    
    line_thickness = 1
    dot_radius = 2.5

    prime_ideals = [F.ideal(p).factor() for p in prime_list]
    
        
    coord_list = [
        fp_coords(fplist,
                  (n+1)*x_spread,
                  centre_line,
                  y_spread) for n, fplist in enumerate(prime_ideals)
    ]

    elements.append(
        svg.Line(
            stroke = "black",
            stroke_width = line_thickness,
            x1 = coord_list[0][0][0],
            y1 = bottom_line,
            x2 = width - 2*x_spread,
            y2 = bottom_line
        )
    )
    for y in (bottom_line, centre_line):
        elements.append(
            svg.Line(
                stroke = "black",
                stroke_width = line_thickness,
                stroke_dasharray = "5",
                x1 = width - 2*x_spread,
                y1 = y,
                x2 = width - x_spread,
                y2 = y
            )
        )
        elements.append(svg.Text(
            x = width - x_spread,
            y = y,
            dx = 16,
            dy = 4,
            text = '(0)',
            text_anchor = "middle")
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
        elements.append(
            svg.Text(
                x = pts[0][0],
                y = bottom_line,
                dy = 20,
                text = f'({prime_list[n]})',
                text_anchor = "middle",
            )
        )
        
        for i, (fp, mult) in enumerate(fplist):
            elements.append(
                svg.Circle(
                    cx = pts[i][0],
                    cy = pts[i][1],
                    r = dot_radius + ramify_factor*(mult-1),
                    fill = "black",
                    stroke="black")
            )
        for n in range(nprimes):
            for coord_this in coord_list[n]:
                for coord_next in (coord_list +
                                   [[(width-2*x_spread, centre_line)]])[n + 1]:
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



def test_drawspec(eg_no: int):
    R = PolynomialRing(Integers(), names="x"); x = R.gens()[0]
    match eg_no:
        case 1:
            P = x**7 + 41
            F = NumberField(P, names="a")
        case 2:
            P = x**2 + 33
            F = NumberField(P, names="a")
        case 3: 
            F = CyclotomicField(29, names="a")
        case 4:
            F = QuadraticField(-1)
        case _:
            return f"eg_no = {eg_no} should be an integer between 1 and 4"
        
    canvas = draw_spec(
        F,
        nprimes=20)
    filename = "/tmp/test.svg"
    with open(filename, mode='w') as f:		
        f.write(canvas.as_str())

    print("Saved spectrum to /tmp/test.svg")
    return 0

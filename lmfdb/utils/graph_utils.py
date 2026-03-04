
GRAPH_LAYOUTS = ['Preset', 'Elk-stress', 'Circle', 'Concentric', 'Klay', 'Dagre', 'Cola']


def graph_to_cytoscape_json(G):
    """Convert a Sage Graph with positions to Cytoscape.js elements format.

    Positions are taken from G.get_pos() if available (as set by
    make_graph), otherwise computed via layout_spring().  Returns
    ``(elements, has_preset)`` where *elements* is a list of dicts
    suitable for ``cytoscape({elements: ...})`` and *has_preset* is
    True when positions came from hardcoded coordinates.
    """
    pos = G.get_pos()
    has_preset = pos is not None and len(pos) >= len(G.vertices())
    if not has_preset:
        pos = G.layout_spring()
    elements = []
    for v in G.vertices():
        x, y = pos[v]
        node = {
            "group": "nodes",
            "data": {"id": str(v), "label": str(v)},
            "position": {"x": float(x * 150), "y": float(-y * 150)},
        }
        elements.append(node)
    for u, v, label in G.edges():
        elements.append({
            "group": "edges",
            "data": {"source": str(u), "target": str(v), "label": str(label)},
        })
    return elements, has_preset


def graph_to_svg(G, max_width=200, max_height=150):
    """Generate a compact SVG string for the properties box sidebar.

    Produces a lightweight inline SVG from a Sage Graph with positions,
    suitable for embedding directly in HTML.  Dimensions are computed
    adaptively from the graph layout to avoid excess whitespace.
    """
    from markupsafe import Markup
    pos = G.get_pos()
    vertices = G.vertices()
    n = len(vertices)
    pad = 15
    r = 5

    if n == 0:
        return Markup('<svg width="0" height="0"></svg>')

    # Compute positions if not set by make_graph
    if pos is None or len(pos) < n:
        pos = G.layout_spring()

    if n == 1:
        width = height = 2 * pad
        coords = {vertices[0]: (width / 2, height / 2)}
    else:
        xs = [float(pos[v][0]) for v in vertices]
        ys = [float(pos[v][1]) for v in vertices]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        range_x = max_x - min_x
        range_y = max_y - min_y

        if range_x == 0 and range_y == 0:
            width = height = 2 * pad
            coords = {v: (width / 2, height / 2) for v in vertices}
        elif range_y == 0:
            # Horizontal layout (e.g. path graphs)
            width = max_width
            height = 2 * pad
            coords = {v: (pad + (pos[v][0] - min_x) / range_x * (width - 2 * pad),
                          height / 2) for v in vertices}
        elif range_x == 0:
            # Vertical layout
            width = 2 * pad
            height = min(max_height, max_width)
            coords = {v: (width / 2,
                          pad + (max_y - pos[v][1]) / range_y * (height - 2 * pad))
                      for v in vertices}
        else:
            # General case: fit to max_width, scale height by aspect ratio
            aspect = range_y / range_x
            width = max_width
            draw_w = width - 2 * pad
            height = min(max_height, int(draw_w * aspect + 2 * pad))
            height = max(height, 2 * pad)
            draw_h = height - 2 * pad
            coords = {v: (pad + (pos[v][0] - min_x) / range_x * draw_w,
                          pad + (max_y - pos[v][1]) / range_y * draw_h)
                      for v in vertices}

    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">' % (width, height)]

    # Draw edges
    for u, v, label in G.edges():
        x1, y1 = coords[u]
        x2, y2 = coords[v]
        parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                     'stroke="#888" stroke-width="1.5"/>' % (x1, y1, x2, y2))

    # Draw nodes
    for v in vertices:
        cx, cy = coords[v]
        parts.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="#333" '
                     'stroke="#333" stroke-width="1"/>' % (cx, cy, r))

    parts.append('</svg>')
    return Markup('\n'.join(parts))


def make_graph(M, vertex_labels=None):
    """
    Construct an isogeny graph from a degree matrix.

    Code extracted from Sage's elliptic curve isogeny class (reshaped
    in the case maxdegree==12).  Positions are hardcoded based on
    the shape of the graph, which is classified by the maximum degree
    and number of vertices.

    INPUT:

    - ``M`` -- a square matrix of isogeny degrees
    - ``vertex_labels`` -- optional list of labels for the vertices;
      defaults to ``[1, 2, ..., n]``

    OUTPUT: a Sage Graph with positions set
    """
    from sage.schemes.elliptic_curves.ell_curve_isogeny import fill_isogeny_matrix, unfill_isogeny_matrix
    from sage.graphs.graph import Graph
    n = M.nrows()  # = M.ncols()
    G = Graph(unfill_isogeny_matrix(M), format='weighted_adjacency_matrix')
    MM = fill_isogeny_matrix(M)
    if n == 1:
        # one vertex
        G.set_pos(pos={0: [0, 0]})
    elif n == 2:
        # one edge, two vertices
        G.set_pos(pos={0: [-0.5, 0], 1: [0.5, 0]})
    else:
        maxdegree = max(max(MM))
        if n == 3:
            # o--o--o
            centervert = [i for i in range(3) if max(MM.row(i)) < maxdegree][0]
            other = [i for i in range(3) if i != centervert]
            G.set_pos(pos={centervert: [0, 0], other[0]: [-1, 0], other[1]: [1, 0]})
        elif maxdegree == 4:
            # o--o<8
            centervert = [i for i in range(4) if max(MM.row(i)) < maxdegree][0]
            other = [i for i in range(4) if i != centervert]
            G.set_pos(pos={centervert: [0, 0], other[0]: [0, 1], other[1]: [-0.8660254, -0.5], other[2]: [0.8660254, -0.5]})
        elif maxdegree == 27 and n == 4:
            # o--o--o--o
            centers = [i for i in range(4) if list(MM.row(i)).count(3) == 2]
            left = [j for j in range(4) if MM[centers[0], j] == 3 and j not in centers][0]
            right = [j for j in range(4) if MM[centers[1], j] == 3 and j not in centers][0]
            G.set_pos(pos={left: [-1.5, 0], centers[0]: [-0.5, 0], centers[1]: [0.5, 0], right: [1.5, 0]})
        elif n == 4:
            # square
            opp = [i for i in range(1, 4) if not MM[0, i].is_prime()][0]
            other = [i for i in range(1, 4) if i != opp]
            G.set_pos(pos={0: [0.5, 0.5], other[0]: [-0.5, 0.5], opp: [-0.5, -0.5], other[1]: [0.5, -0.5]})
        elif maxdegree == 8:
            # 8>o--o<8
            centers = [i for i in range(6) if list(MM.row(i)).count(2) == 3]
            left = [j for j in range(6) if MM[centers[0], j] == 2 and j not in centers]
            right = [j for j in range(6) if MM[centers[1], j] == 2 and j not in centers]
            G.set_pos(pos={centers[0]: [-0.5, 0], left[0]: [-1, 0.8660254], left[1]: [-1, -0.8660254], centers[1]: [0.5, 0], right[0]: [1, 0.8660254], right[1]: [1, -0.8660254]})
        elif maxdegree == 18 and n == 6:
            # two squares joined on an edge
            centers = [i for i in range(6) if list(MM.row(i)).count(3) == 2]
            top = [j for j in range(6) if MM[centers[0], j] == 3]
            bl = [j for j in range(6) if MM[top[0], j] == 2][0]
            br = [j for j in range(6) if MM[top[1], j] == 2][0]
            G.set_pos(pos={centers[0]: [0, 0.5], centers[1]: [0, -0.5], top[0]: [-1, 0.5], top[1]: [1, 0.5], bl: [-1, -0.5], br: [1, -0.5]})
        elif maxdegree == 16 and n == 8:
            # tree from bottom, 3 regular except for the leaves
            centers = [i for i in range(8) if list(MM.row(i)).count(2) == 3]
            center = [i for i in centers if len([j for j in centers if MM[i, j] == 2]) == 2][0]
            centers.remove(center)
            bottom = [j for j in range(8) if MM[center, j] == 2 and j not in centers][0]
            left = [j for j in range(8) if MM[centers[0], j] == 2 and j != center]
            right = [j for j in range(8) if MM[centers[1], j] == 2 and j != center]
            G.set_pos(pos={center: [0, 0], bottom: [0, -1], centers[0]: [-0.8660254, 0.5], centers[1]: [0.8660254, 0.5], left[0]: [-0.8660254, 1.5], right[0]: [0.8660254, 1.5], left[1]: [-1.7320508, 0], right[1]: [1.7320508, 0]})
        elif maxdegree == 12:
            # tent
            centers = [i for i in range(8) if list(MM.row(i)).count(2) == 3]
            left = [j for j in range(8) if MM[centers[0], j] == 2]
            right = []
            for i in range(3):
                right.append([j for j in range(8) if MM[centers[1], j] == 2 and MM[left[i], j] == 3][0])
            G.set_pos(pos={centers[0]: [-0.5, 0], centers[1]: [0.5, 0],
                           left[0]: [-1.5, 1], right[0]: [1.5, 1],
                           left[1]: [-1.5, 0], right[1]: [1.5, 0],
                           left[2]: [-1.5, -1], right[2]: [1.5, -1]})

    if vertex_labels:
        G.relabel(vertex_labels)
    else:
        G.relabel(list(range(1, n + 1)))
    return G


def setup_isogeny_graph(G):
    """Return (graph_data, graph_link, graph_layouts, graph_default_layout) for an isogeny graph."""
    graph_data, has_preset = graph_to_cytoscape_json(G)
    graph_link = graph_to_svg(G)
    graph_default_layout = 'Preset' if has_preset else 'Elk-stress'
    return graph_data, graph_link, list(GRAPH_LAYOUTS), graph_default_layout

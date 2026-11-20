# -*- coding: utf-8 -*-
r"""
Portraits (Gauss-sum visualizations) for Dirichlet characters.

Following the design proposed in https://github.com/LMFDB/lmfdb/issues/3996
(see the demo at https://alexjbest.github.io/dirich/), the portrait of a
Dirichlet character `\chi` of modulus `N` shows, for each residue
`a \in \{0, \dots, N-1\}`, the partial Gauss sums

.. MATH::

    S_a(k) = \sum_{n=1}^{k} \chi(n) e^{2\pi i a n / N},

as radial segments from the origin, colored by `a` (rainbow hue), with early
partial sums darkened and later ones at full brightness.  A large dot of the
same color marks the complete Gauss sum `\tau_a(\chi) = S_a(N-1)`, and a grey
circle of radius `\sqrt{N}` is drawn: for a primitive character every dot with
`\gcd(a, N) = 1` lands exactly on this circle, so primitivity (and much else:
the order of the character as rotational symmetry, reality as symmetry about
the real axis, triviality as a red horizontal spike) is visible at a glance.

Only the stages `k` coprime to `N` are drawn.  Since `\chi(n) = 0` when
`\gcd(n, N) > 1`, the omitted stages would each repeat the segment before them
exactly, so leaving them out multiplies the cost of the picture by
`\phi(N) / N` while drawing the same thing.

The plot is computed on the fly, so we only draw it when that is cheap; see
``portrait_is_enabled`` for the two limits involved and ``paint_portrait`` for
the cache.  For speed the segments are rendered as a single matplotlib
``LineCollection`` wrapped in a sage ``GraphicPrimitive``, so the result is an
ordinary sage ``Graphics`` object that is embedded in the page via
``encode_plot``, as for elliptic curve and Maass form plots.
"""

from functools import lru_cache

from sage.all import Graphics, circle, euler_phi, gcd, sqrt
from sage.plot.colors import rainbow
from sage.plot.plot import minmax_data
from sage.plot.primitive import GraphicPrimitive

from lmfdb.characters.TinyConrey import ConreyCharacter
from lmfdb.logger import logger
from lmfdb.utils import encode_plot

# Portraits are drawn on the fly, so they are only drawn when there is little
# work to do.  The cost is driven by the number of segments in the picture,
# which is N * phi(N) and so is far from monotone in N: the prime N = 293 needs
# 85556 of them, while the larger N = 300 needs only 24000 and is some eight
# times faster to draw.  So the cutoff below is on the segment count; 25000
# keeps N = 300 (and every N with a comparably small phi(N)), which takes about
# a tenth of a second, while dropping the slow prime-like cases.  Raising it
# needs timings for worst-case, high-phi(N) moduli.  The modulus bound is a
# cheap extra guard on the parts of the work that grow with N alone.  If
# portraits are ever precomputed and stored in the database, both restrictions
# can be lifted.
PORTRAIT_MAX_MODULUS = 300
PORTRAIT_MAX_SEGMENTS = 25000

# How many completed portraits to keep in this process; each is a data URI of a
# few tens of kilobytes, so the bound keeps the memory used well under a
# megabyte while sparing repeat visitors and crawlers the rendering cost.
PORTRAIT_CACHE_SIZE = 64


class PartialGaussSums(GraphicPrimitive):
    """
    Graphics primitive drawing all partial Gauss sums of a Dirichlet
    character as radial segments, and the complete Gauss sums as dots.

    Rendering ``N * phi(N)`` segments as individual sage lines is far too
    slow, so this primitive holds them in numpy arrays and renders them as a
    single matplotlib ``LineCollection`` (plus one scatter plot for the dots).
    """
    def __init__(self, segments, segment_colors, dots, dot_colors):
        self.segments = segments  # (k, 2, 2): k segments from (0,0) to S_a(n)
        self.segment_colors = segment_colors  # (k, 4) rgba
        self.dots = dots  # (N, 2): complete Gauss sums
        self.dot_colors = dot_colors  # (N, 4) rgba
        GraphicPrimitive.__init__(self, {})

    def get_minmax_data(self):
        xdata = list(self.segments[:, :, 0].flatten()) + list(self.dots[:, 0])
        ydata = list(self.segments[:, :, 1].flatten()) + list(self.dots[:, 1])
        return minmax_data(xdata, ydata, dict=True)

    def _render_on_subplot(self, subplot):
        from matplotlib.collections import LineCollection
        subplot.add_collection(
            LineCollection(self.segments, colors=self.segment_colors,
                           linewidths=1.5, zorder=2))
        subplot.scatter(self.dots[:, 0], self.dots[:, 1], s=60,
                        c=self.dot_colors, zorder=10)


def portrait_complexity(modulus):
    """
    The number of segments in the portrait of a character of this modulus,
    namely `N \\phi(N)`, which is what the cost of drawing it scales with.
    """
    modulus = int(modulus)
    return modulus * int(euler_phi(modulus))


def portrait_is_enabled(modulus):
    """
    Whether portraits are drawn for characters of this modulus: they are when
    the modulus is at most ``PORTRAIT_MAX_MODULUS`` and the portrait has at
    most ``PORTRAIT_MAX_SEGMENTS`` segments.  This is cheap (no character is
    constructed and no array is allocated), so it can be consulted before
    doing any work; a modulus that fails it simply has no portrait, which is a
    normal outcome and not an error.
    """
    modulus = int(modulus)
    return (modulus <= PORTRAIT_MAX_MODULUS
            and portrait_complexity(modulus) <= PORTRAIT_MAX_SEGMENTS)


def partial_gauss_sums(modulus, number):
    """
    The partial Gauss sums of the Dirichlet character
    `\\chi_{modulus}(number, \\cdot)`.

    Returns a pair ``(ns, sums)`` of numpy arrays, where ``ns`` lists the
    `n \\in \\{1, \\dots, N-1\\}` coprime to `N = modulus` and ``sums`` has
    shape ``(N, len(ns))`` with ``sums[a, k]`` the partial Gauss sum
    `S_a(ns[k])`; in particular ``sums[a, -1]`` is the complete Gauss sum
    `\\tau_a(\\chi)`.
    """
    import numpy as np

    N = modulus
    chi = ConreyCharacter(N, number)
    # the n with chi(n) != 0, and chi(n) = e(angle(n)) for those n
    ns = np.array([n for n in range(1, N) if gcd(n, N) == 1])
    angles = np.array([float(chi.conreyangle(int(n))) for n in ns])
    chivals = np.exp(2j * np.pi * angles)
    # partial sums S_a(n) for all a (rows) and n in ns (columns)
    avals = np.arange(N)
    phases = np.exp(2j * np.pi * np.outer(avals, ns) / N)
    return ns, np.cumsum(chivals[np.newaxis, :] * phases, axis=1)


def portrait_data(modulus, number):
    """
    The four numpy arrays ``(segments, segment_colors, dots, dot_colors)``
    making up the portrait of `\\chi_{modulus}(number, \\cdot)`, in the format
    consumed by ``PartialGaussSums``.
    """
    import numpy as np

    N = modulus
    if N == 1:
        # chi(n) = 1 for all n; tau_0 = 1 is the only (empty) Gauss sum
        return (np.zeros((0, 2, 2)), np.zeros((0, 4)),
                np.array([[1.0, 0.0]]), np.array([[1.0, 0.0, 0.0, 0.8]]))

    ns, sums = partial_gauss_sums(N, number)

    # rainbow color for each a, darkened for early partial sums as in
    # the demo: darker(3*(N-1-n)/(5*N)) scales rgb by 1 - 3*(N-1-n)/(5*N)
    base = np.array([[int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)]
                     for h in rainbow(N)]) / 255.0
    brightness = 1.0 - 3.0 * (N - 1 - ns) / (5.0 * N)

    k = N * len(ns)
    segments = np.zeros((k, 2, 2))
    segments[:, 1, 0] = sums.real.flatten()
    segments[:, 1, 1] = sums.imag.flatten()
    segment_colors = np.empty((k, 4))
    segment_colors[:, :3] = (base[:, np.newaxis, :]
                             * brightness[np.newaxis, :, np.newaxis]
                             ).reshape(k, 3)
    segment_colors[:, 3] = 0.35

    dots = np.column_stack([sums[:, -1].real, sums[:, -1].imag])
    dot_colors = np.empty((N, 4))
    dot_colors[:, :3] = base
    dot_colors[:, 3] = 0.8
    return segments, segment_colors, dots, dot_colors


@lru_cache(maxsize=PORTRAIT_CACHE_SIZE)
def _paint_portrait(modulus, number):
    """
    Draw the portrait of `\\chi_{modulus}(number, \\cdot)` and return it as a
    base64-encoded png data URI, assuming the modulus has already passed
    ``portrait_is_enabled``.  Only the finished data URI is kept in the cache,
    not the numpy arrays it was built from, and a failure raises rather than
    caching a bad result.  Call ``paint_portrait`` instead of this.
    """
    G = Graphics()
    G.add_primitive(PartialGaussSums(*portrait_data(modulus, number)))
    G += circle((0, 0), sqrt(modulus), color="grey", zorder=1)
    G.set_aspect_ratio(1)
    G.axes(False)
    return encode_plot(G, pad=0, pad_inches=0, transparent=True,
                       remove_axes=True, axes_pad=0.05, figsize=[4, 4])


def paint_portrait(modulus, number):
    """
    The portrait of the Dirichlet character `\\chi_{modulus}(number, \\cdot)`
    as a base64-encoded png data URI, or ``None`` if drawing it would be too
    much work (see ``portrait_is_enabled``); characters without a portrait are
    rejected here, before they can take up room in the cache.

    Repeated requests for the same character are served from a bounded
    process-local cache; ``paint_portrait.cache_clear()`` empties it and
    ``paint_portrait.cache_info()`` reports on it, as for any ``lru_cache``.
    """
    if not portrait_is_enabled(modulus):
        return None
    return _paint_portrait(int(modulus), int(number))


paint_portrait.cache_clear = _paint_portrait.cache_clear
paint_portrait.cache_info = _paint_portrait.cache_info


def portrait_properties(modulus, number):
    """
    The portrait of `\\chi_{modulus}(number, \\cdot)` as a ``(None, html)``
    pair ready to drop into a properties box: a thumbnail linking to the
    full-size image, exactly as elliptic curve and Maass form plots do.
    Returns ``None`` when there is no portrait (see ``portrait_is_enabled``),
    so callers can test the result directly.
    """
    uri = paint_portrait(modulus, number)
    if uri is None:
        return None
    alt = "Gauss-sum portrait of the Dirichlet character %s.%s" % (modulus, number)
    link = ('<a href="{0}" title="{1}">'
            '<img class="dirichlet-character-portrait" src="{0}" alt="{1}"'
            ' width="200" height="200"/></a>').format(uri, alt)
    return (None, link)


def add_portrait(info, modulus, number):
    """
    Insert the portrait of `\\chi_{modulus}(number, \\cdot)` into the
    properties box carried by ``info['properties']``, just below the label
    (the position used for the elliptic curve plot).  A no-op when there is no
    portrait for this character or when ``info`` has no properties box, so it
    is safe to call unconditionally from the character route.

    Any failure while building the portrait is logged and swallowed: the
    portrait is decorative and must never break the character page.
    """
    try:
        entry = portrait_properties(modulus, number)
    except Exception:
        logger.error("failed to build portrait for character %s.%s",
                     modulus, number, exc_info=True)
        return
    if entry is not None and info.get("properties"):
        info["properties"].insert(1, entry)

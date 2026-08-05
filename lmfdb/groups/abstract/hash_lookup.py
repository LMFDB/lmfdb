# -*- coding: utf-8 -*-
r"""
One place that turns an ``order#hash`` pair into a set of groups, and one place
that decides which stored value may be shown to a user as *the* hash, so that
``N#h`` means the same thing in the find box, on group homepages, in the
subgroup and quotient popups, in the identification tool and in the optional
search column.

Two tables store hashes:

* ``gps_groups.hash`` holds one value per group in the LMFDB.  At most orders
  that value is the isomorphism-invariant (Magma) hash, but at six of the ten
  orders below the data pipeline stored the label counter instead: every row of
  order 512, 1152, 1536, 1920, 2187 or 15625 has ``hash = counter``, so
  ``512.11`` has ``hash = 11`` rather than its actual hash
  ``1584677793794603025``.  (The other four, 6561, 16807, 78125 and 161051,
  store real hashes, as do the identifiable orders, where the hash *is* the
  small-group index and so agrees with the counter anyway.)
* ``gps_smallhash`` holds a complete ``(order, counter, hash)`` table for the
  ten orders in :data:`SMALLHASH_ORDERS`.  It covers every group of those
  orders, including the overwhelming majority that have no LMFDB homepage
  (2558 of the 10494213 groups of order 512 are in ``gps_groups``).

A hash search at one of those ten orders therefore has to go to
``gps_smallhash``, and what comes back is complete: the groups it lists are
provably all the groups of that order with that hash, so a unique match is a
proof of isomorphism.

Index note: ``gps_smallhash`` has 4.2*10^8 rows and a single index, on
``(order, hash)``.  Queries in that direction are fast.  The other direction,
``(order, counter)`` to a hash, is a sequential scan (about six minutes against
devmirror), so the true hash of a group at one of these orders is not something
a page can display; :func:`structural_hash` reports that there is no usable
value rather than showing the counter under a "hash" heading.
"""

from dataclasses import dataclass, field
from typing import List

from flask import url_for
from sage.libs.gap.libgap import libgap

from lmfdb import db

# The ten orders for which gps_smallhash is a complete (order, counter, hash)
# table (= SmallhashOrders() in the FiniteGroups repository's Code/Hash.m).
SMALLHASH_ORDERS = frozenset(
    [512, 1152, 1536, 1920, 2187, 6561, 15625, 16807, 78125, 161051]
)


@dataclass(frozen=True)
class HashResolution:
    """The groups of a given order with a given hash.

    ``labels`` are sorted; ``complete`` says whether they are provably all the
    groups of that order with that hash (as opposed to just the ones in the
    LMFDB with that stored hash); ``source`` is the table they came from.
    """

    order: int
    value: int
    labels: List[str] = field(default_factory=list)
    complete: bool = False
    source: str = "gps_groups"

    def in_lmfdb(self):
        """The sublist of :attr:`labels` that has a row in ``gps_groups``."""
        if not self.labels:
            return []
        present = set(db.gps_groups.search({"label": {"$in": list(self.labels)}}, "label"))
        return [label for label in self.labels if label in present]

    def unique_label(self):
        """The one group this resolution pins down, when it pins down one that
        has a homepage; ``None`` otherwise."""
        if len(self.labels) != 1:
            return None
        if self.in_lmfdb() or live_pages_available(self.order):
            return self.labels[0]
        return None


def live_pages_available(order):
    """Whether a group of this order that is not in the LMFDB still gets a
    homepage, computed live from GAP's small group library.  Of the
    complete-table orders only 6561 = 3^8 misses out, being Magma-only."""
    return bool(libgap.SmallGroupsAvailable(int(order)))


def _sorted_labels(labels):
    # Deferred import: web_groups uses this module for its hash display.
    from .web_groups import label_sortkey
    return sorted(labels, key=label_sortkey)


def smallhash_counters(order, values):
    """The counters of the groups of ``order`` whose hash is one of ``values``,
    from the complete ``gps_smallhash`` table."""
    return sorted({int(c) for c in db.gps_smallhash.search(
        {"order": int(order), "hash": {"$in": [int(v) for v in values]}}, "counter")})


def resolve_order_hash(order, value):
    """The groups of order ``order`` whose hash is ``value``, as a
    :class:`HashResolution`."""
    order, value = int(order), int(value)
    if order in SMALLHASH_ORDERS:
        labels = [f"{order}.{c}" for c in smallhash_counters(order, [value])]
        return HashResolution(order, value, labels, True, "gps_smallhash")
    labels = _sorted_labels(db.gps_groups.search({"order": order, "hash": value}, "label"))
    return HashResolution(order, value, labels, False, "gps_groups")


def hash_constraint(order, values, qfield="hash"):
    """Search constraints selecting the groups of order ``order`` whose hash is
    one of ``values``, to be merged into a ``gps_groups`` query.

    ``order`` may be ``None`` when the order is unconstrained or constrained to
    a range, in which case the stored ``hash`` column is the only thing to go
    on: such a search can pick up a spurious row at one of the orders that
    store counters there, which giving a single order (or using the ``N#h``
    form) avoids.  With an order in hand we resolve the hashes to counters at
    the complete-table orders, since ``gps_groups.hash`` is not the hash there.
    """
    values = [int(v) for v in values]
    if order is not None and int(order) in SMALLHASH_ORDERS:
        return {"counter": {"$in": smallhash_counters(order, values)}}
    return {qfield: values[0] if len(values) == 1 else {"$or": values}}


def structural_hash(counter, stored):
    """The isomorphism-invariant hash to display for a ``gps_groups`` row, or
    ``None`` if the stored value is not one.

    The stored value is the label counter, rather than a hash, at the orders
    whose labels come from a small-group enumeration; the real hashes for those
    orders are only reachable through ``gps_smallhash``, which cannot be
    queried by ``(order, counter)`` (see the module docstring).  Filtering on
    ``stored == counter`` also drops the identifiable orders, where the hash
    *is* the small-group index and so is already visible in the label.
    """
    if stored is None or counter is None or int(stored) == int(counter):
        return None
    return int(stored)


def order_search_url(order):
    """URL of the search page listing all groups of the given order."""
    return url_for("abstract.index", order=int(order))


def hash_search_url(order, value):
    """URL of the search page listing all groups of the given order and hash."""
    return url_for("abstract.index", hash=f"{int(order)}#{int(value)}")

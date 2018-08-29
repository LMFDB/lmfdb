# See genus2_curves/web_g2c.py
# See templates/newform.html for how functions are called

from sage.all import prime_range
from lmfdb.db_backend import db

class WebNewform(object):
    def __init__(self, data):
        # Need to set level, weight, character, orbit, num_characters, degree, has_exact_qexp, has_complex_qexp, hecke_index, is_twist_minimal
        pass

    @staticmethod
    def by_label(label):
        # search in db.mf_newforms
        pass

    def field_display(self):
        # display the coefficient field
        pass

    def order_basis(self):
        # display the Hecke order, defining the variables used in the exact q-expansion display
        pass

    def qexp(self, all):
        # Display the q-expansion.  If all is False, truncate to a low precision (e.g. 10).  Will be inside \( \).
        pass

    def field_poly(self):
        # Display the polynomial defining the coefficient field
        pass

    def conrey_from_embedding(self, m):
        # Given an embedding number, return the Conrey label for the restriction of that embedding to the cyclotomic field
        pass

    def embedding(self, m, n=None, prec=6, format='embed'):
        """
        Return the value of the ``m``th embedding on a specified input.

        INPUT:

        - ``m`` -- an integer, specifying which embedding to use.
        - ``n`` -- an integer, specifying which a_n.  If None, returns the image of
            the generator of the field (i.e. the root corresponding to this embedding).
        - ``prec`` -- the precision to display floating point values
        - ``format`` -- either ``embed`` or ``analytic_embed``.  In the second case, divide by n^((k-1)/2).
        """
        pass

    def satake(self, m, p, prec=6, format='satake'):
        """
        Return a Satake parameter.

        INPUT:

        - ``m`` -- an integer, specifying which embedding to use.
        - ``p`` -- a prime, specifying which a_p.
        - ``prec`` -- the precision to display floating point values
        - ``format`` -- either ``satake`` or ``satake_angle``.  In the second case, give the argument of the Satake parameter
        """
        pass

    def embed_range(self, a, b, format='embed'):
        if format in ['embed', 'analytic_embed']:
            return range(a, b)
        else:
            return prime_range(a, b)

    def cm_field_knowl(self):
        # The knowl for the CM field, with appropriate title
        pass

    def atkinlehner_data(self):
        # A list of triples (Q, c, ev).  I'm not sure what these are exactly...
        pass

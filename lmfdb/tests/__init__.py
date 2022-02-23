# -*- coding: utf-8 -*-
import unittest2
from urllib.request import Request, urlopen
from urllib.error import URLError
import ssl
import errno
from lmfdb.app import app

# The following sage imports are used to check that various sage code
# download pages actually compile in sage. Future tests requiring additional
# imports should be declared here. The assertions following the imports
# keep pyflakes happy.

from sage.all import PolynomialRing, QQ, NumberField
assert PolynomialRing
assert QQ
assert NumberField


class LmfdbTest(unittest2.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.app = app
        self.tc = app.test_client()
        import lmfdb.website

        assert lmfdb.website
        from lmfdb import db

        self.db = db

    def check(self, homepage, path, text):
        assert path in homepage, "%s not in the homepage" % path
        assert text in self.tc.get(path, follow_redirects=True).get_data(
            as_text=True
        ), "%s not in the %s" % (text, path)

    def check_args(self, path, text):
        page = self.tc.get(path, follow_redirects=True).get_data(as_text=True)
        if not isinstance(text, list):
            text = [text]
        for t in text:
            assert t in page, "%s not in the %s" % (t, path)

    def check_args_with_timeout(self, path, text):
        timeout_error = "The search query took longer than expected!"
        data = self.tc.get(path, follow_redirects=True).get_data(as_text=True)
        assert (text in data) or (timeout_error in data), "%s not in the %s" % (
            text,
            path,
        )

    def not_check_args(self, path, text):
        page = self.tc.get(path, follow_redirects=True).get_data(as_text=True)
        if not isinstance(text, list):
            text = [text]
        for t in text:
            assert t not in page, "%s in the %s" % (t, path)

    def check_external(self, homepage, path, text):
        headers = {"User-Agent": "Mozilla/5.0"}
        context = ssl._create_unverified_context()
        request = Request(path, headers=headers)
        assert path in homepage
        try:
            assert text in urlopen(request, context=context).read().decode("utf-8")
        except URLError as e:
            if e.errno in [errno.ETIMEDOUT, errno.ECONNREFUSED, errno.EHOSTDOWN]:
                pass
            elif "Connection refused" in str(e):  # not every error comes with a errno
                pass
            else:
                print(e)
                print(e.errno)
                raise

    def assert_if_magma(self, expected, magma_code, mode='equal'):
        """Helper method for running test_download_magma test. Checks
        equality only if magma is installed; if it isn't, then the test
        passes."""
        from sage.all import magma
        try:
            if mode == 'equal':
                assert expected == magma.eval(magma_code)
            elif mode == 'in':
                assert expected in magma.eval(magma_code)
            else:
                raise ValueError("mode must be either 'equal' or 'in")
        except RuntimeError as the_error:
            if str(the_error).startswith("unable to start magma"):
                pass
            else:
                raise
    def check_sage_compiles_and_extract_variables(self, sage_code):
        """
        Simulates a user downloading the sage code, and then loading it
        into a sage session. This requires the sage imports at the top of
        the file. It returns a desired variable for further checks.

        sage_code [Type: str] : the sage code to execute
        my_name [Type: str] : name of the variable to extract from the
                              sage code. This then allows the developer
                              to implement subsequent checks.
        """

        exec(sage_code, globals())
        return globals()

    def check_sage_compiles_and_extract_var(self, sage_code, my_name):
        """
        Simulates a user downloading the sage code, and then loading it
        into a sage session. This requires the sage imports at the top of
        the file. It returns a desired variable for further checks.

        sage_code [Type: str] : the sage code to execute
        my_name [Type: str] : name of the variable to extract from the
                              sage code. This then allows the developer
                              to implement subsequent checks.
        """

        return self.check_sage_compiles_and_extract_variables(sage_code)[my_name]

import unittest

from urllib.request import Request, HTTPRedirectHandler, HTTPSHandler, HTTPHandler, build_opener
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


class CustomRedirectHandler(HTTPRedirectHandler):
    def http_error_308(self, req, fp, code, msg, headers):
        # Treat 308 like 307 to bypass the check in redirect_request in older Python versions
        # by passing the code 307.
        return self.http_error_307(req, fp, 307, msg, headers)

class LmfdbTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        # Ensure secret key is set for testing (required for session functionality like flash messages)
        if not app.secret_key:
            app.secret_key = "test_secret_key_for_testing_only"
        cls.app = app
        cls.tc = app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        import lmfdb.website

        assert lmfdb.website
        from lmfdb import db

        cls.db = db

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

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
        assert path in homepage, f"Path {path} not found in homepage"
        try:
            # Create opener that follows redirects for both HTTP and HTTPS, including 308
            redirect_handler = CustomRedirectHandler()
            http_handler = HTTPHandler()
            https_handler = HTTPSHandler(context=context)
            opener = build_opener(redirect_handler, http_handler, https_handler)
            response = opener.open(request)

            # Check if we were redirected
            final_url = response.geturl()
            if final_url != path:
                print(f"Redirected from {path} to {final_url}")

            response_text = response.read().decode("utf-8")

            assert text in response_text, f"Text '{text}' not found in response from {path} (final URL: {final_url})"
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
        has_magma = False
        try:
            has_magma = "2" == magma.eval("1 + 1")
        except (RuntimeError, TypeError):
            pass

        if has_magma:
            if mode == 'equal':
                magma_result = magma.eval(magma_code)
                assert expected == magma_result, f"Expected '{expected}', but magma.eval('{magma_code}') returned '{magma_result}'"
            elif mode == 'in':
                magma_result = magma.eval(magma_code)
                assert expected in magma_result, f"Expected '{expected}' to be in magma.eval('{magma_code}') result '{magma_result}'"
            else:
                raise ValueError("mode must be either 'equal' or 'in'")

    def check_sage_compiles_and_extract_variables(self, sage_code):
        """
        Simulates a user downloading the sage code, and then loading it
        into a sage session. This requires the sage imports at the top of
        the file. It returns a desired variable for further checks.

        INPUT:

        - sage_code [Type: str] : the sage code to execute

        - my_name [Type: str] : name of the variable to extract from the
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

        INPUT:

        - sage_code [Type: str] : the sage code to execute

        - my_name [Type: str] : name of the variable to extract from the
          sage code. This then allows the developer
          to implement subsequent checks.
        """
        return self.check_sage_compiles_and_extract_variables(sage_code)[my_name]

    def check_snippets(self, code, labels, path):
        # TODO: extract path from other data, eg. yaml
        pass

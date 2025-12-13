"""
Tests for random object redirects to ensure they use temporary redirects
with proper cache control headers, preventing browsers from caching the redirect.
"""
from lmfdb.tests import LmfdbTest


class RandomRedirectTest(LmfdbTest):
    """Test that random routes use correct redirect behavior"""

    def test_random_redirect_status_code(self):
        """
        Test that random routes return 307 (Temporary Redirect) status code
        instead of 301 (Permanent Redirect) to prevent browser caching.
        """
        random_routes = [
            '/NumberField/random',
            '/Groups/Abstract/random',
            '/Groups/GL2/Q/random',
            '/Groups/GL2/C/random',
            '/Character/Dirichlet/random',
            '/ModularForm/GL2/Q/holomorphic/random',
            '/ModularForm/GL2/ImaginaryQuadratic/random',
            '/Motive/Hypergeometric/Q/random_family',
            '/Motive/Hypergeometric/Q/random_motive',
        ]

        for route in random_routes:
            with self.subTest(route=route):
                response = self.tc.get(route, follow_redirects=False)
                self.assertEqual(
                    response.status_code,
                    307,
                    f"{route} should return 307 (Temporary Redirect), got {response.status_code}"
                )

    def test_random_redirect_cache_control(self):
        """
        Test that random routes have Cache-Control headers set to prevent caching.
        """
        random_routes = [
            '/NumberField/random',
            '/Groups/Abstract/random',
            '/Character/Dirichlet/random',
        ]

        for route in random_routes:
            with self.subTest(route=route):
                response = self.tc.get(route, follow_redirects=False)
                cache_control = response.headers.get('Cache-Control', '')
                self.assertIn(
                    'no-cache',
                    cache_control,
                    f"{route} should have 'no-cache' in Cache-Control header"
                )
                self.assertIn(
                    'no-store',
                    cache_control,
                    f"{route} should have 'no-store' in Cache-Control header"
                )

    def test_random_routes_work(self):
        """
        Test that random routes actually redirect to valid pages.
        This ensures the decorator doesn't break functionality.
        """
        random_routes_and_expected_content = [
            ('/NumberField/random', 'Discriminant'),
            ('/Groups/Abstract/random', 'Group information'),
            ('/Character/Dirichlet/random', 'Dirichlet character'),
            ('/Motive/Hypergeometric/Q/random_family', 'Hypergeometric motive family'),
            ('/Motive/Hypergeometric/Q/random_motive', 'Local information'),
        ]

        for route, expected_text in random_routes_and_expected_content:
            with self.subTest(route=route):
                response = self.tc.get(route, follow_redirects=True)
                self.assertEqual(
                    response.status_code,
                    200,
                    f"{route} should eventually return 200 OK"
                )
                page_content = response.get_data(as_text=True)
                self.assertIn(
                    expected_text,
                    page_content,
                    f"{route} should contain '{expected_text}' in the final page"
                )

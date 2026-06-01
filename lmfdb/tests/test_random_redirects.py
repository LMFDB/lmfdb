"""
Tests for random object redirects to ensure they use temporary redirects
with proper cache control headers, preventing browsers from caching the redirect.
"""
from lmfdb.tests import LmfdbTest


class RandomRedirectTest(LmfdbTest):
    """Test that random routes use correct redirect behavior"""

    # Dictionary mapping all random routes to expected text in the final page
    # This is used across all tests to ensure consistency
    RANDOM_ROUTES = {
        '/NumberField/random': 'Number field',
        '/Variety/Abelian/Fq/random': 'Abelian variety',
        '/ArtinRepresentation/random': 'Artin representation',
        '/Belyi/random': 'Belyi map',
        '/ModularForm/GL2/ImaginaryQuadratic/random': 'Bianchi',
        '/Character/Dirichlet/random': 'Dirichlet character',
        '/ModularForm/GL2/Q/holomorphic/random/': 'Modular form',
        '/ModularForm/GL2/Q/holomorphic/random_space/': 'Newspace',
        '/EllipticCurve/random/': 'Elliptic curve',
        '/EllipticCurve/Q/random': 'Elliptic curve',
        '/GaloisGroup/random': 'Galois group',
        '/Genus2Curve/Q/random/': 'Genus 2',
        '/Groups/Abstract/random': 'Abstract',
        '/Groups/GLnC/random': 'representation',
        '/Groups/GLnQ/random': 'representation',
        '/HigherGenus/C/Aut/random': 'genus',
        '/ModularForm/GL2/TotallyReal/random': 'Hilbert',
        '/random': 'LMFDB',  # homepage random redirects to various objects
        '/Motive/Hypergeometric/Q/random_family': 'family',
        '/Motive/Hypergeometric/Q/random_motive': 'motive',
        '/Lattice/random': 'Lattice',
        '/L/random': 'L-function',
        '/padicField/random': 'adic',
        '/ModularForm/GL2/Q/Maass/random': 'Maass',
        '/ModLGaloisRepresentation/Q/random/': 'Galois',
        '/ModularCurve/Q/random/': 'Modular curve',
        '/SatoTateGroup/random': 'Sato-Tate',
        '/ModularForm/GSp/Q/random': 'Siegel',
    }

    def test_random_redirect_status_code(self):
        """
        Test that random routes return 307 (Temporary Redirect) status code
        instead of 301 (Permanent Redirect) to prevent browser caching.
        """
        for route in self.RANDOM_ROUTES:
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
        for route in self.RANDOM_ROUTES:
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
        for route, expected_text in self.RANDOM_ROUTES.items():
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

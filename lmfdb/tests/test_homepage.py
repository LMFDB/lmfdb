import os
import yaml
import re
from lmfdb.tests import LmfdbTest


class HomePageTest(LmfdbTest):
    _links_data = None
    _homepage_content = None

    @classmethod
    def _parse_links_from_content(cls, content):
        """Extract links from HTML content."""
        link_pattern = r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>'
        return re.findall(link_pattern, content, re.IGNORECASE)

    @classmethod
    def _get_links_data(cls):
        """Parse YAML file once and return all links with metadata."""
        if cls._links_data is None:
            lmfdb_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            yaml_path = os.path.join(lmfdb_dir, "homepage", "index_boxes.yaml")

            with open(yaml_path, "r") as f:
                boxes = list(yaml.load_all(f, Loader=yaml.FullLoader))

            links = []
            for box_idx, box in enumerate(boxes):
                box_title = box.get("title", f"Box {box_idx + 1}")

                if "content" in box:
                    urls = cls._parse_links_from_content(box["content"])
                    for url in urls:
                        links.append({
                            "url": url,
                            "box_title": box_title,
                            "is_external": url.startswith(('http://', 'https://')),
                            "is_internal": url.startswith('/'),
                        })

            cls._links_data = links
        return cls._links_data

    def _get_homepage(self):
        """Get homepage content once and cache it."""
        if self._homepage_content is None:
            self._homepage_content = self.tc.get("/").get_data(as_text=True)
        return self._homepage_content

    def _test_link(self, link_info):
        """Test a single link."""
        url = link_info["url"]
        box_title = link_info["box_title"]
        homepage = self._get_homepage()

        # Check that link appears in homepage
        self.assertIn(url, homepage,
                     f"Link {url} from {box_title} not found in homepage")

        if link_info["is_external"]:
            # Test external links
            try:
                self.check_external(homepage, url, "html")
            except AssertionError:
                self.check_external(homepage, url, "<")
        elif link_info["is_internal"]:
            # Test internal links
            response = self.tc.get(url, follow_redirects=True)
            self.assertEqual(response.status_code, 200,
                           f"Internal link {url} from {box_title} returned status {response.status_code}")

    def test_all_internal_links(self):
        """Test all internal links found in index_boxes.yaml."""
        links = self._get_links_data()
        internal_links = [link for link in links if link["is_internal"]]

        for link_info in internal_links:
            with self.subTest(url=link_info["url"], box=link_info["box_title"]):
                self._test_link(link_info)

    def test_all_external_links(self):
        """Test all external links found in index_boxes.yaml."""
        links = self._get_links_data()
        external_links = [link for link in links if link["is_external"]]

        for link_info in external_links:
            with self.subTest(url=link_info["url"], box=link_info["box_title"]):
                self._test_link(link_info)

    def test_all_links_by_box(self):
        """Test all links grouped by box."""
        links = self._get_links_data()

        # Group links by box
        boxes = {}
        for link in links:
            box_title = link["box_title"]
            if box_title not in boxes:
                boxes[box_title] = []
            boxes[box_title].append(link)

        for box_title, box_links in boxes.items():
            with self.subTest(box=box_title):
                for link_info in box_links:
                    with self.subTest(url=link_info["url"]):
                        self._test_link(link_info)

    def test_random_link(self):
        """Test the global random link functionality."""
        response = self.tc.get("/random", follow_redirects=True)
        assert "Properties" in response.get_data(as_text=True)


# Dynamic test generation for individual boxes
def _create_box_test(box_title, box_links):
    """Create a test method for a specific box."""
    def test_method(self):
        for link_info in box_links:
            with self.subTest(url=link_info["url"]):
                self._test_link(link_info)

    test_method.__doc__ = f"Test links from box: {box_title}"
    return test_method


# Add individual box tests
try:
    links = HomePageTest._get_links_data()

    # Group links by box for dynamic test creation
    boxes = {}
    for link in links:
        box_title = link["box_title"]
        if box_title not in boxes:
            boxes[box_title] = []
        boxes[box_title].append(link)

    # Create test methods for each box
    for box_title, box_links in boxes.items():
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', box_title.lower())
        method_name = f"test_box_{safe_name}"
        setattr(HomePageTest, method_name, _create_box_test(box_title, box_links))

except Exception:
    # Graceful fallback if YAML can't be read
    pass

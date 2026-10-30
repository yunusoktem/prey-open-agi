import os
import unittest
from unittest.mock import patch

import analiz
from evoskill_bridge import load_mode_skills
from ods_engine import is_ods_configured


class CoreSafetyTests(unittest.TestCase):
    def test_unicode_normalization_preserves_cyrillic_and_chinese(self):
        self.assertEqual(analiz._norm("Привет Мир"), "привет мир")
        self.assertEqual(analiz._norm("人工智能"), "人工智能")

    def test_private_and_local_urls_are_rejected(self):
        for url in (
            "http://127.0.0.1/admin",
            "http://localhost/",
            "http://192.168.1.1/",
            "file:///etc/passwd",
        ):
            self.assertFalse(analiz._safe_public_url(url), url)

    def test_public_https_url_is_accepted(self):
        self.assertTrue(analiz._safe_public_url("https://example.com/docs"))

    def test_free_search_uses_bounded_query_count(self):
        self.assertEqual(len(analiz._search_queries("Example Protocol")), 4)

    def test_mode_skills_are_loaded_from_repository(self):
        self.assertIn("research", load_mode_skills("research").lower())
        self.assertIn("ssrf", load_mode_skills("coding").lower())
        self.assertEqual(load_mode_skills("../../etc/passwd"), "")

    def test_ods_is_not_advertised_without_runtime_and_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_ods_configured())


if __name__ == "__main__":
    unittest.main()

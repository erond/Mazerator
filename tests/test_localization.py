from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import unittest

from maze_generator import generate_mazes as gm


class TestLocalizations(unittest.TestCase):
    def test_supported_locales(self):
        expected = {
            "ar", "bn", "de", "el", "en", "es", "fr",
            "hi", "it", "pl", "pt", "ro", "ru", "uk", "zh"
        }
        self.assertEqual(set(gm.LOCALIZATIONS), expected)
        self.assertEqual(gm.DEFAULT_LOCALE, "en")

    def test_localization_bundles_have_required_keys(self):
        required = {
            "start_label",
            "goal_label",
            "page_label",
            "last_page_prefix",
            "pdf_title",
            "theme_pool",
        }
        for code, bundle in gm.LOCALIZATIONS.items():
            self.assertTrue(required.issubset(bundle))
            self.assertEqual(len(bundle["theme_pool"]), len(gm.THEME_POOL))


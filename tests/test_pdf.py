from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import importlib.util
import tempfile
import unittest

from maze_generator import generate_mazes as gm


@unittest.skipUnless(importlib.util.find_spec("reportlab"), "reportlab not installed")
class TestPdfIntegration(unittest.TestCase):
    def test_build_creates_nonempty_pdf(self):
        temp_dir_path = None
        with tempfile.TemporaryDirectory(prefix="mazerator_test_pdf_") as tmp:
            temp_dir_path = Path(tmp)
            out = temp_dir_path / "test_artifact_build_nonempty.pdf"
            self.assertNotEqual(out.name, "mazes.pdf")
            sizes = gm.build(str(out), pages=3, master_seed=99, difficulty=2.0)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 1000)
            self.assertEqual(len(sizes), 3)
            with out.open("rb") as fh:
                self.assertTrue(fh.read(5).startswith(b"%PDF-"))
        self.assertIsNotNone(temp_dir_path)
        self.assertFalse(temp_dir_path.exists())

    def test_same_seed_byte_identical_pdf(self):
        temp_dir_path = None
        with tempfile.TemporaryDirectory(prefix="mazerator_test_pdf_") as tmp:
            temp_dir_path = Path(tmp)
            p1 = temp_dir_path / "test_artifact_seed_a.pdf"
            p2 = temp_dir_path / "test_artifact_seed_b.pdf"
            self.assertNotEqual(p1.name, "mazes.pdf")
            self.assertNotEqual(p2.name, "mazes.pdf")
            gm.build(str(p1), pages=2, master_seed=5, difficulty=3.0)
            gm.build(str(p2), pages=2, master_seed=5, difficulty=3.0)
            with p1.open("rb") as f1, p2.open("rb") as f2:
                self.assertEqual(f1.read(), f2.read())
        self.assertIsNotNone(temp_dir_path)
        self.assertFalse(temp_dir_path.exists())

    def test_all_locales_render_one_page(self):
        temp_dir_path = None
        with tempfile.TemporaryDirectory(prefix="mazerator_test_pdf_") as tmp:
            temp_dir_path = Path(tmp)
            for code in sorted(gm.LOCALIZATIONS):
                out = temp_dir_path / f"test_artifact_locale_{code}.pdf"
                self.assertNotEqual(out.name, "mazes.pdf")
                gm.build(str(out), pages=1, master_seed=17, difficulty=2.0, locale=code)
                self.assertTrue(out.exists())
                self.assertGreater(out.stat().st_size, 1000)
        self.assertIsNotNone(temp_dir_path)
        self.assertFalse(temp_dir_path.exists())


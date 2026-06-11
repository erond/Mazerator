from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import importlib
import tempfile
import unittest
from unittest import mock

from maze_generator import generate_mazes as gm


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

    def test_locale_rendering_with_forced_font_fallback(self):
        """Force missing Unicode font files and ensure rendering still succeeds."""
        temp_dir_path = None
        with tempfile.TemporaryDirectory(prefix="mazerator_test_pdf_") as tmp:
            temp_dir_path = Path(tmp)
            out = temp_dir_path / "test_artifact_fallback_locale_el.pdf"
            self.assertNotEqual(out.name, "mazes.pdf")

            with mock.patch.object(gm, "UNICODE_FONT_CANDIDATES", ["/definitely/missing/unicode.ttf"]):
                gm.build(str(out), pages=1, master_seed=17, difficulty=2.0, locale="el")

            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 1000)
            with out.open("rb") as fh:
                self.assertTrue(fh.read(5).startswith(b"%PDF-"))

        self.assertIsNotNone(temp_dir_path)
        self.assertFalse(temp_dir_path.exists())

    def test_footer_reports_seed(self):
        """Every page footer should carry the seed used for the build."""
        pypdf = importlib.import_module("pypdf")

        temp_dir_path = None
        with tempfile.TemporaryDirectory(prefix="mazerator_test_pdf_") as tmp:
            temp_dir_path = Path(tmp)
            out = temp_dir_path / "test_artifact_seed_footer.pdf"
            self.assertNotEqual(out.name, "mazes.pdf")

            gm.build(str(out), pages=2, master_seed=424242, difficulty=2.0)

            reader = pypdf.PdfReader(str(out))
            for page in reader.pages:
                extracted = page.extract_text() or ""
                self.assertIn("Seed: 424242", extracted)

        self.assertIsNotNone(temp_dir_path)
        self.assertFalse(temp_dir_path.exists())

    def test_forced_font_fallback_extracts_expected_labels(self):
        """Fallback rendering should preserve extractable locale labels."""
        pypdf = importlib.import_module("pypdf")

        temp_dir_path = None
        with tempfile.TemporaryDirectory(prefix="mazerator_test_pdf_") as tmp:
            temp_dir_path = Path(tmp)
            out = temp_dir_path / "test_artifact_fallback_locale_ro_text.pdf"
            self.assertNotEqual(out.name, "mazes.pdf")

            with mock.patch.object(gm, "UNICODE_FONT_CANDIDATES", ["/definitely/missing/unicode.ttf"]):
                gm.build(str(out), pages=1, master_seed=17, difficulty=2.0, locale="ro")

            reader = pypdf.PdfReader(str(out))
            extracted = "\n".join((page.extract_text() or "") for page in reader.pages)
            self.assertIn("START", extracted)
            self.assertIn("SOSIRE", extracted)

        self.assertIsNotNone(temp_dir_path)
        self.assertFalse(temp_dir_path.exists())


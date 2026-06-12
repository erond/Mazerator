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

    def test_labels_never_overlap_difficulty_stars_band(self):
        """Entrance/exit labels must stay clear of the title/stars header.

        Regression for a top-edge opening whose label was drawn on top of the
        difficulty stars (reported seed 9467890544195417111).
        """
        title_y = min(gm.PAGE_H - 42, gm.MAZE_TOP + 152)
        star_y = title_y - 24
        star_x0 = gm.PAGE_W / 2 - (5 * 16) / 2 + 8
        stars_band = (star_x0 - 8, star_y - 8, star_x0 + 4 * 16 + 8, star_y + 8)
        title_band = (0, title_y - 6, gm.PAGE_W, title_y + 16)

        def overlaps(a, b):
            ax0, ay0, ax1, ay1 = a
            bx0, by0, bx1, by1 = b
            return not (ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0)

        cases = [
            (9467890544195417111, 12, "it"),
            (9467890544195417111, 24, "en"),
            (9467890544195417111, 30, "it"),
            (7, 20, "en"),
            (123456789, 16, "ro"),
        ]
        original = gm.place_icon_and_label
        captured = []

        def spy(c, point, icon_name, label, size, label_font="Helvetica-Bold", **kw):
            result = original(c, point, icon_name, label, size, label_font, **kw)
            captured.append((label, result["label_rect"]))
            return result

        with tempfile.TemporaryDirectory(prefix="mazerator_test_pdf_") as tmp:
            out = Path(tmp) / "test_artifact_header_clear.pdf"
            with mock.patch.object(gm, "place_icon_and_label", spy):
                for seed, pages, locale in cases:
                    captured.clear()
                    gm.build(str(out), pages=pages, master_seed=seed,
                             difficulty=6.0, locale=locale)
                    for label, rect in captured:
                        self.assertFalse(
                            overlaps(rect, stars_band),
                            f"label {label!r} overlaps stars band "
                            f"(seed={seed}, pages={pages}, locale={locale}): {rect}",
                        )
                        self.assertFalse(
                            overlaps(rect, title_band),
                            f"label {label!r} overlaps title band "
                            f"(seed={seed}, pages={pages}, locale={locale}): {rect}",
                        )

    def test_decorations_toggle_controls_margin_motifs(self):
        """Disabling decorations must drop the playful margin motifs.

        The same motif primitives can also serve as entrance/exit theme icons,
        so we compare counts for an identical seed: turning decorations off must
        strictly reduce the number of motif draws (the margin motifs disappear).
        """
        # `star` also draws difficulty stars; counting it would mask the margin
        # motifs, so spy only on motif primitives that are not used elsewhere
        # on every page.
        motif_names = ("draw_cloud", "draw_flower", "draw_heart", "draw_star")

        def count_motifs(decorations):
            counters = {"n": 0}

            def make_spy(orig):
                def spy(*args, **kwargs):
                    counters["n"] += 1
                    return orig(*args, **kwargs)
                return spy

            patches = [
                mock.patch.object(gm, name, make_spy(getattr(gm, name)))
                for name in motif_names
            ]
            with tempfile.TemporaryDirectory(prefix="mazerator_test_pdf_") as tmp:
                out = Path(tmp) / "test_artifact_decorations.pdf"
                for p in patches:
                    p.start()
                try:
                    gm.build(str(out), pages=4, master_seed=2026, difficulty=4.0,
                             locale="en", decorations=decorations)
                finally:
                    for p in patches:
                        p.stop()
                self.assertTrue(out.exists())
                self.assertGreater(out.stat().st_size, 1000)
            return counters["n"]

        with_deco = count_motifs(decorations=True)
        without_deco = count_motifs(decorations=False)
        self.assertGreater(with_deco, without_deco)

    def test_decorations_disabled_pdf_is_valid(self):
        """A motif-free build is still a valid, non-empty PDF with labels."""
        pypdf = importlib.import_module("pypdf")
        with tempfile.TemporaryDirectory(prefix="mazerator_test_pdf_") as tmp:
            out = Path(tmp) / "test_artifact_no_decorations.pdf"
            gm.build(str(out), pages=2, master_seed=2026, difficulty=3.0,
                     locale="en", decorations=False)
            self.assertTrue(out.exists())
            reader = pypdf.PdfReader(str(out))
            extracted = "\n".join((page.extract_text() or "") for page in reader.pages)
            self.assertIn("START", extracted)

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


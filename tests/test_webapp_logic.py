from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import unittest

from maze_generator.generate_mazes import (
    GenerationOptions,
    MAX_DIFFICULTY,
    MIN_DIFFICULTY,
)
from maze_generator.webapp_logic import (
    PRESET_BY_KEY,
    PRESETS,
    UiInputs,
    build_download_filename,
    find_matching_preset,
    locale_display_name,
    locale_menu_label,
    make_generation_options,
    parse_seed,
    sanitize_output_stem,
)


class TestWebAppLogic(unittest.TestCase):
    def test_parse_seed_accepts_empty(self):
        self.assertIsNone(parse_seed(""))
        self.assertIsNone(parse_seed("   "))

    def test_parse_seed_accepts_integer(self):
        self.assertEqual(parse_seed("42"), 42)
        self.assertEqual(parse_seed("  -7 "), -7)

    def test_parse_seed_rejects_invalid(self):
        with self.assertRaisesRegex(ValueError, "seed must be empty or an integer"):
            parse_seed("x12")

    def test_sanitize_output_stem(self):
        self.assertEqual(sanitize_output_stem("My Mazes 2026!"), "My-Mazes-2026")
        self.assertEqual(sanitize_output_stem("   "), "mazes")

    def test_build_download_filename_with_seed(self):
        inputs = UiInputs(
            pages=20,
            difficulty=3.0,
            min_path_factor=0.5,
            locale="it",
            seed=123,
            output_stem="Kid Mazes",
        )
        name = build_download_filename(inputs)
        self.assertEqual(name, "Kid-Mazes_it_20p_seed-123.pdf")

    def test_make_generation_options(self):
        inputs = UiInputs(
            pages=12,
            difficulty=2.5,
            min_path_factor=0.65,
            locale="en",
            seed=99,
            output_stem="custom",
        )
        out = Path("/tmp/test-output.pdf")
        opts = make_generation_options(inputs, out)
        self.assertIsInstance(opts, GenerationOptions)
        self.assertEqual(opts.output, str(out))
        self.assertEqual(opts.pages, 12)
        self.assertEqual(opts.difficulty, 2.5)
        self.assertEqual(opts.seed, 99)
        self.assertEqual(opts.min_path_factor, 0.65)
        self.assertEqual(opts.locale, "en")
        self.assertTrue(opts.decorations)

    def test_decorations_default_enabled(self):
        inputs = UiInputs(pages=5, difficulty=2.0, min_path_factor=0.5)
        self.assertTrue(inputs.decorations)

    def test_make_generation_options_propagates_decorations(self):
        inputs = UiInputs(
            pages=8,
            difficulty=2.0,
            min_path_factor=0.5,
            locale="en",
            decorations=False,
        )
        opts = make_generation_options(inputs, Path("/tmp/test-output.pdf"))
        self.assertFalse(opts.decorations)

    def test_locale_display_name(self):
        self.assertEqual(locale_display_name("it"), "Italian")
        self.assertEqual(locale_display_name("zh"), "Chinese")

    def test_locale_display_name_fallback(self):
        self.assertEqual(locale_display_name("xx"), "xx")

    def test_locale_menu_label_includes_flag_and_name(self):
        self.assertEqual(locale_menu_label("it"), "🇮🇹 Italian")
        self.assertEqual(locale_menu_label("zh"), "🇨🇳 Chinese")

    def test_locale_menu_label_fallback(self):
        self.assertEqual(locale_menu_label("xx"), "🏳️ xx")


class TestPresets(unittest.TestCase):
    def test_expected_presets_present_and_ordered(self):
        keys = [p.key for p in PRESETS]
        self.assertEqual(keys, ["simple", "medium", "hard"])

    def test_presets_are_monotonic_in_difficulty(self):
        diffs = [p.difficulty for p in PRESETS]
        self.assertEqual(diffs, sorted(diffs))
        paths = [p.min_path_factor for p in PRESETS]
        self.assertEqual(paths, sorted(paths))

    def test_preset_values_within_supported_bounds(self):
        for preset in PRESETS:
            self.assertGreaterEqual(preset.difficulty, MIN_DIFFICULTY)
            self.assertLessEqual(preset.difficulty, MAX_DIFFICULTY)
            self.assertGreaterEqual(preset.min_path_factor, 0.1)
            self.assertLessEqual(preset.min_path_factor, 1.0)
            self.assertGreaterEqual(preset.pages, 1)
            self.assertTrue(preset.age)
            self.assertTrue(preset.blurb)

    def test_find_matching_preset_exact(self):
        simple = PRESET_BY_KEY["simple"]
        self.assertEqual(
            find_matching_preset(simple.pages, simple.difficulty, simple.min_path_factor),
            "simple",
        )

    def test_find_matching_preset_none_when_off(self):
        simple = PRESET_BY_KEY["simple"]
        self.assertIsNone(
            find_matching_preset(simple.pages + 1, simple.difficulty, simple.min_path_factor)
        )


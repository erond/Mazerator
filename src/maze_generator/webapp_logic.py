"""Pure helpers for the Streamlit web UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import tempfile

from .generate_mazes import DEFAULT_LOCALE, GenerationOptions, run_generation

_FILENAME_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")
LOCALE_NAMES = {
    "ar": "Arabic",
    "bn": "Bengali",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "hi": "Hindi",
    "it": "Italian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "uk": "Ukrainian",
    "zh": "Chinese",
}

# Representative country flag per language (languages without a single country
# use the most commonly associated flag).
LOCALE_FLAGS = {
    "ar": "🇸🇦",
    "bn": "🇧🇩",
    "de": "🇩🇪",
    "el": "🇬🇷",
    "en": "🇬🇧",
    "es": "🇪🇸",
    "fr": "🇫🇷",
    "hi": "🇮🇳",
    "it": "🇮🇹",
    "pl": "🇵🇱",
    "pt": "🇵🇹",
    "ro": "🇷🇴",
    "ru": "🇷🇺",
    "uk": "🇺🇦",
    "zh": "🇨🇳",
}


@dataclass(frozen=True)
class UiInputs:
    """Validated user inputs from the web interface."""

    pages: int
    difficulty: float
    min_path_factor: float
    locale: str = DEFAULT_LOCALE
    seed: int | None = None
    output_stem: str = "mazes"
    decorations: bool = True


@dataclass(frozen=True)
class Preset:
    """A named, age-targeted bundle of generation settings."""

    key: str
    label: str
    icon: str
    age: str
    blurb: str
    pages: int
    difficulty: float
    min_path_factor: float


# Ordered easiest -> hardest. Lower difficulty => smaller grids; lower
# min_path_factor => shorter forced solution (gentler for younger kids).
PRESETS: tuple[Preset, ...] = (
    Preset("simple", "Simple", "👶", "Ages 2–4",
           "Small grids and short, gentle paths for first-time solvers.",
           pages=12, difficulty=2.0, min_path_factor=0.30),
    Preset("medium", "Medium", "🧒", "Ages 3–5",
           "Balanced grids and solution length for growing confidence.",
           pages=16, difficulty=5.0, min_path_factor=0.50),
    Preset("hard", "Hard", "👩‍🎓", "Ages 4–6",
           "Larger grids and longer, twistier routes for a real challenge.",
           pages=20, difficulty=7.0, min_path_factor=0.65),
)

PRESET_BY_KEY: dict[str, Preset] = {p.key: p for p in PRESETS}


def find_matching_preset(
    pages: int, difficulty: float, min_path_factor: float
) -> str | None:
    """Return the preset key whose settings match the given values, if any."""
    for preset in PRESETS:
        if (
            preset.pages == pages
            and abs(preset.difficulty - difficulty) < 1e-9
            and abs(preset.min_path_factor - min_path_factor) < 1e-9
        ):
            return preset.key
    return None


def locale_display_name(locale_code: str) -> str:
    """Return a user-friendly language name for a locale code."""
    return LOCALE_NAMES.get(locale_code, locale_code)


def locale_menu_label(locale_code: str) -> str:
    """Return a flag + space + language name label for menus."""
    flag = LOCALE_FLAGS.get(locale_code, "🏳️")
    return f"{flag} {locale_display_name(locale_code)}"


def parse_seed(seed_text: str) -> int | None:
    """Parse an optional seed from text input."""
    stripped = seed_text.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError as exc:
        raise ValueError("seed must be empty or an integer") from exc


def sanitize_output_stem(stem: str) -> str:
    """Return a filesystem-safe filename stem."""
    cleaned = _FILENAME_SAFE.sub("-", stem.strip()).strip("-._")
    return cleaned or "mazes"


def build_download_filename(inputs: UiInputs, seed_used: int | None = None) -> str:
    """Create a descriptive download filename."""
    used_seed = inputs.seed if seed_used is None else seed_used
    if used_seed is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        seed_tag = f"random-{timestamp}"
    else:
        seed_tag = f"seed-{used_seed}"
    stem = sanitize_output_stem(inputs.output_stem)
    return f"{stem}_{inputs.locale}_{inputs.pages}p_{seed_tag}.pdf"


def make_generation_options(inputs: UiInputs, output_path: Path) -> GenerationOptions:
    """Translate UI inputs into generator options."""
    return GenerationOptions(
        output=str(output_path),
        pages=inputs.pages,
        difficulty=inputs.difficulty,
        seed=inputs.seed,
        min_path_factor=inputs.min_path_factor,
        locale=inputs.locale,
        decorations=inputs.decorations,
    )


def generate_pdf_bytes(inputs: UiInputs) -> tuple[bytes, int, list[int]]:
    """Generate a PDF and return bytes + execution metadata."""
    with tempfile.TemporaryDirectory(prefix="mazerator_streamlit_") as tmp:
        out = Path(tmp) / "mazerator-output.pdf"
        opts = make_generation_options(inputs, out)
        seed_used, sizes = run_generation(opts)
        pdf_bytes = out.read_bytes()
    return pdf_bytes, seed_used, sizes

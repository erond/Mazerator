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


@dataclass(frozen=True)
class UiInputs:
    """Validated user inputs from the web interface."""

    pages: int
    difficulty: float
    min_path_factor: float
    locale: str = DEFAULT_LOCALE
    seed: int | None = None
    output_stem: str = "mazes"


def locale_display_name(locale_code: str) -> str:
    """Return a user-friendly language name for a locale code."""
    return LOCALE_NAMES.get(locale_code, locale_code)


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
    )


def generate_pdf_bytes(inputs: UiInputs) -> tuple[bytes, int, list[int]]:
    """Generate a PDF and return bytes + execution metadata."""
    with tempfile.TemporaryDirectory(prefix="mazerator_streamlit_") as tmp:
        out = Path(tmp) / "mazerator-output.pdf"
        opts = make_generation_options(inputs, out)
        seed_used, sizes = run_generation(opts)
        pdf_bytes = out.read_bytes()
    return pdf_bytes, seed_used, sizes

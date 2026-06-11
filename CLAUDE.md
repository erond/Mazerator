# CLAUDE.md

Maintainer context for Claude Code sessions in this repository.

## Project Intent

`Mazerator` generates printable A4 black-and-white PDF maze booklets for kids.
It is fully offline (no AI/runtime services), library-first, and deterministic
when a seed is provided.

Primary goals:
- generate "perfect mazes" (spanning tree => one unique solution),
- increase difficulty page-by-page,
- enforce non-trivial solution length (`min_path_factor`),
- support locale-aware labels/theme text in a single PDF pipeline.

## Source Of Truth

- Implementation: `src/maze_generator/generate_mazes.py`
- CLI entrypoint: `src/maze_generator/cli.py`
- Tests: `tests/test_*.py`
- Packaging/deps: `pyproject.toml`
- CI: `.github/workflows/ci.yml`

Prefer updating code/tests first, then README if behavior/flags changed.

## Architecture Notes

`generate_mazes.py` is intentionally split by concern:
- pure maze logic (testable without reportlab),
- path selection/complexity guarantees,
- rendering helpers and PDF build path (lazy imports for reportlab).

Localization is driven by `LOCALIZATIONS` bundle entries:
- labels/title/theme pool,
- font keys: `title_font`, `label_font`, `footer_font`.

## Font/Locale Rendering (Important)

Recent fix: locale PDF generation must not fail on Linux CI due to missing
macOS-only Unicode fonts.

Current behavior:
- `UNICODE_FONT_CANDIDATES` includes macOS + common Linux paths.
- if no Unicode candidate exists, `_register_locale_fonts(...)` registers a
  safe fallback alias (`UniversalUnicode` -> Helvetica/WinAnsi) instead of
  raising.

Why: keeps generation/test flow alive in minimal runners and local envs.

## Test Strategy

Test layers:
- algorithmic/unit tests (no reportlab requirement),
- PDF integration tests (gated by `reportlab` availability),
- fallback-specific integration checks.

Fallback coverage added:
- forced missing Unicode candidates still produce valid `%PDF` output,
- optional text extraction check via `pypdf` verifies expected labels under
  forced fallback path.

CI installs `pypdf` explicitly in workflow:
- `pip install -e . pypdf`

## Local Dev Commands

Recommended (uv):
```bash
uv run mazerator
uv run --with reportlab python -m unittest discover -s tests -p "test_*.py" -v
```

Standard Python:
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -e . pypdf
python3 -m unittest discover -s tests -p "test_*.py" -v
```

## Change Rules For Future Agents

- Do not break deterministic output for fixed `--seed`.
- Keep CLI backward-compatible unless explicitly requested.
- Keep pure logic import-safe (avoid hard reportlab dependency at module load).
- Add/adjust tests for behavior changes; avoid "fix without test" when feasible.
- For locale/font changes, validate both:
  - PDF artifact generation, and
  - at least one semantic signal (labels/text extraction when available).

## Known Practical Constraints

- PDF text extraction from non-Latin scripts can vary by font/extractor; keep
  assertions conservative and stable.
- Local test runs may skip PDF tests if `reportlab` is missing; CI is expected
  to run them.

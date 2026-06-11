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
- keep difficulty bounded to `[1, 10]` across CLI/web/runtime validation.

## Source Of Truth

- Implementation: `src/maze_generator/generate_mazes.py`
- CLI entrypoint: `src/maze_generator/cli.py`
- Streamlit app UI: `src/maze_generator/webapp.py`
- Streamlit app pure logic: `src/maze_generator/webapp_logic.py`
- Streamlit launcher: `src/maze_generator/webapp_cli.py`
- Tests: `tests/test_*.py`
- Packaging/deps: `pyproject.toml`
- CI: `.github/workflows/ci.yml`

Prefer updating code/tests first, then README if behavior/flags changed.

## Architecture Notes

`generate_mazes.py` is intentionally split by concern:
- pure maze logic (testable without reportlab),
- path selection/complexity guarantees,
- rendering helpers and PDF build path (lazy imports for reportlab).

Web UI split:
- `webapp.py`: Streamlit presentation layer only (layout, controls, styling).
- `webapp_logic.py`: pure/testable UI helpers (seed parsing, filenames, generation adapter).
- Input controls are hosted in `st.sidebar` (left panel); main pane is output/download.
- On mobile, sidebar auto-collapses after submit so users can reach download quickly.
  Implemented via injected JS (`_collapse_sidebar_on_mobile_after_submit`) that clicks
  Streamlit's collapse control. The injected HTML MUST embed a per-run nonce
  (`_gen_count`) — identical `components.html` payloads are cached by Streamlit and the
  script will not re-execute on repeat generations. Detect device width via
  `window.parent.innerWidth` (the iframe's own width is not the device viewport), and
  retry/poll until `section[data-testid="stSidebar"]` is actually collapsed.
- On mobile, fallback behavior must scroll/focus to the download CTA even if sidebar
  collapse fails (`_focus_download_area_on_mobile`, also nonce-keyed).
- Main pane includes a visual user guidance flow (icon steps + connectors), practical tips,
  and a configuration preview bound to current sidebar values.
- Locale selectors must display human-readable language names while preserving code values internally.
- Age-based difficulty presets live in `webapp_logic.py` (`PRESETS`, `PRESET_BY_KEY`,
  `find_matching_preset`); UI is a sidebar `st.segmented_control` whose `on_change`
  callback writes the `cfg_*` widget state, plus a main-pane card showcase that
  highlights the active preset. Keep preset values inside the documented bounds
  (difficulty `[1,10]`, path factor `[0.1,1.0]`) and add/adjust them in the logic
  module (with tests), never inline in the UI.
- Sidebar controls are driven purely via `st.session_state` defaults
  (`_CONTROL_DEFAULTS` seeded with `setdefault`); widgets use `key=` only (no
  `value=`/`index=`) so presets/reset can set state without the "default value +
  session state" warning. Reset uses an `on_click` callback.
- Streamlit theming source of truth: `.streamlit/config.toml` (`[theme]`).
- Keep the app palette visually consistent with the black/white logo (neutral monochrome).

Localization is driven by `LOCALIZATIONS` bundle entries:
- labels/title/theme pool,
- font keys: `title_font`, `label_font`, `footer_font`.

`RECOMMENDED_MAX_PATH_FACTOR = 0.65` is the advised ceiling for
`min_path_factor`. It is NOT enforced (the slider/CLI still allow up to 1.0), but
must be surfaced everywhere: CLI `--min-path-factor` help, the webapp slider help
plus an inline `st.warning` when exceeded, `run_generation` emits a stderr
warning, and the README documents it. Above it, carving is much slower and the
target may be unreachable (the generator relaxes it). Keep all built-in presets
at or below this value.

Each page footer shows the centered page label and a small right-aligned
`Seed: <n>` reference (`draw_page(..., seed=master_seed)`). `run_generation`
always resolves a concrete seed before calling `build`, so even random runs
print a reusable seed for byte-identical reprints.

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

Policy:
- test suite should run with **no skipped tests** in normal project environments;
  required test dependencies are part of install requirements.
- CI must fail if any test is skipped, failed, or errors.

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

Streamlit web UI:
```bash
uv run mazerator-web
# or
python -m streamlit run src/maze_generator/webapp.py
```

## Change Rules For Future Agents

- Do not break deterministic output for fixed `--seed`.
- Keep CLI backward-compatible unless explicitly requested.
- Keep pure logic import-safe (avoid hard reportlab dependency at module load).
- Keep Streamlit UI thin and move business logic to `webapp_logic.py`.
- Keep contrast accessible in both light/dark themes (no low-visibility text).
- Use vector logo asset (`docs/mazerator_logo.svg`) in web UI.
- Prefer Streamlit native theming/config over broad CSS color overrides.
- Do not add an in-app theme selector; rely on Streamlit built-in Light/Dark/System UI.
- Do not add in-page toolbar controls for theme/repo links unless explicitly requested.
- Add/adjust tests for behavior changes; avoid "fix without test" when feasible.
- For locale/font changes, validate both:
  - PDF artifact generation, and
  - at least one semantic signal (labels/text extraction when available).

## Known Practical Constraints

- PDF text extraction from non-Latin scripts can vary by font/extractor; keep
  assertions conservative and stable.
- Local test runs may skip PDF tests if `reportlab` is missing; CI is expected
  to run them.
- Streamlit is not a static site artifact; deployment requires an app runtime
  (hosted Streamlit/container/PaaS).
- GitHub Pages cannot serve the Streamlit runtime; use GitHub for source + CI/CD deployment.
- Light/Dark/System are user-selected in Streamlit Settings UI; app-level controls
  should not attempt to override Streamlit internals.

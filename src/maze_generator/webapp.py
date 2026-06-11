"""Streamlit web app for Mazerator."""

from __future__ import annotations

import importlib
from pathlib import Path

try:
    from .generate_mazes import (
        DEFAULT_DIFFICULTY,
        DEFAULT_LOCALE,
        LOCALIZATIONS,
        MAX_DIFFICULTY,
        MIN_PATH_FACTOR,
        RECOMMENDED_MAX_PATH_FACTOR,
    )
    from .webapp_logic import (
        PRESET_BY_KEY,
        PRESETS,
        UiInputs,
        build_download_filename,
        find_matching_preset,
        generate_pdf_bytes,
        locale_display_name,
        locale_menu_label,
        parse_seed,
    )
except ImportError:
    from maze_generator.generate_mazes import (
        DEFAULT_DIFFICULTY,
        DEFAULT_LOCALE,
        LOCALIZATIONS,
        MAX_DIFFICULTY,
        MIN_PATH_FACTOR,
        RECOMMENDED_MAX_PATH_FACTOR,
    )
    from maze_generator.webapp_logic import (
        PRESET_BY_KEY,
        PRESETS,
        UiInputs,
        build_download_filename,
        find_matching_preset,
        generate_pdf_bytes,
        locale_display_name,
        locale_menu_label,
        parse_seed,
    )


def _logo_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "mazerator_logo.svg"


def _icon_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "mazerator_icon.png"


def _example_output_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "example-output.png"


def _inject_styles(st) -> None:
    st.markdown(
        """
        <style>
        .main .block-container {
            max-width: 860px;
            padding-top: 1rem;
            padding-bottom: 2rem;
        }
        [data-testid="stSidebar"] {
            border-right: 1px solid var(--secondary-background-color);
        }
        [data-testid="stSidebar"] > div:first-child {
            background: color-mix(in srgb, var(--background-color) 92%, var(--secondary-background-color) 8%);
        }
        [data-testid="stSidebar"] [data-baseweb="slider"] {
            color: var(--text-color);
        }
        div[data-testid="stForm"] {
            border: 1px solid var(--secondary-background-color);
            border-radius: 16px;
            padding: 0.8rem 1rem 1rem;
            background: var(--background-color);
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
        }
        .mz-guide-shell {
            border: 1px solid var(--secondary-background-color);
            border-radius: 18px;
            padding: 0.75rem 0.8rem 0.85rem;
            background: color-mix(in srgb, var(--background-color) 94%, var(--secondary-background-color) 6%);
            box-shadow: 0 8px 26px rgba(0, 0, 0, 0.06);
        }
        .mz-flow-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 48px minmax(0, 1fr);
            align-items: center;
            gap: 0.65rem;
            margin: 0.35rem 0 0.75rem;
        }
        .mz-flow-arrow {
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0.55;
            font-size: 1.15rem;
        }
        .mz-guide-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.75rem;
            margin: 0.35rem 0 0.7rem;
        }
        .mz-guide-card {
            border: 1px solid var(--secondary-background-color);
            background: color-mix(in srgb, var(--background-color) 92%, var(--secondary-background-color) 8%);
            border-radius: 14px;
            padding: 0.9rem 1rem;
            min-height: 170px;
        }
        .mz-guide-step {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            opacity: 0.78;
            margin-bottom: 0.2rem;
        }
        .mz-guide-title {
            font-size: 0.98rem;
            font-weight: 600;
            margin-bottom: 0.15rem;
        }
        .mz-guide-desc {
            font-size: 1rem;
            line-height: 1.45rem;
            opacity: 0.92;
        }
        .mz-node-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.45rem;
            height: 1.45rem;
            border-radius: 999px;
            margin-right: 0.25rem;
            background: var(--secondary-background-color);
            font-size: 0.9rem;
        }
        .mz-tip-band {
            border: 1px solid var(--secondary-background-color);
            border-radius: 12px;
            padding: 0.6rem 0.75rem;
            margin-top: 0.45rem;
            background: color-mix(in srgb, var(--background-color) 85%, var(--secondary-background-color) 15%);
        }
        .mz-example-title {
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            margin: 0.6rem 0 0.35rem;
        }
        .mz-preset-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.7rem;
            margin: 0.3rem 0 0.4rem;
        }
        .mz-preset-card {
            position: relative;
            border: 1px solid var(--secondary-background-color);
            border-radius: 14px;
            padding: 0.85rem 0.9rem 0.9rem;
            background: color-mix(in srgb, var(--background-color) 92%, var(--secondary-background-color) 8%);
            transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.06s ease;
        }
        .mz-preset-card--active {
            border: 2px solid var(--text-color);
            background: color-mix(in srgb, var(--background-color) 82%, var(--secondary-background-color) 18%);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.10);
        }
        .mz-preset-head {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            margin-bottom: 0.15rem;
        }
        .mz-preset-icon {
            font-size: 1.35rem;
            line-height: 1;
        }
        .mz-preset-name {
            font-size: 1.02rem;
            font-weight: 700;
        }
        .mz-preset-badge {
            margin-left: auto;
            font-size: 0.62rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 0.12rem 0.4rem;
            border-radius: 999px;
            background: var(--text-color);
            color: var(--background-color);
        }
        .mz-preset-age {
            font-size: 0.82rem;
            font-weight: 600;
            opacity: 0.7;
            margin-bottom: 0.3rem;
        }
        .mz-preset-blurb {
            font-size: 0.86rem;
            line-height: 1.25rem;
            opacity: 0.9;
            margin-bottom: 0.5rem;
            min-height: 2.5rem;
        }
        .mz-preset-stats {
            font-size: 0.76rem;
            opacity: 0.72;
            border-top: 1px dashed var(--secondary-background-color);
            padding-top: 0.4rem;
        }
        .mz-preset-hint {
            font-size: 0.82rem;
            opacity: 0.78;
            margin: 0.1rem 0 0.5rem;
        }
        .mz-preset-detail {
            border: 1px solid var(--secondary-background-color);
            border-left: 5px solid var(--text-color);
            border-radius: 10px;
            padding: 0.5rem 0.6rem;
            margin: 0.4rem 0 0.2rem;
            font-size: 0.86rem;
            line-height: 1.25rem;
            background: color-mix(in srgb, var(--background-color) 86%, var(--secondary-background-color) 14%);
        }
        .mz-preset-detail--custom {
            border-left-color: color-mix(in srgb, var(--text-color) 45%, var(--secondary-background-color) 55%);
        }
        .mz-preset-detail-blurb {
            opacity: 0.82;
        }
        .mz-preset-detail-stats {
            font-size: 0.76rem;
            opacity: 0.7;
        }
        .mz-soft-warn {
            font-size: 0.74rem;
            line-height: 1.05rem;
            margin: -0.1rem 0 0.4rem;
            padding: 0.32rem 0.5rem;
            border: 1px solid #e6c200;
            border-left: 4px solid #e6c200;
            border-radius: 8px;
            background: rgba(255, 214, 0, 0.12);
            color: color-mix(in srgb, var(--text-color) 88%, #7a5b00 12%);
        }
        section[data-testid="stSidebar"] div[data-testid="stButtonGroup"] {
            width: 100%;
        }
        section[data-testid="stSidebar"] div[data-testid="stButtonGroup"] > div {
            flex: 1 1 0;
        }
        .mz-context-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.45rem;
            margin-top: 0.45rem;
        }
        .mz-context-pill {
            border: 1px solid var(--secondary-background-color);
            border-radius: 10px;
            padding: 0.42rem 0.5rem;
            background: color-mix(in srgb, var(--background-color) 92%, var(--secondary-background-color) 8%);
        }
        .mz-context-k {
            font-size: 0.72rem;
            opacity: 0.72;
            margin-bottom: 0.1rem;
        }
        .mz-context-v {
            font-size: 0.92rem;
            font-weight: 600;
        }
        .mz-note,
        .mz-ready {
            border: 1px solid var(--secondary-background-color);
            border-radius: 12px;
            padding: 0.62rem 0.75rem;
            background: color-mix(in srgb, var(--background-color) 90%, var(--secondary-background-color) 10%);
            margin-top: 0.55rem;
            margin-bottom: 0.4rem;
            font-size: 0.94rem;
        }
        .mz-note {
            border: 2px solid color-mix(in srgb, var(--text-color) 25%, var(--secondary-background-color) 75%);
            border-left: 6px solid var(--text-color);
            background: color-mix(in srgb, var(--background-color) 80%, var(--secondary-background-color) 20%);
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
        }
        .mz-ready {
            font-weight: 600;
            border: 2px solid #2f7d32;
            border-left: 7px solid #2f7d32;
            background: #eaf7ea;
            color: #16421b;
            box-shadow: 0 8px 18px rgba(47, 125, 50, 0.16);
            font-size: 1rem;
        }
        div[data-testid="stDownloadButton"] {
            margin-top: 0.5rem;
        }
        div[data-testid="stDownloadButton"] > button {
            width: 100%;
            min-height: 3.6rem;
            border-radius: 14px;
            border: 2px solid #2f7d32;
            background: #2f7d32;
            color: #ffffff;
            box-shadow: 0 10px 26px rgba(47, 125, 50, 0.30);
            transition: transform 0.06s ease, box-shadow 0.15s ease, background 0.15s ease;
        }
        div[data-testid="stDownloadButton"] > button p,
        div[data-testid="stDownloadButton"] > button div {
            font-size: 1.18rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            color: #ffffff;
        }
        div[data-testid="stDownloadButton"] > button:hover {
            background: #276a2a;
            border-color: #276a2a;
            box-shadow: 0 12px 30px rgba(47, 125, 50, 0.38);
        }
        div[data-testid="stDownloadButton"] > button:hover p,
        div[data-testid="stDownloadButton"] > button:hover div {
            color: #ffffff;
        }
        div[data-testid="stDownloadButton"] > button:active {
            transform: translateY(1px);
        }
        @media (max-width: 640px) {
            div[data-testid="stDownloadButton"] > button {
                min-height: 4rem;
            }
            div[data-testid="stDownloadButton"] > button p,
            div[data-testid="stDownloadButton"] > button div {
                font-size: 1.28rem;
            }
            .main .block-container {
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }
            div[data-testid="stForm"] {
                border-radius: 12px;
                padding: 0.7rem 0.8rem 0.9rem;
            }
            .mz-guide-grid {
                grid-template-columns: 1fr;
            }
            .mz-flow-row {
                grid-template-columns: 1fr;
                gap: 0.5rem;
            }
            .mz-flow-arrow {
                transform: rotate(90deg);
                height: 18px;
            }
            .mz-context-grid {
                grid-template-columns: 1fr 1fr;
            }
            .mz-preset-grid {
                grid-template-columns: 1fr;
            }
            .mz-preset-blurb {
                min-height: 0;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header(st) -> None:
    logo = _logo_path()
    if logo.exists():
        _, col_logo, _ = st.columns([1, 2.6, 1])
        with col_logo:
            st.image(str(logo), width=420)


def _render_guidelines(st, current_inputs: UiInputs) -> None:
    st.subheader("How to Use")
    st.markdown(
        f"""
        <div class="mz-guide-shell">
        <div class="mz-flow-row">
          <div class="mz-guide-card">
            <div class="mz-guide-step">1 · Configure</div>
            <div class="mz-guide-title">Configure in the left panel</div>
            <div class="mz-guide-desc"><span class="mz-node-icon">🎛️</span>Set pages, difficulty, language, and optional seed.</div>
          </div>
          <div class="mz-flow-arrow">➜</div>
          <div class="mz-guide-card">
            <div class="mz-guide-step">2 · Generate</div>
            <div class="mz-guide-title">Generate and download</div>
            <div class="mz-guide-desc"><span class="mz-node-icon">📄</span>Click <strong>Generate PDF</strong>, then download instantly.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    example = _example_output_path()
    if example.exists():
        st.markdown(
            '<div class="mz-example-title">Example Output</div>',
            unsafe_allow_html=True,
        )
        st.image(str(example), width="stretch")
    active_key = find_matching_preset(
        current_inputs.pages,
        current_inputs.difficulty,
        current_inputs.min_path_factor,
    )
    cards = []
    for preset in PRESETS:
        is_active = preset.key == active_key
        active_cls = " mz-preset-card--active" if is_active else ""
        badge = '<span class="mz-preset-badge">Selected</span>' if is_active else ""
        cards.append(
            f'<div class="mz-preset-card{active_cls}">'
            f'<div class="mz-preset-head">'
            f'<span class="mz-preset-icon">{preset.icon}</span>'
            f'<span class="mz-preset-name">{preset.label}</span>{badge}'
            f"</div>"
            f'<div class="mz-preset-age">{preset.age}</div>'
            f'<div class="mz-preset-blurb">{preset.blurb}</div>'
            f'<div class="mz-preset-stats">{preset.pages} pages · '
            f"difficulty {preset.difficulty:.1f} · path {preset.min_path_factor:.2f}</div>"
            f"</div>"
        )
    st.subheader("Difficulty presets")
    st.markdown(
        f'<div class="mz-preset-grid">{"".join(cards)}</div>'
        '<div class="mz-preset-hint">Apply one from the <strong>Quick start</strong> '
        "selector in the left panel, then fine-tune any control for a custom set.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="mz-tip-band">
          <strong>Current configuration preview</strong>
          <div class="mz-context-grid">
            <div class="mz-context-pill"><div class="mz-context-k">Pages</div><div class="mz-context-v">{current_inputs.pages}</div></div>
            <div class="mz-context-pill"><div class="mz-context-k">Difficulty</div><div class="mz-context-v">{current_inputs.difficulty:.1f}</div></div>
            <div class="mz-context-pill"><div class="mz-context-k">Path factor</div><div class="mz-context-v">{current_inputs.min_path_factor:.2f}</div></div>
            <div class="mz-context-pill"><div class="mz-context-k">Language</div><div class="mz-context-v">{locale_display_name(current_inputs.locale)}</div></div>
            <div class="mz-context-pill"><div class="mz-context-k">Seed mode</div><div class="mz-context-v">{"Random" if current_inputs.seed is None else "Fixed"}</div></div>
            <div class="mz-context-pill"><div class="mz-context-k">File prefix</div><div class="mz-context-v">{current_inputs.output_stem}</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_note(st, text: str) -> None:
    st.markdown(f'<div class="mz-note">{text}</div>', unsafe_allow_html=True)


def _render_ready(st, text: str) -> None:
    st.markdown(f'<div class="mz-ready">{text}</div>', unsafe_allow_html=True)


def _collapse_sidebar_on_mobile_after_submit(st, nonce) -> None:
    """On small screens, close the sidebar after submission.

    `nonce` is embedded in the injected HTML so Streamlit treats each call as a
    distinct component and re-runs the script on every generation (identical
    HTML would otherwise be cached and never execute again).
    """
    components = importlib.import_module("streamlit.components.v1")
    script = """
        <script>
        (function () {
          // Unique per run so the iframe reloads and this script re-executes: __NONCE__
          const doc = window.parent.document;
          const win = window.parent;
          const isMobile = win.innerWidth <= 768
            || win.matchMedia("(max-width: 768px)").matches;
          if (!isMobile) return;

          function sidebar() {
            return doc.querySelector('section[data-testid="stSidebar"]');
          }
          function isExpanded() {
            const sb = sidebar();
            if (!sb) return false;
            const aria = sb.getAttribute("aria-expanded");
            if (aria !== null) return aria === "true";
            return sb.getBoundingClientRect().width > 5;
          }
          function collapseButton() {
            return (
              doc.querySelector('[data-testid="stSidebarCollapseButton"] button') ||
              doc.querySelector('[data-testid="stSidebarCollapseButton"]') ||
              doc.querySelector('[data-testid="stSidebarHeader"] button') ||
              doc.querySelector('button[aria-label="Close sidebar"]') ||
              doc.querySelector('button[aria-label*="Close sidebar"]') ||
              doc.querySelector('button[aria-label*="collapse" i]') ||
              doc.querySelector('section[data-testid="stSidebar"] button[kind="header"]')
            );
          }

          let attempts = 0;
          const maxAttempts = 50; // ~4s at 80ms
          const timer = setInterval(function () {
            attempts += 1;
            if (!isExpanded()) { clearInterval(timer); return; }
            const btn = collapseButton();
            if (btn) { btn.click(); }
            if (attempts >= maxAttempts) { clearInterval(timer); }
          }, 80);
        })();
        </script>
    """.replace("__NONCE__", str(nonce))
    components.html(script, height=0)


def _focus_download_area_on_mobile(st, nonce) -> None:
    """On small screens, bring the download call-to-action into view."""
    components = importlib.import_module("streamlit.components.v1")
    script = """
        <script>
        (function () {
          // Unique per run so the script re-executes each generation: __NONCE__
          const win = window.parent;
          const isMobile = win.innerWidth <= 768
            || win.matchMedia("(max-width: 768px)").matches;
          if (!isMobile) return;
          const parentDoc = win.document;

          let attempts = 0;
          const maxAttempts = 50; // ~4s
          const timer = setInterval(function () {
            attempts += 1;
            const target =
              parentDoc.querySelector("#mz-download-anchor") ||
              parentDoc.querySelector('[data-testid="stDownloadButton"]') ||
              parentDoc.querySelector('button[kind="secondaryFormSubmit"]');
            if (target) {
              target.scrollIntoView({ behavior: "smooth", block: "center" });
              clearInterval(timer);
              return;
            }
            if (attempts >= maxAttempts) {
              clearInterval(timer);
            }
          }, 80);
        })();
        </script>
    """.replace("__NONCE__", str(nonce))
    components.html(script, height=0)


def _apply_preset(st) -> None:
    """Callback: push the chosen preset's values into the control widgets."""
    key = st.session_state.get("preset_choice")
    if not key:
        return
    preset = PRESET_BY_KEY[key]
    st.session_state["cfg_pages"] = int(preset.pages)
    st.session_state["cfg_difficulty"] = float(preset.difficulty)
    st.session_state["cfg_min_path"] = float(preset.min_path_factor)


def _render_preset_selector(st) -> None:
    st.subheader("Quick start")
    st.caption("Pick an age-based preset, then fine-tune below if you like.")

    # Keep the highlighted preset honest: if the live values no longer match the
    # selected preset (user fine-tuned a control), clear the selection.
    current_match = find_matching_preset(
        st.session_state.get("cfg_pages", 20),
        st.session_state.get("cfg_difficulty", float(DEFAULT_DIFFICULTY)),
        st.session_state.get("cfg_min_path", float(MIN_PATH_FACTOR)),
    )
    if current_match is None and st.session_state.get("preset_choice") is not None:
        st.session_state["preset_choice"] = None

    st.segmented_control(
        "Age-based preset",
        options=[p.key for p in PRESETS],
        format_func=lambda k: f"{PRESET_BY_KEY[k].icon} {PRESET_BY_KEY[k].label}",
        selection_mode="single",
        key="preset_choice",
        on_change=_apply_preset,
        args=(st,),
        label_visibility="collapsed",
    )

    if current_match is not None:
        preset = PRESET_BY_KEY[current_match]
        st.markdown(
            f'<div class="mz-preset-detail">{preset.icon} <strong>{preset.label}</strong>'
            f' · {preset.age}<br><span class="mz-preset-detail-blurb">{preset.blurb}</span>'
            f'<br><span class="mz-preset-detail-stats">{preset.pages} pages · '
            f"difficulty {preset.difficulty:.1f} · path {preset.min_path_factor:.2f}</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="mz-preset-detail mz-preset-detail--custom">'
            "✏️ <strong>Custom</strong><br>"
            '<span class="mz-preset-detail-blurb">Your own fine-tuned settings.</span></div>',
            unsafe_allow_html=True,
        )


_CONTROL_DEFAULTS = {
    "cfg_pages": 20,
    "cfg_difficulty": float(DEFAULT_DIFFICULTY),
    "cfg_min_path": float(MIN_PATH_FACTOR),
    "cfg_locale": DEFAULT_LOCALE,
    "cfg_seed_text": "",
    "cfg_output_stem": "mazerator",
}


def _reset_controls(st) -> None:
    """Callback: restore every control to its default value."""
    for key, value in _CONTROL_DEFAULTS.items():
        st.session_state[key] = value
    st.session_state["preset_choice"] = None


def _render_sidebar_controls(st) -> tuple[bool, UiInputs | None]:
    # Seed widget state once so controls can be driven purely via session_state
    # (no `value=`/`index=`), which keeps presets/reset clean and warning-free.
    for key, value in _CONTROL_DEFAULTS.items():
        st.session_state.setdefault(key, value)

    with st.sidebar:
        _render_preset_selector(st)
        st.header("Configuration")
        st.button(
            "Reset to defaults",
            width="stretch",
            on_click=_reset_controls,
            args=(st,),
        )
        pages = st.slider("Pages", min_value=1, max_value=60, step=1, key="cfg_pages")
        difficulty = st.slider(
            "Difficulty",
            min_value=1.0,
            max_value=float(MAX_DIFFICULTY),
            step=0.1,
            help="Higher values increase average maze size.",
            key="cfg_difficulty",
        )
        min_path_factor = st.slider(
            "Minimum Path Factor",
            min_value=0.1,
            max_value=1.0,
            step=0.05,
            help=(
                "Higher values force longer solutions. Recommended "
                f"<= {RECOMMENDED_MAX_PATH_FACTOR:g}: above this, generation is much "
                "slower and the target complexity may not be reachable."
            ),
            key="cfg_min_path",
        )
        if min_path_factor > RECOMMENDED_MAX_PATH_FACTOR:
            st.markdown(
                f'<div class="mz-soft-warn">⚠️ Above {RECOMMENDED_MAX_PATH_FACTOR:g}: '
                "slower and may not be fully achievable.</div>",
                unsafe_allow_html=True,
            )
        locale = st.selectbox(
            "Locale",
            options=sorted(LOCALIZATIONS),
            format_func=locale_menu_label,
            key="cfg_locale",
        )
        seed_text = st.text_input(
            "Seed (optional)",
            placeholder="Leave empty for random output",
            help="Use an integer for reproducible, byte-identical PDFs.",
            key="cfg_seed_text",
        )
        output_stem = st.text_input(
            "Downloaded file name prefix",
            help="The app appends locale/pages/seed metadata automatically.",
            key="cfg_output_stem",
        )
        submitted = st.button("Generate PDF", width="stretch", type="primary")

        try:
            seed = parse_seed(seed_text)
        except ValueError as exc:
            st.error(str(exc))
            return submitted, None

        return submitted, UiInputs(
            pages=pages,
            difficulty=difficulty,
            min_path_factor=min_path_factor,
            locale=locale,
            seed=seed,
            output_stem=output_stem,
        )


def main() -> None:
    try:
        st = importlib.import_module("streamlit")
    except ImportError as exc:
        raise SystemExit(
            "streamlit is required for the web app. Install dependencies with "
            "'pip install -e .' and run 'mazerator-web'."
        ) from exc

    icon = _icon_path()
    st.set_page_config(
        page_title="Mazerator",
        page_icon=str(icon) if icon.exists() else "🧩",
        layout="centered",
    )
    _inject_styles(st)
    _render_header(st)
    submitted, inputs = _render_sidebar_controls(st)
    if inputs is not None:
        _render_guidelines(st, inputs)

    if not submitted or inputs is None:
        _render_note(st, "Set options in the left panel, then click <strong>Generate PDF</strong>.")
        return

    st.session_state["_gen_count"] = st.session_state.get("_gen_count", 0) + 1
    _collapse_sidebar_on_mobile_after_submit(st, st.session_state["_gen_count"])

    with st.spinner("Generating your PDF..."):
        try:
            pdf_bytes, seed_used, sizes = generate_pdf_bytes(inputs)
        except ValueError as exc:
            st.error(str(exc))
            return
        except SystemExit as exc:
            st.error(str(exc))
            return

    download_name = build_download_filename(inputs, seed_used=seed_used)
    _render_ready(st, "PDF ready.")
    st.markdown('<div id="mz-download-anchor"></div>', unsafe_allow_html=True)
    st.download_button(
        "⬇  Download PDF",
        data=pdf_bytes,
        file_name=download_name,
        mime="application/pdf",
        width="stretch",
        type="primary",
    )
    _focus_download_area_on_mobile(st, st.session_state["_gen_count"])

    st.caption(
        f"Seed used: `{seed_used}` | Grid range: `{sizes[0]}x{sizes[0]} -> {sizes[-1]}x{sizes[-1]}`"
    )


if __name__ == "__main__":
    main()

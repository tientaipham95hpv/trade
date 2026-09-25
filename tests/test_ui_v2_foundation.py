"""Test suite for Obsidian Quants UI V2 Web Design Foundation."""
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]
UI_V2_DIR = ROOT / "web" / "static" / "ui_v2"
PREVIEW_TEMPLATE = ROOT / "web" / "templates" / "ui_v2_preview.html"


def test_ui_v2_files_exist():
    assert UI_V2_DIR.is_dir(), "web/static/ui_v2 directory must exist"
    required_files = [
        "tokens.css",
        "base.css",
        "layout.css",
        "components.css",
        "responsive.css",
        "obsidian_quants.css",
    ]
    for filename in required_files:
        path = UI_V2_DIR / filename
        assert path.is_file(), f"Missing required stylesheet: {filename}"
        assert path.stat().st_size > 0, f"Stylesheet must not be empty: {filename}"


def test_canonical_color_tokens():
    tokens_path = UI_V2_DIR / "tokens.css"
    content = tokens_path.read_text(encoding="utf-8")

    expected_tokens = {
        "--bg": ["#051424", "#070B12"],
        "--surface-lowest": ["#010F1F", "#070B12"],
        "--surface-low": ["#0D1C2D", "#0D111A"],
        "--surface": ["#122131", "#0D111A"],
        "--surface-high": ["#1C2B3C", "#121824"],
        "--surface-highest": ["#273647", "#171E2B"],
        "--border": ["#1C2E42", "#202938"],
        "--border-active": ["#334155"],
        "--gold": ["#F0B90B", "#F3BA2F"],
        "--cyan": ["#00F0FF", "#3DD9EB"],
        "--green": ["#0ECB81", "#18C784"],
        "--red": ["#F6465D", "#F0445E"],
        "--purple": ["#A855F7"],
        "--text-primary": ["#D4E4FA", "#E8EDF5"],
        "--text-secondary": ["#B9CACB", "#95A1B2"],
        "--text-muted": ["#849495", "#5E6A7D"],
    }

    for token, hex_vals in expected_tokens.items():
        found = False
        for hex_val in hex_vals:
            pattern = rf"{re.escape(token)}\s*:\s*{re.escape(hex_val)}"
            if re.search(pattern, content, re.IGNORECASE):
                found = True
                break
        assert found, f"Missing or incorrect token: {token} -> expected one of {hex_vals}"

    # Semantic aliases
    for alias in ["--status-healthy", "--status-warning", "--status-critical", "--status-offline"]:
        assert alias in content, f"Missing semantic alias: {alias}"


def test_no_runtime_cdn_in_ui_v2():
    """Verify that the UI V2 asset foundation has zero runtime external CDN links."""
    cdn_patterns = [
        "cdn.tailwindcss.com",
        "cdnjs.cloudflare.com",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "cdn.jsdelivr.net",
        "unpkg.com",
    ]

    for css_file in UI_V2_DIR.glob("*.css"):
        content = css_file.read_text(encoding="utf-8")
        for cdn in cdn_patterns:
            assert cdn not in content, f"Forbidden CDN found in {css_file.name}: {cdn}"

    # Preview template should also avoid runtime CDNs
    if PREVIEW_TEMPLATE.is_file():
        preview_content = PREVIEW_TEMPLATE.read_text(encoding="utf-8")
        for cdn in cdn_patterns:
            assert cdn not in preview_content, f"Forbidden CDN found in preview template: {cdn}"


def test_required_component_classes():
    components_path = UI_V2_DIR / "components.css"
    content = components_path.read_text(encoding="utf-8")

    required_classes = [
        ".terminal-panel",
        ".metric-card",
        ".telemetry-item",
        ".env-badge",
        ".status-badge",
        ".dense-table",
        ".risk-alert",
        ".empty-state",
        ".skeleton",
        ".confirm-dialog-backdrop",
        ".section-header",
    ]

    for cls in required_classes:
        assert cls in content, f"Missing required component class: {cls}"


def test_numeric_tabular_features():
    base_path = UI_V2_DIR / "base.css"
    content = base_path.read_text(encoding="utf-8")
    tokens_path = UI_V2_DIR / "tokens.css"
    tokens_content = tokens_path.read_text(encoding="utf-8")

    combined = base_path.name + content + tokens_path.name + tokens_content
    assert '"tnum" 1' in combined, 'Must specify font-feature-settings with "tnum" 1'
    assert '"zero" 1' in combined, 'Must specify font-feature-settings with "zero" 1'


def test_responsive_breakpoints():
    resp_path = UI_V2_DIR / "responsive.css"
    content = resp_path.read_text(encoding="utf-8")

    assert "1440px" in content, "Must declare >= 1440px desktop breakpoint"
    assert "1024px" in content, "Must declare tablet breakpoint around 1024px"
    assert "640px" in content, "Must declare compact mobile breakpoint"


def test_no_forbidden_surfaces_in_ui_v2():
    """Verify that UI V2 code introduces zero forbidden credential or active trading surfaces."""
    forbidden_terms = [
        "Binance API Key",
        "Binance Secret",
        "Enable Copy Trade",
        "Manual Buy",
        "Manual Sell",
        "Enable Live Trading",
        "Switch to LIVE",
    ]

    for file_path in list(UI_V2_DIR.glob("*.css")) + [PREVIEW_TEMPLATE]:
        if not file_path.is_file():
            continue
        content = file_path.read_text(encoding="utf-8")
        for term in forbidden_terms:
            assert term.lower() not in content.lower(), f"Forbidden active control text in {file_path.name}: {term}"

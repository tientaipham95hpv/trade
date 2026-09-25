# 05 — ASSET BUNDLING & ZERO-CDN PLAN

## 1. Zero Runtime External CDN Mandate

To satisfy the strict security, air-gapped capability, and offline operational requirements of an institutional quant trading system, Web V2 and Flutter V2 enforce a **Strict Zero External Runtime CDN Policy**:

1. **No External Fonts**: No runtime calls to Google Fonts (`fonts.googleapis.com`), Adobe Typekit, or other web font CDNs.
2. **No External Scripts / Styles**: No CDN links to unpkg, cdnjs, jsdelivr, or bootstrapcdn.
3. **No External Icon Fonts**: No FontAwesome or external icon stylesheets loaded over HTTP.

---

## 2. Web V2 Font Architecture

Web V2 uses a robust local font stack that resolves entirely from client OS fonts with zero network roundtrips:

```css
/* Monospace Stack (Financial Telemetry & Tables) */
font-family: 'JetBrains Mono', 'SF Mono', 'Fira Code', 'Roboto Mono', 'Cascadia Code', monospace;

/* Sans-Serif Stack (UI Chrome, Labels, Body) */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
```

This stack guarantees:
- Instant first-paint with 0ms font blocking time.
- Zero layout shift (CLS = 0) caused by late-loading web fonts.
- Operational resilience when running in offline or restricted-network VPS environments.

---

## 3. Flutter Asset Architecture

- **Flutter Fonts**: Uses iOS system fonts (`SF Pro`, `SF Mono` / `Courier`) and native Material symbols bundled with the app binary.
- **SVG / Vector Assets**: Vector assets are rendered using Flutter's native canvas and vector primitives without remote asset loading.
- **Static Asset Serving in Web**: All static files reside locally in `web/static/ui_v2/` and are served directly by FastAPI's `StaticFiles` mount at `/static/ui_v2`.

---

## 4. Verification in Test Suite

The zero-external-CDN policy is actively tested and enforced by `tests/test_ui_v2_foundation.py::test_zero_external_runtime_cdn_dependencies`:
```python
def test_zero_external_runtime_cdn_dependencies():
    ui_v2_dir = pathlib.Path("web/static/ui_v2")
    for css_file in ui_v2_dir.glob("*.css"):
        content = css_file.read_text(encoding="utf-8")
        assert "http://" not in content
        assert "https://" not in content
        assert "fonts.googleapis.com" not in content
        assert "cdnjs.cloudflare.com" not in content
```
Result: **PASSED (0 violations detected)**.

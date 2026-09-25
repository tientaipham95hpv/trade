"""Comprehensive Test Suite for Web V2 — Obsidian Quants Operator Terminal.

Validates route authorization, template rendering, zero-CDN policy, prohibited surfaces absence,
fail-closed error handling, security headers, and view models.
"""

import os
import pathlib
import time
import pytest
from fastapi.testclient import TestClient
from web.app import app, _active_sessions
from web.view_models import build_terminal_view_model

UI_V2_TEMPLATES_DIR = pathlib.Path("web/templates/ui_v2")
UI_V2_STATIC_DIR = pathlib.Path("web/static/ui_v2")


@pytest.fixture
def client():
    """Return a fresh TestClient instance without residual session cookies."""
    return TestClient(app)


@pytest.fixture
def authenticated_session():
    """Create a temporary authenticated admin session in _active_sessions."""
    test_token = f"test_admin_session_token_{int(time.time())}"
    from database.connection import get_db_session
    from database.models import Client
    with get_db_session() as db:
        admin = db.query(Client).filter(Client.role == "admin", Client.is_active == True).first()
        if not admin:
            # Fallback to any active client elevated for testing
            admin = db.query(Client).filter(Client.is_active == True).first()
        admin_id = admin.id
        username = admin.username
        role = admin.role
        password_hash = admin.password_hash

    _active_sessions[test_token] = {
        "client_id": admin_id,
        "username": username,
        "role": role,
        "password_hash": password_hash,
        "expires_at": time.time() + 3600,
    }
    yield test_token
    _active_sessions.pop(test_token, None)


def test_anonymous_v2_terminal_redirects_to_login(client):
    """Anonymous requests to /portal/dashboard-v2 must be denied and redirected."""
    resp = client.get("/portal/dashboard-v2", follow_redirects=False)
    assert resp.status_code == 302
    assert "/portal/login" in resp.headers.get("location", "")


def test_authenticated_v2_terminal_access(client, authenticated_session):
    """Authenticated requests to /portal/dashboard-v2 must return 200 with V2 terminal shell."""
    client.cookies.set("session_token", authenticated_session)
    resp = client.get("/portal/dashboard-v2")
    assert resp.status_code == 200
    assert "terminal-shell" in resp.text
    assert "BINANCE QUANT PRO" in resp.text
    assert "top-telemetry-bar" in resp.text


def test_preview_route_protected_against_anonymous_leak(client):
    """The preview route /portal/ui_v2_preview must require authentication and not leak data."""
    import web.app
    web.app.UI_V2_DEV_PREVIEW_ENABLED = False

    resp = client.get("/portal/ui_v2_preview", follow_redirects=False)
    assert resp.status_code == 302
    assert "/portal/login" in resp.headers.get("location", "")


def test_preview_route_accessible_when_authenticated(client, authenticated_session):
    """When authenticated, /portal/ui_v2_preview serves the preview template."""
    client.cookies.set("session_token", authenticated_session)
    resp = client.get("/portal/ui_v2_preview")
    assert resp.status_code == 200
    assert "Obsidian Quants" in resp.text or "UI V2" in resp.text


def test_v2_navigation_contains_only_allowed_sections(client, authenticated_session):
    """V2 navigation must contain OVERVIEW, POSITIONS, RISK, ACTIVITY, SYSTEM and no obsolete links."""
    client.cookies.set("session_token", authenticated_session)
    resp = client.get("/portal/dashboard-v2")
    assert resp.status_code == 200
    content = resp.text

    # Allowed sections
    assert "data-tab=\"overview\"" in content
    assert "data-tab=\"positions\"" in content
    assert "data-tab=\"risk\"" in content
    assert "data-tab=\"activity\"" in content
    assert "data-tab=\"system\"" in content

    # Forbidden navigation sections
    assert "api-settings" not in content.lower()
    assert "copy-trade" not in content.lower()
    assert "ai-copilot" not in content.lower()
    assert "scanner-control" not in content.lower()


def test_zero_runtime_cdn_in_ui_v2_templates():
    """UI V2 templates must not reference external runtime CDNs."""
    forbidden_cdns = [
        "cdn.tailwindcss.com",
        "cdnjs.cloudflare.com",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "cdn.jsdelivr.net",
        "unpkg.com",
    ]
    for tmpl in UI_V2_TEMPLATES_DIR.rglob("*.html"):
        text = tmpl.read_text(encoding="utf-8")
        for cdn in forbidden_cdns:
            assert cdn not in text, f"Forbidden CDN '{cdn}' found in {tmpl}"


def test_no_forbidden_surfaces_in_v2_templates():
    """Verify templates contain zero Binance API Key/Secret inputs or active manual trading buttons."""
    forbidden_terms = [
        "name=\"api_key\"",
        "name=\"api_secret\"",
        "name=\"secret_key\"",
        "type=\"password\" id=\"api_secret\"",
        ">Enable Copy Trade<",
        ">Open Trade<",
        ">Manual Buy<",
        ">Manual Sell<",
    ]
    for tmpl in UI_V2_TEMPLATES_DIR.rglob("*.html"):
        text = tmpl.read_text(encoding="utf-8")
        for term in forbidden_terms:
            assert term.lower() not in text.lower(), f"Forbidden surface term '{term}' in {tmpl}"


def test_feature_flag_routes_behavior(client):
    """Test routing when UI_V2_ENABLED is True vs False."""
    # Test when UI_V2_ENABLED = False
    os.environ["UI_V2_ENABLED"] = "false"
    resp_landing_legacy = client.get("/")
    assert resp_landing_legacy.status_code == 200

    resp_terms_legacy = client.get("/terms")
    assert resp_terms_legacy.status_code == 200

    # Test when UI_V2_ENABLED = True
    os.environ["UI_V2_ENABLED"] = "true"
    resp_landing_v2 = client.get("/")
    assert resp_landing_v2.status_code == 200
    assert "INSTITUTIONAL QUANT SYSTEM V2" in resp_landing_v2.text or "Institutional Quant Trading" in resp_landing_v2.text

    resp_terms_v2 = client.get("/terms")
    assert resp_terms_v2.status_code == 200
    assert "TERMS OF SERVICE" in resp_terms_v2.text

    # Revert flag to False (safe baseline default)
    os.environ["UI_V2_ENABLED"] = "false"


def test_security_headers_present(client):
    """Ensure institutional security headers remain active on V2 endpoints."""
    resp = client.get("/portal/login-v2")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in resp.headers


def test_production_health_and_ready_unaffected(client):
    """Verify /health and /ready continue returning existing contracts."""
    h_resp = client.get("/health")
    assert h_resp.status_code == 200
    assert h_resp.json().get("status") in ("ok", "HEALTHY", "HALTED", "DEGRADED", "UNKNOWN", "OFFLINE")

    r_resp = client.get("/ready")
    assert r_resp.status_code in (200, 503)


def test_feature_disabled_credential_api_remains_fail_closed(client, authenticated_session):
    """Old credential endpoints must remain fail-closed with FEATURE_DISABLED (HTTP 503)."""
    client.cookies.set("session_token", authenticated_session)
    resp = client.post("/portal/api-settings")
    assert resp.status_code == 503
    data = resp.json()
    assert data.get("state") == "DISABLED"
    assert data.get("code") == "FEATURE_DISABLED"


def test_terminal_view_model_builder():
    """Verify build_terminal_view_model formats data cleanly with fail-closed null defaults."""
    vm = build_terminal_view_model(
        status_data={"status": "HEALTHY", "is_paused": False, "halt_generation": 4, "realized_pnl": 125.50},
        positions_data={"BTCUSDT": {"side": "LONG", "qty": 0.5}},
        environment="OFFLINE",
    )
    assert vm["environment"] == "OFFLINE"
    assert vm["services"]["execution"] == "HEALTHY"
    assert vm["halt"]["active"] is False
    assert vm["halt"]["generation"] == 4
    assert vm["pnl"]["realized_pnl"] == 125.50
    assert vm["pnl"]["win_rate"] is None  # Unproven, strictly None
    assert vm["pnl"]["trade_count"] is None
    assert len(vm["positions"]) == 1
    assert vm["positions"][0]["symbol"] == "BTCUSDT"
    assert vm["certification"]["execution_core"] == "OFFLINE EXECUTION CORE ACCEPTED"

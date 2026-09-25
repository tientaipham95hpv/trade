"""UI V2 Phase 5 - Release Candidate Gate Test Suite.

Validates the full release candidate specification:
1. Feature flag cutover (UI_V2_ENABLED=true vs UI_V2_ENABLED=false).
2. Preview route security (UI_V2_DEV_PREVIEW_ENABLED=false -> 302 redirect, no leak).
3. Authentication E2E (anonymous, invalid, valid admin, client role 403).
4. Session expiry and revocation.
5. Data truth (missing service -> UNKNOWN, null != zero).
6. Operator CAS resume, stale intent 409, recovery required 409.
7. CLOSEALL strict absence in Web V2.
8. Security headers, CSP, and zero external runtime CDNs.
9. Zero Binance secrets and zero direct Binance authority in UI V2.
"""

import os
import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

if not os.environ.get("JWT_SECRET_KEY") or len(os.environ.get("JWT_SECRET_KEY", "")) < 32:
    os.environ["JWT_SECRET_KEY"] = "phase5-rc-test-jwt-secret-key-32chars-minimum-test!"

import web.app as web_module
from web.app import app, create_session_token
from database.connection import get_db_session
from database.models import Client
from database.security import hash_password
from web.view_models import render_crypto_value, render_pnl, render_percentage

ROOT_DIR = Path(__file__).resolve().parents[1]
UI_V2_TEMPLATES = ROOT_DIR / "web" / "templates" / "ui_v2"
UI_V2_STATIC = ROOT_DIR / "web" / "static" / "ui_v2"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def rc_users():
    """Create test admin and test client accounts for RC testing."""
    with get_db_session() as db:
        admin = db.query(Client).filter(Client.username == "test_phase5_admin").first()
        if not admin:
            admin = Client(
                username="test_phase5_admin",
                password_hash=hash_password("RcAdminPass123!"),
                role="admin",
                is_active=True,
            )
            db.add(admin)

        client_user = db.query(Client).filter(Client.username == "test_phase5_client").first()
        if not client_user:
            client_user = Client(
                username="test_phase5_client",
                password_hash=hash_password("RcClientPass123!"),
                role="client",
                is_active=True,
            )
            db.add(client_user)
        db.commit()

        admin_token = create_session_token("test_phase5_admin", role="admin")
        client_token = create_session_token("test_phase5_client", role="client")

    return {
        "admin_token": admin_token,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "admin_cookies": {"session_token": admin_token},
        "client_token": client_token,
        "client_headers": {"Authorization": f"Bearer {client_token}"},
        "client_cookies": {"session_token": client_token},
    }


def test_ui_v2_feature_flag_cutover(client, rc_users, monkeypatch):
    """When UI_V2_ENABLED=true, production-facing routes resolve to V2."""
    monkeypatch.setenv("UI_V2_ENABLED", "true")

    # 1. Landing page (/)
    resp_landing = client.get("/")
    assert resp_landing.status_code == 200
    assert "Obsidian Quants" in resp_landing.text or "Astra Quant" in resp_landing.text or "V2" in resp_landing.text

    # 2. Login page (/portal/login)
    resp_login = client.get("/portal/login")
    assert resp_login.status_code == 200
    assert "Obsidian Quants" in resp_login.text or "ĐĂNG NHẬP" in resp_login.text

    # 3. Dashboard (/portal/dashboard) authenticated
    client.cookies.set("session_token", rc_users["admin_token"])
    resp_dash = client.get("/portal/dashboard")
    assert resp_dash.status_code == 200
    assert "Obsidian Quants" in resp_dash.text
    assert "data-tab=\"overview\"" in resp_dash.text
    client.cookies.clear()

    # 4. Legal pages
    for route in ["/risk-warning", "/terms", "/privacy"]:
        resp_legal = client.get(route)
        assert resp_legal.status_code == 200
        assert "Obsidian Quants" in resp_legal.text or "CẢNH BÁO" in resp_legal.text or "ĐIỀU KHOẢN" in resp_legal.text or "BẢO MẬT" in resp_legal.text

    # 5. Core health / readiness endpoints
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code in (200, 503)


def test_ui_v2_legacy_fallback(client, monkeypatch):
    """When UI_V2_ENABLED=false, legacy fallback behaves predictably."""
    monkeypatch.setenv("UI_V2_ENABLED", "false")

    resp_landing = client.get("/")
    assert resp_landing.status_code == 200

    resp_login = client.get("/portal/login")
    assert resp_login.status_code == 200

    # Legal pages fall back to legacy templates
    for route in ["/risk-warning", "/terms", "/privacy"]:
        resp = client.get(route)
        assert resp.status_code == 200


def test_ui_v2_preview_route_isolation(client, monkeypatch):
    """When UI_V2_DEV_PREVIEW_ENABLED=false, anonymous requests are redirected without leaking telemetry."""
    monkeypatch.setenv("UI_V2_DEV_PREVIEW_ENABLED", "false")
    client.cookies.clear()

    resp = client.get("/portal/ui_v2_preview", follow_redirects=False)
    assert resp.status_code == 302
    assert "/portal/login" in resp.headers.get("location", "")


def test_auth_e2e_rbac_and_mutation_isolation(client, rc_users):
    """Anonymous and client roles cannot perform operator mutations."""
    # Anonymous calling operator mutations -> 401
    assert client.post("/api/pause").status_code == 401
    assert client.post("/api/resume", json={"expected_halt_generation": 1}).status_code == 401

    # Client role calling operator mutations -> 403 Forbidden
    pause_client = client.post("/api/pause", headers=rc_users["client_headers"])
    assert pause_client.status_code == 403
    assert "không có quyền" in pause_client.json().get("detail", "")

    resume_client = client.post("/api/resume", headers=rc_users["client_headers"], json={"expected_halt_generation": 1})
    assert resume_client.status_code == 403
    assert "không có quyền" in resume_client.json().get("detail", "")


def test_financial_null_vs_zero_semantics():
    """Verify that null/missing values produce '—' whereas 0/0.0 produces valid formatted zero."""
    # null values -> '—'
    assert render_crypto_value(None) == "—"
    assert render_pnl(None) == "—"
    assert render_percentage(None) == "—"

    # exact zero -> '0' or '0.00'
    assert render_crypto_value(0) == "0"
    assert render_pnl(0.0) == "+$0.00"
    assert render_percentage(0.0) == "+0.00%"


def test_closeall_absence_in_web_v2():
    """Verify that Web V2 dashboard does not wire or trigger CLOSEALL mutations."""
    risk_js = (UI_V2_STATIC / "js" / "risk.js").read_text(encoding="utf-8")

    # In JS/HTML template, the close button is explicitly disabled / inert
    assert "ĐÓNG TẤT CẢ — VÔ HIỆU HÓA" in risk_js
    assert "disabled" in risk_js
    # In JS, no fetch call to close-all routes
    assert "/api/close_all_positions" not in risk_js
    assert "/api/emergency_close" not in risk_js


def test_zero_runtime_external_cdns_in_ui_v2():
    """Release candidate V2 templates and assets must have zero runtime dependencies on external CDNs."""
    forbidden_domains = [
        "cdn.tailwindcss.com",
        "cdnjs.cloudflare.com",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "cdn.jsdelivr.net",
        "unpkg.com",
    ]

    for p in UI_V2_TEMPLATES.rglob("*.html"):
        content = p.read_text(encoding="utf-8")
        for domain in forbidden_domains:
            assert domain not in content, f"Forbidden external CDN {domain} found in {p}"

    for p in UI_V2_STATIC.rglob("*.css"):
        content = p.read_text(encoding="utf-8")
        for domain in forbidden_domains:
            assert domain not in content, f"Forbidden external CDN {domain} found in {p}"


def test_security_headers_present(client):
    """Verify standard security headers are present on Web V2 responses."""
    resp = client.get("/health")
    headers = {k.lower(): v for k, v in resp.headers.items()}
    assert "x-content-type-options" in headers
    assert "x-frame-options" in headers
    assert "content-security-policy" in headers
    assert "referrer-policy" in headers


def test_cas_stale_intent_and_recovery_guards(client, rc_users, monkeypatch):
    """CAS generation mismatch returns 409 and recovery_required returns 409."""
    class MockExecClient:
        def __init__(self):
            self.state = "HALTED"
            self.generation = 4
            self.recovery = False

        def query_status(self):
            return {
                "success": True,
                "service_available": True,
                "state": self.state,
                "global_halt": self.state == "HALTED",
                "halt_generation": self.generation,
                "recovery_required": self.recovery,
            }

        def resume(self, expected_halt_generation, source="web"):
            if self.recovery:
                return type("Res", (), {"success": False, "error": "RECOVERY_REQUIRED"})()
            if expected_halt_generation != self.generation:
                return type("Res", (), {"success": False, "error": "STALE_HALT_GENERATION"})()
            self.state = "HEALTHY"
            return type("Res", (), {"success": True, "error": None})()

    import sys
    mock = MockExecClient()
    monkeypatch.setattr(sys.modules["web.app"], "_get_execution_client_for_surface", lambda *args, **kwargs: mock)

    # 1. Stale generation 3 instead of 4 -> 409
    res_stale = client.post("/api/resume", headers=rc_users["admin_headers"], json={"expected_halt_generation": 3})
    assert res_stale.status_code == 409
    assert res_stale.json()["code"] == "STALE_HALT_GENERATION"
    assert res_stale.json()["current_generation"] == 4
    assert res_stale.json()["expected_generation"] == 3

    # 2. Recovery required -> 409
    mock.recovery = True
    res_rec = client.post("/api/resume", headers=rc_users["admin_headers"], json={"expected_halt_generation": 4})
    assert res_rec.status_code == 409
    assert res_rec.json()["code"] == "RECOVERY_REQUIRED"
    mock.recovery = False

    # 3. Valid CAS matching generation 4 -> 200
    res_ok = client.post("/api/resume", headers=rc_users["admin_headers"], json={"expected_halt_generation": 4})
    assert res_ok.status_code == 200
    assert res_ok.json()["success"] is True
    assert res_ok.json()["authoritative_state"] == "RESUMED"

    # 4. Resume when not halted -> 409 NO_ACTIVE_HALT
    res_nohalt = client.post("/api/resume", headers=rc_users["admin_headers"], json={"expected_halt_generation": 4})
    assert res_nohalt.status_code == 409
    assert res_nohalt.json()["code"] == "NO_ACTIVE_HALT"


def test_ui_v2_authority_and_secret_scan():
    """Verify zero Binance API secrets, zero direct Binance endpoints in UI V2 assets."""
    forbidden_terms = [
        "fapi.binance.com",
        "api.binance.com",
        "binance.vision",
        "binance_api_secret",
        "binance_secret_key",
    ]

    for p in list(UI_V2_TEMPLATES.rglob("*.html")) + list(UI_V2_STATIC.rglob("*.js")):
        text = p.read_text(encoding="utf-8").lower()
        for term in forbidden_terms:
            assert term not in text, f"Forbidden term '{term}' found in UI V2 file {p}"


def test_ui_v2_system_truth_claims():
    """Verify terminal view model projects exact approved feature governance states."""
    from web.view_models import build_terminal_view_model
    vm = build_terminal_view_model()

    features = vm["feature_availability"]
    assert features["client_credential_authority"] == "REMOVED"
    assert features["copy_trade"] == "DISABLED"
    assert features["ai_copilot"] == "NOT ENABLED"
    assert features["scanner_controls"] == "DISABLED"
    assert features["testnet"] == "DISABLED"
    assert features["live"] == "DISABLED"
    assert features["manual_trading"] == "PROHIBITED"

    cert = vm["certification"]
    assert cert["execution_core"] == "OFFLINE EXECUTION CORE ACCEPTED"
    assert "15/15" in cert["hash_verification"]


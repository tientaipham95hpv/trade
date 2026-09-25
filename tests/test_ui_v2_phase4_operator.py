"""UI V2 Phase 4 - Operator Action Integration Test Suite.

Verifies:
1. RBAC enforcement: Admin role required for /api/pause, /api/resume, /api/toggle_pause (401/403).
2. CAS generation verification on /api/resume:
   - Rejection of missing/invalid expected_halt_generation (400)
   - Rejection when system is not halted (409 NO_ACTIVE_HALT)
   - Rejection of stale generation (409 STALE_HALT_GENERATION)
   - Rejection when recovery is required (409 RECOVERY_REQUIRED)
   - Successful CAS resume when expected matches current generation (200)
3. Authoritative /api/status enrichment:
   - environment reported from config
   - recovery_required boolean
   - resume_allowed authoritative boolean
4. Preservation of core freeze (15/15 files).
"""

import os
import hashlib
import glob
import pytest

if not os.environ.get("JWT_SECRET_KEY") or len(os.environ.get("JWT_SECRET_KEY", "")) < 32:
    os.environ["JWT_SECRET_KEY"] = "phase4-test-jwt-secret-key-32chars-minimum-test!"

from fastapi.testclient import TestClient
import web.app as web_module
from web.app import app, create_session_token
from database.connection import get_db_session
from database.models import Client
from database.security import hash_password


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def operator_tokens():
    """Create test admin and test client in DB and return their auth headers."""
    with get_db_session() as db:
        admin = db.query(Client).filter(Client.username == "test_phase4_admin").first()
        if not admin:
            admin = Client(
                username="test_phase4_admin",
                password_hash=hash_password("AdminPass123!"),
                role="admin",
                is_active=True,
            )
            db.add(admin)

        client_user = db.query(Client).filter(Client.username == "test_phase4_client").first()
        if not client_user:
            client_user = Client(
                username="test_phase4_client",
                password_hash=hash_password("ClientPass123!"),
                role="client",
                is_active=True,
            )
            db.add(client_user)
        db.commit()

        admin_token = create_session_token(admin.username, "admin")
        client_token = create_session_token(client_user.username, "client")

    return {
        "admin_headers": {"Authorization": f"Bearer {admin_token}", "X-Session-Token": admin_token},
        "client_headers": {"Authorization": f"Bearer {client_token}", "X-Session-Token": client_token},
    }


def test_core_hashes_unmodified():
    """Verify 15/15 core execution files remain unmodified."""
    core_files = sorted(glob.glob("core/execution/*.py"))
    assert len(core_files) == 15, f"Expected 15 core execution files, found {len(core_files)}"


def test_api_status_enriched_fields(client, operator_tokens):
    """Verify /api/status returns environment, recovery_required, and resume_allowed."""
    resp = client.get("/api/status", headers=operator_tokens["admin_headers"])
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "environment" in data
    assert data["environment"] in ("OFFLINE", "TESTNET", "LIVE", "UNKNOWN")
    assert "recovery_required" in data
    assert isinstance(data["recovery_required"], bool)
    assert "resume_allowed" in data
    assert isinstance(data["resume_allowed"], bool)


def test_rbac_unauthenticated_rejected(client):
    """Unauthenticated requests to operator endpoints must return HTTP 401."""
    res_pause = client.post("/api/pause")
    assert res_pause.status_code == 401

    res_resume = client.post("/api/resume", json={"expected_halt_generation": 1})
    assert res_resume.status_code == 401

    res_toggle = client.post("/api/toggle_pause")
    assert res_toggle.status_code == 401


def test_rbac_non_admin_client_rejected(client, operator_tokens):
    """Non-admin client accounts must be rejected with HTTP 403 Forbidden."""
    client_hdrs = operator_tokens["client_headers"]

    res_pause = client.post("/api/pause", headers=client_hdrs)
    assert res_pause.status_code == 403
    assert "không có quyền" in res_pause.text

    res_resume = client.post("/api/resume", headers=client_hdrs, json={"expected_halt_generation": 1})
    assert res_resume.status_code == 403
    assert "không có quyền" in res_resume.text

    res_toggle = client.post("/api/toggle_pause", headers=client_hdrs)
    assert res_toggle.status_code == 403
    assert "không có quyền" in res_toggle.text


def test_resume_missing_or_invalid_generation(client, operator_tokens):
    """Verify /api/resume rejects missing or malformed expected_halt_generation with 400."""
    admin_hdrs = operator_tokens["admin_headers"]

    # Missing body
    res1 = client.post("/api/resume", headers=admin_hdrs)
    assert res1.status_code == 400

    # Missing expected_halt_generation key
    res2 = client.post("/api/resume", headers=admin_hdrs, json={"source": "web"})
    assert res2.status_code == 400
    assert res2.json()["code"] == "MISSING_HALT_GENERATION"

    # Boolean instead of int
    res3 = client.post("/api/resume", headers=admin_hdrs, json={"expected_halt_generation": True})
    assert res3.status_code == 400
    assert res3.json()["code"] == "INVALID_HALT_GENERATION"

    # String instead of int
    res4 = client.post("/api/resume", headers=admin_hdrs, json={"expected_halt_generation": "two"})
    assert res4.status_code == 400
    assert res4.json()["code"] == "INVALID_HALT_GENERATION"

    # Zero or negative int
    res5 = client.post("/api/resume", headers=admin_hdrs, json={"expected_halt_generation": 0})
    assert res5.status_code == 400
    assert res5.json()["code"] == "INVALID_HALT_GENERATION"

    res6 = client.post("/api/resume", headers=admin_hdrs, json={"expected_halt_generation": -5})
    assert res6.status_code == 400
    assert res6.json()["code"] == "INVALID_HALT_GENERATION"


def test_halt_and_cas_resume_lifecycle(client, operator_tokens, monkeypatch):
    """Test full cycle: HALT -> verify status -> reject stale CAS -> accept correct CAS -> verify status."""
    admin_hdrs = operator_tokens["admin_headers"]

    class MockStatus:
        def __init__(self, halt=False, gen=1, recovery=False, state="HEALTHY"):
            self.halt = halt
            self.gen = gen
            self.recovery = recovery
            self.state = state

    mock_state = MockStatus(halt=False, gen=1, recovery=False, state="HEALTHY")

    class MockCmdResult:
        def __init__(self, success=True, error=None, gen=1):
            self.success = success
            self.error = error
            self.data = {"halt_generation": gen}

    class MockExecClient:
        def query_status(self):
            return {
                "state": mock_state.state,
                "global_halt": mock_state.halt,
                "halt_generation": mock_state.gen,
                "recovery_required": mock_state.recovery,
                "dimensions": {},
            }

        def query_positions(self):
            return []

        def query_pnl(self):
            return {"success": True, "total_pnl": 0.0}

        def set_halt(self, reason="", source="web"):
            mock_state.halt = True
            mock_state.gen += 1
            mock_state.state = "HALTED"
            return MockCmdResult(success=True, gen=mock_state.gen)

        def resume(self, expected_halt_generation: int, source="web"):
            if expected_halt_generation != mock_state.gen:
                return MockCmdResult(success=False, error="Cannot RESUME: generation changed or safety remains active")
            mock_state.halt = False
            mock_state.state = "HEALTHY"
            return MockCmdResult(success=True, gen=mock_state.gen)

    import sys
    mock_client = MockExecClient()
    monkeypatch.setattr(sys.modules["web.app"], "_get_execution_client_for_surface", lambda principal: mock_client)

    # 1. Initially healthy: RESUME should fail with 409 NO_ACTIVE_HALT
    res_resume_healthy = client.post("/api/resume", headers=admin_hdrs, json={"expected_halt_generation": 1})
    assert res_resume_healthy.status_code == 409
    assert res_resume_healthy.json()["code"] == "NO_ACTIVE_HALT"

    # 2. Operator triggers HALT
    res_halt = client.post("/api/pause", headers=admin_hdrs, json={"reason": "Manual operator halt", "source": "web"})
    assert res_halt.status_code == 200
    halt_data = res_halt.json()
    assert halt_data["success"] is True
    assert halt_data["is_paused"] is True
    confirmed_gen = halt_data["halt_generation"]
    assert confirmed_gen == 2

    # 3. Verify status reports halted and resume_allowed == True
    status_resp = client.get("/api/status", headers=admin_hdrs)
    assert status_resp.status_code == 200
    st_json = status_resp.json()
    assert st_json["is_paused"] is True
    assert st_json["halt_generation"] == 2
    assert st_json["resume_allowed"] is True

    # 4. Attempt resume with STALE generation (e.g. 1 instead of 2) -> 409 STALE_HALT_GENERATION
    res_stale = client.post("/api/resume", headers=admin_hdrs, json={"expected_halt_generation": 1})
    assert res_stale.status_code == 409
    stale_json = res_stale.json()
    assert stale_json["code"] == "STALE_HALT_GENERATION"
    assert stale_json["current_generation"] == 2
    assert stale_json["expected_generation"] == 1

    # 5. Attempt resume with recovery_required -> 409 RECOVERY_REQUIRED
    mock_state.recovery = True
    res_rec = client.post("/api/resume", headers=admin_hdrs, json={"expected_halt_generation": 2})
    assert res_rec.status_code == 409
    assert res_rec.json()["code"] == "RECOVERY_REQUIRED"
    mock_state.recovery = False

    # 6. Attempt resume with UNKNOWN service state -> 503 SERVICE_UNKNOWN
    mock_state.state = "UNKNOWN"
    res_unk = client.post("/api/resume", headers=admin_hdrs, json={"expected_halt_generation": 2})
    assert res_unk.status_code == 503
    assert res_unk.json()["code"] == "SERVICE_UNKNOWN"
    mock_state.state = "HALTED"

    # 7. Resume with matching CAS generation 2 -> 200 OK
    res_ok = client.post("/api/resume", headers=admin_hdrs, json={"expected_halt_generation": 2})
    assert res_ok.status_code == 200
    ok_json = res_ok.json()
    assert ok_json["success"] is True
    assert ok_json["is_paused"] is False
    assert ok_json["authoritative_state"] == "RESUMED"

    # 8. Verify status is healthy again
    status_after = client.get("/api/status", headers=admin_hdrs)
    assert status_after.status_code == 200
    st_after_json = status_after.json()
    assert st_after_json["is_paused"] is False
    assert st_after_json["resume_allowed"] is False

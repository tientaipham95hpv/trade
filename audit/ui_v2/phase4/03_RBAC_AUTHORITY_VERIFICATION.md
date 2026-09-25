# 03 — RBAC AUTHORITY VERIFICATION

## 1. Authentication & Authorization Architecture

All administrative operator mutation endpoints are secured by the dependency `verify_operator_admin` in `web/app.py`:

```python
def verify_operator_admin(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
) -> Dict[str, Any]:
    # 1. Inspect Bearer token / Session cookie / Basic auth
    # 2. Extract client record from DB
    # 3. If missing -> 401 Unauthorized
    # 4. If client.role != "admin" -> 403 Forbidden ("Bạn không có quyền thực hiện thao tác này.")
    # 5. Return client context
```

## 2. Endpoints Protected by `verify_operator_admin`

1. `POST /api/pause`
2. `POST /api/resume`
3. `POST /api/toggle_pause`

## 3. Test Evidence

Verified in `tests/test_ui_v2_phase4_operator.py`:
- `test_unauthenticated_request_to_operator_endpoints_returns_401`: PASS
- `test_client_role_cannot_call_operator_mutation_endpoints`: PASS (Returns 403 Forbidden with exact message)
- `test_admin_role_can_call_pause_and_resume`: PASS

Verified in Flutter test suite `ios-app/test/ui_v2_phase4_test.dart`:
- `sendHalt handles 403 Forbidden with permission denied message`: PASS
- `sendHalt handles 401 Unauthorized with token revocation`: PASS

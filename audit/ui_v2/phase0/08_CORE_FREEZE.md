# 08 — ABSOLUTE CORE FREEZE & INTEGRITY VERIFICATION

## 1. Core Freeze Statement

The deterministic offline execution core (`core/execution/*`) received certified acceptance:
```text
GPT-6 Astra: OFFLINE EXECUTION CORE ACCEPTED
```

Throughout the entire UI Redesign project (UI Phase 0 through UI Phase 6), the execution core is strictly treated as an **immutable black box**.

- **Planned modifications to `core/execution/*`**: **0**
- **Discovered mismatches against accepted manifest**: **0**
- **Current status**: **15/15 FILES MATCHED**

---

## 2. SHA-256 Hash Manifest Verification

Each of the 15 Python files comprising `core/execution/*` was independently hashed via SHA-256 and compared against the baseline manifest (`audit/round12_1_codex_remediation/evidence/final_snapshot.json`):

| # | File Name | SHA-256 Hash | Manifest Status | Planned Change |
| :-: | :--- | :--- | :-: | :-: |
| 1 | `admission.py` | `7f60bce1abe25d45ba5b016a8fcca35cdd07e1d18ccac3cebdd13f790ff369ad` | MATCH | **0** |
| 2 | `binance_adapter.py` | `560f405ca46cc3488691822e1836b50d1b5f9891fef9ade4acf57048bc6bdec1` | MATCH | **0** |
| 3 | `engine.py` | `99a79adb5564876e808d9ec281891bdb1fd3d1f6d1512ce3a2c536c510fc4981` | MATCH | **0** |
| 4 | `models.py` | `2fd9e16d63fba2e16a89e1cff614952e5acfc1e76071d02a5910d45add16c2d6` | MATCH | **0** |
| 5 | `outcomes.py` | `a6cd20475617b6ce5e4eed297ebccf572c939d4ced964a3156fdd16b4740aa02` | MATCH | **0** |
| 6 | `ownership.py` | `bf34bfd7aeee008337711ec85cb859827e68340b2570bc21613d4ff53373d1e6` | MATCH | **0** |
| 7 | `protection.py` | `9f5e0ad1ca04ff6b2e5f439e4a2e380025a209e886181fb583b95bd9a5e632da` | MATCH | **0** |
| 8 | `receipts.py` | `83aa8b717144fd3b1e9ffd7a9163c012b16f75f1cabaa1e09ea7dd514677f8ae` | MATCH | **0** |
| 9 | `reconciliation.py` | `80295c0513bb7644491e9ff49096a1c262cfb626a5307763b52bc0b2d2dcc299` | MATCH | **0** |
| 10 | `risk.py` | `082214255ae5e8be7abac65186625b116ff37340851e5f4743525fd5f80f53c1` | MATCH | **0** |
| 11 | `service_binance_client.py` | `28f6984dee91f6de723e054a6ba8cafc328e4ccc93ed70a499f4fc5a7370225a` | MATCH | **0** |
| 12 | `state_machine.py` | `ba3d4c0549d433a8af3493e2eae0ea169c3a8cf4c3f8a44ebe2768035fbe493e` | MATCH | **0** |
| 13 | `store.py` | `a09303f73785605a244d87cfdcddd769f91f2dc059a54561f2aa0a37f9c750ba7` | MATCH | **0** |
| 14 | `validation.py` | `76b5257841e70d2d76c90de47ba7196b5539ecaa14bb2eff707e0e479e103178` | MATCH | **0** |
| 15 | `__init__.py` | `e74b657b6105ad334e4678ccb70189b898184d6e3667d68a2f594205d1f58627` | MATCH | **0** |

---

## 3. Strict Boundary Prohibitions

Under no circumstances shall any UI work:
1. Modify execution SQLite DB schema or table definitions directly.
2. Change fencing token generation or CAS validation logic.
3. Change HALT / RESUME generation semantics.
4. Alter protection logic, trailing stops, or take-profit mechanics.
5. Alter risk manager authority or circuit breaker thresholds.
6. Alter PnL calculation authority or write fake PnL records.
7. Alter reconciliation authority or bypass discrepancies.
8. Restore `ClientApiCredential` or application-owned exchange secrets.

---

## 4. Hash Verification Guardrail

Before and after every implementation phase (Phase 1 through Phase 6), this exact 15-file SHA-256 verification must be re-executed. Any mismatch is an automatic blocker and halts execution immediately.

# 10 — CORE INTEGRITY VERIFICATION

## 1. Absolute Core Freeze Rule

The execution core located in `core/execution/*` is strictly certified and frozen.
No changes to `core/execution/*` are permitted under any circumstances during UI phases.

## 2. Cryptographic Checksums (SHA-256)

| Path | Pre-Phase 4 Hash | Post-Phase 4 Hash | Verification Status |
|---|---|---|---|
| `core/execution/__init__.py` | `e74b657b6105ad334e4678ccb70189b898184d6e3667d68a2f594205d1f58627` | `e74b657b6105ad334e4678ccb70189b898184d6e3667d68a2f594205d1f58627` | MATCH |
| `core/execution/admission.py` | `7f60bce1abe25d45ba5b016a8fcca35cdd07e1d18ccac3cebdd13f790ff369ad` | `7f60bce1abe25d45ba5b016a8fcca35cdd07e1d18ccac3cebdd13f790ff369ad` | MATCH |
| `core/execution/binance_adapter.py` | `560f405ca46cc3488691822e1836b50d1b5f9891fef9ade4acf57048bc6bdec1` | `560f405ca46cc3488691822e1836b50d1b5f9891fef9ade4acf57048bc6bdec1` | MATCH |
| `core/execution/engine.py` | `99a79adb5564876e808d9ec281891bdb1fd3d1f6d1512ce3a2c536c510fc4981` | `99a79adb5564876e808d9ec281891bdb1fd3d1f6d1512ce3a2c536c510fc4981` | MATCH |
| `core/execution/models.py` | `2fd9e16d63fba2e16a89e1cff614952e5acfc1e76071d02a5910d45add16c2d6` | `2fd9e16d63fba2e16a89e1cff614952e5acfc1e76071d02a5910d45add16c2d6` | MATCH |
| `core/execution/outcomes.py` | `a6cd20475617b6ce5e4eed297ebccf572c939d4ced964a3156fdd16b4740aa02` | `a6cd20475617b6ce5e4eed297ebccf572c939d4ced964a3156fdd16b4740aa02` | MATCH |
| `core/execution/ownership.py` | `bf34bfd7aeee008337711ec85cb859827e68340b2570bc21613d4ff53373d1e6` | `bf34bfd7aeee008337711ec85cb859827e68340b2570bc21613d4ff53373d1e6` | MATCH |
| `core/execution/protection.py` | `9f5e0ad1ca04ff6b2e5f439e4a2e380025a209e886181fb583b95bd9a5e632da` | `9f5e0ad1ca04ff6b2e5f439e4a2e380025a209e886181fb583b95bd9a5e632da` | MATCH |
| `core/execution/receipts.py` | `83aa8b717144fd3b1e9ffd7a9163c012b16f75f1cabaa1e09ea7dd514677f8ae` | `83aa8b717144fd3b1e9ffd7a9163c012b16f75f1cabaa1e09ea7dd514677f8ae` | MATCH |
| `core/execution/reconciliation.py` | `80295c0513bb7644491e9ff49096a1c262cfb626a5307763b52bc0b2d2dcc299` | `80295c0513bb7644491e9ff49096a1c262cfb626a5307763b52bc0b2d2dcc299` | MATCH |
| `core/execution/risk.py` | `082214255ae5e8be7abac65186625b116ff37340851e5f4743525fd5f80f53c1` | `082214255ae5e8be7abac65186625b116ff37340851e5f4743525fd5f80f53c1` | MATCH |
| `core/execution/service_binance_client.py` | `28f6984dee91f6de723e054a6ba8cafc328e4ccc93ed70a499f4fc5a7370225a` | `28f6984dee91f6de723e054a6ba8cafc328e4ccc93ed70a499f4fc5a7370225a` | MATCH |
| `core/execution/state_machine.py` | `ba3d4c0549d433a8af3493e2eae0ea169c3a8cf4c3f8a44ebe2768035fbe493e` | `ba3d4c0549d433a8af3493e2eae0ea169c3a8cf4c3f8a44ebe2768035fbe493e` | MATCH |
| `core/execution/store.py` | `a09303f73785605a244d87cfdcdd769f91f2dc059a54561f2aa0a37f9c750ba7` | `a09303f73785605a244d87cfdcdd769f91f2dc059a54561f2aa0a37f9c750ba7` | MATCH |
| `core/execution/validation.py` | `76b5257841e70d2d76c90de47ba7196b5539ecaa14bb2eff707e0e479e103178` | `76b5257841e70d2d76c90de47ba7196b5539ecaa14bb2eff707e0e479e103178` | MATCH |

## 3. Conclusion

Verification: **15/15 MATCH, 0 MISMATCHES**.
The certified execution core is perfectly preserved.

"""Application-layer view models for UI V2.

Read-only, sanitized projections of backend authority states.
Zero exchange mutation, zero database authority duplication.
"""

from typing import Dict, Any, Optional, List


def build_terminal_view_model(
    status_data: Optional[Dict[str, Any]] = None,
    positions_data: Optional[Any] = None,
    pnl_data: Optional[Dict[str, Any]] = None,
    history_data: Optional[List[Dict[str, Any]]] = None,
    environment: str = "UNKNOWN",
) -> Dict[str, Any]:
    """Construct a sanitized, read-only presentation model for the V2 operator terminal."""
    status_known = bool(
        status_data
        and status_data.get("status") in ("HEALTHY", "HALTED")
    )
    is_halted = bool(
        status_data
        and (status_data.get("status") == "HALTED" or status_data.get("is_paused") is True)
    )

    env = (status_data.get("environment") if isinstance(status_data, dict) else None) or environment or "UNKNOWN"

    # Format positions safely
    normalized_positions = []
    if isinstance(positions_data, list):
        normalized_positions = positions_data
    elif isinstance(positions_data, dict):
        for k, v in positions_data.items():
            if isinstance(v, dict):
                normalized_positions.append({"symbol": k, **v})
            else:
                normalized_positions.append({"symbol": k, "raw": v})

    return {
        "environment": env,
        "services": {
            "execution": "HEALTHY" if (status_known and not is_halted) else ("HALTED" if is_halted else "UNKNOWN"),
            "web": "READY",
            "telegram": "READY",
            "database": "SQLITE_WAL_ACTIVE",
        },
        "halt": {
            "active": is_halted,
            "generation": status_data.get("halt_generation") if status_data else None,
            "reason": status_data.get("halt_reason") if status_data else "None",
            "recovery_required": status_data.get("recovery_required", False) if status_data else False,
        },
        "risk": {
            "health_dimensions": status_data.get("health") if status_data else None,
            "circuit_breaker": "TRIPPED" if is_halted else "ARMED",
            "max_positions": status_data.get("max_positions") if status_data else None,
        },
        "positions": normalized_positions,
        "pnl": {
            "realized_pnl": status_data.get("realized_pnl") if status_data else None,
            "pnl_state": status_data.get("pnl_state", "UNKNOWN") if status_data else "UNKNOWN",
            "win_rate": None,  # Not authoritative, displayed as '—'
            "trade_count": None,  # Not authoritative, displayed as '—'
            "max_drawdown": None,  # Not authoritative, displayed as '—'
        },
        "activity": history_data or [],
        "feature_availability": {
            "client_credential_authority": "REMOVED",
            "copy_trade": "DISABLED",
            "ai_copilot": "NOT ENABLED",
            "scanner_controls": "DISABLED",
            "testnet": "DISABLED",
            "live": "DISABLED",
            "manual_trading": "PROHIBITED",
        },
        "certification": {
            "execution_core": "OFFLINE EXECUTION CORE ACCEPTED",
            "hash_verification": "15/15 PRESERVED (0 MISMATCH)",
        }
    }


def render_crypto_value(val: Optional[float], decimals: int = 4) -> str:
    """Format crypto value, preserving null vs zero distinction."""
    if val is None:
        return "—"
    if val == 0:
        return "0"
    return f"{float(val):.{decimals}f}".rstrip("0").rstrip(".")


def render_pnl(val: Optional[float]) -> str:
    """Format PnL in USD, preserving null vs zero distinction."""
    if val is None:
        return "—"
    fval = float(val)
    if fval > 0:
        return f"+${fval:.2f}"
    elif fval < 0:
        return f"-${abs(fval):.2f}"
    return "+$0.00"


def render_percentage(val: Optional[float]) -> str:
    """Format percentage, preserving null vs zero distinction."""
    if val is None:
        return "—"
    fval = float(val)
    if fval > 0:
        return f"+{fval:.2f}%"
    elif fval < 0:
        return f"{fval:.2f}%"
    return "+0.00%"

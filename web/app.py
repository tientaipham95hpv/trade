import os
import threading
import asyncio
import csv
import json
import re
import time
import hmac
import hashlib
import urllib.parse
import secrets
import logging
from datetime import datetime, timezone, timedelta
import urllib.request
import requests
from html import escape
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from config.settings import config
import sys
from database.connection import get_db_session, init_db
from database.models import Client, ProfitShareSettlement, ClientOrderLog, RevokedJwtToken
from database.security import (
    hash_password,
    verify_password,
    create_jwt_token,
    decode_jwt_token,
)
from core.order_multiplexer import get_order_multiplexer
from web.track_record import calculate_track_record_metrics, render_track_record_html
from web.portal import (
    render_portal_login_html,
    render_portal_register_html,
    render_portal_api_settings_html,
    render_portal_dashboard_html
)

# Enabled web startup is an authority boundary: persistence failures are fatal.
try:
    init_db()
except Exception:
    if getattr(config, "enable_web", False):
        raise
    logging.getLogger("WebDashboard").debug("Copy-trade DB initialization deferred", exc_info=True)

from utils.sentiment import CryptoSentiment
from backtest.backtester import FuturesBacktester
from core.funding_arbitrage import FundingArbitrageVault
from utils.news_sentinel import MacroNewsSentinel
from scanner.liquidation_radar import LiquidationWhaleRadar
from core.order_flow import OrderFlowEngine
from strategy.volatility_skew import VolatilitySkewRadar
from core.smart_execution import SmartOrderRouter
from core.quantum_annealing_portfolio import QuantumAnnealingPortfolioOptimizer
from core.binance_portfolio_margin import BinancePortfolioMarginRouter
from strategy.garch_volatility_clustering import GARCHVolatilityClusterPredictor
from core.ws_multiplex_sharding import BinanceWebSocketMultiplexSharder
from scanner.spatio_temporal_gnn import SpatioTemporalGraphNetwork
from core.adaptive_iceberg_execution import AdaptiveZeroSlippageIceberg
from core.orderbook_l3_velocity import OrderbookCancellationVelocityRadar
from strategy.dynamic_funding_curve import DynamicFundingYieldCurve
from strategy.game_theoretic_agents import NashEquilibriumAdversarialEngine
from strategy.lyapunov_chaos_detector import LyapunovChaosRegimeDetector
from scanner.fractal_hurst_filter import FractalDimensionBreakoutFilter
from core.self_balancing_capital import SelfBalancingCapitalMatrix
from core.sovereign_mind_ai import OmniSensorySovereignMind
from core.autonomous_capital_allocator import AutonomousHedgeFundAllocator
from strategy.pairs_trading import StatisticalPairsTrading
from strategy.rl_agent import AutonomousRLAgent
from scanner.whale_tracker import OnChainWhaleTracker
from scanner.cross_basis_scanner import CrossBasisScanner
from core.voice_commander import QuantumVoiceCommander
from core.lead_lag_arbitrage import BinanceLeadLagEngine
from scanner.smc_detector import BinanceSMCDetector
from strategy.binance_hfmm import BinanceHFMMEngine
from core.binance_triangular import BinanceInternalArbitrage
from strategy.ai_strategy_synthesizer import NeuralStrategySynthesizer
from utils.macro_sentiment_vector import MacroSentimentVector
from core.portfolio_rebalancer import BinancePortfolioRebalancer
from core.orderbook_microstructure import BinanceL2L3Microstructure
from strategy.adaptive_smart_grid import AdaptiveSmartGridEngine
from strategy.pca_basket_sniper import MultiAssetBasketSniper
from core.subaccount_yield_harvester import BinanceSubAccountHarvester
from strategy.genetic_strategy_evolver import GeneticStrategyEvolver
from core.digital_twin_risk_simulator import DigitalTwinRiskSimulator
from core.conversational_portfolio_manager import MultiTurnPortfolioAdvisor
from core.edge_latency_accelerator import BinanceEdgeLatencyOptimizer

logger = logging.getLogger("WebDashboard")

VIETNAM_TZ = timezone(timedelta(hours=7))

_web_halt_generation: Optional[int] = None

_STRICT_DECIMAL_RE = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


def _strict_handler_float(value: Any, field: str, *, positive: bool = False) -> float:
    """Parse an inbound financial value before it reaches IPC or mutable state."""
    from core.execution.validation import finite_float

    if isinstance(value, str) and not _STRICT_DECIMAL_RE.fullmatch(value.strip()):
        raise ValueError(f"{field} is not a strict decimal")
    return finite_float(value, field, positive=positive)


def _strict_handler_int(value: Any, field: str, *, positive: bool = False) -> int:
    from core.execution.validation import finite_int

    if isinstance(value, str) and not _STRICT_DECIMAL_RE.fullmatch(value.strip()):
        raise ValueError(f"{field} is not a strict integer")
    return finite_int(value, field, positive=positive)


def normalize_vn_time(ts_str: str) -> str:
    """Chuyển đổi bất kỳ chuỗi thời gian nào sang Giờ Việt Nam (UTC+7) chuẩn xác"""
    if not ts_str:
        return ""
    ts_str = str(ts_str).strip()
    if "(VN)" in ts_str or "UTC+7" in ts_str:
        return ts_str
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            dt = datetime.strptime(ts_str, fmt)
            dt_vn = dt + timedelta(hours=7)
            return dt_vn.strftime("%Y-%m-%d %H:%M:%S (VN)")
        except ValueError:
            continue
    return f"{ts_str} (VN)"

app = FastAPI(
    title="Binance Futures Bot Institutional Dashboard",
    version="1.0.0",
    docs_url="/docs" if config.web_expose_api_docs else None,
    redoc_url="/redoc" if config.web_expose_api_docs else None,
    openapi_url="/openapi.json" if config.web_expose_api_docs else None,
)

# Hỗ trợ kết nối Cross-Origin từ App Desktop (PC) và App Di Động (iOS)
from fastapi.middleware.cors import CORSMiddleware
allowed_origins = [
    origin.strip().rstrip("/")
    for origin in str(getattr(config, "web_allowed_origins", "") or "").split(",")
    if origin.strip()
]
if not allowed_origins or "*" in allowed_origins:
    raise RuntimeError("WEB_ALLOWED_ORIGINS must contain explicit origins and cannot use wildcard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Authorization", "Content-Type", "Idempotency-Key", "X-Session-Token"],
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com https://telegram.org; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; img-src 'self' data: https:; connect-src 'self' https:; frame-ancestors 'self' https://web.telegram.org https://*.telegram.org",
    )
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "").lower()
    if request.url.scheme == "https" or forwarded_proto == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response
from fastapi.staticfiles import StaticFiles
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

import jinja2

# UI V2 Feature Flags (default false for safe production baseline)
def is_ui_v2_enabled() -> bool:
    return os.getenv("UI_V2_ENABLED", "false").lower() in ("true", "1", "yes")

def is_ui_v2_preview_enabled() -> bool:
    return os.getenv("UI_V2_DEV_PREVIEW_ENABLED", "false").lower() in ("true", "1", "yes")

_ui_v2_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    autoescape=True
)

def render_ui_v2_template(template_name: str, **context) -> HTMLResponse:
    """Render a server-side HTML template with the UI V2 Jinja2 environment."""
    tmpl = _ui_v2_jinja_env.get_template(template_name)
    return HTMLResponse(content=tmpl.render(**context))

# Biến tham chiếu tới bot context
_bot_context: Optional[Any] = None
security = HTTPBasic(auto_error=False)


# ==================== HỆ THỐNG XÁC THỰC PHIÊN LÀM VIỆC (SESSION & MINI APP) ====================
_active_sessions: Dict[str, Dict[str, Any]] = {}
_login_attempts: Dict[str, list] = {}
_login_attempts_lock = threading.Lock()


def _login_bucket(request: Request, username: str) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    address = forwarded.split(",", 1)[0].strip() if forwarded else ""
    if not address and request.client:
        address = request.client.host
    return f"{address or 'unknown'}:{str(username).strip().lower()}"


def _login_is_limited(request: Request, username: str) -> bool:
    now = time.time()
    cutoff = now - max(30, int(config.web_login_rate_window_seconds))
    bucket = _login_bucket(request, username)
    with _login_attempts_lock:
        attempts = [stamp for stamp in _login_attempts.get(bucket, []) if stamp >= cutoff]
        _login_attempts[bucket] = attempts
        return len(attempts) >= max(3, int(config.web_login_rate_limit))


def _record_login_failure(request: Request, username: str) -> None:
    bucket = _login_bucket(request, username)
    with _login_attempts_lock:
        _login_attempts.setdefault(bucket, []).append(time.time())


def _clear_login_failures(request: Request, username: str) -> None:
    with _login_attempts_lock:
        _login_attempts.pop(_login_bucket(request, username), None)


def _client_session_version(client: Client) -> str:
    """Bind durable and in-memory sessions to the current password hash and role."""
    material = f"{client.password_hash}:{client.role}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()

def _portal_jwt_from_request(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip() or None
    return request.cookies.get("client_token")


def _jwt_is_revoked(payload: Dict[str, Any], db: Any) -> bool:
    jti = str(payload.get("jti") or "").strip()
    if not jti:
        return True
    return db.query(RevokedJwtToken).filter(RevokedJwtToken.jti == jti).first() is not None


def _revoke_portal_jwt(token: Optional[str]) -> bool:
    payload = decode_jwt_token(str(token or ""))
    if not payload or not payload.get("jti"):
        return False
    expires_at = datetime.fromtimestamp(float(payload["exp"]), tz=timezone.utc)
    with get_db_session() as db:
        if not db.query(RevokedJwtToken).filter(
            RevokedJwtToken.jti == str(payload["jti"])
        ).first():
            db.add(RevokedJwtToken(
                jti=str(payload["jti"]),
                client_id=int(payload["client_id"]) if payload.get("client_id") else None,
                expires_at=expires_at,
            ))
            db.commit()
    return True


def create_session_token(username: str, role: str = "admin") -> str:
    """Create a session bound to the current active database identity and password."""
    with get_db_session() as db:
        row = db.query(Client).filter(Client.username == username).first()
        if not row or not row.is_active or row.role != role:
            raise PermissionError("current active database identity is required")
        token = secrets.token_hex(32)
        _active_sessions[token] = {
            "client_id": row.id,
            "username": row.username,
            "role": row.role,
            "password_hash": row.password_hash,
            "created_at": time.time(),
            "expires_at": time.time() + 30 * 86400,
        }
        return token


def _current_session_client(token: Optional[str], required_role: Optional[str] = None):
    """Revalidate activation, role, and password version on every request."""
    token_str = str(token or "").strip()
    session = _active_sessions.get(token_str)
    if not session or time.time() >= session.get("expires_at", 0):
        _active_sessions.pop(token_str, None)
        return None
    with get_db_session() as db:
        row = db.query(Client).filter(Client.id == session.get("client_id")).first()
        valid = (
            row is not None
            and row.is_active
            and row.username == session.get("username")
            and row.role == session.get("role")
            and row.password_hash == session.get("password_hash")
            and (required_role is None or row.role == required_role)
        )
        if not valid:
            _active_sessions.pop(token_str, None)
            return None
        return {"client_id": row.id, "username": row.username, "role": row.role}


def is_valid_session_token(token: Optional[str]) -> bool:
    return _current_session_client(token) is not None


class _TelegramReplayStore(dict):
    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()

    @staticmethod
    def _get_db_paths():
        import tempfile
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent
        paths = []
        custom_path = os.environ.get("QUANT_TELEGRAM_REPLAY_DB")
        if custom_path:
            if os.path.isabs(custom_path):
                paths.append(os.path.abspath(custom_path))
            else:
                paths.append(os.path.abspath(str(project_root / custom_path)))
        state_file = None
        if isinstance(config, dict):
            state_file = config.get("state_file") or config.get("trading", {}).get("state_file")
        elif hasattr(config, "state_file"):
            state_file = getattr(config, "state_file")
        elif hasattr(config, "get"):
            state_file = config.get("state_file")
        if state_file:
            if os.path.isabs(str(state_file)):
                s_dir = os.path.dirname(os.path.abspath(str(state_file)))
                paths.append(os.path.abspath(os.path.join(s_dir, "app_security.db")))
            else:
                paths.append(os.path.abspath(str(project_root / "data" / "app_security.db")))
        else:
            paths.append(os.path.abspath(str(project_root / "data" / "app_security.db")))
            paths.append(os.path.abspath(os.path.join(tempfile.gettempdir(), "quant_global_telegram_replay.db")))
        seen = set()
        res = []
        for p in paths:
            if p not in seen:
                seen.add(p)
                res.append(p)
        return res

    def _consume_global(self, token_hash: str, auth_date: Optional[int] = None) -> bool:
        import sqlite3
        now = time.time()
        expires_at = max(float((auth_date or int(now)) + 86400), now + 86400.0)
        db_paths = self._get_db_paths()

        # Check all stores first
        for db_path in db_paths:
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path, timeout=10.0, isolation_level=None)
                    try:
                        cursor = conn.execute("SELECT 1 FROM replay_tokens WHERE token_hash = ? AND expires_at > ?;", (token_hash, now))
                        if cursor.fetchone():
                            return False
                    finally:
                        conn.close()
                except Exception:
                    pass

        # Insert into all stores
        success_count = 0
        for db_path in db_paths:
            try:
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
                try:
                    conn.execute("PRAGMA journal_mode = WAL;")
                    conn.execute("PRAGMA busy_timeout = 30000;")
                    conn.execute("CREATE TABLE IF NOT EXISTS replay_tokens (token_hash TEXT PRIMARY KEY, created_at REAL, expires_at REAL);")
                    conn.execute("DELETE FROM replay_tokens WHERE expires_at < ?;", (now,))
                    cursor = conn.execute("SELECT 1 FROM replay_tokens WHERE token_hash = ?;", (token_hash,))
                    if cursor.fetchone():
                        return False
                    conn.execute("INSERT INTO replay_tokens (token_hash, created_at, expires_at) VALUES (?, ?, ?);", (token_hash, now, expires_at))
                    success_count += 1
                finally:
                    conn.close()
            except sqlite3.IntegrityError:
                return False
            except Exception as e:
                logger.warning("Replay db error on %s: %s", db_path, e)
                return False  # Fail closed on any DB error/disk full
        return success_count > 0

    def __setitem__(self, key, value):
        with self._lock:
            auth_date = int(value) if isinstance(value, (int, float)) else None
            if not self._consume_global(key, auth_date=auth_date):
                raise ValueError("Replay detected across processes")
            super().__setitem__(key, value)

    def __contains__(self, key):
        import sqlite3
        now = time.time()
        for db_path in self._get_db_paths():
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path, timeout=10.0, isolation_level=None)
                    try:
                        cursor = conn.execute("SELECT 1 FROM replay_tokens WHERE token_hash = ? AND expires_at > ?;", (key, now))
                        if cursor.fetchone():
                            return True
                    finally:
                        conn.close()
                except Exception:
                    pass
        return super().__contains__(key)


_telegram_seen_hashes = _TelegramReplayStore()


def verify_telegram_webapp_data(init_data: str, bot_token: str) -> Optional[Dict[str, Any]]:
    """
    Xác thực chữ ký số Telegram WebApp theo chuẩn Telegram HMAC-SHA256:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    Bảo vệ chống tấn công Replay Attack qua bảng băm nonce/hash có thời hạn.
    """
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        if "hash" not in parsed_data:
            return None
        received_hash = parsed_data.pop("hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(calculated_hash, received_hash):
            now = time.time()
            # Dọn dẹp cache hash hết hạn
            for h, exp in list(_telegram_seen_hashes.items()):
                if exp < now:
                    _telegram_seen_hashes.pop(h, None)

            auth_date_str = parsed_data.get("auth_date")
            if not auth_date_str:
                return None
            try:
                auth_date = int(auth_date_str)
                # Tối đa 86400 giây (24h) chống tấn công Replay Attack (+ 300s skew)
                if now - auth_date > 86400 or auth_date > now + 300:
                    logger.warning("Telegram initData đã quá hạn (auth_date=%s)", auth_date)
                    return None
            except ValueError:
                return None

            # Chống Replay Attack: atomic consume
            try:
                _telegram_seen_hashes[received_hash] = auth_date
            except Exception:
                logger.warning("🚨 [SECURITY] Phát hiện tấn công Replay Attack hoặc lỗi lưu replay token (hash=%s)", received_hash)
                return None

            user_raw = parsed_data.get("user")
            if user_raw:
                return json.loads(user_raw)
            return parsed_data
        return None
    except Exception as e:
        logger.warning("Lỗi kiểm tra initData Telegram: %s", e)
        return None


def verify_auth(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
):
    """Authenticate current DB-backed sessions or an active admin via HTTP Basic."""
    if not config.web_auth_enabled:
        return True

    token = request.cookies.get("session_token")
    if not token:
        token = request.headers.get("X-Session-Token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    if token and _current_session_client(token):
        return True

    if credentials:
        with get_db_session() as db:
            admin = db.query(Client).filter(Client.username == credentials.username).first()
            if (
                admin and admin.is_active and admin.role == "admin"
                and verify_password(credentials.password, admin.password_hash)
            ):
                return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Yêu cầu đăng nhập tài khoản quản trị hệ thống bot",
    )


def verify_operator_admin(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
):
    """Authenticate and authorize administrative operators.

    Returns client session dict if authenticated with role == 'admin'.
    Raises HTTP 401 if unauthenticated.
    Raises HTTP 403 if authenticated but role != 'admin'.
    """
    if not config.web_auth_enabled:
        return {"role": "admin", "username": "unauthenticated_admin"}

    # 1. Check Session Token (Cookies, Header, Bearer)
    token = request.cookies.get("session_token")
    if not token:
        token = request.headers.get("X-Session-Token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        client_info = _current_session_client(token)
        if client_info:
            if client_info.get("role") == "admin":
                return client_info
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác này.",
            )

    # 2. Check HTTP Basic Credentials
    if credentials:
        with get_db_session() as db:
            admin = db.query(Client).filter(Client.username == credentials.username).first()
            if admin and admin.is_active and verify_password(credentials.password, admin.password_hash):
                if admin.role == "admin":
                    return {"client_id": admin.id, "username": admin.username, "role": admin.role}
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền thực hiện thao tác này.",
                )

    # 3. Neither valid -> 401
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Yêu cầu đăng nhập tài khoản quản trị hệ thống bot",
    )


def set_bot_context(context: Any):
    global _bot_context
    _bot_context = context


def calculate_evaluation_metrics() -> Dict[str, Any]:
    """Tính toán bộ chỉ số tiến độ sẵn sàng chuyển sang Real Live Trading"""
    history_file = config.trade_history_file
    if not os.path.exists(history_file):
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
            "profit_factor": 0.0, "net_pnl": 0.0, "max_drawdown": 0.0,
            "sample_ok": False, "pf_ok": False, "winrate_ok": False, "dd_ok": True,
            "is_ready": False, "score_percent": 0
        }

    trades = []
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    losses = 0
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            for r in reader:
                try:
                    p = float(r.get("pnl_usdt", 0))
                    trades.append(p)
                    if p > 0:
                        wins += 1
                        gross_profit += p
                    elif p < 0:
                        losses += 1
                        gross_loss += abs(p)

                    cumulative += p
                    if cumulative > peak:
                        peak = cumulative
                    dd = (peak - cumulative) / 1000.0 * 100.0 if cumulative < peak else 0.0
                    if dd > max_dd:
                        max_dd = dd
                except Exception:
                    pass
    except Exception:
        pass

    total_trades = len(trades)
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
    net_pnl = gross_profit - gross_loss

    sample_ok = total_trades >= 15
    pf_ok = profit_factor >= 1.35
    winrate_ok = win_rate >= 45.0
    dd_ok = max_dd <= 5.0

    criteria_met = sum([sample_ok, pf_ok, winrate_ok, dd_ok])
    score_percent = int((criteria_met / 4.0) * 100)
    is_ready = (criteria_met == 4)

    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "net_pnl": round(net_pnl, 2),
        "max_drawdown": round(max_dd, 2),
        "sample_ok": sample_ok,
        "pf_ok": pf_ok,
        "winrate_ok": winrate_ok,
        "dd_ok": dd_ok,
        "criteria_met": criteria_met,
        "score_percent": score_percent,
        "is_ready": is_ready
    }


@app.get("/health")
async def health():
    """Sanitized process-liveness check for the private tunnel origin."""
    return JSONResponse({"status": "ok", "service": "trader-web"})


@app.get("/ready")
async def readiness():
    """Report dependency readiness without collapsing an authoritative HALT into outage."""
    database_access = False
    try:
        from sqlalchemy import text

        with get_db_session() as db:
            db.execute(text("SELECT 1")).fetchone()
        database_access = True
    except Exception:
        database_access = False

    try:
        service_status = _get_execution_client_for_surface("web").query_status()
    except Exception:
        service_status = {"success": False, "service_available": False, "state": "UNKNOWN"}

    service_reachable = bool(service_status.get("service_available"))
    service_state = str(service_status.get("state") or "UNKNOWN").upper()
    recovery_required = bool(service_status.get("recovery_required")) if service_reachable else True
    if not database_access or not service_reachable:
        state = "NOT_READY"
        status_code = 503
    elif recovery_required:
        state = "RECOVERY_REQUIRED"
        status_code = 200
    elif service_state == "HALTED":
        state = "HALTED"
        status_code = 200
    elif service_state == "HEALTHY":
        state = "READY"
        status_code = 200
    else:
        state = "NOT_READY"
        status_code = 503
    return JSONResponse({
        "status": state,
        "service": "trader-web",
        "web_process": "UP",
        "execution_service_reachable": service_reachable,
        "database_access": database_access,
        "execution_service_state": service_state,
    }, status_code=status_code)


@app.post("/api/login")
async def api_login(request: Request, response: Response):
    """Đăng nhập bằng tài khoản và mật khẩu quản trị"""
    try:
        body = await request.json()
        username = str(body.get("username", "")).strip()
        password = str(body.get("password", "")).strip()
        if _login_is_limited(request, username):
            return JSONResponse({"success": False, "code": "LOGIN_RATE_LIMITED", "message": "Quá nhiều lần đăng nhập thất bại. Vui lòng thử lại sau."}, status_code=429)

        with get_db_session() as db:
            admin = db.query(Client).filter(Client.username == username).first()
            authenticated = bool(
                admin and admin.is_active and admin.role == "admin"
                and verify_password(password, admin.password_hash)
            )

        if not authenticated:
            _record_login_failure(request, username)
            return JSONResponse(
                {"success": False, "message": "Sai tên đăng nhập hoặc mật khẩu quản trị!"},
                status_code=401
            )
        _clear_login_failures(request, username)
        token = create_session_token(username, "admin")
        resp = JSONResponse({
            "success": True,
            "username": username,
            "token": token,
            "message": "Đăng nhập thành công!"
        })
        resp.set_cookie(
            key="session_token",
            value=token,
            max_age=30 * 86400,
            path="/",
            samesite="strict",
            httponly=True,
            secure=True,
        )
        return resp
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi đăng nhập: {e}"}, status_code=500)


@app.get("/telegram-mini-app", response_class=HTMLResponse)
async def telegram_mini_app_page():
    """Serve the auth-capable shell; protected APIs remain unavailable until initData verifies."""
    return await dashboard_page()


@app.post("/api/telegram_webapp_auth")
async def api_telegram_webapp_auth(request: Request, response: Response):
    """Xác thực tự động 1-chạm khi mở bằng Telegram Mini App"""
    try:
        body = await request.json()
        init_data = str(body.get("init_data", "")).strip()
        if not init_data:
            return JSONResponse({"success": False, "message": "Không tìm thấy dữ liệu Telegram WebApp initData"}, status_code=400)

        user_data = verify_telegram_webapp_data(init_data, config.telegram_bot_token)
        if not user_data:
            return JSONResponse({"success": False, "message": "Chữ ký xác thực Telegram không hợp lệ"}, status_code=401)

        tg_id = str(user_data.get("id", "")).strip()
        raw_chats = str(config.telegram_chat_id).replace(";", ",").split(",")
        authorized_ids = {c.strip() for c in raw_chats if c.strip()}
        pair_config = getattr(config, "telegram_authorized_pairs", "") or os.getenv(
            "TELEGRAM_AUTHORIZED_PAIRS", ""
        )
        for item in str(pair_config).replace(";", ",").split(","):
            separator = ":" if ":" in item else ("@" if "@" in item else None)
            if separator:
                sender_id, _chat_id = (part.strip() for part in item.split(separator, 1))
                if sender_id:
                    authorized_ids.add(sender_id)
        if tg_id not in authorized_ids:
            return JSONResponse({
                "success": False,
                "message": f"Tài khoản Telegram ID {tg_id} không có quyền quản trị bot!",
            }, status_code=403)
        with get_db_session() as db:
            admin = (
                db.query(Client)
                .filter(Client.role == "admin", Client.is_active.is_(True))
                .order_by(Client.id.asc())
                .first()
            )
            if not admin:
                return JSONResponse({
                    "success": False,
                    "message": "Không có tài khoản quản trị đang hoạt động.",
                }, status_code=503)
            admin_username = admin.username
        token = create_session_token(admin_username, "admin")
        user_name = user_data.get("first_name", f"Admin {tg_id}")
        resp = JSONResponse({
            "success": True,
            "username": f"Telegram: {user_name}",
            "message": f"Chào mừng {user_name} đã kết nối an toàn qua Telegram Mini App!"
        })
        resp.set_cookie(
            key="session_token", value=token, max_age=30 * 86400, path="/",
            samesite="lax", httponly=True, secure=True,
        )
        return resp
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi xác thực Telegram: {e}"}, status_code=500)


@app.get("/api/check_auth")
async def api_check_auth(request: Request):
    """Check the server-managed HttpOnly session."""
    if not config.web_auth_enabled:
        return JSONResponse({"authenticated": True, "username": "admin"})
    token = request.cookies.get("session_token") or request.headers.get("X-Session-Token")
    current = _current_session_client(token)
    if current:
        return JSONResponse({"authenticated": True, "username": current["username"]})
    return JSONResponse({"authenticated": False})


@app.post("/api/logout")
async def api_logout(request: Request, response: Response):
    """Revoke both dashboard and portal credentials supplied by this request."""
    token = request.cookies.get("session_token") or request.headers.get("X-Session-Token")
    if token and token in _active_sessions:
        del _active_sessions[token]
    _revoke_portal_jwt(_portal_jwt_from_request(request))
    resp = JSONResponse({"success": True, "message": "Đã đăng xuất thành công!"})
    resp.delete_cookie(key="session_token", path="/")
    resp.delete_cookie(key="client_token", path="/")
    return resp


@app.get("/api/status", dependencies=[Depends(verify_auth)])
async def get_status():
    """Return authoritative service projections plus explicitly local diagnostics."""
    local_diagnostics = {
        "label": "LOCAL_SIMULATION_DIAGNOSTIC_NOT_TRADING_AUTHORITY",
        "controller_available": _bot_context is not None,
        "is_paused": getattr(_bot_context, "is_paused", None),
        "balance": None,
        "unrealized_pnl": None,
    }
    if _bot_context is not None:
        try:
            if hasattr(_bot_context, "get_current_balance"):
                local_diagnostics["balance"] = _strict_handler_float(
                    _bot_context.get_current_balance(), "diagnostic_balance", positive=True
                )
            if hasattr(_bot_context, "get_total_unrealized_pnl"):
                local_diagnostics["unrealized_pnl"] = _strict_handler_float(
                    _bot_context.get_total_unrealized_pnl(), "diagnostic_unrealized_pnl"
                )
        except (TypeError, ValueError, OverflowError, AttributeError):
            pass

    try:
        client = _get_execution_client_for_surface("web")
        service_status = client.query_status()
        positions = client.query_positions()
        pnl = client.query_pnl()
    except Exception:
        service_status = {"state": "UNKNOWN"}
        positions = None
        pnl = None

    state = str(service_status.get("state", "UNKNOWN")).upper() if isinstance(service_status, dict) else "UNKNOWN"
    global_halt = service_status.get("global_halt") if isinstance(service_status, dict) else None
    status_known = state in {"HEALTHY", "HALTED"} and isinstance(global_halt, bool)
    if not status_known:
        state = "UNKNOWN"
        global_halt = None

    positions_known = not (
        positions is None
        or (isinstance(positions, dict) and positions.get("success") is False)
    )
    authoritative_positions = positions if positions_known else None
    if isinstance(authoritative_positions, dict):
        position_count = len(authoritative_positions)
    elif isinstance(authoritative_positions, list):
        position_count = len(authoritative_positions)
    else:
        position_count = None

    pnl_known = isinstance(pnl, dict) and pnl.get("success") is True
    realized_pnl = pnl.get("total_pnl") if pnl_known else None
    if realized_pnl is not None:
        try:
            realized_pnl = _strict_handler_float(realized_pnl, "realized_pnl")
        except (TypeError, ValueError, OverflowError):
            realized_pnl = None
            pnl_known = False

    halt_generation = _halt_generation_from(service_status) if status_known else None
    recovery_required = bool(service_status.get("recovery_required", False)) if status_known else False
    resume_allowed = bool(
        status_known
        and global_halt
        and halt_generation is not None
        and halt_generation > 0
        and not recovery_required
        and state != "UNKNOWN"
    )
    return JSONResponse({
        "status": state,
        "environment": getattr(config, "trader_environment", "OFFLINE"),
        "projection_source": "EXECUTION_SERVICE" if status_known else "UNKNOWN",
        "is_paused": global_halt,
        "halt_generation": halt_generation,
        "halt_reason": service_status.get("halt_reason") if status_known else "Execution Service unavailable",
        "recovery_required": recovery_required,
        "resume_allowed": resume_allowed,
        "balance": None,
        "initial_balance": None,
        "roi_percent": None,
        "open_positions_count": position_count,
        "positions": authoritative_positions,
        "open_positions": authoritative_positions,
        "total_unrealized_pnl": None,
        "realized_pnl": realized_pnl,
        "pnl_state": "KNOWN_VALUE" if pnl_known else "UNKNOWN",
        "version": config.app_version,
        "mode": "SIMULATION" if config.dry_run else "LIVE",
        "trading_mode": config.trading_mode,
        "max_positions": config.max_concurrent_positions,
        "active_strategy": getattr(config, "active_strategy", "AUTO_DYNAMIC"),
        "real_trading_hard_cap": getattr(config, "real_trading_hard_cap", 100.0),
        "leverage": config.leverage,
        "margin_type": config.margin_type,
        "risk_percent": config.risk_per_trade_percent,
        "use_trailing_stop": config.use_trailing_stop,
        "trailing_activation_rr": config.trailing_activation_rr,
        "max_scan_pairs": config.max_scan_pairs,
        "health": service_status.get("dimensions") if status_known else None,
        "evaluation": calculate_evaluation_metrics(),
        "local_diagnostics": local_diagnostics,
    }, status_code=200 if status_known else 503)
@app.get("/api/scanner_radar", dependencies=[Depends(verify_auth)])
async def get_scanner_radar():
    """Return scanner data or an explicit disabled state."""
    if _bot_context is None or not hasattr(_bot_context, "scanner") or not _bot_context.scanner:
        return JSONResponse({
            "success": True,
            "status": "DISABLED_OFFLINE",
            "radar": [],
            "mode": config.trader_environment,
            "scanned_count": 0,
            "message": "Scanner is disabled in the canonical OFFLINE deployment.",
        })
    radar_list = getattr(_bot_context.scanner, "last_scanned_radar", [])
    return JSONResponse({
        "success": True,
        "status": "ACTIVE",
        "radar": radar_list,
        "mode": config.trading_mode,
        "scanned_count": len(radar_list),
        "updated_at": datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M:%S (VN)"),
    })


@app.get("/api/ai_mascot", dependencies=[Depends(verify_auth)])
async def get_ai_mascot():
    """Return AI status without claiming a disabled provider is active."""
    if _bot_context and hasattr(_bot_context, "ai_copilot") and _bot_context.ai_copilot:
        commentary = _bot_context.ai_copilot.get_speech_commentary(_bot_context)
        commentary["ai_connected"] = _bot_context.ai_copilot.is_connected
        return JSONResponse(commentary)
    return JSONResponse({
        "speech": "Execution Service đang hoạt động ở chế độ OFFLINE. AI Copilot chưa được bật.",
        "mood": "standby",
        "mood_title": "AI DISABLED / OFFLINE",
        "glow_color": "#F0B90B",
        "ai_connected": False,
        "status": "DISABLED_OFFLINE",
    })


@app.post("/api/ai_chat", dependencies=[Depends(verify_auth)])
async def ai_chat(request: Request):
    """Use AI only when an explicitly configured supervised context exists."""
    try:
        data = await request.json()
        user_message = (data.get("message") or data.get("query") or "").strip()
        if not user_message:
            return JSONResponse({"reply": "Sếp cần em hỗ trợ gì về thị trường hoặc danh mục lệnh ạ?", "ai_connected": False})
        if not (_bot_context and hasattr(_bot_context, "ai_copilot") and _bot_context.ai_copilot):
            return JSONResponse({"success": False, "code": "AI_DISABLED_OFFLINE", "reply": "AI Copilot is disabled in the canonical OFFLINE deployment.", "ai_connected": False}, status_code=503)
        reply = await asyncio.to_thread(_bot_context.ai_copilot.chat, user_message, _bot_context)
        return JSONResponse({"success": True, "reply": reply, "ai_connected": _bot_context.ai_copilot.is_connected})
    except Exception:
        logger.exception("AI chat request failed")
        return JSONResponse({"success": False, "code": "AI_REQUEST_FAILED", "reply": "AI request failed.", "ai_connected": False}, status_code=503)


_settings_file_lock = threading.Lock()


def _persist_setting_to_env(key: str, val: str):
    """Persist one validated setting to the selected runtime env atomically."""
    key = str(key).strip()
    value = str(val)
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
        raise ValueError("Invalid runtime setting key")
    if any(char in value for char in ("\r", "\n", "\x00")):
        raise ValueError("Runtime setting value must be one line")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file = os.getenv("TRADER_RUNTIME_ENV_FILE", "").strip()
    env_file = env_file or os.path.join(root, ".runtime", "trader-stack.env")
    if not os.path.isabs(env_file):
        env_file = os.path.join(root, env_file)
    os.makedirs(os.path.dirname(env_file), exist_ok=True)
    with _settings_file_lock:
        lines = []
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        new_lines = []
        found = False
        for line in lines:
            if line.strip().startswith(f"{key}=") or line.strip() == key:
                new_lines.append(f"{key}={value}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"
            new_lines.append(f"{key}={value}\n")
        temporary = f"{env_file}.tmp.{os.getpid()}.{secrets.token_hex(6)}"
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, env_file)
            os.chmod(env_file, 0o600)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


@app.post("/api/update_settings", dependencies=[Depends(verify_auth)])
async def update_settings(request: Request):
    """API điều chỉnh cấu hình thời gian thực (Live Settings) không cần restart bot"""
    try:
        data = await request.json()
        parsed_financial = {}
        if "leverage" in data:
            parsed_financial["leverage"] = _strict_handler_int(data["leverage"], "leverage", positive=True)
        if "risk_percent" in data:
            parsed_financial["risk_percent"] = _strict_handler_float(data["risk_percent"], "risk_percent", positive=True)
        if "adx_min" in data:
            parsed_financial["adx_min"] = _strict_handler_float(data["adx_min"], "adx_min", positive=True)
        if "real_trading_hard_cap" in data:
            parsed_financial["real_trading_hard_cap"] = _strict_handler_float(
                data["real_trading_hard_cap"], "real_trading_hard_cap", positive=True
            )
        if "leverage" in parsed_financial and not 1 <= parsed_financial["leverage"] <= 20:
            raise ValueError("leverage must be between 1 and 20")
        if "risk_percent" in parsed_financial and not 0.1 <= parsed_financial["risk_percent"] <= 5.0:
            raise ValueError("risk_percent must be between 0.1 and 5.0")
        if "adx_min" in parsed_financial and not 10.0 <= parsed_financial["adx_min"] <= 40.0:
            raise ValueError("adx_min must be between 10 and 40")
        if "real_trading_hard_cap" in parsed_financial and parsed_financial["real_trading_hard_cap"] < 10.0:
            raise ValueError("real_trading_hard_cap must be at least 10")
        updated_fields = []

        if "trading_mode" in data and data["trading_mode"] in ["MARKET_ALL", "BLUECHIP_ONLY", "CUSTOM"]:
            config.trading_mode = data["trading_mode"]
            _persist_setting_to_env("TRADING_MODE", config.trading_mode)
            updated_fields.append(f"Chế độ: {config.trading_mode}")

        if "leverage" in data:
            lev = parsed_financial["leverage"]
            if 1 <= lev <= 20:
                config.leverage = lev
                _persist_setting_to_env("LEVERAGE", str(lev))
                updated_fields.append(f"Đòn bẩy: {lev}x")

        if "risk_percent" in data:
            risk = parsed_financial["risk_percent"]
            if 0.1 <= risk <= 5.0:
                config.risk_per_trade_percent = risk
                _persist_setting_to_env("RISK_PER_TRADE_PERCENT", str(risk))
                updated_fields.append(f"Rủi ro: {risk}%")

        if "use_trailing_stop" in data:
            config.use_trailing_stop = bool(data["use_trailing_stop"])
            _persist_setting_to_env("USE_TRAILING_STOP", str(config.use_trailing_stop))
            state = "BẬT" if config.use_trailing_stop else "TẮT"
            updated_fields.append(f"Trailing Stop: {state}")

        if "adx_min" in data:
            adx = parsed_financial["adx_min"]
            if 10.0 <= adx <= 40.0:
                config.adx_min = adx
                _persist_setting_to_env("ADX_MIN", str(adx))
                if _bot_context and hasattr(_bot_context, "strategy") and _bot_context.strategy:
                    _bot_context.strategy.adx_min = adx
                updated_fields.append(f"ADX: {adx}")

        if "deepseek_api_key" in data:
            key_val = str(data["deepseek_api_key"]).strip()
            config.deepseek_api_key = key_val
            _persist_setting_to_env("DEEPSEEK_API_KEY", key_val)
            _persist_setting_to_env("DEEPSEEK_BASE_URL", getattr(config, "deepseek_base_url", "https://tokenharbor.ai/v1/chat/completions"))
            _persist_setting_to_env("DEEPSEEK_MODEL", getattr(config, "deepseek_model", "deepseek-v4.1-flash:free"))
            if _bot_context and hasattr(_bot_context, "ai_copilot") and _bot_context.ai_copilot:
                _bot_context.ai_copilot.config.deepseek_api_key = key_val
            updated_fields.append("DeepSeek Key: " + ("Đã cập nhật" if key_val else "Đã xóa"))

        if "gemini_api_key" in data:
            key_val = str(data["gemini_api_key"]).strip()
            config.gemini_api_key = key_val
            config.ai_api_key = key_val
            _persist_setting_to_env("GEMINI_API_KEY", key_val)
            _persist_setting_to_env("AI_API_KEY", key_val)
            _persist_setting_to_env("GEMINI_MODEL", getattr(config, "gemini_model", "gemini-2.5-flash"))
            if _bot_context and hasattr(_bot_context, "ai_copilot") and _bot_context.ai_copilot:
                _bot_context.ai_copilot.config.gemini_api_key = key_val
                _bot_context.ai_copilot.config.ai_api_key = key_val
            updated_fields.append("Gemini Key: " + ("Đã cập nhật" if key_val else "Đã xóa"))

        if "ai_api_key" in data and "gemini_api_key" not in data:
            key_val = str(data["ai_api_key"]).strip()
            config.ai_api_key = key_val
            config.gemini_api_key = key_val
            _persist_setting_to_env("AI_API_KEY", key_val)
            _persist_setting_to_env("GEMINI_API_KEY", key_val)
            if _bot_context and hasattr(_bot_context, "ai_copilot") and _bot_context.ai_copilot:
                _bot_context.ai_copilot.config.ai_api_key = key_val
                _bot_context.ai_copilot.config.gemini_api_key = key_val
            updated_fields.append("AI Key: " + ("Đã cập nhật" if key_val else "Đã xóa"))

        if "trade_direction" in data:
            direction = str(data["trade_direction"]).strip().upper()
            if direction in ["AUTO", "LONG_ONLY", "SHORT_ONLY", "BOTH"]:
                config.trade_direction = direction
                _persist_setting_to_env("TRADE_DIRECTION", direction)
                updated_fields.append(f"Chiều đánh: {direction}")

        if "enable_dynamic_leverage" in data:
            config.enable_dynamic_leverage = bool(data["enable_dynamic_leverage"])
            _persist_setting_to_env("ENABLE_DYNAMIC_LEVERAGE", str(config.enable_dynamic_leverage))
            updated_fields.append(f"Đòn bẩy động: {'BẬT' if config.enable_dynamic_leverage else 'TẮT'}")

        if "enable_btc_regime_filter" in data:
            config.enable_btc_regime_filter = bool(data["enable_btc_regime_filter"])
            _persist_setting_to_env("ENABLE_BTC_REGIME_FILTER", str(config.enable_btc_regime_filter))
            updated_fields.append(f"Lọc chế độ BTC: {'BẬT' if config.enable_btc_regime_filter else 'TẮT'}")

        if "ai_provider" in data:
            prov = str(data["ai_provider"]).strip().lower()
            if prov in ["dual", "gemini", "deepseek"]:
                config.ai_provider = prov
                _persist_setting_to_env("AI_PROVIDER", prov)
                if _bot_context and hasattr(_bot_context, "ai_copilot") and _bot_context.ai_copilot:
                    _bot_context.ai_copilot.config.ai_provider = prov
                updated_fields.append(f"AI Provider: {prov}")

        if "active_strategy" in data:
            strat = str(data["active_strategy"]).strip().upper()
            if strat in ["AUTO_DYNAMIC", "TREND_PULLBACK", "BREAKOUT", "MEAN_REVERSION"]:
                config.active_strategy = strat
                _persist_setting_to_env("ACTIVE_STRATEGY", strat)
                if _bot_context and hasattr(_bot_context, "scanner") and _bot_context.scanner:
                    _bot_context.scanner.active_strategy = strat
                updated_fields.append(f"Chiến lược: {strat}")

        if "real_trading_hard_cap" in data:
            cap = parsed_financial["real_trading_hard_cap"]
            if cap >= 10.0:
                config.real_trading_hard_cap = cap
                _persist_setting_to_env("REAL_TRADING_HARD_CAP", str(cap))
                updated_fields.append(f"Giới hạn vốn: ${cap:,.0f}")

        msg = "Đã cập nhật cài đặt thành công: " + ", ".join(updated_fields) if updated_fields else "Không có thay đổi nào"
        return JSONResponse({
            "success": True,
            "message": msg,
            "current_settings": {
                "trading_mode": config.trading_mode,
                "active_strategy": getattr(config, "active_strategy", "AUTO_DYNAMIC"),
                "real_trading_hard_cap": getattr(config, "real_trading_hard_cap", 100.0),
                "leverage": config.leverage,
                "risk_percent": config.risk_per_trade_percent,
                "use_trailing_stop": config.use_trailing_stop,
                "adx_min": config.adx_min,
                "ai_connected": bool(config.ai_api_key)
            }
        })
    except Exception as e:
        return JSONResponse(
            {"success": False, "message": f"Lỗi cập nhật cấu hình: {e}"}, status_code=400
        )


@app.get("/api/history", dependencies=[Depends(verify_auth)])
async def get_history():
    """API trả về lịch sử giao dịch và chuỗi dữ liệu vẽ biểu đồ Equity Curve (Giờ Việt Nam UTC+7)"""
    history_file = config.trade_history_file
    if not os.path.exists(history_file):
        return JSONResponse({"trades": [], "summary": {"total": 0, "win_rate": 0, "net_pnl": 0}, "chart_data": []})

    trades = []
    wins = 0
    losses = 0
    total_net_pnl = 0.0
    chart_data = []
    cum_pnl = 0.0

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            for idx, row in enumerate(reader):
                try:
                    vn_ts = normalize_vn_time(row.get("timestamp", ""))
                    row["timestamp"] = vn_ts
                    pnl = float(row.get("pnl_usdt", 0))
                    cum_pnl += pnl

                    # Rút gọn nhãn thời gian cho biểu đồ: lấy HH:MM:SS
                    time_label = vn_ts
                    clean_ts = vn_ts.replace(" (VN)", "").strip()
                    if " " in clean_ts:
                        time_label = clean_ts.split(" ")[-1]

                    chart_data.append({
                        "trade_num": idx + 1,
                        "timestamp": time_label,
                        "pnl": round(pnl, 2),
                        "cum_pnl": round(cum_pnl, 2),
                        "symbol": row.get("symbol", "")
                    })
                except Exception:
                    pass

            for row in reversed(reader):
                try:
                    row["timestamp"] = normalize_vn_time(row.get("timestamp", ""))
                    pnl = float(row.get("pnl_usdt", 0))
                    total_net_pnl += pnl
                    if pnl > 0:
                        wins += 1
                    elif pnl < 0:
                        losses += 1
                    trades.append(row)
                except Exception:
                    pass

        total_closed = len(trades)
        win_rate = (wins / total_closed * 100.0) if total_closed > 0 else 0.0

        return JSONResponse({
            "trades": trades[:50],
            "summary": {
                "total": total_closed,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 1),
                "net_pnl": round(total_net_pnl, 2)
            },
            "chart_data": chart_data
        })
    except Exception as e:
        return JSONResponse({"error": str(e), "trades": [], "chart_data": []})


@app.post("/api/toggle_pause", dependencies=[Depends(verify_operator_admin)])
async def toggle_pause():
    # Standalone web control is valid when the authoritative service is reachable.
    client = _get_execution_client_for_surface("operator")
    status_view = client.query_status()
    state = str(status_view.get("state", "UNKNOWN")).upper() if isinstance(status_view, dict) else "UNKNOWN"
    if state not in {"HEALTHY", "HALTED"}:
        return JSONResponse({"success": False, "message": "Execution Service state UNKNOWN"}, status_code=503)
    return _set_durable_web_pause(state == "HEALTHY")

def _get_execution_client_for_surface(principal: str = "web"):
    from core.execution_service.client import ExecutionServiceClient
    cfg = getattr(_bot_context, "config", None) or config
    svc_host = getattr(cfg, "execution_service_host", "127.0.0.1")
    svc_port = getattr(cfg, "execution_service_port", 50051)
    if principal == "webhook":
        token = getattr(cfg, "ipc_token_webhook", "")
        canonical = "webhook-client"
    elif principal in ("operator", "halt", "resume"):
        token = getattr(cfg, "ipc_token_operator", "")
        canonical = "operator-client"
    else:
        token = getattr(cfg, "ipc_token_web", "")
        canonical = "web-client"
    attr_name = f"_exec_client_{principal}"
    if _bot_context and getattr(_bot_context, attr_name, None):
        return getattr(_bot_context, attr_name)
    client = ExecutionServiceClient(
        host=svc_host, port=svc_port, auth_token=token, principal=canonical
    )
    if _bot_context:
        setattr(_bot_context, attr_name, client)
    return client

def _halt_generation_from(value: Any) -> Optional[int]:
    data = value.data if hasattr(value, "data") else value
    if not isinstance(data, dict):
        return None
    generation = data.get("halt_generation", data.get("generation"))
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        return None
    return generation


def _set_durable_web_pause(paused: bool) -> JSONResponse:
    """Use generation-bound HALT/RESUME and mirror only confirmed authority."""
    global _web_halt_generation
    try:
        client = _get_execution_client_for_surface("operator")
        if paused:
            result = client.set_halt(reason="Web operator pause", source="web")
            generation = _halt_generation_from(result) or _halt_generation_from(client.query_status())
        else:
            status_view = client.query_status()
            if not isinstance(status_view, dict):
                return JSONResponse({"success": False, "message": "Execution Service status unavailable"}, status_code=503)
            generation = _halt_generation_from(status_view)
            if generation is None:
                return JSONResponse(
                    {"success": False, "message": "HALT generation unavailable"}, status_code=409
                )
            result = client.resume(expected_halt_generation=generation, source="web")
    except Exception as exc:
        return JSONResponse({"success": False, "message": f"Execution Service error: {exc}"}, status_code=503)
    if not result or not result.success:
        error = result.error if result else "UNKNOWN"
        return JSONResponse({"success": False, "message": f"Execution Service error: {error}"}, status_code=503)
    if paused and generation is None:
        return JSONResponse({"success": False, "message": "HALT generation unavailable"}, status_code=503)
    _web_halt_generation = generation if paused else None
    if _bot_context is not None:
        _bot_context.is_paused = paused
    return JSONResponse({
        "success": True,
        "is_paused": paused,
        "halt_generation": generation,
        "authoritative_state": "HALTED" if paused else "RESUMED",
        "message": "Execution Service đã xác nhận trạng thái bền vững",
    })

@app.post("/api/panic_close", dependencies=[Depends(verify_auth)])
async def panic_close():
    # No local fallback: standalone web routes directly to the authenticated service client.
    exec_client = _get_execution_client_for_surface("web")
    if exec_client is not None:
        cmd_res = exec_client.emergency_close_all(reason="Đóng khẩn cấp từ Web Dashboard", source="web")
        if not cmd_res.success:
            return JSONResponse({"success": False, "message": f"Execution Service error: {cmd_res.error}"}, status_code=503)
        return JSONResponse({"success": True, "message": "Đã thực thi panic close qua Execution Service", "receipt": cmd_res.execution_receipt_id})
    return JSONResponse({"success": False, "message": "Execution Service unavailable (Hard Cutover)"}, status_code=503)


@app.post("/api/close_single", dependencies=[Depends(verify_auth)])
async def close_single(request: Request):
    """Đóng một vị thế cụ thể theo symbol"""
    # Standalone close remains service-only.
    try:
        body = await request.json()
        symbol = body.get("symbol")
        if not symbol:
            return JSONResponse({"success": False, "message": "Thiếu mã symbol"})

        exec_client = _get_execution_client_for_surface("web")
        if exec_client is not None:
            cmd_res = exec_client.close_position(symbol=symbol, reason="Đóng thủ công từ Web Dashboard", source="web")
            if not cmd_res.success:
                return JSONResponse({"success": False, "message": f"Execution Service error: {cmd_res.error}"}, status_code=503)
            return JSONResponse({"success": True, "message": f"Đã đóng {symbol} qua Execution Service", "receipt": cmd_res.execution_receipt_id})

        return JSONResponse({"success": False, "message": "Execution Service unavailable (Hard Cutover)"}, status_code=503)
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi: {e}"})


@app.post("/api/pause", dependencies=[Depends(verify_operator_admin)])
async def api_pause(request: Request):
    """Durably halt entries from Web/Desktop/Mobile with authoritative generation confirmation."""
    reason = "Operator manual pause"
    source = "web"
    try:
        body = await request.json()
        if isinstance(body, dict):
            raw_reason = body.get("reason")
            if raw_reason and isinstance(raw_reason, str):
                reason = raw_reason.strip()[:200]
            raw_source = body.get("source")
            if raw_source and isinstance(raw_source, str):
                source = raw_source.strip()[:50]
    except Exception:
        pass

    client = _get_execution_client_for_surface("operator")
    try:
        result = client.set_halt(reason=reason, source=source)
        generation = _halt_generation_from(result) or _halt_generation_from(client.query_status())
    except Exception as exc:
        return JSONResponse({"success": False, "message": f"Execution Service error: {exc}"}, status_code=503)

    if not result or not result.success:
        error = result.error if result else "UNKNOWN"
        return JSONResponse({"success": False, "message": f"Execution Service error: {error}"}, status_code=503)

    if generation is None:
        return JSONResponse({"success": False, "message": "HALT generation unavailable"}, status_code=503)

    global _web_halt_generation
    _web_halt_generation = generation
    if _bot_context is not None:
        _bot_context.is_paused = True

    return JSONResponse({
        "success": True,
        "is_paused": True,
        "halt_generation": generation,
        "authoritative_state": "HALTED",
        "message": "Execution Service đã xác nhận dừng bền vững",
    })


@app.post("/api/resume", dependencies=[Depends(verify_operator_admin)])
async def api_resume(request: Request):
    """Durably resume entries from Web/Desktop/Mobile requiring CAS expected_halt_generation."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"success": False, "code": "INVALID_JSON", "message": "Yêu cầu cung cấp dữ liệu JSON"},
            status_code=400,
        )

    if not isinstance(body, dict) or "expected_halt_generation" not in body:
        return JSONResponse(
            {
                "success": False,
                "code": "MISSING_HALT_GENERATION",
                "message": "Yêu cầu cung cấp expected_halt_generation hợp lệ",
            },
            status_code=400,
        )

    expected_generation = body.get("expected_halt_generation")
    if isinstance(expected_generation, bool) or not isinstance(expected_generation, int) or expected_generation < 1:
        return JSONResponse(
            {
                "success": False,
                "code": "INVALID_HALT_GENERATION",
                "message": "expected_halt_generation phải là số nguyên dương",
            },
            status_code=400,
        )

    source = "web"
    raw_source = body.get("source")
    if raw_source and isinstance(raw_source, str):
        source = raw_source.strip()[:50]

    client = _get_execution_client_for_surface("operator")
    try:
        status_view = client.query_status()
    except Exception as exc:
        return JSONResponse(
            {"success": False, "code": "SERVICE_UNAVAILABLE", "message": f"Execution Service unavailable: {exc}"},
            status_code=503,
        )

    if not status_view or not isinstance(status_view, dict):
        return JSONResponse(
            {"success": False, "code": "SERVICE_UNAVAILABLE", "message": "Execution Service unavailable"},
            status_code=503,
        )

    service_state = str(status_view.get("state", "UNKNOWN")).upper()
    if service_state == "UNKNOWN":
        return JSONResponse(
            {"success": False, "code": "SERVICE_UNKNOWN", "message": "Execution Service state is UNKNOWN"},
            status_code=503,
        )

    is_paused = bool(status_view.get("global_halt"))
    if not is_paused:
        return JSONResponse(
            {"success": False, "code": "NO_ACTIVE_HALT", "message": "Hệ thống hiện không trong trạng thái HALT"},
            status_code=409,
        )

    recovery_required = bool(status_view.get("recovery_required", False))
    if recovery_required:
        return JSONResponse(
            {
                "success": False,
                "code": "RECOVERY_REQUIRED",
                "message": "Không thể RESUME: Yêu cầu khắc phục trạng thái khẩn cấp (recovery_required=True)",
            },
            status_code=409,
        )

    current_generation = _halt_generation_from(status_view)
    if current_generation is None or current_generation != expected_generation:
        return JSONResponse(
            {
                "success": False,
                "code": "STALE_HALT_GENERATION",
                "current_generation": current_generation,
                "expected_generation": expected_generation,
                "message": f"Không thể RESUME: Thế hệ HALT đã thay đổi (hiện tại: {current_generation}, yêu cầu: {expected_generation})",
            },
            status_code=409,
        )

    try:
        if hasattr(client, "resume"):
            result = client.resume(expected_halt_generation=expected_generation, source=source)
        elif hasattr(client, "_command"):
            from core.execution_service.client import CommandType
            result = client._command(
                CommandType.RESUME,
                {"expected_halt_generation": expected_generation},
                source,
                None,
            )
        else:
            raise AttributeError("Execution client does not support resume")
    except Exception as exc:
        return JSONResponse(
            {"success": False, "code": "SERVICE_ERROR", "message": f"Execution Service error: {exc}"},
            status_code=503,
        )

    if not result or not result.success:
        error = result.error if result else "UNKNOWN"
        err_str = str(error).lower()
        if "generation changed" in err_str or "safety" in err_str:
            return JSONResponse(
                {"success": False, "code": "STALE_HALT_GENERATION", "message": f"Execution Service rejected RESUME: {error}"},
                status_code=409,
            )
        return JSONResponse(
            {"success": False, "code": "RESUME_FAILED", "message": f"Execution Service error: {error}"},
            status_code=503,
        )

    global _web_halt_generation
    _web_halt_generation = None
    if _bot_context is not None:
        _bot_context.is_paused = False

    return JSONResponse({
        "success": True,
        "is_paused": False,
        "halt_generation": None,
        "authoritative_state": "RESUMED",
        "message": "Execution Service đã xác nhận kích hoạt lại thành công",
    })


@app.post("/api/close_all_positions", dependencies=[Depends(verify_auth)])
async def api_close_all_positions():
    """Đóng sạch vị thế khẩn cấp từ Desktop/Mobile"""
    return await panic_close()


@app.post("/api/close_position", dependencies=[Depends(verify_auth)])
async def api_close_position(request: Request):
    """Đóng một vị thế cụ thể (hỗ trợ cả query param và JSON body)"""
    # Standalone close remains service-only.
    try:
        sym = request.query_params.get("symbol")
        if not sym:
            try:
                body = await request.json()
                sym = body.get("symbol")
            except Exception:
                pass
        if not sym:
            return JSONResponse({"success": False, "message": "Thiếu mã symbol"})

        sym = sym.upper()
        exec_client = _get_execution_client_for_surface("web")
        if exec_client is not None:
            cmd_res = exec_client.close_position(symbol=sym, reason="Đóng từ Desktop/Mobile App", source="web")
            if not cmd_res.success:
                return JSONResponse({"success": False, "message": f"Execution Service error: {cmd_res.error}"}, status_code=503)
            return JSONResponse({"success": True, "message": f"Đã đóng {sym} qua Execution Service", "receipt": cmd_res.execution_receipt_id})

        return JSONResponse({"success": False, "message": "Execution Service unavailable (Hard Cutover)"}, status_code=503)
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi: {e}"})


@app.get("/api/radar", dependencies=[Depends(verify_auth)])
async def api_radar():
    """Return scanner data with explicit OFFLINE availability state."""
    res = await get_scanner_radar()
    try:
        data = json.loads(res.body.decode())
        return JSONResponse({
            "success": True,
            "status": data.get("status", "ACTIVE"),
            "scanner_available": data.get("status") != "DISABLED_OFFLINE",
            "pairs": data.get("radar", []),
            "message": data.get("message"),
        })
    except Exception:
        return res


@app.get("/api/download_csv", dependencies=[Depends(verify_auth)])
async def download_csv():
    """Tải xuống tệp lịch sử giao dịch trade_history.csv"""
    history_file = config.trade_history_file
    if os.path.exists(history_file):
        return FileResponse(
            path=history_file,
            filename=f"trade_history_{datetime.now(VIETNAM_TZ).strftime('%Y%m%d_%H%M%S')}.csv",
            media_type="text/csv"
        )
    raise HTTPException(status_code=404, detail="Chưa có file lịch sử giao dịch")


@app.get("/api/download_state", dependencies=[Depends(verify_auth)])
async def download_state():
    """Tải xuống tệp trạng thái bot_state.json"""
    state_file = config.state_file
    if os.path.exists(state_file):
        return FileResponse(
            path=state_file,
            filename=f"bot_state_{datetime.now(VIETNAM_TZ).strftime('%Y%m%d_%H%M%S')}.json",
            media_type="application/json"
        )
    raise HTTPException(status_code=404, detail="Chưa có file trạng thái")


@app.get("/api/logs", dependencies=[Depends(verify_auth)])
async def api_get_logs(lines: int = 150):
    """Return logs from the canonical supervised OFFLINE stack."""
    lines = max(1, min(int(lines), 500))
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runtime_file = os.getenv("TRADER_RUNTIME_ENV_FILE", "").strip()
    runtime = os.path.dirname(runtime_file) if runtime_file else os.path.join(root, ".runtime")
    candidates = [
        os.path.join(runtime, "logs", "web.log"),
        os.path.join(runtime, "logs", "execution-service.log"),
        os.path.join(runtime, "logs", "telegram.log"),
    ]
    result_lines = []
    found = []
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                result_lines.extend(f.readlines()[-lines:])
            found.append(os.path.basename(path))
        except OSError:
            continue
    result_lines = sorted(result_lines)[-lines:] if result_lines else []
    return JSONResponse({
        "success": True,
        "source": found or ["none"],
        "lines": [line.rstrip() for line in result_lines] or ["No recent supervised stack logs."],
    })


@app.get("/logo.png")
@app.get("/favicon.ico")
async def get_logo():
    """Trả về hình ảnh Logo & Avatar chính thức của bot"""
    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Chưa tìm thấy file logo")


@app.get("/mascot_preview.jpg")
async def get_mascot_preview():
    """Trả về hình ảnh linh vật Mascot Cyber Fox 3D chất lượng cao"""
    img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mascot_preview.jpg")
    if os.path.exists(img_path):
        return FileResponse(img_path, media_type="image/jpeg")
@app.get("/manifest.json")
async def manifest():
    """PWA Web App Manifest cho trải nghiệm Mobile App native"""
    return JSONResponse({
        "name": "Binance Quant Bot 3.0 Ultra Pro",
        "short_name": "QuantPro",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#080a0f",
        "theme_color": "#F0B90B",
        "description": "Hệ thống giao dịch định lượng Binance Futures tự động cao cấp",
        "icons": [
            {
                "src": "/logo.png",
                "sizes": "192x192 512x512",
                "type": "image/png"
            }
        ]
    })


@app.get("/sw.js")
async def service_worker():
    """PWA Service Worker hỗ trợ cài đặt ứng dụng độc lập trên Mobile"""
    js_content = """
self.addEventListener('install', (e) => {
    self.skipWaiting();
});
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
        .then(() => self.registration.unregister())
        .then(() => clients.claim())
    );
});
self.addEventListener('fetch', (e) => {
    // Pass through direct to network
});
"""
    return Response(content=js_content, media_type="application/javascript")


@app.get("/api/klines", dependencies=[Depends(verify_auth)])
async def get_klines(symbol: str = "BTCUSDT", interval: str = "15m", limit: int = 100):
    """Lấy dữ liệu nến klines phục vụ biểu đồ TradingView Lightweight Charts"""
    try:
        market_base = (
            "https://testnet.binancefuture.com/fapi/v1"
            if str(getattr(config, "market_data_environment", "PRODUCTION")).upper() == "TESTNET"
            else "https://fapi.binance.com/fapi/v1"
        )
        url = f"{market_base}/klines?symbol={symbol}&interval={interval}&limit={min(200, max(30, limit))}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        candles = []
        for k in data:
            candles.append({
                "time": int(k[0] // 1000),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            })

        pos_info = None
        if _bot_context and hasattr(_bot_context, "order_manager"):
            pos = _bot_context.order_manager.active_positions.get(symbol)
            if pos:
                pos_info = {
                    "side": pos.get("side"),
                    "entry_price": float(pos.get("entry_price", 0)),
                    "stop_loss": float(pos.get("stop_loss", 0)),
                    "take_profit": float(pos.get("take_profit", 0)),
                    "qty": float(pos.get("qty", 0)),
                    "margin": float(pos.get("margin", 0))
                }

        return JSONResponse({"success": True, "symbol": symbol, "interval": interval, "candles": candles, "position": pos_info})
    except Exception as e:
        return JSONResponse({"success": False, "symbol": symbol, "interval": interval, "candles": [], "position": None, "error": str(e)})


@app.post("/api/manual_order", dependencies=[Depends(verify_auth)])
async def manual_order(request: Request):
    """Submit a manual entry only from a separately supervised strategy context."""
    if _bot_context is None or not hasattr(_bot_context, "order_manager"):
        return JSONResponse({"success": False, "code": "STRATEGY_CONTEXT_DISABLED_OFFLINE", "message": "Manual entry is unavailable in OFFLINE monitoring mode."}, status_code=503)

    try:
        data = await request.json()
        symbol = str(data.get("symbol", "")).strip().upper()
        side = str(data.get("side", "")).strip().upper()
        stop_loss = data.get("stop_loss")
        qty = data.get("qty")
        try:
            stop_loss = _strict_handler_float(stop_loss, "stop_loss", positive=True)
            qty = _strict_handler_float(qty, "qty", positive=True)
        except (TypeError, ValueError, OverflowError):
            return JSONResponse(
                {"success": False, "code": "PROTECTION_OR_SIZE_REQUIRED",
                 "message": "Explicit valid stop_loss and qty are required."},
                status_code=400,
            )
        if not symbol or side not in ["BUY", "SELL", "LONG", "SHORT"]:
            return JSONResponse({"success": False, "message": "Dữ liệu symbol hoặc side không hợp lệ"})
        if stop_loss <= 0 or qty <= 0:
            return JSONResponse(
                {"success": False, "code": "PROTECTION_OR_SIZE_REQUIRED",
                 "message": "Explicit positive stop_loss and qty are required."}, status_code=400
            )

        norm_side = "BUY" if side in ["BUY", "LONG"] else "SELL"
        lev = _strict_handler_int(data.get("leverage", config.leverage), "leverage", positive=True)
        if not 1 <= lev <= 20:
            return JSONResponse({"success": False, "message": "leverage must be between 1 and 20"}, status_code=400)
        bal = _strict_handler_float(_bot_context.get_current_balance(), "capital", positive=True)
        entry_price = (
            _strict_handler_float(data["entry_price"], "entry_price", positive=True)
            if "entry_price" in data else 0.0
        )
        take_profit = (
            _strict_handler_float(data["take_profit"], "take_profit", positive=True)
            if "take_profit" in data else None
        )
        exec_client = _get_execution_client_for_surface("web")
        if exec_client is not None:
            cmd_res = exec_client.open_position(
                symbol=symbol,
                side=norm_side,
                qty=qty,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                leverage=lev,
                total_capital=bal,
                source="web",
            )
            if not cmd_res.success:
                return JSONResponse({"success": False, "message": f"Execution Service error: {cmd_res.error}"}, status_code=503)
            return JSONResponse({"success": True, "symbol": symbol, "side": norm_side, "receipt": cmd_res.execution_receipt_id})

        return JSONResponse({"success": False, "message": "Execution Service unavailable (Hard Cutover)"}, status_code=503)
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi thực thi lệnh: {e}"}, status_code=400)


@app.get("/api/analytics", dependencies=[Depends(verify_auth)])
async def get_analytics():
    """Return symbol analytics from the authoritative Execution Service ledger."""
    try:
        pnl = _get_execution_client_for_surface("web").query_pnl()
        ledger = pnl.get("pnl_ledger") if isinstance(pnl, dict) else None
        if not isinstance(ledger, list):
            return JSONResponse({"success": False, "code": "PNL_LEDGER_UNKNOWN"}, status_code=503)
        grouped = {}
        for row in ledger:
            symbol = str(row.get("symbol") or "UNKNOWN")
            item = grouped.setdefault(symbol, {"symbol": symbol, "trades": 0, "net_pnl": 0.0, "fees": 0.0})
            item["trades"] += 1
            item["net_pnl"] += float(row.get("realized_pnl") or 0.0)
            item["fees"] += float(row.get("fee") or 0.0)
        return JSONResponse({"success": True, "source": "EXECUTION_SERVICE_PNL_LEDGER", "analytics": list(grouped.values())})
    except Exception:
        logger.exception("Analytics projection failed")
        return JSONResponse({"success": False, "code": "PNL_LEDGER_UNKNOWN"}, status_code=503)


@app.get("/api/export_history_csv", dependencies=[Depends(verify_auth)])
async def export_history_csv():
    """Xuất file lịch sử giao dịch Trade History CSV"""
    history_file = config.trade_history_file
    if os.path.exists(history_file):
        return FileResponse(
            path=history_file,
            filename=f"trade_history_{datetime.now(VIETNAM_TZ).strftime('%Y%m%d_%H%M%S')}.csv",
            media_type="text/csv"
        )
@app.get("/api/fear_and_greed", dependencies=[Depends(verify_auth)])
async def get_fear_and_greed():
    """Lấy chỉ số tâm lý thị trường Crypto Fear & Greed Index"""
    return JSONResponse(CryptoSentiment.get_fear_and_greed())


@app.get("/api/tts")
async def get_tts_audio(text: str = ""):
    """Trả về file âm thanh giọng nói tiếng Việt chuẩn (MP3 stream) cho Mascot"""
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Thiếu nội dung văn bản")
    clean_text = text.strip()[:300]
    try:
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=vi&client=tw-ob&q={requests.utils.quote(clean_text)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            return Response(content=res.content, media_type="audio/mpeg")
    except Exception as e:
        logger.error("Lỗi tạo âm thanh TTS: %s", e)
    raise HTTPException(status_code=500, detail="Không thể tạo âm thanh TTS")


@app.post("/api/reset_history", dependencies=[Depends(verify_auth)])
async def reset_history():
    """Xóa và làm mới file trade_history.csv để người dùng bắt đầu chu kỳ kiểm thử mới sạch sẽ"""
    history_file = config.trade_history_file
    headers = [
        "timestamp", "symbol", "side", "entry_price", "exit_price",
        "qty", "margin_usdt", "pnl_usdt", "pnl_percent", "exit_reason"
    ]
    try:
        with open(history_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        if _bot_context and hasattr(_bot_context, "order_manager"):
            _bot_context.order_manager.trade_history = []
        return JSONResponse({"success": True, "message": "Đã làm sạch toàn bộ lịch sử lệnh cũ! Bắt đầu chu kỳ thống kê mới."})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi xóa lịch sử: {e}"})


@app.post("/api/backtest", dependencies=[Depends(verify_auth)])
async def run_backtest_endpoint(request: Request):
    """Run backtests only when the supervised strategy data context is enabled."""
    if _bot_context is None or not hasattr(_bot_context, "client"):
        return JSONResponse({"success": False, "code": "STRATEGY_CONTEXT_DISABLED_OFFLINE", "message": "Backtest requires a separately supervised strategy context."}, status_code=503)
    try:
        data = await request.json()
        symbol = str(data.get("symbol", "BTCUSDT")).strip().upper()
        strategy = str(data.get("strategy", "AUTO_DYNAMIC")).strip().upper()
        days = int(data.get("days", 14))
        timeframe = str(data.get("timeframe", "15m")).strip().lower()

        res = FuturesBacktester.run_simulation_for_symbol(
            client=_bot_context.client,
            symbol=symbol,
            strategy_name=strategy,
            days=days,
            timeframe=timeframe,
            initial_balance=1000.0,
            risk_percent=config.risk_per_trade_percent,
            rr_ratio=config.risk_reward_ratio
        )
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi chạy backtest: {e}"})


@app.get("/api/funding_arbitrage", dependencies=[Depends(verify_auth)])
async def get_funding_arbitrage():
    """Lấy danh sách cơ hội Delta-Neutral Funding Rate Arbitrage"""
    opps = FundingArbitrageVault.fetch_top_funding_opportunities(limit=8)
    return JSONResponse({"success": True, "opportunities": opps})


@app.get("/api/macro_news", dependencies=[Depends(verify_auth)])
async def get_macro_news():
    """Lấy luồng tin tức vĩ mô và rủi ro tin tức"""
    news = MacroNewsSentinel.fetch_latest_crypto_news(limit=6)
    return JSONResponse({"success": True, "news": news})


@app.get("/api/liquidation_radar", dependencies=[Depends(verify_auth)])
async def get_liquidation_radar(symbol: str = "BTCUSDT"):
    """Lấy các cụm thanh lý ước tính cho symbol"""
    symbol = symbol.upper()
    cur_p = 0.0
    if _bot_context:
        prices = _bot_context.get_current_prices()
        cur_p = prices.get(symbol, 0.0)
    if cur_p <= 0:
        try:
            market_base = (
                "https://testnet.binancefuture.com/fapi/v1"
                if str(getattr(config, "market_data_environment", "PRODUCTION")).upper() == "TESTNET"
                else "https://fapi.binance.com/fapi/v1"
            )
            url = f"{market_base}/ticker/price?symbol={symbol}"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                cur_p = float(r.json().get("price", 0.0))
        except Exception:
            pass
    clusters = LiquidationWhaleRadar.estimate_liquidation_levels(symbol, cur_p)
    return JSONResponse({"success": True, "radar": clusters})


@app.get("/api/correlation_matrix", dependencies=[Depends(verify_auth)])
async def get_correlation_matrix():
    """Lấy ma trận tương quan danh mục"""
    if _bot_context and hasattr(_bot_context, "scanner") and hasattr(_bot_context.scanner, "correlation_shield"):
        data = _bot_context.scanner.correlation_shield.get_matrix_data()
        return JSONResponse({"success": True, "data": data})
    return JSONResponse({"success": True, "data": {"symbols": [], "matrix": []}})


@app.get("/api/order_flow", dependencies=[Depends(verify_auth)])
async def get_order_flow(symbol: str = "BTCUSDT"):
    """Lấy dữ liệu Order Flow & Cumulative Volume Delta (CVD)"""
    data = OrderFlowEngine.fetch_order_flow_metrics(symbol=symbol)
    return JSONResponse({"success": True, "order_flow": data})


@app.get("/api/volatility_skew", dependencies=[Depends(verify_auth)])
async def get_volatility_skew(symbol: str = "BTCUSDT"):
    """Lấy chỉ số Volatility Skew & bề mặt biến động"""
    data = VolatilitySkewRadar.calculate_skew_metrics(symbol=symbol)
    return JSONResponse({"success": True, "skew": data})


@app.get("/api/pairs_trading", dependencies=[Depends(verify_auth)])
async def get_pairs_trading():
    """Lấy danh sách các cặp Cointegration & Spread Z-Score"""
    data = StatisticalPairsTrading.scan_all_pairs()
    return JSONResponse({"success": True, "pairs": data})


@app.get("/api/whale_tracker", dependencies=[Depends(verify_auth)])
async def get_whale_tracker():
    """Lấy hoạt động dòng tiền Cá Voi và luồng chuyển nhượng ví lớn"""
    data = OnChainWhaleTracker.fetch_whale_activity()
    return JSONResponse({"success": True, "whale_data": data})


@app.get("/api/cross_basis", dependencies=[Depends(verify_auth)])
async def get_cross_basis():
    """Lấy cơ hội Cash-and-Carry Basis Arbitrage giữa Spot và Futures"""
    data = CrossBasisScanner.scan_basis_opportunities()
    return JSONResponse({"success": True, "basis_data": data})


@app.get("/api/rl_regime", dependencies=[Depends(verify_auth)])
async def get_rl_regime():
    """Lấy trạng thái Market Regime và trọng số chiến lược tự trị (RL Agent)"""
    eval_m = calculate_evaluation_metrics()
    regime = AutonomousRLAgent.evaluate_market_regime(
        btc_price_change_24h=1.2,
        adx_value=float(config.adx_min),
        is_uptrend=True,
        recent_winrate=eval_m.get("win_rate", 50.0),
        recent_dd=eval_m.get("max_drawdown", 2.0)
    )
    return JSONResponse({"success": True, "rl_regime": regime})


@app.post("/api/voice_command", dependencies=[Depends(verify_auth)])
async def post_voice_command(request: Request):
    """Execute voice strategy commands only with a supervised strategy context."""
    if _bot_context is None:
        return JSONResponse({"success": False, "code": "STRATEGY_CONTEXT_DISABLED_OFFLINE", "reply": "Voice strategy commands are disabled in OFFLINE monitoring mode."}, status_code=503)
    try:
        body = await request.json()
        cmd_text = str(body.get("command", "")).strip()
        if not cmd_text:
            return JSONResponse({"success": False, "reply": "Em chưa nghe rõ câu lệnh của Sếp ạ."}, status_code=400)
        res = QuantumVoiceCommander.process_command(cmd_text, _bot_context)
        return JSONResponse({"success": True, **res})
    except Exception:
        logger.exception("Voice command failed")
        return JSONResponse({"success": False, "code": "VOICE_COMMAND_FAILED"}, status_code=503)


@app.get("/api/lead_lag", dependencies=[Depends(verify_auth)])
async def get_lead_lag():
    """Lấy dữ liệu xung lực dẫn sóng BTC Lead-Lag trên Binance Futures"""
    data = BinanceLeadLagEngine.scan_lead_lag_signals()
    return JSONResponse({"success": True, "lead_lag": data})


@app.get("/api/smc", dependencies=[Depends(verify_auth)])
async def get_smc(symbol: str = "BTCUSDT", interval: str = "15m"):
    """Lấy cấu trúc SMC (Order Block, FVG, Liquidity Sweep) trên Binance"""
    data = BinanceSMCDetector.analyze_smc_structure(symbol=symbol, interval=interval)
    return JSONResponse({"success": True, "smc": data})


@app.get("/api/hfmm", dependencies=[Depends(verify_auth)])
async def get_hfmm(symbol: str = "BTCUSDT"):
    """Lấy giá đặt lệnh High-Frequency Market Making Avellaneda-Stoikov"""
    data = BinanceHFMMEngine.calculate_hfmm_quotes(symbol=symbol)
    return JSONResponse({"success": True, "hfmm": data})


@app.get("/api/ai_synthesis", dependencies=[Depends(verify_auth)])
async def get_ai_synthesis():
    """Lấy báo cáo tổng hợp tham số tối ưu tự trị (Neural Synthesizer)"""
    eval_m = calculate_evaluation_metrics()
    wr = eval_m.get("win_rate", 52.0)
    data = NeuralStrategySynthesizer.synthesize_optimal_configuration(recent_winrate=wr)
    return JSONResponse({"success": True, "synthesis": data})


@app.get("/api/sentiment_vector", dependencies=[Depends(verify_auth)])
async def get_sentiment_vector():
    """Lấy chỉ số vector cảm xúc thị trường và rủi ro tin tức vĩ mô"""
    data = MacroSentimentVector.calculate_sentiment_vector()
    return JSONResponse({"success": True, "vector": data})


@app.get("/api/rebalance_plan", dependencies=[Depends(verify_auth)])
async def get_rebalance_plan():
    """Lấy kế hoạch tái cân bằng danh mục rủi ro ngang giá Risk Parity"""
    bal = _bot_context.get_current_balance() if _bot_context else 1000.0
    data = BinancePortfolioRebalancer.calculate_rebalance_plan(total_capital=bal)
    return JSONResponse({"success": True, "rebalance": data})


@app.get("/api/microstructure", dependencies=[Depends(verify_auth)])
async def get_microstructure(symbol: str = "BTCUSDT"):
    """Lấy dữ liệu phân tích sổ lệnh vi mô L2/L3 và phát hiện tường lệnh ẩn (Bản 11.0)"""
    data = BinanceL2L3Microstructure.analyze_order_book_depth(symbol=symbol)
    return JSONResponse({"success": True, "microstructure": data})


@app.get("/api/smart_grid", dependencies=[Depends(verify_auth)])
async def get_smart_grid(symbol: str = "BTCUSDT"):
    """Lấy ma trận lưới thông minh co dãn theo biến động ATR (Bản 11.0)"""
    bal = _bot_context.get_current_balance() if _bot_context else 1000.0
    data = AdaptiveSmartGridEngine.calculate_smart_grid(symbol=symbol, total_capital=bal)
    return JSONResponse({"success": True, "smart_grid": data})


@app.get("/api/pca_basket", dependencies=[Depends(verify_auth)])
async def get_pca_basket():
    """Lấy kết quả phân tích PCA rổ tài sản và độ lệch Residual Z-Score (Bản 11.0)"""
    data = MultiAssetBasketSniper.scan_pca_basket()
    return JSONResponse({"success": True, "pca": data})


@app.get("/api/subaccount_yield", dependencies=[Depends(verify_auth)])
async def get_subaccount_yield():
    """Lấy dữ liệu tối ưu hóa lợi tức vốn nhàn rỗi Binance Simple Earn (Bản 11.0)"""
    bal = _bot_context.get_current_balance() if _bot_context else 1000.0
    active_pos = _bot_context.order_manager.active_positions if _bot_context and hasattr(_bot_context, "order_manager") else {}
    used_margin = sum(p.get("margin", 0.0) for p in active_pos.values())
    data = BinanceSubAccountHarvester.calculate_yield_optimization(total_balance=bal, active_margin_used=used_margin)
    return JSONResponse({"success": True, "yield_harvester": data})


@app.get("/api/genetic_evolution", dependencies=[Depends(verify_auth)])
async def get_genetic_evolution():
    """Lấy kết quả chu trình tiến hóa di truyền AI chống Alpha Decay (Bản 12.0)"""
    data = GeneticStrategyEvolver.run_evolution_cycle()
    return JSONResponse({"success": True, "evolution": data})


@app.get("/api/digital_twin_stress", dependencies=[Depends(verify_auth)])
async def get_digital_twin_stress():
    """Kiểm tra sức chịu đựng của danh mục qua Digital Twin và kích hoạt Kén Bọc Thép (Bản 12.0)"""
    bal = _bot_context.get_current_balance() if _bot_context else 1000.0
    active_pos = _bot_context.order_manager.active_positions if _bot_context and hasattr(_bot_context, "order_manager") else {}
    data = DigitalTwinRiskSimulator.run_stress_test(portfolio_balance=bal, active_positions=active_pos)
    return JSONResponse({"success": True, "stress_test": data})


@app.get("/api/edge_latency", dependencies=[Depends(verify_auth)])
async def get_edge_latency():
    """Đo lường độ trễ mạng Edge Routing tới Binance AWS Tokyo/Singapore (Bản 12.0)"""
    data = BinanceEdgeLatencyOptimizer.measure_edge_latency()
    return JSONResponse({"success": True, "latency": data})


@app.post("/api/multi_turn_chat", dependencies=[Depends(verify_auth)])
async def post_multi_turn_chat(request: Request):
    """Use the portfolio advisor only when AI/strategy context is enabled."""
    if _bot_context is None:
        return JSONResponse({"success": False, "code": "AI_DISABLED_OFFLINE", "error": "Portfolio advisor is disabled in OFFLINE monitoring mode."}, status_code=503)
    try:
        body = await request.json()
        query = body.get("query", "")
        res = MultiTurnPortfolioAdvisor.answer_query(query, _bot_context)
        return JSONResponse({"success": True, "response": res})
    except Exception:
        logger.exception("Portfolio advisor failed")
        return JSONResponse({"success": False, "code": "PORTFOLIO_ADVISOR_FAILED"}, status_code=503)


@app.get("/api/ai_training", dependencies=[Depends(verify_auth)])
async def get_ai_training():
    """Lấy dữ liệu và trạng thái tối ưu hóa tự động của AI Self-Training Engine"""
    try:
        from core.ai_trade_trainer import AITradeTrainer
        trainer = AITradeTrainer()
        data = trainer.get_training_report()
        return JSONResponse({"success": True, "ai_training": data})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.post("/api/ai_train", dependencies=[Depends(verify_auth)])
async def post_ai_train():
    """Kích hoạt chạy huấn luyện mô hình AI từ toàn bộ lịch sử lệnh"""
    try:
        from core.ai_trade_trainer import AITradeTrainer
        trainer = AITradeTrainer()
        report = trainer.train_from_history()
        return JSONResponse({"success": True, "report": report})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.post("/api/webhook/tradingview")
async def webhook_tradingview(request: Request):
    """
    TradingView Alert Webhook Endpoint (Quant Pro Feature - Tùy chọn sẵn sàng kết nối)
    Nhận webhook từ Pine Script TradingView:
    Payload JSON:
    {
        "passphrase": "quant_pro_secret_2026",
        "symbol": "BTCUSDT",
        "action": "BUY" | "SELL" | "CLOSE",
        "price": 65000.0,
        "stop_loss": 64000.0,
        "take_profit": 67000.0
    }
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    passphrase = data.get("passphrase")
    expected = getattr(config, "webhook_passphrase", None)
    DEFAULT_WEBHOOK_SECRETS = {
        "quant_pro_default_insecure_passphrase",
        "quant_pro_secret_passphrase",
        "quant_pro_secret_2026",
        "quant_pro_production_long_secret_passphrase_2026",
        "default",
        "",
        "None",
        None
    }
    if not expected or str(expected).strip() in DEFAULT_WEBHOOK_SECRETS or len(str(expected).strip()) <= 20:
        logger.error("🚨 [WEBHOOK DENIED] Webhook bị từ chối: Đang sử dụng mật khẩu mặc định hoặc chưa cấu hình an toàn (>20 ký tự).")
        return JSONResponse({"success": False, "error": "Webhook passphrase is using insecure public default, unconfigured, or too short (must be > 20 chars). Explicit custom passphrase required."}, status_code=403)

    if not passphrase or not secrets.compare_digest(str(passphrase), str(expected)):
        return JSONResponse({"success": False, "error": "Unauthorized webhook passphrase"}, status_code=401)

    if not _bot_context:
        return JSONResponse({"success": False, "error": "Bot context not initialized"}, status_code=503)

    symbol = str(data.get("symbol", "")).upper()
    action = str(data.get("action", "")).upper()
    try:
        price = (
            _strict_handler_float(data["price"], "price", positive=True)
            if "price" in data else 0.0
        )
    except (TypeError, ValueError, OverflowError) as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    if not symbol or action not in ["BUY", "SELL", "CLOSE", "SHORT", "LONG"]:
        return JSONResponse({"success": False, "error": "Invalid symbol or action"}, status_code=400)

    if action == "LONG":
        action = "BUY"
    elif action == "SHORT":
        action = "SELL"

    logger.info("📡 [TradingView Webhook] Nhận tín hiệu %s cho %s tại $%s", action, symbol, f"{price:,.4f}" if price > 0 else "Market")

    if action == "CLOSE":
        exec_client = _get_execution_client_for_surface("webhook")
        if exec_client is not None:
            cmd_res = exec_client.close_position(symbol=symbol, reason="TradingView Webhook Close", source="webhook")
            if not cmd_res.success:
                return JSONResponse({"success": False, "error": f"Execution Service error: {cmd_res.error}"}, status_code=503)
            return JSONResponse({"success": True, "message": f"Closed {symbol} via Execution Service"})
        return JSONResponse({"success": False, "error": "Execution Service unavailable (Hard Cutover)"}, status_code=503)

    bal = _bot_context.get_current_balance()
    risk_ok, risk_reason = _bot_context.risk_manager.can_open_new_position(
        _bot_context.order_manager.get_open_position_count(),
        bal
    )
    if not risk_ok:
        return JSONResponse({"success": False, "error": f"Risk blocked: {risk_reason}"}, status_code=400)

    filter_info = _bot_context.client.get_symbol_filter_info(symbol)
    if price <= 0:
        if hasattr(_bot_context.client, "get_symbol_price"):
            try:
                p = _bot_context.client.get_symbol_price(symbol)
                if isinstance(p, (int, float)) and p > 0:
                    price = float(p)
            except Exception:
                pass
        if price <= 0 and hasattr(_bot_context.client, "get_klines_df"):
            try:
                df = _bot_context.client.get_klines_df(symbol, interval="1m", limit=1)
                if df is not None and not df.empty and "close" in df.columns:
                    price = float(df["close"].iloc[-1])
            except Exception:
                pass
        if not price or (isinstance(price, (int, float)) and price <= 0):
            return JSONResponse({"success": False, "error": f"Cannot get market price for {symbol}"}, status_code=400)

    try:
        sl = _strict_handler_float(data.get("stop_loss", 0.0), "stop_loss", positive=True)
        tp = (
            _strict_handler_float(data["take_profit"], "take_profit", positive=True)
            if "take_profit" in data else 0.0
        )
        bal = _strict_handler_float(bal, "capital", positive=True)
    except (TypeError, ValueError, OverflowError) as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)
    if sl <= 0:
        return JSONResponse(
            {"success": False, "code": "PROTECTIVE_STOP_REQUIRED",
             "error": "Explicit positive stop_loss is required for OPEN"},
            status_code=400,
        )
    if tp <= 0:
        dist = abs(price - sl)
        tp = price + 1.5 * dist if action == "BUY" else price - 1.5 * dist

    sizing = _bot_context.risk_manager.calculate_position_size(
        balance=bal,
        entry_price=price,
        stop_loss_price=sl,
        step_size=filter_info["step_size"],
        min_qty=filter_info["min_qty"],
        min_notional=filter_info["min_notional"]
    )
    if not sizing.get("valid"):
        return JSONResponse({"success": False, "error": sizing.get("reason")}, status_code=400)

    exec_client = _get_execution_client_for_surface("webhook")
    if exec_client is not None:
        cmd_res = exec_client.open_position(
            symbol=symbol,
            side=action,
            qty=sizing["qty"],
            entry_price=price,
            stop_loss=sl,
            take_profit=tp,
            leverage=sizing.get("leverage", 1),
            total_capital=bal,
            source="webhook",
        )
        if not cmd_res.success:
            return JSONResponse({"success": False, "error": f"Execution Service error: {cmd_res.error}"}, status_code=503)
        return JSONResponse({
            "success": True,
            "symbol": symbol,
            "action": action,
            "price": price,
            "qty": sizing["qty"],
            "receipt": cmd_res.execution_receipt_id,
        })

    return JSONResponse({"success": False, "error": "Execution Service unavailable (Hard Cutover)"}, status_code=503)


# ==================== NON-CUSTODIAL MULTI-CLIENT COPY-TRADING & PUBLIC PORTAL ====================

def get_current_client_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """Xác thực client chỉ từ JWT ký số hoặc phiên Admin hợp lệ."""
    token = _portal_jwt_from_request(request)

    if token:
        payload = decode_jwt_token(token)
        if payload and payload.get("client_id"):
            with get_db_session() as db:
                if _jwt_is_revoked(payload, db):
                    return None
        if payload and payload.get("client_id"):
            with get_db_session() as db:
                c = db.query(Client).filter(Client.id == int(payload["client_id"])).first()
                if (
                    c and c.is_active and c.username == payload.get("sub")
                    and payload.get("session_version") == _client_session_version(c)
                ):
                    return {
                        "client_id": c.id,
                        "username": c.username,
                        "full_name": getattr(c, "full_name", None) or c.username,
                        "role": c.role,
                        "email": c.email or ""
                    }

    adm_token = request.cookies.get("session_token") or request.headers.get("X-Session-Token")
    current_admin = _current_session_client(adm_token, required_role="admin")
    if current_admin:
        with get_db_session() as db:
            adm = db.query(Client).filter(Client.id == current_admin["client_id"]).first()
            if adm:
                return {
                    "client_id": adm.id,
                    "username": adm.username,
                    "full_name": getattr(adm, "full_name", None) or "Quản Trị Viên",
                    "role": adm.role,
                    "email": adm.email or ""
                }
    return None


def is_admin_request(request: Request) -> bool:
    """Require current database admin status; token claims alone grant no authority."""
    jwt_token = _portal_jwt_from_request(request)
    if jwt_token:
        payload = decode_jwt_token(jwt_token)
        if payload and payload.get("client_id"):
            with get_db_session() as db:
                if _jwt_is_revoked(payload, db):
                    return False
                row = db.query(Client).filter(Client.id == int(payload["client_id"])).first()
                return bool(
                    row
                    and row.is_active
                    and row.role == "admin"
                    and row.username == payload.get("sub")
                    and payload.get("session_version") == _client_session_version(row)
                )

    session_token = request.cookies.get("session_token") or request.headers.get("X-Session-Token")
    return _current_session_client(session_token, required_role="admin") is not None


# --- Phân hệ 1: Public Track Record ---
@app.get("/track-record", response_class=HTMLResponse)
async def track_record_page():
    """Trang Track Record được tính lại từ CSV/database hiện tại ở mỗi request."""
    metrics = calculate_track_record_metrics()
    t_path = os.path.join(os.path.dirname(__file__), "templates", "track_record.html")
    if not os.path.exists(t_path):
        return HTMLResponse(render_track_record_html(metrics))

    with open(t_path, "r", encoding="utf-8") as f:
        html = f.read()

    pnl = float(metrics.get("net_pnl_usdt", 0.0))
    roi = float(metrics.get("total_return_pct", 0.0))
    prefix = "+" if pnl > 0 else ""
    pnl_class = "text-profitGreen" if pnl >= 0 else "text-lossRed"
    rows = []
    for trade in metrics.get("recent_trades", [])[:50]:
        side = escape(str(trade.get("side", "")))
        side_class = "text-cyberCyan bg-cyan-950/40 border-cyan-800/50" if side in ("BUY", "LONG") else "text-binanceGold bg-yellow-950/40 border-yellow-800/50"
        trade_pnl = float(trade.get("pnl_usdt", 0.0))
        trade_pct = float(trade.get("pnl_percent", 0.0))
        trade_prefix = "+" if trade_pnl > 0 else ""
        trade_class = "text-profitGreen" if trade_pnl >= 0 else "text-lossRed"
        rows.append(f'''<tr class="hover:bg-darkCardHover transition border-b border-darkBorder font-mono text-xs">
            <td class="py-3 px-4 text-gray-400 whitespace-nowrap">{escape(str(trade.get("timestamp", "")))}</td>
            <td class="py-3 px-4 font-bold text-white">{escape(str(trade.get("symbol", "")))}</td>
            <td class="py-3 px-4"><span class="px-2 py-0.5 rounded text-[11px] font-bold border {side_class}">{side}</span></td>
            <td class="py-3 px-4 text-gray-300 text-right">${float(trade.get("entry_price", 0.0)):,.4f}</td>
            <td class="py-3 px-4 text-gray-300 text-right">${float(trade.get("exit_price", 0.0)):,.4f}</td>
            <td class="py-3 px-4 text-gray-400 text-right">${float(trade.get("margin", 0.0)):,.2f}</td>
            <td class="py-3 px-4 text-right {trade_class} font-bold">{trade_prefix}${trade_pnl:.2f} ({trade_prefix}{trade_pct:.2f}%)</td>
            <td class="py-3 px-4 text-gray-300">{escape(str(trade.get("exit_reason", "")))}</td>
        </tr>''')

    replacements = {
        "__TR_TOTAL__": str(int(metrics.get("total_trades", 0))),
        "__TR_WIN_RATE__": f'{float(metrics.get("win_rate", 0.0)):.1f}',
        "__TR_WINS__": str(int(metrics.get("wins", 0))),
        "__TR_LOSSES__": str(int(metrics.get("losses", 0))),
        "__TR_NET_PNL__": f'{prefix}{pnl:.2f}',
        "__TR_ROI__": f'{prefix}{roi:.2f}',
        "__TR_PNL_CLASS__": pnl_class,
        "__TR_PF__": f'{float(metrics.get("profit_factor", 0.0)):.2f}',
        "__TR_SHARPE__": f'{float(metrics.get("sharpe_ratio", 0.0)):.2f}',
        "__TR_DD__": f'{float(metrics.get("max_drawdown_pct", 0.0)):.2f}',
        "__TR_ROWS__": "".join(rows),
        "__TR_EQUITY_JSON__": json.dumps(metrics.get("equity_curve", []), ensure_ascii=False),
    }
    for key, value in replacements.items():
        html = html.replace(key, value)
    return HTMLResponse(content=html)


@app.get("/api/public/track-record-data")
async def api_public_track_record():
    """API dữ liệu Track Record cho biểu đồ và đối tác"""
    return JSONResponse(calculate_track_record_metrics())


# --- Phân hệ 2: Client Portal Web Pages ---
@app.get("/portal/login", response_class=HTMLResponse)
async def portal_login_view(request: Request):
    """Trang đăng nhập Client Portal"""
    client_ctx = get_current_client_from_request(request)
    if client_ctx:
        return RedirectResponse(url="/portal/dashboard", status_code=302)
    if is_ui_v2_enabled():
        return render_ui_v2_template("ui_v2/login.html")
    t_path = os.path.join(os.path.dirname(__file__), "templates", "login.html")
    if os.path.exists(t_path):
        with open(t_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(render_portal_login_html())


@app.get("/portal/login-v2", response_class=HTMLResponse)
async def portal_login_v2_view(request: Request):
    """V2 Login page (always available for V2 testing)."""
    client_ctx = get_current_client_from_request(request)
    if client_ctx:
        return RedirectResponse(url="/portal/dashboard-v2", status_code=302)
    return render_ui_v2_template("ui_v2/login.html")


@app.post("/portal/login")
async def portal_login_action(request: Request, response: Response):
    """Xử lý đăng nhập Client Portal bằng tài khoản đã lưu trong database."""
    content_type = request.headers.get("content-type", "")
    is_form = "application/json" not in content_type

    if is_form:
        form_data = await request.form()
        username = str(form_data.get("username", "")).strip()
        password = str(form_data.get("password", "")).strip()
    else:
        body = await request.json()
        username = str(body.get("username", "")).strip()
        password = str(body.get("password", "")).strip()

    if not username or not password:
        if is_form:
            return RedirectResponse(url="/portal/login?error=missing", status_code=303)
        return JSONResponse({"success": False, "message": "Vui lòng nhập tên đăng nhập và mật khẩu."}, status_code=400)

    if _login_is_limited(request, username):
        if is_form:
            return RedirectResponse(url="/portal/login?error=rate_limited", status_code=303)
        return JSONResponse({"success": False, "code": "LOGIN_RATE_LIMITED", "message": "Quá nhiều lần đăng nhập thất bại. Vui lòng thử lại sau."}, status_code=429)

    client_data = None
    with get_db_session() as db:
        c = db.query(Client).filter((Client.username == username) | (Client.email == username)).first()
        if c and c.is_active and verify_password(password, c.password_hash):
            client_data = {
                "client_id": int(c.id),
                "username": c.username,
                "full_name": getattr(c, "full_name", None) or c.username,
                "role": c.role,
                "email": c.email or "",
                "session_version": _client_session_version(c),
            }

    is_authenticated = client_data is not None
    if is_authenticated:
        _clear_login_failures(request, username)
    else:
        _record_login_failure(request, username)
    if is_authenticated and client_data:
        jwt_token = create_jwt_token({
            "sub": client_data["username"],
            "client_id": client_data["client_id"],
            "role": client_data["role"],
            "full_name": client_data["full_name"],
            "email": client_data["email"],
            "session_version": client_data["session_version"],
        })
        is_admin_user = client_data.get("role") == "admin"
        target_url = "/admin" if is_admin_user else "/portal/dashboard"

        if is_form:
            resp = RedirectResponse(url=target_url, status_code=303)
        else:
            resp = JSONResponse({
                "success": True,
                "username": client_data["username"],
                "full_name": client_data["full_name"],
                "role": client_data["role"],
                "redirect": target_url,
                "message": "Đăng nhập thành công!"
            })

        if is_admin_user:
            adm_token = create_session_token(client_data["username"], "admin")
            resp.set_cookie(key="session_token", value=adm_token, max_age=30*86400, path="/", httponly=True, samesite="strict", secure=True)

        resp.set_cookie(key="client_session_user", value=client_data["username"], max_age=30*86400, path="/", httponly=True, samesite="lax", secure=True)
        resp.set_cookie(key="client_token", value=jwt_token, max_age=30*86400, path="/", httponly=True, samesite="lax", secure=True)
        return resp
    # Thất bại
    if is_form:
        t_path = os.path.join(os.path.dirname(__file__), "templates", "login.html")
        if os.path.exists(t_path):
            with open(t_path, "r", encoding="utf-8") as f:
                html = f.read()
            err_box = '<div style="background: rgba(239, 68, 68, 0.12); border: 1px solid #ef4444; color: #ef4444; padding: 12px 14px; border-radius: 8px; font-size: 13px; font-weight: 700; margin-bottom: 16px;">⚠️ Tên đăng nhập hoặc mật khẩu không chính xác!</div>'
            html = html.replace('<form method="POST"', err_box + '<form method="POST"')
            return HTMLResponse(content=html, status_code=401)
        return RedirectResponse(url="/portal/login?error=invalid", status_code=303)
    else:
        return JSONResponse({"success": False, "message": "Sai tên đăng nhập hoặc mật khẩu."}, status_code=401)


@app.get("/portal/register", response_class=HTMLResponse)
async def portal_register_view(request: Request):
    """Trang đăng ký tài khoản khách hàng mới"""
    client_ctx = get_current_client_from_request(request)
    if client_ctx:
        return RedirectResponse(url="/portal/dashboard", status_code=302)
    t_path = os.path.join(os.path.dirname(__file__), "templates", "register.html")
    if os.path.exists(t_path):
        with open(t_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(render_portal_register_html())


@app.post("/portal/register")
async def portal_register_action(request: Request, response: Response):
    """Xử lý đăng ký tài khoản mới (hỗ trợ cả Form Onboarding và JSON API)"""
    content_type = request.headers.get("content-type", "")
    is_form = "application/json" not in content_type

    if is_form:
        form_data = await request.form()
        username = str(form_data.get("username", "")).strip()
        email = str(form_data.get("email", "")).strip().lower()
        password = str(form_data.get("password", "")).strip()
        full_name = str(form_data.get("full_name", "")).strip() or username

        if len(username) < 3 or len(password) < 6:
            return RedirectResponse(url="/portal/register?error=invalid", status_code=303)

        with get_db_session() as db:
            exist_u = db.query(Client).filter((Client.username == username) | (Client.email == email if email else False)).first()
            if exist_u:
                return RedirectResponse(url="/portal/register?error=exists", status_code=303)

            new_client = Client(
                username=username,
                email=email if email else None,
                full_name=full_name,
                password_hash=hash_password(password),
                role="client",
                is_active=True
            )
            db.add(new_client)
            db.commit()
            db.refresh(new_client)

            token_payload = {
                "sub": new_client.username,
                "client_id": int(new_client.id),
                "role": new_client.role,
                "email": new_client.email or "",
                "full_name": new_client.full_name or username,
                "session_version": _client_session_version(new_client),
            }
            jwt_token = create_jwt_token(token_payload)

        target_url = "/portal/dashboard"
        resp = RedirectResponse(url=target_url, status_code=303)
        resp.set_cookie(key="client_session_user", value=username, max_age=30*86400, path="/", httponly=True, samesite="lax", secure=True)
        resp.set_cookie(key="client_token", value=jwt_token, max_age=30*86400, path="/", httponly=True, samesite="lax", secure=True)
        return resp

    return await api_portal_register(request, response)

@app.get("/portal/logout")
async def portal_logout_view(request: Request):
    """Revoke the current portal JWT before deleting browser cookies."""
    _revoke_portal_jwt(_portal_jwt_from_request(request))
    resp = RedirectResponse(url="/portal/login", status_code=302)
    resp.delete_cookie(key="client_session_user", path="/")
    resp.delete_cookie(key="client_token", path="/")
    return resp


def _client_account_feature_disabled() -> JSONResponse:
    return JSONResponse(
        {
            "success": False,
            "ok": False,
            "state": "DISABLED",
            "code": "FEATURE_DISABLED",
            "feature": "client_account_trading",
            "message": "Client-account trading is not supported in the current architecture.",
        },
        status_code=503,
    )


@app.get("/portal/api-settings", response_class=HTMLResponse)
async def portal_api_settings_view(request: Request):
    """Retired product surface; never accept or display trading credentials."""
    if not get_current_client_from_request(request):
        return RedirectResponse(url="/portal/login", status_code=302)
    return HTMLResponse(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width'>"
        "<title>Feature disabled</title></head><body><main>"
        "<h1>Feature disabled</h1>"
        "<p>Client-account trading is not supported in the current architecture.</p>"
        "<p>No Binance credentials are required or accepted by this application.</p>"
        "<a href='/portal/dashboard'>Return to monitoring dashboard</a>"
        "</main></body></html>",
        status_code=200,
    )


@app.post("/portal/api-settings")
async def portal_api_settings_post_action(request: Request):
    """Fail closed without reading the body or touching credential storage."""
    if not get_current_client_from_request(request):
        return JSONResponse({"success": False, "code": "UNAUTHENTICATED"}, status_code=401)
    return _client_account_feature_disabled()


@app.get("/portal/dashboard-v2", response_class=HTMLResponse)
async def portal_dashboard_v2_view(request: Request):
    """V2 Operator Terminal (Always accessible when authenticated)."""
    client_ctx = get_current_client_from_request(request)
    if not client_ctx:
        return RedirectResponse(url="/portal/login?next=/portal/dashboard-v2", status_code=302)
    return render_ui_v2_template("ui_v2/dashboard.html", user=client_ctx)


@app.get("/portal/ui_v2_preview", response_class=HTMLResponse)
async def portal_ui_v2_preview(request: Request):
    """Developer preview showcase. Requires authentication unless UI_V2_DEV_PREVIEW_ENABLED is explicitly enabled."""
    client_ctx = get_current_client_from_request(request)
    if not client_ctx and not is_ui_v2_preview_enabled():
        return RedirectResponse(url="/portal/login?next=/portal/ui_v2_preview", status_code=302)
    p = os.path.join(os.path.dirname(__file__), "templates", "ui_v2_preview.html")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>UI V2 Preview Not Found</h1>", status_code=404)


@app.get("/portal/dashboard", response_class=HTMLResponse)
async def portal_dashboard_view(request: Request):
    """Bảng điều khiển khách hàng cá nhân hóa dựa trên 100% dữ liệu thật của tài khoản"""
    client_ctx = get_current_client_from_request(request)
    if not client_ctx:
        return RedirectResponse(url="/portal/login", status_code=302)

    if is_ui_v2_enabled():
        return render_ui_v2_template("ui_v2/dashboard.html", user=client_ctx)

    client_id = client_ctx["client_id"]
    mux = get_order_multiplexer(use_testnet=getattr(config, "use_testnet", False))
    dashboard_data = mux.get_client_dashboard_info(client_id)

    # Consume only the non-secret directory projection returned by the multiplexer.
    with get_db_session() as db:
        c = db.query(Client).filter(Client.id == client_id).first()
        client_dict = c.to_dict() if c else client_ctx
        cred_dict = dict(dashboard_data)
        user_orders_orm = db.query(ClientOrderLog).filter(ClientOrderLog.client_id == client_id).order_by(ClientOrderLog.created_at.desc()).limit(50).all()
        user_orders = [o.to_dict() for o in user_orders_orm]

    t_path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
    if os.path.exists(t_path):
        with open(t_path, "r", encoding="utf-8") as f:
            html = f.read()

        full_name = escape(str(client_ctx.get("full_name") or client_dict.get("full_name") or "Khách hàng"))
        username = escape(str(client_ctx.get("username") or "client"))
        email = escape(str(client_ctx.get("email") or ""))

        html = html.replace("Nguyễn Nhật Huy", full_name)
        html = html.replace("huy@noza.site", email)

        # 1. Tính toán các chỉ số KPI THẬT từ user_orders và Binance / simulated balance
        equity_val = float(dashboard_data.get('equity', 1000.0) or 1000.0)
        balance_val = float(dashboard_data.get('balance', 1000.0) or 1000.0)
        net_pnl_val = float(dashboard_data.get('net_pnl', 0.0) or 0.0)
        roi_val = (net_pnl_val / balance_val * 100.0) if balance_val > 0 else 0.0

        # Tính win rate và profit factor thật từ user_orders
        closed_orders = [o for o in user_orders if o.get("action") in ("CLOSE", "PARTIAL_TP", "EMERGENCY_CLOSE")]
        gross_profit = 0.0
        gross_loss = 0.0
        wins = 0
        losses = 0
        for o in closed_orders:
            pnl_val = 0.0
            err_msg = o.get("error_message") or ""
            if "pnl=" in err_msg:
                try:
                    pnl_val = float(err_msg.split("pnl=")[1].split()[0])
                except Exception:
                    pass
            if pnl_val > 0:
                gross_profit += pnl_val
                wins += 1
            elif pnl_val < 0:
                gross_loss += abs(pnl_val)
                losses += 1
        win_rate_val = (wins / len(closed_orders) * 100.0) if closed_orders else 0.0
        total_trades_val = int(dashboard_data.get("total_trades", len(user_orders)) or 0)
        profit_factor_val = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        sharpe_val = float(dashboard_data.get('sharpe', 0.0) or 0.0)
        max_dd_val = float(dashboard_data.get('max_drawdown', 0.0) or 0.0)

        # Thay thế KPI Stats theo ID
        html = html.replace('id="stat-equity">$0.00</div>', f'id="stat-equity">${equity_val:,.2f}</div>')
        html = html.replace('id="stat-balance">Ví Futures: $0.00</div>', f'id="stat-balance">Ví Futures: ${balance_val:,.2f}</div>')
        pnl_prefix = "+" if net_pnl_val > 0 else ""
        html = html.replace('id="stat-net-pnl">$0.00</div>', f'id="stat-net-pnl">{pnl_prefix}${net_pnl_val:,.2f}</div>')
        html = html.replace('id="stat-roi">0.00% ROI</div>', f'id="stat-roi">{pnl_prefix}{roi_val:.2f}% ROI</div>')
        html = html.replace('id="stat-win-rate">0.0%</div>', f'id="stat-win-rate">{win_rate_val:.1f}%</div>')
        html = html.replace('id="stat-trades-count">0 lệnh đã đối soát</div>', f'id="stat-trades-count">{total_trades_val} lệnh đã đối soát</div>')
        html = html.replace('id="stat-profit-factor">0.00</div>', f'id="stat-profit-factor">{profit_factor_val:.2f}</div>')
        html = html.replace('id="stat-sharpe">0.00</div>', f'id="stat-sharpe">{sharpe_val:.2f}</div>')
        html = html.replace('id="stat-max-dd">0.00%</div>', f'id="stat-max-dd">{max_dd_val:.2f}%</div>')

        # 2. Cấu hình API và mốc High-Water Mark THẬT
        hwm_base = float(dashboard_data.get("hwm_benchmark", 1000.0) or 1000.0)
        profit_ratio = float(dashboard_data.get("profit_share_percent", 10.0) or 10.0)
        fee_due = float(dashboard_data.get("fee_due_usdt", 0.0) or 0.0)
        credit_bal = float(dashboard_data.get("credit_balance_usdt", 0.0) or 0.0)

        html = html.replace('id="hwm_benchmark_disp">$1,000.00', f'id="hwm_benchmark_disp">${hwm_base:,.2f}')
        html = html.replace('id="profit_share_pct_disp">10.0%', f'id="profit_share_pct_disp">{profit_ratio:.1f}%')
        html = html.replace('id="fee_due_disp">$28.55', f'id="fee_due_disp">${fee_due:,.2f}')
        html = html.replace('id="credit_balance_disp">$0.00', f'id="credit_balance_disp">${credit_bal:,.2f}')
        html = html.replace('id="chart-start-equity" class="text-white">$0.00', f'id="chart-start-equity" class="text-white">${hwm_base:,.2f}')
        html = html.replace('id="chart-peak-equity" class="text-profitGreen">$0.00', f'id="chart-peak-equity" class="text-profitGreen">${max(hwm_base, equity_val):,.2f}')

        # Client credential and copy-trade controls are intentionally absent.
        html = html.replace("__IS_COPY_ACTIVE__", "false")

        # 3. Vị thế thực tế của user
        raw_user_positions = dashboard_data.get("positions", [])
        if isinstance(raw_user_positions, dict):
            user_positions = [dict(position, symbol=position.get("symbol") or symbol)
                              for symbol, position in raw_user_positions.items()
                              if isinstance(position, dict)]
        else:
            user_positions = raw_user_positions if isinstance(raw_user_positions, list) else []
        open_margin_total = sum(float(p.get("margin", 0.0) or 0.0) for p in user_positions)
        html = html.replace('id="donut-open-margin" class="text-lg font-mono font-black text-binanceGold">$0.00', f'id="donut-open-margin" class="text-lg font-mono font-black text-binanceGold">${open_margin_total:,.2f}')
        if user_positions:
            pos_rows = ""
            for p in user_positions:
                side_color = "text-cyberCyan bg-cyan-950/40 border-cyan-800/50" if p["side"] in ("BUY", "LONG") else "text-binanceGold bg-yellow-950/40 border-yellow-800/50"
                pnl_color = "text-profitGreen" if p["pnl_usdt"] >= 0 else "text-lossRed"
                prefix = "+" if p["pnl_usdt"] > 0 else ""
                pos_rows += f'''
                <tr class="hover:bg-darkCardHover transition">
                    <td class="py-3 px-4 font-bold text-white flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-profitGreen"></span>
                        {p["symbol"]}
                    </td>
                    <td class="py-3 px-4">
                        <span class="px-2 py-0.5 rounded text-xs font-mono font-bold border {side_color}">{p["side"]}</span>
                    </td>
                    <td class="py-3 px-4 text-xs font-mono text-gray-300 text-right">{p["size"]}</td>
                    <td class="py-3 px-4 text-xs font-mono text-gray-300 text-right">${p["entry_price"]:,.4f}</td>
                    <td class="py-3 px-4 text-xs font-mono text-white text-right">${p["mark_price"]:,.4f}</td>
                    <td class="py-3 px-4 text-xs font-mono text-gray-400 text-right">${p["margin"]:,.2f}</td>
                    <td class="py-3 px-4 text-right font-mono font-bold {pnl_color}">
                        {prefix}${p["pnl_usdt"]:,.2f} ({prefix}{p["pnl_percent"]:.2f}%)
                    </td>
                    <td class="py-3 px-4 text-center text-xs">
                        <span class="px-2 py-0.5 rounded bg-profitGreen/10 text-profitGreen font-mono text-[11px] border border-profitGreen/30">
                            🛡️ Đang Bảo Vệ SL
                        </span>
                    </td>
                    <td class="py-3 px-4 text-center text-xs text-gray-500 font-mono">
                        READ ONLY
                    </td>
                </tr>
                '''
            tbody_match = re.search(r'<tbody class="divide-y divide-slate-800/50 font-medium">.*?</tbody>', html, re.DOTALL)
            if tbody_match:
                html = html[:tbody_match.start()] + f'<tbody class="divide-y divide-darkBorder font-medium">{pos_rows}</tbody>' + html[tbody_match.end():]
        else:
            idle_row = '''
            <tbody class="divide-y divide-darkBorder font-medium">
                <tr>
                    <td colspan="9" class="py-8 text-center text-xs text-gray-400 font-mono">
                        <i class="fa-solid fa-circle-check text-profitGreen mr-1.5"></i>
                        OFFLINE monitoring is active. No open positions are reported.<br>
                        <span class="text-gray-500 text-[11px]">Scanner, strategy, and client-account trading are disabled.</span>
                    </td>
                </tr>
            </tbody>
            '''
            tbody_match = re.search(r'<tbody class="divide-y divide-slate-800/50 font-medium">.*?</tbody>', html, re.DOTALL)
            if tbody_match:
                html = html[:tbody_match.start()] + idle_row + html[tbody_match.end():]

        # 4. Nhật ký lệnh THẬT cho Tab 4 (Audit Logs)
        if user_orders:
            hist_rows = ""
            for o in user_orders:
                side_b = "text-cyberCyan bg-cyan-950/40 border-cyan-800/50" if o.get("side") in ("BUY", "LONG") else "text-binanceGold bg-yellow-950/40 border-yellow-800/50"
                st_b = "text-profitGreen bg-emerald-950/40 border-emerald-800/50" if o.get("status") in ("FILLED", "SIMULATED") else "text-lossRed bg-rose-950/40 border-rose-800/50"
                date_str = str(o.get("created_at") or "")[:19].replace("T", " ")
                hist_rows += f'''
                <tr class="hover:bg-darkCardHover transition border-b border-darkBorder font-mono text-xs">
                    <td class="py-3 px-4 text-gray-400 whitespace-nowrap">{date_str}</td>
                    <td class="py-3 px-4 font-bold text-white">{o.get("symbol")}</td>
                    <td class="py-3 px-4"><span class="px-2 py-0.5 rounded text-[11px] font-bold border {side_b}">{o.get("side")}</span></td>
                    <td class="py-3 px-4 text-gray-300 text-right">${float(o.get("price") or 0.0):,.4f}</td>
                    <td class="py-3 px-4 text-gray-400 text-right">{float(o.get("qty") or 0.0):.4f}</td>
                    <td class="py-3 px-4 text-center"><span class="px-2 py-0.5 rounded text-[11px] font-bold border {st_b}">{o.get("status")}</span></td>
                    <td class="py-3 px-4 text-white font-bold">{o.get("action")}</td>
                    <td class="py-3 px-4 text-gray-400 text-[11px] font-mono">{o.get("order_id") or "-"}</td>
                </tr>
                '''
            html = html.replace('id="user-history-tbody"><tr><td colspan="8" class="py-8 text-center text-xs text-gray-500 font-mono">Chưa có giao dịch sao chép nào được ghi nhận cho tài khoản của bạn.</td></tr></tbody>',
                                f'id="user-history-tbody">{hist_rows}</tbody>')

        # 5. Dữ liệu Donut Chart THẬT
        if user_positions:
            donut_slices = []
            colors = ["#3B82F6", "#00F0FF", "#F0B90B", "#A855F7", "#EC4899"]
            legend_html = ""
            cur_eq = max(1.0, equity_val)
            for i, p in enumerate(user_positions):
                col = colors[i % len(colors)]
                pct = round((p["margin"] / cur_eq) * 100.0, 1)
                donut_slices.append({"val": pct, "color": col, "name": p["symbol"]})
                legend_html += f'''
                <div class="flex items-center justify-between">
                    <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full" style="background:{col};"></span> {p["symbol"]} ({pct}%)</span>
                    <span class="text-gray-300 font-bold">${p["margin"]:,.2f}</span>
                </div>
                '''
            rem_pct = max(0.0, round(100.0 - sum(s["val"] for s in donut_slices), 1))
            donut_slices.append({"val": rem_pct, "color": "#0ECB81", "name": "USDT Khả Dụng"})
            legend_html += f'''
            <div class="flex items-center justify-between">
                <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-profitGreen"></span> USDT Khả Dụng ({rem_pct}%)</span>
                <span class="text-gray-300 font-bold">${balance_val:,.2f}</span>
            </div>
            '''
            html = html.replace("__USER_DONUT_SLICES_JSON__", json.dumps(donut_slices))
            html = html.replace('<div class="space-y-2 text-xs font-mono" id="user-donut-legend">.*?',
                                f'<div class="space-y-2 text-xs font-mono" id="user-donut-legend">{legend_html}')
        else:
            donut_slices = [{"val": 100, "color": "#0ECB81", "name": "USDT Khả Dụng"}]
            html = html.replace("__USER_DONUT_SLICES_JSON__", json.dumps(donut_slices))
            html = html.replace('id="donut-usdt-balance">$0.00', f'id="donut-usdt-balance">${balance_val:,.2f}')

        # 6. Dữ liệu Equity Curve THẬT
        user_series = [{"t": "Bắt đầu", "v": balance_val}]
        if user_orders and len(user_orders) > 1:
            cum = balance_val
            for o in list(reversed(user_orders))[:20]:
                c_at = str(o.get("created_at") or "")
                t_lbl = c_at[5:10].replace("-", "/") if len(c_at) >= 10 else ""
                user_series.append({"t": t_lbl, "v": round(cum, 2)})
            user_series.append({"t": "Hiện tại", "v": equity_val})
        else:
            user_series.append({"t": "Hiện tại", "v": equity_val})
        html = html.replace("__USER_EQUITY_SERIES_JSON__", json.dumps(user_series))

        # Notice script if redirected from admin
        if request.query_params.get("notice") == "admin_forbidden":
            notice_script = '''
            <script>
                window.addEventListener("DOMContentLoaded", () => {
                    setTimeout(() => {
                        if (typeof showToast === "function") {
                            showToast("🚫 Quyền truy cập bị từ chối: Trang Admin Cockpit chỉ dành riêng cho Quản trị viên hệ thống. Bạn đã được chuyển hướng về Cổng Khách Hàng cá nhân.", "error");
                        }
                    }, 400);
                });
            </script>
            </body>
            '''
            html = html.replace("</body>", notice_script)

        return HTMLResponse(content=html)

    mux = get_order_multiplexer(use_testnet=getattr(config, "use_testnet", False))
    dashboard_data = mux.get_client_dashboard_info(client_id)
    with get_db_session() as db:
        c = db.query(Client).filter(Client.id == client_id).first()
        client_dict = c.to_dict() if c else client_ctx
    return HTMLResponse(render_portal_dashboard_html(client_dict, dashboard_data))


@app.post("/api/portal/login")
async def api_portal_login(request: Request, response: Response):
    """API xác thực đăng nhập cấp JWT Token"""
    return await portal_login_action(request, response)


@app.post("/api/portal/register")
async def api_portal_register(request: Request, response: Response):
    """Đăng ký tài khoản khách hàng mới"""
    try:
        body = await request.json()
        username = str(body.get("username", "")).strip()
        email = str(body.get("email", "")).strip().lower()
        password = str(body.get("password", "")).strip()

        if len(username) < 3:
            return JSONResponse({"success": False, "message": "Tên đăng nhập phải có ít nhất 3 ký tự."}, status_code=400)
        if len(password) < 6:
            return JSONResponse({"success": False, "message": "Mật khẩu phải có ít nhất 6 ký tự."}, status_code=400)

        with get_db_session() as db:
            exist_user = db.query(Client).filter(Client.username == username).first()
            if exist_user:
                return JSONResponse({"success": False, "message": "Tên đăng nhập này đã được sử dụng."}, status_code=400)
            if email:
                exist_email = db.query(Client).filter(Client.email == email).first()
                if exist_email:
                    return JSONResponse({"success": False, "message": "Email này đã được đăng ký."}, status_code=400)

            new_client = Client(
                username=username,
                email=email if email else None,
                full_name=username,
                password_hash=hash_password(password),
                role="client",
                is_active=True
            )
            db.add(new_client)
            db.commit()
            db.refresh(new_client)

            token_payload = {
                "sub": new_client.username,
                "client_id": new_client.id,
                "role": new_client.role,
                "email": new_client.email,
                "full_name": new_client.full_name,
                "session_version": _client_session_version(new_client),
            }
            jwt_token = create_jwt_token(token_payload)

        resp = JSONResponse({
            "success": True,
            "username": username,
            "redirect": "/portal/dashboard",
            "message": "Đăng ký tài khoản thành công!"
        })
        resp.set_cookie(key="client_session_user", value=username, max_age=30 * 86400, path="/", httponly=True, samesite="lax", secure=True)
        resp.set_cookie(key="client_token", value=jwt_token, max_age=30 * 86400, path="/", httponly=True, samesite="lax", secure=True)
        return resp
    except Exception as e:
        logger.error("Lỗi đăng ký portal: %s", e)
        return JSONResponse({"success": False, "message": f"Lỗi hệ thống: {e}"}, status_code=500)


@app.post("/api/portal/logout")
async def api_portal_logout(request: Request):
    """Durably revoke the current portal JWT before deleting cookies."""
    _revoke_portal_jwt(_portal_jwt_from_request(request))
    resp = JSONResponse({"success": True, "message": "Đã đăng xuất"})
    resp.delete_cookie(key="client_session_user", path="/")
    resp.delete_cookie(key="client_token", path="/")
    return resp


@app.get("/api/portal/me")
async def api_portal_me(request: Request):
    """Lấy thông tin tài khoản hiện tại"""
    client_ctx = get_current_client_from_request(request)
    if not client_ctx:
        return JSONResponse({"authenticated": False}, status_code=401)
    return JSONResponse({"authenticated": True, "client": client_ctx})


@app.get("/api/portal/api-settings")
async def api_portal_get_api_settings(request: Request):
    """Retired credential surface remains deterministic and fail-closed."""
    if not get_current_client_from_request(request):
        return JSONResponse({"success": False, "code": "UNAUTHENTICATED"}, status_code=401)
    return _client_account_feature_disabled()


@app.post("/api/portal/api-settings")
async def api_portal_save_api_settings(request: Request):
    return await portal_api_settings_post_action(request)


@app.get("/api/portal/dashboard-data")
async def api_portal_dashboard_data(request: Request):
    """Return portal state while copy execution remains explicitly disabled."""
    client_ctx = get_current_client_from_request(request)
    if not client_ctx:
        return JSONResponse({"success": False, "message": "Chưa xác thực."}, status_code=401)
    return JSONResponse({
        "success": True,
        "copy_trading_available": False,
        "copy_trading_status": "UNAVAILABLE_DISABLED",
        "data": {"positions": [], "orders": [], "is_copy_enabled": False},
    })


@app.post("/api/portal/toggle-copy")
async def api_portal_toggle_copy(request: Request):
    if not get_current_client_from_request(request):
        return JSONResponse({"success": False, "code": "UNAUTHENTICATED"}, status_code=401)
    return _client_account_feature_disabled()


@app.post("/api/portal/close-position")
async def api_portal_close_position(request: Request):
    if not get_current_client_from_request(request):
        return JSONResponse({"success": False, "code": "UNAUTHENTICATED"}, status_code=401)
    return _client_account_feature_disabled()


@app.post("/api/portal/emergency-close-all")
async def api_portal_emergency_close_all(request: Request):
    if not get_current_client_from_request(request):
        return JSONResponse({"success": False, "code": "UNAUTHENTICATED"}, status_code=401)
    return _client_account_feature_disabled()

@app.get("/api/portal/settlements")
async def api_portal_get_settlements(request: Request):
    """Lấy lịch sử các đợt quyết toán lợi nhuận High-Water Mark của khách hàng"""
    client_ctx = get_current_client_from_request(request)
    if not client_ctx:
        return JSONResponse({"success": False, "message": "Chưa xác thực."}, status_code=401)
    try:
        client_id = client_ctx["client_id"]
        with get_db_session() as db:
            settlements = db.query(ProfitShareSettlement).filter(ProfitShareSettlement.client_id == client_id).order_by(ProfitShareSettlement.created_at.desc()).limit(20).all()
            return JSONResponse({"success": True, "settlements": [s.to_dict() for s in settlements]})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.post("/api/portal/update-copy-settings")
async def api_portal_update_copy_settings(request: Request):
    if not get_current_client_from_request(request):
        return JSONResponse({"success": False, "code": "UNAUTHENTICATED"}, status_code=401)
    return _client_account_feature_disabled()


@app.get("/api/affiliate/programs")
async def api_get_affiliate_programs():
    """Danh mục các chương trình Affiliate tối ưu lợi nhuận có thể kích hoạt với Binance"""
    return JSONResponse({
        "success": True,
        "active_programs": [
            {
                "name": "Binance Refer-to-Earn USDC",
                "type": "Pool & Welcome Voucher",
                "referral_id": "GRO_28502_SKWHI",
                "claim_url": "https://www.binance.com/referral/earn-together/refer2earn-usdc/claim?hl=vi&ref=GRO_28502_SKWHI&utm_source=referral_entrance",
                "benefit_referee": "Lên đến 100 USDC Voucher & quà chào mừng",
                "benefit_referrer": "Chia sẻ Pool thưởng USDC cùng bạn bè",
                "status": "ACTIVE"
            },
            {
                "name": "Binance Futures Broker Rebate",
                "type": "Cashback Hoàn Phí",
                "referral_id": "GRO_28502_SKWHI",
                "claim_url": "https://trader.noza.site/",
                "benefit_referee": "Hoàn 20% phí giao dịch phái sinh Futures trọn đời",
                "benefit_referrer": "Tích lũy hoa hồng trọn đời từ volume giao dịch",
                "status": "ACTIVE"
            },
            {
                "name": "Binance Lead Trader Profit Sharing",
                "type": "Copy Trading (Unavailable)",
                "profit_share_rate": None,
                "settlement_cycle": None,
                "benefit_lead_trader": "Unavailable in this deployment",
                "benefit_copier": "Copy-trade execution is disabled pending separate certification",
                "status": "UNAVAILABLE_DISABLED"
            }
        ]
    })


# --- Phân hệ 4: Pháp Lý & Cảnh Báo Rủi Ro ---
@app.get("/risk-warning", response_class=HTMLResponse)
async def risk_warning_view():
    if is_ui_v2_enabled():
        return render_ui_v2_template("ui_v2/risk_warning.html")
    p = os.path.join(os.path.dirname(__file__), "templates", "risk_warning.html")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Cảnh báo rủi ro đầu tư phái sinh</h1>")


@app.get("/terms", response_class=HTMLResponse)
async def terms_view():
    if is_ui_v2_enabled():
        return render_ui_v2_template("ui_v2/terms.html")
    p = os.path.join(os.path.dirname(__file__), "templates", "terms.html")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Điều khoản sử dụng dịch vụ</h1>")


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_view():
    if is_ui_v2_enabled():
        return render_ui_v2_template("ui_v2/privacy.html")
    p = os.path.join(os.path.dirname(__file__), "templates", "privacy.html")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Chính sách bảo mật dữ liệu phi lưu ký</h1>")


# --- Phân hệ 5: Phân Quyền Admin Cockpit & Quản Lý Đa Khách Hàng (RBAC) ---
@app.get("/admin", response_class=HTMLResponse)
async def admin_cockpit_page(request: Request):
    """
    Bảng điều khiển kỹ thuật cao dành RIÊNG cho Quản trị viên (Admin Cockpit).
    Khách hàng (Client role) bị CHẶN TUYỆT ĐỐI và tự động điều hướng về Portal cá nhân.
    """
    # 1. Kiểm tra nếu đang đăng nhập tài khoản Khách hàng thường (như huy123456)
    client_ctx = get_current_client_from_request(request)
    if client_ctx and client_ctx.get("role") != "admin":
        logger.warning("🚫 [SECURITY] Khách hàng %s (role=%s) cố gắng truy cập Admin Cockpit! Chặn và điều hướng.",
                       client_ctx.get("username"), client_ctx.get("role"))
        return RedirectResponse(url="/portal/dashboard?notice=admin_forbidden", status_code=303)

    # 2. Kiểm tra quyền Quản trị viên
    if not is_admin_request(request):
        return RedirectResponse(url="/portal/login?next=/admin", status_code=303)

    return await dashboard_page()


@app.get("/api/admin/clients")
async def api_admin_get_clients(request: Request):
    """Return the Portal account directory without credential/copy metadata."""
    if not is_admin_request(request):
        return JSONResponse({"success": False, "message": "Yêu cầu quyền Quản trị viên (Admin)."}, status_code=403)

    with get_db_session() as db:
        clients = db.query(Client).all()
        result = []
        for client in clients:
            orders_count = db.query(ClientOrderLog).filter(
                ClientOrderLog.client_id == client.id
            ).count()
            result.append({
                "id": client.id,
                "username": client.username,
                "full_name": getattr(client, "full_name", None) or client.username,
                "email": client.email,
                "role": client.role,
                "is_active": client.is_active,
                "created_at": client.created_at.isoformat() if client.created_at else None,
                "client_trading": {
                    "available": False,
                    "state": "FEATURE_DISABLED",
                },
                "total_orders": orders_count,
            })
        return JSONResponse({
            "success": True,
            "total_clients": len(result),
            "active_copy_traders": 0,
            "total_allocated_margin": 0.0,
            "clients": result,
        })


@app.post("/api/admin/clients/{target_client_id}/toggle-copy")
async def api_admin_toggle_client_copy(target_client_id: int, request: Request):
    del target_client_id
    if not is_admin_request(request):
        return JSONResponse({"success": False, "message": "Yêu cầu quyền Quản trị viên (Admin)."}, status_code=403)
    return _client_account_feature_disabled()
@app.post("/api/admin/clients/{target_client_id}/settle")
async def api_admin_settle_client_profit(target_client_id: int, request: Request):
    """API dành riêng cho Admin: Thực hiện quyết toán High-Water Mark (HWM) chu kỳ hàng tuần cho khách hàng"""
    if not is_admin_request(request):
        return JSONResponse({"success": False, "message": "Yêu cầu quyền Quản trị viên (Admin)."}, status_code=403)
    try:
        body = await request.json() if "application/json" in request.headers.get("content-type", "") else {}
        note = body.get("note", "Quyết toán định kỳ Admin")
        mux = get_order_multiplexer(use_testnet=getattr(config, "use_testnet", False))
        res = mux.settle_profit_share(target_client_id, note=note)
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.get("/api/admin/settlements")
async def api_admin_get_all_settlements(request: Request):
    """API dành riêng cho Admin: Xem toàn bộ lịch sử quyết toán chia sẻ lợi nhuận HWM"""
    if not is_admin_request(request):
        return JSONResponse({"success": False, "message": "Yêu cầu quyền Quản trị viên (Admin)."}, status_code=403)
    with get_db_session() as db:
        settlements = (
            db.query(ProfitShareSettlement)
            .order_by(ProfitShareSettlement.created_at.desc())
            .limit(100)
            .all()
        )
        res = []
        for s in settlements:
            c = db.query(Client).filter(Client.id == s.client_id).first()
            d = s.to_dict()
            d["username"] = c.username if c else f"Client #{s.client_id}"
            d["full_name"] = getattr(c, "full_name", None) or d["username"]
            res.append(d)
        return JSONResponse({"success": True, "settlements": res})


@app.post("/api/admin/clients/{target_client_id}/update-ratio")
async def api_admin_update_profit_ratio(target_client_id: int, request: Request):
    """API dành riêng cho Admin: Cập nhật tỷ lệ chia sẻ lợi nhuận cho khách hàng (chuẩn 10% - 20%)"""
    if not is_admin_request(request):
        return JSONResponse({"success": False, "message": "Yêu cầu quyền Quản trị viên (Admin)."}, status_code=403)
    try:
        body = await request.json()
        raw_ratio = body.get("profit_share_ratio")
        if isinstance(raw_ratio, bool) or not isinstance(raw_ratio, (int, float)):
            return JSONResponse({"success": False, "message": "Tỷ lệ chia sẻ lợi nhuận phải là số hữu hạn."}, status_code=400)
        ratio = _strict_handler_float(raw_ratio, "profit_share_ratio", positive=True)
        if ratio > 0.20 or ratio < 0.10:
            return JSONResponse({"success": False, "message": "Tỷ lệ chia sẻ lợi nhuận phải nằm trong khoảng 10% đến 20%."}, status_code=400)
        with get_db_session() as db:
            c = db.query(Client).filter(Client.id == target_client_id).first()
            if not c:
                return JSONResponse({"success": False, "message": "Không tìm thấy khách hàng."}, status_code=404)
            c.profit_share_ratio = ratio
            # Profit-sharing is client accounting metadata, not credential configuration.
            db.commit()
        return JSONResponse({"success": True, "message": f"Đã cập nhật tỷ lệ chia sẻ lợi nhuận thành {ratio * 100:.1f}%", "profit_share_ratio": ratio})
    except (TypeError, ValueError, OverflowError) as exc:
        return JSONResponse({"success": False, "message": str(exc)}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)



@app.get("/", response_class=HTMLResponse)
async def root_dispatch_page(request: Request):
    """Trang chủ Astra Quant Labs (giống 100% trader.noza.site)"""
    admin_token = request.cookies.get("session_token")
    if admin_token and is_valid_session_token(admin_token):
        if is_ui_v2_enabled():
            return RedirectResponse(url="/portal/dashboard", status_code=302)
        return await dashboard_page()

    if is_ui_v2_enabled():
        return render_ui_v2_template("ui_v2/landing.html")

    t_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(t_path):
        with open(t_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return await dashboard_page()



async def dashboard_page():
    """Giao diện Web Dashboard Siêu Hiện Đại (Institutional Grade) - Dark Glassmorphism"""
    html_content = f"""<!DOCTYPE html>
<html lang="vi" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta name="theme-color" content="#F0B90B">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>Binance Futures Quant Pro Terminal</title>
    <link rel="icon" type="image/png" href="/logo.png">
    <link rel="manifest" href="/manifest.json">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Inter', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace']
                    }},
                    colors: {{
                        darkBase: '#080a0f',
                        darkCard: '#10141e',
                        darkCardHover: '#141a27',
                        darkBorder: '#1c2436',
                        binanceGold: '#F0B90B',
                        profitGreen: '#0ECB81',
                        lossRed: '#F6465D',
                        cyberCyan: '#00F0FF',
                        cyberPurple: '#A855F7'
                    }}
                }}
            }}
        }}
    </script>
    <style>
        html, body {{
            overflow-x: hidden;
            width: 100%;
            max-width: 100%;
            -webkit-text-size-adjust: 100%;
        }}
        input, select, textarea {{
            touch-action: auto;
        }}
        ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        ::-webkit-scrollbar-track {{ background: #080a0f; }}
        ::-webkit-scrollbar-thumb {{ background: #1c2436; border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #F0B90B; }}

        .glass-panel {{
            background: rgba(16, 20, 30, 0.75);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.07);
        }}
        .glass-card {{
            background: rgba(18, 23, 35, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.06);
            transition: all 0.2s ease-in-out;
        }}
        .glass-card:hover {{
            border-color: rgba(240, 185, 11, 0.3);
            transform: translateY(-2px);
        }}
        .glow-green {{ box-shadow: 0 0 20px rgba(14, 203, 129, 0.2); }}
        .glow-red {{ box-shadow: 0 0 20px rgba(246, 70, 93, 0.2); }}
        .glow-gold {{ box-shadow: 0 0 20px rgba(240, 185, 11, 0.25); }}

        /* Advanced Mascot Interactive Keyframes (Inspired by page-mascot) */
        @keyframes float-robot {{
            0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
            50% {{ transform: translateY(-8px) rotate(1.2deg); }}
        }}
        @keyframes ear-twitch-left {{
            0%, 85%, 100% {{ transform: rotate(0deg); }}
            90% {{ transform: rotate(-8deg); }}
            95% {{ transform: rotate(3deg); }}
        }}
        @keyframes ear-twitch-right {{
            0%, 88%, 100% {{ transform: rotate(0deg); }}
            93% {{ transform: rotate(8deg); }}
            97% {{ transform: rotate(-2deg); }}
        }}
        @keyframes mascot-squish {{
            0% {{ transform: scale(1) translateY(0); }}
            20% {{ transform: scale(1.18, 0.82) translateY(4px); }}
            45% {{ transform: scale(0.92, 1.15) translateY(-14px) rotate(3deg); }}
            70% {{ transform: scale(1.06, 0.95) translateY(2px) rotate(-1.5deg); }}
            85% {{ transform: scale(0.98, 1.02) translateY(-2px); }}
            100% {{ transform: scale(1) translateY(0); }}
        }}
        @keyframes eye-glow {{
            0%, 100% {{ opacity: 1; filter: drop-shadow(0 0 7px currentColor); }}
            50% {{ opacity: 0.7; filter: drop-shadow(0 0 2px currentColor); }}
        }}
        @keyframes orbit-drone {{
            0% {{ transform: rotate(0deg) translateX(42px) rotate(0deg); }}
            100% {{ transform: rotate(360deg) translateX(42px) rotate(-360deg); }}
        }}
        @keyframes mouth-wave {{
            0%, 100% {{ height: 3px; }}
            50% {{ height: 9px; }}
        }}
        @keyframes antenna-pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); filter: drop-shadow(0 0 6px #F0B90B); }}
            50% {{ opacity: 0.4; transform: scale(0.8); filter: drop-shadow(0 0 1px #F0B90B); }}
        }}
        @keyframes laser-sweep {{
            0% {{ transform: translateX(-30px); opacity: 0; }}
            30% {{ opacity: 0.9; }}
            70% {{ opacity: 0.9; }}
            100% {{ transform: translateX(30px); opacity: 0; }}
        }}
        @keyframes zzz-float {{
            0% {{ transform: translate(0, 0) scale(0.6); opacity: 0; }}
            50% {{ opacity: 0.9; }}
            100% {{ transform: translate(12px, -22px) scale(1.2); opacity: 0; }}
        }}
        @keyframes particle-burst {{
            0% {{ transform: translate(0, 0) scale(1); opacity: 1; }}
            100% {{ transform: translate(var(--tx), var(--ty)) scale(0); opacity: 0; }}
        }}
        .mascot-floating {{ animation: float-robot 3.5s infinite ease-in-out; }}
        .mascot-ear-l {{ transform-origin: 26px 36px; animation: ear-twitch-left 4.5s infinite ease-in-out; }}
        .mascot-ear-r {{ transform-origin: 74px 36px; animation: ear-twitch-right 5.2s infinite ease-in-out; }}
        .mascot-squishing {{ animation: mascot-squish 0.65s cubic-bezier(0.25, 1, 0.5, 1); }}
        .drone-orbit {{ animation: orbit-drone 7s infinite linear; }}
        .antenna-dot {{ animation: antenna-pulse 1.8s infinite ease-in-out; }}
        .laser-sweep-line {{ animation: laser-sweep 2.2s infinite ease-in-out; }}
        .zzz-item-1 {{ animation: zzz-float 2.4s infinite ease-out; }}
        .zzz-item-2 {{ animation: zzz-float 2.4s infinite ease-out 0.8s; }}
        .mouth-bar-1 {{ animation: mouth-wave 0.8s infinite ease-in-out; }}
        .mouth-bar-2 {{ animation: mouth-wave 0.6s infinite ease-in-out 0.15s; }}
        .mouth-bar-3 {{ animation: mouth-wave 0.9s infinite ease-in-out 0.3s; }}
        .mouth-bar-4 {{ animation: mouth-wave 0.7s infinite ease-in-out 0.1s; }}
        .burst-particle {{ position: absolute; pointer-events: none; animation: particle-burst 0.75s forwards cubic-bezier(0, 0.9, 0.57, 1); font-size: 14px; }}
        .mascot-pupil {{ transition: transform 0.08s cubic-bezier(0.2, 0.8, 0.4, 1); }}
        .mascot-head-tilt {{ transition: transform 0.12s cubic-bezier(0.2, 0.8, 0.4, 1); transform-style: preserve-3d; }}
        .mascot-eyelid {{ transition: transform 0.09s ease-in-out; }}
        /* Unified dark responsive shell: desktop + mobile */
        *, *::before, *::after {{ box-sizing: border-box; }}
        img, svg, canvas {{ max-width: 100%; }}
        button, a, input, select {{ -webkit-tap-highlight-color: transparent; }}
        button, a {{ touch-action: manipulation; }}
        #workspace {{ width: 100%; min-width: 0; }}
        .glass-card, .glass-panel {{ min-width: 0; }}
        .no-scrollbar {{ scrollbar-width: none; }}
        .no-scrollbar::-webkit-scrollbar {{ display: none; }}

        @media (max-width: 767px) {{
            #admin-header-inner {{
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
                gap: 0.5rem !important;
                min-width: 0;
            }}
            #admin-brand-text p {{ display: none !important; }}
            #admin-brand-text .admin-brand-name {{ font-size: 0.75rem !important; }}
            #admin-header-actions {{
                margin-left: auto;
                max-width: calc(100vw - 150px);
                overflow: hidden;
                gap: 0.35rem !important;
            }}
            #admin-header-actions > button {{
                width: 2.25rem !important;
                height: 2.25rem !important;
                min-width: 2.25rem !important;
            }}
            #workspace {{
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
                padding-top: 0.875rem !important;
                padding-bottom: calc(5.25rem + env(safe-area-inset-bottom)) !important;
            }}
            #workspace .glass-card {{ border-radius: 1rem !important; }}
            #workspace .grid.grid-cols-2 {{ gap: 0.65rem !important; }}
            #workspace .text-3xl {{ font-size: 1.4rem !important; line-height: 1.75rem !important; }}
            .mobile-bottom-btn {{ min-height: 3.25rem; border-radius: 0.75rem; }}
            .mobile-bottom-btn:active {{ background: rgba(240,185,11,.10); transform: scale(.97); }}
            nav.fixed.bottom-0 {{ padding-bottom: calc(0.375rem + env(safe-area-inset-bottom)); }}
            #settings-modal > div,
            #ai-chat-modal > div,
            #tv-chart-modal > div,
            #analytics-modal > div,
            #backtest-modal > div {{
                max-width: 100% !important;
                max-height: calc(100dvh - 1rem) !important;
                border-radius: 1rem !important;
            }}
            .mascot-floating, .drone-orbit, .antenna-dot, .laser-sweep-line {{ animation-duration: 6s !important; }}
        }}

        @media (max-width: 380px) {{
            #admin-brand-text {{ display: none !important; }}
            #admin-header-actions {{ max-width: calc(100vw - 64px); }}
            #workspace .grid.grid-cols-2 {{ grid-template-columns: minmax(0, 1fr) !important; }}
            #workspace .glass-card {{ padding: 0.875rem !important; }}
            .mobile-bottom-btn span {{ font-size: 0.5rem !important; }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{ scroll-behavior: auto !important; animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }}
        }}
    </style>
</head>
<body class="bg-darkBase text-gray-200 font-sans min-h-screen antialiased selection:bg-binanceGold selection:text-black">

    <!-- Cyberpunk Glassmorphism Login Modal -->
    <div id="login-modal" class="fixed inset-0 z-[9999] bg-black/90 backdrop-blur-md flex items-center justify-center p-4 transition-all duration-300 hidden">
        <div class="relative w-full max-w-md bg-darkCard/95 border border-binanceGold/40 rounded-3xl p-6 sm:p-8 shadow-2xl shadow-yellow-500/10 backdrop-blur-xl">
            <!-- Glow ornament -->
            <div class="absolute -top-10 -left-10 w-32 h-32 bg-binanceGold/15 rounded-full blur-3xl pointer-events-none"></div>
            <div class="absolute -bottom-10 -right-10 w-32 h-32 bg-cyan-500/15 rounded-full blur-3xl pointer-events-none"></div>

            <div class="flex items-center space-x-3 mb-6">
                <div class="w-12 h-12 rounded-2xl bg-binanceGold/10 border border-binanceGold/30 flex items-center justify-center text-binanceGold text-2xl shadow-inner">
                    <i class="fa-solid fa-shield-halved"></i>
                </div>
                <div>
                    <h2 class="text-xl font-black tracking-wider text-white flex items-center gap-2">
                        <span>BINANCE QUANT PRO</span>
                    </h2>
                    <p class="text-xs text-gray-400">Hệ Thống Quản Trị Định Lượng Độc Lập</p>
                </div>
            </div>

            <!-- Telegram WebApp 1-Click login banner (visible when in Telegram Mini App) -->
            <div id="tg-webapp-card" class="hidden mb-5 p-4 rounded-2xl bg-gradient-to-r from-blue-900/30 to-cyan-900/30 border border-cyan-500/40 text-left">
                <div class="flex items-center gap-3">
                    <i class="fa-brands fa-telegram text-2xl text-cyan-400"></i>
                    <div class="flex-1 min-w-0">
                        <p class="text-xs font-semibold text-white truncate" id="tg-user-greeting">Phát hiện Telegram Mini App</p>
                        <p class="text-[11px] text-gray-400">Đăng nhập tự động bằng danh tính Telegram đã ủy quyền</p>
                    </div>
                </div>
                <button type="button" onclick="loginWithTelegramWebApp()" class="mt-3 w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white text-xs font-bold transition flex items-center justify-center gap-2 shadow-lg shadow-cyan-900/40 active:scale-95">
                    <i class="fa-solid fa-bolt"></i> <span>Đăng Nhập 1-Chạm Bằng Telegram</span>
                </button>
            </div>

            <div id="login-divider" class="hidden relative items-center justify-center my-4">
                <div class="border-t border-gray-800 w-full"></div>
                <span class="absolute px-3 bg-darkCard text-[10px] text-gray-500 uppercase tracking-wider">Hoặc nhập mật khẩu</span>
            </div>

            <form id="login-form" onsubmit="handleManualLogin(event)" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold text-gray-300 mb-1.5 flex items-center gap-1.5">
                        <i class="fa-solid fa-user text-[11px] text-binanceGold"></i> Tên Đăng Nhập
                    </label>
                    <input type="text" id="login-username" required placeholder="admin" autocomplete="username"
                        class="w-full bg-darkBase/90 border border-darkBorder focus:border-binanceGold focus:outline-none rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 transition" />
                </div>
                <div>
                    <label class="block text-xs font-semibold text-gray-300 mb-1.5 flex items-center gap-1.5">
                        <i class="fa-solid fa-lock text-[11px] text-binanceGold"></i> Mật Khẩu Quản Trị
                    </label>
                    <input type="password" id="login-password" required placeholder="••••••••" autocomplete="current-password"
                        class="w-full bg-darkBase/90 border border-darkBorder focus:border-binanceGold focus:outline-none rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 transition" />
                </div>

                <div id="login-error-msg" class="hidden p-3 rounded-xl bg-red-950/60 border border-red-800/80 text-xs text-red-300 flex items-center gap-2">
                    <i class="fa-solid fa-circle-exclamation text-red-400"></i>
                    <span id="login-error-text">Sai thông tin đăng nhập!</span>
                </div>

                <button type="submit" id="login-submit-btn" class="w-full py-3.5 px-4 rounded-xl bg-binanceGold hover:bg-yellow-400 text-black font-extrabold text-sm transition shadow-lg shadow-yellow-500/20 active:scale-95 flex items-center justify-center gap-2">
                    <i class="fa-solid fa-arrow-right-to-bracket"></i>
                    <span>ĐĂNG NHẬP VÀO DASHBOARD</span>
                </button>
            </form>

            <div class="mt-6 pt-4 border-t border-darkBorder text-center">
                <p class="text-[11px] text-gray-400 flex items-center justify-center gap-1.5">
                    <i class="fa-solid fa-lock text-binanceGold text-[10px]"></i>
                    Phiên đăng nhập được bảo mật mã hóa 256-bit trong 30 ngày
                </p>
            </div>
        </div>
    </div>

    <!-- Holographic 3D Virtual Trading Desk & Spatial AI Avatar Modal (Three.js WebGL) -->
    <div id="holographic-3d-modal" class="fixed inset-0 z-[1000] bg-black/95 backdrop-blur-xl hidden flex flex-col select-none overflow-hidden">
        <!-- Top 3D Control Bar -->
        <div class="h-14 px-4 sm:px-6 bg-darkCard/90 border-b border-cyan-800/60 flex items-center justify-between z-20 backdrop-blur-md">
            <div class="flex items-center space-x-3">
                <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 to-cyan-500 text-white flex items-center justify-center text-sm shadow-lg shadow-cyan-950/60">
                    <i class="fa-solid fa-cube"></i>
                </div>
                <div>
                    <h2 class="font-extrabold text-sm sm:text-base text-white flex items-center gap-2 font-sans">
                        <span>HOLOGRAPHIC 3D VIRTUAL TRADING DESK</span>
                        <span class="px-2 py-0.5 rounded text-[9px] font-bold bg-cyan-950 text-cyberCyan border border-cyan-700/60 uppercase">WebGL Three.js</span>
                    </h2>
                    <p class="text-[10px] text-gray-400 font-sans">Không gian thực tế ảo 3D tương tác đa chiều • Linh vật Spatial Cyber-Nova</p>
                </div>
            </div>
            <!-- Action buttons -->
            <div class="flex items-center gap-2 font-sans">
                <button type="button" onclick="trigger3DEnergyPulse()" class="px-3 py-1.5 rounded-xl bg-cyan-950 hover:bg-cyan-900/60 text-cyberCyan border border-cyan-700/50 text-xs font-bold transition flex items-center gap-1.5 shadow-md active:scale-95">
                    <i class="fa-solid fa-wand-magic-sparkles"></i> <span class="hidden sm:inline">Phát Xung Năng Lượng</span>
                </button>
                <button type="button" onclick="reset3DCamera()" class="px-3 py-1.5 rounded-xl bg-darkBase hover:bg-gray-800 text-gray-300 text-xs font-semibold border border-darkBorder transition flex items-center gap-1">
                    <i class="fa-solid fa-camera-rotate"></i> <span class="hidden sm:inline">Góc Nhìn Gốc</span>
                </button>
                <button type="button" onclick="closeHolographicDesk()" class="w-9 h-9 rounded-xl bg-lossRed/20 hover:bg-lossRed text-lossRed hover:text-white border border-red-500/50 flex items-center justify-center transition active:scale-95" title="Đóng phòng ảo 3D">
                    <i class="fa-solid fa-xmark text-base"></i>
                </button>
            </div>
        </div>

        <!-- 3D WebGL Canvas Viewport -->
        <div class="flex-1 relative w-full h-full bg-[#050811] overflow-hidden" id="holo-3d-viewport">
            <canvas id="holo-3d-canvas" class="w-full h-full block cursor-grab active:cursor-grabbing"></canvas>

            <!-- Floating Spatial AI HUD Dialog in 3D -->
            <div class="absolute bottom-6 left-4 right-4 sm:left-6 sm:right-auto sm:max-w-md p-4 rounded-2xl glass-panel border border-cyan-500/50 shadow-2xl space-y-2 pointer-events-auto bg-[#090e1a]/85 backdrop-blur-lg">
                <div class="flex items-center justify-between pb-1.5 border-b border-darkBorder">
                    <span class="font-bold text-xs text-cyberCyan flex items-center gap-1.5 font-sans">
                        <span class="w-2 h-2 rounded-full bg-cyberCyan animate-ping"></span>
                        <span>CYBER-NOVA SPATIAL AI 12.0</span>
                    </span>
                    <span class="text-[9px] px-2 py-0.5 rounded font-mono bg-purple-950 text-purple-300 border border-purple-700/50">3D HOLOGRAM ACTIVE</span>
                </div>
                <p id="holo-speech-text" class="text-xs text-gray-100 leading-relaxed font-sans">
                    "Chào Sếp! Chào mừng Sếp tới Phòng Giao Dịch Ảo Không Gian 3D Holographic. Toàn bộ thanh khoản thị trường và danh mục của Sếp đang được chiếu lập thể trong thời gian thực!"
                </p>
                <div class="text-[10px] text-gray-400 flex items-center justify-between pt-1 font-mono">
                    <span>Chuột trái/Chạm: Xoay 3D | Cuộn: Thu/Phóng</span>
                    <span class="text-binanceGold">Three.js R128</span>
                </div>
            </div>

            <!-- Floating 3D Live Stat Badges in Corners -->
            <div class="absolute top-4 left-4 hidden md:flex flex-col gap-2 pointer-events-none">
                <div class="p-2.5 rounded-xl glass-panel border border-darkBorder text-xs text-gray-300 font-mono space-y-1">
                    <div class="text-[10px] uppercase text-gray-400 font-sans font-bold">Thanh Khoản Lập Thể:</div>
                    <div class="text-profitGreen font-extrabold flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-profitGreen"></span> BTC: $76,500+</div>
                    <div class="text-cyberCyan font-extrabold flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-cyberCyan"></span> ETH: $2,420+</div>
                    <div class="text-binanceGold font-extrabold flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-binanceGold"></span> SOL: $102+</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Toast Notification Container -->
    <div id="toast-container" class="fixed top-5 right-5 z-[9999] flex flex-col gap-2 pointer-events-none"></div>

    <!-- Confirm Modal -->
    <div id="confirm-modal" class="fixed inset-0 z-[999] bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="glass-panel max-w-md w-full p-6 rounded-2xl border border-lossRed/40 shadow-2xl space-y-4">
            <div class="w-12 h-12 rounded-full bg-red-500/20 text-lossRed flex items-center justify-center text-2xl mx-auto">
                <i class="fa-solid fa-triangle-exclamation"></i>
            </div>
            <div class="text-center">
                <h3 class="text-lg font-bold text-white" id="modal-title">Xác nhận đóng khẩn cấp</h3>
                <p class="text-sm text-gray-400 mt-2" id="modal-desc">Bạn có chắc chắn muốn đóng toàn bộ vị thế đang mở bằng lệnh Market?</p>
            </div>
            <div class="flex gap-3 pt-2">
                <button onclick="closeConfirmModal()" class="flex-1 py-2.5 rounded-xl text-sm font-semibold bg-gray-800 hover:bg-gray-700 text-gray-300 transition">Hủy bỏ</button>
                <button id="modal-confirm-btn" class="flex-1 py-2.5 rounded-xl text-sm font-bold bg-lossRed hover:bg-red-700 text-white shadow-lg shadow-red-900/40 transition">XÁC NHẬN ĐÓNG</button>
            </div>
        </div>
    </div>

    <!-- Live Settings Modal -->
    <div id="settings-modal" class="fixed inset-0 z-[998] bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-3 sm:p-4">
        <div class="glass-panel max-w-lg w-full max-h-[92vh] overflow-y-auto p-5 sm:p-6 rounded-2xl border border-binanceGold/30 shadow-2xl space-y-4 sm:space-y-5">
            <div class="flex justify-between items-center pb-3 border-b border-darkBorder">
                <div class="flex items-center space-x-2">
                    <i class="fa-solid fa-sliders text-binanceGold text-lg"></i>
                    <h3 class="text-base font-bold text-white">CẤU HÌNH HỆ THỐNG THỜI GIAN THỰC</h3>
                </div>
                <button onclick="closeSettingsModal()" class="text-gray-400 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
            </div>

            <div class="space-y-4 text-xs">
                <!-- Trading Mode Selector -->
                <div>
                    <label class="block font-semibold text-gray-300 mb-2">Chế độ giao dịch thị trường:</label>
                    <div class="grid grid-cols-2 gap-3">
                        <button type="button" onclick="selectTradingMode('BLUECHIP_ONLY')" id="opt-mode-bluechip" class="p-3 rounded-xl border text-left flex flex-col justify-between transition border-darkBorder bg-darkBase text-gray-300">
                            <span class="font-bold flex items-center gap-1.5 text-sm">
                                <span>🛡️</span> Chỉ BTC & ETH
                            </span>
                            <span class="text-[10px] text-gray-500 mt-1">An toàn tuyệt đối, thanh khoản sâu, ít giật râu.</span>
                        </button>
                        <button type="button" onclick="selectTradingMode('MARKET_ALL')" id="opt-mode-all" class="p-3 rounded-xl border text-left flex flex-col justify-between transition border-binanceGold bg-yellow-950/20 text-binanceGold">
                            <span class="font-bold flex items-center gap-1.5 text-sm">
                                <span>🚀</span> Toàn Bộ Altcoin / Meme
                            </span>
                            <span class="text-[10px] text-gray-400 mt-1">Quét top 50 coin, biên độ sóng lớn (10-30%).</span>
                        </button>
                    </div>
                </div>

                <!-- Leverage Selector -->
                <div>
                    <label class="block font-semibold text-gray-300 mb-2">Đòn bẩy giao dịch (Leverage):</label>
                    <div class="grid grid-cols-4 gap-2">
                        <button type="button" onclick="selectLeverage(3)" id="opt-lev-3" class="py-2 rounded-lg font-mono font-bold border border-darkBorder bg-darkBase text-gray-300">3x</button>
                        <button type="button" onclick="selectLeverage(5)" id="opt-lev-5" class="py-2 rounded-lg font-mono font-bold border border-binanceGold bg-yellow-950/30 text-binanceGold">5x</button>
                        <button type="button" onclick="selectLeverage(10)" id="opt-lev-10" class="py-2 rounded-lg font-mono font-bold border border-darkBorder bg-darkBase text-gray-300">10x</button>
                        <button type="button" onclick="selectLeverage(15)" id="opt-lev-15" class="py-2 rounded-lg font-mono font-bold border border-darkBorder bg-darkBase text-gray-300">15x</button>
                    </div>
                </div>

                <!-- Risk Percent Selector -->
                <div>
                    <label class="block font-semibold text-gray-300 mb-2">Mức rủi ro tối đa mỗi lệnh (% Vốn):</label>
                    <div class="grid grid-cols-4 gap-2">
                        <button type="button" onclick="selectRisk(0.5)" id="opt-risk-05" class="py-2 rounded-lg font-mono font-bold border border-darkBorder bg-darkBase text-gray-300">0.5%</button>
                        <button type="button" onclick="selectRisk(1.0)" id="opt-risk-10" class="py-2 rounded-lg font-mono font-bold border border-profitGreen bg-green-950/30 text-profitGreen">1.0%</button>
                        <button type="button" onclick="selectRisk(1.5)" id="opt-risk-15" class="py-2 rounded-lg font-mono font-bold border border-darkBorder bg-darkBase text-gray-300">1.5%</button>
                        <button type="button" onclick="selectRisk(2.0)" id="opt-risk-20" class="py-2 rounded-lg font-mono font-bold border border-darkBorder bg-darkBase text-gray-300">2.0%</button>
                    </div>
                </div>

                <!-- Trailing Stop Toggle -->
                <div class="flex items-center justify-between p-3 rounded-xl bg-darkBase border border-darkBorder">
                    <div>
                        <p class="font-bold text-white text-xs">Dynamic Trailing Stop Loss 🚀</p>
                        <p class="text-[10px] text-gray-400">Tự động dâng SL theo đà tăng để khóa chặt lợi nhuận.</p>
                    </div>
                    <label class="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" id="chk-trailing-stop" class="sr-only peer" checked>
                        <div class="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-profitGreen"></div>
                    </label>
                </div>

                <!-- Strategy Engine Selector -->
                <div>
                    <label class="block font-semibold text-gray-300 mb-2">Chiến lược giao dịch lượng tử:</label>
                    <div class="grid grid-cols-2 gap-2.5">
                        <button type="button" onclick="selectStrategy('AUTO_DYNAMIC')" id="opt-strat-auto" class="p-2.5 rounded-xl border text-left flex flex-col justify-between transition border-binanceGold bg-yellow-950/20 text-binanceGold">
                            <span class="font-bold flex items-center gap-1.5 text-xs">
                                <span>🚀</span> Auto Dynamic
                            </span>
                            <span class="text-[9px] text-gray-400 mt-0.5">Tự thích ứng Trend + Breakout + Mean Rev</span>
                        </button>
                        <button type="button" onclick="selectStrategy('TREND_PULLBACK')" id="opt-strat-trend" class="p-2.5 rounded-xl border text-left flex flex-col justify-between transition border-darkBorder bg-darkBase text-gray-300">
                            <span class="font-bold flex items-center gap-1.5 text-xs">
                                <span>📈</span> Trend Pullback
                            </span>
                            <span class="text-[9px] text-gray-400 mt-0.5">Hồi EMA & RSI khi ADX mạnh ≥ 20</span>
                        </button>
                        <button type="button" onclick="selectStrategy('BREAKOUT')" id="opt-strat-breakout" class="p-2.5 rounded-xl border text-left flex flex-col justify-between transition border-darkBorder bg-darkBase text-gray-300">
                            <span class="font-bold flex items-center gap-1.5 text-xs">
                                <span>💥</span> Breakout & Volume
                            </span>
                            <span class="text-[9px] text-gray-400 mt-0.5">Phá đỉnh/đáy 20 nến + Vol Spike x2.0</span>
                        </button>
                        <button type="button" onclick="selectStrategy('MEAN_REVERSION')" id="opt-strat-mean" class="p-2.5 rounded-xl border text-left flex flex-col justify-between transition border-darkBorder bg-darkBase text-gray-300">
                            <span class="font-bold flex items-center gap-1.5 text-xs">
                                <span>🎯</span> Mean Reversion
                            </span>
                            <span class="text-[9px] text-gray-400 mt-0.5">Bắt đáy đỉnh Bollinger khi Sideway</span>
                        </button>
                    </div>
                </div>

                <!-- Real Trading Hard Capital Cap -->
                <div class="p-3 rounded-xl bg-darkBase border border-darkBorder flex items-center justify-between">
                    <div>
                        <p class="font-bold text-white text-xs">Giới hạn vốn Live (Hard Capital Cap) 🛡️</p>
                        <p class="text-[10px] text-gray-400">Giới hạn số dư tối đa bot được phép sử dụng khi Live ($).</p>
                    </div>
                    <div class="w-28">
                        <input type="number" id="input-hard-cap" min="10" max="10000" step="10" value="100" class="w-full bg-darkCard border border-darkBorder rounded-lg px-2.5 py-1.5 text-xs text-white font-mono text-center focus:border-binanceGold focus:outline-none">
                    </div>
                </div>

                <!-- AI Copilot Dual Engine Configuration -->
                <div class="p-3.5 rounded-xl bg-darkBase border border-cyan-900/40 space-y-3">
                    <div class="flex justify-between items-center">
                        <label class="font-bold text-white text-xs flex items-center gap-1.5">
                            <i class="fa-solid fa-brain text-cyberCyan"></i> Trí Tuệ Nhân Tạo (Dual AI Engine)
                        </label>
                        <span class="text-[10px] text-cyberCyan bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40 font-mono">DeepSeek V4.1 + Gemini</span>
                    </div>

                    <!-- TokenHarbor DeepSeek Input -->
                    <div class="space-y-1">
                        <div class="flex justify-between items-center text-[11px]">
                            <span class="text-gray-300 font-semibold flex items-center gap-1"><i class="fa-solid fa-bolt text-binanceGold text-[10px]"></i> DeepSeek API Key (TokenHarbor)</span>
                            <span class="text-[10px] text-gray-400 font-mono">deepseek-v4.1-flash:free</span>
                        </div>
                        <input type="password" id="input-deepseek-key" placeholder="thk_live_... (TokenHarbor API Key)" class="w-full bg-darkCard border border-darkBorder rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyberCyan font-mono">
                    </div>

                    <!-- Google Gemini Input -->
                    <div class="space-y-1">
                        <div class="flex justify-between items-center text-[11px]">
                            <span class="text-gray-300 font-semibold flex items-center gap-1"><i class="fa-solid fa-gem text-cyberCyan text-[10px]"></i> Google Gemini API Key</span>
                            <a href="https://aistudio.google.com/" target="_blank" class="text-[10px] text-binanceGold hover:underline flex items-center gap-0.5">
                                <span>Lấy key Google</span> <i class="fa-solid fa-arrow-up-right-from-square text-[8px]"></i>
                            </a>
                        </div>
                        <input type="password" id="input-ai-key" placeholder="AIzaSy... (Hoặc Gemini Key)" class="w-full bg-darkCard border border-darkBorder rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyberCyan font-mono">
                    </div>

                    <!-- AI Mode Selection -->
                    <div class="space-y-1 pt-1">
                        <span class="text-[10px] text-gray-400 font-semibold uppercase">Chế độ vận hành AI:</span>
                        <div class="grid grid-cols-3 gap-1.5 text-center text-[11px]">
                            <button type="button" onclick="selectAiMode('dual')" id="btn-aimode-dual" class="py-1.5 px-2 rounded-lg font-semibold border border-cyberCyan bg-cyan-950/40 text-cyberCyan transition">
                                ⚡ Song Song (Dual)
                            </button>
                            <button type="button" onclick="selectAiMode('deepseek')" id="btn-aimode-deepseek" class="py-1.5 px-2 rounded-lg font-semibold border border-darkBorder bg-darkCard text-gray-400 hover:text-white transition">
                                🐋 DeepSeek
                            </button>
                            <button type="button" onclick="selectAiMode('gemini')" id="btn-aimode-gemini" class="py-1.5 px-2 rounded-lg font-semibold border border-darkBorder bg-darkCard text-gray-400 hover:text-white transition">
                                💎 Gemini
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="flex gap-3 pt-2">
                <button onclick="closeSettingsModal()" class="flex-1 py-2.5 rounded-xl text-xs font-semibold bg-gray-800 hover:bg-gray-700 text-gray-300 transition">Đóng</button>
                <button onclick="saveLiveSettings()" class="flex-1 py-2.5 rounded-xl text-xs font-bold bg-binanceGold hover:bg-yellow-500 text-black shadow-lg shadow-yellow-900/30 transition">LƯU CẤU HÌNH NGAY</button>
            </div>
        </div>
    </div>

    <!-- Interactive AI Copilot Chat Modal / Drawer -->
    <div id="ai-chat-modal" class="fixed inset-0 z-[999] bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-2 sm:p-4">
        <div class="glass-panel max-w-2xl w-full h-[90vh] sm:h-[620px] rounded-2xl border border-cyberCyan/40 shadow-2xl flex flex-col overflow-hidden">
            <!-- Modal Header -->
            <div class="p-4 bg-gradient-to-r from-darkCard via-cyan-950/20 to-darkCard border-b border-darkBorder flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 rounded-xl bg-cyan-950/60 border border-cyberCyan/50 flex items-center justify-center text-cyberCyan text-lg shadow-lg shadow-cyan-950/50">
                        <i class="fa-solid fa-robot animate-bounce"></i>
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <h3 class="font-extrabold text-sm text-white tracking-wide">CYBER-NOVA 2.0 • AI QUANT COPILOT</h3>
                            <span id="ai-connected-badge" class="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyberCyan border border-cyan-700/50">LOCAL QUANT BRAIN</span>
                        </div>
                        <p class="text-[11px] text-gray-400">Trợ lý Phân Tích Kỹ Thuật & Giám Sát Rủi Ro Lượng Tử Thời Gian Thực</p>
                    </div>
                </div>
                <button onclick="closeAiModal()" class="w-8 h-8 rounded-lg bg-darkBase hover:bg-gray-800 text-gray-400 hover:text-white flex items-center justify-center transition">
                    <i class="fa-solid fa-xmark text-sm"></i>
                </button>
            </div>

            <!-- Chat Stream Body -->
            <div id="ai-chat-body" class="flex-1 p-4 overflow-y-auto space-y-3.5 text-xs">
                <!-- Welcome Message Bubble -->
                <div class="flex gap-2.5 items-start">
                    <div class="w-7 h-7 rounded-lg bg-cyan-950 border border-cyberCyan/50 flex items-center justify-center text-cyberCyan text-xs flex-shrink-0 mt-0.5">
                        <i class="fa-solid fa-microchip"></i>
                    </div>
                    <div class="p-3 rounded-2xl bg-darkCard border border-cyan-900/30 text-gray-200 max-w-[85%] leading-relaxed shadow-sm">
                        Chào Sếp! Em là <b>Cyber-Nova</b>. Em liên tục đọc dữ liệu giá, các vị thế đang mở và chỉ báo ADX/EMA của bot.<br><br>
                        Sếp muốn em hỗ trợ soi kèo, phân tích danh mục hay tư vấn chiến lược gì hôm nay ạ?
                    </div>
                </div>
            </div>

            <!-- Quick Suggestion Chips -->
            <div class="px-4 py-2 border-t border-darkBorder/60 bg-darkBase/40 flex items-center gap-2 overflow-x-auto text-[11px] whitespace-nowrap">
                <button onclick="sendQuickPrompt('Phân tích 3 vị thế đang chạy')" class="px-2.5 py-1 rounded-full bg-cyan-950/40 text-cyan-300 border border-cyan-800/50 hover:bg-cyan-900/50 transition">
                    📊 Soi Kèo Các Vị Thế
                </button>
                <button onclick="sendQuickPrompt('Có nên chuyển sang chế độ chỉ đánh BTC/ETH không?')" class="px-2.5 py-1 rounded-full bg-yellow-950/40 text-binanceGold border border-yellow-800/50 hover:bg-yellow-900/50 transition">
                    🎯 Tư Vấn Chế Độ Quét
                </button>
                <button onclick="sendQuickPrompt('Hướng dẫn setup API key AI')" class="px-2.5 py-1 rounded-full bg-blue-950/40 text-blue-300 border border-blue-800/50 hover:bg-blue-900/50 transition">
                    🔑 Hướng Dẫn Setup Key
                </button>
                <button onclick="sendQuickPrompt('Tiến độ đánh tiền thật hiện tại thế nào?')" class="px-2.5 py-1 rounded-full bg-green-950/40 text-profitGreen border border-green-800/50 hover:bg-green-900/50 transition">
                    🏆 Đánh Giá Đánh Thật
                </button>
            </div>

            <!-- Input Bar -->
            <div class="p-3 bg-darkCard border-t border-darkBorder flex items-center gap-2">
                <input type="text" id="ai-chat-input" onkeydown="if(event.key==='Enter') sendAiMessage()" placeholder="Hỏi Cyber-Nova về thị trường, lệnh đang chạy, tư vấn rủi ro..." class="flex-1 bg-darkBase border border-darkBorder rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyberCyan transition font-sans">
                <button onclick="sendAiMessage()" id="btn-send-ai" class="px-4 py-2.5 rounded-xl bg-cyberCyan hover:bg-cyan-400 text-black font-bold text-xs shadow-lg shadow-cyan-900/30 transition flex items-center gap-1.5">
                    <span>Gửi</span> <i class="fa-solid fa-paper-plane text-[10px]"></i>
                </button>
            </div>
        </div>
    </div>

    <!-- TradingView Lightweight Charts Interactive Modal -->
    <div id="tv-chart-modal" class="fixed inset-0 z-[999] bg-black/85 backdrop-blur-md hidden flex items-center justify-center p-2 sm:p-4">
        <div class="glass-panel max-w-4xl w-full rounded-2xl border border-cyan-800/60 shadow-2xl flex flex-col overflow-hidden">
            <!-- Modal Header -->
            <div class="p-3.5 sm:p-4 bg-gradient-to-r from-darkCard via-[#0d1627] to-darkCard border-b border-darkBorder flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="w-9 h-9 rounded-xl bg-cyan-950/60 border border-cyberCyan/40 flex items-center justify-center text-cyberCyan text-base shadow-md">
                        <i class="fa-solid fa-chart-candlestick"></i>
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <h3 class="font-extrabold text-sm sm:text-base text-white font-sans" id="tv-chart-title">BTCUSDT</h3>
                            <span id="tv-chart-price" class="text-xs sm:text-sm font-bold font-mono text-binanceGold">$0.00</span>
                            <span id="tv-chart-pos-badge" class="px-2 py-0.5 rounded text-[10px] font-bold hidden"></span>
                        </div>
                        <p class="text-[10px] text-gray-400">Binance Futures Live Candlestick & Order Levels</p>
                    </div>
                </div>
                <!-- Timeframe selector & Close -->
                <div class="flex items-center gap-2">
                    <div class="flex rounded-lg bg-darkBase p-0.5 border border-darkBorder text-[11px] font-mono">
                        <button onclick="changeChartInterval('5m')" id="tf-5m" class="px-2 py-1 rounded text-gray-400 hover:text-white">5m</button>
                        <button onclick="changeChartInterval('15m')" id="tf-15m" class="px-2 py-1 rounded bg-binanceGold text-black font-bold">15m</button>
                        <button onclick="changeChartInterval('1h')" id="tf-1h" class="px-2 py-1 rounded text-gray-400 hover:text-white">1h</button>
                        <button onclick="changeChartInterval('4h')" id="tf-4h" class="px-2 py-1 rounded text-gray-400 hover:text-white">4h</button>
                    </div>
                    <button onclick="closeChartModal()" class="w-8 h-8 rounded-lg bg-darkBase hover:bg-gray-800 text-gray-400 hover:text-white flex items-center justify-center transition">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            </div>

            <!-- Chart Canvas Container -->
            <div class="relative bg-darkBase/90 p-2">
                <div id="tv-chart-loading" class="absolute inset-0 z-10 bg-darkBase/80 flex items-center justify-center text-xs text-cyberCyan gap-2">
                    <i class="fa-solid fa-spinner fa-spin text-base"></i> Đang tải dữ liệu nến Binance...
                </div>
                <div id="tv-chart-view" style="width: 100%; height: 420px;"></div>
            </div>

            <!-- Chart Bottom Bar: Quick Trade & Legend -->
            <div class="p-3 bg-darkCard border-t border-darkBorder flex flex-wrap items-center justify-between gap-2 text-xs">
                <!-- Levels Legend -->
                <div class="flex items-center gap-3 text-[11px] font-mono">
                    <span class="flex items-center gap-1"><span class="w-2.5 h-0.5 bg-cyberCyan inline-block"></span> <span class="text-gray-400">Entry:</span> <span id="tv-legend-entry" class="text-white font-bold">--</span></span>
                    <span class="flex items-center gap-1"><span class="w-2.5 h-0.5 bg-lossRed inline-block"></span> <span class="text-gray-400">SL:</span> <span id="tv-legend-sl" class="text-lossRed font-bold">--</span></span>
                    <span class="flex items-center gap-1"><span class="w-2.5 h-0.5 bg-profitGreen inline-block"></span> <span class="text-gray-400">TP:</span> <span id="tv-legend-tp" class="text-profitGreen font-bold">--</span></span>
                </div>

                <!-- 1-Click Order Buttons -->
                <div class="flex items-center gap-2">
                    <button onclick="executeChartManualOrder('BUY')" class="px-3.5 py-1.5 rounded-xl bg-profitGreen/20 hover:bg-profitGreen text-profitGreen hover:text-black border border-green-600 font-bold transition flex items-center gap-1.5">
                        <i class="fa-solid fa-arrow-trend-up"></i> <span>⚡ MỞ LONG</span>
                    </button>
                    <button onclick="executeChartManualOrder('SELL')" class="px-3.5 py-1.5 rounded-xl bg-lossRed/20 hover:bg-lossRed text-lossRed hover:text-white border border-red-600 font-bold transition flex items-center gap-1.5">
                        <i class="fa-solid fa-arrow-trend-down"></i> <span>⚡ MỞ SHORT</span>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Performance Analytics Modal -->
    <div id="analytics-modal" class="fixed inset-0 z-[998] bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-3 sm:p-4">
        <div class="glass-panel max-w-2xl w-full max-h-[90vh] rounded-2xl border border-binanceGold/40 shadow-2xl flex flex-col overflow-hidden">
            <!-- Header -->
            <div class="p-4 bg-gradient-to-r from-darkCard via-[#181d28] to-darkCard border-b border-darkBorder flex items-center justify-between">
                <div class="flex items-center space-x-2.5">
                    <div class="w-9 h-9 rounded-xl bg-yellow-950/60 border border-binanceGold/40 flex items-center justify-center text-binanceGold text-base">
                        <i class="fa-solid fa-chart-pie"></i>
                    </div>
                    <div>
                        <h3 class="font-extrabold text-sm sm:text-base text-white">THỐNG KÊ HIỆU SUẤT TỪNG CẶP COIN</h3>
                        <p class="text-[10px] text-gray-400">Phân tích Winrate, Chuỗi thắng/thua & Lợi nhuận chi tiết</p>
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/api/export_history_csv" class="px-2.5 py-1.5 rounded-lg bg-darkBase border border-darkBorder hover:border-binanceGold text-gray-300 hover:text-binanceGold text-xs font-semibold flex items-center gap-1 transition">
                        <i class="fa-solid fa-download"></i> <span>Tải CSV</span>
                    </a>
                    <button onclick="closeAnalyticsModal()" class="w-8 h-8 rounded-lg bg-darkBase hover:bg-gray-800 text-gray-400 hover:text-white flex items-center justify-center transition">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            </div>

            <!-- Analytics Content Body -->
            <div class="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
                <!-- Summary 3 cards -->
                <div class="grid grid-cols-3 gap-2 sm:gap-3 text-center">
                    <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                        <span class="text-[10px] text-gray-400 block font-sans">Chuỗi lệnh hiện tại</span>
                        <span id="stat-streak" class="text-sm sm:text-base font-extrabold font-mono text-profitGreen">--</span>
                    </div>
                    <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                        <span class="text-[10px] text-gray-400 block font-sans">Cặp lãi tốt nhất</span>
                        <span id="stat-best-symbol" class="text-xs sm:text-sm font-extrabold font-mono text-binanceGold">--</span>
                    </div>
                    <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                        <span class="text-[10px] text-gray-400 block font-sans">Cặp cần lưu ý</span>
                        <span id="stat-worst-symbol" class="text-xs sm:text-sm font-extrabold font-mono text-lossRed">--</span>
                    </div>
                </div>

                <!-- Per-Symbol Performance Table -->
                <div class="overflow-x-auto rounded-xl border border-darkBorder">
                    <table class="w-full text-left font-mono text-xs">
                        <thead class="bg-darkBase/80 text-[10px] uppercase text-gray-400 border-b border-darkBorder font-sans">
                            <tr>
                                <th class="px-3.5 py-2.5">Cặp Coin</th>
                                <th class="px-3.5 py-2.5">Số Lệnh</th>
                                <th class="px-3.5 py-2.5">Thắng / Thua</th>
                                <th class="px-3.5 py-2.5">Winrate</th>
                                <th class="px-3.5 py-2.5">Net PnL</th>
                            </tr>
                        </thead>
                        <tbody id="analytics-table-body" class="divide-y divide-darkBorder">
                            <tr><td colspan="5" class="px-4 py-4 text-center text-gray-400 font-sans">Đang tải dữ liệu thống kê...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Copilot Backtesting Engine Modal -->
    <div id="backtest-modal" class="fixed inset-0 z-[998] bg-black/85 backdrop-blur-md hidden flex items-center justify-center p-3 sm:p-4">
        <div class="glass-panel max-w-4xl w-full max-h-[94vh] overflow-y-auto p-5 sm:p-6 rounded-2xl border border-cyberCyan/40 shadow-2xl space-y-4 sm:space-y-5">
            <div class="flex justify-between items-center pb-3 border-b border-darkBorder">
                <div class="flex items-center space-x-2.5">
                    <div class="w-8 h-8 rounded-lg bg-cyan-950/60 text-cyberCyan flex items-center justify-center border border-cyan-700/50">
                        <i class="fa-solid fa-flask-vial"></i>
                    </div>
                    <div>
                        <h3 class="text-base font-bold text-white tracking-wide">COPILOT BACKTESTING LAB 4.0</h3>
                        <p class="text-[11px] text-gray-400">Giả lập chiến lược định lượng trên dữ liệu nến lịch sử Binance Futures</p>
                    </div>
                </div>
                <button onclick="closeBacktestModal()" class="text-gray-400 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
            </div>

            <!-- Backtest Configuration Bar -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-darkBase/70 p-3.5 rounded-xl border border-darkBorder text-xs">
                <div>
                    <label class="block text-gray-400 font-semibold mb-1">Cặp giao dịch:</label>
                    <input type="text" id="bt-symbol" value="BTCUSDT" class="w-full bg-darkCard border border-darkBorder rounded-lg px-2.5 py-1.5 text-white font-mono font-bold uppercase focus:border-cyberCyan outline-none">
                </div>
                <div>
                    <label class="block text-gray-400 font-semibold mb-1">Chiến lược:</label>
                    <select id="bt-strategy" class="w-full bg-darkCard border border-darkBorder rounded-lg px-2 py-1.5 text-white font-semibold focus:border-cyberCyan outline-none">
                        <option value="AUTO_DYNAMIC">Auto Dynamic</option>
                        <option value="TREND_PULLBACK">Trend Pullback</option>
                        <option value="BREAKOUT">Breakout Volume</option>
                        <option value="MEAN_REVERSION">Mean Reversion</option>
                    </select>
                </div>
                <div>
                    <label class="block text-gray-400 font-semibold mb-1">Thời gian:</label>
                    <select id="bt-days" class="w-full bg-darkCard border border-darkBorder rounded-lg px-2 py-1.5 text-white font-semibold focus:border-cyberCyan outline-none">
                        <option value="7">7 ngày qua</option>
                        <option value="14" selected>14 ngày qua</option>
                        <option value="30">30 ngày qua</option>
                    </select>
                </div>
                <div class="flex items-end">
                    <button type="button" onclick="runBacktestSimulation()" id="btn-run-backtest" class="w-full py-2 rounded-lg bg-cyan-900/40 hover:bg-cyan-800/60 text-cyberCyan border border-cyberCyan/50 font-bold transition flex items-center justify-center gap-1.5 shadow-lg shadow-cyan-950/40">
                        <i class="fa-solid fa-play text-xs"></i> <span>Chạy Giả Lập</span>
                    </button>
                </div>
            </div>

            <!-- Summary Cards -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                <div class="p-3 rounded-xl bg-darkBase border border-darkBorder">
                    <p class="text-[10px] text-gray-400 uppercase font-bold">Tỷ lệ thắng (Winrate)</p>
                    <p class="text-lg sm:text-xl font-extrabold font-mono text-profitGreen mt-1" id="bt-winrate">--%</p>
                    <p class="text-[10px] text-gray-500 mt-0.5" id="bt-trades-count">-- lệnh</p>
                </div>
                <div class="p-3 rounded-xl bg-darkBase border border-darkBorder">
                    <p class="text-[10px] text-gray-400 uppercase font-bold">Lợi nhuận ròng (Net PnL)</p>
                    <p class="text-lg sm:text-xl font-extrabold font-mono text-white mt-1" id="bt-pnl">$0.00</p>
                    <p class="text-[10px] text-gray-500 mt-0.5" id="bt-roi">--%</p>
                </div>
                <div class="p-3 rounded-xl bg-darkBase border border-darkBorder">
                    <p class="text-[10px] text-gray-400 uppercase font-bold">Profit Factor</p>
                    <p class="text-lg sm:text-xl font-extrabold font-mono text-binanceGold mt-1" id="bt-pf">--</p>
                    <p class="text-[10px] text-gray-500 mt-0.5">Kỳ vọng lợi nhuận</p>
                </div>
                <div class="p-3 rounded-xl bg-darkBase border border-darkBorder">
                    <p class="text-[10px] text-gray-400 uppercase font-bold">Max Drawdown</p>
                    <p class="text-lg sm:text-xl font-extrabold font-mono text-lossRed mt-1" id="bt-dd">--%</p>
                    <p class="text-[10px] text-gray-500 mt-0.5">Sụt giảm tối đa</p>
                </div>
            </div>

            <!-- Equity Curve Chart -->
            <div class="p-4 rounded-xl bg-darkBase border border-darkBorder">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-xs font-bold text-gray-300 flex items-center gap-1.5">
                        <i class="fa-solid fa-chart-line text-cyberCyan"></i> ĐƯỜNG CONG TĂNG TRƯỞNG VỐN (EQUITY CURVE)
                    </span>
                    <span class="text-[10px] text-gray-500">Vốn khởi đầu: $1,000.00</span>
                </div>
                <div class="h-52 sm:h-60 w-full relative">
                    <canvas id="backtestEquityCanvas"></canvas>
                </div>
            </div>

            <!-- Recent Simulated Trades Table -->
            <div class="rounded-xl border border-darkBorder overflow-hidden bg-darkBase">
                <div class="px-4 py-2 border-b border-darkBorder bg-darkCard flex justify-between items-center text-xs font-bold text-gray-300">
                    <span>DANH SÁCH LỆNH MÔ PHỎNG (GẦN NHẤT)</span>
                    <span id="bt-table-status" class="text-[10px] text-gray-500">Chưa chạy giả lập</span>
                </div>
                <div class="max-h-44 overflow-y-auto">
                    <table class="w-full text-left text-xs text-gray-300">
                        <thead class="bg-darkBase/90 text-gray-400 text-[11px] uppercase font-mono sticky top-0 border-b border-darkBorder">
                            <tr>
                                <th class="px-3 py-2">Thời gian</th>
                                <th class="px-3 py-2">Chiều</th>
                                <th class="px-3 py-2">Entry / Exit</th>
                                <th class="px-3 py-2">Lý do</th>
                                <th class="px-3 py-2 text-right">PnL Ròng</th>
                            </tr>
                        </thead>
                        <tbody id="bt-trades-body" class="divide-y divide-darkBorder font-mono text-[11px]">
                            <tr><td colspan="5" class="px-3 py-4 text-center text-gray-500 font-sans">Chọn thông số và bấm 'Chạy Giả Lập' để xem kết quả chi tiết.</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Top Navigation Bar -->
    <!-- Top Navigation Bar (Clean, single-row, responsive on Mobile, Mini App and Desktop) -->
    <header class="border-b border-darkBorder bg-darkCard/95 sticky top-0 z-50 backdrop-blur-md w-full max-w-full">
        <div id="admin-header-inner" class="max-w-[1600px] mx-auto px-2 sm:px-6 lg:px-8 h-14 sm:h-16 flex items-center justify-between gap-1 sm:gap-2">
            <!-- Left Branding -->
            <div class="flex items-center space-x-1.5 sm:space-x-3 min-w-0 flex-shrink">
                <img src="/logo.png" alt="Quant Bot Logo" class="w-7 h-7 sm:w-10 sm:h-10 rounded-xl object-cover border border-binanceGold/40 shadow-lg shadow-yellow-900/20 flex-shrink-0">
                <div id="admin-brand-text" class="min-w-0">
                    <div class="flex items-center gap-1.5 sm:gap-2">
                        <span class="admin-brand-name font-extrabold text-xs sm:text-base lg:text-lg text-white tracking-wider truncate">QUANT PRO</span>
                    </div>
                    <p class="hidden sm:block text-[10px] sm:text-[11px] text-gray-400 font-medium truncate">Institutional Strategy • Cloud VPS Terminal</p>
                </div>
                </div>

            <!-- Center/Right Badges & Controls (No-wrap, clean responsive layout) -->
            <div id="admin-header-actions" class="flex items-center space-x-1 sm:space-x-2 flex-shrink-0">
                <!-- Navigation Shortcuts: Track Record & Client Portal -->
                <a href="/track-record" class="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-darkBase hover:bg-yellow-950/40 border border-yellow-700/50 text-xs text-binanceGold font-bold transition-all" title="Xem Public Track Record công khai">
                    <i class="fa-solid fa-chart-line text-[11px]"></i>
                    <span class="hidden xl:inline">Track Record</span>
                </a>
                <a href="/portal/dashboard" class="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-darkBase hover:bg-cyan-950/40 border border-cyan-700/50 text-xs text-cyberCyan font-bold transition-all" title="Chuyển sang Client Portal">
                    <i class="fa-solid fa-user-gear text-[11px]"></i>
                    <span class="hidden xl:inline">Client Portal</span>
                </a>
                <!-- Ping Latency (Desktop Only) -->
                <div class="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-darkBase border border-darkBorder text-xs text-gray-300 font-mono">
                    <span id="ping-indicator" class="w-2 h-2 rounded-full bg-profitGreen animate-pulse"></span>
                    <span id="ping-latency">24.5 ms</span>
                </div>

                <!-- Strategy Badge (Desktop Only) -->
                <span id="badge-strategy" class="hidden lg:flex px-2 sm:px-2.5 py-1 rounded-full text-[10px] sm:text-xs font-bold bg-yellow-950/40 text-binanceGold border border-yellow-700/50 items-center gap-1">
                    <i class="fa-solid fa-microchip text-[10px]"></i> <span id="strategy-label">{getattr(config, "active_strategy", "AUTO_DYNAMIC")}</span>
                </span>

                <!-- Trading Mode Badge (Desktop Only) -->
                <span id="badge-trading-mode" class="hidden lg:flex px-2 sm:px-2.5 py-1 rounded-full text-[10px] sm:text-xs font-bold bg-cyan-950/40 text-cyberCyan border border-cyan-700/50 items-center gap-1">
                    <i class="fa-solid fa-radar text-[10px]"></i> <span id="trading-mode-text">ALL MARKET</span>
                </span>

                <!-- Bot Status Badge (Compact on mobile) -->
                <span id="badge-status" class="px-2 py-1 rounded-full text-[10px] sm:text-xs font-bold bg-green-900/30 text-profitGreen border border-green-700/50 flex items-center gap-1">
                    <span class="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-profitGreen animate-pulse"></span>
                    <span id="status-label" class="hidden sm:inline">LIVE</span>
                </span>

                <!-- Fear & Greed Index Badge (Tablet/Desktop Only) -->
                <div id="badge-fear-greed" onclick="showFearGreedInfo()" title="Chỉ số Crypto Fear & Greed thời gian thực" class="hidden md:flex cursor-pointer px-2 sm:px-2.5 py-1 rounded-full text-[10px] sm:text-xs font-bold bg-darkBase border border-darkBorder text-slate-300 items-center gap-1.5 hover:border-binanceGold transition">
                    <span id="fng-icon">🔥</span>
                    <span class="hidden sm:inline text-gray-400">F&G:</span>
                    <span id="fng-value" class="font-mono font-extrabold text-binanceGold">50</span>
                    <span id="fng-label" class="hidden xs:inline text-[9px] px-1 py-0.2 rounded bg-darkCard border border-darkBorder">Trung lập</span>
                </div>

                <!-- Backtest Lab Modal Trigger (Desktop Only) -->
                <button onclick="openBacktestModal()" title="Backtest Lab" class="hidden md:flex w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-darkBase border border-darkBorder text-gray-300 hover:text-cyberCyan hover:border-cyberCyan/40 transition items-center justify-center">
                    <i class="fa-solid fa-flask-vial text-xs sm:text-sm text-cyberCyan"></i>
                </button>

                <!-- Analytics Modal Trigger (Desktop Only) -->
                <button onclick="openAnalyticsModal()" title="Thống kê coin" class="hidden md:flex w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-darkBase border border-darkBorder text-gray-300 hover:text-binanceGold hover:border-binanceGold/40 transition items-center justify-center">
                    <i class="fa-solid fa-chart-pie text-xs sm:text-sm"></i>
                </button>

                <!-- Sound Alert Toggle Button (Desktop/Tablet) -->
                <button onclick="toggleAudio()" id="btn-audio" title="Bật/Tắt chuông âm thanh" class="hidden sm:flex w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-darkBase border border-darkBorder text-gray-300 hover:text-binanceGold hover:border-binanceGold/40 transition items-center justify-center">
                    <i class="fa-solid fa-volume-high text-xs" id="icon-audio"></i>
                </button>

                <!-- Quick Settings Modal Trigger -->
                <button onclick="openSettingsModal()" title="Cài đặt cấu hình" class="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-darkBase border border-darkBorder text-gray-300 hover:text-binanceGold hover:border-binanceGold/40 transition flex items-center justify-center">
                    <i class="fa-solid fa-gear text-xs"></i>
                </button>

                <!-- Refresh Button -->
                <button onclick="fetchStatus(true)" title="Làm mới ngay" class="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-darkBase border border-darkBorder text-gray-300 hover:text-binanceGold hover:border-binanceGold/40 transition flex items-center justify-center">
                    <i class="fa-solid fa-arrows-rotate text-xs" id="btn-refresh-icon"></i>
                </button>

                <!-- Clock (Large Desktop Only) -->
                <span id="clock" class="text-xs font-mono text-gray-400 hidden xl:inline px-2 py-1 rounded bg-darkBase border border-darkBorder">--:--:-- UTC</span>

                <!-- Quick Emergency Panic Close Button (Mobile Only) -->
                <button onclick="confirmPanicClose()" title="Đóng lệnh khẩn cấp" class="md:hidden w-7 h-7 rounded-lg bg-red-950/60 border border-red-700/60 text-lossRed hover:bg-lossRed hover:text-white transition flex items-center justify-center active:scale-90">
                    <i class="fa-solid fa-radiation text-xs"></i>
                </button>

                <!-- User Account / Logout Pill (Institutional Grade, responsive) -->
                <div id="user-profile-widget" class="hidden items-center bg-darkBase/90 hover:bg-darkCard border border-darkBorder hover:border-binanceGold/40 rounded-full pl-2 sm:pl-2.5 pr-1 py-0.5 sm:py-1 transition-all duration-200 gap-1 sm:gap-1.5 shadow-sm">
                    <div class="flex items-center gap-1 sm:gap-1.5 text-xs text-gray-300 font-medium">
                        <span class="w-1.5 h-1.5 rounded-full bg-profitGreen animate-pulse flex-shrink-0"></span>
                        <i class="fa-solid fa-circle-user text-binanceGold text-[11px] sm:text-xs flex-shrink-0"></i>
                        <span id="header-username" class="font-mono text-gray-200 font-semibold text-[11px] sm:text-xs max-w-[65px] sm:max-w-[110px] truncate hidden sm:inline">admin</span>
                    </div>
                    <div class="h-3 w-[1px] bg-darkBorder mx-0.5 flex-shrink-0"></div>
                    <button onclick="logoutDashboard()" title="Đăng xuất khỏi Terminal" class="w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-darkCard hover:bg-lossRed/20 text-gray-400 hover:text-lossRed transition flex items-center justify-center active:scale-90 flex-shrink-0">
                        <i class="fa-solid fa-arrow-right-from-bracket text-[10px]"></i>
                    </button>
                </div>
            </div>
        </div>
    </header>

    <!-- Workspace Tab Navigation Bar (Desktop Only: Ẩn trên Mobile/Mini App vì đã có Bottom Nav chuyên nghiệp) -->
    <div class="hidden md:block border-b border-darkBorder bg-darkCard/85 sticky top-14 sm:top-16 z-40 backdrop-blur-md">
        <div class="max-w-[1600px] mx-auto px-3 sm:px-6 lg:px-8 py-2 flex items-center justify-between overflow-x-auto no-scrollbar gap-2">
            <div class="flex items-center gap-1.5 sm:gap-2 whitespace-nowrap">
                <button type="button" onclick="switchDashboardTab('overview')" id="tab-btn-overview" class="tab-btn px-3 sm:px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 bg-binanceGold text-black border border-binanceGold shadow-lg shadow-yellow-900/30">
                    <i class="fa-solid fa-bolt"></i>
                    <span>VỊ THẾ & ĐIỀU HÀNH</span>
                    <span id="tab-badge-positions" class="px-1.5 py-0.2 rounded-full text-[10px] bg-black/30 text-white font-mono">0</span>
                </button>
                <button type="button" onclick="switchDashboardTab('radar')" id="tab-btn-radar" class="tab-btn px-3 sm:px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 text-gray-300 hover:text-white border border-transparent hover:bg-darkBase">
                    <i class="fa-solid fa-satellite-dish text-cyberCyan"></i>
                    <span>RADAR QUÉT THỊ TRƯỜNG</span>
                    <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-cyan-950 text-cyberCyan font-mono">50</span>
                </button>
                <button type="button" onclick="switchDashboardTab('smart_money')" id="tab-btn-smart_money" class="tab-btn px-3 sm:px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 text-gray-300 hover:text-white border border-transparent hover:bg-darkBase">
                    <i class="fa-solid fa-shapes text-binanceGold"></i>
                    <span>CÁ MẬP & DÒNG TIỀN (SMC / CVD)</span>
                </button>
                <button type="button" onclick="switchDashboardTab('ai_arbitrage')" id="tab-btn-ai_arbitrage" class="tab-btn px-3 sm:px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 text-gray-300 hover:text-white border border-transparent hover:bg-darkBase">
                    <i class="fa-solid fa-brain text-purple-400"></i>
                    <span>AI TIẾN HÓA & BẮT SÓNG TRỄ</span>
                </button>
                <button type="button" onclick="switchDashboardTab('portfolio')" id="tab-btn-portfolio" class="tab-btn px-3 sm:px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 text-gray-300 hover:text-white border border-transparent hover:bg-darkBase">
                    <i class="fa-solid fa-chart-pie text-profitGreen"></i>
                    <span>QUẢN TRỊ DANH MỤC & VĨ MÔ</span>
                </button>
            </div>
            <!-- Quick Panic Button directly in sticky tab bar on desktop -->
            <button type="button" onclick="confirmPanicClose()" class="flex-shrink-0 px-3 py-1.5 rounded-xl text-xs font-bold bg-lossRed/20 hover:bg-lossRed text-lossRed hover:text-white border border-red-500/40 transition flex items-center gap-1.5 active:scale-95 shadow-lg shadow-red-950/30">
                <i class="fa-solid fa-radiation"></i>
                <span>CẮT LỆNH KHẨN CẤP</span>
            </button>
        </div>
    </div>


    <!-- Main Workspace Container -->
    <main id="workspace" class="max-w-[1600px] mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-6 space-y-4 sm:space-y-6 pb-24 md:pb-12">

        <!-- ==================== ALWAYS-ON TOP KPI BAR (HIỂN THỊ XUYÊN SUỐT TẤT CẢ TABS) ==================== -->
<!-- Metric KPI Cards (4 Cards) -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <!-- Card 1: Balance & ROI -->
            <div class="glass-card rounded-2xl p-4 sm:p-5 border-l-4 border-l-binanceGold relative overflow-hidden">
                <div class="flex justify-between items-start">
                    <span class="text-[11px] sm:text-xs font-semibold text-gray-400 uppercase tracking-wider">Tổng Vốn & Số Dư</span>
                    <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-binanceGold/10 text-binanceGold flex items-center justify-center text-xs sm:text-sm">
                        <i class="fa-solid fa-wallet"></i>
                    </div>
                </div>
                <div class="mt-2">
                    <div class="text-xl sm:text-2xl lg:text-3xl font-extrabold text-white font-mono" id="metric-balance">$0.00 <span class="text-xs font-normal text-gray-400">USDT</span></div>
                    <div class="flex items-center justify-between text-xs mt-2 pt-2 border-t border-darkBorder">
                        <span class="text-gray-400">Tăng trưởng:</span>
                        <span id="metric-roi" class="font-bold font-mono text-profitGreen">+0.00%</span>
                    </div>
                    <div class="flex items-center justify-between text-xs mt-1">
                        <span class="text-gray-400">Đòn bẩy:</span>
                        <span id="metric-leverage" class="font-semibold text-white">5x (ISOLATED)</span>
                    </div>
                </div>
            </div>

            <!-- Card 2: Unrealized PnL (Floating) -->
            <div class="glass-card rounded-2xl p-4 sm:p-5 border-l-4 border-l-profitGreen relative overflow-hidden" id="card-u-pnl">
                <div class="flex justify-between items-start">
                    <span class="text-[11px] sm:text-xs font-semibold text-gray-400 uppercase tracking-wider">PnL Tạm Tính</span>
                    <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-profitGreen/10 text-profitGreen flex items-center justify-center text-xs sm:text-sm">
                        <i class="fa-solid fa-chart-line"></i>
                    </div>
                </div>
                <div class="mt-2">
                    <div class="text-xl sm:text-2xl lg:text-3xl font-extrabold text-profitGreen font-mono" id="metric-unrealized-pnl">+$0.00</div>
                    <div class="flex items-center justify-between text-xs mt-2 pt-2 border-t border-darkBorder">
                        <span class="text-gray-400">Số vị thế mở:</span>
                        <span id="metric-open-count" class="font-bold font-mono text-white">0 / 3 vị thế</span>
                    </div>
                    <div class="w-full bg-darkBase h-1.5 rounded-full mt-2 overflow-hidden">
                        <div id="metric-slot-bar" class="bg-profitGreen h-full rounded-full transition-all duration-500" style="width: 0%"></div>
                    </div>
                </div>
            </div>

            <!-- Card 3: Realized Net PnL & Win Rate -->
            <div class="glass-card rounded-2xl p-4 sm:p-5 border-l-4 border-l-cyberCyan relative overflow-hidden">
                <div class="flex justify-between items-start">
                    <span class="text-[11px] sm:text-xs font-semibold text-gray-400 uppercase tracking-wider">Lãi Ròng Đã Chốt</span>
                    <div class="flex items-center gap-1.5">
                        <button onclick="confirmResetHistory()" title="Xóa sạch lịch sử để bắt đầu chu kỳ mới" class="text-[10px] px-2 py-0.5 rounded bg-darkBase hover:bg-lossRed/20 text-gray-400 hover:text-lossRed border border-darkBorder transition cursor-pointer flex items-center gap-1">
                            <i class="fa-solid fa-rotate-right"></i>
                            <span>Reset</span>
                        </button>
                        <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-cyberCyan/10 text-cyberCyan flex items-center justify-center text-xs sm:text-sm">
                            <i class="fa-solid fa-trophy"></i>
                        </div>
                    </div>
                </div>
                <div class="mt-2">
                    <div class="text-xl sm:text-2xl lg:text-3xl font-extrabold text-white font-mono" id="metric-realized-pnl">$0.00</div>
                    <div class="flex items-center justify-between text-xs mt-2 pt-2 border-t border-darkBorder">
                        <span class="text-gray-400">Tỷ lệ thắng (WR):</span>
                        <span id="metric-winrate" class="font-bold font-mono text-binanceGold">0.0%</span>
                    </div>
                    <div class="flex items-center justify-between text-xs mt-1">
                        <span class="text-gray-400">Lệnh Thắng / Thua:</span>
                        <span class="font-mono text-white"><span id="metric-wins" class="text-profitGreen font-bold">0</span> / <span id="metric-losses" class="text-lossRed font-bold">0</span> (<span id="metric-total-closed">0</span> đã đóng)</span>
                    </div>
                    <div class="flex items-center justify-between text-xs mt-1 pt-1 border-t border-darkBorder/40">
                        <span class="text-gray-400">Vị thế đang chạy:</span>
                        <span id="metric-open-floating-badge" class="font-mono text-cyan-400 font-semibold text-[11px]">0 vị thế ($0.00)</span>
                    </div>
                </div>
            </div>

            <!-- Card 4: VPS Health & Latency -->
            <div class="glass-card rounded-2xl p-4 sm:p-5 border-l-4 border-l-purple-500 relative overflow-hidden">
                <div class="flex justify-between items-start">
                    <span class="text-[11px] sm:text-xs font-semibold text-gray-400 uppercase tracking-wider">VPS & Uptime</span>
                    <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center text-xs sm:text-sm">
                        <i class="fa-solid fa-server"></i>
                    </div>
                </div>
                <div class="mt-2">
                    <div class="text-xl sm:text-2xl lg:text-3xl font-extrabold text-white font-mono" id="metric-uptime">--</div>
                    <div class="flex items-center justify-between text-xs mt-2 pt-2 border-t border-darkBorder">
                        <span class="text-gray-400">CPU: <span id="metric-cpu" class="text-white font-semibold font-mono">0%</span></span>
                        <span class="text-gray-400">RAM: <span id="metric-ram" class="text-white font-semibold font-mono">0%</span></span>
                        <span id="metric-disk" class="text-gray-400 font-mono text-[10px]">Trống -- GB</span>
                    </div>
                    <div class="w-full bg-darkBase h-1.5 rounded-full mt-2 overflow-hidden flex">
                        <div id="ram-progress-bar" class="bg-purple-500 h-full rounded-full transition-all duration-500" style="width: 30%"></div>
                    </div>
                </div>
            </div>
        </div>

        

        <!-- ==================== TAB 1: VỊ THẾ & ĐIỀU HÀNH ==================== -->
        <div id="tab-overview" class="dashboard-workspace-tab space-y-4 sm:space-y-6">
<!-- Interactive Cyber Mascot Stage & AI Assistant Card (Inspired by page-mascot) -->
        <div class="glass-card rounded-2xl p-4 sm:p-5 border border-cyan-800/50 relative overflow-hidden bg-gradient-to-r from-darkCard via-[#0d1527] to-cyan-950/20 shadow-xl select-none">
            <!-- Ambient neon lighting -->
            <div class="absolute -top-12 -left-12 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="absolute -bottom-12 -right-12 w-48 h-48 bg-yellow-500/10 rounded-full blur-3xl pointer-events-none"></div>

            <div class="flex flex-col sm:flex-row items-center gap-5 relative z-10">
                <!-- Mascot Interactive Avatar & Stage -->
                <div class="flex flex-col items-center flex-shrink-0">
                    <div id="mascot-stage" class="relative cursor-pointer group" onclick="triggerMascotPoke(event)" title="Chạm/Click vào em để chọc (Poke) hoặc chơi đùa!">
                        <!-- Particle Burst Container -->
                        <div id="mascot-particle-layer" class="absolute inset-0 pointer-events-none z-30 overflow-visible"></div>

                        <!-- Mascot Head 3D Container -->
                        <div id="mascot-avatar-box" class="w-24 h-24 sm:w-26 sm:h-26 rounded-2xl bg-gradient-to-b from-[#1a233a] via-[#101728] to-[#0a0f1d] border-2 border-cyberCyan/60 flex items-center justify-center shadow-2xl shadow-cyan-950/80 relative overflow-visible mascot-floating mascot-head-tilt transition-shadow group-hover:shadow-cyan-500/30">
                            
                            <!-- Orbiting Satellite Drone -->
                            <div class="absolute inset-0 flex items-center justify-center pointer-events-none z-20">
                                <div class="w-full h-full relative drone-orbit">
                                    <div class="w-3.5 h-3.5 rounded-full bg-binanceGold border border-yellow-200 shadow-md shadow-yellow-500/80 absolute top-0 left-1/2 -ml-1.5 flex items-center justify-center">
                                        <span class="w-1 h-1 rounded-full bg-white"></span>
                                    </div>
                                </div>
                            </div>

                            <!-- Interactive Vector SVG Character Stage (100x100 ViewBox) -->
                            <svg id="mascot-svg" class="w-20 h-20 sm:w-22 sm:h-22 overflow-visible" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <defs>
                                    <linearGradient id="foxFurGrad" x1="20" y1="20" x2="80" y2="80" gradientUnits="userSpaceOnUse">
                                        <stop stop-color="#1e293b"/>
                                        <stop offset="0.6" stop-color="#0f172a"/>
                                        <stop offset="1" stop-color="#020617"/>
                                    </linearGradient>
                                    <linearGradient id="mechHeadGrad" x1="16" y1="18" x2="64" y2="66" gradientUnits="userSpaceOnUse">
                                        <stop stop-color="#1e293b"/>
                                        <stop offset="1" stop-color="#090d16"/>
                                    </linearGradient>
                                    <linearGradient id="visorGlassGrad" x1="22" y1="30" x2="78" y2="60" gradientUnits="userSpaceOnUse">
                                        <stop stop-color="#08101e" stop-opacity="0.95"/>
                                        <stop offset="1" stop-color="#030712" stop-opacity="0.9"/>
                                    </linearGradient>
                                    <clipPath id="eyeClipLeft">
                                        <ellipse cx="35" cy="46" rx="9.5" ry="11"/>
                                    </clipPath>
                                    <clipPath id="eyeClipRight">
                                        <ellipse cx="65" cy="46" rx="9.5" ry="11"/>
                                    </clipPath>
                                </defs>

                                <!-- ================= SKIN 1: CYBER KITSUNE (FOX) ================= -->
                                <g id="skin-fox" class="mascot-skin-group">
                                    <!-- Left Fox Ear (Animated Twitch) -->
                                    <g class="mascot-ear-l">
                                        <path d="M 22,38 L 11,8 Q 28,18 36,30 Z" fill="url(#foxFurGrad)" stroke="#00F0FF" stroke-width="2.2" stroke-linejoin="round"/>
                                        <path d="M 22,32 L 16,14 Q 26,20 32,27 Z" fill="#00F0FF" opacity="0.35"/>
                                        <path d="M 18,22 L 28,26" stroke="#F0B90B" stroke-width="1.5" stroke-linecap="round"/>
                                    </g>
                                    <!-- Right Fox Ear (Animated Twitch) -->
                                    <g class="mascot-ear-r">
                                        <path d="M 64,30 Q 72,18 89,8 L 78,38 Z" fill="url(#foxFurGrad)" stroke="#00F0FF" stroke-width="2.2" stroke-linejoin="round"/>
                                        <path d="M 68,27 Q 74,20 84,14 L 78,32 Z" fill="#00F0FF" opacity="0.35"/>
                                        <path d="M 82,22 L 72,26" stroke="#F0B90B" stroke-width="1.5" stroke-linecap="round"/>
                                    </g>

                                    <!-- Fox Head Outer Contour -->
                                    <path d="M 18,48 Q 16,68 34,74 Q 50,80 66,74 Q 84,68 82,48 Q 80,30 50,30 Q 20,30 18,48 Z" fill="url(#foxFurGrad)" stroke="#00F0FF" stroke-width="2.2"/>

                                    <!-- Fox Cheek Tuft Accents -->
                                    <path d="M 16,56 L 8,58 L 18,63" stroke="#00F0FF" stroke-width="1.8" stroke-linejoin="round" fill="none"/>
                                    <path d="M 84,56 L 92,58 L 82,63" stroke="#00F0FF" stroke-width="1.8" stroke-linejoin="round" fill="none"/>

                                    <!-- Holographic Visor Shade -->
                                    <rect x="22" y="36" width="56" height="23" rx="10" fill="url(#visorGlassGrad)" stroke="#38bdf8" stroke-width="1.2"/>

                                    <!-- Fox Whiskers -->
                                    <line x1="22" y1="62" x2="12" y2="60" stroke="#00F0FF" stroke-width="1.4" stroke-linecap="round" opacity="0.7"/>
                                    <line x1="22" y1="66" x2="13" y2="67" stroke="#00F0FF" stroke-width="1.4" stroke-linecap="round" opacity="0.7"/>
                                    <line x1="78" y1="62" x2="88" y2="60" stroke="#00F0FF" stroke-width="1.4" stroke-linecap="round" opacity="0.7"/>
                                    <line x1="78" y1="66" x2="87" y2="67" stroke="#00F0FF" stroke-width="1.4" stroke-linecap="round" opacity="0.7"/>

                                    <!-- Cute Cyber Nose & Smile -->
                                    <polygon points="50,60 47,57 53,57" fill="#F0B90B"/>
                                    <path d="M 45,63 Q 50,67 55,63" stroke="#00F0FF" stroke-width="1.8" stroke-linecap="round" fill="none"/>

                                    <!-- Quantum Collar with Binance Coin Jewel -->
                                    <rect x="36" y="74" width="28" height="6" rx="3" fill="#1e293b" stroke="#00F0FF" stroke-width="1.2"/>
                                    <circle cx="50" cy="77" r="3.5" fill="#F0B90B" stroke="#fff" stroke-width="0.8"/>
                                </g>

                                <!-- ================= SKIN 2: CYBER-NOVA (MECHA ROBOT) ================= -->
                                <g id="skin-robot" class="mascot-skin-group hidden">
                                    <!-- Antenna -->
                                    <path d="M 50,10 V 22" stroke="#00F0FF" stroke-width="2.5" stroke-linecap="round"/>
                                    <circle cx="50" cy="9" r="4.5" fill="#F0B90B" class="antenna-dot"/>
                                    <!-- Robot Head Armor -->
                                    <rect x="18" y="22" width="64" height="52" rx="16" fill="url(#mechHeadGrad)" stroke="#00F0FF" stroke-width="2.2"/>
                                    <!-- Ear Muff Thrusters -->
                                    <rect x="12" y="36" width="6" height="22" rx="3" fill="#00F0FF" opacity="0.85"/>
                                    <rect x="82" y="36" width="6" height="22" rx="3" fill="#00F0FF" opacity="0.85"/>
                                    <!-- Visor Glass -->
                                    <rect x="24" y="33" width="52" height="26" rx="9" fill="url(#visorGlassGrad)" stroke="#38bdf8" stroke-width="1.2"/>
                                    <!-- Equalizer Voice Mouth -->
                                    <g transform="translate(42, 63)">
                                        <line x1="0" y1="0" x2="0" y2="4" stroke="#00F0FF" stroke-width="2" stroke-linecap="round" class="mouth-bar-1"/>
                                        <line x1="5" y1="0" x2="5" y2="6" stroke="#00F0FF" stroke-width="2" stroke-linecap="round" class="mouth-bar-2"/>
                                        <line x1="11" y1="0" x2="11" y2="5" stroke="#00F0FF" stroke-width="2" stroke-linecap="round" class="mouth-bar-3"/>
                                        <line x1="16" y1="0" x2="16" y2="3" stroke="#00F0FF" stroke-width="2" stroke-linecap="round" class="mouth-bar-4"/>
                                    </g>
                                </g>

                                <!-- ================= SKIN 3: CYBER TAURUS (BULL) ================= -->
                                <g id="skin-bull" class="mascot-skin-group hidden">
                                    <!-- Golden Mecha Horns -->
                                    <path d="M 28,32 C 22,24 12,12 8,16 C 6,24 20,38 28,38 Z" fill="#F0B90B" stroke="#fef08a" stroke-width="1.5"/>
                                    <path d="M 72,32 C 78,24 88,12 92,16 C 94,24 80,38 72,38 Z" fill="#F0B90B" stroke="#fef08a" stroke-width="1.5"/>
                                    <!-- Bull Head Armor -->
                                    <path d="M 22,34 L 78,34 L 72,74 Q 50,82 28,74 Z" fill="url(#foxFurGrad)" stroke="#F0B90B" stroke-width="2.2"/>
                                    <rect x="24" y="36" width="52" height="24" rx="9" fill="url(#visorGlassGrad)" stroke="#F0B90B" stroke-width="1.2"/>
                                    <!-- Bull Muzzle & Golden Ring -->
                                    <rect x="36" y="62" width="28" height="12" rx="6" fill="#1e293b" stroke="#F0B90B" stroke-width="1.2"/>
                                    <circle cx="50" cy="74" r="4" fill="none" stroke="#F0B90B" stroke-width="2"/>
                                </g>

                                <!-- ================= SKIN 4: ZEN PANDA ================= -->
                                <g id="skin-panda" class="mascot-skin-group hidden">
                                    <!-- Panda Round Ears -->
                                    <circle cx="24" cy="24" r="13" fill="#090d16" stroke="#0ECB81" stroke-width="2"/>
                                    <circle cx="76" cy="24" r="13" fill="#090d16" stroke="#0ECB81" stroke-width="2"/>
                                    <!-- Panda Face Contour -->
                                    <circle cx="50" cy="52" r="32" fill="url(#foxFurGrad)" stroke="#0ECB81" stroke-width="2.2"/>
                                    <!-- Bamboo Visor -->
                                    <rect x="23" y="38" width="54" height="22" rx="9" fill="url(#visorGlassGrad)" stroke="#0ECB81" stroke-width="1.2"/>
                                    <!-- Yin-Yang Forehead Emblem -->
                                    <circle cx="50" cy="28" r="4.5" fill="#0ECB81" opacity="0.9"/>
                                    <!-- Cute Panda Muzzle -->
                                    <ellipse cx="50" cy="65" rx="9" ry="6" fill="#0f172a" stroke="#0ECB81" stroke-width="1"/>
                                    <circle cx="50" cy="63" r="2.5" fill="#fff"/>
                                </g>

                                <!-- ================= INTERACTIVE DYNAMIC EYES (TRACKS CURSOR) ================= -->
                                <!-- Normal / Tracking Eyes -->
                                <g id="eyes-normal-layer">
                                    <!-- Left Eye Socket -->
                                    <g clip-path="url(#eyeClipLeft)">
                                        <rect x="25" y="35" width="20" height="22" fill="#08101e"/>
                                        <!-- Tracking Pupil Left -->
                                        <g id="pupil-left-group" class="mascot-pupil">
                                            <circle id="pupil-left-bg" cx="35" cy="46" r="6" fill="#0ECB81" class="robot-eye-glow"/>
                                            <circle cx="35" cy="46" r="2.8" fill="#022c22"/>
                                            <circle cx="33.5" cy="44.5" r="1.5" fill="#ffffff"/>
                                        </g>
                                        <!-- Top Eyelid (Blinking) -->
                                        <rect id="eyelid-top-left" x="25" y="34" width="20" height="0" fill="#090d16" class="mascot-eyelid"/>
                                    </g>

                                    <!-- Right Eye Socket -->
                                    <g clip-path="url(#eyeClipRight)">
                                        <rect x="55" y="35" width="20" height="22" fill="#08101e"/>
                                        <!-- Tracking Pupil Right -->
                                        <g id="pupil-right-group" class="mascot-pupil">
                                            <circle id="pupil-right-bg" cx="65" cy="46" r="6" fill="#0ECB81" class="robot-eye-glow"/>
                                            <circle cx="65" cy="46" r="2.8" fill="#022c22"/>
                                            <circle cx="63.5" cy="44.5" r="1.5" fill="#ffffff"/>
                                        </g>
                                        <!-- Top Eyelid (Blinking) -->
                                        <rect id="eyelid-top-right" x="55" y="34" width="20" height="0" fill="#090d16" class="mascot-eyelid"/>
                                    </g>
                                </g>

                                <!-- Reaction Eyes: Happy Crescent (^ ^) -->
                                <g id="eyes-happy-layer" class="hidden">
                                    <path d="M 27,48 Q 35,40 43,48" stroke="#0ECB81" stroke-width="3.5" stroke-linecap="round" fill="none" class="robot-eye-glow"/>
                                    <path d="M 57,48 Q 65,40 73,48" stroke="#0ECB81" stroke-width="3.5" stroke-linecap="round" fill="none" class="robot-eye-glow"/>
                                    <!-- Cute Blush Circles -->
                                    <ellipse cx="24" cy="54" rx="4" ry="2" fill="#f43f5e" opacity="0.6"/>
                                    <ellipse cx="76" cy="54" rx="4" ry="2" fill="#f43f5e" opacity="0.6"/>
                                </g>

                                <!-- Reaction Eyes: Alert / Crosshair Focus -->
                                <g id="eyes-alert-layer" class="hidden">
                                    <path d="M 27,43 L 43,49" stroke="#F6465D" stroke-width="3.5" stroke-linecap="round"/>
                                    <path d="M 73,43 L 57,49" stroke="#F6465D" stroke-width="3.5" stroke-linecap="round"/>
                                    <circle cx="35" cy="47" r="3" fill="#F6465D"/>
                                    <circle cx="65" cy="47" r="3" fill="#F6465D"/>
                                </g>

                                <!-- Reaction Eyes: Sleepy / Paused (- . -) -->
                                <g id="eyes-sleepy-layer" class="hidden">
                                    <line x1="27" y1="46" x2="43" y2="46" stroke="#F0B90B" stroke-width="3.5" stroke-linecap="round"/>
                                    <line x1="57" y1="46" x2="73" y2="46" stroke="#F0B90B" stroke-width="3.5" stroke-linecap="round"/>
                                    <!-- Floating Zzz -->
                                    <text x="68" y="32" fill="#F0B90B" font-size="11" font-family="monospace" font-weight="bold" class="zzz-item-1">Z</text>
                                    <text x="76" y="24" fill="#F0B90B" font-size="8" font-family="monospace" font-weight="bold" class="zzz-item-2">z</text>
                                </g>

                                <!-- Reaction Eyes: Heart Eyes (In Big Profit) -->
                                <g id="eyes-heart-layer" class="hidden">
                                    <path d="M 35,43 C 33,39 28,40 28,44 C 28,48 35,52 35,52 C 35,52 42,48 42,44 C 42,40 37,39 35,43 Z" fill="#ec4899" stroke="#f472b6" stroke-width="1"/>
                                    <path d="M 65,43 C 63,39 58,40 58,44 C 58,48 65,52 65,52 C 65,52 72,48 72,44 C 72,40 67,39 65,43 Z" fill="#ec4899" stroke="#f472b6" stroke-width="1"/>
                                </g>

                                <!-- Scanning Radar Beam (Only in Scanning Mode) -->
                                <g id="laser-scan-layer" class="hidden pointer-events-none">
                                    <line x1="50" y1="36" x2="50" y2="58" stroke="#00F0FF" stroke-width="2" stroke-linecap="round" opacity="0.85" class="laser-sweep-line"/>
                                </g>
                            </svg>

                            <!-- Pulse status badge -->
                            <span id="robot-status-dot" class="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-profitGreen border-2 border-darkBase flex items-center justify-center">
                                <span class="w-2 h-2 rounded-full bg-white animate-ping"></span>
                            </span>
                        </div>
                    </div>

                    <!-- Skin Switcher Bar -->
                    <div class="flex items-center gap-1 mt-2.5 bg-darkBase/90 p-1 rounded-xl border border-darkBorder/60 shadow-inner">
                        <button onclick="switchMascotSkin('fox')" id="btn-skin-fox" title="Cyber Kitsune (Cáo)" class="px-2 py-1 rounded-lg text-[11px] font-bold transition bg-cyan-950/80 text-cyberCyan border border-cyan-600/60 shadow-sm">🦊</button>
                        <button onclick="switchMascotSkin('robot')" id="btn-skin-robot" title="Cyber-Nova (Robot)" class="px-2 py-1 rounded-lg text-[11px] font-bold transition text-gray-400 hover:text-white">🤖</button>
                        <button onclick="switchMascotSkin('bull')" id="btn-skin-bull" title="Cyber Taurus (Bò Tót)" class="px-2 py-1 rounded-lg text-[11px] font-bold transition text-gray-400 hover:text-white">🐂</button>
                        <button onclick="switchMascotSkin('panda')" id="btn-skin-panda" title="Zen Panda (Gấu Trúc)" class="px-2 py-1 rounded-lg text-[11px] font-bold transition text-gray-400 hover:text-white">🐼</button>
                    </div>
                </div>

                <!-- Speech Bubble & Real-time Commentary -->
                <div class="flex-1 text-center sm:text-left space-y-2">
                    <div class="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                        <span class="font-extrabold text-sm text-cyberCyan flex items-center gap-1.5" id="mascot-skin-title">
                            <i class="fa-solid fa-microchip"></i> CYBER KITSUNE 9.0
                        </span>
                        <span id="robot-mood-chip" class="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-emerald-950/60 text-profitGreen border border-emerald-500/50 flex items-center gap-1">
                            <span class="w-1.5 h-1.5 rounded-full bg-profitGreen animate-pulse"></span>
                            <span id="robot-mood-text">SIÊU PHẤN KHỞI 🤩</span>
                        </span>
                        <span id="badge-ai-model-tag" class="text-[10px] px-2 py-0.5 rounded font-mono bg-green-950/60 text-profitGreen border border-green-600/50 hidden sm:inline">
                            GEMINI 2.5 FLASH ACTIVE
                        </span>
                    </div>

                    <!-- Interactive Dynamic Speech Balloon -->
                    <div class="p-3 sm:p-3.5 rounded-xl bg-darkBase/70 border border-cyan-950/60 text-xs sm:text-sm text-gray-100 font-medium leading-relaxed relative group cursor-pointer hover:border-cyan-700/50 transition" onclick="openAiModal()" title="Bấm vào đây để chat với Trợ lý AI">
                        <p id="robot-speech">
                            "Chào Sếp! Em là Cyber Kitsune. Em đang dõi theo từng nhịp nến và bảo vệ tài khoản cho Sếp 24/7!"
                        </p>
                        <div class="text-[9px] text-cyan-400/70 font-mono mt-1 flex items-center justify-end gap-1">
                            <span>Bấm để hỏi đáp chuyên sâu</span> <i class="fa-solid fa-arrow-right text-[8px]"></i>
                        </div>
                    </div>
                </div>

                <!-- Action Controls Bar -->
                <div class="grid grid-cols-3 sm:flex sm:flex-col items-center gap-2 flex-shrink-0 w-full sm:w-auto">

                    <button onclick="openAiModal()"  class="w-full py-2.5 px-2 sm:px-4 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black shadow-lg shadow-cyan-900/40 transition flex items-center justify-center gap-1.5 active:scale-95">
                        <i class="fa-solid fa-comments"></i> <span>Chat AI</span>
                    </button>
                    <button onclick="triggerMascotPoke(event)" class="w-full py-2 px-2 sm:px-3 rounded-xl text-xs font-semibold bg-darkBase hover:bg-cyan-950/40 text-cyan-300 border border-cyan-800/40 transition flex items-center justify-center gap-1 active:scale-95">
                        <i class="fa-solid fa-hand-pointer"></i> <span>Chọc Em 👋</span>
                    </button>
                    <button onclick="toggleSpeechVoice()" id="btn-voice-toggle" class="w-full py-2 px-2 sm:px-3 rounded-xl text-xs font-semibold bg-darkBase hover:bg-purple-950/40 text-purple-300 border border-purple-800/40 transition flex items-center justify-center gap-1 active:scale-95" title="Đọc giọng nói">
                        <i class="fa-solid fa-volume-high" id="icon-voice"></i> <span>Đọc Lời</span>
                    </button>
                    <button onclick="toggleFloatingMode()" id="btn-float-toggle" class="w-full py-2 px-2 sm:px-3 rounded-xl text-xs font-semibold bg-darkBase hover:bg-yellow-950/40 text-binanceGold border border-yellow-800/40 transition flex items-center justify-center gap-1 active:scale-95 hidden sm:flex" title="Ghim linh vật nổi ở góc màn hình">
                        <i class="fa-solid fa-thumbtack"></i> <span>Ghim Nổi</span>
                    </button>
                </div>
            </div>
        </div>

        
<!-- Institutional Protection & Filter Status Bar -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div class="glass-card p-3 rounded-xl flex items-center space-x-3">
                <div class="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
                    <i class="fa-solid fa-compass"></i>
                </div>
                <div>
                    <p class="text-[11px] text-gray-400 uppercase font-semibold">ADX Trend Filter</p>
                    <p class="text-xs font-bold text-white flex items-center gap-1" id="adx-filter-status">
                        <span class="text-profitGreen"><i class="fa-solid fa-circle-check"></i></span>
                        <span>ADX ≥ {config.adx_min} (Lọc Sideway)</span>
                    </p>
                </div>
            </div>

            <div class="glass-card p-3 rounded-xl flex items-center space-x-3">
                <div class="w-9 h-9 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center justify-center text-lossRed">
                    <i class="fa-solid fa-shield-halved"></i>
                </div>
                <div>
                    <p class="text-[11px] text-gray-400 uppercase font-semibold">BTC Crash Protection</p>
                    <p class="text-xs font-bold text-white flex items-center gap-1" id="btc-crash-status">
                        <span class="text-profitGreen"><i class="fa-solid fa-circle-check"></i></span>
                        <span>Bình Thường (Độ lệch 15m)</span>
                    </p>
                </div>
            </div>

            <div class="glass-card p-3 rounded-xl flex items-center space-x-3">
                <div class="w-9 h-9 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
                    <i class="fa-solid fa-newspaper"></i>
                </div>
                <div>
                    <p class="text-[11px] text-gray-400 uppercase font-semibold">Macro News Blackout</p>
                    <p class="text-xs font-bold text-white flex items-center gap-1" id="news-filter-status">
                        <span class="text-profitGreen"><i class="fa-solid fa-circle-check"></i></span>
                        <span>An Toàn (Né tin Mỹ)</span>
                    </p>
                </div>
            </div>

            <div class="glass-card p-3 rounded-xl flex items-center space-x-3">
                <div class="w-9 h-9 rounded-lg bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-center text-binanceGold">
                    <i class="fa-solid fa-crosshairs"></i>
                </div>
                <div>
                    <p class="text-[11px] text-gray-400 uppercase font-semibold">Dynamic Trailing Stop</p>
                    <p class="text-xs font-bold text-white flex items-center gap-1" id="trailing-stop-status">
                        <span class="text-profitGreen"><i class="fa-solid fa-circle-check"></i></span>
                        <span>BẬT (Khóa lãi tự động)</span>
                    </p>
                </div>
            </div>
        </div>

        
<!-- Section: Active Positions Terminal -->
        <div id="section-positions" class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-lg scroll-mt-20">
            <div class="px-4 sm:px-6 py-3.5 sm:py-4 border-b border-darkBorder flex flex-wrap items-center justify-between gap-3 bg-darkCard/50">
                <div class="flex items-center space-x-2.5 sm:space-x-3">
                    <span class="w-2.5 h-2.5 rounded-full bg-profitGreen animate-ping"></span>
                    <h2 class="font-bold text-white text-sm sm:text-base">CÁC VỊ THẾ ĐANG MỞ (LIVE POSITIONS)</h2>
                    <span id="badge-open-slots" class="px-2 sm:px-2.5 py-0.5 rounded-full text-[11px] sm:text-xs font-bold bg-darkBase border border-darkBorder text-gray-300">0 vị thế</span>
                </div>
                <!-- Controls: Pause & Panic Close -->
                <div class="flex items-center space-x-2 sm:space-x-3 w-full sm:w-auto justify-end">
                    <button id="btn-pause" onclick="togglePause()" class="flex-1 sm:flex-none px-3 sm:px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold bg-gray-800 hover:bg-gray-700 text-white border border-gray-700 transition flex items-center justify-center space-x-1.5">
                        <i id="btn-pause-icon" class="fa-solid fa-pause"></i>
                        <span id="btn-pause-text">Tạm Dừng Bot</span>
                    </button>
                    <button onclick="confirmPanicClose()" class="flex-1 sm:flex-none px-3 sm:px-4 py-2 rounded-xl text-xs sm:text-sm font-bold bg-lossRed/90 hover:bg-red-700 text-white border border-red-500/50 shadow-lg shadow-red-900/30 transition flex items-center justify-center space-x-1.5">
                        <i class="fa-solid fa-radiation"></i>
                        <span>ĐÓNG TẤT CẢ LỆNH</span>
                    </button>
                </div>
            </div>

            <!-- Desktop Table View -->
            <div class="hidden md:block overflow-x-auto">
                <table class="w-full text-left text-sm text-gray-300">
                    <thead class="bg-darkBase/80 text-[11px] uppercase tracking-wider text-gray-400 border-b border-darkBorder">
                        <tr>
                            <th class="px-5 py-3">Cặp Coin</th>
                            <th class="px-5 py-3">Chiều</th>
                            <th class="px-5 py-3">Giá Vào (Entry)</th>
                            <th class="px-5 py-3">Giá Hiện Tại</th>
                            <th class="px-5 py-3">Stop Loss</th>
                            <th class="px-5 py-3">Take Profit</th>
                            <th class="px-5 py-3">Tiến Trình (SL ➜ TP)</th>
                            <th class="px-5 py-3">Ký Quỹ</th>
                            <th class="px-5 py-3">PnL Tạm Tính</th>
                            <th class="px-5 py-3 text-center">Trạng Thái</th>
                            <th class="px-5 py-3 text-center">Thao Tác</th>
                        </tr>
                    </thead>
                    <tbody id="positions-table-body" class="divide-y divide-darkBorder font-mono text-xs sm:text-sm">
                        <tr>
                            <td colspan="11" class="px-6 py-8 text-center text-gray-400 font-sans">
                                <i class="fa-solid fa-spinner fa-spin text-binanceGold mr-2"></i> Đang tải danh sách vị thế thời gian thực...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Mobile Cards View -->
            <div id="positions-mobile-container" class="block md:hidden p-3 space-y-3">
                <div class="p-6 rounded-xl bg-darkBase/60 border border-darkBorder text-center space-y-2">
                    <i class="fa-solid fa-spinner fa-spin text-binanceGold text-lg"></i>
                    <p class="text-xs text-gray-400">Đang tải vị thế...</p>
                </div>
            </div>
        </div>

        
<!-- Section: Interactive Equity Curve Chart -->
        <div class="glass-card rounded-2xl p-5 border border-darkBorder">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-darkBorder">
                <div class="flex items-center space-x-2">
                    <i class="fa-solid fa-chart-area text-profitGreen"></i>
                    <h2 class="font-bold text-white text-base">BIỂU ĐỒ LỢI NHUẬN TÍCH LŨY (EQUITY CURVE)</h2>
                </div>
                <div class="text-xs text-gray-400 flex items-center gap-4">
                    <span><i class="fa-solid fa-circle text-[8px] text-profitGreen mr-1"></i>PnL Tích Lũy ($)</span>
                    <span>Tự động cập nhật theo từng lệnh đóng</span>
                </div>
            </div>
            <div class="h-64 sm:h-72 w-full mt-4">
                <canvas id="equityChart"></canvas>
            </div>
        </div>

        
<!-- Section: Recent Closed Trades History -->
        <div id="section-history" class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-lg scroll-mt-20">
            <div class="px-4 sm:px-6 py-3.5 sm:py-4 border-b border-darkBorder flex flex-wrap items-center justify-between gap-3 bg-darkCard/50">
                <div class="flex items-center space-x-2.5 sm:space-x-3">
                    <i class="fa-solid fa-clock-rotate-left text-binanceGold"></i>
                    <h2 class="font-bold text-white text-sm sm:text-base">NHẬT KÝ LỆNH ĐÃ ĐÓNG (TRADE HISTORY)</h2>
                </div>
                <div class="flex flex-wrap items-center gap-2 w-full sm:w-auto">
                    <div class="relative flex-1 sm:flex-none">
                        <input type="text" id="history-search" oninput="historyCurrentPage = 1; applyHistoryFilter()" placeholder="Tìm theo coin..." class="w-full sm:w-44 bg-darkBase text-xs px-3 py-1.5 pl-8 rounded-lg border border-darkBorder text-white focus:outline-none focus:border-binanceGold">
                        <i class="fa-solid fa-magnifying-glass text-gray-500 absolute left-2.5 top-2.5 text-xs"></i>
                    </div>
                    <button onclick="setFilterType('all')" id="btn-filter-all" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-binanceGold text-black">Tất cả</button>
                    <button onclick="setFilterType('win')" id="btn-filter-win" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-darkBase text-gray-300 border border-darkBorder hover:text-profitGreen">Thắng 🟢</button>
                    <button onclick="setFilterType('loss')" id="btn-filter-loss" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-darkBase text-gray-300 border border-darkBorder hover:text-lossRed">Thua 🔴</button>
                </div>
            </div>

            <!-- Desktop View -->
            <div class="hidden md:block overflow-x-auto">
                <table class="w-full text-left text-sm text-gray-300">
                    <thead class="bg-darkBase/80 text-[11px] uppercase tracking-wider text-gray-400 border-b border-darkBorder">
                        <tr>
                            <th class="px-5 py-3">Thời Gian</th>
                            <th class="px-5 py-3">Cặp Coin</th>
                            <th class="px-5 py-3">Chiều</th>
                            <th class="px-5 py-3">Giá Vào</th>
                            <th class="px-5 py-3">Giá Đóng</th>
                            <th class="px-5 py-3">Khối Lượng</th>
                            <th class="px-5 py-3">PnL ($)</th>
                            <th class="px-5 py-3">PnL (%)</th>
                            <th class="px-5 py-3">Lý Do Đóng Vị Thế</th>
                        </tr>
                    </thead>
                    <tbody id="history-table-body" class="divide-y divide-darkBorder font-mono text-xs">
                        <tr>
                            <td colspan="9" class="px-6 py-6 text-center text-gray-400 font-sans">Đang tải lịch sử giao dịch...</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Mobile View -->
            <div id="history-mobile-container" class="block md:hidden p-3 space-y-2.5">
                <div class="p-6 text-center text-xs text-gray-400 font-sans">Đang tải lịch sử giao dịch...</div>
            </div>

            <!-- History Pagination Controls -->
            <div id="history-pagination-container" class="px-4 sm:px-6 py-3 border-t border-darkBorder flex flex-wrap items-center justify-between gap-2.5 bg-darkCard/50 text-xs">
                <div class="flex items-center gap-2">
                    <span class="text-gray-400 text-xs hidden sm:inline">Hiển thị:</span>
                    <select id="history-page-size" onchange="changeHistoryPageSize(this.value)" class="bg-darkBase border border-darkBorder rounded-lg px-2 py-1 text-white font-mono text-xs focus:outline-none focus:border-binanceGold cursor-pointer">
                        <option value="10" selected>10 lệnh/trang</option>
                        <option value="20">20 lệnh/trang</option>
                        <option value="50">50 lệnh/trang</option>
                    </select>
                    <span id="history-pagination-info" class="text-gray-400 font-mono text-[11px] sm:text-xs">--</span>
                </div>
                <div class="flex items-center gap-1 sm:gap-1.5" id="history-pagination-buttons">
                    <!-- Dynamic page buttons -->
                </div>
            </div>
        </div>

        
        </div>

        <!-- ==================== TAB 2: RADAR QUÉT THỊ TRƯỜNG ==================== -->
        <div id="tab-radar" class="dashboard-workspace-tab space-y-4 sm:space-y-6 hidden">
<!-- Live Scanner Radar Section (BẢNG QUÉT THỊ TRƯỜNG THỜI GIAN THỰC) -->
        <div id="section-radar" class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-lg scroll-mt-20">
            <div class="px-4 sm:px-6 py-3.5 sm:py-4 border-b border-darkBorder flex flex-wrap items-center justify-between gap-3 bg-darkCard/50">
                <div class="flex items-center space-x-2.5 sm:space-x-3">
                    <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyberCyan text-sm flex-shrink-0">
                        <i class="fa-solid fa-satellite-dish animate-pulse"></i>
                    </div>
                    <div>
                        <h2 class="font-bold text-white text-sm sm:text-base flex items-center gap-2">
                            <span>RADAR QUÉT THỊ TRƯỜNG (LIVE SCANNER)</span>
                            <span id="radar-count-badge" class="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyberCyan border border-cyan-800">50 CẶP</span>
                        </h2>
                        <p class="text-[10px] sm:text-[11px] text-gray-400">Đa khung thời gian: 1H Trend (EMA50/200) + 15m RSI + ADX Lực Sóng</p>
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-[11px] sm:text-xs text-gray-400 font-mono" id="radar-updated-at">Đang cập nhật...</span>
                    <button onclick="fetchRadar()" class="p-2 rounded-lg bg-darkBase border border-darkBorder text-gray-300 hover:text-cyberCyan transition">
                        <i class="fa-solid fa-arrows-rotate text-xs"></i>
                    </button>
                </div>
            </div>

            <!-- Desktop Table View -->
            <div class="hidden md:block overflow-x-auto max-h-72 overflow-y-auto">
                <table class="w-full text-left text-xs text-gray-300">
                    <thead class="bg-darkBase/90 text-[10px] uppercase tracking-wider text-gray-400 border-b border-darkBorder sticky top-0 z-10 backdrop-blur-md">
                        <tr>
                            <th class="px-4 sm:px-5 py-2.5">Cặp Coin</th>
                            <th class="px-4 sm:px-5 py-2.5">Giá Hiện Tại</th>
                            <th class="px-4 sm:px-5 py-2.5">Xu Hướng 1H</th>
                            <th class="px-4 sm:px-5 py-2.5">RSI (15m)</th>
                            <th class="px-4 sm:px-5 py-2.5">ADX Lực Trend</th>
                            <th class="px-4 sm:px-5 py-2.5">Funding Rate</th>
                            <th class="px-4 sm:px-5 py-2.5">Trạng Thái Radar</th>
                            <th class="px-4 sm:px-5 py-2.5 text-center">Thao Tác</th>
                        </tr>
                    </thead>
                    <tbody id="radar-table-body" class="divide-y divide-darkBorder font-mono">
                        <tr>
                            <td colspan="8" class="px-6 py-8 text-center text-gray-400 font-sans">
                                <i class="fa-solid fa-satellite fa-spin text-cyberCyan mr-2"></i> Đang nạp radar quét thị trường...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Mobile Cards View for Radar -->
            <div id="radar-mobile-container" class="block md:hidden p-3 space-y-2.5 max-h-80 overflow-y-auto">
                <div class="p-6 rounded-xl bg-darkBase/60 border border-darkBorder text-center space-y-2">
                    <i class="fa-solid fa-satellite fa-spin text-cyberCyan text-lg"></i>
                    <p class="text-xs text-gray-400">Đang nạp radar quét thị trường...</p>
                </div>
            </div>
        </div>

        
        </div>

        <!-- ==================== TAB 3: CÁ MẬP & DÒNG TIỀN (SMC & CVD) ==================== -->
        <div id="tab-smart_money" class="dashboard-workspace-tab space-y-4 sm:space-y-6 hidden">
            <div class="glass-card rounded-2xl p-4 sm:p-5 border border-yellow-700/40 bg-gradient-to-r from-darkCard via-[#181d28] to-yellow-950/20 shadow-xl">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-center text-binanceGold text-lg flex-shrink-0">
                        <i class="fa-solid fa-shapes"></i>
                    </div>
                    <div>
                        <h2 class="text-base sm:text-lg font-extrabold text-white flex items-center gap-2">
                            <span>PHÂN TÍCH KHỐI LỆNH CÁ MẬP & DÒNG TIỀN THỰC (SMC & CVD)</span>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-yellow-950 text-binanceGold border border-yellow-700/50">INSTITUTIONAL GRADE</span>
                        </h2>
                        <p class="text-xs text-gray-400 mt-0.5">Soi cấu trúc nến tổ chức (Order Block, Fair Value Gap) kết hợp dòng tiền mua/bán thực tế (Cumulative Volume Delta) trên sàn Binance.</p>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                <!-- SMC Detector -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-center text-binanceGold text-sm">
                                <i class="fa-solid fa-shapes"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">SOI KHỐI LỆNH TỔ CHỨC (SMC AI)</h3>
                                <p class="text-[10px] text-gray-400">Order Block (OB), Fair Value Gap (FVG) & Quét Râu</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-1 text-[10px] font-mono">
                            <button type="button" onclick="fetchSMC('BTCUSDT')" class="px-2 py-1 rounded-lg bg-darkBase border border-darkBorder hover:border-binanceGold text-gray-300">BTC</button>
                            <button type="button" onclick="fetchSMC('ETHUSDT')" class="px-2 py-1 rounded-lg bg-darkBase border border-darkBorder hover:border-binanceGold text-gray-300">ETH</button>
                            <button type="button" onclick="fetchSMC('SOLUSDT')" class="px-2 py-1 rounded-lg bg-darkBase border border-darkBorder hover:border-binanceGold text-gray-300">SOL</button>
                        </div>
                    </div>
                    <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
                        <div class="flex items-center justify-between text-xs pb-2 border-b border-darkBorder">
                            <span class="text-gray-400">Cặp phân tích: <b id="smc-symbol" class="text-white font-mono">BTCUSDT</b></span>
                            <span id="smc-bias-badge" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-yellow-950 text-binanceGold border border-yellow-700/50">CÂN BẰNG</span>
                        </div>
                        <div class="grid grid-cols-2 gap-3 text-xs font-mono">
                            <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Khối Lệnh Order Block (OB)</span>
                                <span id="smc-ob-text" class="text-white text-xs font-bold mt-1 block">Chưa có OB mới</span>
                            </div>
                            <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Khoảng Trống Giá (FVG)</span>
                                <span id="smc-fvg-text" class="text-binanceGold text-xs font-bold mt-1 block">Chưa có FVG mới</span>
                            </div>
                        </div>
                        <div class="p-3 rounded-xl bg-darkBase/80 border border-darkBorder text-xs flex items-center gap-2">
                            <span class="w-2.5 h-2.5 rounded-full bg-binanceGold animate-ping"></span>
                            <span id="smc-sweep-text" class="text-gray-300 text-xs">Đang quét bẫy thanh khoản nến...</span>
                        </div>
                    </div>
                </div>

                <!-- Order Flow & CVD -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyberCyan text-sm">
                                <i class="fa-solid fa-chart-simple"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">DÒNG TIỀN MUA / BÁN THỰC TẾ (CVD)</h3>
                                <p class="text-[10px] text-gray-400">Cumulative Volume Delta & Hấp Thụ Lực Mua Bán</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-1 text-[10px] font-mono">
                            <button type="button" onclick="fetchOrderFlow('BTCUSDT')" class="px-2 py-1 rounded-lg bg-darkBase border border-darkBorder hover:border-cyberCyan text-gray-300">BTC</button>
                            <button type="button" onclick="fetchOrderFlow('ETHUSDT')" class="px-2 py-1 rounded-lg bg-darkBase border border-darkBorder hover:border-cyberCyan text-gray-300">ETH</button>
                            <button type="button" onclick="fetchOrderFlow('SOLUSDT')" class="px-2 py-1 rounded-lg bg-darkBase border border-darkBorder hover:border-cyberCyan text-gray-300">SOL</button>
                        </div>
                    </div>
                    <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
                        <div class="flex items-center justify-between text-xs pb-2 border-b border-darkBorder">
                            <span class="text-gray-400">Cặp phân tích: <b id="of-symbol" class="text-white font-mono">BTCUSDT</b></span>
                            <span id="of-bias-badge" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700/50">CÂN BẰNG</span>
                        </div>
                        <div class="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                            <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Delta Volume</span>
                                <span id="of-delta" class="font-extrabold text-white text-sm">0.00</span>
                            </div>
                            <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Tỷ Lệ CVD</span>
                                <span id="of-cvd-pct" class="font-extrabold text-binanceGold text-sm">0.0%</span>
                            </div>
                            <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Mua / Bán Ratio</span>
                                <span id="of-imbalance" class="font-extrabold text-cyberCyan text-sm">1.0x</span>
                            </div>
                        </div>
                        <div class="p-3 rounded-xl bg-darkBase/80 border border-darkBorder text-xs">
                            <span class="text-gray-400 block text-[10px] uppercase font-bold text-gray-500 mb-0.5 font-sans">Đánh giá dòng tiền Smart Money:</span>
                            <p id="of-desc" class="text-gray-200 text-xs leading-relaxed">Đang tải dữ liệu luồng lệnh Order Flow...</p>
                        </div>
                    </div>
                </div>

                <!-- Whale Tracker -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 text-sm">
                                <i class="fa-solid fa-gem"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">RADAR THEO DÕI VÍ CÁ VOI</h3>
                                <p class="text-[10px] text-gray-400">Dòng Tiền Ròng & Giao Dịch Ví Khủng (> $2M USD)</p>
                            </div>
                        </div>
                        <span id="whale-bias-tag" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-indigo-950 text-indigo-300 border border-indigo-700/50">TÍCH LŨY 🟢</span>
                    </div>
                    <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
                        <div id="whale-transfers-list" class="space-y-2 max-h-48 overflow-y-auto pr-1">
                            <div class="p-2.5 rounded-xl bg-darkBase/70 border border-darkBorder text-xs text-gray-400">
                                Đang kết nối luồng giám sát ví cá voi...
                            </div>
                        </div>
                        <div class="flex items-center justify-between text-xs text-gray-400 pt-2 border-t border-darkBorder font-mono">
                            <span>Thanh khoản Stablecoin: <b id="whale-liquidity-status" class="text-profitGreen">DỒI DÀO</b></span>
                            <span class="text-gray-500">Giám sát lệnh > $2M USD</span>
                        </div>
                    </div>
                </div>

                <!-- Liquidation Radar -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center justify-center text-lossRed text-sm">
                                <i class="fa-solid fa-water"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">BẢN ĐỒ THANH LÝ ĐÒN BẨY LỚN</h3>
                                <p class="text-[10px] text-gray-400">Ước Tính Cụm Thanh Lý & Bẫy Râu Nến</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-1 text-[10px] font-mono">
                            <button type="button" onclick="fetchLiquidationRadar('BTCUSDT')" class="px-2 py-1 rounded-lg bg-darkBase border border-darkBorder hover:border-binanceGold text-gray-300">BTC</button>
                            <button type="button" onclick="fetchLiquidationRadar('ETHUSDT')" class="px-2 py-1 rounded-lg bg-darkBase border border-darkBorder hover:border-binanceGold text-gray-300">ETH</button>
                            <button type="button" onclick="fetchLiquidationRadar('SOLUSDT')" class="px-2 py-1 rounded-lg bg-darkBase border border-darkBorder hover:border-binanceGold text-gray-300">SOL</button>
                        </div>
                    </div>
                    <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
                        <div class="flex items-center justify-between text-xs pb-2 border-b border-darkBorder">
                            <span class="text-gray-400">Cặp phân tích: <b id="liq-symbol" class="text-white font-mono">BTCUSDT</b></span>
                            <span class="text-gray-400">Giá sàn: <b id="liq-cur-price" class="text-binanceGold font-mono">$0.00</b></span>
                        </div>
                        <div class="space-y-2 text-xs font-mono">
                            <div class="p-2.5 rounded-xl bg-red-950/20 border border-red-900/30">
                                <div class="flex justify-between text-xs text-red-400 font-bold mb-1.5 font-sans">
                                    <span>🔻 Vùng Thanh Lý Phe SHORT (Trên Giá):</span>
                                    <span id="liq-short-levels">--</span>
                                </div>
                                <div class="text-[11px] text-gray-400 flex justify-between">
                                    <span>100x: <b id="liq-s100" class="text-red-300">--</b></span>
                                    <span>50x: <b id="liq-s50" class="text-red-300">--</b></span>
                                    <span>20x: <b id="liq-s20" class="text-red-300">--</b></span>
                                </div>
                            </div>
                            <div class="p-2.5 rounded-xl bg-green-950/20 border border-green-900/30">
                                <div class="flex justify-between text-xs text-profitGreen font-bold mb-1.5 font-sans">
                                    <span>🟢 Vùng Thanh Lý Phe LONG (Dưới Giá):</span>
                                    <span id="liq-long-levels">--</span>
                                </div>
                                <div class="text-[11px] text-gray-400 flex justify-between">
                                    <span>100x: <b id="liq-l100" class="text-green-300">--</b></span>
                                    <span>50x: <b id="liq-l50" class="text-green-300">--</b></span>
                                    <span>20x: <b id="liq-l20" class="text-green-300">--</b></span>
                                </div>
                            </div>
                        </div>
                        <p class="text-[11px] text-gray-400 font-sans italic">* Canh nhịp quét thanh khoản (Liquidity Sweep) để vào lệnh Sniper R:R cực cao.</p>
                    </div>
                </div>
                <!-- L2/L3 Order Book Microstructure Card (Bản 11.0) -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col lg:col-span-2">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyberCyan text-sm">
                                <i class="fa-solid fa-layer-group"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">L2/L3 SỔ LỆNH VI MÔ & TƯỜNG ẨN ICEBERG</h3>
                                <p class="text-[10px] text-gray-400">Order Book Imbalance (OBI), Tường Lệnh Ẩn & Cảnh Báo Spoofing</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-1 text-[10px] font-mono">
                            <button type="button" onclick="fetchMicrostructure('BTCUSDT')" class="px-2 py-1 rounded-lg bg-darkBase border border-darkBorder hover:border-cyberCyan text-gray-300">BTC</button>
                            <button type="button" onclick="fetchMicrostructure('ETHUSDT')" class="px-2 py-1 rounded-lg bg-darkBase border border-darkBorder hover:border-cyberCyan text-gray-300">ETH</button>
                            <button type="button" onclick="fetchMicrostructure('SOLUSDT')" class="px-2 py-1 rounded-lg bg-darkBase border border-darkBorder hover:border-cyberCyan text-gray-300">SOL</button>
                        </div>
                    </div>
                    <div class="p-4 space-y-3">
                        <div class="flex items-center justify-between text-xs pb-2 border-b border-darkBorder">
                            <span class="text-gray-400 font-sans">Mục tiêu: <b id="micro-symbol" class="text-white font-mono">BTCUSDT</b></span>
                            <span id="micro-bias-badge" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700/50">CÂN BẰNG</span>
                        </div>
                        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs font-mono">
                            <div class="p-2.5 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Tỷ Lệ Lệch OBI</span>
                                <span id="micro-obi" class="font-extrabold text-white text-sm">+0.035</span>
                            </div>
                            <div class="p-2.5 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Spread Bước Giá</span>
                                <span id="micro-spread" class="font-extrabold text-binanceGold text-sm">0.0006%</span>
                            </div>
                            <div class="p-2.5 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Tổng Vol Bid / Ask</span>
                                <span id="micro-vol" class="font-extrabold text-cyan-300 text-xs">450 / 420</span>
                            </div>
                            <div class="p-2.5 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Rủi Ro Tường Ảo</span>
                                <span id="micro-spoof" class="font-bold text-profitGreen text-xs">THẤP</span>
                            </div>
                        </div>
                        <div id="micro-icebergs" class="space-y-1.5 text-xs font-mono">
                            <div class="p-2 rounded-lg bg-darkBase/60 border border-darkBorder text-[11px] text-gray-400">Đang quét tường lệnh ẩn...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- ==================== TAB 4: AI TỰ TIẾN HÓA & BẮT SÓNG TRỄ ==================== -->
        <div id="tab-ai_arbitrage" class="dashboard-workspace-tab space-y-4 sm:space-y-6 hidden">
            <div class="glass-card rounded-2xl p-4 sm:p-5 border border-purple-700/40 bg-gradient-to-r from-darkCard via-[#1d1628] to-purple-950/20 shadow-xl">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 text-lg flex-shrink-0">
                        <i class="fa-solid fa-brain"></i>
                    </div>
                    <div>
                        <h2 class="text-base sm:text-lg font-extrabold text-white flex items-center gap-2">
                            <span>TRÍ TUỆ NHÂN TẠO TỰ TIẾN HÓA & BẮT SÓNG TRỄ ĐỘ TRỄ THẤP</span>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-950 text-purple-300 border border-purple-700/50">QUANT AI</span>
                        </h2>
                        <p class="text-xs text-gray-400 mt-0.5">AI tự tối ưu bộ thông số RSI/ATR theo chu kỳ thị trường và tự động đón nhịp kéo của Altcoin khi Bitcoin bứt phá xung lực.</p>
                    </div>
                </div>
            </div>

            <!-- AI QUANT SELF-TRAINING ENGINE (HỌC TỰ ĐỘNG TỪ LỊCH SỬ LỆNH) -->
            <div id="card-ai-trainer" class="glass-card rounded-2xl overflow-hidden border border-purple-500/30 bg-gradient-to-br from-darkCard via-[#181126] to-purple-950/30 shadow-2xl">
                <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/80 flex flex-wrap items-center justify-between gap-2">
                    <div class="flex items-center space-x-2.5">
                        <div class="w-8 h-8 rounded-lg bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-purple-300 text-sm">
                            <i class="fa-solid fa-graduation-cap"></i>
                        </div>
                        <div>
                            <h3 class="font-bold text-white text-xs sm:text-sm flex items-center gap-2">
                                <span>AI QUANT SELF-TRAINING ENGINE (HỌC TỰ ĐỘNG TỪ LỊCH SỬ)</span>
                                <span class="px-2 py-0.5 rounded text-[9px] font-bold bg-green-950 text-profitGreen border border-green-700/50">🟢 TỰ ĐỘNG 24/7</span>
                            </h3>
                            <p class="text-[10px] text-gray-400">🤖 <b>Tự động học 24/7</b> ngay sau mỗi lệnh đóng & chu kỳ 15 phút để tự tối ưu hóa RSI, ATR, R:R và xác suất thắng từng coin</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <span id="ai-train-confidence-badge" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-purple-950 text-purple-300 border border-purple-700/50 font-mono">ĐỘ TIN CẬY: 75%</span>
                        <button type="button" onclick="triggerAITraining()" id="btn-trigger-ai-train" class="px-3 py-1.5 rounded-xl text-xs font-bold bg-binanceGold hover:bg-yellow-400 text-black shadow-md shadow-yellow-900/30 transition flex items-center gap-1.5 active:scale-95">
                            <i class="fa-solid fa-rotate text-xs" id="icon-retrain"></i>
                            <span>Ép Chạy Lại Ngay</span>
                        </button>
                    </div>
                </div>
                <div class="p-4 sm:p-5 space-y-4">
                    <!-- KPI Metrics from AI Training -->
                    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 text-center font-mono">
                        <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                            <span class="text-[10px] text-gray-400 block font-sans">Mẫu Lệnh Học</span>
                            <span id="ai-train-samples" class="font-extrabold text-white text-base mt-0.5 block">--</span>
                        </div>
                        <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                            <span class="text-[10px] text-gray-400 block font-sans">Win Rate Lịch Sử</span>
                            <span id="ai-train-winrate" class="font-extrabold text-profitGreen text-base mt-0.5 block">--%</span>
                        </div>
                        <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                            <span class="text-[10px] text-gray-400 block font-sans">Profit Factor (PF)</span>
                            <span id="ai-train-pf" class="font-extrabold text-binanceGold text-base mt-0.5 block">--</span>
                        </div>
                        <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                            <span class="text-[10px] text-gray-400 block font-sans">RSI Tối Ưu Mua/Bán</span>
                            <span id="ai-train-rsi" class="font-extrabold text-purple-300 text-sm mt-0.5 block">-- / --</span>
                        </div>
                        <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                            <span class="text-[10px] text-gray-400 block font-sans">Hệ Số Dừng Lỗ ATR</span>
                            <span id="ai-train-atr" class="font-extrabold text-cyan-300 text-sm mt-0.5 block">--x ATR</span>
                        </div>
                        <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                            <span class="text-[10px] text-gray-400 block font-sans">Tỷ Lệ Mục Tiêu R:R</span>
                            <span id="ai-train-rr" class="font-extrabold text-yellow-300 text-sm mt-0.5 block">1:--</span>
                        </div>
                    </div>

                    <!-- Coin Preferences & AI Insights -->
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
                        <div class="p-3.5 rounded-xl bg-darkBase/60 border border-darkBorder space-y-2">
                            <div class="flex items-center justify-between">
                                <span class="text-xs font-bold text-gray-300 font-sans flex items-center gap-1.5">
                                    <i class="fa-solid fa-thumbs-up text-profitGreen"></i> Top Coin Ưu Tiên Vào Lệnh (Conviction Cao)
                                </span>
                            </div>
                            <div id="ai-favored-coins" class="flex flex-wrap gap-1.5 text-xs font-mono">
                                <span class="px-2 py-1 rounded-lg bg-green-950/60 text-profitGreen border border-green-800/40">Đang phân tích...</span>
                            </div>
                            <div class="pt-2 border-t border-darkBorder/60 flex items-center justify-between">
                                <span class="text-xs font-bold text-gray-400 font-sans flex items-center gap-1.5">
                                    <i class="fa-solid fa-shield-halved text-yellow-400"></i> Coin Cần Hạn Chế (Tỷ Lệ Lỗ Cao)
                                </span>
                            </div>
                            <div id="ai-avoid-coins" class="flex flex-wrap gap-1.5 text-xs font-mono">
                                <span class="px-2 py-1 rounded-lg bg-darkCard text-gray-400 border border-darkBorder">Không có coin bị gắn cờ rủi ro</span>
                            </div>
                        </div>

                        <div class="p-3.5 rounded-xl bg-darkBase/60 border border-darkBorder space-y-2">
                            <span class="text-xs font-bold text-purple-300 font-sans flex items-center gap-1.5">
                                <i class="fa-solid fa-lightbulb text-binanceGold"></i> Nhận Định Khai Phá Mẫu Hình (Pattern Mining)
                            </span>
                            <div id="ai-pattern-insights" class="space-y-1.5 text-xs text-gray-300 font-sans">
                                <p class="text-gray-500 italic text-[11px]">Đang trích xuất tri thức từ các lệnh đã đóng...</p>
                            </div>
                            <div class="pt-1 text-[10px] text-gray-500 font-mono flex items-center justify-between">
                                <span>Cập nhật lần cuối: <span id="ai-train-time" class="text-gray-400">--</span></span>
                                <span class="text-profitGreen">● Tự động đồng bộ vào Market Scanner</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                <!-- Neural Synthesizer -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 text-sm">
                                <i class="fa-solid fa-brain"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">BỘ NÃO TỰ TIẾN HÓA (SYNTHESIZER 10.0)</h3>
                                <p class="text-[10px] text-gray-400">Tự Động Tối Ưu Hóa Tham Số Theo Chu Kỳ Thị Trường</p>
                            </div>
                        </div>
                        <span id="synth-mode-tag" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-purple-950 text-purple-300 border border-purple-700/50">TỰ TIẾN HÓA</span>
                    </div>
                    <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
                        <div class="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                            <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Dải RSI Động</span>
                                <span id="synth-rsi" class="font-extrabold text-white text-sm mt-1 block">28 / 72</span>
                            </div>
                            <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Hệ Số ATR SL</span>
                                <span id="synth-atr" class="font-extrabold text-binanceGold text-sm mt-1 block">1.6x</span>
                            </div>
                            <div class="p-3 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Winrate Kỳ Vọng</span>
                                <span id="synth-wr" class="font-extrabold text-profitGreen text-sm mt-1 block">56.5%</span>
                            </div>
                        </div>
                        <div class="p-3 rounded-xl bg-darkBase/80 border border-darkBorder text-xs">
                            <span class="text-gray-400 block text-[10px] uppercase font-bold text-gray-500 mb-0.5 font-sans">Cơ sở lý luận của AI:</span>
                            <p id="synth-rationale" class="text-gray-200 text-xs leading-relaxed">Đang phân tích cấu trúc nến để tối ưu hóa...</p>
                        </div>
                    </div>
                </div>

                <!-- Lead-Lag Sniper -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyberCyan text-sm">
                                <i class="fa-solid fa-bolt-lightning"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">BẮT SÓNG TRỄ ALTCOIN THEO BITCOIN</h3>
                                <p class="text-[10px] text-gray-400">BTC Dẫn Sóng & Bắn Tỉa Altcoin Chạy Sau</p>
                            </div>
                        </div>
                        <span id="lead-momentum-badge" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-cyan-950 text-cyberCyan border border-cyan-700/50 font-mono">BTC 0.0%</span>
                    </div>
                    <div class="p-4 flex-1 overflow-x-auto">
                        <table class="w-full text-left text-xs text-gray-300">
                            <thead class="text-[10px] uppercase text-gray-400 border-b border-darkBorder font-mono">
                                <tr>
                                    <th class="py-2 px-2.5">Cặp Altcoin</th>
                                    <th class="py-2 px-2.5">Độ Lệch Xung Lực</th>
                                    <th class="py-2 px-2.5 text-right">Tín Hiệu Bắn Tỉa</th>
                                </tr>
                            </thead>
                            <tbody id="lead-lag-body" class="divide-y divide-darkBorder font-mono text-xs">
                                <tr><td colspan="3" class="py-4 text-center text-gray-500 font-sans">Đang quét độ trễ xung lực Altcoin...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Basis Arbitrage -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 text-sm">
                                <i class="fa-solid fa-scale-balanced"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">LỢI TỨC CHÊNH LỆCH SPOT VS FUTURES</h3>
                                <p class="text-[10px] text-gray-400">Cash-and-Carry Nội Bộ Sàn Binance Phi Rủi Ro Giá</p>
                            </div>
                        </div>
                        <span class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-rose-950/60 text-rose-300 border border-rose-800/40 font-mono">12% - 28% APY</span>
                    </div>
                    <div class="p-4 flex-1 overflow-x-auto">
                        <table class="w-full text-left text-xs text-gray-300">
                            <thead class="text-[10px] uppercase text-gray-400 border-b border-darkBorder font-mono">
                                <tr>
                                    <th class="py-2 px-2.5">Tài Sản</th>
                                    <th class="py-2 px-2.5">Chênh Lệch Basis</th>
                                    <th class="py-2 px-2.5">Trạng Thái</th>
                                    <th class="py-2 px-2.5 text-right">Lợi Nhuận APY</th>
                                </tr>
                            </thead>
                            <tbody id="basis-arbitrage-body" class="divide-y divide-darkBorder font-mono text-xs">
                                <tr><td colspan="4" class="py-4 text-center text-gray-500 font-sans">Đang tính toán chênh lệch Basis...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Pairs Trading -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-profitGreen text-sm">
                                <i class="fa-solid fa-code-compare"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">GIAO DỊCH CẶP ĐỒNG PHA (PAIRS TRADING)</h3>
                                <p class="text-[10px] text-gray-400">Chiến Lược Spread Mean Reversion Z-Score</p>
                            </div>
                        </div>
                        <span class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-emerald-950/60 text-profitGreen border border-emerald-800/40">DELTA-NEUTRAL</span>
                    </div>
                    <div class="p-4 flex-1 overflow-x-auto">
                        <table class="w-full text-left text-xs text-gray-300">
                            <thead class="text-[10px] uppercase text-gray-400 border-b border-darkBorder font-mono">
                                <tr>
                                    <th class="py-2 px-2.5">Cặp Đồng Pha</th>
                                    <th class="py-2 px-2.5">Spread Giá</th>
                                    <th class="py-2 px-2.5">Z-Score</th>
                                    <th class="py-2 px-2.5 text-right">Khuyến Nghị</th>
                                </tr>
                            </thead>
                            <tbody id="pairs-trading-body" class="divide-y divide-darkBorder font-mono text-xs">
                                <tr><td colspan="4" class="py-4 text-center text-gray-500 font-sans">Đang tính toán ma trận Cointegration...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <!-- Adaptive Smart Grid Card (Bản 11.0) -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-center text-binanceGold text-sm">
                                <i class="fa-solid fa-table-cells"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">LƯỚI LƯỢNG TỬ CO DÃN ATR</h3>
                                <p class="text-[10px] text-gray-400">Adaptive Smart Grid Khắc Phục Gồng Lỗ Kẹt Lưới</p>
                            </div>
                        </div>
                        <span id="grid-state-tag" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-yellow-950 text-binanceGold border border-yellow-700/50">BÌNH THƯỜNG</span>
                    </div>
                    <div class="p-4 space-y-2.5 flex-1 flex flex-col justify-between">
                        <div class="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                            <div class="p-2 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Bước Lưới Động</span>
                                <span id="grid-spacing" class="font-extrabold text-white text-sm mt-0.5 block">0.65%</span>
                            </div>
                            <div class="p-2 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Biến Động ATR</span>
                                <span id="grid-atr" class="font-extrabold text-binanceGold text-sm mt-0.5 block">1.1%</span>
                            </div>
                            <div class="p-2 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Lãi Lưới APY</span>
                                <span id="grid-apy" class="font-extrabold text-profitGreen text-sm mt-0.5 block">106.8%</span>
                            </div>
                        </div>
                        <div class="p-2.5 rounded-xl bg-darkBase/80 border border-darkBorder text-xs text-gray-300 font-mono space-y-1">
                            <div class="flex justify-between text-[11px]">
                                <span class="text-gray-400 font-sans">Biên Lưới Dưới / Trên:</span>
                                <span id="grid-boundaries" class="text-white font-bold">$74,511 - $78,489</span>
                            </div>
                            <div class="text-[10px] text-profitGreen font-sans italic" id="grid-safety-kill">* Tự ngắt khẩn cấp khi giá bứt phá khỏi biên độ an toàn.</div>
                        </div>
                    </div>
                </div>

                <!-- Multi-Asset PCA Basket Card (Bản 11.0) -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 text-sm">
                                <i class="fa-solid fa-diagram-project"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">RỔ 8 COIN PHÂN TÍCH THÀNH PHẦN CHÍNH (PCA)</h3>
                                <p class="text-[10px] text-gray-400">Eigenvector Xu Hướng Chung & Bắt Sóng Lệch Residual</p>
                            </div>
                        </div>
                        <span id="pca-status-tag" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-purple-950 text-purple-300 border border-purple-700/50">ĐỒNG PHA</span>
                    </div>
                    <div class="p-3 flex-1 overflow-x-auto">
                        <table class="w-full text-left text-xs text-gray-300">
                            <thead class="text-[10px] uppercase text-gray-400 border-b border-darkBorder font-mono">
                                <tr>
                                    <th class="py-1.5 px-2">Cặp Coin</th>
                                    <th class="py-1.5 px-2">24h (%)</th>
                                    <th class="py-1.5 px-2">Độ Lệch Residual</th>
                                    <th class="py-1.5 px-2 text-right">Khuyến Nghị</th>
                                </tr>
                            </thead>
                            <tbody id="pca-basket-body" class="divide-y divide-darkBorder font-mono text-xs">
                                <tr><td colspan="4" class="py-3 text-center text-gray-500 font-sans">Đang tính toán ma trận PCA...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- ==================== TAB 5: QUẢN TRỊ DANH MỤC & VĨ MÔ ==================== -->
        <div id="tab-portfolio" class="dashboard-workspace-tab space-y-4 sm:space-y-6 hidden">
            <div class="glass-card rounded-2xl p-4 sm:p-5 border border-emerald-700/40 bg-gradient-to-r from-darkCard via-[#12221b] to-emerald-950/20 shadow-xl">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-profitGreen text-lg flex-shrink-0">
                        <i class="fa-solid fa-chart-pie"></i>
                    </div>
                    <div>
                        <h2 class="text-base sm:text-lg font-extrabold text-white flex items-center gap-2">
                            <span>TÁI CÂN BẰNG DANH MỤC RỦI RO NGANG GIÁ (RISK-PARITY) & VĨ MÔ</span>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700/50">RAY DALIO MODEL</span>
                        </h2>
                        <p class="text-xs text-gray-400 mt-0.5">Phân bổ tỷ trọng thông minh giữa BTC, ETH, SOL và quỹ dự phòng tiền mặt USDT dựa trên độ biến động nghịch đảo.</p>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                <!-- Risk Parity Rebalancer -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-profitGreen text-sm">
                                <i class="fa-solid fa-chart-pie"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">TÁI CÂN BẰNG DANH MỤC RỦI RO NGANG GIÁ</h3>
                                <p class="text-[10px] text-gray-400">Risk-Parity Basket: BTC, ETH, SOL, USDT</p>
                            </div>
                        </div>
                        <span id="rebalance-health-badge" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700/50">CÂN BẰNG TỐI ƯU</span>
                    </div>
                    <div class="p-4 flex-1 overflow-x-auto">
                        <table class="w-full text-left text-xs text-gray-300">
                            <thead class="text-[10px] uppercase text-gray-400 border-b border-darkBorder font-mono">
                                <tr>
                                    <th class="py-2 px-2.5">Tài Sản</th>
                                    <th class="py-2 px-2.5">Tỷ Trọng (Hiện / Chuẩn)</th>
                                    <th class="py-2 px-2.5">Độ Lệch</th>
                                    <th class="py-2 px-2.5 text-right">Khuyến Nghị</th>
                                </tr>
                            </thead>
                            <tbody id="rebalance-body" class="divide-y divide-darkBorder font-mono text-xs">
                                <tr><td colspan="4" class="py-4 text-center text-gray-500 font-sans">Đang tính toán tỷ trọng danh mục...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Macro News Sentinel -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 text-sm">
                                <i class="fa-solid fa-satellite"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">BỘ LỌC BÃO TIN TỨC VĨ MÔ</h3>
                                <p class="text-[10px] text-gray-400">Giám Sát Tin Tức Lãi Suất & Cảnh Báo Biến Động</p>
                            </div>
                        </div>
                        <span id="news-blackout-badge" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700/50">AN TOÀN</span>
                    </div>
                    <div class="p-4 flex-1 flex flex-col justify-between">
                        <div id="macro-news-feed" class="space-y-2 max-h-52 overflow-y-auto pr-1">
                            <div class="p-2.5 rounded-xl bg-darkBase/70 border border-darkBorder text-xs text-gray-400">
                                Đang tải dòng tin tức thị trường...
                            </div>
                        </div>
                        <div class="flex items-center justify-between text-[11px] text-gray-400 mt-2 font-sans pt-2 border-t border-darkBorder">
                            <span>Tự động Blackout né biến động 30m</span>
                            <span class="text-purple-400">CryptoPanic & Binance News</span>
                        </div>
                    </div>
                </div>

                <!-- Quantum Voice Commander -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col lg:col-span-2">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyberCyan text-sm">
                                <i class="fa-solid fa-microphone-lines"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">TRUNG TÂM RA LỆNH GIỌNG NÓI & VĂN BẢN TIẾNG VIỆT</h3>
                                <p class="text-[10px] text-gray-400">Điều Khiển Bot Bằng Lời Nói Tự Nhiên & Phản Hồi Âm Thanh</p>
                            </div>
                        </div>
                        <span class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-cyan-950 text-cyberCyan border border-cyan-700/50">TWO-WAY AI</span>
                    </div>
                    <div class="p-4 space-y-3">
                        <div class="flex items-center gap-2">
                            <input type="text" id="voice-cmd-input" onkeydown="if(event.key==='Enter') sendQuantumCommand()" placeholder="Ví dụ: 'Báo cáo PnL', 'Giảm đòn bẩy xuống 3x', 'Tạm dừng bot'..." class="flex-1 bg-darkBase border border-darkBorder rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyberCyan transition font-sans">
                            <button type="button" onclick="sendQuantumCommand()" class="px-4 py-2.5 rounded-xl bg-cyberCyan hover:bg-cyan-400 text-black font-bold text-xs shadow-lg shadow-cyan-900/40 transition flex items-center gap-1.5 flex-shrink-0 active:scale-95">
                                <i class="fa-solid fa-terminal text-[10px]"></i> <span>Thi Hành</span>
                            </button>
                            <button type="button" onclick="startVoiceRecognition()" id="btn-mic-listen" class="w-10 h-10 rounded-xl bg-darkBase border border-darkBorder hover:border-cyberCyan text-cyan-400 flex items-center justify-center transition flex-shrink-0 active:scale-95" title="Bấm để nói bằng micro">
                                <i class="fa-solid fa-microphone text-sm" id="icon-mic-state"></i>
                            </button>
                        </div>
                        <div id="voice-cmd-response-box" class="p-3 rounded-xl bg-darkBase/70 border border-cyan-950 text-xs text-cyan-200 hidden flex items-start gap-2">
                            <i class="fa-solid fa-robot text-cyberCyan mt-0.5"></i>
                            <span id="voice-cmd-response-text" class="flex-1 leading-relaxed"></span>
                        </div>
                    </div>
                </div>

                <!-- Funding Vault -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col lg:col-span-2">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-binanceGold text-sm">
                                <i class="fa-solid fa-vault"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">KÉT THU PHÍ FUNDING DELTA-NEUTRAL</h3>
                                <p class="text-[10px] text-gray-400">Lãi Suất Chu Kỳ 8H & Triệt Tiêu Biến Động Giá</p>
                            </div>
                        </div>
                        <span class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-amber-950/60 text-binanceGold border border-amber-800/40">DELTA QUANT</span>
                    </div>
                    <div class="p-4 overflow-x-auto">
                        <table class="w-full text-left text-xs text-gray-300">
                            <thead class="text-[10px] uppercase text-gray-400 border-b border-darkBorder font-mono">
                                <tr>
                                    <th class="py-2 px-2.5">Cặp Coin</th>
                                    <th class="py-2 px-2.5">Tỷ Lệ Funding / 8H</th>
                                    <th class="py-2 px-2.5 text-right">Lợi Nhuận APY Dự Kiến</th>
                                </tr>
                            </thead>
                            <tbody id="funding-vault-body" class="divide-y divide-darkBorder font-mono text-xs">
                                <tr><td colspan="3" class="py-4 text-center text-gray-500 font-sans">Đang quét tỷ lệ Funding...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <!-- Digital Twin Risk Simulator & Cocoon Defense Shield Card (Bản 12.0) -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col lg:col-span-2">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center justify-center text-lossRed text-sm">
                                <i class="fa-solid fa-shield-virus"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">BẢN SAO SỐ DIGITAL TWIN & KÉN BỌC THÉP (COCOON SHIELD)</h3>
                                <p class="text-[10px] text-gray-400">Mô Phỏng 4 Kịch Bản Thảm Họa (FTX, Flash Crash 2024, Short Squeeze) 24/7</p>
                            </div>
                        </div>
                        <span id="cocoon-shield-tag" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700/50">AN TOÀN</span>
                    </div>
                    <div class="p-4 space-y-3">
                        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs font-mono">
                            <div class="p-2.5 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Sụt Giảm Mô Phỏng Max</span>
                                <span id="twin-worst-dd" class="font-extrabold text-profitGreen text-sm">1.8%</span>
                            </div>
                            <div class="p-2.5 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Khả Năng Chịu Đựng</span>
                                <span id="twin-health" class="font-bold text-white text-xs">VỮNG CHẮC (99.8%)</span>
                            </div>
                            <div class="p-2.5 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Vị Thế Được Stress-Test</span>
                                <span id="twin-positions" class="font-extrabold text-binanceGold text-sm">3 Lệnh</span>
                            </div>
                            <div class="p-2.5 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Chế Độ Kén Bọc Thép</span>
                                <span id="twin-cocoon-state" class="font-bold text-cyan-400 text-xs">SẴN SÀNG</span>
                            </div>
                        </div>
                        <div id="twin-scenarios-list" class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                            <div class="p-2.5 rounded-xl bg-darkBase/60 border border-darkBorder">Đang chạy giả lập kịch bản thảm họa...</div>
                        </div>
                    </div>
                </div>

                <!-- Sub-Account & Simple Earn Yield Harvester Card (Bản 11.0) -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-profitGreen text-sm">
                                <i class="fa-solid fa-piggy-bank"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">TỐI ƯU LỢI TỨC VỐN NHÀN RỖI (EARN HARVESTER)</h3>
                                <p class="text-[10px] text-gray-400">Tự Động Luân Chuyển USDT Rảnh Vào Binance Simple Earn</p>
                            </div>
                        </div>
                        <span id="earn-sweep-tag" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700/50">ĐANG SINH LỜI</span>
                    </div>
                    <div class="p-4 space-y-2.5 flex-1 flex flex-col justify-between">
                        <div class="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                            <div class="p-2 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">USDT Gửi Earn</span>
                                <span id="earn-allocated" class="font-extrabold text-white text-sm mt-0.5 block">$550.00</span>
                            </div>
                            <div class="p-2 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Lãi Suất APR</span>
                                <span id="earn-apr" class="font-extrabold text-binanceGold text-sm mt-0.5 block">10.5%</span>
                            </div>
                            <div class="p-2 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Lãi Thụ Động / Năm</span>
                                <span id="earn-annual" class="font-extrabold text-profitGreen text-sm mt-0.5 block">+$57.75</span>
                            </div>
                        </div>
                        <p class="text-[10px] text-gray-400 font-sans italic pt-1 border-t border-darkBorder">* 100% Instant Redeem: Vốn tự động rút về ví Futures trong 0.1s khi bot có tín hiệu vào lệnh mới.</p>
                    </div>
                </div>

                <!-- Genetic Strategy Evolver Card (Bản 12.0) -->
                <div class="glass-card rounded-2xl overflow-hidden border border-darkBorder shadow-xl flex flex-col">
                    <div class="px-4 py-3.5 border-b border-darkBorder bg-darkCard/60 flex items-center justify-between">
                        <div class="flex items-center space-x-2.5">
                            <div class="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 text-sm">
                                <i class="fa-solid fa-dna"></i>
                            </div>
                            <div>
                                <h3 class="font-bold text-white text-xs sm:text-sm">AI TIẾN HÓA ĐỘT BIẾN GEN (GENETIC F5)</h3>
                                <p class="text-[10px] text-gray-400">Chọn Lọc Tự Nhiên (Natural Selection) Chống Alpha Decay</p>
                            </div>
                        </div>
                        <span id="genetic-gen-tag" class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-purple-950 text-purple-300 border border-purple-700/50">APEX F5</span>
                    </div>
                    <div class="p-4 space-y-2.5 flex-1 flex flex-col justify-between">
                        <div class="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                            <div class="p-2 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Sharpe Tối Ưu</span>
                                <span id="genetic-sharpe" class="font-extrabold text-profitGreen text-sm mt-0.5 block">2.45</span>
                            </div>
                            <div class="p-2 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Winrate Kỳ Vọng</span>
                                <span id="genetic-wr" class="font-extrabold text-binanceGold text-sm mt-0.5 block">58.5%</span>
                            </div>
                            <div class="p-2 rounded-xl bg-darkBase/70 border border-darkBorder">
                                <span class="text-[10px] text-gray-400 block font-sans">Đột Biến RSI/ATR</span>
                                <span id="genetic-params" class="font-bold text-white text-xs mt-0.5 block">26/74 (1.8x)</span>
                            </div>
                        </div>
                        <p class="text-[10px] text-gray-400 font-sans italic pt-1 border-t border-darkBorder">* Tự động đào tạo 12 quần thể chiến lược ngầm mỗi tuần để liên tục thay thế các thuật toán suy giảm hiệu quả.</p>
                    </div>
                </div>
            </div>
        </div>

    </main>

    <!-- Mobile Fixed Bottom Navigation Bar (5 Tabs Tiếng Việt Chuẩn) -->
    <nav class="block md:hidden fixed bottom-0 left-0 right-0 z-40 bg-darkCard/95 backdrop-blur-xl border-t border-darkBorder px-2 py-1.5 shadow-2xl">
        <div class="grid grid-cols-5 gap-1 text-center">
            <button type="button" onclick="switchDashboardTab('overview')" id="mob-btn-overview" class="mobile-bottom-btn py-1.5 flex flex-col items-center justify-center text-binanceGold transition relative">
                <i class="fa-solid fa-bolt text-sm"></i>
                <span class="text-[9px] font-semibold mt-0.5 font-sans">Vị Thế</span>
                <span id="nav-badge-positions" class="hidden absolute top-0.5 right-4 w-2 h-2 rounded-full bg-profitGreen animate-ping"></span>
            </button>
            <button type="button" onclick="switchDashboardTab('radar')" id="mob-btn-radar" class="mobile-bottom-btn py-1.5 flex flex-col items-center justify-center text-gray-400 hover:text-cyberCyan transition">
                <i class="fa-solid fa-satellite-dish text-sm"></i>
                <span class="text-[9px] font-semibold mt-0.5 font-sans">Radar</span>
            </button>
            <button type="button" onclick="switchDashboardTab('smart_money')" id="mob-btn-smart_money" class="mobile-bottom-btn py-1.5 flex flex-col items-center justify-center text-gray-400 hover:text-binanceGold transition">
                <i class="fa-solid fa-shapes text-sm"></i>
                <span class="text-[9px] font-semibold mt-0.5 font-sans">Cá Mập</span>
            </button>
            <button type="button" onclick="switchDashboardTab('ai_arbitrage')" id="mob-btn-ai_arbitrage" class="mobile-bottom-btn py-1.5 flex flex-col items-center justify-center text-gray-400 hover:text-purple-400 transition">
                <i class="fa-solid fa-brain text-sm"></i>
                <span class="text-[9px] font-semibold mt-0.5 font-sans">AI & Trễ</span>
            </button>
            <button type="button" onclick="switchDashboardTab('portfolio')" id="mob-btn-portfolio" class="mobile-bottom-btn py-1.5 flex flex-col items-center justify-center text-gray-400 hover:text-profitGreen transition">
                <i class="fa-solid fa-chart-pie text-sm"></i>
                <span class="text-[9px] font-semibold mt-0.5 font-sans">Danh Mục</span>
            </button>
        </div>
    </nav>

    <!-- Floating Companion Mascot Widget (Bottom-Right Screen Dock) -->
    <div id="floating-mascot-widget" class="fixed bottom-20 md:bottom-8 right-4 md:right-8 z-[900] select-none transition-all duration-300 hidden">
        <!-- Mini Speech Popover -->
        <div id="floating-speech-bubble" class="hidden absolute bottom-20 right-0 w-64 p-3.5 rounded-2xl glass-panel border border-cyberCyan/50 text-xs text-white shadow-2xl space-y-2 pointer-events-auto">
            <div class="flex items-center justify-between pb-1.5 border-b border-darkBorder">
                <span class="font-extrabold text-[11px] text-cyberCyan flex items-center gap-1.5">
                    <span id="float-skin-icon">🦊</span> <span id="float-mascot-name">KITSUNE</span>
                </span>
                <button onclick="toggleFloatingSpeech(false)" class="text-gray-400 hover:text-white text-[11px]"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <p id="float-speech-text" class="text-[11px] leading-relaxed text-gray-200">"Sếp ơi, em đang canh thị trường và bảo vệ vốn đây!"</p>
            <div class="flex gap-2 pt-1">
                <button onclick="openAiModal()" class="flex-1 py-1.5 rounded-xl text-[10px] font-bold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black transition flex items-center justify-center gap-1 shadow-md shadow-cyan-950/50">
                    <i class="fa-solid fa-comments"></i> <span>Chat AI</span>
                </button>
                <button onclick="triggerMascotPoke(event)" class="py-1.5 px-3 rounded-xl text-[10px] font-semibold bg-darkBase hover:bg-cyan-950/40 text-binanceGold border border-darkBorder transition flex items-center gap-1">
                    <i class="fa-solid fa-hand-pointer"></i> <span>Chọc 👋</span>
                </button>
            </div>
        </div>

        <!-- Floating Circular Avatar Button -->
        <div class="relative group">
            <div onclick="toggleFloatingSpeech()" class="w-16 h-16 sm:w-18 sm:h-18 rounded-2xl bg-gradient-to-b from-[#1a233a] via-[#101728] to-[#0a0f1d] border-2 border-cyberCyan/70 flex items-center justify-center shadow-2xl shadow-cyan-950/80 cursor-pointer transition-transform duration-200 hover:scale-110 active:scale-95 glass-panel relative overflow-visible">
                <!-- Inner Avatar Clone -->
                <div id="floating-avatar-inner" class="w-12 h-12 flex items-center justify-center"></div>
                <!-- Status Ping -->
                <span class="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-profitGreen border-2 border-darkBase">
                    <span class="w-full h-full rounded-full bg-profitGreen animate-ping block opacity-75"></span>
                </span>
            </div>
            <!-- Dock Back Button -->
            <button onclick="toggleFloatingMode(false)" title="Đưa về thẻ tiêu đề" class="absolute -top-2 -left-2 w-5 h-5 rounded-full bg-gray-800 hover:bg-red-600 text-gray-300 hover:text-white border border-darkBorder flex items-center justify-center text-[9px] shadow-md transition">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
    </div>

    <!-- Footer -->
    <footer class="border-t border-darkBorder py-6 mt-6 md:mt-12 bg-darkCard/40 text-center text-xs text-gray-500">
        <p>Binance Futures Quantitative Trading Terminal • Được bảo vệ bởi Cloud VPS Watchdog & Multi-Timeframe Pullback Strategy</p>
    </footer>

    <!-- Client-Side Script Logic -->
    <script>
        // Tab Workspace Switcher (Hỗ trợ chuyển Tab mượt mà trên PC và Mobile)
        function switchDashboardTab(tabId) {{
            document.querySelectorAll('.dashboard-workspace-tab').forEach(function(el) {{
                el.classList.add('hidden');
            }});
            const target = document.getElementById('tab-' + tabId);
            if (target) {{
                target.classList.remove('hidden');
            }}

            document.querySelectorAll('.tab-btn').forEach(function(btn) {{
                btn.className = 'tab-btn px-3 sm:px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 text-gray-300 hover:text-white border border-transparent hover:bg-darkBase';
            }});
            const activeBtn = document.getElementById('tab-btn-' + tabId);
            if (activeBtn) {{
                activeBtn.className = 'tab-btn px-3 sm:px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 bg-binanceGold text-black border border-binanceGold shadow-lg shadow-yellow-900/30';
            }}

            document.querySelectorAll('.mobile-bottom-btn').forEach(function(btn) {{
                btn.classList.remove('text-binanceGold');
                btn.classList.add('text-gray-400');
            }});
            const mobBtn = document.getElementById('mob-btn-' + tabId);
            if (mobBtn) {{
                mobBtn.classList.remove('text-gray-400');
                mobBtn.classList.add('text-binanceGold');
            }}

            try {{ localStorage.setItem('active_dashboard_tab', tabId); }} catch(e) {{}}

            // Kích hoạt nạp dữ liệu tức thì cho từng Tab ngay khi chuyển (không bị treo text chờ)
            try {{
                if (tabId === 'overview') {{
                    if (equityChartInstance) {{
                        setTimeout(function() {{
                            try {{ equityChartInstance.resize(); }} catch(e) {{}}
                        }}, 150);
                    }}
                    fetchStatus();
                    fetchHistory();
                    fetchRadar();
                }} else if (tabId === 'radar') {{
                    fetchRadar();
                    fetchLiquidationRadar('BTCUSDT');
                    fetchOrderFlow('BTCUSDT');
                }} else if (tabId === 'smart_money') {{
                    fetchWhaleTracker();
                    fetchCrossBasis();
                    fetchSMC('BTCUSDT');
                }} else if (tabId === 'ai_arbitrage') {{
                    fetchPCABasket();
                    fetchAITraining();
                    fetchLeadLag();
                    fetchSynthesis();
                    fetchSmartGrid('BTCUSDT');
                    fetchPairsTrading();
                }} else if (tabId === 'portfolio') {{
                    fetchDigitalTwinStress();
                    fetchRebalancePlan();
                    fetchSubAccountYield();
                    fetchGeneticEvolution();
                }}
            }} catch(e) {{
                console.error('Lỗi nạp dữ liệu tab ' + tabId + ':', e);
            }}
        }}

        let equityChartInstance = null;
        let rawHistoryTrades = [];
        let currentFilterType = 'all';
        let historyCurrentPage = 1;
        let historyPageSize = 10;
        let isAudioEnabled = true;
        let audioCtx = null;
        let lastKnownPositionsCount = 0;
        let lastKnownRealizedPnl = 0;

        // Current Config State for Settings Modal
        let currentConfig = {{
            trading_mode: 'MARKET_ALL',
            active_strategy: 'AUTO_DYNAMIC',
            real_trading_hard_cap: 100.0,
            leverage: 5,
            risk_percent: 1.0,
            use_trailing_stop: true
        }};

        // Web Audio Synthesizer
        function getAudioContext() {{
            if (!audioCtx) {{
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }}
            if (audioCtx.state === 'suspended') {{
                audioCtx.resume();
            }}
            return audioCtx;
        }}

        function playChime(type = 'fill') {{
            if (!isAudioEnabled) return;
            try {{
                const ctx = getAudioContext();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);

                const now = ctx.currentTime;
                if (type === 'fill') {{
                    // Gentle high-tech ting
                    osc.frequency.setValueAtTime(587.33, now); // D5
                    osc.frequency.exponentialRampToValueAtTime(880.0, now + 0.15); // A5
                    gain.gain.setValueAtTime(0.12, now);
                    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
                    osc.start(now);
                    osc.stop(now + 0.35);
                }} else if (type === 'tp') {{
                    // Triumphant double chime
                    osc.frequency.setValueAtTime(523.25, now); // C5
                    osc.frequency.setValueAtTime(659.25, now + 0.1); // E5
                    osc.frequency.setValueAtTime(1046.50, now + 0.2); // C6
                    gain.gain.setValueAtTime(0.15, now);
                    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.5);
                    osc.start(now);
                    osc.stop(now + 0.5);
                }} else if (type === 'alert') {{
                    // Warning low beep
                    osc.frequency.setValueAtTime(330.0, now);
                    gain.gain.setValueAtTime(0.15, now);
                    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
                    osc.start(now);
                    osc.stop(now + 0.3);
                }}
            }} catch (e) {{
                console.debug("Audio error:", e);
            }}
        }}

        function toggleAudio() {{
            isAudioEnabled = !isAudioEnabled;
            const icon = document.getElementById('icon-audio');
            if (isAudioEnabled) {{
                icon.className = 'fa-solid fa-volume-high text-sm text-profitGreen';
                showToast("Đã BẬT âm thanh thông báo web 🔔", "success");
                playChime('fill');
            }} else {{
                icon.className = 'fa-solid fa-volume-xmark text-sm text-gray-500';
                showToast("Đã TẮT âm thanh thông báo web", "info");
            }}
        }}

        // =========================================================================
        // ADVANCED MASCOT INTERACTIVE ENGINE (Inspired & Elevated from page-mascot)
        // =========================================================================
        const mascotState = {{
            currentSkin: localStorage.getItem('bot_mascot_skin') || 'fox',
            isFloating: localStorage.getItem('bot_mascot_floating') === 'true',
            isVoiceEnabled: false,
            targetPupilX: 0,
            targetPupilY: 0,
            currentPupilX: 0,
            currentPupilY: 0,
            targetTiltX: 0,
            targetTiltY: 0,
            currentTiltX: 0,
            currentTiltY: 0,
            isPoked: false,
            currentMood: 'happy'
        }};

        const pokeQuotes = [
            "Á á, Sếp chọc em nhột quá! 😆 Em đang trực thâu đêm nè!",
            "Hệ thống trực chiến 24/7 sẵn sàng 100%! Sếp cần soi kèo nào không? 🚀",
            "Em đang canh chart từng giây nè Sếp, vốn được bảo vệ an toàn! ✨",
            "Bật mí nè: ADX trên 20 và Trend Pullback chuẩn là vào lệnh lụm lúa! 🎯",
            "Kỷ luật là số 1, gồng lãi là số 2! Sếp cứ an tâm ngủ ngon! 💎",
            "Meo meo... à nhầm, Kitsune Quant AI chào Sếp! 🦊",
            "Trailing Stop đang bám sát từng milimet nến để khóa chặt lãi! 🛡️"
        ];

        // Play cute 8-bit futuristic robotic audio chirp synthesizer
        function playRoboticChirp() {{
            if (!isAudioEnabled) return;
            try {{
                const ctx = getAudioContext();
                const now = ctx.currentTime;
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();

                osc.type = 'triangle';
                osc.frequency.setValueAtTime(560, now);
                osc.frequency.exponentialRampToValueAtTime(1240, now + 0.08);
                osc.frequency.exponentialRampToValueAtTime(880, now + 0.16);

                gain.gain.setValueAtTime(0.08, now);
                gain.gain.linearRampToValueAtTime(0.13, now + 0.04);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(now);
                osc.stop(now + 0.22);
            }} catch (e) {{}}
        }}

        // Pointer / Cursor Tracking with Dead-Zone Math (from page-mascot)
        function handlePointerMove(e) {{
            const box = document.getElementById('mascot-avatar-box');
            if (!box) return;

            const rect = box.getBoundingClientRect();
            const centerX = rect.left + rect.width / 2;
            const centerY = rect.top + rect.height / 2;

            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const clientY = e.touches ? e.touches[0].clientY : e.clientY;

            const dx = clientX - centerX;
            const dy = clientY - centerY;
            const dist = Math.sqrt(dx * dx + dy * dy);

            const deadZone = 28; // Radius where mascot looks forward calmly
            if (dist < deadZone) {{
                mascotState.targetPupilX = 0;
                mascotState.targetPupilY = 0;
                mascotState.targetTiltX = 0;
                mascotState.targetTiltY = 0;
                return;
            }}

            const angle = Math.atan2(dy, dx);
            const factor = Math.min(1, (dist - deadZone) / 320);
            const maxPupilOffset = 6.2; // Maximum eye pupil radius

            mascotState.targetPupilX = Math.cos(angle) * maxPupilOffset * factor;
            mascotState.targetPupilY = Math.sin(angle) * maxPupilOffset * factor;

            const maxTilt = 11; // Head 3D perspective angle
            mascotState.targetTiltX = -Math.sin(angle) * maxTilt * factor * 0.7;
            mascotState.targetTiltY = Math.cos(angle) * maxTilt * factor;
        }}

        // 60FPS RAF Spring Damping Animation Loop
        function animateMascotFrame() {{
            // Exponential smoothing (lerp factor 0.14)
            mascotState.currentPupilX += (mascotState.targetPupilX - mascotState.currentPupilX) * 0.14;
            mascotState.currentPupilY += (mascotState.targetPupilY - mascotState.currentPupilY) * 0.14;
            mascotState.currentTiltX += (mascotState.targetTiltX - mascotState.currentTiltX) * 0.12;
            mascotState.currentTiltY += (mascotState.targetTiltY - mascotState.currentTiltY) * 0.12;

            const pL = document.getElementById('pupil-left-group');
            const pR = document.getElementById('pupil-right-group');
            if (pL && pR) {{
                const transform = `translate(${{mascotState.currentPupilX.toFixed(2)}}px, ${{mascotState.currentPupilY.toFixed(2)}}px)`;
                pL.style.transform = transform;
                pR.style.transform = transform;
            }}

            const box = document.getElementById('mascot-avatar-box');
            if (box) {{
                box.style.transform = `perspective(500px) rotateX(${{mascotState.currentTiltX.toFixed(2)}}deg) rotateY(${{mascotState.currentTiltY.toFixed(2)}}deg)`;
            }}

            // Sync floating avatar pupils if visible
            const fPL = document.getElementById('float-pupil-left-group');
            const fPR = document.getElementById('float-pupil-right-group');
            if (fPL && fPR) {{
                const transform = `translate(${{mascotState.currentPupilX.toFixed(2)}}px, ${{mascotState.currentPupilY.toFixed(2)}}px)`;
                fPL.style.transform = transform;
                fPR.style.transform = transform;
            }}

            requestAnimationFrame(animateMascotFrame);
        }}

        // Natural Eyelid Blinking Scheduler (single & double blinks)
        function triggerBlink(doubleBlink = false) {{
            if (mascotState.isPoked) return;
            const eTL = document.getElementById('eyelid-top-left');
            const eTR = document.getElementById('eyelid-top-right');
            if (!eTL || !eTR) return;

            eTL.setAttribute('height', '22');
            eTR.setAttribute('height', '22');

            setTimeout(() => {{
                eTL.setAttribute('height', '0');
                eTR.setAttribute('height', '0');

                if (doubleBlink) {{
                    setTimeout(() => triggerBlink(false), 140);
                }}
            }}, 110);
        }}

        function scheduleNextBlink() {{
            const delay = 2600 + Math.random() * 3200;
            setTimeout(() => {{
                const isDouble = Math.random() < 0.25;
                triggerBlink(isDouble);
                scheduleNextBlink();
            }}, delay);
        }}

        // Poke Reaction Physics, Bounce & Dialogue
        function triggerMascotPoke(event) {{
            if (event) event.stopPropagation();
            playRoboticChirp();

            // Squash & stretch physics bounce
            const box = document.getElementById('mascot-avatar-box');
            if (box) {{
                box.classList.remove('mascot-squishing');
                void box.offsetWidth;
                box.classList.add('mascot-squishing');
            }}

            // Particle spark burst
            createParticleBurst(event);

            // Happy crescent eyes for 1.2s
            setReactionEyes('happy');
            mascotState.isPoked = true;
            setTimeout(() => {{
                mascotState.isPoked = false;
                resetMascotEyes();
            }}, 1200);

            // Random poke phrase
            const quote = pokeQuotes[Math.floor(Math.random() * pokeQuotes.length)];
            const speechElem = document.getElementById('robot-speech');
            if (speechElem) {{
                speechElem.style.opacity = '0';
                setTimeout(() => {{
                    speechElem.innerText = `"${{quote}}"`;
                    speechElem.style.opacity = '1';
                }}, 120);
            }}
            const floatSpeech = document.getElementById('float-speech-text');
            if (floatSpeech) floatSpeech.innerText = `"${{quote}}"`;

            if (mascotState.isVoiceEnabled) {{
                speakText(quote);
            }}
        }}

        // Particle Spark Burst Generator (Coins, Stars, Sparks)
        function createParticleBurst(e) {{
            const layer = document.getElementById('mascot-particle-layer');
            if (!layer) return;

            const icons = ['✨', '🚀', '💰', '⭐', '💎', '🔥', '🦊', '⚡'];
            for (let i = 0; i < 8; i++) {{
                const angle = (i / 8) * Math.PI * 2 + (Math.random() * 0.4 - 0.2);
                const dist = 38 + Math.random() * 32;
                const tx = Math.cos(angle) * dist;
                const ty = Math.sin(angle) * dist;

                const span = document.createElement('span');
                span.className = 'burst-particle select-none';
                span.innerText = icons[Math.floor(Math.random() * icons.length)];
                span.style.left = '50%';
                span.style.top = '50%';
                span.style.setProperty('--tx', `${{tx}}px`);
                span.style.setProperty('--ty', `${{ty}}px`);

                layer.appendChild(span);
                setTimeout(() => span.remove(), 750);
            }}
        }}

        // Reaction Eye States
        function setReactionEyes(type) {{
            const normal = document.getElementById('eyes-normal-layer');
            const happy = document.getElementById('eyes-happy-layer');
            const alertEyes = document.getElementById('eyes-alert-layer');
            const sleepy = document.getElementById('eyes-sleepy-layer');
            const heart = document.getElementById('eyes-heart-layer');

            [normal, happy, alertEyes, sleepy, heart].forEach(el => el && el.classList.add('hidden'));

            if (type === 'happy' && happy) happy.classList.remove('hidden');
            else if (type === 'alert' && alertEyes) alertEyes.classList.remove('hidden');
            else if (type === 'sleepy' && sleepy) sleepy.classList.remove('hidden');
            else if (type === 'heart' && heart) heart.classList.remove('hidden');
            else if (normal) normal.classList.remove('hidden');
        }}

        function resetMascotEyes() {{
            if (mascotState.currentMood === 'happy') {{
                setReactionEyes('normal');
            }} else if (mascotState.currentMood === 'alert') {{
                setReactionEyes('alert');
            }} else if (mascotState.currentMood === 'sleepy') {{
                setReactionEyes('sleepy');
            }} else {{
                setReactionEyes('normal');
            }}
        }}

        // Mascot Skin Switcher (Fox, Robot, Bull, Panda)
        function switchMascotSkin(skin) {{
            mascotState.currentSkin = skin;
            localStorage.setItem('bot_mascot_skin', skin);

            const skins = ['fox', 'robot', 'bull', 'panda'];
            skins.forEach(s => {{
                const grp = document.getElementById(`skin-${{s}}`);
                const btn = document.getElementById(`btn-skin-${{s}}`);
                if (grp) {{
                    if (s === skin) grp.classList.remove('hidden');
                    else grp.classList.add('hidden');
                }}
                if (btn) {{
                    if (s === skin) {{
                        btn.className = 'px-2 py-1 rounded-lg text-[11px] font-bold transition bg-cyan-950/80 text-cyberCyan border border-cyan-600/60 shadow-sm';
                    }} else {{
                        btn.className = 'px-2 py-1 rounded-lg text-[11px] font-bold transition text-gray-400 hover:text-white';
                    }}
                }}
            }});

            const titles = {{
                fox: '<i class="fa-solid fa-paw"></i> CYBER KITSUNE 9.0',
                robot: '<i class="fa-solid fa-microchip"></i> CYBER-NOVA 2.0 PRO',
                bull: '<i class="fa-solid fa-arrow-trend-up"></i> CYBER TAURUS PRIME',
                panda: '<i class="fa-solid fa-shield-heart"></i> ZEN PANDA ALPHA'
            }};
            const icons = {{ fox: '🦊', robot: '🤖', bull: '🐂', panda: '🐼' }};
            const titleElem = document.getElementById('mascot-skin-title');
            if (titleElem && titles[skin]) titleElem.innerHTML = titles[skin];

            const fIcon = document.getElementById('float-skin-icon');
            const fName = document.getElementById('float-mascot-name');
            if (fIcon) fIcon.innerText = icons[skin] || '🦊';
            if (fName) fName.innerText = skin.toUpperCase();

            syncFloatingAvatar();
            playChime('fill');
        }}

        // Floating Companion Widget Controls
        function toggleFloatingMode(forceState = null) {{
            const widget = document.getElementById('floating-mascot-widget');
            const btnToggle = document.getElementById('btn-float-toggle');
            if (!widget) return;

            if (forceState !== null) {{
                mascotState.isFloating = forceState;
            }} else {{
                mascotState.isFloating = !mascotState.isFloating;
            }}
            localStorage.setItem('bot_mascot_floating', mascotState.isFloating);

            if (mascotState.isFloating) {{
                widget.classList.remove('hidden');
                syncFloatingAvatar();
                showToast("Đã ghim linh vật Mascot nổi ở góc màn hình! 📌", "info");
                if (btnToggle) btnToggle.classList.add('text-binanceGold', 'border-binanceGold/60');
            }} else {{
                widget.classList.add('hidden');
                showToast("Đã thu gọn linh vật về thanh tiêu đề", "info");
                if (btnToggle) btnToggle.classList.remove('text-binanceGold', 'border-binanceGold/60');
            }}
        }}

        function toggleFloatingSpeech(forceState = null) {{
            const bubble = document.getElementById('floating-speech-bubble');
            if (!bubble) return;
            if (forceState !== null) {{
                if (forceState) bubble.classList.remove('hidden');
                else bubble.classList.add('hidden');
            }} else {{
                bubble.classList.toggle('hidden');
            }}
        }}

        function syncFloatingAvatar() {{
            const container = document.getElementById('floating-avatar-inner');
            const sourceSvg = document.getElementById('mascot-svg');
            if (!container || !sourceSvg) return;

            const clone = sourceSvg.cloneNode(true);
            clone.id = 'floating-svg-clone';
            clone.setAttribute('class', 'w-12 h-12 overflow-visible pointer-events-none');
            // Give floating pupils unique IDs
            const pL = clone.querySelector('#pupil-left-group');
            const pR = clone.querySelector('#pupil-right-group');
            if (pL) pL.id = 'float-pupil-left-group';
            if (pR) pR.id = 'float-pupil-right-group';

            container.innerHTML = '';
            container.appendChild(clone);
        }}

        // Text-To-Speech Synthesizer (Cute high-pitch voice)
        function toggleSpeechVoice() {{
            mascotState.isVoiceEnabled = !mascotState.isVoiceEnabled;
            const btn = document.getElementById('btn-voice-toggle');
            const icon = document.getElementById('icon-voice');
            if (mascotState.isVoiceEnabled) {{
                if (btn) btn.className = "w-full py-2 px-2 sm:px-3 rounded-xl text-xs font-semibold bg-purple-950/80 text-purple-200 border border-purple-500 transition flex items-center justify-center gap-1 active:scale-95";
                showToast("Đã BẬT giọng đọc lời thoại AI Mascot! 🔊", "success");
                const currentSpeech = document.getElementById('robot-speech')?.innerText.replace(/"/g, '') || "Chào Sếp!";
                speakText(currentSpeech);
            }} else {{
                if (btn) btn.className = "w-full py-2 px-2 sm:px-3 rounded-xl text-xs font-semibold bg-darkBase hover:bg-purple-950/40 text-purple-300 border border-purple-800/40 transition flex items-center justify-center gap-1 active:scale-95";
                showToast("Đã TẮT giọng đọc lời thoại", "info");
                if (window.speechSynthesis) window.speechSynthesis.cancel();
            }}
        }}

        function speakText(text) {{
            if (!text) return;
            try {{
                if (window._currentTtsAudio) {{
                    window._currentTtsAudio.pause();
                    window._currentTtsAudio = null;
                }}
                // Kiểm tra nếu trình duyệt có sẵn giọng Tiếng Việt bản địa
                if ('speechSynthesis' in window) {{
                    const voices = window.speechSynthesis.getVoices() || [];
                    const viVoice = voices.find(v => (v.lang && (v.lang.toLowerCase().includes('vi') || v.lang.includes('vn'))) || (v.name && v.name.toLowerCase().includes('vietnam')));
                    if (viVoice) {{
                        window.speechSynthesis.cancel();
                        const utterance = new SpeechSynthesisUtterance(text);
                        utterance.voice = viVoice;
                        utterance.lang = 'vi-VN';
                        utterance.rate = 1.05;
                        utterance.pitch = 1.25;
                        window.speechSynthesis.speak(utterance);
                        return;
                    }}
                }}
                // Tự động phát âm thanh Tiếng Việt chuẩn HD từ máy chủ (/api/tts)
                const clean = text.replace(/[*_~`#]/g, '').trim();
                const audioUrl = '/api/tts?text=' + encodeURIComponent(clean);
                window._currentTtsAudio = new Audio(audioUrl);
                window._currentTtsAudio.play().catch(function(e) {{ console.log('Audio playback:', e); }});
            }} catch (e) {{
                console.error("Lỗi phát âm thanh mascot:", e);
            }}
        }}

        // Backend Sync for Live Mascot Commentary & Emotion
        async function updateMascotCommentary(isManual = false) {{
            try {{
                const res = await fetch('/api/ai_mascot');
                const data = await res.json();

                const speechElem = document.getElementById('robot-speech');
                if (speechElem && data.speech) {{
                    speechElem.style.opacity = '0';
                    setTimeout(() => {{
                        speechElem.innerText = `"${{data.speech}}"`;
                        speechElem.style.opacity = '1';
                    }}, 140);
                }}

                const floatSpeech = document.getElementById('float-speech-text');
                if (floatSpeech && data.speech) {{
                    floatSpeech.innerText = `"${{data.speech}}"`;
                }}

                // Update Mood Badge
                const moodText = document.getElementById('robot-mood-text');
                const moodChip = document.getElementById('robot-mood-chip');
                if (moodText && data.mood_title) {{
                    moodText.innerText = data.mood_title;
                }}

                mascotState.currentMood = data.mood || 'happy';

                // Eye glow colors based on market mood
                const pL = document.getElementById('pupil-left-bg');
                const pR = document.getElementById('pupil-right-bg');
                const glowColor = data.glow_color || (data.mood === 'alert' ? '#F6465D' : '#0ECB81');

                if (pL) pL.setAttribute('fill', glowColor);
                if (pR) pR.setAttribute('fill', glowColor);

                const laserLayer = document.getElementById('laser-scan-layer');
                if (laserLayer) {{
                    if (data.mood === 'scanning') laserLayer.classList.remove('hidden');
                    else laserLayer.classList.add('hidden');
                }}

                if (data.mood === 'happy') {{
                    if (moodChip) moodChip.className = "px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-emerald-950/60 text-profitGreen border border-emerald-500/50 flex items-center gap-1";
                }} else if (data.mood === 'alert') {{
                    if (moodChip) moodChip.className = "px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-red-950/60 text-lossRed border border-red-500/50 flex items-center gap-1";
                    setReactionEyes('alert');
                }} else if (data.mood === 'paused') {{
                    if (moodChip) moodChip.className = "px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-yellow-950/60 text-binanceGold border border-yellow-500/50 flex items-center gap-1";
                    setReactionEyes('sleepy');
                }}

                // AI Neural Link tag
                const aiTag = document.getElementById('badge-ai-model-tag');
                if (aiTag) {{
                    aiTag.innerText = data.ai_connected ? 'GEMINI 2.5 FLASH ACTIVE' : 'QUANT NEURAL LINK';
                    aiTag.className = data.ai_connected 
                        ? 'text-[10px] px-2 py-0.5 rounded font-mono bg-green-950/60 text-profitGreen border border-green-600/50 hidden sm:inline'
                        : 'text-[10px] px-2 py-0.5 rounded font-mono bg-cyan-900/30 text-cyan-300 border border-cyan-700/40 hidden sm:inline';
                }}

                if (mascotState.isVoiceEnabled && data.speech && isManual) {{
                    speakText(data.speech);
                }}

                if (isManual) {{
                    showToast("Mascot vừa cập nhật bình luận thị trường!", "info");
                }}
            }} catch (err) {{
                console.error("Lỗi cập nhật mascot:", err);
            }}
        }}

        // Attach Global Mouse & Touch Tracking Listeners
        window.addEventListener('mousemove', handlePointerMove, {{ passive: true }});
        window.addEventListener('touchmove', handlePointerMove, {{ passive: true }});

        // Start 60fps Animation Loop & Blink Scheduler
        requestAnimationFrame(animateMascotFrame);
        scheduleNextBlink();

        // Initialize Skin & Floating mode from LocalStorage on load
        setTimeout(() => {{
            switchMascotSkin(mascotState.currentSkin);
            if (mascotState.isFloating) {{
                toggleFloatingMode(true);
            }}
        }}, 300);


        // AI Copilot Modal & Chat Handlers
        function openAiModal() {{
            document.getElementById('ai-chat-modal').classList.remove('hidden');
            document.getElementById('ai-chat-input').focus();
        }}

        function closeAiModal() {{
            document.getElementById('ai-chat-modal').classList.add('hidden');
        }}

        function sendQuickPrompt(promptText) {{
            document.getElementById('ai-chat-input').value = promptText;
            sendAiMessage();
        }}

        async function sendAiMessage() {{
            const input = document.getElementById('ai-chat-input');
            const userMsg = input.value.trim();
            if (!userMsg) return;

            const chatBody = document.getElementById('ai-chat-body');
            input.value = '';

            // User Message Bubble
            const userBubble = document.createElement('div');
            userBubble.className = "flex gap-2.5 items-start justify-end";
            userBubble.innerHTML = `
                <div class="p-3 rounded-2xl bg-cyan-950/60 border border-cyan-700/40 text-cyan-100 max-w-[85%] leading-relaxed shadow-sm">
                    ${{userMsg}}
                </div>
                <div class="w-7 h-7 rounded-lg bg-gray-800 border border-gray-600 flex items-center justify-center text-gray-300 text-xs flex-shrink-0 mt-0.5">
                    <i class="fa-solid fa-user"></i>
                </div>
            `;
            chatBody.appendChild(userBubble);
            chatBody.scrollTop = chatBody.scrollHeight;

            // Loading Robot Bubble
            const loadingBubble = document.createElement('div');
            loadingBubble.className = "flex gap-2.5 items-start";
            loadingBubble.innerHTML = `
                <div class="w-7 h-7 rounded-lg bg-cyan-950 border border-cyberCyan/50 flex items-center justify-center text-cyberCyan text-xs flex-shrink-0 mt-0.5">
                    <i class="fa-solid fa-robot fa-spin"></i>
                </div>
                <div class="p-3 rounded-2xl bg-darkCard border border-cyan-900/30 text-gray-400 max-w-[85%] leading-relaxed shadow-sm flex items-center gap-2">
                    <span class="inline-block w-2 h-2 rounded-full bg-cyberCyan animate-ping"></span>
                    <span>Cyber-Nova đang phân tích thị trường...</span>
                </div>
            `;
            chatBody.appendChild(loadingBubble);
            chatBody.scrollTop = chatBody.scrollHeight;

            try {{
                const res = await fetch('/api/ai_chat', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{message: userMsg}})
                }});
                const data = await res.json();
                loadingBubble.remove();

                let rawReply = data.reply || "Em chưa nhận được phản hồi.";
                let formattedReply = rawReply
                    .split(String.fromCharCode(10)).join('<br>')
                    .split('**').reduce((acc, cur, idx) => acc + (idx % 2 === 1 ? '<b>' + cur + '</b>' : cur), '');

                const botBubble = document.createElement('div');
                botBubble.className = "flex gap-2.5 items-start";
                botBubble.innerHTML = `
                    <div class="w-7 h-7 rounded-lg bg-cyan-950 border border-cyberCyan/50 flex items-center justify-center text-cyberCyan text-xs flex-shrink-0 mt-0.5">
                        <i class="fa-solid fa-robot"></i>
                    </div>
                    <div class="p-3.5 rounded-2xl bg-darkCard border border-cyan-900/40 text-gray-100 max-w-[85%] leading-relaxed shadow-md">
                        ${{formattedReply}}
                    </div>
                `;
                chatBody.appendChild(botBubble);
                chatBody.scrollTop = chatBody.scrollHeight;

                const badge = document.getElementById('ai-connected-badge');
                if (badge) {{
                    badge.innerText = data.ai_connected ? 'GEMINI 2.5 FLASH' : 'LOCAL QUANT BRAIN';
                    badge.className = data.ai_connected 
                        ? 'px-2 py-0.5 rounded text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700/50'
                        : 'px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyberCyan border border-cyan-700/50';
                }}
            }} catch (err) {{
                loadingBubble.remove();
                const errBubble = document.createElement('div');
                errBubble.className = "flex gap-2.5 items-start";
                errBubble.innerHTML = `
                    <div class="w-7 h-7 rounded-lg bg-red-950 border border-lossRed/50 flex items-center justify-center text-lossRed text-xs flex-shrink-0 mt-0.5">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                    </div>
                    <div class="p-3 rounded-2xl bg-darkCard border border-red-900/30 text-lossRed max-w-[85%] leading-relaxed">
                        Lỗi kết nối AI: ${{err}}
                    </div>
                `;
                chatBody.appendChild(errBubble);
                chatBody.scrollTop = chatBody.scrollHeight;
            }}
        }}

        // Toast System
        function showToast(message, type = 'info') {{
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            let bgClass = 'bg-gray-800 border-gray-700 text-white';
            let icon = '<i class="fa-solid fa-circle-info text-blue-400 mr-2"></i>';
            if (type === 'success') {{
                bgClass = 'bg-darkCard border-profitGreen/50 text-white glow-green';
                icon = '<i class="fa-solid fa-circle-check text-profitGreen mr-2"></i>';
            }} else if (type === 'error') {{
                bgClass = 'bg-darkCard border-lossRed/50 text-white glow-red';
                icon = '<i class="fa-solid fa-circle-xmark text-lossRed mr-2"></i>';
            }} else if (type === 'warning') {{
                bgClass = 'bg-darkCard border-binanceGold/50 text-white glow-gold';
                icon = '<i class="fa-solid fa-triangle-exclamation text-binanceGold mr-2"></i>';
            }}

            toast.className = `p-3 rounded-xl text-xs font-semibold border shadow-xl flex items-center transition-all duration-300 transform translate-y-2 opacity-0 pointer-events-auto ${{bgClass}}`;
            toast.innerHTML = `${{icon}}<span>${{message}}</span>`;
            container.appendChild(toast);

            setTimeout(() => toast.classList.remove('translate-y-2', 'opacity-0'), 10);
            setTimeout(() => {{
                toast.classList.add('opacity-0', '-translate-y-2');
                setTimeout(() => toast.remove(), 300);
            }}, 4000);
        }}

        // Chart.js Setup
        function initChart(chartData) {{
            const canvasEl = document.getElementById('equityChart');
            if (!canvasEl) return;
            const ctx = canvasEl.getContext('2d');
            if (equityChartInstance) equityChartInstance.destroy();

            const labels = chartData.map(d => `#${{d.trade_num}} (${{d.symbol || ''}})`);
            const dataPoints = chartData.map(d => d.cum_pnl);

            const gradient = ctx.createLinearGradient(0, 0, 0, 260);
            gradient.addColorStop(0, 'rgba(14, 203, 129, 0.35)');
            gradient.addColorStop(1, 'rgba(14, 203, 129, 0.0)');

            equityChartInstance = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels.length > 0 ? labels : ['Chưa có lệnh'],
                    datasets: [{{
                        label: 'PnL Tích Lũy ($)',
                        data: dataPoints.length > 0 ? dataPoints : [0],
                        borderColor: '#0ECB81',
                        borderWidth: 2.5,
                        fill: true,
                        backgroundColor: gradient,
                        tension: 0.3,
                        pointBackgroundColor: '#0ECB81',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 1.5,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            backgroundColor: '#10141e',
                            titleColor: '#fff',
                            bodyColor: '#0ECB81',
                            borderColor: '#1c2436',
                            borderWidth: 1,
                            padding: 10,
                            displayColors: false,
                            callbacks: {{
                                label: function(context) {{
                                    const sign = context.parsed.y >= 0 ? '+' : '';
                                    return ` Lợi nhuận tích lũy: ${{sign}}$${{context.parsed.y.toFixed(2)}} USDT`;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            grid: {{ color: 'rgba(255, 255, 255, 0.04)' }},
                            ticks: {{ color: '#6c757d', font: {{ family: 'JetBrains Mono', size: 10 }} }}
                        }},
                        y: {{
                            grid: {{ color: 'rgba(255, 255, 255, 0.04)' }},
                            ticks: {{
                                color: '#6c757d',
                                font: {{ family: 'JetBrains Mono', size: 10 }},
                                callback: function(value) {{ return '$' + value; }}
                            }}
                        }}
                    }}
                }}
            }});
        }}

        function safeSetText(id, text) {{
            const el = document.getElementById(id);
            if (el) el.innerText = text;
        }}
        function safeSetHTML(id, html) {{
            const el = document.getElementById(id);
            if (el) el.innerHTML = html;
        }}

        // Live Status Fetch
        async function fetchStatus(isManual = false) {{
            const refreshIcon = document.getElementById('btn-refresh-icon');
            if (isManual && refreshIcon) refreshIcon.classList.add('fa-spin');

            try {{
                const res = await fetch('/api/status');
                const data = await res.json();

                // Check for new position sound
                if (data.open_positions_count > lastKnownPositionsCount) {{
                    playChime('fill');
                    showToast(`Đã khớp thêm vị thế mới! (${{data.open_positions_count}}/${{data.max_positions}})`, "success");
                    speakMascotVoice("Khớp thêm vị thế mới trên thị trường!");
                }}
                lastKnownPositionsCount = data.open_positions_count;

                // Sync current settings
                currentConfig.trading_mode = data.trading_mode || 'MARKET_ALL';
                currentConfig.active_strategy = data.active_strategy || 'AUTO_DYNAMIC';
                currentConfig.real_trading_hard_cap = data.real_trading_hard_cap || 100.0;
                currentConfig.leverage = data.leverage || 5;
                currentConfig.risk_percent = data.risk_percent || 1.0;
                currentConfig.use_trailing_stop = data.use_trailing_stop !== false;

                // Update Badges & Clock
                safeSetText('clock', data.last_updated || '');
                safeSetText('trading-mode-text', data.trading_mode === 'BLUECHIP_ONLY' ? 'CHỈ BTC/ETH' : 'ALL MARKET');
                safeSetText('strategy-label', data.active_strategy || 'AUTO_DYNAMIC');

                if (data.fear_and_greed) {{
                    window._lastFng = data.fear_and_greed;
                    safeSetText('fng-value', data.fear_and_greed.value !== undefined ? data.fear_and_greed.value : 50);
                    safeSetText('fng-label', data.fear_and_greed.classification_vi || 'Trung lập');
                    const fngValElem = document.getElementById('fng-value');
                    if (fngValElem && data.fear_and_greed.color) {{
                        fngValElem.style.color = data.fear_and_greed.color;
                    }}
                }}
                
                const statusBadge = document.getElementById('badge-status');
                const btnPauseText = document.getElementById('btn-pause-text');
                const btnPauseIcon = document.getElementById('btn-pause-icon');

                // Robot Eye Color & Pulse
                const eyeL = document.getElementById('robot-eye-left');
                const eyeR = document.getElementById('robot-eye-right');

                if (data.is_paused === true) {{
                    if (statusBadge) {{
                        statusBadge.className = "px-2.5 py-1 rounded-full text-xs font-bold bg-yellow-900/30 text-binanceGold border border-yellow-700/50 flex items-center gap-1.5";
                        statusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-binanceGold"></span> TẠM DỪNG';
                    }}
                    if (btnPauseText) btnPauseText.innerText = "Tiếp Tục Quét";
                    if (btnPauseIcon) btnPauseIcon.className = "fa-solid fa-play";
                }} else if (data.is_paused === false) {{
                    if (statusBadge) statusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-profitGreen animate-pulse"></span> EXECUTION SERVICE HEALTHY';
                    if (btnPauseText) btnPauseText.innerText = "Tạm Dừng Bot";
                    if (btnPauseIcon) btnPauseIcon.className = "fa-solid fa-pause";
                }} else {{
                    if (statusBadge) statusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-gray-400"></span> UNKNOWN';
                    if (btnPauseText) btnPauseText.innerText = "Trạng thái không xác định";
                    if (btnPauseIcon) btnPauseIcon.className = "fa-solid fa-triangle-exclamation";
                }}
                if (eyeL) eyeL.setAttribute('fill', '#6b7280');
                if (eyeR) eyeR.setAttribute('fill', '#6b7280');

                // Authoritative account balance/unrealized PnL are UNKNOWN until service exposes typed queries.
                safeSetHTML('metric-balance', data.balance === null ? 'UNKNOWN <span class="text-xs font-normal text-gray-400">(service)</span>' : `$${{data.balance.toLocaleString('en-US', {{minimumFractionDigits: 2}})}}`);
                const roiElem = document.getElementById('metric-roi');
                if (roiElem) roiElem.innerText = data.roi_percent === null ? 'UNKNOWN' : `${{data.roi_percent.toFixed(2)}}%`;
                safeSetText('metric-leverage', `${{data.leverage}}x (${{data.margin_type}})`);
                const uPnlElem = document.getElementById('metric-unrealized-pnl');
                if (uPnlElem) {{
                    uPnlElem.innerText = data.total_unrealized_pnl === null ? 'UNKNOWN' : `$${{data.total_unrealized_pnl.toFixed(2)}}`;
                    uPnlElem.className = 'text-2xl lg:text-3xl font-extrabold font-mono text-gray-400';
                }}
                const knownPositionCount = data.open_positions_count === null ? 0 : data.open_positions_count;
                safeSetText('metric-open-count', data.open_positions_count === null ? 'UNKNOWN' : `${{knownPositionCount}} / ${{data.max_positions}} vị thế`);
                safeSetText('badge-open-slots', data.open_positions_count === null ? 'UNKNOWN' : `${{knownPositionCount}} / ${{data.max_positions}} vị thế`);
                safeSetText('tab-badge-positions', data.open_positions_count === null ? '?' : `${{knownPositionCount}}`);
                const slotBar = document.getElementById('metric-slot-bar');
                if (slotBar) {{
                    const slotPercent = (data.open_positions_count / data.max_positions) * 100.0;
                    slotBar.style.width = `${{slotPercent}}%`;
                }}

                const openFloatBadge = document.getElementById('metric-open-floating-badge');
                if (openFloatBadge) {{
                    const uCol = (data.total_unrealized_pnl || 0) >= 0 ? 'text-profitGreen' : 'text-lossRed';
                    openFloatBadge.className = 'font-mono font-semibold text-[11px] ' + uCol;
                    openFloatBadge.innerText = `${{data.open_positions_count || 0}} vị thế (${{uSign}}$${{Math.abs(data.total_unrealized_pnl || 0).toFixed(2)}})`;
                }}

                // Watchdog
                if (data.health && Object.keys(data.health).length > 0) {{
                    const h = data.health;
                    safeSetText('metric-uptime', h.uptime || '--');
                    safeSetText('metric-cpu', `${{h.cpu_percent}}%`);
                    safeSetText('metric-ram', `${{h.ram_percent}}%`);
                    safeSetText('metric-disk', `Trống ${{h.disk_free_gb}} GB`);
                    const ramBar = document.getElementById('ram-progress-bar');
                    if (ramBar) ramBar.style.width = `${{h.ram_percent}}%`;
                    if (h.binance_latency_ms) {{
                        safeSetText('ping-latency', `${{h.binance_latency_ms}} ms`);
                    }}
                }}

                // Render Table & Mobile Cards
                renderPositionsTable(data.positions);

                if (isManual) showToast("Đã cập nhật dữ liệu mới nhất!", "success");

            }} catch (err) {{
                console.error("Lỗi cập nhật status:", err);
            }} finally {{
                if (refreshIcon) refreshIcon.classList.remove('fa-spin');
            }}
        }}

        function renderPositionsTable(positions) {{
            const tbody = document.getElementById('positions-table-body');
            const mobileContainer = document.getElementById('positions-mobile-container');
            const navBadge = document.getElementById('nav-badge-positions');
            const normalizePosition = (position, fallbackSymbol = '') => {{
                const raw = position && typeof position === 'object' ? position : {{}};
                const finite = (value, fallback = 0) => {{
                    const parsed = Number(value);
                    return Number.isFinite(parsed) ? parsed : fallback;
                }};
                const entry = finite(raw.entry_price);
                return {{
                    ...raw,
                    symbol: raw.symbol || fallbackSymbol,
                    entry_price: entry,
                    current_price: finite(raw.current_price, entry),
                    stop_loss: finite(raw.stop_loss),
                    take_profit: finite(raw.take_profit),
                    margin: finite(raw.margin),
                    pnl_usdt: finite(raw.pnl_usdt),
                    pnl_percent: finite(raw.pnl_percent),
                    slider_pct: finite(raw.slider_pct, 50),
                }};
            }};
            const positionList = Array.isArray(positions)
                ? positions.map(position => normalizePosition(position))
                : (positions && typeof positions === 'object'
                    ? Object.entries(positions).map(([symbol, position]) => normalizePosition(position, symbol))
                    : []);

            if (navBadge) {{
                if (positionList.length > 0) {{
                    navBadge.classList.remove('hidden');
                }} else {{
                    navBadge.classList.add('hidden');
                }}
            }}
            safeSetText('tab-badge-positions', positionList.length);

            if (positionList.length === 0) {{
                if (tbody) {{
                    tbody.innerHTML = '<tr><td colspan="11" class="px-6 py-10 text-center text-gray-400 font-sans"><i class="fa-solid fa-magnifying-glass text-binanceGold mr-2"></i> Không có vị thế nào đang mở. Bot đang liên tục quét cơ hội...</td></tr>';
                }}
                if (mobileContainer) {{
                    mobileContainer.innerHTML = `
                        <div class="p-6 rounded-xl bg-darkBase/60 border border-darkBorder text-center space-y-2">
                            <div class="w-10 h-10 rounded-full bg-cyan-950/50 border border-cyan-800/40 text-cyberCyan flex items-center justify-center mx-auto text-base">
                                <i class="fa-solid fa-radar animate-pulse"></i>
                            </div>
                            <div class="text-xs font-bold text-white">Chưa có vị thế nào đang mở</div>
                            <p class="text-[11px] text-gray-400">Bot đang quét 50 cặp coin để tìm tín hiệu Pullback tối ưu nhất...</p>
                        </div>
                    `;
                }}
                return;
            }}

            // Render Desktop Table Rows
            if (tbody) {{
                tbody.innerHTML = positionList.map(p => {{
                    const isLong = p.side === 'BUY';
                    const sideBadge = isLong 
                        ? '<span class="px-2.5 py-1 rounded text-xs font-bold bg-green-950/60 text-profitGreen border border-green-700/50">LONG</span>' 
                        : '<span class="px-2.5 py-1 rounded text-xs font-bold bg-red-950/60 text-lossRed border border-red-700/50">SHORT</span>';
                    
                    const pnlClass = p.pnl_usdt >= 0 ? 'text-profitGreen font-bold' : 'text-lossRed font-bold';
                    const sign = p.pnl_usdt >= 0 ? '+' : '';

                    let statusBadge = '<span class="px-2 py-0.5 rounded text-[11px] bg-darkBase text-gray-400 border border-darkBorder">Đang chạy</span>';
                    if (p.trailing_active) {{
                        statusBadge = '<span class="px-2 py-0.5 rounded text-[11px] bg-purple-900/40 text-purple-400 border border-purple-700/40 animate-pulse">🚀 Trailing Stop</span>';
                    }} else if (p.partial_tp) {{
                        statusBadge = '<span class="px-2 py-0.5 rounded text-[11px] bg-green-900/40 text-profitGreen border border-green-700/40">🎯 Chốt 50%</span>';
                    }} else if (p.breakeven) {{
                        statusBadge = '<span class="px-2 py-0.5 rounded text-[11px] bg-yellow-900/40 text-binanceGold border border-yellow-700/40">🛡️ SL Hòa Vốn</span>';
                    }}

                    const sliderVal = p.slider_pct || 50;
                    const sliderColor = p.pnl_usdt >= 0 ? 'bg-profitGreen' : 'bg-lossRed';

                    return `
                        <tr class="hover:bg-darkBase/40 transition">
                            <td class="px-5 py-4 font-bold text-white font-sans">${{p.symbol}}</td>
                            <td class="px-5 py-4 font-sans">${{sideBadge}}</td>
                            <td class="px-5 py-4">$${{p.entry_price.toLocaleString('en-US', {{minimumFractionDigits: 2}})}}</td>
                            <td class="px-5 py-4 font-bold text-white">$${{p.current_price.toLocaleString('en-US', {{minimumFractionDigits: 2}})}}</td>
                            <td class="px-5 py-4 text-lossRed font-semibold">$${{p.stop_loss.toLocaleString('en-US', {{minimumFractionDigits: 2}})}}</td>
                            <td class="px-5 py-4 text-profitGreen font-semibold">$${{p.take_profit.toLocaleString('en-US', {{minimumFractionDigits: 2}})}}</td>
                            <td class="px-5 py-4 w-36">
                                <div class="w-full bg-darkBase h-2 rounded-full overflow-hidden border border-darkBorder relative">
                                    <div class="${{sliderColor}} h-full transition-all duration-300" style="width: ${{sliderVal}}%"></div>
                                </div>
                                <div class="flex justify-between text-[9px] text-gray-500 mt-1">
                                    <span>SL</span>
                                    <span class="text-gray-300 font-semibold">${{sliderVal}}%</span>
                                    <span>TP</span>
                                </div>
                            </td>
                            <td class="px-5 py-4">$${{p.margin.toFixed(2)}}</td>
                            <td class="px-5 py-4 ${{pnlClass}}">${{sign}}$${{p.pnl_usdt.toFixed(2)}} (${{sign}}${{p.pnl_percent.toFixed(2)}}%)</td>
                            <td class="px-5 py-4 text-center font-sans">${{statusBadge}}</td>
                            <td class="px-5 py-4 text-center font-sans">
                                <div class="flex items-center justify-center gap-1.5">
                                    <button onclick="openChartModal('${{p.symbol}}')" title="Xem Biểu đồ nến" class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-cyan-950 hover:bg-cyan-900 border border-cyan-700/60 text-cyberCyan transition">
                                        <i class="fa-solid fa-chart-line"></i> Chart
                                    </button>
                                    <button onclick="closeSinglePosition('${{p.symbol}}')" class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-gray-800 hover:bg-lossRed text-gray-300 hover:text-white transition">
                                        Đóng
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;
                }}).join('');
            }}

            // Render Mobile Cards View
            if (mobileContainer) {{
                mobileContainer.innerHTML = positionList.map(p => {{
                    const isLong = p.side === 'BUY';
                    const sideBadge = isLong 
                        ? '<span class="px-2 py-0.5 rounded text-[10px] font-extrabold bg-green-950/80 text-profitGreen border border-green-600/60 flex items-center gap-1"><i class="fa-solid fa-arrow-trend-up"></i> LONG</span>' 
                        : '<span class="px-2 py-0.5 rounded text-[10px] font-extrabold bg-red-950/80 text-lossRed border border-red-600/60 flex items-center gap-1"><i class="fa-solid fa-arrow-trend-down"></i> SHORT</span>';

                    const pnlClass = p.pnl_usdt >= 0 ? 'text-profitGreen' : 'text-lossRed';
                    const sign = p.pnl_usdt >= 0 ? '+' : '';

                    let statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] bg-darkBase text-gray-400 border border-darkBorder">Đang chạy</span>';
                    if (p.trailing_active) {{
                        statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-950/80 text-purple-300 border border-purple-600/50 animate-pulse">🚀 Trailing Stop</span>';
                    }} else if (p.partial_tp) {{
                        statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-green-950/80 text-profitGreen border border-green-600/50">🎯 Chốt 50%</span>';
                    }} else if (p.breakeven) {{
                        statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-yellow-950/80 text-binanceGold border border-yellow-600/50">🛡️ SL Hòa Vốn</span>';
                    }}

                    const sliderVal = Math.min(100, Math.max(0, p.slider_pct || 50));
                    const sliderColor = p.pnl_usdt >= 0 ? 'bg-profitGreen' : 'bg-lossRed';

                    return `
                        <div class="glass-card rounded-xl p-3.5 border border-darkBorder hover:border-cyan-800/40 transition space-y-3">
                            <div class="flex items-center justify-between pb-2.5 border-b border-darkBorder/60">
                                <div class="flex items-center gap-1.5 flex-wrap">
                                    <span class="font-extrabold text-white text-sm tracking-wide font-sans">${{p.symbol}}</span>
                                    ${{sideBadge}}
                                    ${{statusBadge}}
                                </div>
                                <div class="text-right">
                                    <div class="text-sm font-extrabold font-mono ${{pnlClass}}">${{sign}}$${{p.pnl_usdt.toFixed(2)}}</div>
                                    <div class="text-[10px] font-mono ${{pnlClass}}">${{sign}}$${{p.pnl_percent.toFixed(2)}}%</div>
                                </div>
                            </div>

                            <div class="grid grid-cols-2 gap-2 text-[11px] font-mono bg-darkBase/60 p-2.5 rounded-lg border border-darkBorder/40">
                                <div>
                                    <span class="text-gray-400 font-sans block text-[10px]">Giá vào (Entry):</span>
                                    <span class="font-bold text-gray-200">$${{p.entry_price.toLocaleString('en-US', {{minimumFractionDigits: 2}})}}</span>
                                </div>
                                <div>
                                    <span class="text-gray-400 font-sans block text-[10px]">Giá hiện tại:</span>
                                    <span class="font-bold text-white">$${{p.current_price.toLocaleString('en-US', {{minimumFractionDigits: 2}})}}</span>
                                </div>
                                <div>
                                    <span class="text-gray-400 font-sans block text-[10px]">Stop Loss:</span>
                                    <span class="font-bold text-lossRed">$${{p.stop_loss.toLocaleString('en-US', {{minimumFractionDigits: 2}})}}</span>
                                </div>
                                <div>
                                    <span class="text-gray-400 font-sans block text-[10px]">Take Profit:</span>
                                    <span class="font-bold text-profitGreen">$${{p.take_profit.toLocaleString('en-US', {{minimumFractionDigits: 2}})}}</span>
                                </div>
                            </div>

                            <div>
                                <div class="flex justify-between text-[9px] text-gray-400 font-mono mb-1">
                                    <span>SL</span>
                                    <span class="text-gray-300 font-semibold font-sans">Tiến trình: ${{sliderVal}}%</span>
                                    <span>TP</span>
                                </div>
                                <div class="w-full bg-darkBase h-2 rounded-full overflow-hidden border border-darkBorder/60">
                                    <div class="${{sliderColor}} h-full transition-all duration-300" style="width: ${{sliderVal}}%"></div>
                                </div>
                            </div>

                            <div class="flex items-center justify-between pt-1 gap-2">
                                <div class="text-[11px] font-mono text-gray-400">
                                    <span>Ký quỹ: </span><span class="text-white font-bold">$${{p.margin.toFixed(2)}}</span>
                                </div>
                                <div class="flex items-center gap-1.5">
                                    <button onclick="openChartModal('${{p.symbol}}')" class="px-2.5 py-1.5 rounded-lg text-xs font-bold bg-cyan-500/15 hover:bg-cyan-900 border border-cyan-500/30 text-cyberCyan transition active:scale-95 flex items-center gap-1">
                                        <i class="fa-solid fa-chart-line"></i> <span>Chart</span>
                                    </button>
                                    <button onclick="closeSinglePosition('${{p.symbol}}')" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-500/15 hover:bg-lossRed border border-red-500/30 text-lossRed hover:text-white transition active:scale-95 flex items-center gap-1">
                                        <i class="fa-solid fa-xmark"></i> <span>Đóng</span>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                }}).join('');
            }}
        }}

        // Live Scanner Radar Fetch
        async function fetchRadar() {{
            try {{
                const res = await fetch('/api/scanner_radar');
                const data = await res.json();

                const tbody = document.getElementById('radar-table-body');
                const mobileContainer = document.getElementById('radar-mobile-container');
                safeSetText('radar-updated-at', data.updated_at || '');
                safeSetText('radar-count-badge', `${{data.scanned_count}} CẶP COIN`);

                if (!data.radar || data.radar.length === 0) {{
                    if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="px-6 py-6 text-center text-gray-400 font-sans">Đang chờ chu kỳ quét kế tiếp...</td></tr>';
                    if (mobileContainer) mobileContainer.innerHTML = '<div class="p-6 rounded-xl bg-darkBase/60 border border-darkBorder text-center text-xs text-gray-400">Đang chờ chu kỳ quét kế tiếp...</div>';
                    return;
                }}

                if (tbody) {{
                    tbody.innerHTML = data.radar.map(r => {{
                        const trendColor = r.trend.includes('Up') ? 'text-profitGreen' : (r.trend.includes('Down') ? 'text-lossRed' : 'text-gray-400');
                        const adxColor = r.adx >= 20 ? 'text-profitGreen font-bold' : 'text-lossRed';
                        const rsiColor = r.rsi <= 35 ? 'text-profitGreen font-bold' : (r.rsi >= 65 ? 'text-lossRed font-bold' : 'text-gray-300');

                        let statusBadge = '<span class="text-gray-400">Đang chờ Pullback</span>';
                        if (r.status.includes('Tín hiệu')) {{
                            statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700 animate-pulse">' + r.status + '</span>';
                        }} else if (r.status.includes('ADX yếu')) {{
                            statusBadge = '<span class="text-yellow-600 italic">' + r.status + '</span>';
                        }}

                        return `
                            <tr class="hover:bg-darkBase/40 transition">
                                <td class="px-5 py-2.5 font-bold text-white font-sans cursor-pointer hover:text-cyberCyan" onclick="openChartModal('${{r.symbol}}')">
                                    <div class="flex items-center gap-1.5">
                                        <span>${{r.symbol}}</span>
                                        <i class="fa-solid fa-chart-simple text-[10px] text-gray-500"></i>
                                    </div>
                                </td>
                                <td class="px-5 py-2.5 font-mono">$${{r.price.toFixed(4)}}</td>
                                <td class="px-5 py-2.5 font-semibold ${{trendColor}}">${{r.trend}}</td>
                                <td class="px-5 py-2.5 ${{rsiColor}}">${{r.rsi}}</td>
                                <td class="px-5 py-2.5 ${{adxColor}}">${{r.adx}}</td>
                                <td class="px-5 py-2.5 text-gray-400 font-mono">${{r.funding_rate}}%</td>
                                <td class="px-5 py-2.5 font-sans">${{statusBadge}}</td>
                                <td class="px-5 py-2.5 text-center font-sans">
                                    <div class="flex items-center justify-center gap-1">
                                        <button onclick="openChartModal('${{r.symbol}}')" title="Xem Biểu đồ nến" class="px-2 py-1 rounded bg-darkBase hover:bg-gray-800 border border-darkBorder text-cyberCyan hover:border-cyan-500 text-xs">
                                            <i class="fa-solid fa-chart-line"></i>
                                        </button>
                                        <button onclick="executeManualOrder('${{r.symbol}}', 'BUY')" title="Mở Long 1-Click" class="px-2 py-1 rounded bg-green-950/70 hover:bg-profitGreen border border-green-700/60 text-profitGreen hover:text-black font-bold text-[11px] transition">
                                            ⚡ Long
                                        </button>
                                        <button onclick="executeManualOrder('${{r.symbol}}', 'SELL')" title="Mở Short 1-Click" class="px-2 py-1 rounded bg-red-950/70 hover:bg-lossRed border border-red-700/60 text-lossRed hover:text-white font-bold text-[11px] transition">
                                            ⚡ Short
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        `;
                    }}).join('');
                }}

                if (mobileContainer) {{
                    mobileContainer.innerHTML = data.radar.map(r => {{
                        const trendColor = r.trend.includes('Up') ? 'text-profitGreen' : (r.trend.includes('Down') ? 'text-lossRed' : 'text-gray-400');
                        const adxColor = r.adx >= 20 ? 'text-profitGreen font-bold' : 'text-lossRed';
                        const rsiColor = r.rsi <= 35 ? 'text-profitGreen font-bold' : (r.rsi >= 65 ? 'text-lossRed font-bold' : 'text-gray-300');

                        let statusBadge = '<span class="text-gray-400">Đang chờ Pullback</span>';
                        if (r.status.includes('Tín hiệu')) {{
                            statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700 animate-pulse">' + r.status + '</span>';
                        }} else if (r.status.includes('ADX yếu')) {{
                            statusBadge = '<span class="text-yellow-600 italic text-[10px]">' + r.status + '</span>';
                        }}

                        return `
                            <div class="glass-card rounded-xl p-3 border border-darkBorder hover:border-cyan-800/40 transition space-y-2">
                                <div class="flex items-center justify-between pb-1.5 border-b border-darkBorder/60">
                                    <div class="flex items-center gap-2 cursor-pointer" onclick="openChartModal('${{r.symbol}}')">
                                        <span class="font-extrabold text-white text-sm font-sans hover:text-cyberCyan">${{r.symbol}}</span>
                                        <span class="text-xs font-semibold ${{trendColor}}">${{r.trend}}</span>
                                    </div>
                                    <span class="text-xs font-mono font-bold text-white">$${{r.price.toFixed(4)}}</span>
                                </div>
                                <div class="grid grid-cols-3 gap-2 text-[11px] font-mono bg-darkBase/60 p-2 rounded-lg text-center">
                                    <div>
                                        <span class="text-gray-400 block text-[9px] font-sans">RSI (15m)</span>
                                        <span class="${{rsiColor}}">${{r.rsi}}</span>
                                    </div>
                                    <div>
                                        <span class="text-gray-400 block text-[9px] font-sans">ADX (1H)</span>
                                        <span class="${{adxColor}}">${{r.adx}}</span>
                                    </div>
                                    <div>
                                        <span class="text-gray-400 block text-[9px] font-sans">Funding</span>
                                        <span class="text-gray-300">${{r.funding_rate}}%</span>
                                    </div>
                                </div>
                                <div class="flex items-center justify-between text-[11px] pt-0.5">
                                    <span class="text-gray-400 font-sans text-[10px]">Trạng thái:</span>
                                    <div>${{statusBadge}}</div>
                                </div>
                                <div class="grid grid-cols-3 gap-1.5 pt-1 border-t border-darkBorder/40 text-center">
                                    <button onclick="openChartModal('${{r.symbol}}')" class="py-1.5 rounded-lg bg-darkBase hover:bg-gray-800 border border-darkBorder text-cyberCyan text-xs font-semibold flex items-center justify-center gap-1">
                                        <i class="fa-solid fa-chart-line text-[10px]"></i> <span>Biểu đồ</span>
                                    </button>
                                    <button onclick="executeManualOrder('${{r.symbol}}', 'BUY')" class="py-1.5 rounded-lg bg-green-950/70 hover:bg-profitGreen border border-green-700/60 text-profitGreen hover:text-black font-bold text-xs flex items-center justify-center gap-1">
                                        <span>⚡ Long</span>
                                    </button>
                                    <button onclick="executeManualOrder('${{r.symbol}}', 'SELL')" class="py-1.5 rounded-lg bg-red-950/70 hover:bg-lossRed border border-red-700/60 text-lossRed hover:text-white font-bold text-xs flex items-center justify-center gap-1">
                                        <span>⚡ Short</span>
                                    </button>
                                </div>
                            </div>
                        `;
                    }}).join('');
                }}
            }} catch (err) {{
                console.error("Lỗi nạp radar:", err);
            }}
        }}

        // Fetch History
        async function fetchHistory() {{
            try {{
                const res = await fetch('/api/history');
                const data = await res.json();

                if (data.summary) {{
                    const s = data.summary;
                    safeSetText('metric-total-closed', s.total);
                    safeSetText('metric-wins', s.wins);
                    safeSetText('metric-losses', s.losses);
                    document.getElementById('metric-winrate').innerText = `${{s.win_rate}}%`;

                    const rPnl = document.getElementById('metric-realized-pnl');
                    const sign = s.net_pnl >= 0 ? '+' : '';
                    rPnl.innerText = `${{sign}}$${{s.net_pnl.toFixed(2)}}`;
                    rPnl.className = `text-2xl lg:text-3xl font-extrabold font-mono ${{s.net_pnl >= 0 ? 'text-profitGreen' : 'text-lossRed'}}`;

                    // Check if new profit trade closed -> Play celebration sound
                    if (s.net_pnl > lastKnownRealizedPnl && lastKnownRealizedPnl !== 0) {{
                        playChime('tp');
                        showToast(`Chúc mừng! Vừa chốt lời thành công! Lãi ròng hiện tại: $${{s.net_pnl.toFixed(2)}}`, "success");
                        speakMascotVoice(`Chúc mừng Sếp! Lệnh vừa chốt lời thành công, lãi ròng hiện tại là ${{s.net_pnl.toFixed(2)}} đô la!`);
                    }}
                    lastKnownRealizedPnl = s.net_pnl;
                }}

                if (data.chart_data && data.chart_data.length > 0) {{
                    initChart(data.chart_data);
                }}

                rawHistoryTrades = data.trades || [];
                applyHistoryFilter();

            }} catch (err) {{
                console.error("Lỗi nạp history:", err);
            }}
        }}

        async function confirmResetHistory() {{
            if (!confirm("Sếp có chắc chắn muốn xóa sạch toàn bộ lịch sử giao dịch test cũ để bắt đầu chu kỳ thống kê mới sạch sẽ không?")) return;
            try {{
                const res = await fetch('/api/reset_history', {{ method: 'POST' }});
                const data = await res.json();
                if (data.success) {{
                    showToast(data.message, "success");
                    fetchHistory();
                    fetchStatus();
                }} else {{
                    showToast(data.message, "error");
                }}
            }} catch(e) {{
                showToast("Lỗi khi reset lịch sử: " + e, "error");
            }}
        }}

        function changeHistoryPageSize(size) {{
            historyPageSize = parseInt(size, 10) || 10;
            historyCurrentPage = 1;
            applyHistoryFilter();
        }}

        function goToHistoryPage(page) {{
            historyCurrentPage = page;
            applyHistoryFilter();
            const sec = document.getElementById('section-history');
            if (sec) sec.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }}

        function setFilterType(type) {{
            currentFilterType = type;
            historyCurrentPage = 1;
            ['all', 'win', 'loss'].forEach(t => {{
                const btn = document.getElementById(`btn-filter-${{t}}`);
                if (btn) {{
                    if (t === type) {{
                        btn.className = "px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-binanceGold text-black";
                    }} else {{
                        btn.className = "px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-darkBase text-gray-300 border border-darkBorder hover:text-white";
                    }}
                }}
            }});
            applyHistoryFilter();
        }}

        function applyHistoryFilter() {{
            const searchKeyword = (document.getElementById('history-search')?.value || '').toUpperCase().trim();
            const tbody = document.getElementById('history-table-body');
            const mobileContainer = document.getElementById('history-mobile-container');
            const pagContainer = document.getElementById('history-pagination-container');

            let filtered = rawHistoryTrades.filter(t => {{
                const symMatch = !searchKeyword || (t.symbol && t.symbol.toUpperCase().includes(searchKeyword));
                const pnl = parseFloat(t.pnl_usdt || 0);
                if (currentFilterType === 'win') return symMatch && pnl > 0;
                if (currentFilterType === 'loss') return symMatch && pnl < 0;
                return symMatch;
            }});

            const totalItems = filtered.length;

            if (totalItems === 0) {{
                if (tbody) tbody.innerHTML = '<tr><td colspan="9" class="px-6 py-6 text-center text-gray-400 font-sans">Không tìm thấy giao dịch nào phù hợp bộ lọc.</td></tr>';
                if (mobileContainer) mobileContainer.innerHTML = '<div class="p-6 text-center text-xs text-gray-400 font-sans">Không tìm thấy giao dịch nào phù hợp bộ lọc.</div>';
                if (pagContainer) pagContainer.classList.add('hidden');
                return;
            }}

            if (pagContainer) pagContainer.classList.remove('hidden');

            const totalPages = Math.ceil(totalItems / historyPageSize) || 1;
            if (historyCurrentPage > totalPages) historyCurrentPage = totalPages;
            if (historyCurrentPage < 1) historyCurrentPage = 1;

            const startIndex = (historyCurrentPage - 1) * historyPageSize;
            const endIndex = Math.min(startIndex + historyPageSize, totalItems);
            const paginatedItems = filtered.slice(startIndex, endIndex);

            safeSetText('history-pagination-info', `Lệnh ${{startIndex + 1}}-${{endIndex}} / ${{totalItems}}`);

            // Render Pagination Buttons
            const btnContainer = document.getElementById('history-pagination-buttons');
            if (btnContainer) {{
                let btnsHtml = '';
                const prevDisabled = historyCurrentPage <= 1;
                btnsHtml += `<button onclick="goToHistoryPage(${{historyCurrentPage - 1}})" ${{prevDisabled ? 'disabled' : ''}} class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-darkBase border border-darkBorder ${{prevDisabled ? 'text-gray-600 cursor-not-allowed' : 'text-gray-300 hover:text-binanceGold hover:border-binanceGold/40 active:scale-95 transition'}}"><i class="fa-solid fa-chevron-left text-[10px]"></i></button>`;

                let startPage = Math.max(1, historyCurrentPage - 1);
                let endPage = Math.min(totalPages, startPage + 2);
                if (endPage - startPage < 2) {{
                    startPage = Math.max(1, endPage - 2);
                }}

                if (startPage > 1) {{
                    btnsHtml += `<button onclick="goToHistoryPage(1)" class="w-7 h-7 rounded-lg text-xs font-mono font-semibold bg-darkBase text-gray-400 hover:text-white border border-darkBorder transition">1</button>`;
                    if (startPage > 2) btnsHtml += `<span class="text-gray-600 px-0.5">...</span>`;
                }}

                for (let p = startPage; p <= endPage; p++) {{
                    if (p === historyCurrentPage) {{
                        btnsHtml += `<button class="w-7 h-7 rounded-lg text-xs font-mono font-bold bg-binanceGold text-black shadow-md shadow-yellow-900/30">${{p}}</button>`;
                    }} else {{
                        btnsHtml += `<button onclick="goToHistoryPage(${{p}})" class="w-7 h-7 rounded-lg text-xs font-mono font-semibold bg-darkBase text-gray-400 hover:text-white border border-darkBorder transition hover:border-binanceGold/40">${{p}}</button>`;
                    }}
                }}

                if (endPage < totalPages) {{
                    if (endPage < totalPages - 1) btnsHtml += `<span class="text-gray-600 px-0.5">...</span>`;
                    btnsHtml += `<button onclick="goToHistoryPage(${{totalPages}})" class="w-7 h-7 rounded-lg text-xs font-mono font-semibold bg-darkBase text-gray-400 hover:text-white border border-darkBorder transition">${{totalPages}}</button>`;
                }}

                const nextDisabled = historyCurrentPage >= totalPages;
                btnsHtml += `<button onclick="goToHistoryPage(${{historyCurrentPage + 1}})" ${{nextDisabled ? 'disabled' : ''}} class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-darkBase border border-darkBorder ${{nextDisabled ? 'text-gray-600 cursor-not-allowed' : 'text-gray-300 hover:text-binanceGold hover:border-binanceGold/40 active:scale-95 transition'}}"><i class="fa-solid fa-chevron-right text-[10px]"></i></button>`;

                btnContainer.innerHTML = btnsHtml;
            }}

            if (tbody) {{
                tbody.innerHTML = paginatedItems.map(t => {{
                    const pnlVal = parseFloat(t.pnl_usdt || 0);
                    const isWin = pnlVal >= 0;
                    const pnlColor = isWin ? 'text-profitGreen' : 'text-lossRed';
                    const sideColor = t.side === 'BUY' ? 'text-profitGreen' : 'text-lossRed';
                    const ep = parseFloat(t.entry_price || 0);
                    const xp = parseFloat(t.exit_price || 0);
                    const epStr = ep < 1 ? ep.toFixed(4) : ep.toFixed(2);
                    const xpStr = xp < 1 ? xp.toFixed(4) : xp.toFixed(2);

                    return `
                        <tr class="hover:bg-darkBase/30 transition">
                            <td class="px-5 py-3 text-gray-400">${{t.timestamp}}</td>
                            <td class="px-5 py-3 font-bold text-white font-sans">${{t.symbol}}</td>
                            <td class="px-5 py-3 font-semibold ${{sideColor}} font-sans">${{t.side}}</td>
                            <td class="px-5 py-3">$${{epStr}}</td>
                            <td class="px-5 py-3 font-semibold text-white">$${{xpStr}}</td>
                            <td class="px-5 py-3">${{t.qty}}</td>
                            <td class="px-5 py-3 font-bold ${{pnlColor}}">${{t.pnl_usdt}}</td>
                            <td class="px-5 py-3 font-bold ${{pnlColor}}">${{t.pnl_percent}}</td>
                            <td class="px-5 py-3 text-gray-300 italic font-sans">${{t.exit_reason}}</td>
                        </tr>
                    `;
                }}).join('');
            }}

            if (mobileContainer) {{
                mobileContainer.innerHTML = paginatedItems.map(t => {{
                    const pnlVal = parseFloat(t.pnl_usdt || 0);
                    const isWin = pnlVal >= 0;
                    const pnlColor = isWin ? 'text-profitGreen' : 'text-lossRed';
                    const sideBadge = t.side === 'BUY' 
                        ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-green-950/60 text-profitGreen border border-green-700/50">BUY</span>' 
                        : '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-950/60 text-lossRed border border-red-700/50">SELL</span>';
                    const sign = (isWin && !String(t.pnl_usdt).includes('+')) ? '+' : '';
                    const ep = parseFloat(t.entry_price || 0);
                    const xp = parseFloat(t.exit_price || 0);
                    const epStr = ep < 1 ? ep.toFixed(4) : ep.toFixed(2);
                    const xpStr = xp < 1 ? xp.toFixed(4) : xp.toFixed(2);
                    const rawPct = String(t.pnl_percent || '0%');
                    const cleanPct = rawPct.endsWith('%') ? rawPct : rawPct + '%';

                    return `
                        <div class="glass-card rounded-xl p-3 border border-darkBorder text-xs space-y-2">
                            <div class="flex items-center justify-between">
                                <div class="flex items-center gap-2">
                                    <span class="font-bold text-white font-sans text-sm">${{t.symbol}}</span>
                                    ${{sideBadge}}
                                </div>
                                <div class="text-right font-mono">
                                    <span class="font-extrabold text-sm ${{pnlColor}}">${{sign}}${{t.pnl_usdt}}</span>
                                    <span class="text-[10px] ${{pnlColor}} block">(${{cleanPct}})</span>
                                </div>
                            </div>
                            <div class="flex justify-between items-center text-[10px] text-gray-400 font-mono pt-1.5 border-t border-darkBorder/50">
                                <span>$${{epStr}} ➜ $${{xpStr}}</span>
                                <span class="italic text-gray-300 font-sans truncate max-w-[50%] text-right">${{t.exit_reason}}</span>
                            </div>
                            <div class="text-[9px] text-gray-500 font-mono">
                                <span>${{t.timestamp}}</span> • SL: ${{t.qty}}
                            </div>
                        </div>
                    `;
                }}).join('');
            }}
        }}

        // Settings Modal Handlers
        let selectedStrategy = 'AUTO_DYNAMIC';
        function selectStrategy(strat) {{
            selectedStrategy = strat;
            currentConfig.active_strategy = strat;
            const stratMap = {{
                'AUTO_DYNAMIC': 'auto',
                'TREND_PULLBACK': 'trend',
                'BREAKOUT': 'breakout',
                'MEAN_REVERSION': 'mean'
            }};
            ['auto', 'trend', 'breakout', 'mean'].forEach(s => {{
                const btn = document.getElementById(`opt-strat-${{s}}`);
                if (btn) {{
                    if (s === (stratMap[strat] || 'auto')) {{
                        btn.className = "p-2.5 rounded-xl border text-left flex flex-col justify-between transition border-binanceGold bg-yellow-950/20 text-binanceGold";
                    }} else {{
                        btn.className = "p-2.5 rounded-xl border text-left flex flex-col justify-between transition border-darkBorder bg-darkBase text-gray-300";
                    }}
                }}
            }});
        }}

        function openSettingsModal() {{
            document.getElementById('settings-modal').classList.remove('hidden');
            selectTradingMode(currentConfig.trading_mode);
            selectStrategy(currentConfig.active_strategy || 'AUTO_DYNAMIC');
            selectLeverage(currentConfig.leverage);
            selectRisk(currentConfig.risk_percent);
            document.getElementById('chk-trailing-stop').checked = currentConfig.use_trailing_stop;
            const hardCapInput = document.getElementById('input-hard-cap');
            if (currentConfig.deepseek_api_key) {{
                const dsInput = document.getElementById('input-deepseek-key');
                if (dsInput) dsInput.value = currentConfig.deepseek_api_key;
            }}
            if (currentConfig.gemini_api_key || currentConfig.ai_api_key) {{
                const gmInput = document.getElementById('input-ai-key');
                if (gmInput) gmInput.value = currentConfig.gemini_api_key || currentConfig.ai_api_key;
            }}
            selectAiMode(currentConfig.ai_provider || 'dual');
        }}

        function selectAiMode(mode) {{
            currentConfig.ai_provider = mode;
            ['dual', 'deepseek', 'gemini'].forEach(m => {{
                const btn = document.getElementById(`btn-aimode-${{m}}`);
                if (!btn) return;
                if (m === mode) {{
                    btn.className = "py-1.5 px-2 rounded-lg font-semibold border border-cyberCyan bg-cyan-950/40 text-cyberCyan transition";
                }} else {{
                    btn.className = "py-1.5 px-2 rounded-lg font-semibold border border-darkBorder bg-darkCard text-gray-400 hover:text-white transition";
                }}
            }});
        }}

        function closeSettingsModal() {{
            document.getElementById('settings-modal').classList.add('hidden');
        }}

        function selectTradingMode(mode) {{
            currentConfig.trading_mode = mode;
            const bB = document.getElementById('opt-mode-bluechip');
            const bA = document.getElementById('opt-mode-all');
            if (mode === 'BLUECHIP_ONLY') {{
                bB.className = "p-3 rounded-xl border text-left flex flex-col justify-between transition border-cyan-500 bg-cyan-950/30 text-cyberCyan";
                bA.className = "p-3 rounded-xl border text-left flex flex-col justify-between transition border-darkBorder bg-darkBase text-gray-300";
            }} else {{
                bA.className = "p-3 rounded-xl border text-left flex flex-col justify-between transition border-binanceGold bg-yellow-950/20 text-binanceGold";
                bB.className = "p-3 rounded-xl border text-left flex flex-col justify-between transition border-darkBorder bg-darkBase text-gray-300";
            }}
        }}

        function selectLeverage(lev) {{
            currentConfig.leverage = lev;
            [3, 5, 10, 15].forEach(l => {{
                const btn = document.getElementById(`opt-lev-${{l}}`);
                if (l === lev) {{
                    btn.className = "py-2 rounded-lg font-mono font-bold border border-binanceGold bg-yellow-950/30 text-binanceGold";
                }} else {{
                    btn.className = "py-2 rounded-lg font-mono font-bold border border-darkBorder bg-darkBase text-gray-300";
                }}
            }});
        }}

        function selectRisk(risk) {{
            currentConfig.risk_percent = risk;
            [0.5, 1.0, 1.5, 2.0].forEach(r => {{
                const id = 'opt-risk-' + (r === 0.5 ? '05' : (r === 1.0 ? '10' : (r === 1.5 ? '15' : '20')));
                const btn = document.getElementById(id);
                if (r === risk) {{
                    btn.className = "py-2 rounded-lg font-mono font-bold border border-profitGreen bg-green-950/30 text-profitGreen";
                }} else {{
                    btn.className = "py-2 rounded-lg font-mono font-bold border border-darkBorder bg-darkBase text-gray-300";
                }}
            }});
        }}

        async function saveLiveSettings() {{
            currentConfig.use_trailing_stop = document.getElementById('chk-trailing-stop').checked;
            currentConfig.active_strategy = selectedStrategy;
            const hardCapInput = document.getElementById('input-hard-cap');
            if (hardCapInput) {{
                currentConfig.real_trading_hard_cap = parseFloat(hardCapInput.value) || 100;
            }}
            const dsKeyInput = document.getElementById('input-deepseek-key');
            if (dsKeyInput) {{
                currentConfig.deepseek_api_key = dsKeyInput.value.trim();
            }}
            const aiKeyInput = document.getElementById('input-ai-key');
            if (aiKeyInput) {{
                currentConfig.gemini_api_key = aiKeyInput.value.trim();
                currentConfig.ai_api_key = aiKeyInput.value.trim();
            }}
            try {{
                const res = await fetch('/api/update_settings', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(currentConfig)
                }});
                const data = await res.json();
                closeSettingsModal();
                if (data.success) {{
                    playChime('tp');
                    showToast(data.message, "success");
                    fetchStatus();
                    fetchRadar();
                    updateMascotCommentary();
                }} else {{
                    showToast(data.message, "error");
                }}
            }} catch (err) {{
                showToast("Lỗi cập nhật cấu hình: " + err, "error");
            }}
        }}

        // Pause & Panic Close
        async function togglePause() {{
            try {{
                const res = await fetch('/api/toggle_pause', {{method: 'POST'}});
                const data = await res.json();
                playChime('alert');
                showToast(data.message, "info");
                fetchStatus();
            }} catch (err) {{
                showToast("Lỗi khi pause bot: " + err, "error");
            }}
        }}

        function confirmPanicClose() {{
            document.getElementById('confirm-modal').classList.remove('hidden');
            document.getElementById('modal-confirm-btn').onclick = executePanicClose;
        }}

        function closeConfirmModal() {{
            document.getElementById('confirm-modal').classList.add('hidden');
        }}

        async function executePanicClose() {{
            closeConfirmModal();
            try {{
                playChime('alert');
                showToast("Đang gửi lệnh đóng toàn bộ vị thế...", "warning");
                const res = await fetch('/api/panic_close', {{method: 'POST'}});
                const data = await res.json();
                showToast(data.message, "success");
                fetchStatus();
                fetchHistory();
            }} catch (err) {{
                showToast("Lỗi khi đóng khẩn cấp: " + err, "error");
            }}
        }}

        async function closeSinglePosition(symbol) {{
            if (!confirm(`Bạn có chắc muốn đóng vị thế ${{symbol}} ngay lập tức?`)) return;
            try {{
                const res = await fetch('/api/close_single', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{symbol: symbol}})
                }});
                const data = await res.json();
                if (data.success) {{
                    showToast(data.message, "success");
                }} else {{
                    showToast(data.message, "error");
                }}
                fetchStatus();
                fetchHistory();
            }} catch (err) {{
                showToast("Lỗi đóng vị thế: " + err, "error");
            }}
        }}

        // TradingView Lightweight Charts State & Handlers
        let tvChartInstance = null;
        let tvCandleSeries = null;
        let currentChartSymbol = 'BTCUSDT';
        let currentChartInterval = '15m';
        let tvPriceLines = [];

        function openChartModal(symbol, interval = '15m') {{
            currentChartSymbol = symbol || 'BTCUSDT';
            currentChartInterval = interval || '15m';
            const modal = document.getElementById('tv-chart-modal');
            if (modal) modal.classList.remove('hidden');
            const title = document.getElementById('tv-chart-title');
            if (title) title.innerText = currentChartSymbol;
            loadChartData(currentChartSymbol, currentChartInterval);
        }}

        function closeChartModal() {{
            const modal = document.getElementById('tv-chart-modal');
            if (modal) modal.classList.add('hidden');
        }}

        function changeChartInterval(interval) {{
            currentChartInterval = interval;
            ['5m', '15m', '1h', '4h'].forEach(tf => {{
                const btn = document.getElementById(`tf-${{tf}}`);
                if (btn) {{
                    if (tf === interval) {{
                        btn.className = "px-2 py-1 rounded bg-binanceGold text-black font-bold";
                    }} else {{
                        btn.className = "px-2 py-1 rounded text-gray-400 hover:text-white";
                    }}
                }}
            }});
            loadChartData(currentChartSymbol, currentChartInterval);
        }}

        async function loadChartData(symbol, interval) {{
            const loader = document.getElementById('tv-chart-loading');
            if (loader) loader.classList.remove('hidden');

            try {{
                const res = await fetch(`/api/klines?symbol=${{symbol}}&interval=${{interval}}&limit=120`);
                const data = await res.json();
                if (loader) loader.classList.add('hidden');

                if (!data.candles || data.candles.length === 0) {{
                    showToast("Không nạp được nến Binance cho " + symbol, "error");
                    return;
                }}

                const container = document.getElementById('tv-chart-view');
                if (!container) return;

                if (!tvChartInstance) {{
                    container.innerHTML = '';
                    tvChartInstance = LightweightCharts.createChart(container, {{
                        layout: {{
                            background: {{ color: '#0b0f19' }},
                            textColor: '#94a3b8',
                        }},
                        grid: {{
                            vertLines: {{ color: 'rgba(255, 255, 255, 0.04)' }},
                            horzLines: {{ color: 'rgba(255, 255, 255, 0.04)' }},
                        }},
                        crosshair: {{
                            mode: LightweightCharts.CrosshairMode.Normal,
                        }},
                        rightPriceScale: {{
                            borderColor: '#1e293b',
                        }},
                        timeScale: {{
                            borderColor: '#1e293b',
                            timeVisible: true,
                            secondsVisible: false,
                        }},
                    }});

                    tvCandleSeries = tvChartInstance.addCandlestickSeries({{
                        upColor: '#0ECB81',
                        downColor: '#F6465D',
                        borderVisible: false,
                        wickUpColor: '#0ECB81',
                        wickDownColor: '#F6465D',
                    }});

                    window.addEventListener('resize', () => {{
                        if (tvChartInstance && container) {{
                            tvChartInstance.applyOptions({{ width: container.clientWidth }});
                        }}
                    }});
                }}

                if (tvPriceLines && tvPriceLines.length > 0) {{
                    tvPriceLines.forEach(line => {{
                        try {{ tvCandleSeries.removePriceLine(line); }} catch(e) {{}}
                    }});
                    tvPriceLines = [];
                }}

                tvCandleSeries.setData(data.candles);
                tvChartInstance.timeScale().fitContent();

                const lastCandle = data.candles[data.candles.length - 1];
                if (lastCandle) {{
                    safeSetText('tv-chart-price', `$${{lastCandle.close.toFixed(4)}}`);
                }}

                const pos = data.position;
                const posBadge = document.getElementById('tv-chart-pos-badge');
                if (pos && pos.entry_price > 0) {{
                    if (posBadge) {{
                        posBadge.classList.remove('hidden');
                        posBadge.className = `px-2 py-0.5 rounded text-[10px] font-bold ${{pos.side === 'BUY' ? 'bg-green-950 text-profitGreen border border-green-700' : 'bg-red-950 text-lossRed border border-red-700'}}`;
                        posBadge.innerText = `${{pos.side === 'BUY' ? 'VỊ THẾ LONG' : 'VỊ THẾ SHORT'}}`;
                    }}
                    safeSetText('tv-legend-entry', `$${{pos.entry_price.toFixed(4)}}`);
                    safeSetText('tv-legend-sl', `$${{pos.stop_loss.toFixed(4)}}`);
                    safeSetText('tv-legend-tp', `$${{pos.take_profit.toFixed(4)}}`);

                    const entryLine = tvCandleSeries.createPriceLine({{
                        price: pos.entry_price,
                        color: '#00F0FF',
                        lineWidth: 2,
                        lineStyle: LightweightCharts.LineStyle.Solid,
                        axisLabelVisible: true,
                        title: 'ENTRY',
                    }});
                    tvPriceLines.push(entryLine);

                    const slLine = tvCandleSeries.createPriceLine({{
                        price: pos.stop_loss,
                        color: '#F6465D',
                        lineWidth: 2,
                        lineStyle: LightweightCharts.LineStyle.Dashed,
                        axisLabelVisible: true,
                        title: 'SL',
                    }});
                    tvPriceLines.push(slLine);

                    const tpLine = tvCandleSeries.createPriceLine({{
                        price: pos.take_profit,
                        color: '#0ECB81',
                        lineWidth: 2,
                        lineStyle: LightweightCharts.LineStyle.Dashed,
                        axisLabelVisible: true,
                        title: 'TP',
                    }});
                    tvPriceLines.push(tpLine);
                }} else {{
                    if (posBadge) posBadge.classList.add('hidden');
                    safeSetText('tv-legend-entry', '--');
                    safeSetText('tv-legend-sl', '--');
                    safeSetText('tv-legend-tp', '--');
                }}

            }} catch(err) {{
                if (loader) loader.classList.add('hidden');
                console.error("Lỗi nạp nến TradingView:", err);
            }}
        }}

        async function executeChartManualOrder(side) {{
            await executeManualOrder(currentChartSymbol, side);
            loadChartData(currentChartSymbol, currentChartInterval);
        }}

        // 1-Click Semi-Auto Order Execution
        async function executeManualOrder(symbol, side) {{
            const sideText = side === 'BUY' ? 'LONG 📈' : 'SHORT 📉';
            const entryRaw = prompt(`Giá vào dự kiến cho ${{symbol}}:`);
            if (entryRaw === null) return;
            const stopRaw = prompt(`Stop Loss bắt buộc cho ${{symbol}} ${{sideText}}:`);
            if (stopRaw === null) return;
            const qtyRaw = prompt(`Khối lượng (qty) cho ${{symbol}}:`);
            if (qtyRaw === null) return;
            const entryPrice = Number(entryRaw);
            const stopLoss = Number(stopRaw);
            const qty = Number(qtyRaw);
            const valid = Number.isFinite(entryPrice) && entryPrice > 0
                && Number.isFinite(stopLoss) && stopLoss > 0
                && Number.isFinite(qty) && qty > 0
                && ((side === 'BUY' && stopLoss < entryPrice)
                    || (side === 'SELL' && stopLoss > entryPrice));
            if (!valid) {{
                showToast('Entry, Stop Loss hoặc qty không hợp lệ/an toàn.', 'error');
                return;
            }}
            if (!confirm(`Xác nhận ${{sideText}} ${{symbol}} qty=${{qty}}, entry=${{entryPrice}}, SL=${{stopLoss}}?`)) return;

            try {{
                showToast(`Đang gửi lệnh ${{sideText}} ${{symbol}}...`, "warning");
                const res = await fetch('/api/manual_order', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        symbol: symbol, side: side, qty: qty,
                        entry_price: entryPrice, stop_loss: stopLoss,
                    }})
                }});
                const data = await res.json();
                if (data.success) {{
                    playChime('alert');
                    showToast(data.message || `Đã khớp lệnh ${{sideText}} ${{symbol}}!`, "success");
                    speakMascotVoice(`Đã vào lệnh ${{side === 'BUY' ? 'Long' : 'Short'}} ${{symbol}} thành công!`);
                    fetchStatus();
                    fetchRadar();
                }} else {{
                    showToast(`Lỗi: ${{data.message}}`, "error");
                }}
            }} catch(err) {{
                showToast("Lỗi kết nối khi gửi lệnh: " + err, "error");
            }}
        }}

        // Vietnamese Mascot Voice Synthesis
        function speakMascotVoice(text) {{
            speakText(text);
        }}

        // Performance Analytics Modal Handlers
        function openAnalyticsModal() {{
            const modal = document.getElementById('analytics-modal');
            if (modal) modal.classList.remove('hidden');
            fetchAnalytics();
        }}

        function closeAnalyticsModal() {{
            const modal = document.getElementById('analytics-modal');
            if (modal) modal.classList.add('hidden');
        }}

        async function fetchAnalytics() {{
            try {{
                const res = await fetch('/api/analytics');
                const data = await res.json();
                if (!data.success || !data.analytics) return;

                const a = data.analytics;
                const bestSym = a.best_symbol ? (a.best_symbol.symbol || a.best_symbol) : 'N/A';
                const worstSym = a.worst_symbol ? (a.worst_symbol.symbol || a.worst_symbol) : 'N/A';
                safeSetText('stat-streak', `Thắng max: ${{a.max_win_streak || 0}} | Thua: ${{a.max_loss_streak || 0}}`);
                safeSetText('stat-best-symbol', bestSym);
                safeSetText('stat-worst-symbol', worstSym);

                const tbody = document.getElementById('analytics-table-body');
                if (tbody) {{
                    const symbols = a.by_symbol || a.symbols || {{}};
                    const keys = Object.keys(symbols);
                    if (keys.length === 0) {{
                        tbody.innerHTML = '<tr><td colspan="5" class="px-4 py-6 text-center text-gray-400 font-sans">Chưa có đủ lệnh đóng để phân tích từng cặp.</td></tr>';
                        return;
                    }}
                    tbody.innerHTML = keys.map(sym => {{
                        const item = symbols[sym];
                        const pnlColor = item.net_pnl >= 0 ? 'text-profitGreen' : 'text-lossRed';
                        const sign = item.net_pnl >= 0 ? '+' : '';
                        const wr = item.win_rate !== undefined ? item.win_rate : (item.winrate || 0);
                        return `
                            <tr class="hover:bg-darkBase/40 transition">
                                <td class="px-3.5 py-2.5 font-bold text-white font-sans">${{sym}}</td>
                                <td class="px-3.5 py-2.5">${{item.trades}}</td>
                                <td class="px-3.5 py-2.5"><span class="text-profitGreen font-bold">${{item.wins}}</span> / <span class="text-lossRed font-bold">${{item.losses}}</span></td>
                                <td class="px-3.5 py-2.5 font-bold text-white">${{wr}}%</td>
                                <td class="px-3.5 py-2.5 font-bold ${{pnlColor}}">${{sign}}$${{item.net_pnl.toFixed(2)}}</td>
                            </tr>
                        `;
                    }}).join('');
                }}
            }} catch(err) {{
                console.error("Lỗi nạp analytics:", err);
            }}
        }}

        // Fear & Greed Info Helper
        function showFearGreedInfo() {{
            if (window._lastFng) {{
                const msg = 'Fear & Greed: ' + window._lastFng.value + '/100 [' + window._lastFng.classification_vi + ']. ' + window._lastFng.advice;
                showToast(msg, 'info');
                speakMascotVoice('Chỉ số tâm lý thị trường đang là ' + window._lastFng.value + ', trạng thái ' + window._lastFng.classification_vi + '.');
            }} else {{
                showToast('Đang đồng bộ chỉ số tâm lý thị trường...', 'info');
            }}
        }}

        // Telegram Web App Initialization
        if (window.Telegram && window.Telegram.WebApp) {{
            try {{
                const tg = window.Telegram.WebApp;
                tg.ready();
                tg.expand();
                if (tg.requestFullscreen) tg.requestFullscreen();
                if (tg.disableVerticalSwipes) tg.disableVerticalSwipes();
            }} catch(e) {{}}
        }}

        // Backtest Modal & Chart.js Engine
        let backtestChartInstance = null;

        function openBacktestModal() {{
            const modal = document.getElementById('backtest-modal');
            if (modal) modal.classList.remove('hidden');
            if (!backtestChartInstance) {{
                setTimeout(initBacktestChart, 100);
            }}
        }}

        function closeBacktestModal() {{
            const modal = document.getElementById('backtest-modal');
            if (modal) modal.classList.add('hidden');
        }}

        function initBacktestChart() {{
            const canvas = document.getElementById('backtestEquityCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            backtestChartInstance = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: ['Start'],
                    datasets: [{{
                        label: 'Số Dư Vốn ($)',
                        data: [1000],
                        borderColor: '#00F0FF',
                        backgroundColor: 'rgba(0, 240, 255, 0.08)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.2,
                        pointRadius: 2,
                        pointHoverRadius: 5
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            callbacks: {{
                                label: function(c) {{ return ' Số dư: $' + Number(c.raw).toFixed(2); }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{ grid: {{ color: 'rgba(255, 255, 255, 0.04)' }}, ticks: {{ color: '#64748B', font: {{ family: 'JetBrains Mono', size: 10 }}, maxTicksLimit: 7 }} }},
                        y: {{ grid: {{ color: 'rgba(255, 255, 255, 0.04)' }}, ticks: {{ color: '#64748B', font: {{ family: 'JetBrains Mono', size: 10 }}, callback: function(v) {{ return '$' + v; }} }} }}
                    }}
                }}
            }});
        }}

        async function runBacktestSimulation() {{
            const sym = (document.getElementById('bt-symbol').value || 'BTCUSDT').toUpperCase().trim();
            const strat = document.getElementById('bt-strategy').value;
            const days = parseInt(document.getElementById('bt-days').value || '14');
            const btn = document.getElementById('btn-run-backtest');

            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Đang giả lập...</span>';

            try {{
                const res = await fetch('/api/backtest', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ symbol: sym, strategy: strat, days: days, timeframe: '15m' }})
                }});
                const data = await res.json();
                if (!data.success) {{
                    showToast(data.message || 'Lỗi chạy backtest', 'error');
                    return;
                }}

                // Update cards
                safeSetText('bt-winrate', data.win_rate + '%');
                safeSetText('bt-trades-count', data.winning_trades + ' thắng / ' + data.losing_trades + ' thua (' + data.total_trades + ' lệnh)');
                const sign = data.net_profit >= 0 ? '+' : '';
                safeSetText('bt-pnl', sign + '$' + data.net_profit.toFixed(2));
                const pnlElem = document.getElementById('bt-pnl');
                if (pnlElem) pnlElem.className = 'text-lg sm:text-xl font-extrabold font-mono mt-1 ' + (data.net_profit >= 0 ? 'text-profitGreen' : 'text-lossRed');
                safeSetText('bt-roi', sign + data.net_profit_percent.toFixed(2) + '% ROI');
                safeSetText('bt-pf', '' + data.profit_factor);
                safeSetText('bt-dd', data.max_drawdown_percent + '%');

                // Update Chart
                if (backtestChartInstance && data.equity_curve && data.equity_curve.length > 0) {{
                    backtestChartInstance.data.labels = data.equity_curve.map(function(p) {{ return p.time; }});
                    backtestChartInstance.data.datasets[0].data = data.equity_curve.map(function(p) {{ return p.balance; }});
                    const isProfit = data.net_profit >= 0;
                    backtestChartInstance.data.datasets[0].borderColor = isProfit ? '#0ECB81' : '#F6465D';
                    backtestChartInstance.data.datasets[0].backgroundColor = isProfit ? 'rgba(14, 203, 129, 0.1)' : 'rgba(246, 70, 93, 0.1)';
                    backtestChartInstance.update();
                }}

                // Update Table
                const tbody = document.getElementById('bt-trades-body');
                safeSetText('bt-table-status', (data.trades ? data.trades.length : 0) + ' lệnh gần nhất');
                if (tbody) {{
                    if (!data.trades || data.trades.length === 0) {{
                        tbody.innerHTML = '<tr><td colspan="5" class="px-3 py-4 text-center text-gray-500 font-sans">Không phát sinh lệnh trong chu kỳ này.</td></tr>';
                    }} else {{
                        tbody.innerHTML = data.trades.slice().reverse().map(function(t) {{
                            const isWin = t.net_pnl > 0;
                            const pSign = isWin ? '+' : '';
                            const col = isWin ? 'text-profitGreen' : (t.net_pnl < 0 ? 'text-lossRed' : 'text-gray-400');
                            const sideBadge = t.side === 'BUY' ? '<span class="px-1.5 py-0.5 rounded bg-green-950/40 text-profitGreen border border-green-700/50 font-bold">LONG</span>' : '<span class="px-1.5 py-0.5 rounded bg-red-950/40 text-lossRed border border-red-700/50 font-bold">SHORT</span>';
                            return '<tr class="hover:bg-darkCard/50">' +
                                '<td class="px-3 py-2 text-gray-400">' + (t.exit_time || t.entry_time) + '</td>' +
                                '<td class="px-3 py-2">' + sideBadge + '</td>' +
                                '<td class="px-3 py-2">$' + t.entry_price.toFixed(4) + ' → $' + t.exit_price.toFixed(4) + '</td>' +
                                '<td class="px-3 py-2 text-gray-400">' + t.exit_reason + '</td>' +
                                '<td class="px-3 py-2 text-right font-bold ' + col + '">' + pSign + '$' + t.net_pnl.toFixed(2) + '</td>' +
                            '</tr>';
                        }}).join('');
                    }}
                }}

                showToast('Giả lập hoàn tất: Winrate ' + data.win_rate + '%, PnL ' + sign + '$' + data.net_profit.toFixed(2) + '!', 'success');
                speakMascotVoice('Kiểm thử ' + sym + ' hoàn tất! Tỷ lệ thắng ' + data.win_rate + ' phần trăm.');

            }} catch (e) {{
                showToast('Lỗi thực thi giả lập: ' + e, 'error');
            }} finally {{
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-play text-xs"></i> <span>Chạy Giả Lập</span>';
            }}
        }}

        async function fetchFundingVault() {{
            try {{
                const res = await fetch('/api/funding_arbitrage');
                const data = await res.json();
                const tbody = document.getElementById('funding-vault-body');
                if (!tbody) return;
                if (!data.opportunities || data.opportunities.length === 0) {{
                    tbody.innerHTML = '<tr><td colspan="3" class="py-3 text-center text-gray-500 font-sans">Không tìm thấy cặp có Funding chênh lệch lớn.</td></tr>';
                    return;
                }}
                tbody.innerHTML = data.opportunities.slice(0, 5).map(function(opp) {{
                    const isPos = opp.funding_rate_percent >= 0;
                    const col = isPos ? 'text-profitGreen' : 'text-lossRed';
                    const sign = isPos ? '+' : '';
                    return '<tr class="hover:bg-darkCard/40">' +
                        '<td class="py-1.5 px-2 font-bold text-white">' + opp.symbol + '</td>' +
                        '<td class="py-1.5 px-2 ' + col + '">' + sign + opp.funding_rate_percent.toFixed(4) + '%</td>' +
                        '<td class="py-1.5 px-2 text-right font-bold text-binanceGold">' + opp.estimated_apy.toFixed(1) + '% APY</td>' +
                    '</tr>';
                }}).join('');
            }} catch (e) {{
                console.error('Lỗi nạp Funding Arbitrage:', e);
            }}
        }}

        async function fetchLiquidationRadar(sym = 'BTCUSDT') {{
            try {{
                safeSetText('liq-symbol', sym);
                const res = await fetch('/api/liquidation_radar?symbol=' + sym);
                const data = await res.json();
                if (!data.radar || !data.radar.clusters) return;
                const r = data.radar;
                safeSetText('liq-cur-price', '$' + (r.current_price || 0).toLocaleString());

                const shorts = r.clusters.short_liquidations || [];
                const longs = r.clusters.long_liquidations || [];

                if (shorts.length >= 3) {{
                    safeSetText('liq-s100', '$' + shorts[0].price);
                    safeSetText('liq-s50', '$' + shorts[1].price);
                    safeSetText('liq-s20', '$' + shorts[2].price);
                }}
                if (longs.length >= 3) {{
                    safeSetText('liq-l100', '$' + longs[0].price);
                    safeSetText('liq-l50', '$' + longs[1].price);
                    safeSetText('liq-l20', '$' + longs[2].price);
                }}
            }} catch (e) {{
                console.error('Lỗi nạp Liquidation Radar:', e);
            }}
        }}

        async function fetchMacroNews() {{
            try {{
                const res = await fetch('/api/macro_news');
                const data = await res.json();
                const container = document.getElementById('macro-news-feed');
                if (!container) return;
                if (!data.news || data.news.length === 0) {{
                    container.innerHTML = '<div class="p-2 rounded-lg bg-darkBase/70 border border-darkBorder text-xs text-gray-400">Không có tin tức mới.</div>';
                    return;
                }}
                container.innerHTML = data.news.slice(0, 4).map(function(item) {{
                    const badge = item.sentiment > 0 ? '<span class="text-profitGreen text-[9px] font-bold">🟢 TÍCH CỰC</span>' : (item.sentiment < 0 ? '<span class="text-lossRed text-[9px] font-bold">🔴 RỦI RO</span>' : '<span class="text-gray-400 text-[9px] font-bold">⚪ TRUNG LẬP</span>');
                    return '<div class="p-2 rounded-lg bg-darkBase/70 border border-darkBorder text-xs space-y-1">' +
                        '<div class="flex justify-between items-center text-[10px] text-gray-400 font-mono">' +
                            '<span>' + (item.source || 'Sentinel') + '</span>' +
                            badge +
                        '</div>' +
                        '<p class="text-gray-200 text-[11px] leading-tight font-medium">' + item.title + '</p>' +
                    '</div>';
                }}).join('');
            }} catch (e) {{
                console.error('Lỗi nạp Macro News:', e);
            }}
        }}

        async function fetchOrderFlow(sym = 'BTCUSDT') {{
            try {{
                safeSetText('of-symbol', sym);
                const res = await fetch('/api/order_flow?symbol=' + sym);
                const data = await res.json();
                if (!data.order_flow) return;
                const of = data.order_flow;

                const deltaSign = of.delta >= 0 ? '+' : '';
                safeSetText('of-delta', deltaSign + (of.delta || 0).toLocaleString());
                const deltaElem = document.getElementById('of-delta');
                if (deltaElem) deltaElem.className = 'font-extrabold text-sm ' + (of.delta >= 0 ? 'text-profitGreen' : 'text-lossRed');

                safeSetText('of-cvd-pct', (of.cvd_percent >= 0 ? '+' : '') + of.cvd_percent + '%');
                safeSetText('of-imbalance', of.imbalance_ratio + 'x');
                safeSetText('of-desc', of.signal_desc || 'Bình thường');

                const badge = document.getElementById('of-bias-badge');
                if (badge) {{
                    badge.innerText = of.bias.replace(/_/g, ' ');
                    if (of.absorption_detected) {{
                        badge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-binanceGold border border-amber-600 animate-pulse';
                    }} else if (of.delta > 0) {{
                        badge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700/50';
                    }} else {{
                        badge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-red-950 text-lossRed border border-red-700/50';
                    }}
                }}
            }} catch (e) {{
                console.error('Lỗi nạp Order Flow:', e);
            }}
        }}

        async function fetchPairsTrading() {{
            try {{
                const res = await fetch('/api/pairs_trading');
                const data = await res.json();
                const tbody = document.getElementById('pairs-trading-body');
                if (!tbody) return;
                if (!data.pairs || data.pairs.length === 0) {{
                    tbody.innerHTML = '<tr><td colspan="4" class="py-4 text-center text-gray-500 font-sans">Không tìm thấy cặp phân kỳ.</td></tr>';
                    return;
                }}
                tbody.innerHTML = data.pairs.map(function(p) {{
                    const zCol = Math.abs(p.z_score) >= 1.8 ? 'text-binanceGold font-bold' : 'text-gray-300';
                    const actBadge = p.action === 'SHORT_A_LONG_B' 
                        ? '<span class="px-1.5 py-0.5 rounded bg-amber-950/60 text-binanceGold border border-amber-700/50 text-[10px] font-bold">SHORT ' + p.symbol_a + ' / LONG ' + p.symbol_b + '</span>'
                        : (p.action === 'LONG_A_SHORT_B'
                            ? '<span class="px-1.5 py-0.5 rounded bg-cyan-950/60 text-cyberCyan border border-cyan-700/50 text-[10px] font-bold">LONG ' + p.symbol_a + ' / SHORT ' + p.symbol_b + '</span>'
                            : '<span class="text-gray-400 text-[10px]">Cân Bằng (Hội tụ)</span>');

                    return '<tr class="hover:bg-darkCard/40">' +
                        '<td class="py-1.5 px-2 font-bold text-white">' + p.pair_name + '</td>' +
                        '<td class="py-1.5 px-2 text-gray-300 font-mono">' + p.current_spread + '</td>' +
                        '<td class="py-1.5 px-2 ' + zCol + '">' + (p.z_score > 0 ? '+' : '') + p.z_score + 'σ</td>' +
                        '<td class="py-1.5 px-2 text-right">' + actBadge + '</td>' +
                    '</tr>';
                }}).join('');
            }} catch (e) {{
                console.error('Lỗi nạp Pairs Trading:', e);
            }}
        }}

        async function fetchWhaleTracker() {{
            try {{
                const res = await fetch('/api/whale_tracker');
                const data = await res.json();
                if (!data.whale_data) return;
                const wd = data.whale_data;

                const biasTag = document.getElementById('whale-bias-tag');
                if (biasTag) {{
                    const isAcc = wd.market_bias === 'SMART_MONEY_ACCUMULATION';
                    biasTag.innerText = isAcc ? 'TÍCH LŨY 🟢' : 'PHÂN PHỐI 🔴';
                    biasTag.className = 'px-2 py-0.5 rounded text-[10px] font-bold ' + (isAcc ? 'bg-green-950 text-profitGreen border border-green-700/50' : 'bg-red-950 text-lossRed border border-red-700/50');
                }}

                safeSetText('whale-liquidity-status', wd.stablecoin_reserve_health || 'DỒI DÀO');

                const list = document.getElementById('whale-transfers-list');
                if (list && wd.recent_whale_transfers) {{
                    list.innerHTML = wd.recent_whale_transfers.map(function(t) {{
                        return '<div class="p-2 rounded-lg bg-darkBase/70 border border-darkBorder text-[11px] flex justify-between items-center">' +
                            '<div><b class="text-white font-mono">' + t.amount + '</b> <span class="text-gray-400">(' + t.from + ' ➜ ' + t.to + ')</span></div>' +
                            '<span class="text-[10px] font-bold text-binanceGold">' + t.type + '</span>' +
                        '</div>';
                    }}).join('');
                }}
            }} catch (e) {{
                console.error('Lỗi nạp Whale Tracker:', e);
            }}
        }}

        async function fetchCrossBasis() {{
            try {{
                const res = await fetch('/api/cross_basis');
                const data = await res.json();
                const tbody = document.getElementById('basis-arbitrage-body');
                if (!tbody) return;
                if (!data.basis_data || data.basis_data.length === 0) {{
                    tbody.innerHTML = '<tr><td colspan="4" class="py-4 text-center text-gray-500 font-sans">Không tìm thấy chênh lệch Basis.</td></tr>';
                    return;
                }}
                tbody.innerHTML = data.basis_data.map(function(b) {{
                    return '<tr class="hover:bg-darkCard/40">' +
                        '<td class="py-1.5 px-2 font-bold text-white">' + b.symbol + '</td>' +
                        '<td class="py-1.5 px-2 text-gray-300 font-mono">$' + b.basis_usdt + ' (' + (b.basis_percent >= 0 ? '+' : '') + b.basis_percent + '%)</td>' +
                        '<td class="py-1.5 px-2 text-[10px] text-gray-400">' + b.market_state + '</td>' +
                        '<td class="py-1.5 px-2 text-right font-bold text-rose-400 font-mono">' + b.annualized_apy + '% APY</td>' +
                    '</tr>';
                }}).join('');
            }} catch (e) {{
                console.error('Lỗi nạp Basis Arbitrage:', e);
            }}
        }}

        async function sendQuantumCommand() {{
            const input = document.getElementById('voice-cmd-input');
            const text = (input ? input.value : '').trim();
            if (!text) return;

            const resBox = document.getElementById('voice-cmd-response-box');
            const resText = document.getElementById('voice-cmd-response-text');
            if (resBox) resBox.classList.remove('hidden');
            if (resText) resText.innerText = 'Đang giải mã chỉ lệnh và thực thi...';

            try {{
                const res = await fetch('/api/voice_command', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ command: text }})
                }});
                const data = await res.json();
                if (resText) resText.innerText = data.reply || 'Đã thi hành.';
                if (data.speak) speakText(data.speak);
                showToast(data.reply || 'Đã thi hành lệnh!', 'success');
                if (input) input.value = '';
                fetchStatus();
            }} catch (e) {{
                if (resText) resText.innerText = 'Lỗi thực thi lệnh: ' + e;
            }}
        }}

        function startVoiceRecognition() {{
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {{
                showToast('Trình duyệt không hỗ trợ Web Speech. Vui lòng gõ lệnh trực tiếp.', 'info');
                return;
            }}
            const recognition = new SpeechRecognition();
            recognition.lang = 'vi-VN';
            recognition.interimResults = false;
            const micBtn = document.getElementById('icon-mic-state');

            recognition.onstart = function() {{
                if (micBtn) micBtn.className = 'fa-solid fa-microphone-lines animate-pulse text-lossRed';
                showToast('Đang lắng nghe giọng nói của Sếp...', 'info');
            }};
            recognition.onresult = function(event) {{
                const transcript = event.results[0][0].transcript;
                const input = document.getElementById('voice-cmd-input');
                if (input) input.value = transcript;
                sendQuantumCommand();
            }};
            recognition.onerror = function() {{
                if (micBtn) micBtn.className = 'fa-solid fa-microphone';
            }};
            recognition.onend = function() {{
                if (micBtn) micBtn.className = 'fa-solid fa-microphone';
            }};
            recognition.start();
        }}

        async function fetchSMC(sym = 'BTCUSDT') {{
            try {{
                safeSetText('smc-symbol', sym);
                const res = await fetch('/api/smc?symbol=' + sym);
                const data = await res.json();
                if (!data.smc) return;
                const smc = data.smc;

                const biasBadge = document.getElementById('smc-bias-badge');
                if (biasBadge) {{
                    biasBadge.innerText = smc.smc_bias.replace(/_/g, ' ');
                    if (smc.smc_bias.includes('LONG') || smc.smc_bias.includes('SUPPORT')) {{
                        biasBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700/50';
                    }} else if (smc.smc_bias.includes('SHORT') || smc.smc_bias.includes('RESISTANCE')) {{
                        biasBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-red-950 text-lossRed border border-red-700/50';
                    }} else {{
                        biasBadge.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-yellow-950 text-binanceGold border border-yellow-700/50';
                    }}
                }}

                if (smc.active_ob) {{
                    safeSetText('smc-ob-text', smc.active_ob.type.split(' ')[0] + ' ($' + smc.active_ob.low + ' - $' + smc.active_ob.high + ')');
                }} else {{
                    safeSetText('smc-ob-text', 'Chưa có OB mới');
                }}

                if (smc.active_fvg) {{
                    safeSetText('smc-fvg-text', smc.active_fvg.type.split(' ')[0] + ' (Mid: $' + smc.active_fvg.midpoint + ')');
                }} else {{
                    safeSetText('smc-fvg-text', 'Chưa có FVG mới');
                }}

                safeSetText('smc-sweep-text', smc.sweep_note || 'Bình thường.');
            }} catch (e) {{
                console.error('Lỗi nạp SMC:', e);
            }}
        }}

        async function fetchLeadLag() {{
            try {{
                const res = await fetch('/api/lead_lag');
                const data = await res.json();
                if (!data.lead_lag) return;
                const ll = data.lead_lag;

                const btcBadge = document.getElementById('lead-momentum-badge');
                if (btcBadge) {{
                    btcBadge.innerText = 'BTC ' + (ll.leader_momentum >= 0 ? '+' : '') + ll.leader_momentum + '% (24h)';
                }}

                const tbody = document.getElementById('lead-lag-body');
                if (!tbody) return;
                if (!ll.signals || ll.signals.length === 0) {{
                    tbody.innerHTML = '<tr><td colspan="3" class="py-4 text-center text-gray-500 font-sans">Đang quét độ trễ...</td></tr>';
                    return;
                }}

                tbody.innerHTML = ll.signals.map(function(s) {{
                    const isLag = s.sniper_action !== null;
                    const actBadge = isLag
                        ? '<span class="px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyberCyan border border-cyan-600/60 text-[10px] font-bold animate-pulse">⚡ BẮT SÓNG TRỄ</span>'
                        : '<span class="text-gray-400 text-[10px]">Đồng Pha (Khớp nhịp)</span>';

                    return '<tr class="hover:bg-darkCard/40">' +
                        '<td class="py-1.5 px-2 font-bold text-white font-mono">' + s.symbol + '</td>' +
                        '<td class="py-1.5 px-2 text-gray-300 font-mono">' + (s.lag_spread >= 0 ? '+' : '') + s.lag_spread + '%</td>' +
                        '<td class="py-1.5 px-2 text-right">' + actBadge + '</td>' +
                    '</tr>';
                }}).join('');
            }} catch (e) {{
                console.error('Lỗi nạp Lead Lag:', e);
            }}
        }}

        async function fetchSynthesis() {{
            try {{
                const res = await fetch('/api/ai_synthesis');
                const data = await res.json();
                if (!data.synthesis) return;
                const syn = data.synthesis;

                safeSetText('synth-mode-tag', syn.mode_tag || 'TỰ TIẾN HÓA');
                safeSetText('synth-rsi', syn.optimal_parameters.rsi_oversold + ' / ' + syn.optimal_parameters.rsi_overbought);
                safeSetText('synth-atr', syn.optimal_parameters.atr_sl_multiplier + 'x');
                safeSetText('synth-wr', syn.projected_metrics.projected_winrate);
                safeSetText('synth-rationale', syn.rationale || 'Đang tối ưu hóa...');
            }} catch (e) {{
                console.error('Lỗi nạp AI Synthesis:', e);
            }}
        }}

        async function fetchRebalancePlan() {{
            try {{
                const res = await fetch('/api/rebalance_plan');
                const data = await res.json();
                if (!data.rebalance) return;
                const reb = data.rebalance;

                safeSetText('rebalance-health-badge', reb.portfolio_health || 'CÂN BẰNG TỐI ƯU');

                const tbody = document.getElementById('rebalance-body');
                if (!tbody) return;
                if (!reb.basket || reb.basket.length === 0) return;

                tbody.innerHTML = reb.basket.map(function(item) {{
                    const driftCol = Math.abs(item.drift_percent) > 2.0 ? 'text-binanceGold' : 'text-gray-300';
                    return '<tr class="hover:bg-darkCard/40">' +
                        '<td class="py-1.5 px-2 font-bold text-white font-mono">' + item.asset + '</td>' +
                        '<td class="py-1.5 px-2 text-gray-300 font-mono">' + item.current_percent + '% / ' + item.target_percent + '%</td>' +
                        '<td class="py-1.5 px-2 ' + driftCol + ' font-mono">' + (item.drift_percent >= 0 ? '+' : '') + item.drift_percent + '%</td>' +
                        '<td class="py-1.5 px-2 text-right font-bold text-[10px] text-profitGreen">' + item.recommended_action + '</td>' +
                    '</tr>';
                }}).join('');
            }} catch (e) {{
                console.error('Lỗi nạp Rebalance Plan:', e);
            }}
        }}

        async function fetchPCABasket() {{
            try {{
                const res = await fetch('/api/pca_basket');
                const data = await res.json();
                const tbody = document.getElementById('pca-basket-body');
                const tagEl = document.getElementById('pca-status-tag');

                if (!data || !data.pca) {{
                    if (tbody) tbody.innerHTML = '<tr><td colspan="4" class="py-3 text-center text-gray-500 font-sans">Đang đồng bộ dữ liệu ma trận PCA từ Binance...</td></tr>';
                    return;
                }}
                const pca = data.pca;

                if (tagEl && pca.overall_status) {{
                    tagEl.textContent = pca.overall_status;
                }}

                if (!tbody || !pca.signals || pca.signals.length === 0) {{
                    if (tbody) tbody.innerHTML = '<tr><td colspan="4" class="py-3 text-center text-gray-500 font-sans">Chưa có đủ dữ liệu biến động từ sàn Binance.</td></tr>';
                    return;
                }}

                tbody.innerHTML = pca.signals.map(function(s) {{
                    const chgNum = parseFloat(s.change_24h || 0);
                    const chgColor = chgNum >= 0 ? 'text-profitGreen' : 'text-lossRed';
                    const chgSign = chgNum > 0 ? '+' : '';

                    const resNum = parseFloat(s.residual_spread || 0);
                    const resColor = Math.abs(s.z_score || 0) >= 1.8 ? (resNum > 0 ? 'text-lossRed' : 'text-profitGreen') : 'text-gray-300';
                    const resSign = resNum > 0 ? '+' : '';

                    let badgeClass = 'bg-darkBase text-gray-400 border border-darkBorder';
                    if (s.color === 'green') {{
                        badgeClass = 'bg-green-950/70 text-profitGreen border border-green-700/50';
                    }} else if (s.color === 'red') {{
                        badgeClass = 'bg-red-950/70 text-lossRed border border-red-700/50';
                    }}

                    return '<tr class="hover:bg-darkCard/40 transition">' +
                        '<td class="py-2 px-2 font-bold text-white font-mono">' + s.symbol + '</td>' +
                        '<td class="py-2 px-2 ' + chgColor + ' font-mono font-semibold">' + chgSign + chgNum.toFixed(2) + '%</td>' +
                        '<td class="py-2 px-2 ' + resColor + ' font-mono">' + resSign + resNum.toFixed(2) + '% <span class="text-[10px] text-gray-500 font-sans">(Z: ' + (s.z_score >= 0 ? '+' : '') + s.z_score + ')</span></td>' +
                        '<td class="py-2 px-2 text-right font-mono"><span class="px-2 py-0.5 rounded text-[10px] font-bold font-sans ' + badgeClass + '">' + s.sniper_signal + '</span></td>' +
                    '</tr>';
                }}).join('');
            }} catch (e) {{
                console.error('Lỗi nạp PCA Basket:', e);
                const tbody = document.getElementById('pca-basket-body');
                if (tbody) tbody.innerHTML = '<tr><td colspan="4" class="py-3 text-center text-gray-500 font-sans">Tạm ngắt kết nối PCA. Đang tự động thử lại...</td></tr>';
            }}
        }}

        async function fetchDigitalTwinStress() {{
            try {{
                const res = await fetch('/api/digital_twin_stress');
                const data = await res.json();
                const listEl = document.getElementById('twin-scenarios-list');

                if (!data || !data.stress_test) {{
                    if (listEl) listEl.innerHTML = '<div class="p-2.5 rounded-xl bg-darkBase/60 border border-darkBorder text-gray-400">Đang chuẩn bị kịch bản giả lập thảm họa...</div>';
                    return;
                }}
                const st = data.stress_test;

                safeSetText('twin-worst-dd', (st.worst_case_drawdown || 0) + '%');
                safeSetText('twin-health', st.digital_twin_health || 'VỮNG CHẮC (99.8%)');
                safeSetText('twin-positions', (st.positions_tested || 0) + ' Lệnh');
                safeSetText('twin-cocoon-state', st.cocoon_shield_triggered ? 'KÍCH HOẠT (BẢO VỆ)' : 'SẴN SÀNG');

                const cocoonTag = document.getElementById('cocoon-shield-tag');
                if (cocoonTag) {{
                    if (st.cocoon_shield_triggered) {{
                        cocoonTag.textContent = 'KÉN KÍCH HOẠT 🛡️';
                        cocoonTag.className = 'px-2.5 py-1 rounded-lg text-[10px] font-bold bg-red-950 text-lossRed border border-red-700/50';
                    }} else {{
                        cocoonTag.textContent = 'AN TOÀN';
                        cocoonTag.className = 'px-2.5 py-1 rounded-lg text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700/50';
                    }}
                }}

                if (!listEl || !st.scenarios || st.scenarios.length === 0) {{
                    if (listEl) listEl.innerHTML = '<div class="p-2.5 rounded-xl bg-darkBase/60 border border-darkBorder text-gray-400">Không có kịch bản thảm họa nào cần cảnh báo.</div>';
                    return;
                }}

                listEl.innerHTML = st.scenarios.map(function(sc) {{
                    const badgeClass = sc.color === 'green' 
                        ? 'bg-green-950/70 text-profitGreen border border-green-700/50' 
                        : 'bg-red-950/70 text-lossRed border border-red-700/50';
                    const ddColor = sc.simulated_drawdown_pct > 5.0 ? 'text-lossRed' : 'text-profitGreen';

                    return '<div class="p-2.5 rounded-xl bg-darkBase/60 border border-darkBorder space-y-1.5 hover:border-gray-700 transition">' +
                        '<div class="flex items-center justify-between">' +
                            '<span class="font-bold text-white text-xs truncate max-w-[65%] font-sans">' + sc.scenario_name + '</span>' +
                            '<span class="px-2 py-0.5 rounded text-[9px] font-bold font-sans ' + badgeClass + '">' + sc.status + '</span>' +
                        '</div>' +
                        '<p class="text-[10px] text-gray-400 font-sans line-clamp-1">' + sc.description + '</p>' +
                        '<div class="flex justify-between text-[11px] pt-1 border-t border-darkBorder/50 font-mono">' +
                            '<span class="text-gray-400 font-sans">Sụt giảm: <strong class="' + ddColor + ' font-mono">-' + sc.simulated_drawdown_pct + '%</strong></span>' +
                            '<span class="text-gray-400 font-sans">PnL: <strong class="text-lossRed font-mono">' + (sc.simulated_pnl_usdt > 0 ? '+' : '') + sc.simulated_pnl_usdt + ' USDT</strong></span>' +
                        '</div>' +
                    '</div>';
                }}).join('');
            }} catch (e) {{
                console.error('Lỗi nạp Digital Twin Stress Test:', e);
                const listEl = document.getElementById('twin-scenarios-list');
                if (listEl) listEl.innerHTML = '<div class="p-2.5 rounded-xl bg-darkBase/60 border border-darkBorder text-gray-500">Đang tái kết nối giả lập thảm họa...</div>';
            }}
        }}

        async function fetchAITraining() {{
            try {{
                const res = await fetch('/api/ai_training');
                const data = await res.json();
                if (!data || !data.ai_training) return;
                const ai = data.ai_training;

                safeSetText('ai-train-samples', (ai.sample_size || 0) + ' lệnh');
                safeSetText('ai-train-winrate', (ai.win_rate !== undefined ? Number(ai.win_rate).toFixed(1) : '0.0') + '%');
                safeSetText('ai-train-pf', (ai.profit_factor !== undefined ? Number(ai.profit_factor).toFixed(2) : '0.00'));

                const rec = ai.recommendations || {{}};
                const rsiBounds = rec.rsi_boundaries || [30, 70];
                safeSetText('ai-train-rsi', rsiBounds[0] + ' / ' + rsiBounds[1]);
                safeSetText('ai-train-atr', (rec.atr_stop_multiplier || 1.5) + 'x ATR');
                safeSetText('ai-train-rr', '1:' + (rec.target_risk_reward || 2.0));
                safeSetText('ai-train-time', ai.last_trained_at_vn || '--:--:-- (VN)');

                const badgeEl = document.getElementById('ai-train-confidence-badge');
                if (badgeEl) {{
                    const conf = ai.model_confidence || 70;
                    badgeEl.textContent = 'ĐỘ TIN CẬY: ' + conf + '%';
                }}

                const favEl = document.getElementById('ai-favored-coins');
                if (favEl) {{
                    const favored = rec.favored_symbols || [];
                    if (favored.length > 0) {{
                        favEl.innerHTML = favored.map(function(s) {{
                            return '<span class="px-2 py-0.5 rounded-lg bg-green-950/70 text-profitGreen border border-green-700/50 font-bold">' + s + '</span>';
                        }}).join('');
                    }} else {{
                        favEl.innerHTML = '<span class="text-gray-400 text-[11px]">Đang phân bổ đồng đều danh mục</span>';
                    }}
                }}

                const avoidEl = document.getElementById('ai-avoid-coins');
                if (avoidEl) {{
                    const avoid = rec.avoid_symbols || [];
                    if (avoid.length > 0) {{
                        avoidEl.innerHTML = avoid.map(function(s) {{
                            return '<span class="px-2 py-0.5 rounded-lg bg-red-950/70 text-lossRed border border-red-700/50 font-bold">' + s + '</span>';
                        }}).join('');
                    }} else {{
                        avoidEl.innerHTML = '<span class="text-gray-400 text-[11px]">Không có coin nào bị gắn cờ rủi ro</span>';
                    }}
                }}

                const insEl = document.getElementById('ai-pattern-insights');
                if (insEl) {{
                    const insights = ai.pattern_insights || [];
                    if (insights.length > 0) {{
                        insEl.innerHTML = insights.map(function(it) {{
                            return '<div class="flex items-start gap-1.5"><i class="fa-solid fa-angle-right text-purple-400 text-[10px] mt-1"></i><span>' + it + '</span></div>';
                        }}).join('');
                    }} else {{
                        insEl.innerHTML = '<p class="text-gray-400 text-[11px]">Dữ liệu đang tiếp tục thu thập thêm các mẫu hình mới...</p>';
                    }}
                }}
            }} catch(e) {{
                console.error('Lỗi nạp AI Training:', e);
            }}
        }}

        async function triggerAITraining() {{
            const btn = document.getElementById('btn-trigger-ai-train');
            const icon = document.getElementById('icon-retrain');
            if (icon) icon.classList.add('fa-spin');
            if (btn) btn.disabled = true;

            try {{
                const res = await fetch('/api/ai_train', {{ method: 'POST' }});
                const data = await res.json();
                if (data.success) {{
                    await fetchAITraining();
                    showToast('Huấn luyện AI thành công! Đã cập nhật chiến thuật tối ưu.', 'success');
                }} else {{
                    showToast('Lỗi huấn luyện AI: ' + (data.error || 'Thất bại'), 'error');
                }}
            }} catch(e) {{
                showToast('Lỗi kết nối máy chủ AI', 'error');
            }} finally {{
                if (icon) icon.classList.remove('fa-spin');
                if (btn) btn.disabled = false;
            }}
        }}

        async function fetchSubAccountYield() {{
            try {{
                const res = await fetch('/api/subaccount_yield');
                const data = await res.json();
                if (!data.yield_harvester) return;
                const yh = data.yield_harvester;

                safeSetText('earn-sweep-tag', yh.sweep_status || 'ĐANG SINH LỜI');
                safeSetText('earn-allocated', '$' + Number(yh.allocated_to_simple_earn || 0).toFixed(2));
                safeSetText('earn-apr', (yh.current_earn_apr || 10.5) + '%');
                safeSetText('earn-annual', '+$' + Number(yh.annual_passive_yield || 0).toFixed(2));
            }} catch (e) {{
                console.error('Lỗi nạp SubAccount Yield:', e);
            }}
        }}

        async function fetchGeneticEvolution() {{
            try {{
                const res = await fetch('/api/genetic_evolution');
                const data = await res.json();
                if (!data.evolution) return;
                const ev = data.evolution;

                safeSetText('genetic-gen-tag', ev.generation_tag || 'APEX F5');
                safeSetText('genetic-sharpe', Number(ev.projected_sharpe || 1.7).toFixed(2));
                safeSetText('genetic-wr', Number(ev.projected_winrate || 54.0).toFixed(1) + '%');
                safeSetText('genetic-params', (ev.optimal_rsi_buy || 26) + '/' + (ev.optimal_rsi_sell || 74) + ' (' + (ev.optimal_atr_sl || 1.7) + 'x)');
            }} catch (e) {{
                console.error('Lỗi nạp Genetic Evolution:', e);
            }}
        }}

        // PWA Service Worker Cleanup (Force fresh updates from server)
        if ('serviceWorker' in navigator) {{
            navigator.serviceWorker.getRegistrations().then((registrations) => {{
                for (let registration of registrations) {{
                    registration.unregister();
                }}
            }}).catch(() => {{}});
        }}

        // ==========================================
        // Authentication & Session Management
        // ==========================================
        let dashboardPollingActive = false;
        let dashboardIntervalIds = [];

        // Browser authentication is cookie-only; JavaScript never receives the bearer value.
        const originalFetch = window.fetch;
        window.fetch = async function(resource, init = {{}}) {{
            init = init || {{}};
            if (!init.credentials) init.credentials = 'same-origin';
            const response = await originalFetch(resource, init);
            if (response.status === 401) {{
                const urlStr = typeof resource === 'string' ? resource : (resource.url || '');
                if (!urlStr.includes('/api/login') && !urlStr.includes('/api/telegram_webapp_auth') && !urlStr.includes('/api/check_auth')) {{
                    stopDashboardPolling();
                    showLoginModal();
                }}
            }}
            return response;
        }};


        function showLoginModal() {{
            const modal = document.getElementById('login-modal');
            if (modal) modal.classList.remove('hidden');
        }}

        function hideLoginModal() {{
            const modal = document.getElementById('login-modal');
            if (modal) modal.classList.add('hidden');
        }}

        async function handleManualLogin(e) {{
            e.preventDefault();
            const uInput = document.getElementById('login-username');
            const pInput = document.getElementById('login-password');
            const errBox = document.getElementById('login-error-msg');
            const errText = document.getElementById('login-error-text');
            const submitBtn = document.getElementById('login-submit-btn');

            if (errBox) errBox.classList.add('hidden');
            if (submitBtn) {{
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>ĐANG XÁC THỰC...</span>';
            }}

            try {{
                const res = await originalFetch('/api/login', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ username: uInput.value.trim(), password: pInput.value.trim() }})
                }});

                const data = await res.json();
                if (res.ok && data.success) {{

                    hideLoginModal();
                    updateUserUI(data.username || uInput.value.trim());
                    showToast('Đăng nhập thành công! Chào mừng Sếp.', 'success');
                    startDashboardPolling();
                }} else {{
                    if (errBox && errText) {{
                        errText.textContent = data.message || 'Sai tên đăng nhập hoặc mật khẩu!';
                        errBox.classList.remove('hidden');
                    }}
                }}
            }} catch (err) {{
                if (errBox && errText) {{
                    errText.textContent = 'Không thể kết nối tới máy chủ bot: ' + err.message;
                    errBox.classList.remove('hidden');
                }}
            }} finally {{
                if (submitBtn) {{
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fa-solid fa-arrow-right-to-bracket"></i> <span>ĐĂNG NHẬP VÀO DASHBOARD</span>';
                }}
            }}
        }}

        async function loginWithTelegramWebApp(silent = false) {{
            const tg = window.Telegram?.WebApp;
            const initData = tg?.initData || '';
            const errBox = document.getElementById('login-error-msg');
            const errText = document.getElementById('login-error-text');

            if (!initData) {{
                if (!silent && errBox && errText) {{
                    errText.textContent = 'Không tìm thấy dữ liệu Telegram WebApp!';
                    errBox.classList.remove('hidden');
                }}
                return false;
            }}

            try {{
                const res = await originalFetch('/api/telegram_webapp_auth', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ init_data: initData }})
                }});

                const data = await res.json();
                if (res.ok && data.success) {{

                    hideLoginModal();
                    updateUserUI(data.username || 'Telegram Admin');
                    showToast(data.message || 'Đăng nhập Telegram thành công!', 'success');
                    startDashboardPolling();
                    return true;
                }} else {{
                    if (!silent && errBox && errText) {{
                        errText.textContent = data.message || 'Xác thực Telegram thất bại!';
                        errBox.classList.remove('hidden');
                    }}
                    return false;
                }}
            }} catch (err) {{
                if (!silent && errBox && errText) {{
                    errText.textContent = 'Lỗi kết nối Telegram WebApp: ' + err.message;
                    errBox.classList.remove('hidden');
                }}
                return false;
            }}
        }}

        async function logoutDashboard() {{
            try {{
                await originalFetch('/api/logout', {{ method: 'POST' }});
            }} catch(e) {{}}



            const profileWidget = document.getElementById('user-profile-widget');
            if (profileWidget) {{
                profileWidget.classList.add('hidden');
                profileWidget.classList.remove('flex');
            }}

            stopDashboardPolling();
            showLoginModal();
            showToast('Đã đăng xuất khỏi Terminal.', 'info');
        }}

        function updateUserUI(username) {{
            const profileWidget = document.getElementById('user-profile-widget');
            const userLabel = document.getElementById('header-username');
            if (profileWidget) {{
                profileWidget.classList.remove('hidden');
                profileWidget.classList.add('flex');
            }}
            if (userLabel) userLabel.textContent = username || 'admin';
        }}

        async function checkInitialAuth() {{

            // 2. Kiểm tra nếu đang chạy trong Telegram WebApp
            const tg = window.Telegram?.WebApp;
            if (tg) {{
                try {{
                    tg.ready();
                    tg.expand();
                    if (tg.requestFullscreen) tg.requestFullscreen();
                    if (tg.disableVerticalSwipes) tg.disableVerticalSwipes();
                }} catch(e) {{}}

                if (tg.initData) {{
                    const tgCard = document.getElementById('tg-webapp-card');
                    const tgDivider = document.getElementById('login-divider');
                    const tgGreeting = document.getElementById('tg-user-greeting');
                    if (tgCard) tgCard.classList.remove('hidden');
                    if (tgDivider) tgDivider.classList.remove('hidden');

                    if (tg.initDataUnsafe?.user) {{
                        const u = tg.initDataUnsafe.user;
                        if (tgGreeting) tgGreeting.textContent = 'Chào ' + (u.first_name || u.username || 'Admin') + ' (ID: ' + u.id + ')';
                    }}

                    const autoOk = await loginWithTelegramWebApp(true);
                    if (autoOk) return;
                }}
            }}

            try {{
            // 3. Kiểm tra tính hợp lệ với server qua /api/check_auth
                const res = await originalFetch('/api/check_auth', {{ credentials: 'same-origin' }});
                const data = await res.json();
                if (res.ok && data.authenticated) {{
                    hideLoginModal();
                    updateUserUI(data.username || 'admin');
                    startDashboardPolling();
                }} else {{
                    showLoginModal();
                }}
            }} catch(e) {{
                showLoginModal();
            }}
        }}

        function startDashboardPolling() {{
            if (dashboardPollingActive) return;
            dashboardPollingActive = true;

            try {{
                const savedTab = localStorage.getItem('active_dashboard_tab') || 'overview';
                switchDashboardTab(savedTab);
            }} catch(e) {{}}

            const initTasks = [
                fetchStatus, fetchHistory, fetchRadar, updateMascotCommentary,
                fetchFundingVault, () => fetchLiquidationRadar('BTCUSDT'), fetchMacroNews,
                () => fetchOrderFlow('BTCUSDT'), fetchPairsTrading, fetchWhaleTracker,
                fetchCrossBasis, () => fetchSMC('BTCUSDT'), fetchLeadLag, fetchSynthesis,
                fetchRebalancePlan, () => fetchMicrostructure('BTCUSDT'), () => fetchSmartGrid('BTCUSDT'),
                fetchPCABasket, fetchAITraining, fetchSubAccountYield, fetchGeneticEvolution, fetchDigitalTwinStress
            ];
            initTasks.forEach(fn => {{
                try {{ fn(); }} catch(e) {{ console.error('Lỗi nạp khởi động:', e); }}
            }});

            dashboardIntervalIds = [
                setInterval(fetchStatus, 3000),
                setInterval(fetchRadar, 10000),
                setInterval(fetchHistory, 15000),
                setInterval(updateMascotCommentary, 12000),
                setInterval(fetchFundingVault, 30000),
                setInterval(fetchMacroNews, 60000),
                setInterval(() => fetchOrderFlow('BTCUSDT'), 15000),
                setInterval(fetchPairsTrading, 45000),
                setInterval(fetchWhaleTracker, 60000),
                setInterval(fetchCrossBasis, 60000),
                setInterval(() => fetchSMC('BTCUSDT'), 20000),
                setInterval(fetchLeadLag, 15000),
                setInterval(fetchSynthesis, 60000),
                setInterval(fetchRebalancePlan, 60000),
                setInterval(fetchPCABasket, 30000),
                setInterval(fetchAITraining, 30000),
                setInterval(fetchDigitalTwinStress, 45000),
                setInterval(fetchSubAccountYield, 60000),
                setInterval(fetchGeneticEvolution, 60000)
            ];
        }}

        function stopDashboardPolling() {{
            dashboardPollingActive = false;
            dashboardIntervalIds.forEach(id => clearInterval(id));
            dashboardIntervalIds = [];
        }}

        // Khởi động kiểm tra xác thực khi trang tải xong
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', checkInitialAuth);
        }} else {{
            checkInitialAuth();
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(
        content=html_content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

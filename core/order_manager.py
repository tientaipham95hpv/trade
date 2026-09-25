import os
from pathlib import Path
import csv
import json
import time
import math
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from config.settings import BotConfig
from core.binance_client import BinanceFuturesClient
from notifier.telegram_bot import TelegramNotifier
from risk.risk_manager import RiskManager
from core.execution.models import PositionLedgerEntry, PositionOwner

logger = logging.getLogger("OrderManager")

VIETNAM_TZ = timezone(timedelta(hours=7))


class ApplicationStoreFacade:
    """
    Read-only / IPC query facade for Application process.
    Guarantees 0 direct SQLite writers and 0 direct execution.db writers from application.
    All state mutations must be commanded through Execution Service IPC.
    """
    def __init__(self, state_file_path: str, client_getter=None):
        self.state_file = state_file_path
        self.db_path = f"{state_file_path}.db"
        self._client_getter = client_getter

    def set_safety_flag(self, flag: str, value: bool, reason: Optional[str] = None):
        """Application process cannot write safety flags directly to SQLite."""
        logger.info(f"Application safety flag {flag}={value} requested (no direct DB write in app process)")
        return None

    def get_safety_flag(self, flag: str) -> Any:
        client = self._client_getter() if self._client_getter else None
        if client and hasattr(client, "query_status"):
            try:
                status = client.query_status()
                if not status.get("success", False) or status.get("state") == "UNKNOWN":
                    return {"success": False, "state": "UNKNOWN", "error": "EXECUTION_SERVICE_UNAVAILABLE", "value": None}
                return {"success": True, "state": "KNOWN_VALUE", "value": bool(status.get(flag, False))}
            except Exception:
                pass
        return {"success": False, "state": "UNKNOWN", "error": "EXECUTION_SERVICE_UNAVAILABLE", "value": None}

    def is_safety_flag_set(self, flag: str) -> bool:
        res = self.get_safety_flag(flag)
        if isinstance(res, dict) and res.get("state") == "UNKNOWN":
            return True  # Fail-closed: if unknown, treat as active halt/safety condition
        return bool(res.get("value", False)) if isinstance(res, dict) else False
    def is_global_halt(self) -> Tuple[bool, str]:
        client = self._client_getter() if self._client_getter else None
        if client and hasattr(client, "query_status"):
            try:
                status = client.query_status()
                if not status.get("success", False) or status.get("state") == "UNKNOWN":
                    return True, "🚨 Execution Service unreachable / UNKNOWN state (fail-closed)"
                if status.get("global_halt"):
                    return True, status.get("halt_reason", "Global safety halt active in Execution Service")
                return False, ""
            except Exception as e:
                return True, f"🚨 Execution Service query error: {e} (fail-closed)"
        return True, "🚨 No execution service client configured (fail-closed)"

    def get_positions(self) -> Dict[str, Any]:
        client = self._client_getter() if self._client_getter else None
        if client and hasattr(client, "query_positions"):
            try:
                res = client.query_positions()
                if isinstance(res, dict) and (res.get("state") == "UNKNOWN" or not res.get("success", True)):
                    return {
                        "success": False,
                        "state": "UNKNOWN",
                        "error": "EXECUTION_SERVICE_UNAVAILABLE",
                        "positions": None,
                    }
                return res
            except Exception as e:
                logger.error(f"get_positions query failed: {e}")
        return {
            "success": False,
            "state": "UNKNOWN",
            "error": "EXECUTION_SERVICE_UNAVAILABLE",
            "positions": None,
        }

    def get_position(self, symbol: str) -> Any:
        positions = self.get_positions()
        if isinstance(positions, dict) and (positions.get("state") == "UNKNOWN" or not positions.get("success", True)):
            return {"success": False, "state": "UNKNOWN", "error": "EXECUTION_SERVICE_UNAVAILABLE", "position": None}
        if isinstance(positions, dict):
            return positions.get(symbol)
        return {"success": False, "state": "UNKNOWN", "error": "EXECUTION_SERVICE_UNAVAILABLE", "position": None}

    def get_pending_orders(self) -> Any:
        client = self._client_getter() if self._client_getter else None
        if client and hasattr(client, "query_intents"):
            try:
                res = client.query_intents()
                if isinstance(res, dict) and (res.get("state") == "UNKNOWN" or not res.get("success", True)):
                    return {"success": False, "state": "UNKNOWN", "error": "EXECUTION_SERVICE_UNAVAILABLE", "intents": None}
                if isinstance(res, dict) and "intents" in res:
                    return res.get("intents", [])
                if isinstance(res, list):
                    return res
            except Exception:
                pass
        return {"success": False, "state": "UNKNOWN", "error": "EXECUTION_SERVICE_UNAVAILABLE", "intents": None}

    def load_circuit_breaker(self) -> Dict[str, Any]:
        client = self._client_getter() if self._client_getter else None
        if client and hasattr(client, "query_circuit_breaker"):
            try:
                res = client.query_circuit_breaker()
                if isinstance(res, dict) and res.get("success"):
                    return res.get("circuit_breaker", res)
                return {
                    "success": False,
                    "state": "UNKNOWN",
                    "error": "EXECUTION_SERVICE_UNAVAILABLE",
                    "circuit_breaker_triggered": True,
                }
            except Exception:
                pass
        return {
            "success": False,
            "state": "UNKNOWN",
            "error": "EXECUTION_SERVICE_UNAVAILABLE",
            "circuit_breaker_triggered": True,
        }

    def get_circuit_breaker_state(self) -> Tuple[bool, float]:
        cb = self.load_circuit_breaker()
        return bool(cb.get("circuit_breaker_triggered", True)), float(cb.get("cooldown_until", 0.0))

    def is_circuit_breaker_active(self) -> bool:
        triggered, _ = self.get_circuit_breaker_state()
        return triggered

    def save_circuit_breaker(self, *args, **kwargs):
        """Application process cannot write circuit breaker state directly to DB."""
        pass

    def commit_position(self, *args, **kwargs):
        """Application process cannot commit positions to execution DB."""
        pass

    def remove_position(self, *args, **kwargs):
        """Application process cannot remove positions from execution DB."""
        pass

    def update_position(self, *args, **kwargs):
        """Application process cannot update positions in execution DB."""
        pass

    def update_intent_state(self, *args, **kwargs):
        """Application process cannot update intent states in execution DB."""
        pass

    def reserve_symbol_and_capital(self, *args, **kwargs):
        """Application process cannot reserve symbol/capital directly."""
        return False, None, None, "Application has no reservation write authority"

    def release_reservation(self, *args, **kwargs):
        pass

    def process_receipt(self, *args, **kwargs):
        pass


class OrderManager:
    """
    Module Quản lý Vòng Đời Lệnh Nâng Cao (Pure IPC Facade):
    - Toàn bộ thao tác giao dịch (Open/Close/Panic) đều ủy quyền qua Execution Service IPC.
    - Zero local ExecutionEngine, zero execution.db direct writers/readers trong Application.
    """

    def __init__(self, config: BotConfig, client: BinanceFuturesClient, notifier: TelegramNotifier):
        self.config = config
        self.client = client
        self.notifier = notifier
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        if hasattr(self.config, "__dict__"):
            self.config.active_positions = self.active_positions
        self.trade_history: List[Dict[str, Any]] = []
        self.last_known_balance: float = 1000.0
        self._order_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._state_version = 0
        self._pending_symbols = set()
        self._pending_margin = 0.0
        self.recovery_required = False

        state_file_path = getattr(self.config, "state_file", "bot_state.json")
        self._state_file_path = state_file_path

        # Application Process: 0 local execution engine, 0 execution DB writers
        self.execution_engine = None

        # IPC Client to Execution Service
        from core.execution_service.client import ExecutionServiceClient
        svc_port = getattr(self.config, "execution_service_port", 50051)
        svc_host = getattr(self.config, "execution_service_host", "127.0.0.1")
        svc_token = getattr(self.config, "ipc_token_strategy", "")
        if svc_token:
            self.execution_service_client = ExecutionServiceClient(
                host=svc_host, port=svc_port, auth_token=svc_token, principal="strategy-client"
            )
        else:
            logger.error("Execution Service strategy credential is not configured; mutations are disabled")
            self.execution_service_client = None

        # Store facade: read-only/IPC queries, zero direct DB writing
        self.store = ApplicationStoreFacade(state_file_path, client_getter=self._get_service_client)
        self.execution_store = self.store
        self.risk_manager = RiskManager(self.config)
        self.coordinator = None

        # Dọn dẹp file lock của chính bot cũ bị crash
        try:
            state_dir = os.path.dirname(os.path.abspath(state_file_path))
            bot_lock = os.path.join(state_dir, "order_manager.lock")
            if os.path.exists(bot_lock):
                try:
                    os.remove(bot_lock)
                except Exception:
                    pass
        except Exception:
            pass

        # Tự động nạp trạng thái đã lưu trước đó nếu có
        saved_bal = self.load_state()
        if saved_bal is not None:
            self.last_known_balance = float(saved_bal)

        # Đối soát vị thế với sàn khi khởi động (Startup Reconciliation)
        self.reconcile_with_exchange()
        self.save_state()

    def _get_service_client(self):
        try:
            import sys
            web_mod = sys.modules.get("web.app")
            if web_mod:
                ctx = getattr(web_mod, "_bot_context", None)
                if ctx and hasattr(ctx, "execution_service_client") and ctx.execution_service_client is not None:
                    return ctx.execution_service_client
        except Exception:
            pass
        return getattr(self, "execution_service_client", None)

    def save_state(self, simulated_balance: Optional[float] = None):
        """Lưu toàn bộ vị thế đang mở và số dư ra file JSON nguyên tử (atomic write) kèm monotonic version guard"""
        target_bal = float(simulated_balance) if simulated_balance is not None else self.last_known_balance
        self.last_known_balance = target_bal

        with self._state_lock:
            self._state_version += 1
            current_version = self._state_version

        try:
            with self._order_lock:
                serializable_positions = {}
                for sym, pos in self.active_positions.items():
                    if not isinstance(pos, dict):
                        continue
                    p_copy = pos.copy()
                    if isinstance(p_copy.get("opened_at"), datetime):
                        p_copy["opened_at"] = p_copy["opened_at"].isoformat()
                    serializable_positions[sym] = p_copy

            pending = self.store.get_pending_orders()

            state_data = {
                "version": current_version,
                "updated_at": datetime.now(VIETNAM_TZ).isoformat(),
                "simulated_balance": target_bal,
                "active_positions": serializable_positions,
                "pending_orders": pending,
                "total_trades_count": len(self.trade_history)
            }

            state_file = os.path.abspath(self.config.state_file)
            state_dir = os.path.dirname(state_file)
            os.makedirs(state_dir, exist_ok=True)
            tmp_file = f"{state_file}.tmp.{os.getpid()}.{threading.get_ident()}.{time.time_ns()}"

            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(state_data, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())

                with self._state_lock:
                    if current_version < self._state_version:
                        try:
                            os.remove(tmp_file)
                        except Exception:
                            pass
                        return
                    replaced = False
                    for _ in range(10):
                        try:
                            os.replace(tmp_file, state_file)
                            replaced = True
                            break
                        except (PermissionError, OSError):
                            time.sleep(0.02)
                    if not replaced:
                        os.replace(tmp_file, state_file)
            except Exception:
                if os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                    except Exception:
                        pass
                raise

            logger.debug("Đã lưu trạng thái hệ thống vào %s", self.config.state_file)
        except Exception as e:
            logger.error("Lỗi khi lưu state: %s", e)

    def load_state(self) -> Optional[float]:
        """Đọc và phục hồi trạng thái từ SQLite (authoritative) và JSON nếu file tồn tại"""
        db_positions = self.store.get_positions()
        if isinstance(db_positions, dict):
            if db_positions.get("state") == "UNKNOWN" or not db_positions.get("success", True):
                self.recovery_required = True
            else:
                for sym, pos in db_positions.items():
                    if sym not in ("success", "state", "error", "positions") and isinstance(pos, dict):
                        self.active_positions[sym] = pos

        if not os.path.exists(self.config.state_file):
            return None

        try:
            content = None
            for _ in range(10):
                try:
                    with open(self.config.state_file, "r", encoding="utf-8") as f:
                        c = f.read()
                        if c.strip():
                            content = c
                            break
                except (PermissionError, OSError):
                    time.sleep(0.02)
            if content is None:
                with open(self.config.state_file, "r", encoding="utf-8") as f:
                    content = f.read()

            if not content.strip():
                logger.debug("File state rỗng (%s).", self.config.state_file)
                return None

            state_data = json.loads(content)

            # Authoritative SQLite owns active positions and pending orders completely.
            # Stale JSON positions/pending_orders must NEVER resurrect into DB or alter runtime safety truth.
            db_pending = self.store.get_pending_orders()
            if any(isinstance(o, dict) and o.get("state") in ("UNKNOWN", "SUBMITTING", "SUBMITTED") for o in db_pending):
                logger.critical("Phát hiện pending orders ở trạng thái UNKNOWN/SUBMITTING trong DB! Đánh dấu recovery_required.")
                self.recovery_required = True
                self.store.set_safety_flag("recovery_required", True)

            logger.info("Đã phục hồi %d vị thế từ SQLite/State", len(self.active_positions))
            return state_data.get("simulated_balance")
        except Exception as e:
            logger.debug("Không thể đọc file state non-authoritative JSON (%s): %s", self.config.state_file, e)
            return None

    def log_trade_to_csv(self, trade: Dict[str, Any]):
        """Ghi nhận nhật ký trade đã đóng ra file CSV"""
        file_path = self.config.trade_history_file
        file_exists = os.path.exists(file_path)

        headers = [
            "timestamp", "symbol", "side", "entry_price", "exit_price",
            "qty", "margin_usdt", "pnl_usdt", "pnl_percent", "exit_reason"
        ]

        try:
            with open(file_path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(headers)

                closed_at_val = trade.get("closed_at")
                if isinstance(closed_at_val, datetime):
                    if closed_at_val.tzinfo is None:
                        closed_at_val = closed_at_val.replace(tzinfo=timezone.utc).astimezone(VIETNAM_TZ)
                    else:
                        closed_at_val = closed_at_val.astimezone(VIETNAM_TZ)
                    closed_at_str = closed_at_val.strftime("%Y-%m-%d %H:%M:%S (VN)")
                elif isinstance(closed_at_val, str) and closed_at_val.strip():
                    closed_at_str = closed_at_val.strip()
                    if "(VN)" not in closed_at_str:
                        closed_at_str = f"{closed_at_str} (VN)"
                else:
                    closed_at_str = datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d %H:%M:%S (VN)")

                writer.writerow([
                    closed_at_str,
                    trade.get("symbol", ""),
                    trade.get("side", ""),
                    f"{trade.get('entry_price', 0):.4f}",
                    f"{trade.get('exit_price', 0):.4f}",
                    f"{trade.get('qty', 0):.4f}",
                    f"{trade.get('margin', 0):.2f}",
                    f"{trade.get('pnl_usdt', 0):+.2f}",
                    f"{trade.get('pnl_percent', 0):+.2f}%",
                    trade.get("exit_reason", "")
                ])
            logger.info("Đã ghi nhận giao dịch %s vào %s", trade.get("symbol"), file_path)

            if not getattr(self.config, "dry_run", False):
                try:
                    from core.ai_trade_trainer import AITradeTrainer
                    def _bg_train():
                        try:
                            AITradeTrainer().train_from_history()
                        except Exception:
                            pass
                    threading.Thread(target=_bg_train, daemon=True, name="AIAutoTrainThread").start()
                except Exception:
                    pass
        except Exception as e:
            logger.error("Lỗi khi ghi trade ra CSV: %s", e)

    def get_open_position_count(self) -> int:
        return len(self.active_positions)

    def _broadcast_to_clients(self, action: str, **kwargs):
        """Phân bổ lệnh đồng thời tới các tài khoản Copy-Trade phi lưu ký"""
        try:
            from core.order_multiplexer import get_order_multiplexer
            mux = get_order_multiplexer(use_testnet=getattr(self.config, "use_testnet", False))
            payload = {"action": action, **kwargs}
            mux.broadcast_order_to_clients(payload)
        except Exception as e:
            logger.debug("Không thể phân bổ lệnh %s tới copy clients: %s", action, e)

    def execute_entry(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        qty: float,
        stop_loss: float,
        take_profit: float,
        margin: float,
        risk_amount: float = 0.0,
        leverage: Optional[int] = None,
        ai_score: Optional[float] = None,
        simulated_balance_holder: Optional[Dict[str, Any]] = None,
        source: str = "strategy",
        **kwargs
    ) -> bool:
        """
        Pure IPC facade: routes all entry submissions exclusively to Execution Service.
        Fails closed with zero local fallback if service is down or unavailable.
        """
        if getattr(self.config, "dry_run", False) or getattr(self.client, "is_dry_run", False):
            self.active_positions[symbol] = {
                "symbol": symbol,
                "side": side,
                "entry_price": entry_price,
                "qty": qty,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "margin": margin,
                "leverage": leverage or getattr(self.config, "leverage", 5),
                "tp1_done": False,
                "tp2_done": False,
                "partial_tp_activated": False,
                "breakeven_activated": False,
            }
            self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)
            self._broadcast_to_clients("OPEN", symbol=symbol, side=side, entry_price=entry_price, stop_loss=stop_loss, take_profit=take_profit, margin=margin, leverage=(leverage or getattr(self.config, "leverage", 5)), qty=qty)
            return True
        client = self._get_service_client()
        if client is None:
            logger.error(f"🚨 [HARD CUTOVER] Execution Service client unavailable. Rejecting entry for {symbol}.")
            return False

        effective_leverage = leverage or getattr(self.config, "leverage", 5)
        hard_cap = getattr(self.config, "real_trading_hard_cap", 0.0) if not getattr(self.config, "dry_run", False) else 1000.0
        if hard_cap <= 0:
            hard_cap = 1000.0

        try:
            command_id = kwargs.get("command_id")
            res = client.open_position(
                symbol=symbol,
                side=side,
                qty=qty,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                leverage=effective_leverage,
                total_capital=hard_cap,
                source=source,
                command_id=command_id,
            )
            if res and res.success:
                logger.info(f"✅ Entry for {symbol} submitted via Execution Service (Receipt: {res.execution_receipt_id})")
                self._broadcast_to_clients("OPEN", command_id=res.command_id, symbol=symbol, side=side, entry_price=entry_price, stop_loss=stop_loss, take_profit=take_profit, margin=margin, leverage=effective_leverage, qty=qty)
                return True
            err = res.error if res else "Unknown IPC failure"
            logger.warning(f"❌ Execution Service rejected entry for {symbol}: {err}")
            return False
        except Exception as e:
            logger.error(f"Error communicating with Execution Service: {e}")
            return False

    def check_and_update_positions(self, current_prices: Dict[str, float], simulated_balance_holder: Optional[Dict[str, float]] = None):
        """Kiểm tra và cập nhật các vị thế đang chạy, chốt lời từng phần và dời Stop Loss về Breakeven"""
        # 1. Đối soát các lệnh khớp trễ từ sàn
        try:
            ex_pos_list = self.client.get_open_positions()
            if ex_pos_list is None:
                logger.error("Periodic positions query returned None (outage). Activating global halt.")
                self.store.set_safety_flag("global_halt", True)
                self.recovery_required = True
                return
            if isinstance(ex_pos_list, list):
                ex_map = {
                    p.get("symbol"): abs(float(p.get("positionAmt", p.get("amount", 0.0))))
                    for p in ex_pos_list if isinstance(p, dict)
                }
                for s, p in list(self.active_positions.items()):
                    ex_q = ex_map.get(s, 0.0)
                    if ex_q > p.get("qty", 0.0):
                        p["qty"] = ex_q
                        p["margin"] = ex_q * p.get("entry_price", 100.0) / p.get("leverage", 5)
                        self.store.commit_position(
                            s, p["side"], ex_q, p["entry_price"], p["margin"],
                            p.get("leverage", 5), p.get("stop_loss"), p.get("take_profit")
                        )
        except Exception as e:
            logger.error("Periodic positions query failed: %s. Activating global halt.", e)
            self.store.set_safety_flag("global_halt", True)
            self.recovery_required = True
            return

        for symbol, pos in list(self.active_positions.items()):
            if pos.get("owner") in ("EXTERNAL", "MANUAL_EXTERNAL", "UNKNOWN_EXTERNAL") or pos.get("owner_type") in ("EXTERNAL", "MANUAL_EXTERNAL", "UNKNOWN_EXTERNAL"):
                continue

            cur_price = current_prices.get(symbol)
            if not cur_price or cur_price <= 0:
                continue

            entry = pos["entry_price"]
            is_short = pos["side"] in ["SELL", "SHORT"]
            exit_side = "BUY" if is_short else "SELL"

            # Kiểm tra Take Profit 1 (Chốt lời 1R / 50% hoặc Multi-TP)
            r_distance = abs(entry - pos.get("initial_sl", pos["stop_loss"]))
            is_multi_tp = getattr(self.config, "enable_multi_stage_tp", True) and getattr(self.config, "use_multi_tp", True)
            use_partial = getattr(self.config, "use_partial_tp", True)
            tp_ratio = 0.33 if is_multi_tp else getattr(self.config, "partial_tp_ratio", 0.5)

            tp1_target = (entry - r_distance) if is_short else (entry + r_distance)
            hit_tp1 = use_partial and ((cur_price <= tp1_target) if is_short else (cur_price >= tp1_target))

            should_do_tp1 = False
            with self._order_lock:
                if hit_tp1 and not pos.get("tp1_done", False) and not pos.get("tp1_submitting", False):
                    pos["tp1_submitting"] = True
                    should_do_tp1 = True

            if should_do_tp1:
                try:
                    step_size = 0.01
                    filter_info = self.client.get_symbol_filter_info(symbol) if hasattr(self.client, "get_symbol_filter_info") else None
                    if filter_info and filter_info.get("step_size"):
                        step_size = float(filter_info["step_size"])

                    orig_q = pos.get("orig_qty", pos.get("initial_qty", pos["qty"]))
                    close_qty = RiskManager._round_step_size(orig_q * tp_ratio, step_size)
                    if close_qty <= 0 or close_qty >= pos["qty"]:
                        close_qty = RiskManager._round_step_size(pos["qty"] * tp_ratio, step_size)
                    if close_qty <= 0:
                        close_qty = RiskManager._round_step_size(pos["qty"], step_size)

                    order_res = None
                    if getattr(self.config, "dry_run", False):
                        order_res = {"orderId": "sim-tp1", "status": "FILLED", "executedQty": str(close_qty), "avgPrice": str(cur_price)}
                    else:
                        _ipc = self._get_service_client()
                        if _ipc is not None:
                            try:
                                _res = _ipc.close_position(symbol=symbol, qty=close_qty, reason="TP1", source="order_manager")
                                if _res and _res.success:
                                    order_res = {"orderId": _res.execution_receipt_id, "status": "FILLED", "executedQty": str(close_qty), "avgPrice": str(cur_price)}
                            except Exception:
                                order_res = None

                    # Chống xử lý receipt trùng lặp
                    receipt_id = order_res.get("orderId") if isinstance(order_res, dict) else None
                    if receipt_id and pos.get("last_tp_order_id") == receipt_id:
                        continue
                    pos["last_tp_order_id"] = receipt_id

                    actual_tp_qty = 0.0
                    if isinstance(order_res, dict):
                        status = order_res.get("status")
                        if status not in ("REJECTED",):
                            try:
                                q_val = float(order_res.get("executedQty", 0.0))
                                if math.isfinite(q_val) and q_val > 0:
                                    actual_tp_qty = q_val
                            except Exception:
                                pass

                    cur_ex_qty = pos["qty"]
                    if not self.config.dry_run:
                        try:
                            ex_pos = self.client.get_open_positions()
                        except TypeError:
                            ex_pos = self.client.get_open_positions(symbol)
                        except Exception:
                            ex_pos = None

                        if isinstance(ex_pos, list):
                            for p in ex_pos:
                                if isinstance(p, dict) and p.get("symbol") == symbol:
                                    cur_ex_qty = abs(float(p.get("positionAmt", p.get("amount", 0.0))))
                                    actual_tp_qty = max(0.0, pos["qty"] - cur_ex_qty)
                                    break
                        elif actual_tp_qty > 0:
                            cur_ex_qty = max(0.0, pos["qty"] - actual_tp_qty)
                        else:
                            cur_ex_qty = pos["qty"]
                    else:
                        cur_ex_qty = max(0.0, pos["qty"] - close_qty)
                        actual_tp_qty = close_qty

                    applied_delta = max(0.0, pos["qty"] - cur_ex_qty)
                    if applied_delta > 0:
                        pos["qty"] = cur_ex_qty
                        pos["margin"] = (cur_ex_qty * entry) / pos.get("leverage", 5)

                        fill_p = None
                        if not self.config.dry_run:
                            if hasattr(self.client, "client") and hasattr(self.client.client, "events"):
                                fills = [e for e in self.client.client.events("fill") if e.get("symbol") == symbol]
                                if fills:
                                    fill_p = float(fills[-1].get("price", 0.0))
                            if (fill_p is None or fill_p <= 0) and isinstance(order_res, dict) and order_res.get("avgPrice"):
                                try:
                                    fill_p = float(order_res["avgPrice"])
                                except Exception:
                                    pass
                            if fill_p is None or fill_p <= 0:
                                try:
                                    fill_p = float(self.client.get_symbol_price(symbol))
                                except Exception:
                                    fill_p = float(cur_price)
                        else:
                            fill_p = float(cur_price)

                        pnl = applied_delta * (fill_p - entry) * (-1 if is_short else 1)
                        if simulated_balance_holder and isinstance(simulated_balance_holder, dict):
                            simulated_balance_holder["balance"] = simulated_balance_holder.get("balance", 1000.0) + pnl
                            self.last_known_balance = simulated_balance_holder["balance"]

                        part_margin = (applied_delta * entry) / pos.get("leverage", 5)
                        part_pct = (pnl / part_margin * 100.0) if part_margin > 0 else 0.0
                        self.log_trade_to_csv({
                            "symbol": symbol,
                            "side": pos["side"],
                            "entry_price": entry,
                            "exit_price": fill_p,
                            "qty": applied_delta,
                            "margin": round(part_margin, 2),
                            "pnl_usdt": round(pnl, 2),
                            "pnl_percent": round(part_pct, 2),
                            "closed_at": datetime.now(VIETNAM_TZ),
                            "exit_reason": "Chốt lời 50% (TP1 @ 1R)"
                        })

                        # Dời Stop Loss về Breakeven
                        new_sl = None
                        if getattr(self.config, "dry_run", False):
                            new_sl = entry
                        else:
                            _ipc = self._get_service_client()
                            if _ipc is not None:
                                try:
                                    _res = _ipc.place_or_update_sl(symbol=symbol, stop_loss_price=entry, source="order_manager")
                                    if _res and _res.success:
                                        new_sl = entry
                                except Exception:
                                    new_sl = None

                        if new_sl or self.config.dry_run:
                            pos["stop_loss"] = entry
                            pos["breakeven_activated"] = True

                        pos["tp1_done"] = True
                        pos["partial_tp_activated"] = True
                        self.store.update_position(symbol, qty=pos["qty"], margin=pos["margin"], stop_loss=pos["stop_loss"], tp1_done=1)
                        self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)
                        self._broadcast_to_clients("PARTIAL_TP", symbol=symbol, side=exit_side, ratio=tp_ratio, price=cur_price)
                    else:
                        pos["tp1_done"] = False
                finally:
                    with self._order_lock:
                        pos["tp1_submitting"] = False

            # Kiểm tra Take Profit 2 (Chốt lời Nấc 2: 2R cho Multi-TP)
            if is_multi_tp and use_partial and pos.get("tp1_done", False) and not pos.get("tp2_done", False):
                tp2_target = (entry - 2.0 * r_distance) if is_short else (entry + 2.0 * r_distance)
                hit_tp2 = (cur_price <= tp2_target) if is_short else (cur_price >= tp2_target)
                should_do_tp2 = False
                with self._order_lock:
                    if hit_tp2 and not pos.get("tp2_submitting", False):
                        pos["tp2_submitting"] = True
                        should_do_tp2 = True

                if should_do_tp2:
                    try:
                        step_size = 0.01
                        filter_info = self.client.get_symbol_filter_info(symbol) if hasattr(self.client, "get_symbol_filter_info") else None
                        if filter_info and filter_info.get("step_size"):
                            step_size = float(filter_info["step_size"])

                        orig_q = pos.get("orig_qty", pos.get("initial_qty", pos["qty"]))
                        close_qty = RiskManager._round_step_size(orig_q * 0.33, step_size)
                        if close_qty <= 0 or close_qty >= pos["qty"]:
                            close_qty = RiskManager._round_step_size(pos["qty"] * 0.5, step_size)
                        if close_qty <= 0:
                            close_qty = RiskManager._round_step_size(pos["qty"], step_size)

                        order_res = None
                        if getattr(self.config, "dry_run", False):
                            order_res = {"orderId": "sim-tp2", "status": "FILLED", "executedQty": str(close_qty), "avgPrice": str(cur_price)}
                        else:
                            _ipc = self._get_service_client()
                            if _ipc is not None:
                                try:
                                    _res = _ipc.close_position(symbol=symbol, qty=close_qty, reason="TP2", source="order_manager")
                                    if _res and _res.success:
                                        order_res = {"orderId": _res.execution_receipt_id, "status": "FILLED", "executedQty": str(close_qty), "avgPrice": str(cur_price)}
                                except Exception:
                                    order_res = None

                        actual_tp2_qty = 0.0
                        if isinstance(order_res, dict):
                            status = order_res.get("status")
                            if status not in ("REJECTED",):
                                try:
                                    q_val = float(order_res.get("executedQty", 0.0))
                                    if math.isfinite(q_val) and q_val > 0:
                                        actual_tp2_qty = q_val
                                except Exception:
                                    pass

                        cur_ex_qty = pos["qty"]
                        if not self.config.dry_run:
                            try:
                                ex_pos = self.client.get_open_positions()
                            except TypeError:
                                ex_pos = self.client.get_open_positions(symbol)
                            except Exception:
                                ex_pos = None

                            if isinstance(ex_pos, list):
                                for p in ex_pos:
                                    if isinstance(p, dict) and p.get("symbol") == symbol:
                                        cur_ex_qty = abs(float(p.get("positionAmt", p.get("amount", 0.0))))
                                        actual_tp2_qty = max(0.0, pos["qty"] - cur_ex_qty)
                                        break
                            elif actual_tp2_qty > 0:
                                cur_ex_qty = max(0.0, pos["qty"] - actual_tp2_qty)
                            else:
                                cur_ex_qty = pos["qty"]
                        else:
                            cur_ex_qty = max(0.0, pos["qty"] - close_qty)
                            actual_tp2_qty = close_qty

                        applied_delta = max(0.0, pos["qty"] - cur_ex_qty)
                        if applied_delta > 0:
                            pos["qty"] = cur_ex_qty
                            pos["margin"] = (cur_ex_qty * entry) / pos.get("leverage", 5)

                            fill_p = None
                            if isinstance(order_res, dict) and order_res.get("avgPrice"):
                                try:
                                    fill_p = float(order_res["avgPrice"])
                                except Exception:
                                    pass
                            if fill_p is None or fill_p <= 0:
                                sdk_obj = getattr(self.client, "client", None)
                                ledger_obj = getattr(sdk_obj, "_ledger", sdk_obj)
                                if hasattr(ledger_obj, "events"):
                                    fills = [e for e in ledger_obj.events("fill") if e.get("symbol") == symbol and e.get("reduce")]
                                    if fills:
                                        fill_p = float(fills[-1].get("price", 0.0))
                            if fill_p is None or fill_p <= 0:
                                fill_p = float(cur_price)

                            pnl = applied_delta * (fill_p - entry) * (-1 if is_short else 1)
                            if simulated_balance_holder and isinstance(simulated_balance_holder, dict):
                                simulated_balance_holder["balance"] = simulated_balance_holder.get("balance", 1000.0) + pnl
                                self.last_known_balance = simulated_balance_holder["balance"]

                            new_sl = round(entry - r_distance, 4) if is_short else round(entry + r_distance, 4)
                            sl_placed = False
                            if getattr(self.config, "dry_run", False):
                                sl_placed = True
                            else:
                                _ipc = self._get_service_client()
                                if _ipc is not None:
                                    try:
                                        _res = _ipc.place_or_update_sl(symbol=symbol, stop_loss_price=new_sl, source="order_manager")
                                        if _res and _res.success:
                                            sl_placed = True
                                    except Exception:
                                        sl_placed = False

                            if sl_placed:
                                pos["stop_loss"] = new_sl
                            pos["tp2_done"] = True
                            self.store.update_position(symbol, qty=pos["qty"], margin=pos["margin"], stop_loss=pos["stop_loss"], tp2_done=1)
                            self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)
                        else:
                            pos["tp2_done"] = False
                    finally:
                        with self._order_lock:
                            pos["tp2_submitting"] = False

            # Dynamic Trailing Stop
            if getattr(self.config, "use_trailing_stop", False):
                activation_dist = r_distance * getattr(self.config, "trailing_activation_rr", 1.5)
                step_ratio = getattr(self.config, "trailing_step_percent", 1.0) / 100.0

                if not is_short and cur_price >= entry + activation_dist:
                    step_dist = cur_price * step_ratio
                    new_sl = round(cur_price - step_dist, 4)
                    if new_sl > pos["stop_loss"]:
                        sl_placed = False
                        if getattr(self.config, "dry_run", False):
                            sl_placed = True
                        else:
                            _ipc = self._get_service_client()
                            if _ipc is not None:
                                try:
                                    _res = _ipc.place_or_update_sl(symbol=symbol, stop_loss_price=new_sl, source="order_manager")
                                    if _res and _res.success:
                                        sl_placed = True
                                except Exception:
                                    sl_placed = False
                        if sl_placed:
                            pos["stop_loss"] = new_sl
                            pos["trailing_active"] = True
                            self.store.update_position(symbol, stop_loss=new_sl)
                            self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)

                elif is_short and cur_price <= entry - activation_dist:
                    step_dist = cur_price * step_ratio
                    new_sl = round(cur_price + step_dist, 4)
                    if new_sl < pos["stop_loss"]:
                        sl_placed = False
                        if getattr(self.config, "dry_run", False):
                            sl_placed = True
                        else:
                            _ipc = self._get_service_client()
                            if _ipc is not None:
                                try:
                                    _res = _ipc.place_or_update_sl(symbol=symbol, stop_loss_price=new_sl, source="order_manager")
                                    if _res and _res.success:
                                        sl_placed = True
                                except Exception:
                                    sl_placed = False
                        if sl_placed:
                            pos["stop_loss"] = new_sl
                            pos["trailing_active"] = True
                            self.store.update_position(symbol, stop_loss=new_sl)
                            self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)

        # Kiểm tra Take Profit hoặc Stop Loss cuối cùng (Dry Run)
        for symbol, pos in list(self.active_positions.items()):
            cur_price = current_prices.get(symbol)
            if not cur_price or cur_price <= 0:
                continue
            entry = pos["entry_price"]
            is_short = pos["side"] in ["SELL", "SHORT"]
            if self.config.dry_run and symbol in self.active_positions:
                tp_val = pos.get("take_profit")
                sl_val = pos.get("stop_loss")
                is_hit_tp = False
                is_hit_sl = False

                if not is_short:
                    if tp_val and cur_price >= tp_val:
                        is_hit_tp = True
                    elif sl_val and cur_price <= sl_val:
                        is_hit_sl = True
                else:
                    if tp_val and cur_price <= tp_val:
                        is_hit_tp = True
                    elif sl_val and cur_price >= sl_val:
                        is_hit_sl = True

                if is_hit_tp or is_hit_sl:
                    exit_price = tp_val if is_hit_tp else sl_val
                    rem_qty = pos["qty"]
                    pnl_usdt = (exit_price - entry) * rem_qty * (-1 if is_short else 1)
                    pnl_pct = (pnl_usdt / pos["margin"] * 100.0) if pos.get("margin", 0.0) > 0 else 0.0

                    if simulated_balance_holder and isinstance(simulated_balance_holder, dict):
                        simulated_balance_holder["balance"] = simulated_balance_holder.get("balance", 1000.0) + pnl_usdt
                        self.last_known_balance = simulated_balance_holder["balance"]

                    exit_reason = "Chốt Lời Toàn Phần (Final TP)" if is_hit_tp else "Cắt Lỗ (Stop Loss)"
                    self.log_trade_to_csv({
                        "symbol": symbol,
                        "side": pos["side"],
                        "entry_price": entry,
                        "exit_price": exit_price,
                        "qty": rem_qty,
                        "margin": round(pos.get("margin", 0.0), 2),
                        "pnl_usdt": round(pnl_usdt, 2),
                        "pnl_percent": round(pnl_pct, 2),
                        "closed_at": datetime.now(VIETNAM_TZ),
                        "exit_reason": exit_reason
                    })
                    self.active_positions.pop(symbol, None)
                    self.store.remove_position(symbol)
                    self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)
                    self._broadcast_to_clients("CLOSE", symbol=symbol, exit_price=exit_price, reason=exit_reason)

    def close_single_position(
        self,
        symbol: str,
        current_prices: Optional[Dict[str, float]] = None,
        simulated_balance_holder: Optional[Dict[str, float]] = None,
        reason: str = "Thủ công",
        source: str = "order_manager",
        command_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Pure IPC facade for closing single position via Execution Service."""
        client = self._get_service_client()
        if client is None:
            return {"success": False, "message": "Execution Service unavailable (Hard Cutover)"}

        try:
            res = client.close_position(symbol=symbol, reason=reason, source=source, command_id=command_id)
            if res and res.success:
                self.active_positions.pop(symbol, None)
                self.save_state()
                self._broadcast_to_clients("CLOSE", command_id=res.command_id, symbol=symbol, reason=reason)
                return {"success": True, "symbol": symbol, "receipt": res.execution_receipt_id, "message": f"Closed {symbol}"}
            return {"success": False, "message": res.error if res else "Failed to close position"}
        except Exception as e:
            return {"success": False, "message": f"Execution Service exception: {e}"}

    def close_all_positions(
        self,
        current_prices: Optional[Dict[str, float]] = None,
        simulated_balance_holder: Optional[Dict[str, float]] = None,
        reason: str = "Panic close",
        source: str = "order_manager",
        command_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Pure IPC facade for emergency closing all positions via Execution Service."""
        client = self._get_service_client()
        if client is None:
            return {"success": False, "message": "Execution Service unavailable (Hard Cutover)"}

        try:
            res = client.emergency_close_all(reason=reason, source=source, command_id=command_id)
            if res and res.success:
                self.active_positions.clear()
                self.save_state()
                self._broadcast_to_clients("CLOSE_ALL", command_id=res.command_id, reason=reason)
                return {"success": True, "message": "All positions closed via Execution Service", "receipt": res.execution_receipt_id}
            return {"success": False, "message": res.error if res else "Failed panic close"}
        except Exception as e:
            return {"success": False, "message": f"Execution Service exception: {e}"}

    def reconcile_with_exchange(self, simulated_balance_holder: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Pure IPC facade for reconciliation via Execution Service (no local mutation authority)."""
        client = self._get_service_client()
        if client is not None:
            try:
                res = client.reconcile(source="order_manager")
                if res and res.success:
                    return {"status": "ok", "success": True, "reconciled": []}
                err = res.error if res else "Reconciliation failed"
                return {"status": "error", "success": False, "error": err, "reconciled": []}
            except Exception as e:
                return {"status": "error", "success": False, "error": str(e), "reconciled": []}
        return {"status": "error", "success": False, "error": "EXECUTION_SERVICE_UNAVAILABLE", "reconciled": []}

    def execute_manual_order(
        self,
        symbol: str,
        side: str,
        balance: float,
        risk_percent: Optional[float] = None,
        leverage: Optional[int] = None,
        simulated_balance_holder: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Thực thi đặt lệnh thủ công qua chốt kiểm tra rủi ro tập trung"""
        if hasattr(self, "risk_manager") and self.risk_manager:
            can_open, reason = self.risk_manager.can_open_new_position(len(self.active_positions), balance)
            if not can_open:
                logger.warning("Lệnh thủ công bị từ chối bởi Risk Manager: %s", reason)
                return {"success": False, "message": reason}

        if len(self.active_positions) >= self.config.max_concurrent_positions:
            return {"success": False, "message": f"Đã đạt giới hạn tối đa {self.config.max_concurrent_positions} vị thế cùng lúc!"}

        side = side.upper()
        if side not in ["BUY", "SELL"]:
            return {"success": False, "message": "Chiều lệnh phải là BUY hoặc SELL"}

        # Lấy giá thị trường hiện tại (fail-closed, không fallback về $100)
        cur_price = 0.0
        try:
            p = self.client.get_symbol_price(symbol)
            if isinstance(p, (int, float)) and p > 0:
                cur_price = float(p)
            else:
                ltf_df = self.client.get_klines_df(symbol, interval=self.config.ltf, limit=10)
                if hasattr(ltf_df, "empty") and not ltf_df.empty and "close" in ltf_df.columns:
                    val = float(ltf_df.iloc[-1]["close"])
                    if val > 0:
                        cur_price = val
        except Exception:
            pass

        if cur_price <= 0:
            logger.error("Không thể lấy giá thị trường cho %s. Từ chối đặt lệnh thủ công.", symbol)
            return {"success": False, "message": f"Không thể lấy giá thị trường cho {symbol}"}

        eff_lev = leverage or self.config.leverage
        filter_info = {}
        try:
            filter_info = self.client.get_symbol_filter_info(symbol) if hasattr(self.client, "get_symbol_filter_info") else {}
        except Exception:
            pass

        sl_pct = 0.015
        if side == "BUY":
            stop_loss = round(cur_price * (1 - sl_pct), 4)
            take_profit = round(cur_price * (1 + sl_pct * self.config.risk_reward_ratio), 4)
        else:
            stop_loss = round(cur_price * (1 + sl_pct), 4)
            take_profit = round(cur_price * (1 - sl_pct * self.config.risk_reward_ratio), 4)

        used_risk = risk_percent if (risk_percent and risk_percent > 0) else self.config.risk_per_trade_percent
        risk_amount = balance * (used_risk / 100.0)
        risk_distance = abs(cur_price - stop_loss)
        raw_qty = (risk_amount / risk_distance) if risk_distance > 0 else 0.0

        hard_cap = getattr(self.config, "real_trading_hard_cap", 0.0)
        current_total_margin = sum(p.get("margin", 0.0) for p in self.active_positions.values())
        max_margin = balance
        if hard_cap and hard_cap > 0:
            remaining_cap = hard_cap - current_total_margin
            if remaining_cap <= 0:
                return {"success": False, "message": "Đã đạt giới hạn Hard Cap tổng ký quỹ"}
            max_margin = min(max_margin, remaining_cap)

        calculated_margin = (raw_qty * cur_price) / eff_lev
        if calculated_margin > max_margin:
            calculated_margin = max_margin
            raw_qty = (calculated_margin * eff_lev) / cur_price
            risk_amount = raw_qty * risk_distance

        step = float(filter_info.get("step_size", 0.001) or 0.001)
        qty = RiskManager._round_step_size(raw_qty, step)
        min_qty = float(filter_info.get("min_qty", 0.001) or 0.001)
        if qty < min_qty:
            qty = min_qty

        final_margin = (qty * cur_price) / eff_lev
        if final_margin > balance:
            logger.warning("Khối lượng tối thiểu yêu cầu margin (%s) vượt quá số dư (%s)", final_margin, balance)
            return {"success": False, "message": f"Ký quỹ {final_margin:.2f} vượt quá số dư khả dụng {balance:.2f}"}

        success = self.execute_entry(
            symbol=symbol,
            side=side,
            entry_price=cur_price,
            qty=qty,
            stop_loss=stop_loss,
            take_profit=take_profit,
            margin=final_margin,
            risk_amount=risk_amount,
            leverage=eff_lev,
            simulated_balance_holder=simulated_balance_holder
        )

        return {
            "success": success,
            "order": {
                "symbol": symbol,
                "side": side,
                "entry_price": cur_price,
                "qty": qty,
                "margin": final_margin,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "leverage": eff_lev
            } if success else None,
            "symbol": symbol,
            "side": side,
            "entry_price": cur_price,
            "qty": qty,
            "margin": final_margin,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "leverage": eff_lev
        }

    def get_symbol_performance_breakdown(self) -> Dict[str, Any]:
        """Thống kê chi tiết lãi/lỗ và tỷ lệ thắng theo từng cặp coin"""
        history_file = self.config.trade_history_file
        if not os.path.exists(history_file):
            return {"by_symbol": {}, "best_symbol": None, "worst_symbol": None, "max_win_streak": 0, "max_loss_streak": 0, "total_closed": 0}

        by_sym: Dict[str, Dict[str, Any]] = {}
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                for r in reader:
                    sym = r.get("symbol", "UNKNOWN")
                    try:
                        pnl = float(r.get("pnl_usdt", 0.0))
                    except Exception:
                        pnl = 0.0

                    if sym not in by_sym:
                        by_sym[sym] = {"trades": 0, "wins": 0, "losses": 0, "net_pnl": 0.0, "win_rate": 0.0}

                    by_sym[sym]["trades"] += 1
                    by_sym[sym]["net_pnl"] += pnl
                    if pnl > 0:
                        by_sym[sym]["wins"] += 1
                    elif pnl < 0:
                        by_sym[sym]["losses"] += 1

            for sym, st in by_sym.items():
                st["net_pnl"] = round(st["net_pnl"], 2)
                st["win_rate"] = round((st["wins"] / st["trades"] * 100.0) if st["trades"] > 0 else 0.0, 1)

            return {
                "by_symbol": by_sym,
                "total_closed": sum(st["trades"] for st in by_sym.values()),
            }
        except Exception:
            return {"by_symbol": {}, "total_closed": 0}

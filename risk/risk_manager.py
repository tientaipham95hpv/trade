import math
import logging
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional
from config.settings import BotConfig

logger = logging.getLogger("RiskManager")

VIETNAM_TZ = timezone(timedelta(hours=7))

class PositionSizingResult(dict):
    """
    Kết quả tính toán Position Sizing, hỗ trợ cả truy cập dạng Dict:
    sizing["qty"], sizing["margin"], sizing["risk_amount"], sizing["valid"]
    và unpacking dạng Tuple: qty, margin, risk = sizing
    """
    def __iter__(self):
        return iter((self.get("qty", 0.0), self.get("margin", 0.0), self.get("risk_amount", 0.0)))

    @property
    def qty(self) -> float:
        return self.get("qty", 0.0)

    @property
    def margin(self) -> float:
        return self.get("margin", 0.0)

    @property
    def risk_amount(self) -> float:
        return self.get("risk_amount", 0.0)

    @property
    def valid(self) -> bool:
        return self.get("valid", False)


class RiskManager:
    """
    Module Quản trị Rủi ro & Phân bổ Vốn:
    - Tính toán khối lượng vào lệnh động (Position Sizing).
    - Làm tròn số lượng theo stepSize/lotSize của Binance.
    - Kiểm soát sụt giảm tài khoản trong ngày (Max Daily Drawdown).
    - Giới hạn số lượng vị thế mở đồng thời.
    - Chống thất thoát dữ liệu Circuit Breaker xuyên tiến trình / khởi động lại.
    """

    def __init__(self, config: BotConfig, execution_service_client: Optional[Any] = None):
        self.config = config
        self.execution_service_client = execution_service_client
        self.daily_start_balance = 0.0
        self.last_reset_day = None
        self.circuit_breaker_triggered = True
        self._circuit_breaker_until: Optional[datetime] = None
        self.corrupt_circuit_breaker = False
        self.circuit_breaker_state = "UNKNOWN"
        self._load_circuit_breaker()

    @property
    def circuit_breaker_until(self) -> Optional[datetime]:
        self._load_circuit_breaker()
        return self._circuit_breaker_until

    @circuit_breaker_until.setter
    def circuit_breaker_until(self, value: Optional[datetime]):
        """Update display projection only; applications cannot write breaker authority."""
        self._circuit_breaker_until = value
        self.circuit_breaker_triggered = value is not None
        self.circuit_breaker_state = "TRIPPED" if value is not None else "UNKNOWN"

    def _save_circuit_breaker(self):
        """Retained as a no-op for compatibility; breaker authority is service-only."""
        logger.debug("Ignored application breaker persistence request (projection-only)")

    def _load_circuit_breaker(self):
        """Refresh the read-only breaker projection from the Execution Service."""
        client = getattr(self, "execution_service_client", None)
        if client is None or not hasattr(client, "query_circuit_breaker"):
            self.circuit_breaker_state = "UNKNOWN"
            self.circuit_breaker_triggered = True
            self._circuit_breaker_until = None
            return

        try:
            result = client.query_circuit_breaker()
        except Exception:
            result = None
        if not isinstance(result, dict) or not result.get("success"):
            self.circuit_breaker_state = "UNKNOWN"
            self.circuit_breaker_triggered = True
            self._circuit_breaker_until = None
            return

        nested = result.get("circuit_breaker")
        breaker = nested if isinstance(nested, dict) else result
        state_raw = breaker.get("state")
        active_raw = breaker.get("is_active", breaker.get("circuit_breaker_triggered"))
        if not isinstance(state_raw, str) or not isinstance(active_raw, bool):
            self.circuit_breaker_state = "UNKNOWN"
            self.circuit_breaker_triggered = True
            self._circuit_breaker_until = None
            return

        state = state_raw.strip().upper()
        if state not in {"HEALTHY", "TRIPPED"}:
            self.circuit_breaker_state = "UNKNOWN"
            self.circuit_breaker_triggered = True
            self._circuit_breaker_until = None
            return
        cooldown = breaker.get("cooldown_until")
        expired_trip = False
        if state == "TRIPPED" and active_raw is False:
            if isinstance(cooldown, bool) or not isinstance(cooldown, (int, float)):
                self.circuit_breaker_state = "UNKNOWN"
                self.circuit_breaker_triggered = True
                self._circuit_breaker_until = None
                return
            timestamp = float(cooldown)
            expired_trip = math.isfinite(timestamp) and timestamp >= 0 and timestamp <= datetime.now(timezone.utc).timestamp()
        if active_raw != (state == "TRIPPED") and not expired_trip:
            self.circuit_breaker_state = "UNKNOWN"
            self.circuit_breaker_triggered = True
            self._circuit_breaker_until = None
            return

        self.circuit_breaker_state = "HEALTHY" if expired_trip else state
        self.circuit_breaker_triggered = False if expired_trip else active_raw
        self._circuit_breaker_until = None
        cooldown = breaker.get("cooldown_until")
        if cooldown is not None:
            if isinstance(cooldown, bool) or not isinstance(cooldown, (int, float)):
                self.circuit_breaker_state = "UNKNOWN"
                self.circuit_breaker_triggered = True
                return
            timestamp = float(cooldown)
            if not math.isfinite(timestamp) or timestamp < 0:
                self.circuit_breaker_state = "UNKNOWN"
                self.circuit_breaker_triggered = True
                return
            if timestamp > 0:
                self._circuit_breaker_until = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        baseline = breaker.get("daily_baseline_balance", breaker.get("daily_start_balance"))
        if baseline is not None and not isinstance(baseline, bool) and isinstance(baseline, (int, float)):
            parsed = float(baseline)
            if math.isfinite(parsed) and parsed > 0:
                self.daily_start_balance = parsed

    def reset_daily_stats_if_needed(self, current_balance: float):
        """Refresh the service projection; applications never reset authoritative state."""
        del current_balance
        self._load_circuit_breaker()

    def check_circuit_breaker(self, current_balance: float) -> Tuple[bool, str]:
        """Fail closed unless the service explicitly projects a healthy breaker."""
        del current_balance
        self._load_circuit_breaker()
        if self.circuit_breaker_state == "UNKNOWN":
            return False, "CIRCUIT_BREAKER_UNKNOWN: authoritative service sync is unavailable"
        if self.circuit_breaker_state == "TRIPPED":
            if self._circuit_breaker_until:
                return False, (
                    "CIRCUIT_BREAKER_TRIPPED: authoritative cooldown until "
                    f"{self._circuit_breaker_until.isoformat()}"
                )
            return False, "CIRCUIT_BREAKER_TRIPPED: authoritative service has halted entries"
        return True, "Authoritative circuit breaker projection is HEALTHY."

    def is_news_blackout_window(self) -> Tuple[bool, str]:
        """
        Kiểm tra xem thời điểm hiện tại có trùng với khung giờ công bố tin tức vĩ mô lớn của Mỹ hay không:
        - 12:25 - 13:35 UTC: Khung giờ tin CPI, NFP, PPI, GDP, Đơn xin trợ cấp thất nghiệp (8:30 AM EST)
        - 17:55 - 19:05 UTC: Khung giờ công bố Lãi suất FED & Họp báo FOMC (2:00 PM EST)
        - 23:55 - 00:05 UTC: Khung giờ biến động giao phiên ngày mới & Quyết toán Funding Rate
        """
        if not getattr(self.config, "enable_news_filter", False):
            return False, "News filter tắt"

        now_utc = datetime.now(timezone.utc).time()
        current_minute = now_utc.hour * 60 + now_utc.minute

        blackout_intervals = [
            (12 * 60 + 25, 13 * 60 + 35, "Tin tức vĩ mô Mỹ 8:30 AM EST (CPI / NFP / PPI / GDP)"),
            (17 * 60 + 55, 19 * 60 + 5, "Họp báo FED & Quyết định Lãi suất FOMC"),
            (23 * 60 + 55, 24 * 60, "Khung giờ biến động giao phiên ngày mới & Funding Rate (00:00 UTC)"),
            (0, 5, "Khung giờ biến động giao phiên ngày mới & Funding Rate (00:00 UTC)")
        ]

        for start_m, end_m, event_name in blackout_intervals:
            if start_m <= current_minute <= end_m:
                msg = f"Đang trong khung giờ tin tức biến động mạnh ({event_name}). Tạm ngừng mở vị thế mới!"
                logger.warning(f"📰 [NEWS BLACKOUT] {msg}")
                return True, msg

        return False, "Thời gian thị trường bình thường"

    def can_open_new_position(self, current_positions_count: int, current_balance: float) -> Tuple[bool, str]:
        """Check entry policy without granting application-side breaker authority."""
        cb_ok, cb_msg = self.check_circuit_breaker(current_balance)
        if not cb_ok:
            return False, cb_msg

        max_positions = getattr(self.config, "max_concurrent_positions", 3)
        if current_positions_count >= max_positions:
            return False, f"Đã đạt số lượng vị thế mở tối đa ({current_positions_count}/{max_positions})."

        return True, "Đủ điều kiện mở vị thế mới."

    def calculate_position_size(
        self,
        current_balance: float = 0.0,
        entry_price: float = 0.0,
        stop_loss_price: float = 0.0,
        step_size: float = 0.001,
        min_qty: float = 0.001,
        leverage: Optional[int] = None,
        ai_score: Optional[float] = None,
        **kwargs
    ) -> PositionSizingResult:
        """Tính toán khối lượng lệnh (Quantity) và Ký quỹ (Margin) dựa trên quy tắc quản trị rủi ro"""
        bal = kwargs.get("balance", current_balance)
        if bal <= 0:
            bal = current_balance

        if bal <= 0 or entry_price <= 0:
            return PositionSizingResult(valid=False, qty=0.0, margin=0.0, risk_amount=0.0, reason="Invalid balance or price")

        eff_leverage = leverage or getattr(self.config, "leverage", 5)
        stop_distance = abs(entry_price - stop_loss_price)
        if stop_distance <= 0:
            return PositionSizingResult(valid=False, qty=0.0, margin=0.0, risk_amount=0.0, reason="Zero stop distance")

        mode = getattr(self.config, "sizing_mode", "risk_percent").lower()
        if mode == "fixed_amount":
            fixed_usdt = float(getattr(self.config, "fixed_usdt_per_trade", 50.0))
            margin = min(fixed_usdt, bal * 0.5)
            notional = margin * eff_leverage
            raw_qty = notional / entry_price
            risk_amount = raw_qty * stop_distance
        elif mode == "margin_percent":
            margin_pct = float(getattr(self.config, "margin_percent_per_trade", 5.0))
            margin = bal * (margin_pct / 100.0)
            notional = margin * eff_leverage
            raw_qty = notional / entry_price
            risk_amount = raw_qty * stop_distance
        else:
            risk_percent = getattr(self.config, "risk_per_trade_percent", 1.5)
            if ai_score is not None:
                if ai_score >= 8.5:
                    risk_percent = min(risk_percent * 1.25, 2.5)
                elif ai_score <= 6.5:
                    risk_percent = max(risk_percent * 0.75, 0.8)

            risk_amount = bal * (risk_percent / 100.0)
            raw_qty = risk_amount / stop_distance
            max_notional = bal * eff_leverage * 0.95
            raw_qty = min(raw_qty, max_notional / entry_price)

        hard_cap = getattr(self.config, "real_trading_hard_cap", 0.0)
        is_dry_run = getattr(self.config, "dry_run", True)
        if not is_dry_run and hard_cap and hard_cap > 0:
            max_cap_notional = hard_cap * eff_leverage
            raw_qty = min(raw_qty, max_cap_notional / entry_price)

        qty = self._round_step_size(raw_qty, step_size)
        if qty < min_qty:
            return PositionSizingResult(valid=False, qty=0.0, margin=0.0, risk_amount=0.0, reason="Quantity below min_qty")

        actual_notional = qty * entry_price
        actual_margin = actual_notional / eff_leverage
        actual_risk = qty * stop_distance

        return PositionSizingResult(
            valid=True,
            qty=qty,
            margin=round(actual_margin, 2),
            risk_amount=round(actual_risk, 2),
            notional=round(actual_notional, 2),
            leverage=eff_leverage,
            reason="OK"
        )

    @staticmethod
    def _round_step_size(quantity: float, step_size: float) -> float:
        if step_size <= 0:
            return quantity
        d_qty = Decimal(str(quantity))
        d_step = Decimal(str(step_size))
        rounded = (d_qty // d_step) * d_step
        return float(rounded)

    @staticmethod
    def _round_tick_size(price: float, tick_size: float) -> float:
        if tick_size <= 0:
            return price
        d_price = Decimal(str(price))
        d_tick = Decimal(str(tick_size))
        rounded = (d_price / d_tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * d_tick
        return float(rounded)

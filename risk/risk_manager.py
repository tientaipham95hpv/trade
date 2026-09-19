import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional
from config.settings import BotConfig

logger = logging.getLogger("RiskManager")

VIETNAM_TZ = timezone(timedelta(hours=7))


class RiskManager:
    """
    Module Quản trị Rủi ro & Phân bổ Vốn:
    - Tính toán khối lượng vào lệnh động (Position Sizing).
    - Làm tròn số lượng theo stepSize/lotSize của Binance.
    - Kiểm soát sụt giảm tài khoản trong ngày (Max Daily Drawdown).
    - Giới hạn số lượng vị thế mở đồng thời.
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self.daily_start_balance = 0.0
        self.last_reset_day = None
        self.circuit_breaker_triggered = False
        self.circuit_breaker_until: Optional[datetime] = None

    def reset_daily_stats_if_needed(self, current_balance: float):
        """Reset mốc vốn đầu ngày vào 00:00 Giờ Việt Nam (UTC+7)"""
        current_day = datetime.now(VIETNAM_TZ).date()
        if self.last_reset_day != current_day:
            self.last_reset_day = current_day
            self.daily_start_balance = current_balance
            self.circuit_breaker_triggered = False
            self.circuit_breaker_until = None
            logger.info(f"Đã reset vốn mốc đầu ngày mới (Giờ VN UTC+7): ${self.daily_start_balance:.2f}")

    def check_circuit_breaker(self, current_balance: float) -> Tuple[bool, str]:
        """Kiểm tra xem có chạm ngưỡng cắt lỗ cả ngày (Max Daily Loss / Circuit Breaker) hay không"""
        self.reset_daily_stats_if_needed(current_balance)

        now = datetime.now(VIETNAM_TZ)
        if self.circuit_breaker_until and now < self.circuit_breaker_until:
            remain = self.circuit_breaker_until - now
            hours_left = remain.total_seconds() / 3600.0
            msg = f"🚨 CẦU DAO ĐANG KHÓA (Circuit Breaker Cooldown): Còn {hours_left:.1f} giờ để bảo vệ vốn trước khi mở lại."
            return False, msg

        if not getattr(self.config, "enable_circuit_breaker", True):
            return True, "Circuit Breaker đã tắt"

        if self.daily_start_balance <= 0:
            return True, "Hệ thống sẵn sàng"

        loss_usdt = self.daily_start_balance - current_balance
        drawdown_pct = (loss_usdt / self.daily_start_balance * 100.0) if self.daily_start_balance > 0 else 0.0

        max_loss_usdt = getattr(self.config, "circuit_breaker_max_daily_loss", 30.0)
        max_loss_pct = getattr(self.config, "max_daily_loss_percent", 3.0)

        if drawdown_pct >= max_loss_pct or loss_usdt >= max_loss_usdt:
            self.circuit_breaker_triggered = True
            cooldown_h = getattr(self.config, "circuit_breaker_cooldown_hours", 12)
            self.circuit_breaker_until = now + timedelta(hours=cooldown_h)
            msg = (
                f"🚨 CẦU DAO BẢO VỆ VỐN ĐÃ KÍCH HOẠT (CIRCUIT BREAKER)!\n"
                f"• Tổng lỗ trong ngày: -${loss_usdt:.2f} USDT (-{drawdown_pct:.2f}%)\n"
                f"• Ngưỡng ngắt cho phép: ${max_loss_usdt:.2f} USDT ({max_loss_pct}%)\n"
                f"• Khóa tạm thời: {cooldown_h} tiếng để tránh bão thị trường!"
            )
            logger.warning(msg)
            return False, msg

        return True, f"Drawdown ngày an toàn: -${max(0.0, loss_usdt):.2f} (-{max(0.0, drawdown_pct):.2f}%)"

    def is_news_blackout_window(self) -> Tuple[bool, str]:
        """
        Kiểm tra xem thời điểm hiện tại có trùng với khung giờ công bố tin tức vĩ mô lớn của Mỹ hay không:
        - 12:25 - 13:35 UTC: Khung giờ tin CPI, NFP, PPI, GDP, Đơn xin trợ cấp thất nghiệp (8:30 AM EST)
        - 17:55 - 19:05 UTC: Khung giờ công bố Lãi suất FED & Họp báo FOMC (2:00 PM EST)
        - 23:55 - 00:05 UTC: Khung giờ biến động giao phiên ngày mới & Quyết toán Funding Rate
        """
        if not self.config.enable_news_filter:
            return False, "News filter tắt"

        now_utc = datetime.now(timezone.utc).time()
        current_minute = now_utc.hour * 60 + now_utc.minute

        # Danh sách các khoảng phút trong ngày theo UTC cần né lệnh
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

    def can_open_new_position(self, current_open_positions: int, current_balance: float) -> Tuple[bool, str]:
        """Kiểm tra điều kiện an toàn trước khi vào lệnh mới"""
        # 1. Kiểm tra Circuit Breaker (Max daily drawdown)
        safe, reason = self.check_circuit_breaker(current_balance)
        if not safe:
            return False, reason

        # 2. Kiểm tra bộ lọc tin tức vĩ mô (Economic News Blackout)
        in_blackout, blackout_reason = self.is_news_blackout_window()
        if in_blackout:
            return False, blackout_reason

        # 3. Kiểm tra số lệnh tối đa
        if current_open_positions >= self.config.max_concurrent_positions:
            return False, f"Đã đạt số vị thế mở tối đa cho phép ({current_open_positions}/{self.config.max_concurrent_positions})"

        # 4. Kiểm tra số dư tối thiểu
        if current_balance < 10.0:
            return False, f"Số dư khả dụng quá thấp (${current_balance:.2f} USDT) để mở lệnh mới"

        return True, "Đủ điều kiện an toàn để mở vị thế"

    def calculate_dynamic_leverage(self, entry_price: float, stop_loss_price: float) -> int:
        """
        Tự động tính toán mức đòn bẩy thích ứng (Dynamic Volatility Leverage):
        - SL hẹp (<= 1.2% - như BTC, ETH): Đòn bẩy 10x (tiết kiệm ký quỹ, tận dụng vốn tối đa)
        - SL vừa (1.2% - 1.8%): Đòn bẩy 8x
        - SL chuẩn (1.8% - 2.5%): Đòn bẩy 5x
        - SL rộng (2.5% - 3.5%): Đòn bẩy 3x
        - SL biến động lớn (> 3.5% - Altcoin râu dài, Meme): Đòn bẩy 2x (an toàn tuyệt đối, thanh lý cực xa)
        """
        if not getattr(self.config, "enable_dynamic_leverage", True):
            return int(self.config.leverage)

        sl_pct = (abs(entry_price - stop_loss_price) / entry_price) * 100.0 if entry_price > 0 else 2.0
        min_lev = getattr(self.config, "min_leverage", 2)
        max_lev = getattr(self.config, "max_leverage", 10)

        if sl_pct <= 1.2:
            lev = 10
        elif sl_pct <= 1.8:
            lev = 8
        elif sl_pct <= 2.5:
            lev = 5
        elif sl_pct <= 3.5:
            lev = 3
        else:
            lev = 2

        return max(min_lev, min(max_lev, lev))

    def calculate_position_size(
        self,
        balance: float,
        entry_price: float,
        stop_loss_price: float,
        step_size: float = 0.001,
        min_qty: float = 0.001,
        min_notional: float = 5.0,
        leverage: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Tính toán khối lượng vào lệnh (Quantity) theo chế độ đã cấu hình kết hợp Đòn bẩy thích ứng (Dynamic Leverage):
        - risk_percent: Số tiền lỗ nếu dính SL cố định = balance * risk%
        - margin_percent: Ký quỹ = balance * margin%
        - fixed_amount: Ký quỹ cố định = fixed_usdt
        """
        if balance <= 0 or entry_price <= 0 or stop_loss_price <= 0:
            return {"valid": False, "qty": 0.0, "reason": "Dữ liệu đầu vào giá/vốn không hợp lệ"}

        sl_distance = abs(entry_price - stop_loss_price)
        if sl_distance <= 0:
            return {"valid": False, "qty": 0.0, "reason": "Khoảng cách Stop Loss bằng 0"}

        # Xác định mức đòn bẩy thích ứng cho lệnh
        effective_leverage = leverage if leverage is not None else self.calculate_dynamic_leverage(entry_price, stop_loss_price)

        mode = self.config.sizing_mode

        if mode == "risk_percent":
            risk_amount = balance * (self.config.risk_per_trade_percent / 100.0)
            raw_qty = risk_amount / sl_distance
            actual_margin = (raw_qty * entry_price) / effective_leverage
            # Nếu tiền ký quỹ vượt quá 35% tổng tài khoản, giới hạn lại để tránh over-leverage
            max_allowed_margin = balance * 0.35
            if actual_margin > max_allowed_margin:
                raw_qty = (max_allowed_margin * effective_leverage) / entry_price
                risk_amount = raw_qty * sl_distance
        elif mode == "margin_percent":
            margin = balance * (self.config.margin_percent_per_trade / 100.0)
            notional = margin * effective_leverage
            raw_qty = notional / entry_price
            risk_amount = raw_qty * sl_distance
        else:  # fixed_amount
            margin = min(self.config.fixed_usdt_per_trade, balance * 0.5)
            notional = margin * effective_leverage
            raw_qty = notional / entry_price
            risk_amount = raw_qty * sl_distance

        # Làm tròn theo step_size của sàn Binance
        qty = self._round_step_size(raw_qty, step_size)
        notional_value = qty * entry_price
        required_margin = notional_value / effective_leverage

        # Kiểm tra ngưỡng tối thiểu
        if qty < min_qty:
            return {
                "valid": False,
                "qty": 0.0,
                "reason": f"Khối lượng ({qty}) nhỏ hơn mức tối thiểu của sàn ({min_qty})"
            }

        if notional_value < min_notional:
            return {
                "valid": False,
                "qty": 0.0,
                "reason": f"Giá trị vị thế (${notional_value:.2f}) nhỏ hơn mức tối thiểu ${min_notional} USDT"
            }

        if required_margin > balance * 0.9:
            return {
                "valid": False,
                "qty": 0.0,
                "reason": f"Ký quỹ cần (${required_margin:.2f}) vượt quá số dư khả dụng (${balance:.2f})"
            }

        return {
            "valid": True,
            "qty": qty,
            "notional": round(notional_value, 2),
            "margin": round(required_margin, 2),
            "risk_amount": round(risk_amount, 2),
            "risk_percent_actual": round((risk_amount / balance) * 100.0, 2),
            "leverage": effective_leverage,
            "sl_percent": round((sl_distance / entry_price) * 100.0, 2),
            "reason": "OK"
        }

    @staticmethod
    def _round_step_size(qty: float, step_size: float) -> float:
        """Làm tròn số lượng xuống bội số của step_size"""
        if step_size <= 0:
            return round(qty, 3)
        precision = int(round(-math.log10(step_size))) if step_size < 1 else 0
        factor = 10 ** precision
        return math.floor(qty * factor) / factor

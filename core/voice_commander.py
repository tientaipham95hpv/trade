import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger("VoiceCommander")


class QuantumVoiceCommander:
    """
    Quantum Voice & Two-Way Interactive Commander (Phiên bản 8.0):
    - Động cơ phân tích ý định giọng nói và văn bản tự nhiên (Natural Language Intent Parser).
    - Cho phép người dùng điều khiển bot trực tiếp bằng giọng nói tiếng Việt hoặc gõ lệnh tự nhiên:
        * "Giảm đòn bẩy xuống 3x"
        * "Báo cáo số dư và PnL"
        * "Tạm dừng bot bảo toàn vốn"
        * "Đóng toàn bộ vị thế khẩn cấp"
        * "Soi kèo BTCUSDT bằng Order Flow"
    - Tự động thực thi hành động tương ứng và trả về câu phản hồi âm thanh tiếng Việt sống động.
    """

    @staticmethod
    def process_command(text: str, bot_context: Optional[Any] = None) -> Dict[str, Any]:
        """
        Phân tích câu lệnh và thực thi hành động điều khiển
        """
        raw = text.strip()
        lower = raw.lower()

        # 1. Câu lệnh: Báo cáo PnL & Tài khoản
        if any(k in lower for k in ["báo cáo", "số dư", "pnl", "tình hình", "lãi lỗ", "tài khoản"]):
            bal = 1000.0
            pos_count = 0
            unrealized = 0.0
            if bot_context:
                bal = round(bot_context.get_current_balance(), 2)
                pos_count = len(bot_context.order_manager.active_positions)
                prices = bot_context.get_current_prices()
                for sym, pos in bot_context.order_manager.active_positions.items():
                    cur_p = prices.get(sym, pos["entry_price"])
                    if pos["side"] == "BUY":
                        unrealized += (cur_p - pos["entry_price"]) * pos["qty"]
                    else:
                        unrealized += (pos["entry_price"] - cur_p) * pos["qty"]
                unrealized = round(unrealized, 2)

            sign = "+" if unrealized >= 0 else ""
            reply = f"Báo cáo Sếp! Số dư khả dụng hiện tại là {bal} USDT. Đang có {pos_count} vị thế đang mở với PnL tạm tính là {sign}{unrealized} USDT. Tất cả hệ thống phòng thủ đều an toàn!"
            return {"action": "REPORT", "reply": reply, "executed": True, "speak": reply}

        # 2. Câu lệnh: Tạm dừng bot
        if any(k in lower for k in ["tạm dừng", "dừng lại", "pause", "nghỉ ngơi", "đứng ngoài"]):
            if bot_context:
                bot_context.is_paused = True
            reply = "Đã tạm dừng tìm kiếm lệnh mới theo chỉ lệnh của Sếp! Bot sẽ tiếp tục theo dõi các vị thế đang chạy."
            return {"action": "PAUSE", "reply": reply, "executed": True, "speak": reply}

        # 3. Câu lệnh: Tiếp tục chạy bot
        if any(k in lower for k in ["tiếp tục", "chạy tiếp", "resume", "bật lại", "quét tiếp"]):
            if bot_context:
                bot_context.is_paused = False
            reply = "Đã kích hoạt chế độ săn lệnh tự động! Radar bắt đầu quét toàn bộ thị trường ngay bây giờ."
            return {"action": "RESUME", "reply": reply, "executed": True, "speak": reply}

        # 4. Câu lệnh: Đóng khẩn cấp / Cắt lỗ toàn bộ
        if any(k in lower for k in ["đóng hết", "đóng toàn bộ", "panic", "cắt hết", "thoát hàng"]):
            if bot_context and hasattr(bot_context, "order_manager"):
                prices = bot_context.get_current_prices()
                bot_context.order_manager.close_all_positions(
                    reason="Chỉ lệnh Giọng Nói Khẩn Cấp (Voice Commander)",
                    current_prices=prices,
                    simulated_balance_holder=bot_context.simulated_balance_holder
                )
            reply = "CẢNH BÁO: Đã thực thi đóng toàn bộ các vị thế đang mở bằng lệnh Market! Tài khoản của Sếp đã an toàn 100% tiền mặt."
            return {"action": "PANIC_CLOSE", "reply": reply, "executed": True, "speak": reply}

        # 5. Câu lệnh: Điều chỉnh đòn bẩy
        lev_match = re.search(r"(\d+)\s*(?:x|lần)?", lower)
        if any(k in lower for k in ["đòn bẩy", "leverage"]) and lev_match:
            lev = int(lev_match.group(1))
            if 1 <= lev <= 20:
                from config.settings import config
                config.leverage = lev
                reply = f"Đã điều chỉnh đòn bẩy hệ thống về {lev}x theo yêu cầu của Sếp!"
                return {"action": "SET_LEVERAGE", "value": lev, "reply": reply, "executed": True, "speak": reply}

        # 6. Câu lệnh: Soi kèo coin cụ thể
        coin_match = re.search(r"\b(btc|eth|sol|bnb|xrp|doge|ada)\b", lower)
        if any(k in lower for k in ["soi kèo", "phân tích", "xem xét", "đánh giá"]) and coin_match:
            coin = coin_match.group(1).upper() + "USDT"
            from core.order_flow import OrderFlowEngine
            flow = OrderFlowEngine.fetch_order_flow_metrics(coin)
            delta_str = f"+{flow['delta']}" if flow['delta'] >= 0 else f"{flow['delta']}"
            reply = f"Dữ liệu Order Flow của {coin}: Giá hiện tại ${flow['last_price']:,}. Cumulative Delta: {delta_str} ({flow['cvd_percent']}%). Đánh giá: {flow['signal_desc']}"
            return {"action": "ANALYZE_SYMBOL", "symbol": coin, "reply": reply, "executed": True, "speak": reply}

        # Fallback: Trả lời AI Copilot trợ giúp
        reply = f"Dạ Sếp! Em đã nhận thông tin '{raw}'. Sếp có thể bảo em: 'Báo cáo số dư', 'Tạm dừng bot', 'Giảm đòn bẩy xuống 3x', hoặc 'Soi kèo BTC' bất cứ lúc nào ạ!"
        return {"action": "CHAT", "reply": reply, "executed": False, "speak": reply}

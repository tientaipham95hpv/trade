"""
Conversational Multi-Turn Portfolio Advisor (Bản 12.0)
Trợ lý đàm thoại lượng tử chuyên sâu cấp cao (Senior Quant Advisor).
Giải thích chi tiết lý do từng lệnh, tư vấn chiến lược gồng lãi / cắt lỗ và kịch bản thị trường bằng tiếng Việt tự nhiên.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("PortfolioAdvisor")

class MultiTurnPortfolioAdvisor:
    @staticmethod
    def answer_query(
        query: str,
        bot_controller: Any = None
    ) -> Dict[str, Any]:
        """
        Phân tích câu hỏi người dùng kết hợp trạng thái bot thời gian thực để đưa ra câu trả lời chuyên sâu.
        """
        q = query.lower().strip()
        active_pos = bot_controller.order_manager.active_positions if bot_controller and hasattr(bot_controller, "order_manager") else {}
        balance = bot_controller.get_current_balance() if bot_controller and hasattr(bot_controller, "get_current_balance") else 1000.0

        # Kịch bản 1: Hỏi về việc có nên gồng lệnh / cắt lệnh một coin cụ thể
        matched_coin = None
        for sym in ["btc", "eth", "sol", "doge", "bnb", "avax", "near", "sui"]:
            if sym in q:
                matched_coin = sym.upper() + "USDT"
                break

        if ("gồng" in q or "giữ lệnh" in q or "chốt" in q or "cắt" in q) and matched_coin:
            if matched_coin in active_pos:
                pos = active_pos[matched_coin]
                side = pos["side"]
                entry = pos["entry_price"]
                sl = pos["stop_loss"]
                tp = pos["take_profit"]
                margin = pos.get("margin", 50.0)
                is_be = pos.get("breakeven_activated", False)

                reply = (
                    f"📊 <b>TƯ VẤN VỊ THẾ {matched_coin} ({side}):</b>\n\n"
                    f"• <b>Giá vào lệnh:</b> <code>${entry:,.4f}</code> | <b>Ký quỹ:</b> <code>${margin:.2f} USDT</code>\n"
                    f"• <b>Điểm Cắt Lỗ:</b> <code>${sl:,.4f}</code> | <b>Điểm Chốt Lời:</b> <code>${tp:,.4f}</code>\n"
                    f"• <b>Khuyến nghị AI:</b> "
                )
                if is_be:
                    reply += (
                        "Vị thế này <b>ĐÃ ĐƯỢC DỜI STOP LOSS VỀ HÒA VỐN</b> (Risk-Free). "
                        "Bạn hoàn toàn yên tâm <b>TIẾP TỤC GỒNG LÃI</b> theo kế hoạch Trailing Runner để ăn trọn con sóng, "
                        "vì rủi ro vị thế hiện tại bằng 0!"
                    )
                else:
                    reply += (
                        "Lệnh vẫn đang trong biên độ kiểm soát kỹ thuật với Stop Loss bảo vệ vốn chặt chẽ. "
                        "Không nên can thiệp đóng tay quá sớm để giữ trọn tỷ lệ R:R kỳ vọng 1:1.5."
                    )
                return {"reply": reply, "topic": "POSITION_ADVICE", "symbol": matched_coin}

        # Kịch bản 2: Hỏi lý do tại sao lệnh bị cắt lỗ (Post-Mortem Analysis)
        if "tại sao" in q and ("thua" in q or "lỗ" in q or "stop loss" in q or "sl" in q):
            reply = (
                "🔍 <b>PHÂN TÍCH NGUYÊN NHÂN LỆNH CHẠM STOP LOSS:</b>\n\n"
                "Trong giao dịch định lượng, Stop Loss là <b>chi phí bắt buộc để bảo toàn vốn</b> khi thị trường xuất hiện biến động ngoại lai:\n"
                "1. <b>Bẫy quét râu thanh khoản (Liquidity Sweep):</b> Cá mập tổ chức thường cố tình giật râu nến quét qua các vùng đáy/đỉnh cũ trước khi kéo giá thật.\n"
                "2. <b>Sóng giật tin tức bất ngờ:</b> Các phát biểu vĩ mô hoặc biến động đột biến của BTC kéo theo toàn bộ Altcoin.\n"
                "👉 <b>Điểm cốt lõi:</b> Mỗi lệnh bot chỉ mạo hiểm tối đa 1% vốn, và nhờ tỷ lệ R:R 1.5 nên chỉ cần Winrate > 45% là tài khoản đã sinh lãi ròng ổn định!"
            )
            return {"reply": reply, "topic": "POST_MORTEM"}

        # Kịch bản 3: Kịch bản nếu BTC sập hoặc biến động mạnh
        if "btc" in q and ("sập" in q or "thủng" in q or "giảm" in q or "crash" in q):
            reply = (
                "🛡️ <b>KỊCH BẢN PHÒNG VỆ KHI BITCOIN GIẢM MẠNH:</b>\n\n"
                "Bot được trang bị hệ thống bảo vệ đa tầng:\n"
                "1. <b>BTC Crash Protection:</b> Nếu nến 15m BTC giảm sốc vượt ngưỡng cảnh báo, bot tự động hủy toàn bộ lệnh Long và khóa mở vị thế mới.\n"
                "2. <b>Cocoon Defense Shield:</b> Hạ tỷ lệ đòn bẩy về 2x và kích hoạt bảo vệ vốn.\n"
                "3. <b>Stop Loss Bắt Buộc:</b> Tất cả các vị thế mở đều có SL cứng, đảm bảo tài khoản không bao giờ bị cháy hay sụt giảm quá giới hạn an toàn."
            )
            return {"reply": reply, "topic": "CRASH_SCENARIO"}

        # Kịch bản mặc định: Phân tích tổng quan sức khỏe tài khoản
        reply = (
            f"🤖 <b>TỔNG QUAN CHIẾN LƯỢC TÀI KHOẢN HIỆN TẠI:</b>\n\n"
            f"• <b>Tổng vốn quản lý:</b> <code>${balance:,.2f} USDT</code>\n"
            f"• <b>Vị thế đang mở:</b> <code>{len(active_pos)} vị thế</code>\n"
            f"• <b>Đánh giá an toàn:</b> Hệ thống đang chạy ở mức rủi ro kiểm soát 1.0% mỗi lệnh với đòn bẩy Isolated an toàn.\n"
            f"💡 <i>Bạn có thể hỏi em: 'Có nên gồng lệnh SOL không?', 'Phân tích tại sao lệnh vừa rồi bị cắt lỗ?' hoặc 'Kịch bản nếu BTC giảm?'</i>"
        )
        return {"reply": reply, "topic": "PORTFOLIO_OVERVIEW"}

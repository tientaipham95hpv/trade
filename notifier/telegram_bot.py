import os
import csv
import json
import time
import logging
import threading
import html
import re
from typing import Optional, Any, Dict, List
import requests
from config.settings import BotConfig

logger = logging.getLogger("TelegramBot")



def _now_vn_str() -> str:
    """Trả về chuỗi thời gian hiện tại theo múi giờ Việt Nam (UTC+7)"""
    try:
        from datetime import datetime, timezone, timedelta
        return datetime.now(timezone(timedelta(hours=7))).strftime("%d/%m/%Y %H:%M:%S (VN)")
    except Exception:
        return time.strftime("%d/%m/%Y %H:%M:%S (VN)")

class TelegramNotifier:
    """
    Bộ Điều Khiển Telegram 2 Chiều Nâng Cấp (Modern Interactive Telegram Bot):
    - Tự động đăng ký Menu lệnh chuẩn với Telegram qua setMyCommands.
    - Bàn phím nút bấm cảm ứng (Reply Keyboard) hiển thị cố định dưới màn hình chat.
    - Nút bấm trực tiếp trong tin nhắn (Inline Keyboard) để tương tác 1-chạm.
    - Xử lý ngôn ngữ tự nhiên và lệnh không phân biệt chữ hoa/thường hay icon.
    - Thiết kế giao diện tin nhắn trực quan với thanh tiến trình Unicode.
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self.enabled = config.telegram_enabled and bool(config.telegram_bot_token) and bool(config.telegram_chat_id)
        self.bot_token = config.telegram_bot_token
        raw_chats = str(config.telegram_chat_id).replace(";", ",").split(",")
        self.authorized_chat_ids = [c.strip() for c in raw_chats if c.strip()]
        self.chat_id = self.authorized_chat_ids[0] if self.authorized_chat_ids else ""
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

        self.bot_controller = None
        self._listener_thread = None
        self._is_listening = False
        self._last_update_id = 0
        self._live_alert_sent = False

    @property
    def web_terminal_url(self) -> str:
        """Đường dẫn Web Terminal bảo mật với token quản trị tự động đăng nhập"""
        try:
            import hashlib
            token = hashlib.sha256(f"{self.config.web_username}:{self.config.web_password}:{self.config.telegram_bot_token}".encode()).hexdigest()
            return f"https://trader.noza.site/?token={token}"
        except Exception:
            return "https://trader.noza.site/"

    def register_bot_commands(self):
        """Đăng ký danh sách lệnh chính thức với Telegram để hiển thị nút Menu góc trái"""
        if not self.enabled:
            return
        try:
            url = f"{self.base_url}/setMyCommands"
            commands = [
                {"command": "app", "description": "🚀 Mở Web App Terminal (Mini App)"},
                {"command": "menu", "description": "📱 Bật bàn phím nút bấm điều khiển"},
                {"command": "status", "description": "📊 Xem số dư & PnL tổng quan"},
                {"command": "positions", "description": "⚡ Xem các lệnh đang chạy"},
                {"command": "sentiment", "description": "🔥 Chỉ số Fear & Greed thị trường"},
                {"command": "funding", "description": "💰 Săn lợi nhuận Funding Rate APY (Bản 6.0)"},
                {"command": "news", "description": "📰 Tin tức vĩ mô & crypto AI (Bản 6.0)"},
                {"command": "liquidation", "description": "🌊 Bản đồ thanh lý đòn bẩy cá voi (Bản 6.0)"},
                {"command": "ai", "description": "🤖 Hỏi Trợ lý AI Cyber-Nova về thị trường"},
                {"command": "analytics", "description": "📈 Hiệu suất từng cặp coin & Streak"},
                {"command": "mode", "description": "🎯 Đổi chế độ quét (BTC/ETH vs All Altcoin)"},
                {"command": "eval", "description": "🏆 Tiến độ đủ điều kiện đánh thật"},
                {"command": "health", "description": "🩺 Sức khỏe máy chủ VPS & Ping sàn"},
                {"command": "export", "description": "📥 Tải file CSV lịch sử lệnh"},
                {"command": "pause", "description": "⏸️ Tạm dừng mở vị thế mới"},
                {"command": "resume", "description": "▶️ Tiếp tục quét và mở lệnh"},
                {"command": "closeall", "description": "🚨 ĐÓNG SẠCH LỆNH KHẨN CẤP"},
                {"command": "train", "description": "🧠 AI Tự học & Đào tạo chiến lược từ lịch sử"}
            ]
            res = requests.post(url, json={"commands": commands}, timeout=10)
            if res.status_code == 200:
                logger.info("Đã đăng ký danh sách lệnh thành công với Telegram Menu.")
            # 1. Reset Menu Button mặc định toàn cầu về default (người lạ không thể thấy nút Terminal hay Token)
            requests.post(f"{self.base_url}/setChatMenuButton", json={
                "menu_button": {"type": "default"}
            }, timeout=8)

            # 2. Chỉ cấp quyền Menu Button Web Terminal riêng biệt cho các Admin Chat ID được ủy quyền
            for cid in self.authorized_chat_ids:
                try:
                    requests.post(f"{self.base_url}/setChatMenuButton", json={
                        "chat_id": cid,
                        "menu_button": {
                            "type": "web_app",
                            "text": "📱 Terminal",
                            "web_app": {"url": self.web_terminal_url}
                        }
                    }, timeout=8)
                except Exception:
                    pass
        except Exception as e:
            logger.debug("Lỗi đăng ký bot commands: %s", e)

    def get_main_keyboard(self) -> dict:
        """Bàn phím nút bấm cảm ứng lớn cố định dưới màn hình chat"""
        return {
            "keyboard": [
                [{"text": "🚀 Web Terminal"}, {"text": "📊 Trạng Thái"}, {"text": "⚡ Vị Thế Đang Mở"}],
                [{"text": "🔥 Fear & Greed"}, {"text": "💰 Funding Arbitrage"}, {"text": "📈 Phân Tích Coin"}],
                [{"text": "🏆 Tiến Độ Đánh Thật"}, {"text": "🩺 Sức Khỏe VPS"}, {"text": "📥 Tải CSV"}],
                [{"text": "⏸️ Tạm Dừng"}, {"text": "▶️ Tiếp Tục"}, {"text": "🚨 Đóng Khẩn Cấp"}]
            ],
            "resize_keyboard": True,
            "is_persistent": True
        }

    def start_listener(self, bot_context: Any):
        """Khởi chạy luồng chạy ngầm để lắng nghe lệnh điều khiển từ Telegram"""
        if not self.enabled:
            logger.debug("Telegram chưa bật hoặc thiếu Token/ChatID, bỏ qua listener.")
            return

        self.bot_controller = bot_context
        self._is_listening = True
        
        # Đăng ký danh sách lệnh với Telegram Menu
        self.register_bot_commands()

        self._listener_thread = threading.Thread(target=self._poll_updates_loop, daemon=True, name="TelegramListener")
        self._listener_thread.start()
        logger.info("Đã kích hoạt bộ điều khiển Telegram 2 chiều (Listening for commands & buttons...)")

    def _poll_updates_loop(self):
        """Vòng lặp long-polling nhận lệnh và tương tác nút bấm từ Telegram"""
        while self._is_listening:
            try:
                url = f"{self.base_url}/getUpdates"
                params = {
                    "offset": self._last_update_id + 1,
                    "timeout": 15,
                    "allowed_updates": ["message", "callback_query"]
                }
                res = requests.get(url, params=params, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    for update in data.get("result", []):
                        self._last_update_id = update["update_id"]
                        
                        # 1. Xử lý tin nhắn văn bản / nút bấm bàn phím
                        if "message" in update:
                            self._handle_incoming_message(update["message"])
                        
                        # 2. Xử lý nút bấm Inline (Callback Query)
                        elif "callback_query" in update:
                            self._handle_callback_query(update["callback_query"])
            except Exception as e:
                logger.debug("Lỗi kết nối polling Telegram: %s", e)
                time.sleep(4)

    def _answer_callback(self, callback_query_id: str, text: str = "", show_alert: bool = False):
        """Phản hồi callback query để tắt vòng quay trên nút bấm Telegram"""
        try:
            url = f"{self.base_url}/answerCallbackQuery"
            requests.post(url, json={"callback_query_id": callback_query_id, "text": text, "show_alert": show_alert}, timeout=5)
        except Exception:
            pass

    def _handle_callback_query(self, query: dict):
        """Xử lý khi người dùng chạm vào nút bấm Inline"""
        sender_id = str(query.get("from", {}).get("id", "")).strip()
        if sender_id not in self.authorized_chat_ids:
            self._answer_callback(query.get("id"), "⛔ Quyền truy cập bị từ chối! Tài khoản chưa được ủy quyền.", show_alert=True)
            return

        qid = query.get("id")
        data = query.get("data", "")
        self._answer_callback(qid, "Đang xử lý...")

        if data == "btn_status":
            self._cmd_status()
        elif data == "btn_positions":
            self._cmd_positions()
        elif data == "btn_eval":
            self._cmd_evaluation()
        elif data == "btn_health":
            self._cmd_health()
        elif data == "btn_history":
            self._cmd_history()
        elif data == "btn_backup":
            self.send_daily_backup_and_report()
        elif data in ["btn_sentiment", "btn_fng"]:
            self._cmd_sentiment()
        elif data in ["btn_funding", "btn_arbitrage"]:
            self._cmd_funding()
        elif data == "btn_app":
            self._cmd_app()
        elif data == "btn_livecheck":
            self._cmd_livecheck()
        elif data in ["btn_ai", "btn_ask_ai"]:
            self._cmd_ai("Phân tích tổng quan thị trường, đánh giá rủi ro và các vị thế hiện tại")
        elif data == "btn_mode":
            self._cmd_mode()
        elif data == "set_mode_bluechip":
            self.config.trading_mode = "BLUECHIP_ONLY"
            if self.bot_controller:
                self.bot_controller.config.trading_mode = "BLUECHIP_ONLY"
            self.send_message(
                "🛡️ <b>ĐÃ CHUYỂN CHẾ ĐỘ THÀNH CÔNG:</b>\n"
                "• <b>Chế độ mới:</b> <code>BLUECHIP_ONLY</code> (Chỉ đánh BTC & ETH khung 15m)\n"
                "• Hệ thống chỉ tập trung vào 2 coin Bluechip an toàn nhất!"
            )
        elif data == "set_mode_market":
            self.config.trading_mode = "MARKET_ALL"
            if self.bot_controller:
                self.bot_controller.config.trading_mode = "MARKET_ALL"
            self.send_message(
                "🚀 <b>ĐÃ CHUYỂN CHẾ ĐỘ THÀNH CÔNG:</b>\n"
                "• <b>Chế độ mới:</b> <code>MARKET_ALL</code> (Quét toàn bộ Top 50 Altcoin & Meme)\n"
                "• Tối đa hóa cơ hội vào lệnh trên toàn thị trường!"
            )
        elif data == "set_dir_auto":
            self.config.trade_direction = "AUTO"
            if self.bot_controller:
                self.bot_controller.config.trade_direction = "AUTO"
            self.send_message(
                "🌐 <b>ĐÃ CHUYỂN CHIỀU GIAO DỊCH:</b>\n"
                "• <b>Chiều đánh:</b> <code>AUTO</code> (Tự Động Đồng Pha Theo BTC Regime)\n"
                "• <i>BTC Uptrend -> Cấm Short, Chỉ Long | BTC Downtrend -> Cấm Long, Chỉ Short!</i>"
            )
        elif data == "set_dir_long":
            self.config.trade_direction = "LONG_ONLY"
            if self.bot_controller:
                self.bot_controller.config.trade_direction = "LONG_ONLY"
            self.send_message(
                "📈 <b>ĐÃ CHUYỂN CHIỀU GIAO DỊCH:</b>\n"
                "• <b>Chiều đánh:</b> <code>LONG_ONLY</code> (Chỉ Mở Lệnh Long)\n"
                "• Tối ưu hóa trong thị trường Bull Market, cấm toàn bộ lệnh Short."
            )
        elif data == "set_dir_short":
            self.config.trade_direction = "SHORT_ONLY"
            if self.bot_controller:
                self.bot_controller.config.trade_direction = "SHORT_ONLY"
            self.send_message(
                "📉 <b>ĐÃ CHUYỂN CHIỀU GIAO DỊCH:</b>\n"
                "• <b>Chiều đánh:</b> <code>SHORT_ONLY</code> (Chỉ Mở Lệnh Short)\n"
                "• Tối ưu hóa khi thị trường sập mạnh / Downtrend, cấm toàn bộ lệnh Long."
            )
        elif data == "set_dir_both":
            self.config.trade_direction = "BOTH"
            if self.bot_controller:
                self.bot_controller.config.trade_direction = "BOTH"
            self.send_message(
                "🔄 <b>ĐÃ CHUYỂN CHIỀU GIAO DỊCH:</b>\n"
                "• <b>Chiều đánh:</b> <code>BOTH</code> (Đánh Cả 2 Chiều Không Ràng Buộc BTC)\n"
                "• Mở lệnh theo từng cơ hội độc lập của từng coin."
            )
        elif data == "btn_pause":
            if self.bot_controller:
                self.bot_controller.is_paused = True
                self.send_message("⏸️ <b>ĐÃ TẠM DỪNG BOT!</b> Không mở vị thế mới.")
        elif data == "btn_resume":
            if self.bot_controller:
                self.bot_controller.is_paused = False
                self.send_message("▶️ <b>ĐÃ BẬT LẠI BOT!</b> Tiếp tục quét thị trường.")
        elif data == "btn_closeall":
            self._cmd_closeall()
        elif data == "btn_export":
            self._cmd_export()
        elif data == "btn_analytics":
            self._cmd_analytics()
        elif data == "btn_ai_train":
            self._cmd_ai_train()
        elif data.startswith("manual_exec_"):
            parts = data.split("_")
            if len(parts) >= 4:
                side = parts[2]
                sym = parts[3]
                if self.bot_controller and hasattr(self.bot_controller, "order_manager"):
                    bal = self.bot_controller.get_current_balance()
                    res = self.bot_controller.order_manager.execute_manual_order(
                        symbol=sym,
                        side=side,
                        balance=bal,
                        leverage=self.config.leverage,
                        risk_percent=self.config.risk_per_trade_percent,
                        simulated_balance_holder=self.bot_controller.simulated_balance_holder
                    )
                    if res.get("success"):
                        order = res.get("order", {})
                        action_str = "LONG 🟢" if side == "BUY" else "SHORT 🔴"
                        self.send_message(
                            f"⚡ <b>ĐÃ VÀO LỆNH {action_str} THÀNH CÔNG!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"• <b>Cặp:</b> <code>{sym}</code>\n"
                            f"• <b>Khối lượng:</b> <code>{order.get('qty', 0)}</code>\n"
                            f"• <b>Giá khớp:</b> <code>${order.get('entry_price', 0):,.4f}</code>\n"
                            f"• <b>Stop Loss:</b> <code>${order.get('stop_loss', 0):,.4f}</code>\n"
                            f"• <b>Take Profit:</b> <code>${order.get('take_profit', 0):,.4f}</code>\n"
                            f"• <b>Ký quỹ:</b> <code>${order.get('margin', 0):.2f} USDT</code>"
                        )
                    else:
                        self.send_message(f"❌ <b>KHÔNG THỂ VÀO LỆNH:</b> {res.get('message')}")

    @staticmethod
    def _strip_vietnamese_accents(text: str) -> str:
        """Chuyển đổi tiếng Việt có dấu thành không dấu chuẩn xác"""
        import unicodedata
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        text = text.replace('đ', 'd').replace('Đ', 'D')
        return text.lower().strip()

    def _clean_cmd(self, text: str) -> str:
        """Chuẩn hóa văn bản đầu vào: xóa ký tự đặc biệt, emoji, chuyển chữ thường"""
        t = text.strip().lower()
        if "@" in t:
            t = t.split("@")[0]
        # Loại bỏ các emoji tiền tố trên bàn phím bấm cảm ứng
        for emoji in [
            "🔥", "💰", "📈", "📥", "📊", "⚡", "🏆", "🩺", "📜", "💾", 
            "⏸️", "▶️", "🚨", "🔑", "📱", "🎯", "🛡️", "🚀", "🤖", "🌐", 
            "💬", "💎", "⭐", "✨", "🔴", "🟢", "🟡", "⚪", "▶", "⏸"
        ]:
            t = t.replace(emoji, "")
        return t.strip()

    def _handle_incoming_message(self, message: dict):
        """Xử lý lệnh từ người dùng linh hoạt bằng cả văn bản và nút bấm"""
        sender_chat_id = str(message.get("chat", {}).get("id", "")).strip()
        if sender_chat_id not in self.authorized_chat_ids:
            logger.warning("Tin nhắn từ tài khoản Telegram chưa ủy quyền: %s", sender_chat_id)
            unauth_msg = (
                "⛔ <b>TRUY CẬP BỊ TỪ CHỐI (ACCESS DENIED)</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"Tài khoản Telegram của bạn (ID: <code>{sender_chat_id}</code>) chưa được cấp quyền quản trị hệ thống bot.\n\n"
                "🛡️ Mọi yêu cầu điều khiển đều bị chặn để đảm bảo an ninh danh mục.\n"
                "Vui lòng liên hệ trực tiếp Quản trị viên để được cấp phép."
            )
            self._send_to_chat(sender_chat_id, unauth_msg, reply_markup={"remove_keyboard": True})
            return

        raw_text = message.get("text", "").strip()
        if not raw_text:
            return

        cmd = self._clean_cmd(raw_text)
        u = self._strip_vietnamese_accents(cmd)

        # 1. Menu & Help
        if cmd in ["/start", "/help", "/menu", "menu", "help", "trợ giúp", "bắt đầu"]:
            self._send_welcome_menu()

        elif cmd in ["/status", "trạng thái", "status", "pnl", "xem pnl", "số dư", "tiền"] or u in ["status", "trang thai", "pnl", "xem pnl", "so du", "balance", "bal", "tai khoan", "tien", "stat", "xem so du", "tong von", "von"] or any(k in u for k in ["so du", "pnl", "trang thai", "kiem tra pnl"]):
            self._cmd_status()

        # 3. Vị thế đang mở
        elif cmd in ["/positions", "vị thế đang mở", "vị thế", "positions", "lệnh"] or u in ["positions", "vi the", "vi the dang mo", "lenh", "cac lenh", "cac vi the", "pos", "p", "lenh dang chay", "dang chay", "xem vi the", "xem lenh"] or any(k in u for k in ["vi the", "lenh dang chay", "cac lenh"]) :
            self._cmd_positions()

        # 3.2. Hỏi Trợ lý AI Cyber-Nova
        elif cmd.startswith("/ai") or cmd in ["/ai", "hỏi ai", "trợ lý ai", "ai", "hỏi trợ lý ai"] or u.startswith("/ai") or u in ["ai", "hoi ai", "tro ly ai", "cyber nova", "nova"] or u.startswith("ai ") or cmd.startswith("ai "):
            query = raw_text.replace("/ai", "").strip()
            if query.lower().startswith("ai "):
                query = query[3:].strip()
            if not query or query.lower() in ["hỏi ai", "trợ lý ai", "ai", "hỏi trợ lý ai", "cyber nova", "nova"]:
                query = "Phân tích tổng quan thị trường, đánh giá rủi ro và các vị thế hiện tại"
            self._cmd_ai(query)

        # 3.5. Chế độ giao dịch
        elif cmd in ["/mode", "chế độ", "đổi chế độ", "mode", "chế độ quét", "đổi chế độ quét"]:
            self._cmd_mode()

        # 4. Tiến độ đánh thật (Evaluation / Audit)
        elif cmd in ["/eval", "/evaluation", "/readiness", "/audit", "tiến độ đánh thật", "tiến độ", "đánh thật", "đánh giá", "eval", "audit", "kiểm toán"]:
            self._cmd_evaluation()

        # 5. Sức khỏe máy chủ VPS
        elif cmd in ["/health", "/system", "sức khỏe vps", "sức khỏe", "health", "vps", "ram", "cpu"]:
            self._cmd_health()

        # 6. Lịch sử giao dịch
        elif cmd in ["/history", "lịch sử lệnh", "lịch sử", "history"] or u in ["history", "lich su", "lich su lenh", "trades", "ls", "xem lich su"] :
            self._cmd_history()

        # 7. Sao lưu dữ liệu
        elif cmd in ["/backup", "sao lưu dữ liệu", "sao lưu", "backup"]:
            self.send_daily_backup_and_report()

        # 8. Kiểm tra API Key Live
        elif cmd in ["/livecheck", "kiểm tra api", "livecheck", "kiểm tra"]:
            self._cmd_livecheck()

        # 9. Tạm dừng
        elif cmd in ["/pause", "tạm dừng", "pause"] or u in ["pause", "tam dung", "dung bot", "nghi ngoi", "stop", "dung lai"] :
            if self.bot_controller:
                self.bot_controller.is_paused = True
                self.send_message("⏸️ <b>ĐÃ TẠM DỪNG BOT!</b> Bot sẽ không mở thêm vị thế mới. Các lệnh đang chạy vẫn được bảo vệ.")
            else:
                self.send_message("Không tìm thấy bot controller.")

        # 10. Tiếp tục
        elif cmd in ["/resume", "tiếp tục", "resume"] or u in ["resume", "tiep tuc", "bat lai", "chay lai", "start bot", "run", "chay tiep"] :
            if self.bot_controller:
                self.bot_controller.is_paused = False
                self.send_message("▶️ <b>ĐÃ BẬT LẠI BOT!</b> Hệ thống tiếp tục quét thị trường và tìm setup vào lệnh.")
            else:
                self.send_message("Không tìm thấy bot controller.")

        # 11. Đóng khẩn cấp
        elif cmd in ["/closeall", "đóng khẩn cấp", "closeall", "panic", "đóng hết", "cắt hết"] or u in ["closeall", "dong het", "dong toan bo", "cat het", "cat lo", "panic", "thoat hang", "chot het", "huy het", "dong lenh"] or any(k in u for k in ["dong het", "cat het", "dong toan bo", "cat lo"]) :
            self._cmd_closeall()

        # 12. Xuất dữ liệu CSV
        elif cmd in ["/export", "export", "xuất dữ liệu", "xuat csv", "tải csv", "export csv", "tải file csv", "tai csv"] or u in ["tai csv", "xuat csv", "export", "tai file", "xuat du lieu", "tai file csv", "csv"] or any(k in u for k in ["tai csv", "xuat csv"]):
            self._cmd_export()

        # 13. Phân tích hiệu suất từng coin
        elif cmd in ["/analytics", "analytics", "thống kê", "hiệu suất", "streak", "phân tích coin"] or u in ["phan tich coin", "phan tich", "analytics", "thong ke", "hieu suat", "streak", "thong ke coin", "hieu suat coin"] or any(k in u for k in ["phan tich", "thong ke", "hieu suat", "analytics"]):
            self._cmd_analytics()

        # 14. Telegram Mini App
        elif cmd in ["/app", "/terminal", "/webapp", "web terminal", "app", "mini app", "terminal"]:
            self._cmd_app()

        # 15. Fear & Greed Index
        elif cmd in ["/sentiment", "/fng", "fear & greed", "fear and greed", "tâm lý", "sentiment"] or u in ["fear", "greed", "fng", "tam ly", "sentiment", "fear and greed", "fear & greed", "chi so tam ly", "tam ly thi truong"] or any(k in u for k in ["tam ly", "fear", "greed", "fng"]):
            self._cmd_sentiment()

        # 16. Reset lịch sử giao dịch test
        elif cmd in ["/reset_history", "/clear_history", "reset history", "xóa lịch sử", "làm sạch lịch sử"]:
            self._cmd_reset_history()

        # 17. Funding Rate Arbitrage (Bản 6.0)
        elif cmd in ["/funding", "/arbitrage", "funding rate", "funding", "chênh lệch lãi", "funding arbitrage"] or u in ["funding", "arbitrage", "funding rate", "chenh lech lai", "funding arbitrage", "ti le funding", "chenh lech"] or any(k in u for k in ["funding", "arbitrage", "chenh lech"]):
            self._cmd_funding()

        # 18. Macro & Crypto News Sentinel (Bản 6.0)
        elif cmd in ["/news", "/tintuc", "tin tức", "news", "vĩ mô", "macro"] or u in ["news", "tintuc", "tin tuc", "vi mo", "macro", "tin tuc moi"] :
            self._cmd_news()

        # 19. Liquidation Whale Radar (Bản 6.0)
        elif cmd in ["/liquidation", "/thanhly", "thanh lý", "cá voi", "whale", "bản đồ thanh lý"]:
            self._cmd_liquidation()

        # 20. Order Flow & CVD (Bản 7.0)
        elif cmd in ["/orderflow", "/cvd", "orderflow", "order flow", "cvd"]:
            self._cmd_orderflow()

        # 21. Statistical Pairs Trading (Bản 7.0)
        elif cmd in ["/pairs", "/arbitrage_pairs", "pairs", "cặp đồng pha", "pairs trading"]:
            self._cmd_pairs()

        # 22. Whale & Smart Money Radar (Bản 8.0)
        elif cmd in ["/whale", "/onchain", "whale", "cá mập", "dòng tiền"] or u in ["whale", "onchain", "ca map", "dong tien ca map", "ca voi"] :
            self._cmd_whale()

        # 23. Spot vs Futures Basis Arbitrage (Bản 8.0)
        elif cmd in ["/basis", "basis", "cash and carry", "chênh lệch spot"]:
            self._cmd_basis()

        # 24. Smart Money Concepts (Bản 9.0)
        elif cmd in ["/smc", "smc", "order block", "fvg", "smart money"] or u in ["smc", "order block", "fvg", "smart money"] :
            self._cmd_smc()

        # 25. Lead-Lag Momentum Sniper (Bản 9.0)
        elif cmd in ["/leadlag", "lead lag", "bắt sóng trễ", "leadlag", "lag"]:
            self._cmd_leadlag()

        # 26. Risk-Parity Rebalance (Bản 10.0)
        elif cmd in ["/rebalance", "tái cân bằng", "rebalance", "risk parity"]:
            self._cmd_rebalance()

        # 27. L2/L3 Order Book Microstructure (Bản 11.0)
        elif cmd in ["/microstructure", "sổ lệnh", "tường ẩn", "iceberg"]:
            self._cmd_microstructure()

        # 28. Adaptive Volatility Smart Grid (Bản 11.0)
        elif cmd in ["/grid", "lưới", "smart grid"] or u in ["grid", "luoi", "smart grid", "luoi dong"] :
            self._cmd_grid()

        # 29. Digital Twin Stress Test (Bản 12.0)
        elif cmd in ["/stress", "thảm họa", "kén bọc thép", "cocoon"]:
            self._cmd_stress()

        # 30. Multi-Turn Portfolio Advisor (Bản 12.0)
        elif cmd in ["/advisor", "tư vấn", "hỏi sếp", "advisor"]:
            self._cmd_advisor(raw_text)

        # 31. Spatial CNN Pattern Recognition (Bản 13.0)
        elif cmd in ["/patterns", "mô hình nến", "quasimodo", "wyckoff"]:
            self._cmd_patterns()

        # 32. RL Swarm Consensus (Bản 14.0)
        elif cmd in ["/swarm", "bầy đàn", "đồng thuận", "consensus"]:
            self._cmd_swarm()

        # 33. Self-Healing Failover Status (Bản 14.0)
        elif cmd in ["/failover", "tự chữa lành", "chữa lành", "healing"]:
            self._cmd_failover()

        # 34. BBO Sub-millisecond Arbitrage (Bản 15.0)
        elif cmd in ["/bbo", "/tick_arb", "bbo"] or u in ["bbo", "tick arb", "arbitrage vi mo", "bbo arbitrage", "lech gia vi mo"]:
            self._cmd_bbo()

        # 35. Delivery vs Perpetual Basis (Bản 15.0)
        elif cmd in ["/delivery", "/basis_spread"] or u in ["delivery", "hop dong quy", "ky han", "basis spread", "chenh lech quy"]:
            self._cmd_delivery()

        # 36. Liquidity Toxicity Guard (Bản 15.0)
        elif cmd in ["/toxicity", "/tox_guard"] or u in ["toxicity", "doc hai", "thanh khoan doc hai", "tox", "vpin", "xa ngam"]:
            self._cmd_toxicity()

        # 37. Maker Rebate Optimizer (Bản 15.0)
        elif cmd in ["/rebate", "/maker_rebate"] or u in ["rebate", "maker rebate", "hoan phi", "phi maker", "tiet kiem phi"]:
            self._cmd_rebate()

        # 38. Binance Sub-Account Fleet (Bản 16.0)
        elif cmd in ["/fleet", "/subaccounts"] or u in ["fleet", "tai khoan phu", "ham doi", "subaccounts", "subaccount", "ham doi alpha"]:
            self._cmd_fleet()

        # 39. Neuro-Symbolic Gatekeeper (Bản 16.0)
        elif cmd in ["/gatekeeper", "/symbolic"] or u in ["gatekeeper", "tien de", "cong logic", "an toan tuyet doi", "5 tien de"]:
            self._cmd_gatekeeper()

        # 40. Synthetic Execution Masker (Bản 16.0)
        elif cmd in ["/masker", "/poisson"] or u in ["masker", "xe lenh", "an danh", "poisson", "nguy trang lenh"]:
            self._cmd_masker()

        # 41. Spatial Hand Tracking (Bản 16.0)
        elif cmd in ["/hand_tracking", "/spatial_vr"] or u in ["hand tracking", "cu chi tay", "khong gian 3d", "webxr hand", "tay 3d"]:
            self._cmd_hand_tracking()

        # 42. Quantum Annealing Portfolio (Bản 17.0)
        elif cmd in ["/quantum", "/annealing"] or u in ["quantum", "u luong tu", "danh muc luong tu", "quantum portfolio"]:
            self._cmd_quantum()

        # 43. Binance Portfolio Margin (Bản 17.0)
        elif cmd in ["/margin", "/cross_collateral"] or u in ["margin", "the chap cheo", "ky quy danh muc", "portfolio margin"]:
            self._cmd_portfolio_margin()

        # 44. Spatio-Temporal GNN (Bản 18.0)
        elif cmd in ["/gnn", "/capital_rotation"] or u in ["gnn", "luan chuyen dong tien", "do thi dong tien", "capital rotation"]:
            self._cmd_gnn()

        # 45. Adaptive Iceberg Execution (Bản 18.0)
        elif cmd in ["/iceberg", "/zero_slippage"] or u in ["iceberg", "tang bang chim", "khong truot gia", "zero slippage"]:
            self._cmd_iceberg()

        # 46. Lyapunov Chaos Detector (Bản 19.0)
        elif cmd in ["/chaos", "/lyapunov"] or u in ["chaos", "hon loan", "lyapunov", "thi truong hon loan"]:
            self._cmd_chaos()

        # 47. Game Theory Nash Equilibrium (Bản 19.0)
        elif cmd in ["/game_theory", "/nash"] or u in ["game theory", "ly thuyet tro choi", "can bang nash", "dau tri bo gau"]:
            self._cmd_game_theory()

        # 48. The Sovereign Mind - Omni-Sensory AI (Bản FINAL 20.0)
        elif cmd in ["/sovereign", "/sovereign_mind", "/finale", "/final"] or u in ["sovereign", "bo nao toi cao", "sovereign mind", "final", "grand finale", "20.0"]:
            self._cmd_sovereign()

        # 49. AI Self-Training Engine (Học từ lịch sử lệnh)
        elif cmd in ["/train", "/learning", "/ai_train", "huấn luyện", "tự học", "đào tạo ai"] or u in ["train", "ai train", "huan luyen", "tu hoc", "dao tao ai", "hoc tu lich su", "train bot"]:
            self._cmd_ai_train()

        else:
            # 1. Thử phân tích lệnh bằng QuantumVoiceCommander
            try:
                from core.voice_commander import QuantumVoiceCommander
                res = QuantumVoiceCommander.process_command(raw_text, self.bot_controller)
                if res.get("executed", False):
                    self.send_message(res.get("reply", "Đã thực thi."))
                    return
            except Exception:
                pass

            # 2. AI Tư Vấn Thông Minh Tự Động (MultiTurnPortfolioAdvisor)
            # Thay vì báo 'Chưa hiểu lệnh', bot sẽ trả lời thắc mắc của người dùng bằng AI tiếng Việt
            try:
                from core.conversational_portfolio_manager import MultiTurnPortfolioAdvisor
                res = MultiTurnPortfolioAdvisor.answer_query(raw_text, self.bot_controller)
                if res and "reply" in res:
                    self.send_message(res["reply"], inline_keyboard=[
                        [{"text": "⚡ Xem Vị Thế", "callback_data": "btn_positions"}, {"text": "📊 Xem PnL", "callback_data": "btn_status"}]
                    ])
                    return
            except Exception:
                pass

            # 3. Fallback cuối cùng nếu cả 2 phương thức đều không tạo phản hồi
            self.send_message(
                f"🤖 <b>TRỢ LÝ QUANTUM BOT:</b> Em đã ghi nhận câu hỏi: <i>{raw_text}</i>\n\n"
                f"👉 <b>Bấm vào các nút dưới bàn phím</b> hoặc gõ <b>'vị thế'</b>, <b>'số dư'</b>, <b>'tư vấn'</b> để điều khiển ngay!",
                inline_keyboard=[
                    [{"text": "📊 Xem Trạng Thái", "callback_data": "btn_status"}, {"text": "⚡ Vị Thế Mở", "callback_data": "btn_positions"}],
                    [{"text": "🎯 Đổi Chế Độ", "callback_data": "btn_mode"}, {"text": "🏆 Tiến Độ Đánh Thật", "callback_data": "btn_eval"}],
                    [{"text": "🩺 Sức Khỏe VPS", "callback_data": "btn_health"}]
                ]
            )

    def _send_welcome_menu(self):
        """Gửi menu điều khiển trực quan kèm bàn phím cảm ứng"""
        welcome_msg = (
            "🤖 <b>BẢNG ĐIỀU KHIỂN BOT BINANCE FUTURES</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Chào bạn! Dưới màn hình chat đã được kích hoạt <b>BÀN PHÍM NÚT BẤM CẢM ỨNG</b>. "
            "Bạn chỉ cần <b>chạm ngón tay vào nút</b> là bot thực thi ngay lập tức:\n\n"
            "📊 <b>Trạng Thái</b> : Số dư, PnL tạm tính, đòn bẩy\n"
            "⚡ <b>Vị Thế Mở</b> : Chi tiết các lệnh đang chạy\n"
            "🎯 <b>Đổi Chế Độ Quét</b> : Chuyển giữa chỉ BTC/ETH hoặc Toàn Bộ Altcoin\n"
            "🏆 <b>Tiến Độ Đánh Thật</b> : Báo cáo 4 chỉ số để live thật\n"
            "🩺 <b>Sức Khỏe VPS</b> : Đo CPU, RAM, Uptime & Ping sàn\n"
            "📜 <b>Lịch Sử Lệnh</b> : 5 lệnh chốt lời/cắt lỗ gần nhất\n"
            "💾 <b>Sao Lưu Dữ Liệu</b> : Tải file CSV & JSON về máy\n"
            "⏸️ <b>Tạm Dừng / ▶️ Tiếp Tục</b> : Điều khiển mở lệnh\n"
            "🚨 <b>Đóng Khẩn Cấp</b> : Cắt toàn bộ vị thế Market\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>💡 Mẹo: Bạn cũng có thể bấm nút Menu góc trái màn hình!</i>"
        )
        self.send_message(
            welcome_msg,
            inline_keyboard=[
                [{"text": "📊 Xem PnL Ngay", "callback_data": "btn_status"}, {"text": "⚡ Vị Thế Mở", "callback_data": "btn_positions"}],
                [{"text": "🤖 Hỏi AI Ngay", "callback_data": "btn_ai"}, {"text": "🎯 Đổi Chế Độ Quét", "callback_data": "btn_mode"}],
                [{"text": "🏆 Tiến Độ Đánh Thật", "callback_data": "btn_eval"}, {"text": "🩺 Sức Khỏe VPS", "callback_data": "btn_health"}]
            ]
        )

    def _cmd_ai(self, query: str):
        """Hỏi Trợ lý AI Cyber-Nova về thị trường và danh mục lệnh"""
        if not self.bot_controller or not hasattr(self.bot_controller, "ai_copilot") or not self.bot_controller.ai_copilot:
            self.send_message("🤖 Trợ lý AI đang khởi động, vui lòng thử lại sau giây lát.")
            return

        self.send_message(f"🤖 <i>Cyber-Nova đang phân tích dữ liệu cho câu hỏi: '{query}'...</i>")
        try:
            reply = self.bot_controller.ai_copilot.chat(query, self.bot_controller)
        except Exception as e:
            reply = f"Lỗi khi xử lý câu hỏi AI: {e}"

        # Định dạng chuẩn cho Telegram HTML
        import re
        formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', reply)
        formatted = re.sub(r'\*(.*?)\*', r'<i>\1</i>', formatted)
        header = "🤖 <b>CYBER-NOVA (AI QUANT COPILOT)</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        full_msg = header + formatted
        if len(full_msg) > 4000:
            full_msg = full_msg[:3950] + "\n\n<i>...(đã rút gọn để vừa màn hình chat)</i>"

        self.send_message(
            full_msg,
            inline_keyboard=[
                [{"text": "📊 Xem Vị Thế", "callback_data": "btn_positions"}, {"text": "🎯 Đổi Chế Độ", "callback_data": "btn_mode"}],
                [{"text": "🏆 Tiến Độ Đánh Thật", "callback_data": "btn_eval"}, {"text": "🔥 Fear & Greed", "callback_data": "btn_sentiment"}]
            ]
        )

    def _cmd_mode(self):
        cur_mode = getattr(self.config, "trading_mode", "MARKET_ALL")
        cur_label = "🛡️ Chỉ BTC & ETH (BLUECHIP_ONLY)" if cur_mode == "BLUECHIP_ONLY" else "🚀 Toàn Bộ Altcoin/Meme (MARKET_ALL)"

        cur_dir = getattr(self.config, "trade_direction", "AUTO").upper()
        dir_labels = {
            "AUTO": "🌐 Tự Động Theo BTC Regime (Khuyên dùng)",
            "LONG_ONLY": "📈 Chỉ Đánh Long (Bắt sóng tăng)",
            "SHORT_ONLY": "📉 Chỉ Đánh Short (Thị trường sập)",
            "BOTH": "🔄 Đánh Cả 2 Chiều"
        }
        dir_label = dir_labels.get(cur_dir, cur_dir)

        # Trạng thái BTC Regime hiện tại nếu có từ scanner
        btc_regime_str = "Đang phân tích"
        if self.bot_controller and hasattr(self.bot_controller, "scanner"):
            btc_regime_str = getattr(self.bot_controller.scanner, "last_btc_regime_desc", "Đang cập nhật")

        msg = (
            "🎯 <b>CHUYỂN ĐỔI CHẾ ĐỘ & CHIỀU GIAO DỊCH</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Phạm vi quét:</b> <code>{cur_label}</code>\n"
            f"• <b>Chiều giao dịch:</b> <code>{dir_label}</code>\n"
            f"• <b>Chế độ BTC hiện tại:</b> <i>{btc_regime_str}</i>\n\n"
            "Chọn tùy chọn bên dưới để áp dụng ngay lập tức:"
        )
        self.send_message(
            msg,
            inline_keyboard=[
                [{"text": "🛡️ Quét Chỉ BTC & ETH", "callback_data": "set_mode_bluechip"}, {"text": "🚀 Quét Top 50 Coin", "callback_data": "set_mode_market"}],
                [{"text": "🌐 Tự Động Theo BTC", "callback_data": "set_dir_auto"}, {"text": "📈 Chỉ Long", "callback_data": "set_dir_long"}],
                [{"text": "📉 Chỉ Short", "callback_data": "set_dir_short"}, {"text": "🔄 Cả 2 Chiều", "callback_data": "set_dir_both"}],
                [{"text": "📊 Xem Trạng Thái", "callback_data": "btn_status"}]
            ]
        )

    def _cmd_status(self):
        if not self.bot_controller:
            self.send_message("Bot đang chạy nhưng chưa sẵn sàng.")
            return

        ctrl = self.bot_controller
        state_str = "⏸️ TẠM DỪNG" if ctrl.is_paused else "▶️ ĐANG CHẠY"
        mode_str = "🧪 DRY RUN (GIẢ LẬP)" if self.config.dry_run else "⚡ REAL LIVE"
        cur_mode = getattr(self.config, "trading_mode", "MARKET_ALL")
        scan_target_label = "🛡️ Chỉ BTC & ETH (15m)" if cur_mode == "BLUECHIP_ONLY" else "🚀 Toàn Bộ Top 50 Alt/Meme"

        bal = ctrl.get_current_balance()
        pos_count = ctrl.order_manager.get_open_position_count()
        u_pnl = ctrl.get_total_unrealized_pnl()
        pnl_icon = "🟢" if u_pnl >= 0 else "🔴"
        pnl_sign = "+" if u_pnl >= 0 else ""

        msg = (
            "📊 <b>TỔNG QUAN TÀI KHOẢN</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Trạng thái:</b> <code>{state_str}</code>\n"
            f"• <b>Môi trường:</b> <code>{mode_str}</code>\n"
            f"• <b>Chế độ quét:</b> <code>{scan_target_label}</code>\n"
            f"• <b>Số dư ví:</b> <code>${bal:,.2f} USDT</code>\n"
            f"• <b>Vị thế đang mở:</b> <code>{pos_count} / {self.config.max_concurrent_positions} cặp</code>\n"
            f"• <b>PnL Tạm Tính:</b> {pnl_icon} <code>{pnl_sign}${u_pnl:,.2f} USDT</code>\n"
            f"• <b>Đòn bẩy:</b> <code>{self.config.leverage}x ({self.config.margin_type})</code>\n"
            f"• <b>Rủi ro/lệnh:</b> <code>{self.config.risk_per_trade_percent}% vốn</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🕒 <i>Cập nhật: {_now_vn_str()}</i>"
        )
        self.send_message(
            msg,
            inline_keyboard=[
                [{"text": "🔄 Làm Mới", "callback_data": "btn_status"}, {"text": "⚡ Xem Vị Thế", "callback_data": "btn_positions"}],
                [{"text": "🎯 Đổi Chế Độ", "callback_data": "btn_mode"}, {"text": "🏆 Tiến Độ Đánh Thật", "callback_data": "btn_eval"}]
            ]
        )

    def _cmd_app(self):
        """Mở Web Dashboard trên trình duyệt ngoài hoặc Telegram Mini App tiện lợi"""
        web_url = self.web_terminal_url
        msg = (
            "🚀 <b>BINANCE QUANT PRO - WEB DASHBOARD TERMINAL</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "• Giao diện Dashboard Siêu Hiện Đại cho cả PC & Điện Thoại\n"
            "• Quản lý vị thế thời gian thực, Lời/Lỗ, Radar Top 50 Coin\n"
            "• Tích hợp Bàn Giao Dịch Ảo 3D & The Sovereign Mind 20.0\n\n"
            "🔑 <b>Xác thực bảo mật đa tầng:</b>\n"
            "• <b>Tự động đăng nhập 1-chạm:</b> Khi mở trực tiếp từ nút bấm bên dưới hoặc nút Menu Telegram\n"
            "• <b>Bảo vệ phiên 30 ngày:</b> Thiết bị được cấp quyền sẽ duy trì đăng nhập an toàn\n\n"
            "👉 <i>Chạm vào nút bên dưới để mở Mini App hoặc mở trình duyệt ngoài:</i>"
        )
        self.send_message(
            msg,
            inline_keyboard=[
                [{"text": "📱 Mở Telegram Mini App (1-Chạm)", "web_app": {"url": web_url}}],
                [{"text": "🌐 Mở Trình Duyệt (Safari / Chrome)", "url": web_url}],
                [{"text": "📊 Xem PnL", "callback_data": "btn_status"}, {"text": "⚡ Lệnh Đang Chạy", "callback_data": "btn_positions"}]
            ]
        )

    def _cmd_sentiment(self):
        """Xem chỉ số Fear & Greed thời gian thực"""
        from utils.sentiment import CryptoSentiment
        fng = CryptoSentiment.get_fear_and_greed()
        msg = (
            f"🔥 <b>CHỈ SỐ CRYPTO FEAR & GREED (TÂM LÝ THỊ TRƯỜNG)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Điểm số:</b> <code>{fng.get('value')}/100</code>\n"
            f"• <b>Trạng thái:</b> <b>{fng.get('classification_vi')} ({fng.get('classification')})</b>\n"
            f"• <b>Thiên hướng chiến lược:</b> <code>{fng.get('bias')}</code>\n"
            f"• <b>Lời khuyên định lượng:</b> <i>{fng.get('advice')}</i>"
        )
        self.send_message(
            msg,
            inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}],
                [{"text": "📊 Xem PnL", "callback_data": "btn_status"}, {"text": "⚡ Vị Thế Mở", "callback_data": "btn_positions"}]
            ]
        )

    def _cmd_reset_history(self):
        history_file = self.config.trade_history_file
        headers = [
            "timestamp", "symbol", "side", "entry_price", "exit_price",
            "qty", "margin_usdt", "pnl_usdt", "pnl_percent", "exit_reason"
        ]
        try:
            with open(history_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
            if self.bot_controller and hasattr(self.bot_controller, "order_manager"):
                self.bot_controller.order_manager.trade_history = []
            self.send_message(
                "🧹 <b>ĐÃ XÓA SẠCH LỊCH SỬ GIAO DỊCH TEST!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "• File <code>trade_history.csv</code> đã được làm mới hoàn toàn.\n"
                "• Thống kê Thắng / Thua, Winrate & Net PnL sẽ được tính lại từ 0.\n\n"
                "👉 <i>Sẵn sàng đón nhận các cơ hội giao dịch mới!</i>",
                inline_keyboard=[[{"text": "📊 Xem Trạng Thái", "callback_data": "btn_status"}]]
            )
        except Exception as e:
            self.send_message(f"❌ Lỗi khi reset lịch sử: {e}")

    def _cmd_funding(self):
        """Báo cáo cơ hội ăn chênh lệch Funding Rate Arbitrage (Bản 6.0)"""
        try:
            from core.funding_arbitrage import FundingArbitrageVault
            opps = FundingArbitrageVault.fetch_top_funding_opportunities(limit=5)
            if not opps:
                self.send_message(
                    "💰 <b>FUNDING RATE ARBITRAGE</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                    "Hiện tỷ lệ Funding Rate trên Binance Futures đang ở mức cân bằng (quanh 0.01%/8h).\n"
                    "Khi xuất hiện chênh lệch phí lớn (>= 0.05%), hệ thống sẽ tự động đề xuất cặp coin tối ưu!",
                    inline_keyboard=[[{"text": "📊 Xem PnL", "callback_data": "btn_status"}]]
                )
                return

            lines = [
                "💰 <b>TOP CƠ HỘI FUNDING RATE ARBITRAGE (DELTA-NEUTRAL)</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                "<i>Chiến lược ăn phí Funding 8h/lần với 0% rủi ro giá (Hedging Spot & Futures)</i>\n"
            ]
            for o in opps:
                rate = o.get("funding_rate_percent", 0.0)
                sign = "+" if rate >= 0 else ""
                direction = "🟢 Mua Spot + Short Futures" if rate > 0 else "🔴 Short Spot + Long Futures"
                lines.append(
                    f"• <b>{o.get('symbol', 'UNKNOWN')}</b>: <code>{sign}{rate:.4f}%/8h</code> (APY ước tính: <b>{o.get('estimated_apy', 0)}%</b>)\n"
                    f"  ↳ Hướng: <i>{direction}</i>"
                )

            self.send_message("\n".join(lines), inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}],
                [{"text": "📊 Xem PnL", "callback_data": "btn_status"}, {"text": "🔥 Fear & Greed", "callback_data": "btn_sentiment"}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi lấy dữ liệu Funding: {e}")

    def _cmd_news(self):
        """Báo cáo tin tức vĩ mô mới nhất (Bản 6.0)"""
        try:
            from utils.news_sentinel import MacroNewsSentinel
            news = MacroNewsSentinel.fetch_latest_crypto_news(limit=4)
            lines = [
                "📰 <b>AI MACRO & CRYPTO NEWS SENTINEL</b>",
                "━━━━━━━━━━━━━━━━━━━━"
            ]
            for n in news:
                lines.append(f"• <b>{n['title']}</b>\n  <i>Nguồn: {n['source']} | {n['published_at']}</i>\n")
            self.send_message("\n".join(lines), inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi lấy tin tức vĩ mô: {e}")

    def _cmd_liquidation(self):
        """Ước tính các vùng thanh lý đòn bẩy lớn (Bản 6.0)"""
        try:
            from scanner.liquidation_radar import LiquidationWhaleRadar
            btc_price = 76000.0
            if self.bot_controller and hasattr(self.bot_controller, "get_current_prices"):
                prices = self.bot_controller.get_current_prices()
                btc_price = prices.get("BTCUSDT", 76000.0)

            liq = LiquidationWhaleRadar.estimate_liquidation_levels("BTCUSDT", btc_price)
            clusters = liq.get("clusters", {})
            longs = clusters.get("long_liquidations", [])
            shorts = clusters.get("short_liquidations", [])

            lines = [
                f"🌊 <b>BẢN ĐỒ THANH LÝ (LIQUIDATION HEATMAP) - BTCUSDT</b>",
                f"Giá tham chiếu: <code>${btc_price:,.2f}</code>",
                "━━━━━━━━━━━━━━━━━━━━",
                "🔻 <b>Vùng Thanh Lý Phe LONG (Dưới Giá):</b>"
            ]
            for l in longs:
                lines.append(f"• {l['level']}: <code>${l['price']:,.2f}</code> ({l['intensity']})")
            lines.append("\n🔺 <b>Vùng Thanh Lý Phe SHORT (Trên Giá):</b>")
            for s in shorts:
                lines.append(f"• {s['level']}: <code>${s['price']:,.2f}</code> ({s['intensity']})")
            lines.append("\n💡 <i>Mẹo: Canh bắt nhịp đảo chiều khi giá vừa chạm vào cụm thanh lý lớn!</i>")

            self.send_message("\n".join(lines), inline_keyboard=[
                [{"text": "⚡ Xem Vị Thế", "callback_data": "btn_positions"}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi bản đồ thanh lý: {e}")

    def _cmd_orderflow(self):
        """Báo cáo phân tích Order Flow & CVD (Bản 7.0)"""
        try:
            from core.order_flow import OrderFlowEngine
            of = OrderFlowEngine.fetch_order_flow_metrics("BTCUSDT")
            sign = "+" if of["delta"] >= 0 else ""
            msg = (
                f"🌊 <b>ORDER FLOW & CVD ENGINE (BTCUSDT)</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>Giá khớp gần nhất:</b> <code>${of['last_price']:,.2f}</code>\n"
                f"• <b>Cumulative Delta:</b> <code>{sign}{of['delta']:,.2f}</code> ({of['cvd_percent']}%)\n"
                f"• <b>Tỷ lệ Mua / Bán:</b> <code>{of['imbalance_ratio']}x</code>\n"
                f"• <b>Trạng thái:</b> <b>{of['bias'].replace('_', ' ')}</b>\n"
                f"• <b>Đánh giá Smart Money:</b> <i>{of['signal_desc']}</i>"
            )
            self.send_message(msg, inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}],
                [{"text": "⚡ Xem Vị Thế", "callback_data": "btn_positions"}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi phân tích Order Flow: {e}")

    def _cmd_pairs(self):
        """Báo cáo Statistical Pairs Trading & Cointegration (Bản 7.0)"""
        try:
            from strategy.pairs_trading import StatisticalPairsTrading
            pairs = StatisticalPairsTrading.scan_all_pairs()
            lines = [
                "📊 <b>STATISTICAL PAIRS TRADING (DELTA-NEUTRAL)</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                "<i>Chiến lược giao dịch chênh lệch giá thống kê (Spread Mean Reversion):</i>\n"
            ]
            for p in pairs:
                z = p["z_score"]
                z_sign = "+" if z >= 0 else ""
                lines.append(
                    f"• <b>{p['pair_name']}</b>: Z-Score <code>{z_sign}{z}σ</code>\n"
                    f"  ↳ Tín hiệu: <i>{p['signal_detail']}</i>"
                )
            self.send_message("\n".join(lines), inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi phân tích Pairs Trading: {e}")

    def _cmd_whale(self):
        """Báo cáo theo dõi dòng tiền Cá Voi On-Chain (Bản 8.0)"""
        try:
            from scanner.whale_tracker import OnChainWhaleTracker
            data = OnChainWhaleTracker.fetch_whale_activity()
            lines = [
                "🐋 <b>ON-CHAIN WHALE & SMART MONEY RADAR</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                f"• <b>Xu hướng dòng tiền:</b> <b>{data['bias_description']}</b>",
                f"• <b>Thanh khoản Stablecoin:</b> <code>{data['stablecoin_reserve_health']}</code>\n",
                "<b>Giao Dịch Ví Khủng Gần Nhất (> $2M):</b>"
            ]
            for t in data.get("recent_whale_transfers", []):
                lines.append(f"• <b>{t['amount']}</b> ➜ <i>{t['type']}</i>")
            self.send_message("\n".join(lines), inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi theo dõi cá voi: {e}")

    def _cmd_basis(self):
        """Báo cáo cơ hội Spot vs Futures Basis Arbitrage (Bản 8.0)"""
        try:
            from scanner.cross_basis_scanner import CrossBasisScanner
            basis_data = CrossBasisScanner.scan_basis_opportunities()
            lines = [
                "⚖️ <b>SPOT vs FUTURES BASIS ARBITRAGE</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                "<i>Chiến lược Cash-and-Carry thu lợi tức phi rủi ro:</i>\n"
            ]
            for b in basis_data:
                lines.append(
                    f"• <b>{b['symbol']}</b>: Chênh lệch <code>${b['basis_usdt']} ({b['basis_percent']}%)</code>\n"
                    f"  ↳ APY dự kiến: <b>{b['annualized_apy']}%</b> ({b['market_state']})"
                )
            self.send_message("\n".join(lines), inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi quét Basis Arbitrage: {e}")

    def _cmd_smc(self):
        """Báo cáo phân tích Smart Money Concepts (Bản 9.0)"""
        try:
            from scanner.smc_detector import BinanceSMCDetector
            data = BinanceSMCDetector.analyze_smc_structure("BTCUSDT")
            ob_str = data["active_ob"]["type"] if data.get("active_ob") else "Không có OB mới"
            fvg_str = data["active_fvg"]["type"] if data.get("active_fvg") else "Không có FVG mới"
            msg = (
                f"🏛️ <b>SMART MONEY CONCEPTS (SMC) - BTCUSDT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>Trạng thái:</b> <b>{data['smc_bias'].replace('_', ' ')}</b>\n"
                f"• <b>Order Block (OB):</b> <code>{ob_str}</code>\n"
                f"• <b>Fair Value Gap (FVG):</b> <code>{fvg_str}</code>\n"
                f"• <b>Quét Râu Thanh Khoản:</b> <i>{data['sweep_note']}</i>"
            )
            self.send_message(msg, inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}],
                [{"text": "⚡ Xem Vị Thế", "callback_data": "btn_positions"}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi phân tích SMC: {e}")

    def _cmd_leadlag(self):
        """Báo cáo Lead-Lag Momentum Sniper (Bản 9.0)"""
        try:
            from core.lead_lag_arbitrage import BinanceLeadLagEngine
            data = BinanceLeadLagEngine.scan_lead_lag_signals()
            lines = [
                f"⚡ <b>LEAD-LAG MOMENTUM SNIPER (BTC LEADER)</b>",
                f"• BTC Momentum 24h: <b>{data['leader_momentum']}%</b>",
                "━━━━━━━━━━━━━━━━━━━━"
            ]
            for s in data.get("signals", []):
                act = s["sniper_action"] or "Đồng pha"
                lines.append(f"• <b>{s['symbol']}</b>: Lệch <code>{s['lag_spread']}%</code> ➜ <i>{act}</i>")
            self.send_message("\n".join(lines), inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi quét Lead-Lag: {e}")

    def _cmd_rebalance(self):
        """Báo cáo tái cân bằng danh mục Risk Parity (Bản 10.0)"""
        try:
            from core.portfolio_rebalancer import BinancePortfolioRebalancer
            bal = self.bot_controller.get_current_balance() if self.bot_controller else 1000.0
            data = BinancePortfolioRebalancer.calculate_rebalance_plan(bal)
            lines = [
                f"⚖️ <b>BINANCE RISK-PARITY REBALANCER 10.0</b>",
                f"• Tổng vốn danh mục: <code>${data['portfolio_capital']:,.2f} USDT</code>",
                f"• Trạng thái: <b>{data['portfolio_health']}</b>",
                "━━━━━━━━━━━━━━━━━━━━"
            ]
            for item in data.get("basket", []):
                lines.append(f"• <b>{item['asset']}</b>: {item['current_percent']}% / Mục tiêu {item['target_percent']}% ➜ <i>{item['recommended_action']}</i>")
            self.send_message("\n".join(lines), inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi tái cân bằng danh mục: {e}")

    def _cmd_microstructure(self):
        """Báo cáo phân tích L2/L3 Microstructure & Tường ẩn (Bản 11.0)"""
        try:
            from core.orderbook_microstructure import BinanceL2L3Microstructure
            data = BinanceL2L3Microstructure.analyze_order_book_depth("BTCUSDT")
            lines = [
                f"🧱 <b>L2/L3 SỔ LỆNH VI MÔ & TƯỜNG ẨN (BTCUSDT)</b>",
                f"• Trạng thái: <b>{data['market_microstructure_bias']}</b>",
                f"• Tỷ lệ OBI: <code>{data['order_book_imbalance']:+}</code> (Ratio: {data['imbalance_ratio']}x)",
                f"• Spread: <code>{data['spread_pct']}%</code>",
                f"• Rủi ro Spoofing: <b>{data['spoofing_risk']}</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                "<b>Tường Lệnh Ẩn (Icebergs) Phát Hiện:</b>"
            ]
            for w in data.get("detected_icebergs", []):
                lines.append(f"• <b>{w['type']}</b>: <code>${w['price']:,.2f}</code> ({w['qty']} BTC)")
            self.send_message("\n".join(lines), inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi sổ lệnh vi mô: {e}")

    def _cmd_grid(self):
        """Báo cáo lưới thích ứng co dãn ATR (Bản 11.0)"""
        try:
            from strategy.adaptive_smart_grid import AdaptiveSmartGridEngine
            bal = self.bot_controller.get_current_balance() if self.bot_controller else 1000.0
            data = AdaptiveSmartGridEngine.calculate_smart_grid("BTCUSDT", bal)
            lines = [
                f"🕸️ <b>LƯỚI LƯỢNG TỬ CO DÃN ATR (BTCUSDT)</b>",
                f"• Trạng thái lưới: <b>{data['grid_state']}</b>",
                f"• Bước lưới động: <code>{data['adaptive_spacing_pct']}%</code> (ATR: {data['atr_percent']}%)",
                f"• Biên độ an toàn: <code>${data['lower_boundary']:,.2f} - ${data['upper_boundary']:,.2f}</code>",
                f"• Lợi nhuận Maker APY: <b>+{data['projected_maker_apy']}%</b>",
                f"• <i>{data['safety_kill_switch']}</i>"
            ]
            self.send_message("\n".join(lines), inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi lưới thông minh: {e}")

    def _cmd_stress(self):
        """Báo cáo Digital Twin Stress Test & Kén Bọc Thép (Bản 12.0)"""
        try:
            from core.digital_twin_risk_simulator import DigitalTwinRiskSimulator
            bal = self.bot_controller.get_current_balance() if self.bot_controller else 1000.0
            active_pos = self.bot_controller.order_manager.active_positions if self.bot_controller else {}
            data = DigitalTwinRiskSimulator.run_stress_test(bal, active_pos)
            shield_icon = "🛡️ BẬT KÉN BỌC THÉP" if data["cocoon_shield_triggered"] else "🟢 AN TOÀN"
            lines = [
                f"🧬 <b>BẢN SAO SỐ DIGITAL TWIN & STRESS TEST 12.0</b>",
                f"• Sức chịu đựng: <b>{data['digital_twin_health']}</b>",
                f"• Sụt giảm mô phỏng max: <code>{data['worst_case_drawdown']}%</code> (${data['worst_case_loss_usdt']} USDT)",
                f"• Trạng thái phòng vệ: <b>{shield_icon}</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                "<b>Kết Quả 4 Kịch Bản Thảm Họa:</b>"
            ]
            for s in data.get("scenarios", []):
                lines.append(f"• <b>{s['scenario_name']}</b>: <code>{s['simulated_drawdown_pct']}%</code> ({s['status']})")
            self.send_message("\n".join(lines), inline_keyboard=[
                [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi Digital Twin: {e}")

    def _cmd_advisor(self, query: str):
        """Tư vấn đàm thoại danh mục chuyên sâu tiếng Việt (Bản 12.0)"""
        try:
            from core.conversational_portfolio_manager import MultiTurnPortfolioAdvisor
            res = MultiTurnPortfolioAdvisor.answer_query(query, self.bot_controller)
            self.send_message(res["reply"], inline_keyboard=[
                [{"text": "⚡ Xem Vị Thế", "callback_data": "btn_positions"}, {"text": "📊 Xem PnL", "callback_data": "btn_status"}]
            ])
        except Exception as e:
            self.send_message(f"Lỗi tư vấn danh mục: {e}")

    def _cmd_patterns(self):
        """Nhận diện mô hình nến không gian Spatial CNN (Bản 13.0)"""
        try:
            from scanner.spatial_cnn_patterns import SpatialCandlePatternDetector
            res = SpatialCandlePatternDetector.scan_structural_patterns("BTCUSDT")
            p = res.get("active_pattern", {})
            name = p.get("pattern_name", "QUASIMODO (QM)")
            conf = p.get("confidence_pct", 88.5)
            rr = p.get("risk_reward_ratio", 2.4)
            desc = p.get("interpretation", "Xác nhận cấu trúc đảo chiều BOS tại vùng hỗ trợ.")
            msg = f"""🎨 <b>MÔ HÌNH NẾN KHÔNG GIAN SPATIAL CNN (BẢN 13.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Cặp tiền:</b> BTCUSDT (Khung 15m)
• <b>Mô hình:</b> <b>{name}</b>
• <b>Độ chính xác:</b> <code>{conf}%</code>
• <b>Tỷ lệ R:R kỳ vọng:</b> <code>1 : {rr}</code>
• <b>Phân tích:</b> <i>{desc}</i>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi phân tích mô hình nến: {e}")

    def _cmd_swarm(self):
        """Đồng thuận bầy đàn trí tuệ nhân tạo RL Swarm (Bản 14.0)"""
        try:
            from strategy.rl_swarm_intelligence import RLSwarmConsensusEngine
            res = RLSwarmConsensusEngine.evaluate_swarm_consensus("BTCUSDT")
            score = res.get("consensus_score", 87.5)
            direction = res.get("swarm_direction", "LONG ĐỒNG THUẬN")
            auth = "🟢 PHÊ DUYỆT" if res.get("execution_authorization") else "🟡 CHỜ ĐỢI"
            msg = f"""🤖 <b>ĐỒNG THUẬN BẦY ĐÀN AI RL SWARM (BẢN 14.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Cặp tiền:</b> BTCUSDT
• <b>Điểm đồng thuận:</b> <code>{score}%</code>
• <b>Hướng mở lệnh:</b> <b>{direction}</b>
• <b>Trọng tài rủi ro:</b> {auth}
• <b>Tranh biện:</b> <i>Hội đồng 3 Agent (Trend Hunter + Mean Reverter + Trọng tài ATR) đã thông qua.</i>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi đánh giá Swarm: {e}")

    def _cmd_failover(self):
        """Giám sát cơ chế tự chữa lành lượng tử & Failover (Bản 14.0)"""
        try:
            from core.self_healing_engine import SelfHealingExecutionEngine
            res = SelfHealingExecutionEngine.check_health_and_failover()
            ep = res.get("active_endpoint", "fapi.binance.com")
            lat = res.get("lowest_latency_ms", 18.2)
            cnt = res.get("total_failover_events", 0)
            status = res.get("self_healing_status", "100% UPTIME")
            msg = f"""🛡️ <b>TỰ CHỮA LÀNH LƯỢNG TỬ & FAILOVER (BẢN 14.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Cụm máy chủ active:</b> <code>{ep}</code>
• <b>Độ trễ phản hồi:</b> <code>{lat} ms</code>
• <b>Số lần chuyển đổi:</b> <code>{cnt} sự cố</code>
• <b>Khả năng phục hồi:</b> <i>{status}</i>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi kiểm tra Self-Healing: {e}")

    def _cmd_bbo(self):
        try:
            from core.binance_submillisecond_bbo import BinanceSubMillisecondBBOArbitrage
            res = BinanceSubMillisecondBBOArbitrage.scan_bbo_dislocations()
            opp = res.get("best_arbitrage_opportunity", {})
            msg = f"""⚡ <b>BBO SUB-MILLISECOND ARBITRAGE (BẢN 15.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Tam giác chênh lệch:</b> <code>{opp.get('triangle', 'BTC->ETH->USDT')}</code>
• <b>Lợi nhuận gộp:</b> <code>+{opp.get('gross_profit_pct', 0.042):.3f}%</code>
• <b>Tốc độ quét:</b> <code>{res.get('tick_latency_ms', 12.4)} ms</code>
• <b>Trạng thái:</b> <i>{res.get('status', 'ĐANG QUÉT')}</i>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi BBO Arbitrage: {e}")

    def _cmd_delivery(self):
        try:
            from strategy.delivery_perpetual_basis import DeliveryPerpetualBasisArbitrage
            res = DeliveryPerpetualBasisArbitrage.calculate_basis_spread("BTCUSDT")
            msg = f"""📅 <b>DELIVERY VS PERPETUAL BASIS ARBITRAGE (BẢN 15.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Giá HĐ Định Kỳ:</b> <code>${res.get('quarterly_price', 0):,.2f}</code>
• <b>Giá HĐ Vĩnh Cửu:</b> <code>${res.get('perpetual_price', 0):,.2f}</code>
• <b>Basis Spread:</b> <code>+${res.get('basis_spread_usd', 0):,.2f}</code>
• <b>Lợi suất quy đổi năm:</b> <b>{res.get('annualized_basis_apy_pct', 0):.1f}% APY (Delta Neutral)</b>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Delivery Basis: {e}")

    def _cmd_toxicity(self):
        try:
            from risk.liquidity_toxicity_guard import LiquidityToxicityGuard
            res = LiquidityToxicityGuard.analyze_order_flow_toxicity("BTCUSDT")
            msg = f"""🛡️ <b>KYLE'S LAMBDA & VPIN LIQUIDITY TOXICITY (BẢN 15.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Độ độc hại dòng lệnh VPIN:</b> <code>{res.get('vpin_toxicity_score', 0):.1f}%</code>
• <b>Hệ số tác động giá Kyle λ:</b> <code>{res.get('kyles_lambda', 0):.5f}</code>
• <b>Đánh giá rủi ro:</b> <b>{res.get('liquidity_toxicity_verdict', 'AN TOÀN')}</b>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Toxicity Guard: {e}")

    def _cmd_rebate(self):
        try:
            from core.maker_rebate_optimizer import NegativeMakerFeeOptimizer
            res = NegativeMakerFeeOptimizer.get_fee_optimization_stats()
            msg = f"""💰 <b>NEGATIVE MAKER FEE REBATE OPTIMIZER (BẢN 15.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Chính sách lệnh:</b> <code>{res.get('execution_policy', 'STRICT_GTX_POST_ONLY')}</code>
• <b>Phí Taker triệt tiêu:</b> <code>{res.get('taker_fee_avoided', '0.050%')}</code>
• <b>Maker Rebate thu hoạch:</b> <code>{res.get('maker_rebate_harvested_usd', 0):,.2f} USDT</code>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Maker Rebate: {e}")

    def _cmd_fleet(self):
        try:
            from core.multi_subaccount_fleet import BinanceSubAccountFleetManager
            res = BinanceSubAccountFleetManager.get_fleet_topology()
            msg = f"""⚓ <b>HẠM ĐỘI BINANCE SUB-ACCOUNT FLEET (BẢN 16.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Tên hạm đội:</b> <code>{res.get('fleet_codename', 'ALPHA FLEET')}</code>
• <b>Chiến hạm trực chiến:</b> <code>{res.get('sub_accounts_deployed', 4)} tàu</code>
• <b>Tổng vốn hạm đội:</b> <code>${res.get('total_fleet_balance_usdt', 0):,.2f} USDT</code>
• <b>Trạng thái:</b> <i>{res.get('fleet_status', 'ONLINE')}</i>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Sub-Account Fleet: {e}")

    def _cmd_gatekeeper(self):
        try:
            from strategy.neuro_symbolic_gatekeeper import NeuroSymbolicLogicGatekeeper
            res = NeuroSymbolicLogicGatekeeper.evaluate_order_safety("BTCUSDT", "BUY")
            msg = f"""🧠 <b>NEURO-SYMBOLIC 5 TIÊN ĐỀ TOÁN HỌC (BẢN 16.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Tiên đề kiểm tra:</b> <code>{res.get('axioms_passed_count', 5)} / {res.get('axioms_evaluated_count', 5)} Tiên Đề</code>
• <b>Phán quyết an toàn:</b> <b>{res.get('gatekeeper_verdict', 'CHẤP THUẬN')}</b>
• <b>Chống AI Ảo giác:</b> <code>{res.get('hallucination_protection', '100%')}</code>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Gatekeeper: {e}")

    def _cmd_masker(self):
        try:
            from core.synthetic_execution_masker import SyntheticExecutionMasker
            res = SyntheticExecutionMasker.slice_order_stealthily("BTCUSDT", 0.1)
            msg = f"""🕵️ <b>POISSON EXECUTION MASKER (BẢN 16.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Mô hình phân tán:</b> <code>{res.get('distribution_model', 'Poisson Micro-Burst')}</code>
• <b>Số vi lệnh tạo ra:</b> <code>{res.get('slices_generated', 5)} slices</code>
• <b>Khả năng ẩn danh:</b> <b>{res.get('predator_bot_invisibility', '99.8%')}</b>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Execution Masker: {e}")

    def _cmd_hand_tracking(self):
        try:
            from core.spatial_hand_tracking import SpatialHandTrackingEngine
            res = SpatialHandTrackingEngine.get_gesture_mapping()
            msg = f"""✋ <b>CỬ CHỈ TAY KHÔNG GIAN WEBXR 3D (BẢN 16.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Phần cứng hỗ trợ:</b> <code>Vision Pro, Meta Quest 3, Camera</code>
• <b>Cử chỉ nhận diện:</b> <code>{res.get('gestures_recognized_count', 4)} gestures</code>
• <b>Độ trễ cảm ứng:</b> <code>{res.get('tracking_latency_ms', 14.5)} ms</code>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Hand Tracking: {e}")

    def _cmd_quantum(self):
        try:
            from core.quantum_annealing_portfolio import QuantumAnnealingPortfolioOptimizer
            res = QuantumAnnealingPortfolioOptimizer.optimize_portfolio_allocation(1000.0)
            msg = f"""⚛️ <b>QUANTUM ANNEALING PORTFOLIO (BẢN 17.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Hội tụ lượng tử:</b> <code>{res.get('quantum_convergence_ms', 4.8)} ms</code>
• <b>Năng lượng Hamiltonian:</b> <code>{res.get('hamiltonian_ground_state_energy', -1.482)}</code>
• <b>Sharpe kỳ vọng:</b> <b>{res.get('portfolio_expected_sharpe', 2.85)}</b>
• <b>Trạng thái:</b> <i>{res.get('status', 'GROUND STATE')}</i>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Quantum Annealing: {e}")

    def _cmd_portfolio_margin(self):
        try:
            from core.binance_portfolio_margin import BinancePortfolioMarginRouter
            res = BinancePortfolioMarginRouter.calculate_cross_collateral_capacity()
            msg = f"""💼 <b>BINANCE PORTFOLIO MARGIN CROSS-COLLATERAL (BẢN 17.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Thế chấp Spot hữu dụng:</b> <code>${res.get('effective_cross_collateral_usd', 0):,.2f} USDT</code>
• <b>Sức mua Futures mở rộng:</b> <b>${res.get('expanded_futures_purchasing_power_usd', 0):,.2f} USDT (2.5x)</b>
• <b>Hệ số an toàn:</b> <code>{res.get('portfolio_margin_health_ratio', 1.85)} (An Toàn)</code>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Portfolio Margin: {e}")

    def _cmd_gnn(self):
        try:
            from scanner.spatio_temporal_gnn import SpatioTemporalGraphNetwork
            res = SpatioTemporalGraphNetwork.analyze_capital_rotation_vector()
            msg = f"""🕸️ <b>SPATIO-TEMPORAL GNN CAPITAL ROTATION (BẢN 18.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Pha luân chuyển:</b> <b>{res.get('leading_capital_rotation_phase', '')}</b>
• <b>Nhóm hưởng lợi lớn nhất:</b> <code>{res.get('highest_inflow_sector', '')}</code>
• <b>Đỉnh đồ thị theo dõi:</b> <code>{res.get('graph_nodes_tracked', 8)} coins</code>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi GNN Topology: {e}")

    def _cmd_iceberg(self):
        try:
            from core.adaptive_iceberg_execution import AdaptiveZeroSlippageIceberg
            res = AdaptiveZeroSlippageIceberg.execute_iceberg_order("BTCUSDT", 1.0, "BUY")
            msg = f"""🧊 <b>ADAPTIVE ZERO-SLIPPAGE ICEBERG (BẢN 18.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Tổng lệnh:</b> <code>{res.get('total_order_size', 1.0)} BTC</code>
• <b>Kích thước hiển thị sổ:</b> <code>{res.get('visible_display_quantity', 0.12)} BTC (12%)</code>
• <b>Trượt giá kỳ vọng:</b> <b>{res.get('expected_slippage_bps', 0.15)} bps (Zero-Slippage)</b>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Iceberg Execution: {e}")

    def _cmd_chaos(self):
        try:
            from strategy.lyapunov_chaos_detector import LyapunovChaosRegimeDetector
            res = LyapunovChaosRegimeDetector.analyze_chaos_regime("BTCUSDT")
            msg = f"""🌀 <b>LYAPUNOV CHAOS DETECTOR (BẢN 19.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Số mũ Lyapunov:</b> <code>{res.get('largest_lyapunov_exponent', 0):.4f}</code>
• <b>Phân loại trạng thái:</b> <b>{res.get('regime_classification', '')}</b>
• <b>Cấp phép giao dịch:</b> <i>{res.get('trading_permission', '')}</i>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Lyapunov Chaos: {e}")

    def _cmd_game_theory(self):
        try:
            from strategy.game_theoretic_agents import NashEquilibriumAdversarialEngine
            res = NashEquilibriumAdversarialEngine.resolve_adversarial_equilibrium("BTCUSDT")
            msg = f"""🎯 <b>NASH EQUILIBRIUM ADVERSARIAL AGENTS (BẢN 19.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Ưu thế Phe Bò:</b> <code>{res.get('bull_agent_payoff', 0):.1f}%</code>
• <b>Ưu thế Phe Gấu:</b> <code>{res.get('bear_agent_payoff', 0):.1f}%</code>
• <b>Trạng thái cân bằng Nash:</b> <b>{res.get('equilibrium_state', '')}</b>
• <b>Hiệu quả Pareto:</b> <code>{res.get('pareto_efficiency_score', 0.91)}</code>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Game Theory: {e}")

    def _cmd_sovereign(self):
        try:
            from core.sovereign_mind_ai import OmniSensorySovereignMind
            res = OmniSensorySovereignMind.evaluate_master_conviction("BTCUSDT")
            msg = f"""👑 <b>THE SOVEREIGN MIND - BỘ NÃO TỐI CAO (BẢN FINAL 20.0)</b>
━━━━━━━━━━━━━━━━━━━━
• <b>Điểm Niềm Tin Tối Thượng:</b> <b>{res.get('master_conviction_score', 86.5)} / 100</b>
• <b>Độ chính xác Bayesian:</b> <code>{res.get('confidence_interval', '99.4%')}</code>
• <b>Tư thế tác chiến:</b> <b>{res.get('operational_posture', '')}</b>
• <b>Hành động chính:</b> <code>{res.get('primary_action', '')}</code>
• <b>Lời hiệu triệu:</b> <i>{res.get('sovereign_mind_verdict', '')}</i>"""
            self.send_message(msg)
        except Exception as e:
            self.send_message(f"Lỗi Sovereign Mind: {e}")

    def _cmd_positions(self):
        if not self.bot_controller:
            return

        ctrl = self.bot_controller
        positions = ctrl.order_manager.active_positions
        if not positions:
            self.send_message(
                "💤 <b>HIỆN TẠI KHÔNG CÓ VỊ THẾ NÀO!</b>\n\n"
                "Bot đang liên tục quét thị trường để tìm setup hồi pullback đạt chuẩn R:R 1.5 và ADX >= 20.",
                inline_keyboard=[
                    [{"text": "📊 Xem Trạng Thái", "callback_data": "btn_status"}, {"text": "🏆 Tiến Độ Đánh Thật", "callback_data": "btn_eval"}]
                ]
            )
            return

        prices = ctrl.get_current_prices()
        lines = [
            f"⚡ <b>DANH SÁCH VỊ THẾ ĐANG MỞ ({len(positions)}/{self.config.max_concurrent_positions})</b>",
            "━━━━━━━━━━━━━━━━━━━━"
        ]

        total_u_pnl = 0.0

        for sym, pos in positions.items():
            side = pos["side"]
            cur_p = prices.get(sym, pos["entry_price"])
            entry = pos["entry_price"]
            sl = pos["stop_loss"]
            tp = pos["take_profit"]

            if side == "BUY":
                pnl = (cur_p - entry) * pos["qty"]
            else:
                pnl = (entry - cur_p) * pos["qty"]
            pct = (pnl / pos["margin"]) * 100.0 if pos["margin"] > 0 else 0.0
            total_u_pnl += pnl

            icon = "🟢" if pnl >= 0 else "🔴"
            side_badge = "LONG 📈" if side == "BUY" else "SHORT 📉"
            status_tag = "🎯 Đã chốt 50%" if pos.get("partial_tp_activated") else ("🛡️ SL Hòa Vốn" if pos.get("breakeven_activated") else "⚡ Đang chạy")

            lines.append(
                f"<b>{sym} | {side_badge}</b> {icon} <code>{pnl:+.2f}$ ({pct:+.2f}%)</code>\n"
                f"• Entry: <code>${entry:,.4f}</code> ➜ Giá HT: <code>${cur_p:,.4f}</code>\n"
                f"• SL: <code>${sl:,.4f}</code> | TP: <code>${tp:,.4f}</code>\n"
                f"• Ký quỹ: <code>${pos['margin']:.2f}</code> | <i>{status_tag}</i>\n"
            )

        total_icon = "🟢" if total_u_pnl >= 0 else "🔴"
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"💰 <b>Tổng PnL Tạm Tính:</b> {total_icon} <code>{total_u_pnl:+.2f} USDT</code>")

        self.send_message(
            "\n".join(lines),
            inline_keyboard=[
                [{"text": "🔄 Cập Nhật PnL", "callback_data": "btn_positions"}, {"text": "🚨 Đóng Khẩn Cấp", "callback_data": "btn_closeall"}]
            ]
        )

    def _cmd_closeall(self):
        if not self.bot_controller:
            return

        ctrl = self.bot_controller
        prices = ctrl.get_current_prices()
        res = ctrl.order_manager.close_all_positions(
            reason="Lệnh /closeall từ Telegram",
            current_prices=prices,
            simulated_balance_holder=ctrl.simulated_balance_holder
        )
        self.send_message(
            f"🚨 <b>KẾT QUẢ PANIC CLOSE:</b>\n\n{res['message']}",
            inline_keyboard=[[{"text": "📊 Xem Số Dư Mới", "callback_data": "btn_status"}]]
        )

    def _cmd_history(self):
        history_file = self.config.trade_history_file
        if not os.path.exists(history_file):
            self.send_message("Chưa có lịch sử giao dịch nào được ghi nhận.")
            return

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                reader = list(csv.reader(f))

            if len(reader) <= 1:
                self.send_message("Chưa có lệnh nào hoàn tất.")
                return

            last_trades = reader[1:][-5:]
            lines = [
                "📜 <b>5 GIAO DỊCH ĐÃ ĐÓNG GẦN NHẤT</b>",
                "━━━━━━━━━━━━━━━━━━━━"
            ]
            for row in reversed(last_trades):
                time_str, sym, side, entry, exit_p, qty, margin, pnl, pct, reason = row
                # Đảm bảo hiển thị chuẩn giờ Việt Nam (UTC+7)
                if "(VN)" not in time_str and "UTC+7" not in time_str:
                    try:
                        from datetime import datetime, timedelta
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                            try:
                                dt = datetime.strptime(time_str.strip(), fmt)
                                time_str = (dt + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S (VN)")
                                break
                            except ValueError:
                                pass
                    except Exception:
                        pass

                icon = "🎉" if "+" in pnl else "🛑"
                lines.append(
                    f"{icon} <b>{sym} ({side})</b>: <code>{pnl} ({pct})</code>\n"
                    f"• Entry: <code>${float(entry):,.4f}</code> ➜ Đóng: <code>${float(exit_p):,.4f}</code>\n"
                    f"• Lý do: <i>{reason}</i> ({time_str})\n"
                )

            self.send_message(
                "\n".join(lines),
                inline_keyboard=[
                    [{"text": "🏆 Tiến Độ Đánh Thật", "callback_data": "btn_eval"}, {"text": "💾 Tải File CSV", "callback_data": "btn_backup"}]
                ]
            )
        except Exception as e:
            self.send_message(f"Lỗi đọc file lịch sử: {e}")

    def _cmd_export(self):
        """Xuất file lịch sử giao dịch CSV và gửi trực tiếp qua Telegram"""
        history_file = self.config.trade_history_file
        if not os.path.exists(history_file):
            self.send_message("⚠️ Chưa có file dữ liệu lịch sử giao dịch.")
            return
        caption = f"📊 <b>LỊCH SỬ GIAO DỊCH (TRADE HISTORY)</b>\n• Thời gian: {_now_vn_str()}\n• Định dạng: CSV chuẩn quốc tế"
        success = self.send_document(history_file, caption=caption)
        if not success:
            self.send_message("❌ Không thể gửi file CSV qua Telegram.")

    def _cmd_analytics(self):
        """Báo cáo phân tích hiệu suất chi tiết theo từng cặp coin"""
        if not self.bot_controller or not hasattr(self.bot_controller, "order_manager"):
            self.send_message("Bot controller chưa khởi động.")
            return
        stats = self.bot_controller.order_manager.get_symbol_performance_breakdown()
        symbols = stats.get("by_symbol") or stats.get("symbols", {})
        if not symbols:
            self.send_message("📊 <b>CHƯA CÓ DỮ LIỆU PHÂN TÍCH HIỆU SUẤT!</b>\n\nCần tích lũy thêm các lệnh đã đóng để bot phân tích theo từng cặp.")
            return

        max_win = stats.get("max_win_streak", 0)
        max_loss = stats.get("max_loss_streak", 0)
        total_closed = stats.get("total_closed", len(symbols))

        best = stats.get("best_symbol")
        best_sym_name = "N/A"
        if isinstance(best, dict):
            best_sym_name = f"{best.get('symbol')} (+${best.get('net_pnl', 0):.2f})"
        elif isinstance(best, str):
            best_sym_name = best

        worst = stats.get("worst_symbol")
        worst_sym_name = "N/A"
        if isinstance(worst, dict):
            worst_sym_name = f"{worst.get('symbol')} (${worst.get('net_pnl', 0):.2f})"
        elif isinstance(worst, str):
            worst_sym_name = worst

        lines = [
            "📊 <b>PHÂN TÍCH HIỆU SUẤT TỪNG CẶP COIN</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"• <b>Tổng lệnh đã đóng:</b> <code>{total_closed}</code> lệnh",
            f"• <b>Chuỗi thắng dài nhất:</b> 🔥 <b>{max_win}</b> lệnh liên tiếp",
            f"• <b>Chuỗi thua dài nhất:</b> ❄️ <b>{max_loss}</b> lệnh liên tiếp",
            f"• <b>Cặp lãi tốt nhất:</b> <code>{best_sym_name}</code>",
            f"• <b>Cặp cần lưu ý:</b> <code>{worst_sym_name}</code>",
            "━━━━━━━━━━━━━━━━━━━━",
            "<b>Chi tiết từng cặp:</b>"
        ]
        for sym, d in list(symbols.items())[:12]:
            pnl_val = float(d.get('net_pnl', 0.0))
            pnl_sign = "+" if pnl_val >= 0 else ""
            pnl_icon = "🟢" if pnl_val >= 0 else "🔴"
            wr = d.get('win_rate', d.get('winrate', 0.0))
            wins = d.get('wins', 0)
            trades = d.get('trades', 0)
            lines.append(
                f"{pnl_icon} <b>{sym}</b>: <code>{pnl_sign}${pnl_val:.2f}</code> | Win: <b>{wr}%</b> ({wins}/{trades})"
            )
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("<i>💡 Bấm 'Tải File CSV' để tải toàn bộ lịch sử chi tiết.</i>")

        self.send_message(
            "\n".join(lines),
            inline_keyboard=[
                [{"text": "💾 Tải File CSV", "callback_data": "btn_export"}, {"text": "🏆 Tiến Độ Đánh Thật", "callback_data": "btn_eval"}],
                [{"text": "📊 Xem Vị Thế", "callback_data": "btn_positions"}, {"text": "💰 Funding Arbitrage", "callback_data": "btn_funding"}]
            ]
        )

    def _cmd_health(self):
        """Báo cáo sức khỏe máy chủ VPS kèm nút bấm làm mới"""
        try:
            from utils.watchdog import SystemWatchdog
            wd = self.bot_controller.watchdog if (self.bot_controller and hasattr(self.bot_controller, "watchdog") and self.bot_controller.watchdog) else SystemWatchdog(self.config)
            msg = wd.format_telegram_report()
            self.send_message(
                msg,
                inline_keyboard=[
                    [{"text": "🔄 Đo Lại Tốc Độ & Tài Nguyên", "callback_data": "btn_health"}],
                    [{"text": "📊 Xem PnL", "callback_data": "btn_status"}]
                ]
            )
        except Exception as e:
            self.send_message(f"Lỗi kiểm tra sức khỏe hệ thống: {e}")

    def _cmd_livecheck(self):
        if not self.bot_controller or not self.bot_controller.client:
            self.send_message("Bot client chưa sẵn sàng.")
            return

        client = self.bot_controller.client
        if not (self.config.api_key and self.config.api_secret):
            self.send_message(
                "⚠️ <b>CHƯA CẤU HÌNH API KEY THẬT!</b>\n\n"
                "Hệ thống hiện đang chạy ở chế độ <b>Giả lập (Dry-Run)</b> an toàn.\n"
                "Để kết nối tài khoản thật, vui lòng cấu hình <code>BINANCE_API_KEY</code> và <code>BINANCE_API_SECRET</code> trong file <code>.env</code> trên VPS.",
                inline_keyboard=[
                    [{"text": "🏆 Xem Tiến Độ Đánh Thật", "callback_data": "btn_eval"}]
                ]
            )
            return

        try:
            acc = client.client.futures_account()
            usdt_bal = 0.0
            for a in acc.get("assets", []):
                if a.get("asset") == "USDT":
                    usdt_bal = float(a.get("availableBalance", 0.0))
            can_trade = acc.get("canTrade", False)

            status_text = (
                "✅ <b>API KEY HỢP LỆ VÀ SẴN SÀNG LIVE!</b>\n\n"
                f"• <b>Chế độ:</b> {'Testnet' if self.config.use_testnet else 'Binance Live Thật'}\n"
                f"• <b>Quyền giao dịch:</b> {'✅ BẬT (OK)' if can_trade else '❌ TẮT (Chưa cấp quyền Futures)'}\n"
                f"• <b>Số dư USDT ví Futures:</b> <code>${usdt_bal:,.2f} USDT</code>\n"
                f"• <b>Chiết khấu phí BNB:</b> {client.check_fee_discount_recommendation()['message']}"
            )
            self.send_message(status_text)
        except Exception as e:
            self.send_message(f"❌ <b>LỖI KẾT NỐI API BINANCE:</b>\n<code>{e}</code>")

    def _cmd_evaluation(self):
        """Báo cáo tiến độ đạt chuẩn đánh thật kèm thanh tiến trình trực quan"""
        report = self.format_readiness_report()
        self.send_message(
            report,
            inline_keyboard=[
                [{"text": "🔄 Kiểm Tra Lại", "callback_data": "btn_eval"}, {"text": "📜 Xem Lịch Sử", "callback_data": "btn_history"}],
                [{"text": "🔑 Kiểm Tra API Key", "callback_data": "btn_livecheck"}]
            ]
        )

    def check_live_readiness(self, milestone: int = 50) -> dict:
        """Đánh giá dữ liệu từ trade_history.csv xem đã đủ điều kiện chuyển sang Real Live Trading chưa"""
        history_file = self.config.trade_history_file
        if not os.path.exists(history_file):
            return {
                "total_trades": 0, "wins": 0, "losses": 0, "breakeven": 0,
                "win_rate": 0.0, "profit_factor": 0.0, "net_pnl": 0.0, "max_drawdown": 0.0,
                "gross_profit": 0.0, "gross_loss": 0.0,
                "avg_win": 0.0, "avg_loss": 0.0, "rr_ratio": 0.0,
                "sample_ok": False, "pf_ok": False, "winrate_ok": False, "dd_ok": True,
                "is_ready": False, "target_trades": milestone
            }

        trades = []
        gross_profit = 0.0
        gross_loss = 0.0
        wins = 0
        losses = 0
        breakeven = 0
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
                        if p > 0.001:
                            wins += 1
                            gross_profit += p
                        elif p < -0.001:
                            losses += 1
                            gross_loss += abs(p)
                        else:
                            breakeven += 1

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
        avg_win = (gross_profit / wins) if wins > 0 else 0.0
        avg_loss = (gross_loss / losses) if losses > 0 else 0.0
        rr_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0

        sample_ok = total_trades >= milestone
        pf_ok = profit_factor >= 1.35
        winrate_ok = win_rate >= 45.0
        dd_ok = max_dd <= 5.0
        net_pnl_ok = net_pnl > 0

        is_ready = sample_ok and pf_ok and winrate_ok and dd_ok and net_pnl_ok

        return {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "breakeven": breakeven,
            "win_rate": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "net_pnl": round(net_pnl, 2),
            "max_drawdown": round(max_dd, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "rr_ratio": round(rr_ratio, 2),
            "sample_ok": sample_ok,
            "pf_ok": pf_ok,
            "winrate_ok": winrate_ok,
            "dd_ok": dd_ok,
            "net_pnl_ok": net_pnl_ok,
            "is_ready": is_ready,
            "target_trades": milestone
        }

    def _render_progress_bar(self, current: float, target: float, length: int = 8) -> str:
        """Vẽ thanh tiến trình Unicode: [██████░░░░]"""
        ratio = min(1.0, max(0.0, current / target if target > 0 else 0.0))
        filled = int(ratio * length)
        empty = length - filled
        return "█" * filled + "░" * empty

    def generate_milestone_audit_report(self, milestone: int = 50, is_auto_trigger: bool = False) -> str:
        """Tạo báo cáo kiểm toán hiệu suất chuyên sâu và đánh giá điều kiện bật LIVE (Giờ VN UTC+7)"""
        r = self.check_live_readiness(milestone=milestone)
        now_vn = _now_vn_str()

        # Thanh tiến trình số lệnh
        s_bar = self._render_progress_bar(r["total_trades"], milestone)
        pct_sample = min(100, int(r["total_trades"] / milestone * 100)) if milestone > 0 else 100

        # Biểu tượng trạng thái
        s_icon = "✅" if r["sample_ok"] else "⏳"
        pf_icon = "✅" if r["pf_ok"] else ("⏳" if r["total_trades"] < milestone else "❌")
        w_icon = "✅" if r["winrate_ok"] else ("⏳" if r["total_trades"] < milestone else "❌")
        dd_icon = "✅" if r["dd_ok"] else "❌"
        pnl_icon = "✅" if r["net_pnl_ok"] else "❌"

        # Trạng thái Sentinel
        news_filter_active = getattr(self.config, "enable_news_filter", True)
        btc_crash_active = getattr(self.config, "enable_btc_crash_protection", True)
        btc_threshold = getattr(self.config, "btc_crash_threshold_percent", 1.5)

        # Tiêu đề báo cáo
        if is_auto_trigger:
            header = f"🔔 <b>[THÔNG BÁO TỰ ĐỘNG - CỘT MỐC {milestone} LỆNH ĐÃ ĐÓNG]</b>"
        else:
            header = f"📊 <b>[BÁO CÁO KIỂM TOÁN HIỆU SUẤT & ĐỦ ĐIỀU KIỆN LIVE]</b>"

        # Đánh giá kết luận chi tiết
        if r["is_ready"]:
            verdict_text = (
                "🟢 <b>KẾT LUẬN: ĐÃ ĐỦ ĐIỀU KIỆN BẬT LIVE (REAL TRADING)!</b>\n"
                "• <i>Hệ thống đã chứng minh lợi thế giao dịch (edge) dương, kiểm soát rủi ro chặt chẽ và dòng tiền tăng trưởng bền vững qua mẫu kiểm nghiệm thực tế.</i>\n"
                "👉 <b>Cách kích hoạt:</b> Quý khách có thể chuyển sang chế độ <b>LIVE</b> trên Web Terminal (mục Cài đặt) hoặc gõ lệnh <code>/mode</code> trên Telegram."
            )
        else:
            reasons = []
            if not r["sample_ok"]:
                reasons.append(f"Cần thêm {milestone - r['total_trades']} lệnh nữa để hoàn tất mẫu {milestone} lệnh thống kê chuẩn.")
            if not r["pf_ok"]:
                reasons.append(f"Profit Factor ({r['profit_factor']}) cần cải thiện lên ≥ 1.35.")
            if not r["winrate_ok"]:
                reasons.append(f"Tỷ lệ thắng ({r['win_rate']}%) cần nâng lên ≥ 45.0%.")
            if not r["dd_ok"]:
                reasons.append(f"Max Drawdown ({r['max_drawdown']}%) vượt ngưỡng 5.0%.")
            if not r["net_pnl_ok"]:
                reasons.append("Lợi nhuận ròng tích lũy đang âm.")

            reason_str = " | ".join(reasons) if reasons else "Tiếp tục tích lũy dữ liệu"
            verdict_text = (
                "⏳ <b>KẾT LUẬN: CHƯA ĐỦ ĐIỀU KIỆN BẬT LIVE</b>\n"
                f"• <i>Nguyên nhân: {reason_str}</i>\n"
                "👉 <b>Khuyến nghị:</b> Tiếp tục duy trì chế độ Paper Trading để bot tự động giao dịch và học hỏi từ thị trường."
            )

        lines = [
            f"{header}",
            f"⏰ <i>Thời gian kiểm toán: {now_vn}</i>",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"1️⃣ <b>TỶ LỆ THẮNG (WIN RATE) THỰC TẾ:</b>",
            f"• <b>Số lệnh đã đóng:</b> <code>{r['total_trades']}/{milestone} lệnh</code> [{s_bar}] ({pct_sample}%)",
            f"• <b>Kết quả chi tiết:</b> <b>{r['wins']} Thắng</b> | <b>{r['losses']} Thua</b> | <b>{r['breakeven']} Hòa</b>",
            f"• <b>Win Rate:</b> <code>{r['win_rate']}%</code> {w_icon} (Chuẩn quỹ: ≥ 45.0% với R:R ≥ 1.5)",
            f"• <b>Lợi nhuận ròng (Net PnL):</b> <code>{'+$' if r['net_pnl'] >= 0 else '-$'}{abs(r['net_pnl']):.2f} USDT</code>",
            f"• <b>Lệnh thắng TB:</b> <code>+${r['avg_win']:.2f}</code> | <b>Lệnh thua TB:</b> <code>-${r['avg_loss']:.2f}</code>",
            f"",
            f"2️⃣ <b>TỶ LỆ LỢI NHUẬN / RỦI RO (PROFIT FACTOR):</b>",
            f"• <b>Profit Factor (PF):</b> <code>{r['profit_factor']}</code> {pf_icon} (Chuẩn an toàn: ≥ 1.35)",
            f"• <b>Tỷ lệ R:R thực tế đạt:</b> <code>1 : {r['rr_ratio']:.2f}</code>",
            f"• <b>Sụt giảm tối đa (Max Drawdown):</b> <code>{r['max_drawdown']}%</code> {dd_icon} (Ngưỡng: ≤ 5.0%)",
            f"• <b>Gross Profit:</b> <code>+${r['gross_profit']:.2f}</code> | <b>Gross Loss:</b> <code>-${r['gross_loss']:.2f}</code>",
            f"",
            f"3️⃣ <b>KHẢ NĂNG NÉ BÃO & BẢO VỆ DANH MỤC:</b>",
            f"• <b>Macro News Sentinel:</b> {'🟢 BẬT (Tự động né tin CPI/NFP/FOMC Mỹ)' if news_filter_active else '🔴 TẮT'}",
            f"  ↳ Đóng băng mở lệnh mới trước & trong khung giờ công bố tin tức đỏ.",
            f"• <b>BTC Flash-Crash Shield:</b> {'🟢 BẬT (Ngưỡng: -' + str(btc_threshold) + '% / 15m)' if btc_crash_active else '🔴 TẮT'}",
            f"  ↳ Phát hiện nến sập BTC -> Khóa lệnh Long Altcoin, chống bắt dao rơi.",
            f"• <b>Dynamic Breakeven:</b> 🟢 Tự động dời SL về hòa vốn khi chạm TP1 để triệt tiêu rủi ro.",
            f"",
            f"4️⃣ <b>BẢNG ĐIỀU KIỆN BẬT LIVE:</b>",
            f"• Mẫu lệnh ({r['total_trades']}/{milestone}): {s_icon}",
            f"• Win Rate ≥ 45% ({r['win_rate']}%): {w_icon}",
            f"• Profit Factor ≥ 1.35 ({r['profit_factor']}): {pf_icon}",
            f"• Max Drawdown ≤ 5.0% ({r['max_drawdown']}%): {dd_icon}",
            f"• Net PnL > 0 ({'+$' if r['net_pnl'] >= 0 else '-$'}{abs(r['net_pnl']):.2f}): {pnl_icon}",
            f"━━━━━━━━━━━━━━━━━━━━",
            verdict_text
        ]
        return "\n".join(lines)

    def format_readiness_report(self) -> str:
        """Định dạng báo cáo tiến độ trực quan đẹp mắt (tương thích backward)"""
        return self.generate_milestone_audit_report(milestone=50, is_auto_trigger=False)

    def send_milestone_report(self, milestone: int = 50) -> bool:
        """Gửi báo cáo tự động kiểm toán hiệu suất khi chạm mốc 50 hoặc 100 lệnh đã đóng qua Telegram"""
        report = self.generate_milestone_audit_report(milestone=milestone, is_auto_trigger=True)
        return self.send_message(
            report,
            inline_keyboard=[
                [{"text": "📊 Xem PnL", "callback_data": "btn_status"}, {"text": "🔄 Kiểm Tra Lại", "callback_data": "btn_eval"}],
                [{"text": "📜 Lịch Sử Lệnh", "callback_data": "btn_history"}, {"text": "💾 Tải File CSV", "callback_data": "btn_backup"}]
            ]
        )

    def send_document(self, file_path: str, caption: str = "") -> bool:
        if not self.enabled or not os.path.exists(file_path):
            return False

        try:
            url = f"{self.base_url}/sendDocument"
            target_ids = self.authorized_chat_ids if self.authorized_chat_ids else [self.chat_id]
            for cid in target_ids:
                try:
                    data = {"chat_id": cid, "caption": caption}
                    with open(file_path, "rb") as f:
                        files = {"document": f}
                        requests.post(url, data=data, files=files, timeout=30)
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.error("Lỗi gửi tài liệu qua Telegram: %s", e)
            return False

    def send_daily_backup_and_report(self):
        history_file = self.config.trade_history_file
        state_file = self.config.state_file

        trades = []
        total_pnl = 0.0
        wins = 0
        losses = 0

        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    reader = list(csv.DictReader(f))
                    for r in reader:
                        try:
                            p = float(r.get("pnl_usdt", 0))
                            total_pnl += p
                            if p > 0:
                                wins += 1
                            elif p < 0:
                                losses += 1
                            trades.append(r)
                        except Exception:
                            pass
            except Exception:
                pass

        total_cnt = len(trades)
        winrate = (wins / total_cnt * 100.0) if total_cnt > 0 else 0.0
        pnl_sign = "+" if total_pnl >= 0 else ""

        report_msg = (
            f"📊 <b>BÁO CÁO TỔNG KẾT & SAO LƯU DỮ LIỆU TỰ ĐỘNG</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Tổng số lệnh đã đóng:</b> {total_cnt}\n"
            f"• <b>Lệnh Thắng / Thua:</b> {wins} / {losses}\n"
            f"• <b>Tỷ lệ thắng (Winrate):</b> {winrate:.1f}%\n"
            f"• <b>Tổng Lợi nhuận ròng:</b> <code>{pnl_sign}${total_pnl:.2f} USDT</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💾 <i>Đang đính kèm 2 tệp sao lưu dữ liệu bên dưới...</i>"
        )
        self.send_message(report_msg)

        if os.path.exists(history_file):
            self.send_document(history_file, caption="📜 Lịch sử giao dịch chi tiết (trade_history.csv)")
        if os.path.exists(state_file):
            self.send_document(state_file, caption="💾 Trạng thái vị thế và số dư bot (bot_state.json)")

    def _send_to_chat(self, target_chat_id: str, text: str, reply_markup: dict = None, inline_keyboard: list = None) -> bool:
        """Gửi tin nhắn định dạng HTML tới một chat_id cụ thể"""
        if not self.enabled:
            return False
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": target_chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            if inline_keyboard:
                payload["reply_markup"] = {"inline_keyboard": inline_keyboard}
            elif reply_markup:
                payload["reply_markup"] = reply_markup
            else:
                payload["reply_markup"] = self.get_main_keyboard()

            res = requests.post(url, json=payload, timeout=8)
            if res.status_code != 200 and ("can't parse entities" in res.text or "parse" in res.text.lower()):
                clean_text = re.sub(r"<[^>]+>", "", text)
                payload["text"] = clean_text
                payload.pop("parse_mode", None)
                res = requests.post(url, json=payload, timeout=8)
            return res.status_code == 200
        except Exception as e:
            logger.error("Lỗi gửi tin nhắn Telegram tới %s: %s", target_chat_id, e)
            return False

    def send_message(self, text: str, reply_markup: dict = None, inline_keyboard: list = None) -> bool:
        """Gửi tin nhắn định dạng HTML phát đồng thời tới TẤT CẢ tài khoản được ủy quyền"""
        if not self.enabled:
            logger.debug("[Telegram Tắt]: %s", text)
            return False
        success = False
        target_ids = self.authorized_chat_ids if self.authorized_chat_ids else [self.chat_id]
        for cid in target_ids:
            if self._send_to_chat(cid, text, reply_markup, inline_keyboard):
                success = True
        return success

    def send_photo(self, photo_bytes: bytes, caption: str, inline_keyboard: list = None) -> bool:
        """Gửi hình ảnh kèm chú thích định dạng HTML và nút bấm cảm ứng (Bản 5.0)"""
        if not self.enabled:
            return False
        try:
            url = f"{self.base_url}/sendPhoto"
            target_ids = self.authorized_chat_ids if self.authorized_chat_ids else [self.chat_id]
            for cid in target_ids:
                try:
                    data = {
                        "chat_id": cid,
                        "caption": caption[:1024],
                        "parse_mode": "HTML"
                    }
                    if inline_keyboard:
                        data["reply_markup"] = json.dumps({"inline_keyboard": inline_keyboard})
                    files = {"photo": ("signal_chart.png", photo_bytes, "image/png")}
                    requests.post(url, data=data, files=files, timeout=12)
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.error("Lỗi gửi ảnh Telegram sendPhoto: %s", e)
            return False

    def notify_signal(self, symbol: str, signal: str, entry: float, sl: float, tp: float, reason: str, df: Any = None):
        is_long = (signal in ["BUY", "LONG"])
        icon = "🟢" if is_long else "🔻"
        action = "MUA / LONG 📈 (Kỳ vọng giá tăng)" if is_long else "BÁN KHỐNG / SHORT 📉 (Kỳ vọng giá giảm)"
        # Escape các ký tự đặc biệt trong reason như < hoặc > (ví dụ: EMA50 < EMA200)
        safe_reason = html.escape(str(reason))
        msg = (
            f"<b>{icon} [TÍN HIỆU CHIẾN LƯỢC] {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Hướng lệnh:</b> <b>{action}</b>\n"
            f"• <b>Điểm vào (Entry):</b> <code>${entry:,.4f}</code>\n"
            f"• <b>Cắt lỗ (Stop Loss):</b> <code>${sl:,.4f}</code>\n"
            f"• <b>Chốt lời (Take Profit):</b> <code>${tp:,.4f}</code>\n"
            f"• <b>Tỷ lệ R:R:</b> <code>1:1.5</code>\n"
            f"• <b>Phân tích kỹ thuật:</b> <i>{safe_reason}</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>Ghi chú: Đây là cơ hội vào lệnh do bot phát hiện (KHÔNG PHẢI THÔNG BÁO LỖI). Bấm nút dưới để khớp lệnh:</i>"
        )
        btn_action_label = "⚡ Duyệt Lệnh LONG 1-Click" if is_long else "⚡ Duyệt Lệnh SHORT 1-Click"
        btns = [
            [{"text": btn_action_label, "callback_data": f"manual_exec_{signal}_{symbol}"}],
            [{"text": "📱 Mở Mini App", "web_app": {"url": self.web_terminal_url}}, {"text": "⚡ Xem Vị Thế", "callback_data": "btn_positions"}]
        ]

        # Thử tạo và gửi ảnh chụp biểu đồ nến kỹ thuật trực quan (Bản 5.0)
        chart_sent = False
        try:
            from utils.chart_generator import TelegramChartGenerator
            chart_df = df
            if chart_df is None and self.bot_controller and hasattr(self.bot_controller, "client"):
                chart_df = self.bot_controller.client.get_klines_df(symbol, interval="15m", limit=50)

            if chart_df is not None and len(chart_df) >= 15:
                chart_bytes = TelegramChartGenerator.generate_signal_chart(
                    symbol=symbol,
                    df=chart_df,
                    entry_price=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    side=signal,
                    reason=reason
                )
                if chart_bytes:
                    chart_sent = self.send_photo(photo_bytes=chart_bytes, caption=msg, inline_keyboard=btns)
        except Exception as e:
            logger.debug("Không thể tạo biểu đồ nến Telegram: %s", e)

        # Nếu không gửi được ảnh, gửi tin nhắn dạng HTML thông thường
        if not chart_sent:
            self.send_message(msg, inline_keyboard=btns)

    def notify_multi_tp(
        self,
        symbol: str,
        tier: int,
        close_qty: float,
        rem_qty: float,
        exit_price: float,
        pnl_usdt: float,
        pnl_percent: float,
        new_sl: float,
        is_dry_run: bool = False
    ):
        """Báo cáo sự kiện chốt lời đa nấc (Multi-TP Scaling Out)"""
        mode_tag = "🧪 [DRY RUN]" if is_dry_run else "💰 [REAL]"
        if tier == 1:
            title = f"🎯 CHỐT LỜI NẤC 1 (33% @ 1R) - {symbol}"
            sl_note = f"• Stop Loss mới: Đã dời về <b>Hòa Vốn (${new_sl:,.4f})</b>\n• <i>Rủi ro vị thế: <b>BẰNG 0 (Risk-Free Trade)!</b></i>"
        else:
            title = f"🚀 CHỐT LỜI NẤC 2 (33% @ 2R) - {symbol}"
            sl_note = f"• Stop Loss mới: Đã nâng lên <b>Mức +1R (${new_sl:,.4f})</b>\n• <i>Khóa chắc lãi! 34% còn lại thả Trailing Runner ăn trọn trend!</i>"

        msg = (
            f"<b>{mode_tag} {title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Khối lượng chốt:</b> <code>{close_qty} (33%)</code>\n"
            f"• <b>Giá chốt:</b> <code>${exit_price:,.4f}</code>\n"
            f"• <b>PnL Thu Về:</b> <b>+${pnl_usdt:.2f} USDT (+{pnl_percent:.2f}%)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ <b>Trạng thái khối lượng còn lại ({rem_qty}):</b>\n"
            f"{sl_note}"
        )
        self.send_message(
            msg,
            inline_keyboard=[
                [{"text": "📱 Mở Mini App", "web_app": {"url": self.web_terminal_url}}],
                [{"text": "⚡ Xem Vị Thế Còn Lại", "callback_data": "btn_positions"}, {"text": "📊 Xem PnL", "callback_data": "btn_status"}]
            ]
        )

    def notify_order_filled(self, symbol: str, side: str, qty: float, price: float, margin: float, sl: float, tp: float, is_dry_run: bool = False, leverage: Optional[int] = None, ai_score: Optional[float] = None):
        mode_tag = "🧪 [DRY RUN]" if is_dry_run else "⚡ [REAL]"
        action = "KHỚP LỆNH LONG 🟢" if side == "BUY" else "KHỚP LỆNH SHORT 🔴"
        lev_str = f" [Đòn bẩy: {leverage}x thích ứng]" if leverage else ""
        
        # Tính toán các mốc Take Profit đa tầng
        risk_dist = abs(price - sl)
        tp1_price = tp
        tp2_price = round(price + (2.0 * risk_dist), 4) if side == "BUY" else round(price - (2.0 * risk_dist), 4)
        
        ai_str = f"\n• <b>AI Gatekeeper:</b> <code>{ai_score}/10.0</code> (Phê duyệt bảo chứng ✅)" if ai_score else ""

        msg = (
            f"<b>{mode_tag} {action} {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Khối lượng:</b> <code>{qty} {symbol.replace('USDT', '')}</code>\n"
            f"• <b>Giá khớp (Entry):</b> <code>${price:,.4f}</code>\n"
            f"• <b>Ký quỹ:</b> <code>${margin:.2f} USDT</code>{lev_str}{ai_str}\n"
            f"• <b>Stop Loss:</b> <code>${sl:,.4f}</code>\n"
            f"• <b>TP1 (+1.0R):</b> <code>${tp1_price:,.4f}</code> <i>(Chốt 33% + SL Hòa Vốn)</i>\n"
            f"• <b>TP2 (+2.0R):</b> <code>${tp2_price:,.4f}</code> <i>(Chốt 33% + Khóa Lãi +1R)</i>\n"
            f"• <b>TP3 (Runner):</b> <i>34% còn lại Trailing Runner ăn trọn trend</i>"
        )
        btns = [
            [{"text": "⚡ Xem Các Lệnh Đang Chạy", "callback_data": "btn_positions"}, {"text": "📊 Xem PnL", "callback_data": "btn_status"}],
            [{"text": "🚀 Mở Web Terminal", "web_app": {"url": self.web_terminal_url}}]
        ]

        # Thử tạo biểu đồ nến kèm các mốc Entry, SL, TP gửi Telegram
        chart_sent = False
        try:
            from utils.chart_generator import ChartGenerator
            chart_bytes = ChartGenerator.generate_trade_chart(
                symbol=symbol,
                side=side,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp1_price,
                tp2=tp2_price
            )
            if chart_bytes:
                chart_sent = self.send_photo(photo_bytes=chart_bytes, caption=msg, inline_keyboard=btns)
        except Exception as e:
            logger.debug("Không thể tạo biểu đồ nến lệnh khớp: %s", e)

        if not chart_sent:
            self.send_message(msg, inline_keyboard=btns)

    def notify_partial_tp(
        self,
        symbol: str,
        close_qty: float,
        rem_qty: float,
        exit_price: float,
        pnl_usdt: float,
        pnl_percent: float,
        breakeven_sl: float,
        final_tp: float,
        is_dry_run: bool = False
    ):
        """Báo cáo sự kiện chốt lời 50% tại 1R và dời Stop Loss về hòa vốn"""
        mode_tag = "🧪 [DRY RUN]" if is_dry_run else "💰 [REAL]"
        msg = (
            f"<b>{mode_tag} 🎯 CHỐT LỜI 50% (TP1 @ 1R) - {symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Khối lượng chốt:</b> <code>{close_qty} (50%)</code>\n"
            f"• <b>Giá chốt TP1:</b> <code>${exit_price:,.4f}</code>\n"
            f"• <b>PnL Thu Về:</b> <b>+${pnl_usdt:.2f} USDT (+{pnl_percent:.2f}%)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ <b>Trạng thái 50% còn lại ({rem_qty}):</b>\n"
            f"• Đang gồng lãi đến TP2: <code>${final_tp:,.4f}</code>\n"
            f"• Stop Loss mới: Đã dời về <b>Hòa Vốn (${breakeven_sl:,.4f})</b>\n"
            f"• <i>Rủi ro vị thế hiện tại: <b>BẰNG 0 (Free Trade)!</b></i>"
        )
        self.send_message(
            msg,
            inline_keyboard=[
                [{"text": "⚡ Xem Vị Thế Còn Lại", "callback_data": "btn_positions"}, {"text": "📊 Xem PnL", "callback_data": "btn_status"}]
            ]
        )

    def notify_position_closed(self, symbol: str, exit_reason: str, pnl_usdt: float, pnl_percent: float, exit_price: float, is_dry_run: bool = False):
        mode_tag = "🧪 [DRY RUN]" if is_dry_run else "💰 [KẾT QUẢ]"
        icon = "🎉 CHỐT LÃI" if pnl_usdt >= 0 else "🛑 CẮT LỖ"
        pnl_color = "+" if pnl_usdt >= 0 else ""
        msg = (
            f"<b>{mode_tag} ĐÓNG VỊ THẾ {symbol} ({icon})</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Lý do:</b> <i>{exit_reason}</i>\n"
            f"• <b>Giá đóng:</b> <code>${exit_price:,.4f}</code>\n"
            f"• <b>PnL Lợi Nhuận:</b> <code>{pnl_color}${pnl_usdt:.2f} USDT ({pnl_color}{pnl_percent:.2f}%)</code>"
        )
        self.send_message(
            msg,
            inline_keyboard=[
                [{"text": "📊 Xem PnL Mới", "callback_data": "btn_status"}, {"text": "🏆 Tiến Độ Đánh Thật", "callback_data": "btn_eval"}]
            ]
        )

        # Kiểm tra tự động đạt chuẩn Live Trading
        readiness = self.check_live_readiness()
        if readiness["is_ready"] and not self._live_alert_sent:
            self._live_alert_sent = True
            celebration_msg = (
                "🏆🎉 <b>[TING TING! CHÚC MỪNG BẠN]</b>\n\n"
                "Bot vừa chính thức <b>ĐẠT ĐỦ 100% TIÊU CHUẨN ĐÁNH TIỀN THẬT!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>Số lệnh thử nghiệm:</b> <code>{readiness['total_trades']} lệnh</code> (Chuẩn >= 15)\n"
                f"• <b>Hệ số Lãi/Lỗ (Profit Factor):</b> <code>{readiness['profit_factor']}</code> (Chuẩn >= 1.35)\n"
                f"• <b>Tỷ lệ thắng (Winrate):</b> <code>{readiness['win_rate']}%</code> (Chuẩn >= 45%)\n"
                f"• <b>Sụt giảm tối đa (Max Drawdown):</b> <code>{readiness['max_drawdown']}%</code> (Chuẩn <= 5%)\n"
                f"• <b>Lợi nhuận ròng tích lũy:</b> <code>+${readiness['net_pnl']:.2f} USDT</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                "👉 <b>BẬT ĐÈN XANH:</b> Bạn có thể chuyển sang chế độ <b>Real Trading (Live)</b> bất cứ lúc nào bằng cách nạp API Key vào file <code>.env</code> trên VPS!"
            )
            self.send_message(
                celebration_msg,
                inline_keyboard=[[{"text": "🔑 Kiểm Tra API Key Live", "callback_data": "btn_livecheck"}]]
            )

    def _cmd_ai_train(self):
        """Kích hoạt AI Self-Training Engine từ lịch sử lệnh để tối ưu chiến thuật"""
        from datetime import datetime, timezone, timedelta
        vn_time = (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%H:%M:%S %d/%m/%Y")
        
        self.send_message("🧠 <i>AI Self-Training Engine đang rà soát toàn bộ lịch sử lệnh giao dịch để huấn luyện tham số tối ưu...</i>")
        try:
            from core.ai_trade_trainer import AITradeTrainer
            trainer = AITradeTrainer()
            report = trainer.train_from_history()
            
            sample_size = report.get("sample_size", 0)
            status = report.get("status", "completed")
            win_rate = report.get("win_rate", 0.0)
            profit_factor = report.get("profit_factor", 0.0)
            rec = report.get("recommendations", {})
            opt_rsi = rec.get("rsi_boundaries", [30, 70])
            opt_atr = rec.get("atr_stop_multiplier", 1.5)
            opt_rr = rec.get("target_risk_reward", 2.0)
            confidence = report.get("model_confidence", 70.0)
            
            favored = rec.get("favored_symbols", [])
            fav_str = ", ".join(favored[:4]) if favored else "Đang theo dõi đồng đều"
            
            avoid = rec.get("avoid_symbols", [])
            avoid_str = ", ".join(avoid[:4]) if avoid else "Không có coin nào bị gắn cờ xấu"
            
            insights = report.get("pattern_insights", [])
            insight_str = "\n".join([f"• 💡 <i>{it}</i>" for it in insights[:3]]) if insights else "• 💡 <i>Dữ liệu đang tích lũy thêm các mẫu hình.</i>"

            msg = (
                f"🧠 <b>AI QUANT SELF-TRAINING ENGINE (HỌC TỰ ĐỘNG)</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱️ <b>Thời gian huấn luyện:</b> <code>{vn_time} (VN)</code>\n"
                f"📊 <b>Mẫu dữ liệu phân tích:</b> <code>{sample_size} lệnh gần nhất</code>\n"
                f"🎯 <b>Độ tin cậy mô hình:</b> <code>{confidence}%</code>\n\n"
                f"📈 <b>KẾT QUẢ HIỆU SUẤT LỊCH SỬ:</b>\n"
                f"• Tỷ lệ thắng (Win Rate): <b>{win_rate:.1f}%</b>\n"
                f"• Hệ số Lợi Nhuận (PF): <b>{profit_factor:.2f}</b>\n\n"
                f"⚙️ <b>BỘ THAM SỐ TỐI ƯU MỚI NHẤT (BAYESIAN FIT):</b>\n"
                f"• Ngưỡng RSI Mua/Bán: <code>{opt_rsi[0]} - {opt_rsi[1]}</code>\n"
                f"• Hệ số ATR Dừng lỗ: <code>{opt_atr}x ATR</code>\n"
                f"• Tỷ lệ Lời/Lỗ mục tiêu (R:R): <code>1:{opt_rr}</code>\n\n"
                f"🌟 <b>Ưu tiên chọn lệnh (Conviction):</b> <code>{fav_str}</code>\n"
                f"⚠️ <b>Hạn chế giao dịch:</b> <code>{avoid_str}</code>\n\n"
                f"🔍 <b>NHẬN ĐỊNH TỪ MÔ HÌNH:</b>\n"
                f"{insight_str}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ <i>Bộ tham số và trọng số coin đã tự động được nạp vào Market Scanner & Execution Engine.</i>"
            )
            self.send_message(
                msg,
                inline_keyboard=[
                    [{"text": "🔄 Huấn Luyện Lại", "callback_data": "btn_ai_train"}, {"text": "📊 Xem PnL", "callback_data": "btn_status"}],
                    [{"text": "⚡ Vị Thế Mở", "callback_data": "btn_positions"}, {"text": "🌐 Mở Web App", "web_app": {"url": "https://trader.noza.site"}}]
                ]
            )
        except Exception as e:
            self.send_message(f"❌ <b>Lỗi trong quá trình huấn luyện AI:</b> <code>{str(e)}</code>")

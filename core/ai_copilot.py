import os
import json
import logging
import requests
from typing import Dict, Any, Optional
from config.settings import BotConfig
from utils.sentiment import CryptoSentiment

logger = logging.getLogger("AICopilot")


class AICopilot:
    """
    Module Trợ lý AI Thông Minh (Cyber AI Copilot):
    - Tích hợp mô hình Google Gemini 2.5 Flash / DeepSeek V3.
    - Cung cấp bình luận trực quan theo thời gian thực (Speech & Mood) cho Mascot Web Dashboard.
    - Trả lời tư vấn chiến lược, phân tích danh mục lệnh trực tiếp qua Web & Telegram.
    - Kiểm định tín hiệu giao dịch (Trade Auditor) trước khi vào lệnh.
    """

    def __init__(self, config: BotConfig):
        self.config = config

    @property
    def is_deepseek_available(self) -> bool:
        k = getattr(self.config, "deepseek_api_key", "")
        return bool(k and len(k.strip()) > 5)

    @property
    def is_gemini_available(self) -> bool:
        k = getattr(self.config, "gemini_api_key", "") or getattr(self.config, "ai_api_key", "")
        return bool(k and len(k.strip()) > 5)

    @property
    def is_connected(self) -> bool:
        return self.is_deepseek_available or self.is_gemini_available

    def get_speech_commentary(self, bot_context: Any) -> Dict[str, Any]:
        """Tạo câu thoại và biểu cảm sống động cho Mascot dựa trên dữ liệu thực tế"""
        if not bot_context:
            return {
                "speech": "Chào Sếp! Em là Cyber-Nova 2.0. Hệ thống đang sẵn sàng kết nối!",
                "mood": "scanning",
                "mood_title": "KHỞI ĐỘNG ⚡",
                "glow_color": "#00F0FF"
            }

        ctrl = bot_context
        is_paused = getattr(ctrl, "is_paused", False)
        active_pos = getattr(ctrl.order_manager, "active_positions", {})
        pos_count = len(active_pos)
        u_pnl = ctrl.get_total_unrealized_pnl()
        mode = getattr(self.config, "trading_mode", "MARKET_ALL")
        mode_label = "BTC & ETH (15m)" if mode == "BLUECHIP_ONLY" else "Toàn Bộ Altcoin (Top 50)"

        # 1. Trạng thái tạm dừng
        if is_paused:
            return {
                "speech": "Sếp đang tạm dừng mở lệnh mới. Em đang tiếp tục canh gác các vị thế đang chạy để bảo vệ vốn tuyệt đối!",
                "mood": "alert",
                "mood_title": "TẠM DỪNG ⏸️",
                "glow_color": "#F0B90B"
            }

        # 2. Lãi đậm (> +10 USDT)
        if u_pnl >= 10.0:
            top_sym = list(active_pos.keys())[0] if active_pos else "danh mục"
            return {
                "speech": f"Đỉnh nóc kịch trần Sếp ơi! Tổng lãi đang là +${u_pnl:.2f} USDT 🚀. Cặp {top_sym} đang chạy cực mượt, Dynamic Trailing Stop đang bám sát để khóa chặt lãi!",
                "mood": "happy",
                "mood_title": "SIÊU PHẤN KHỞI 🤩",
                "glow_color": "#0ECB81"
            }

        # 3. Lãi vừa (> 0)
        if u_pnl > 0:
            return {
                "speech": f"Lợi nhuận tạm tính đang xanh tươi (+${u_pnl:.2f} USDT) với {pos_count} vị thế. Bộ lọc xu hướng EMA200 và ADX đang phát huy hiệu quả tối đa!",
                "mood": "happy",
                "mood_title": "GỒNG LÃI TÍCH CỰC 🟢",
                "glow_color": "#0ECB81"
            }

        # 4. Không có vị thế nào mở
        if pos_count == 0:
            fng = CryptoSentiment.get_fear_and_greed()
            fng_txt = f"Tâm lý F&G: {fng.get('classification_vi', 'Trung lập')} ({fng.get('value', 50)}/100)."
            return {
                "speech": f"Em đang bật radar quét 24/7 [{mode_label}]. {fng_txt} {fng.get('advice', '')}",
                "mood": "scanning",
                "mood_title": f"F&G {fng.get('value', 50)}: {fng.get('classification_vi', 'Radar')} 📡",
                "glow_color": fng.get("color", "#00F0FF")
            }

        # 5. PnL âm nhẹ hoặc thị trường rung lắc
        return {
            "speech": f"Thị trường đang có nhịp rung lắc (PnL: -${abs(u_pnl):.2f} USDT). Đừng lo Sếp, Stop Loss chuẩn 1R đã được chốt chặn, kỷ luật quản lý vốn là chìa khóa chiến thắng!",
            "mood": "alert",
            "mood_title": "CANH PHÒNG CẨN MẬT 🛡️",
            "glow_color": "#F6465D"
        }

    def chat(self, user_query: str, bot_context: Any) -> str:
        """Xử lý câu hỏi của người dùng kèm ngữ cảnh thị trường thực tế"""
        # Thu thập ngữ cảnh hiện tại của bot
        bal = bot_context.get_current_balance() if bot_context else 1000.0
        u_pnl = bot_context.get_total_unrealized_pnl() if bot_context else 0.0
        positions = getattr(bot_context.order_manager, "active_positions", {}) if bot_context else {}
        mode = getattr(self.config, "trading_mode", "MARKET_ALL")

        pos_summary = []
        for s, p in positions.items():
            pos_summary.append(f"- {s} ({p.get('side')}): Entry ${p.get('entry_price')}, SL ${p.get('stop_loss')}, TP ${p.get('take_profit')}, Margin ${p.get('margin', 0):.2f}")

        pos_str = "\n".join(pos_summary) if pos_summary else "Hiện không có vị thế nào đang mở."

        fng = CryptoSentiment.get_fear_and_greed()
        context_prompt = (
            f"Bạn là CYBER-NOVA, Trợ lý AI Quant Trading cao cấp của hệ thống Binance Futures 3.0 PRO.\n"
            f"Thông tin thị trường & tài khoản thực tế:\n"
            f"- Chỉ số Crypto Fear & Greed: {fng.get('value', 50)}/100 ({fng.get('classification_vi', 'Trung lập')}) - Lời khuyên: {fng.get('advice', '')}\n"
            f"- Số dư: ${bal:,.2f} USDT\n"
            f"- PnL Tạm Tính (Unrealized PnL): {('+' if u_pnl >= 0 else '')}${u_pnl:,.2f} USDT\n"
            f"- Chế độ quét hiện tại: {mode}\n"
            f"- Đòn bẩy: {self.config.leverage}x (Isolated)\n"
            f"- Rủi ro/lệnh: {self.config.risk_per_trade_percent}%\n"
            f"- Danh sách vị thế đang mở:\n{pos_str}\n\n"
            f"Hãy trả lời người dùng một cách chuyên nghiệp, thông minh, ngắn gọn, súc tích, mang phong cách Quant Trader kiên định và thân thiện."
        )

        provider = getattr(self.config, "ai_provider", "dual").lower()
        
        # Dual mode hoặc DeepSeek ưu tiên trước
        if provider in ["dual", "deepseek"]:
            if self.is_deepseek_available:
                ds_res = self._call_deepseek(user_query, context_prompt)
                if ds_res:
                    return ds_res
                logger.info("DeepSeek không phản hồi hoặc rate limit, tự động chuyển sang Google Gemini...")
            if self.is_gemini_available:
                gm_res = self._call_gemini(user_query, context_prompt)
                if gm_res:
                    return gm_res
        elif provider == "gemini":
            if self.is_gemini_available:
                gm_res = self._call_gemini(user_query, context_prompt)
                if gm_res:
                    return gm_res
            if self.is_deepseek_available:
                ds_res = self._call_deepseek(user_query, context_prompt)
                if ds_res:
                    return ds_res

        # Nếu cả 2 đều chưa kết nối hoặc lỗi mạng, sử dụng bộ não suy luận lượng tử nội bộ
        return self._local_heuristic_chat(user_query, bal, u_pnl, positions, mode)

    def _call_gemini(self, user_query: str, system_context: str) -> Optional[str]:
        """Gọi Google Gemini API qua REST Endpoint chuẩn với cơ chế tự động fallback model"""
        api_key = (getattr(self.config, "gemini_api_key", "") or getattr(self.config, "ai_api_key", "")).strip()
        if not api_key:
            return None

        preferred = getattr(self.config, "gemini_model", "gemini-2.5-flash") or "gemini-2.5-flash"
        models_to_try = [preferred, "gemini-2.0-flash", "gemini-1.5-flash"]
        seen = set()
        models = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{system_context}\n\nNgười dùng hỏi: {user_query}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.5,
                    "maxOutputTokens": 2048
                }
            }
            try:
                res = requests.post(url, json=payload, timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        full_text = "".join(p.get("text", "") for p in parts).strip()
                        if full_text:
                            return full_text
                logger.warning("Gemini model %s phản hồi HTTP %s: %s", model, res.status_code, res.text[:120])
            except Exception as e:
                logger.warning("Gemini model %s lỗi/timeout: %s", model, e)
                continue

        return None

    def _call_deepseek(self, user_query: str, system_context: str) -> Optional[str]:
        """Gọi DeepSeek API qua TokenHarbor hoặc DeepSeek Endpoint chuẩn"""
        api_key = getattr(self.config, "deepseek_api_key", "").strip()
        if not api_key:
            return None

        base_url = getattr(self.config, "deepseek_base_url", "https://tokenharbor.ai/v1/chat/completions").strip()
        url = base_url if base_url.endswith("/chat/completions") else f"{base_url.rstrip('/')}/chat/completions"
        model_name = getattr(self.config, "deepseek_model", "deepseek-v4.1-flash:free").strip() or "deepseek-v4.1-flash:free"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_query}
            ],
            "temperature": 0.5,
            "max_tokens": 800
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=7)
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "").strip()
                    if text:
                        return text
            logger.warning("DeepSeek API phản hồi HTTP %s: %s", res.status_code, res.text[:120])
            return None
        except Exception as e:
            logger.warning("DeepSeek API gặp lỗi/timeout: %s", e)
            return None

    def explain_trade_exit(self, trade: dict) -> str:
        """Sử dụng DeepSeek/Gemini để giải thích ngắn gọn nguyên nhân đóng lệnh bằng tiếng Việt"""
        try:
            sym = trade.get("symbol", "")
            side = trade.get("side", "")
            pnl = float(trade.get("pnl_usdt", 0))
            reason = trade.get("exit_reason", "")
            prompt = (
                f"Lệnh {side} cho cặp {sym} vừa đóng với PnL {pnl:+.2f} USDT do lý do: {reason}. "
                f"Hãy phân tích và đưa ra nhận xét ngắn gọn 1-2 câu bằng tiếng Việt chuẩn Quant Trader chuyên nghiệp."
            )
            ctx = "Bạn là Trợ lý AI Quant Phân tích Lệnh Giao dịch."
            provider = getattr(self.config, "ai_provider", "dual").lower()
            if provider in ["dual", "deepseek"]:
                if self.is_deepseek_available:
                    res = self._call_deepseek(prompt, ctx)
                    if res:
                        return res
                if self.is_gemini_available:
                    res = self._call_gemini(prompt, ctx)
                    if res:
                        return res
            else:
                if self.is_gemini_available:
                    res = self._call_gemini(prompt, ctx)
                    if res:
                        return res
                if self.is_deepseek_available:
                    res = self._call_deepseek(prompt, ctx)
                    if res:
                        return res
        except Exception:
            pass
        return ""

    def _local_heuristic_chat(self, query: str, bal: float, u_pnl: float, positions: dict, mode: str) -> str:
        """Bộ suy luận lượng tử tích hợp sẵn khi chưa điền API Key"""
        q = query.lower()

        # 1. Hỏi về vị thế / lệnh đang chạy
        if any(w in q for w in ["vị thế", "lệnh", "chạy", "pnl", "lời", "lỗ"]):
            pos_count = len(positions)
            if pos_count == 0:
                return (
                    "📊 <b>BÁO CÁO VỊ THẾ:</b>\n"
                    "• Hiện tại không có vị thế nào đang mở.\n"
                    "• Radar đang tiếp tục quét thị trường để tìm setup hồi có xác suất thắng cao nhất!"
                )
            lines = [f"📊 <b>PHÂN TÍCH {pos_count} VỊ THẾ ĐANG MỞ:</b>"]
            for s, p in positions.items():
                cur_p = p.get('entry_price', 0)
                lines.append(f"• <b>{s} ({p.get('side')})</b>: Giá vào ${cur_p:.4f} | Ký quỹ: ${p.get('margin', 0):.2f} USDT")
            lines.append(f"\n💰 <b>Tổng PnL Tạm Tính:</b> {'+' if u_pnl >= 0 else ''}${u_pnl:.2f} USDT")
            lines.append("⚡ <b>Chiến lược:</b> Dynamic Trailing Stop đang được kích hoạt để sẵn sàng khóa lãi tự động khi giá tăng tốc.")
            return "\n".join(lines)

        # 2. Hỏi về chế độ giao dịch
        if any(w in q for w in ["chế độ", "mode", "btc", "eth", "altcoin", "meme"]):
            return (
                "🎯 <b>TƯ VẤN CHẾ ĐỘ GIAO DỊCH:</b>\n"
                f"• <b>Chế độ hiện tại:</b> <code>{mode}</code>\n\n"
                "💡 <b>Lời khuyên chuyên gia:</b>\n"
                "- <b>Chỉ BTC & ETH (BLUECHIP_ONLY)</b>: Khuyên dùng khi thị trường có tin bão lớn từ Fed/SEC, hoặc bạn muốn sự ổn định bền vững, ngủ ngon giấc.\n"
                "- <b>Toàn Bộ Thị Trường (MARKET_ALL)</b>: Khuyên dùng khi thị trường có sóng rõ ràng, các Altcoin Top 50 có biên độ 15-30% mang lại lợi nhuận vượt trội."
            )

        # 3. Hỏi về cách setup AI
        if any(w in q for w in ["setup", "cài đặt", "api key", "gemini", "deepseek", "key"]):
            return (
                "🤖 <b>HƯỚNG DẪN SETUP AI THÔNG MINH CHO BOT:</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "1️⃣ <b>Lấy API Key Miễn Phí</b>: Truy cập <a href='https://aistudio.google.com/' target='_blank' style='color:#F0B90B;text-decoration:underline;'>Google AI Studio</a>, bấm <b>Create API Key</b> (hoàn toàn miễn phí).\n"
                "2️⃣ <b>Dán Key vào Bot</b>: Bấm nút <b>⚙️ Cài Đặt</b> ở góc trên Web Dashboard hoặc gửi key cho bot, hệ thống sẽ tự động kích hoạt bộ não <b>Gemini 2.5 Flash</b> siêu tốc!\n"
                "3️⃣ <b>Tính năng sau khi kích hoạt</b>: AI sẽ tự động phân tích thị trường vĩ mô, audit duyệt lệnh trước khi vào và giải đáp mọi chiến lược cho bạn!"
            )

        # Mặc định
        return (
            f"🤖 <b>CYBER-NOVA QUANT AI CHÀO BẠN!</b>\n\n"
            f"Hệ thống đang vận hành ổn định với số dư <b>${bal:,.2f} USDT</b> và PnL tạm tính <b>{'+' if u_pnl >= 0 else ''}${u_pnl:,.2f} USDT</b>.\n"
            f"Bạn có thể hỏi em về: <i>'Phân tích các lệnh đang chạy'</i>, <i>'Tư vấn chế độ quét'</i> hoặc <i>'Hướng dẫn setup key AI'</i>.\n\n"
            f"<i>💡 Mẹo: Nhập Google Gemini API Key trong menu Cài Đặt để mở khóa toàn bộ trí tuệ nhân tạo thế hệ mới!</i>"
        )

    def audit_trade_signal(self, signal: Dict[str, Any], bot_context: Any = None) -> Dict[str, Any]:
        """
        AI Gatekeeper: Duyệt & Chấm điểm tín hiệu trước khi mở vị thế (Bản Quant Pro).
        Phân tích:
        - Tín hiệu: symbol, side, entry_price, stop_loss, take_profit, leverage, adx, rsi
        - Thị trường: BTC Regime, Fear & Greed, Funding Rate
        Trả về:
        {"approved": bool, "score": float, "reason": str, "provider_used": str}
        """
        sym = signal.get("symbol", "UNKNOWN")
        side = signal.get("side", "BUY")
        entry = signal.get("entry_price", 0.0)
        sl = signal.get("stop_loss", 0.0)
        tp = signal.get("take_profit", 0.0)
        adx = signal.get("adx", 0.0)
        rsi = signal.get("rsi", 50.0)
        lev = signal.get("leverage", getattr(self.config, "leverage", 5))
        strategy = signal.get("strategy", "TREND_PULLBACK")

        # Thu thập bối cảnh thị trường
        fng = CryptoSentiment.get_fear_and_greed()
        btc_regime = "BULL"
        if bot_context and hasattr(bot_context, "scanner"):
            btc_regime = getattr(bot_context.scanner, "last_btc_regime", "UNKNOWN")

        prompt = (
            f"Bạn là Trưởng Ban Quản Trị Rủi Ro Định Lượng (Head of Quant Risk) của quỹ Binance Futures.\n"
            f"Hệ thống vừa phát hiện tín hiệu kỹ thuật sau và yêu cầu bạn thẩm định duyệt lệnh (Trade Pre-Audit):\n"
            f"• Cặp giao dịch: {sym}\n"
            f"• Hướng lệnh: {side} (Đòn bẩy: {lev}x Isolated)\n"
            f"• Chiến lược: {strategy}\n"
            f"• Giá vào dự kiến (Entry): ${entry}\n"
            f"• Stop Loss: ${sl} | Take Profit: ${tp}\n"
            f"• Chỉ báo kỹ thuật: ADX={adx:.1f}, RSI={rsi:.1f}\n"
            f"• Bối cảnh vĩ mô: BTC Regime={btc_regime}, Crypto Fear & Greed={fng.get('value', 50)}/100 ({fng.get('classification_vi')})\n\n"
            f"Yêu cầu:\n"
            f"1. Đánh giá xác suất thắng và rủi ro bị quét râu nến/xả hàng.\n"
            f"2. Chấm điểm từ 1.0 đến 10.0 (Ngưỡng đạt chuẩn duyệt lệnh là >= {self.config.ai_min_audit_score}).\n"
            f"3. Trả về DUY NHẤT một chuỗi JSON hợp lệ theo đúng cấu trúc sau (không kèm markdown thừa):\n"
            f'{{"score": 8.5, "approved": true, "reason": "Nhận xét ngắn gọn 1-2 câu tiếng Việt chuyên nghiệp"}}'
        )

        provider_used = "HEURISTIC"
        try:
            raw_reply = None
            if self.is_connected:
                provider = getattr(self.config, "ai_provider", "dual").lower()
                if provider in ["dual", "deepseek"]:
                    if self.is_deepseek_available:
                        raw_reply = self._call_deepseek(prompt, "Bạn là Hệ thống AI Quant Pre-Trade Auditor.")
                        if raw_reply:
                            provider_used = "DEEPSEEK"
                    if not raw_reply and self.is_gemini_available:
                        raw_reply = self._call_gemini(prompt, "Bạn là Hệ thống AI Quant Pre-Trade Auditor.")
                        if raw_reply:
                            provider_used = "GEMINI"
                elif provider == "gemini":
                    if self.is_gemini_available:
                        raw_reply = self._call_gemini(prompt, "Bạn là Hệ thống AI Quant Pre-Trade Auditor.")
                        if raw_reply:
                            provider_used = "GEMINI"
                    if not raw_reply and self.is_deepseek_available:
                        raw_reply = self._call_deepseek(prompt, "Bạn là Hệ thống AI Quant Pre-Trade Auditor.")
                        if raw_reply:
                            provider_used = "DEEPSEEK"

            if raw_reply:
                import re
                json_match = re.search(r'\{.*\}', raw_reply, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    score = float(parsed.get("score", 7.5))
                    approved = bool(score >= self.config.ai_min_audit_score and parsed.get("approved", True))
                    reason = str(parsed.get("reason", "AI đã phân tích và chấp thuận setup."))
                    return {
                        "approved": approved,
                        "score": round(score, 1),
                        "reason": reason,
                        "provider_used": provider_used
                    }
        except Exception as e:
            logger.warning("Lỗi trong AI Gatekeeper audit: %s, fallback sang kỹ thuật nội bộ", e)

        # Fallback an toàn nếu AI offline
        is_tech_ok = adx >= 20.0
        score = 8.0 if is_tech_ok else 6.5
        approved = score >= self.config.ai_min_audit_score
        reason = "Đạt tiêu chuẩn kỹ thuật ADX & EMA xu hướng (Quant Heuristic)" if approved else "Chỉ số động lượng ADX yếu (<20), rủi ro đi ngang"
        return {
            "approved": approved,
            "score": score,
            "reason": reason,
            "provider_used": "LOCAL_HEURISTIC"
        }

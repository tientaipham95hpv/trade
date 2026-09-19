import os
import csv
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from config.settings import BotConfig
from core.binance_client import BinanceFuturesClient
from notifier.telegram_bot import TelegramNotifier

logger = logging.getLogger("OrderManager")

VIETNAM_TZ = timezone(timedelta(hours=7))


class OrderManager:
    """
    Module Quản lý Vòng Đời Lệnh Nâng Cao:
    - Mở lệnh Market + Cài đặt Hard Stop Loss và Take Profit.
    - Lưu & Phục hồi trạng thái (State Persistence - bot_state.json) chống mất điện/sập nguồn.
    - Xuất nhật ký giao dịch chi tiết ra file CSV (trade_history.csv) chuẩn Excel.
    - Chốt lời từng phần (Partial Take Profit): Chốt 50% tại 1R + Kéo Stop Loss về hòa vốn (Breakeven) gồng 50% còn lại.
    - Hỗ trợ đầy đủ Paper Trading (Dry-run simulation) và Live Trading.
    """

    def __init__(self, config: BotConfig, client: BinanceFuturesClient, notifier: TelegramNotifier):
        self.config = config
        self.client = client
        self.notifier = notifier
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.last_known_balance: float = 1000.0

        # Tự động nạp trạng thái đã lưu trước đó nếu có
        saved_bal = self.load_state()
        if saved_bal is not None and saved_bal > 0:
            self.last_known_balance = saved_bal

    def save_state(self, simulated_balance: Optional[float] = None):
        """Lưu toàn bộ vị thế đang mở và số dư ra file JSON để phục hồi khi khởi động lại"""
        if simulated_balance is not None and simulated_balance > 0:
            self.last_known_balance = simulated_balance

        try:
            serializable_positions = {}
            for sym, pos in self.active_positions.items():
                p_copy = pos.copy()
                if isinstance(p_copy.get("opened_at"), datetime):
                    p_copy["opened_at"] = p_copy["opened_at"].isoformat()
                serializable_positions[sym] = p_copy

            state_data = {
                "updated_at": datetime.now(VIETNAM_TZ).isoformat(),
                "simulated_balance": self.last_known_balance,
                "active_positions": serializable_positions,
                "total_trades_count": len(self.trade_history)
            }

            with open(self.config.state_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            logger.debug("Đã lưu trạng thái hệ thống vào %s", self.config.state_file)
        except Exception as e:
            logger.error("Lỗi khi lưu state: %s", e)

    def load_state(self) -> Optional[float]:
        """Đọc và phục hồi trạng thái từ file JSON nếu file tồn tại"""
        if not os.path.exists(self.config.state_file):
            return None

        try:
            with open(self.config.state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            saved_positions = state_data.get("active_positions", {})
            for sym, pos in saved_positions.items():
                if "opened_at" in pos and isinstance(pos["opened_at"], str):
                    try:
                        pos["opened_at"] = datetime.fromisoformat(pos["opened_at"])
                    except Exception:
                        pos["opened_at"] = datetime.now(VIETNAM_TZ)
                self.active_positions[sym] = pos

            logger.info("Đã phục hồi %d vị thế từ %s", len(self.active_positions), self.config.state_file)
            return state_data.get("simulated_balance")
        except Exception as e:
            logger.warning("Không thể đọc file state cũ (%s), tạo mới: %s", self.config.state_file, e)
            return None

    def record_trade_to_csv(self, trade: Dict[str, Any]):
        """Ghi nhận giao dịch đã đóng vào file CSV để xem thống kê trên Excel (Giờ Việt Nam UTC+7)"""
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

            # Tự động kích hoạt AI Quant Self-Training ngầm để học từ lệnh vừa đóng
            try:
                import threading
                from core.ai_trade_trainer import AITradeTrainer
                def _bg_train():
                    try:
                        rep = AITradeTrainer().train_from_history()
                        logger.info(
                            "🧠 [AI AUTO-TRAIN] Đã tự động học lại từ trade vừa đóng! (Mẫu: %s lệnh, Winrate: %s%%, PF: %s, RSI: %s, ATR: %sx)",
                            rep.get("sample_size"),
                            rep.get("win_rate"),
                            rep.get("profit_factor"),
                            rep.get("recommendations", {}).get("rsi_boundaries"),
                            rep.get("recommendations", {}).get("atr_stop_multiplier")
                        )
                    except Exception as err:
                        logger.debug("Lỗi ngầm AI auto-train: %s", err)

                threading.Thread(target=_bg_train, daemon=True, name="AIAutoTrainThread").start()
            except Exception as e:
                logger.debug("Không thể khởi chạy thread AI auto-train: %s", e)

            # Tự động kiểm tra cột mốc 50, 100 lệnh đã đóng để gửi báo cáo kiểm toán Telegram
            try:
                self._check_and_notify_milestones()
            except Exception as e:
                logger.debug("Lỗi ngầm kiểm tra milestone trade: %s", e)
        except Exception as e:
            logger.error("Lỗi khi ghi trade ra CSV: %s", e)

    def _check_and_notify_milestones(self):
        """Kiểm tra xem số lượng lệnh đã đóng có chạm các cột mốc 50, 100... để tự động gửi thông báo kiểm toán Telegram"""
        try:
            if not self.notifier or not getattr(self.notifier, "enabled", False):
                return

            file_path = self.config.trade_history_file
            if not os.path.exists(file_path):
                return

            total_closed = 0
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                total_closed = sum(1 for _ in reader)

            milestones = [50, 100]
            base_dir = os.path.dirname(file_path) or "."
            state_file = os.path.join(base_dir, "milestone_notifications.json")

            sent_milestones = []
            if os.path.exists(state_file):
                try:
                    with open(state_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        sent_milestones = data.get("sent_milestones", [])
                except Exception:
                    sent_milestones = []

            for m in milestones:
                if total_closed >= m and m not in sent_milestones:
                    logger.info("🎉 Đạt mốc %d lệnh đã đóng! Gửi báo cáo kiểm toán cột mốc %d qua Telegram...", total_closed, m)
                    if hasattr(self.notifier, "send_milestone_report"):
                        ok = self.notifier.send_milestone_report(milestone=m)
                        if ok:
                            sent_milestones.append(m)
                            try:
                                with open(state_file, "w", encoding="utf-8") as f:
                                    json.dump({
                                        "sent_milestones": sent_milestones,
                                        "last_reported_count": total_closed,
                                        "updated_at": datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d %H:%M:%S (VN)")
                                    }, f, indent=2, ensure_ascii=False)
                            except Exception as fe:
                                logger.warning("Không thể lưu milestone state: %s", fe)
        except Exception as e:
            logger.error("Lỗi khi kiểm tra cột mốc milestone: %s", e)

    def get_open_position_count(self) -> int:
        """Số lượng vị thế đang mở"""
        return len(self.active_positions)

    def execute_entry(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        qty: float,
        stop_loss: float,
        take_profit: float,
        margin: float,
        risk_amount: float,
        leverage: Optional[int] = None,
        ai_score: Optional[float] = None
    ) -> bool:
        """Thực thi mở vị thế mới kèm SL và TP kết hợp Đòn bẩy thích ứng (Dynamic Leverage) & AI Gatekeeper score"""
        if symbol in self.active_positions:
            logger.warning("%s đã có vị thế mở, bỏ qua tín hiệu mới.", symbol)
            return False

        effective_leverage = leverage or getattr(self.config, "leverage", 5)

        logger.info("==> Mở vị thế %s cho %s tại $%s | SL: $%s | TP: $%s | Đòn bẩy: %dx (Thích ứng)%s",
                    side, symbol, f"{entry_price:,.4f}", f"{stop_loss:,.4f}", f"{take_profit:,.4f}", effective_leverage,
                    f" | AI Score: {ai_score}/10" if ai_score else "")

        # 1. Cấu hình Leverage & Margin Isolated trên Binance
        self.client.set_leverage_and_margin(symbol, effective_leverage, self.config.margin_type)

        # Smart Scaling: Cho phép vào 50% Market trước, bảo đảm khớp vị thế
        smart_scaling = getattr(self.config, "enable_smart_scaling", False)
        exec_qty = round(qty * 0.5, 4) if smart_scaling else qty
        exec_margin = round(margin * 0.5, 2) if smart_scaling else margin
        if smart_scaling:
            logger.info("⚡ [Smart Scaling Active] Vào trước 50%% Market (%s) cho %s", exec_qty, symbol)

        # 2. Gửi lệnh Market Entry
        market_order = self.client.place_market_order(symbol, side, exec_qty)
        if not market_order:
            logger.error("Thất bại khi gửi lệnh Market %s cho %s", side, symbol)
            return False

        # 3. Gửi lệnh Hard Stop Loss và Take Profit
        exit_side = "SELL" if side == "BUY" else "BUY"
        sl_order = self.client.place_stop_loss_order(symbol, exit_side, stop_loss)
        tp_order = self.client.place_take_profit_order(symbol, exit_side, take_profit)

        # 4. Lưu trạng thái vị thế vào bộ nhớ
        position_record = {
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "initial_sl": stop_loss,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "qty": exec_qty,
            "initial_qty": exec_qty,
            "orig_qty": exec_qty,
            "margin": exec_margin,
            "orig_margin": exec_margin,
            "risk_amount": risk_amount,
            "leverage": effective_leverage,
            "ai_score": ai_score,
            "tp1_done": False,
            "tp2_done": False,
            "opened_at": datetime.now(VIETNAM_TZ),
            "breakeven_activated": False,
            "partial_tp_activated": False,
            "sl_order": sl_order,
            "tp_order": tp_order
        }
        self.active_positions[symbol] = position_record
        self.save_state()

        # 5. Báo cáo Telegram
        self.notifier.notify_order_filled(
            symbol=symbol,
            side=side,
            qty=exec_qty,
            price=entry_price,
            margin=exec_margin,
            sl=stop_loss,
            tp=take_profit,
            is_dry_run=self.config.dry_run,
            leverage=effective_leverage,
            ai_score=ai_score
        )
        return True

    def check_and_update_positions(self, current_prices: Dict[str, float], simulated_balance_holder: Optional[Dict[str, float]] = None):
        """
        Kiểm tra và cập nhật các vị thế đang chạy:
        - Chốt lời từng phần 50% khi chạm 1R lợi nhuận.
        - Dời Stop Loss về Break-Even khi đạt 1R.
        - Khớp toàn bộ SL/TP khi chạm mục tiêu cuối.
        - Tự động lưu trạng thái (State Persistence) và xuất file CSV.
        """
        closed_symbols = []

        for symbol, pos in list(self.active_positions.items()):
            cur_price = current_prices.get(symbol)
            if not cur_price:
                continue

            side = pos["side"]
            entry = pos["entry_price"]
            sl = pos["stop_loss"]
            tp = pos["take_profit"]
            qty = pos["qty"]
            margin = pos["margin"]

            # Khoảng cách 1R rủi ro ban đầu
            initial_risk_dist = abs(entry - pos.get("initial_sl", sl))

            # 1. Cơ chế Chốt Lời Đa Nấc (Smart Multi-TP Scaling Out 33% - 33% - 34%)
            pos.setdefault("tp1_done", pos.get("partial_tp_activated", False))
            pos.setdefault("tp2_done", False)
            pos.setdefault("orig_qty", pos.get("initial_qty", qty))
            pos.setdefault("orig_margin", pos.get("margin", margin))

            if getattr(self.config, "enable_multi_stage_tp", getattr(self.config, "use_multi_tp", True)):
                # Nấc 1: Đạt +1R -> Chốt 33% và dời Stop Loss về Hòa Vốn (Breakeven)
                hit_1r = (side == "BUY" and cur_price >= entry + initial_risk_dist) or (side == "SHORT" and cur_price <= entry - initial_risk_dist)
                if hit_1r and not pos["tp1_done"]:
                    close_qty = round(pos["orig_qty"] * 0.33, 4)
                    if 0 < close_qty < pos["qty"]:
                        pnl = (cur_price - entry) * close_qty if side == "BUY" else (entry - cur_price) * close_qty
                        part_margin = pos["orig_margin"] * 0.33
                        part_pct = (pnl / part_margin * 100.0) if part_margin > 0 else 0.0
                        if simulated_balance_holder is not None:
                            simulated_balance_holder["balance"] += pnl
                        pos["qty"] = round(pos["qty"] - close_qty, 4)
                        pos["margin"] = round(pos["margin"] - part_margin, 2)
                        pos["stop_loss"] = entry  # Dời SL về Breakeven
                        pos["tp1_done"] = True
                        pos["partial_tp_activated"] = True
                        pos["breakeven_activated"] = True
                        logger.info(f"[{symbol}] 🎯 CHỐT LỜI NẤC 1 (33% @ 1R) tại ${cur_price:,.4f}! PnL: +${pnl:.2f} (+{part_pct:.2f}%). Dời SL về Hòa Vốn (${entry:,.4f})")
                        self.record_trade_to_csv({
                            "symbol": symbol,
                            "side": side,
                            "entry_price": entry,
                            "exit_price": cur_price,
                            "qty": close_qty,
                            "margin": part_margin,
                            "pnl_usdt": round(pnl, 2),
                            "pnl_percent": round(part_pct, 2),
                            "closed_at": datetime.now(VIETNAM_TZ),
                            "exit_reason": "Chốt lời Nấc 1 (33% @ 1R) 🎯 + SL Hòa Vốn"
                        })
                        if hasattr(self.notifier, "notify_multi_tp"):
                            self.notifier.notify_multi_tp(
                                symbol=symbol, tier=1, close_qty=close_qty, rem_qty=pos["qty"],
                                exit_price=cur_price, pnl_usdt=pnl, pnl_percent=part_pct,
                                new_sl=entry, is_dry_run=self.config.dry_run
                            )
                        self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)
                        continue

                # Nấc 2: Đạt +2R -> Chốt tiếp 33% và nâng Stop Loss lên mức +1R để Khóa Lãi
                hit_2r = (side == "BUY" and cur_price >= entry + (initial_risk_dist * 2.0)) or (side == "SHORT" and cur_price <= entry - (initial_risk_dist * 2.0))
                if hit_2r and pos["tp1_done"] and not pos["tp2_done"]:
                    close_qty = round(pos["orig_qty"] * 0.33, 4)
                    if 0 < close_qty < pos["qty"]:
                        pnl = (cur_price - entry) * close_qty if side == "BUY" else (entry - cur_price) * close_qty
                        part_margin = pos["orig_margin"] * 0.33
                        part_pct = (pnl / part_margin * 100.0) if part_margin > 0 else 0.0
                        new_sl = round(entry + initial_risk_dist, 4) if side == "BUY" else round(entry - initial_risk_dist, 4)
                        if simulated_balance_holder is not None:
                            simulated_balance_holder["balance"] += pnl
                        pos["qty"] = round(pos["qty"] - close_qty, 4)
                        pos["margin"] = round(pos["margin"] - part_margin, 2)
                        pos["stop_loss"] = new_sl  # Khóa lãi tại +1R
                        pos["tp2_done"] = True
                        logger.info(f"[{symbol}] 🚀 CHỐT LỜI NẤC 2 (33% @ 2R) tại ${cur_price:,.4f}! PnL: +${pnl:.2f} (+{part_pct:.2f}%). Dời SL lên +1R (${new_sl:,.4f}) khóa chắc lãi!")
                        self.record_trade_to_csv({
                            "symbol": symbol,
                            "side": side,
                            "entry_price": entry,
                            "exit_price": cur_price,
                            "qty": close_qty,
                            "margin": part_margin,
                            "pnl_usdt": round(pnl, 2),
                            "pnl_percent": round(part_pct, 2),
                            "closed_at": datetime.now(VIETNAM_TZ),
                            "exit_reason": "Chốt lời Nấc 2 (33% @ 2R) 🚀 + Khóa Lãi +1R"
                        })
                        if hasattr(self.notifier, "notify_multi_tp"):
                            self.notifier.notify_multi_tp(
                                symbol=symbol, tier=2, close_qty=close_qty, rem_qty=pos["qty"],
                                exit_price=cur_price, pnl_usdt=pnl, pnl_percent=part_pct,
                                new_sl=new_sl, is_dry_run=self.config.dry_run
                            )
                        self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)
                        continue

            # 1.5. Chốt Lời 50% theo phong cách cũ nếu không bật Multi-TP
            elif self.config.use_partial_tp and not pos.get("partial_tp_activated", False):
                hit_1r = False
                if side == "BUY" and cur_price >= entry + initial_risk_dist:
                    hit_1r = True
                elif side == "SHORT" and cur_price <= entry - initial_risk_dist:
                    hit_1r = True

                if hit_1r:
                    close_qty = round(qty * self.config.partial_tp_ratio, 4)
                    if close_qty > 0 and close_qty < qty:
                        partial_pnl = (cur_price - entry) * close_qty if side == "BUY" else (entry - cur_price) * close_qty
                        partial_margin = margin * self.config.partial_tp_ratio
                        partial_pct = (partial_pnl / partial_margin) * 100.0 if partial_margin > 0 else 0.0
                        if simulated_balance_holder is not None:
                            simulated_balance_holder["balance"] += partial_pnl
                        pos["qty"] = round(qty - close_qty, 4)
                        pos["margin"] = round(margin - partial_margin, 2)
                        pos["stop_loss"] = entry
                        pos["partial_tp_activated"] = True
                        pos["breakeven_activated"] = True
                        logger.info(f"[{symbol}] 🎯 CHỐT LỜI 50% TẠI 1R (${cur_price:,.4f})! PnL: +${partial_pnl:.2f} (+{partial_pct:.2f}%).")
                        self.record_trade_to_csv({
                            "symbol": symbol,
                            "side": side,
                            "entry_price": entry,
                            "exit_price": cur_price,
                            "qty": close_qty,
                            "margin": partial_margin,
                            "pnl_usdt": round(partial_pnl, 2),
                            "pnl_percent": round(partial_pct, 2),
                            "closed_at": datetime.now(VIETNAM_TZ),
                            "exit_reason": "Chốt lời 50% (TP1 @ 1R)"
                        })
                        if hasattr(self.notifier, "notify_partial_tp"):
                            self.notifier.notify_partial_tp(
                                symbol=symbol, close_qty=close_qty, rem_qty=pos["qty"],
                                exit_price=cur_price, pnl_usdt=partial_pnl, pnl_percent=partial_pct,
                                breakeven_sl=entry, final_tp=tp, is_dry_run=self.config.dry_run
                            )
                        self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)
                        continue

            # 2. Cơ chế Dời SL hòa vốn thông thường nếu không bật Partial TP
            elif self.config.use_breakeven_stop and not pos["breakeven_activated"]:
                if side == "BUY" and cur_price >= entry + initial_risk_dist:
                    pos["stop_loss"] = entry
                    pos["breakeven_activated"] = True
                    logger.info(f"[{symbol}] Đã dời SL về Break-even (${entry:,.4f}) sau khi đạt +1R lợi nhuận!")
                    self.save_state()
                elif side == "SHORT" and cur_price <= entry - initial_risk_dist:
                    pos["stop_loss"] = entry
                    pos["breakeven_activated"] = True
                    logger.info(f"[{symbol}] Đã dời SL về Break-even (${entry:,.4f}) sau khi đạt +1R lợi nhuận!")
                    self.save_state()

            # 2.5. Cơ chế Trailing Stop Loss Động (Dynamic Trailing Stop)
            if self.config.use_trailing_stop:
                activation_dist = initial_risk_dist * self.config.trailing_activation_rr
                step_ratio = self.config.trailing_step_percent / 100.0

                if side == "BUY" and cur_price >= entry + activation_dist:
                    step_dist = cur_price * step_ratio
                    new_sl = round(cur_price - step_dist, 4)
                    if new_sl > pos["stop_loss"]:
                        old_sl = pos["stop_loss"]
                        pos["stop_loss"] = new_sl
                        pos["trailing_active"] = True
                        logger.info(f"[{symbol}] 🚀 DÂNG TRAILING STOP: ${new_sl:,.4f} (cũ: ${old_sl:,.4f}) để khóa lợi nhuận!")
                        self.save_state()

                elif side == "SHORT" and cur_price <= entry - activation_dist:
                    step_dist = cur_price * step_ratio
                    new_sl = round(cur_price + step_dist, 4)
                    if new_sl < pos["stop_loss"]:
                        old_sl = pos["stop_loss"]
                        pos["stop_loss"] = new_sl
                        pos["trailing_active"] = True
                        logger.info(f"[{symbol}] 🚀 HẠ TRAILING STOP: ${new_sl:,.4f} (cũ: ${old_sl:,.4f}) để khóa lợi nhuận!")
                        self.save_state()

            # 2.8. Cơ chế Bắt Đỉnh Kiệt Sức Động Lượng (Volume Exhaustion Trailing TP - Bản 5.0)
            hit_exhaustion_zone = (side == "BUY" and cur_price >= entry + (initial_risk_dist * 1.5)) or (side == "SHORT" and cur_price <= entry - (initial_risk_dist * 1.5))
            if hit_exhaustion_zone and not pos.get("exhaustion_tp_done", False):
                tight_step = cur_price * 0.003
                ultra_sl = round(cur_price - tight_step, 4) if side == "BUY" else round(cur_price + tight_step, 4)
                should_update = (side == "BUY" and ultra_sl > pos["stop_loss"]) or (side == "SHORT" and ultra_sl < pos["stop_loss"])
                if should_update:
                    pos["stop_loss"] = ultra_sl
                    pos["exhaustion_tp_done"] = True
                    pos["trailing_active"] = True
                    logger.info(f"[{symbol}] 🔥 BẮT ĐỈNH KIỆT SỨC: Đã siết chặt Trailing Stop về ${ultra_sl:,.4f} để khóa đỉnh lợi nhuận!")
                    if hasattr(self.notifier, "send_message"):
                        self.notifier.send_message(
                            f"🔥 <b>BẮT ĐỈNH KIỆT SỨC (VOLUME EXHAUSTION TP) - {symbol}</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"• Vị thế đã đạt mức lãi ấn tượng (+1.5R)\n"
                            f"• <b>Trailing Stop Đỉnh:</b> Đã siết chặt về <code>${ultra_sl:,.4f}</code> (0.3% cách giá thị trường)\n"
                            f"• <i>Khóa chắc đỉnh sóng lợi nhuận, chống rủi ro rút râu đảo chiều!</i>"
                        )
                    self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)

            # 3. Xử lý khớp SL hoặc Take Profit cuối cùng
            if self.config.dry_run:
                is_hit_tp = False
                is_hit_sl = False

                if side == "BUY":
                    if cur_price >= tp:
                        is_hit_tp = True
                    elif cur_price <= pos["stop_loss"]:
                        is_hit_sl = True
                else:  # SHORT
                    if cur_price <= tp:
                        is_hit_tp = True
                    elif cur_price >= pos["stop_loss"]:
                        is_hit_sl = True

                if is_hit_tp or is_hit_sl:
                    exit_price = tp if is_hit_tp else pos["stop_loss"]
                    is_be = (exit_price == entry)

                    if is_hit_tp:
                        exit_reason = "Chốt Lời Toàn Phần (Final TP 🎯)"
                    elif is_be:
                        exit_reason = "Hòa Vốn (Breakeven 🛡️)"
                    elif pos.get("trailing_active") and ((side == "BUY" and exit_price > entry) or (side == "SELL" and exit_price < entry)):
                        exit_reason = "Chốt Lãi Trailing Stop 🚀"
                    else:
                        exit_reason = "Cắt Lỗ (Stop Loss 🛑)"

                    # Tính PnL cho khối lượng còn lại
                    rem_qty = pos["qty"]
                    if side == "BUY":
                        pnl_usdt = (exit_price - entry) * rem_qty
                    else:
                        pnl_usdt = (entry - exit_price) * rem_qty

                    pnl_pct = (pnl_usdt / pos["margin"]) * 100.0 if pos["margin"] > 0 else 0.0

                    # Cập nhật số dư giả lập
                    if simulated_balance_holder is not None:
                        simulated_balance_holder["balance"] += pnl_usdt

                    # Ghi lịch sử bộ nhớ và file CSV
                    closed_record = {
                        **pos,
                        "exit_price": exit_price,
                        "exit_reason": exit_reason,
                        "pnl_usdt": round(pnl_usdt, 2),
                        "pnl_percent": round(pnl_pct, 2),
                        "closed_at": datetime.now(VIETNAM_TZ)
                    }
                    self.trade_history.append(closed_record)
                    closed_symbols.append(symbol)

                    self.record_trade_to_csv(closed_record)

                    # Báo cáo Telegram & Console
                    self.notifier.notify_position_closed(
                        symbol=symbol,
                        exit_reason=exit_reason,
                        pnl_usdt=pnl_usdt,
                        pnl_percent=pnl_pct,
                        exit_price=exit_price,
                        is_dry_run=True
                    )
                    logger.info(f"[{symbol}] Đóng vị thế: {exit_reason} | PnL: ${pnl_usdt:+.2f} ({pnl_pct:+.2f}%)")

        for s in closed_symbols:
            del self.active_positions[s]

        if closed_symbols:
            self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)

    def close_all_positions(
        self,
        reason: str = "ĐÓNG KHẨN CẤP (PANIC CLOSE)",
        current_prices: Optional[Dict[str, float]] = None,
        simulated_balance_holder: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        NÚT DỪNG KHẨN CẤP (PANIC BUTTON):
        - Hủy toàn bộ lệnh chờ (SL / TP) trên sàn.
        - Đóng sạch toàn bộ các vị thế đang mở bằng lệnh Market.
        - Cập nhật số dư, ghi vào trade_history.csv và lưu state.
        """
        if not self.active_positions:
            return {"success": True, "closed_count": 0, "total_pnl": 0.0, "message": "Không có vị thế nào đang mở"}

        current_prices = current_prices or {}
        closed_count = 0
        total_pnl = 0.0
        closed_details = []

        logger.warning("🚨 [PANIC BUTTON] Đang kích hoạt đóng toàn bộ %d vị thế khẩn cấp! Lý do: %s", len(self.active_positions), reason)

        for symbol, pos in list(self.active_positions.items()):
            side = pos["side"]
            qty = pos["qty"]
            entry = pos["entry_price"]

            # Lấy giá thị trường hiện tại
            cur_price = current_prices.get(symbol)
            if not cur_price:
                filter_info = self.client.get_symbol_filter_info(symbol)
                cur_price = entry  # Fallback

            # 1. Hủy toàn bộ lệnh chờ của symbol trên sàn
            self.client.cancel_all_symbol_orders(symbol)

            # 2. Đặt lệnh Market ngược chiều để đóng vị thế ngay
            exit_side = "SELL" if side == "BUY" else "BUY"
            self.client.place_market_order(symbol, exit_side, qty)

            # 3. Tính PnL
            if side == "BUY":
                pnl = (cur_price - entry) * qty
            else:
                pnl = (entry - cur_price) * qty
            pnl_pct = (pnl / pos["margin"]) * 100.0 if pos["margin"] > 0 else 0.0

            total_pnl += pnl
            closed_count += 1

            if simulated_balance_holder is not None:
                simulated_balance_holder["balance"] += pnl

            # 4. Ghi nhận giao dịch
            record = {
                **pos,
                "exit_price": cur_price,
                "exit_reason": reason,
                "pnl_usdt": round(pnl, 2),
                "pnl_percent": round(pnl_pct, 2),
                "closed_at": datetime.now(VIETNAM_TZ)
            }
            self.trade_history.append(record)
            self.record_trade_to_csv(record)

            self.notifier.notify_position_closed(
                symbol=symbol,
                exit_reason=reason,
                pnl_usdt=pnl,
                pnl_percent=pnl_pct,
                exit_price=cur_price,
                is_dry_run=self.config.dry_run
            )
            closed_details.append(f"{symbol}: {pnl:+.2f} USDT")

        # Xóa sạch vị thế và lưu state
        self.active_positions.clear()
        self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)

        summary_msg = f"Đã đóng thành công {closed_count} vị thế. Tổng PnL: {total_pnl:+.2f} USDT ({', '.join(closed_details)})"
        logger.info("🚨 [PANIC CLOSE HOÀN TẤT]: %s", summary_msg)
        return {
            "success": True,
            "closed_count": closed_count,
            "total_pnl": round(total_pnl, 2),
            "message": summary_msg
        }

    def close_single_position(
        self,
        symbol: str,
        reason: str = "Đóng thủ công từ Web Dashboard",
        current_prices: Optional[Dict[str, float]] = None,
        simulated_balance_holder: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Đóng một vị thế cụ thể theo yêu cầu từ Web Dashboard hoặc Telegram"""
        if symbol not in self.active_positions:
            return {"success": False, "message": f"Không tìm thấy vị thế mở cho {symbol}"}

        pos = self.active_positions[symbol]
        side = pos["side"]
        qty = pos["qty"]
        entry = pos["entry_price"]

        current_prices = current_prices or {}
        cur_price = current_prices.get(symbol)
        if not cur_price:
            cur_price = entry

        # 1. Hủy lệnh chờ trên sàn
        self.client.cancel_all_symbol_orders(symbol)

        # 2. Đặt lệnh Market ngược chiều nếu không phải dry_run
        exit_side = "SELL" if side == "BUY" else "BUY"
        self.client.place_market_order(symbol, exit_side, qty)

        # 3. Tính PnL
        if side == "BUY":
            pnl = (cur_price - entry) * qty
        else:
            pnl = (entry - cur_price) * qty
        pnl_pct = (pnl / pos["margin"]) * 100.0 if pos["margin"] > 0 else 0.0

        if simulated_balance_holder is not None:
            simulated_balance_holder["balance"] += pnl

        # 4. Ghi nhận giao dịch
        record = {
            **pos,
            "exit_price": cur_price,
            "exit_reason": reason,
            "pnl_usdt": round(pnl, 2),
            "pnl_percent": round(pnl_pct, 2),
            "closed_at": datetime.now(VIETNAM_TZ)
        }
        self.trade_history.append(record)
        self.record_trade_to_csv(record)

        self.notifier.notify_position_closed(
            symbol=symbol,
            exit_reason=reason,
            pnl_usdt=pnl,
            pnl_percent=pnl_pct,
            exit_price=cur_price,
            is_dry_run=self.config.dry_run
        )

        del self.active_positions[symbol]
        self.save_state(simulated_balance_holder.get("balance") if simulated_balance_holder else None)

        msg = f"Đã đóng thành công vị thế {symbol} tại giá ${cur_price:,.4f}. PnL: {pnl:+.2f} USDT ({pnl_pct:+.2f}%)"
        logger.info(msg)
        return {"success": True, "symbol": symbol, "pnl": round(pnl, 2), "pnl_percent": round(pnl_pct, 2), "message": msg}

    def get_symbol_performance_breakdown(self) -> Dict[str, Any]:
        """Thống kê chi tiết lãi/lỗ và tỷ lệ thắng theo từng cặp coin"""
        history_file = self.config.trade_history_file
        if not os.path.exists(history_file):
            return {"by_symbol": {}, "best_symbol": None, "worst_symbol": None, "max_win_streak": 0, "max_loss_streak": 0, "total_closed": 0}

        by_sym: Dict[str, Dict[str, Any]] = {}
        trade_pnl_list = []

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                for r in reader:
                    sym = r.get("symbol", "UNKNOWN")
                    try:
                        pnl = float(r.get("pnl_usdt", 0.0))
                    except Exception:
                        pnl = 0.0
                    trade_pnl_list.append(pnl)

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

            sorted_symbols = sorted(by_sym.items(), key=lambda x: x[1]["net_pnl"], reverse=True)
            best_sym = sorted_symbols[0] if sorted_symbols else None
            worst_sym = sorted_symbols[-1] if sorted_symbols else None

            # Tính win streak / loss streak
            cur_win = 0
            max_win = 0
            cur_loss = 0
            max_loss = 0
            for p in trade_pnl_list:
                if p > 0:
                    cur_win += 1
                    cur_loss = 0
                    if cur_win > max_win:
                        max_win = cur_win
                elif p < 0:
                    cur_loss += 1
                    cur_win = 0
                    if cur_loss > max_loss:
                        max_loss = cur_loss
                else:
                    cur_win = 0
                    cur_loss = 0

            return {
                "by_symbol": dict(sorted_symbols),
                "best_symbol": {"symbol": best_sym[0], **best_sym[1]} if best_sym else None,
                "worst_symbol": {"symbol": worst_sym[0], **worst_sym[1]} if worst_sym else None,
                "max_win_streak": max_win,
                "max_loss_streak": max_loss,
                "total_closed": len(trade_pnl_list)
            }
        except Exception as e:
            logger.error(f"Lỗi phân tích performance: {e}")
            return {"by_symbol": {}, "best_symbol": None, "worst_symbol": None, "max_win_streak": 0, "max_loss_streak": 0, "total_closed": 0}

    def execute_manual_order(
        self,
        symbol: str,
        side: str,
        balance: float,
        leverage: Optional[int] = None,
        risk_percent: Optional[float] = None,
        simulated_balance_holder: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mở lệnh thủ công 1-Click từ Web Dashboard hoặc Telegram Bot"""
        if symbol in self.active_positions:
            return {"success": False, "message": f"Vị thế {symbol} đã đang mở từ trước!"}

        if len(self.active_positions) >= self.config.max_concurrent_positions:
            return {"success": False, "message": f"Đã đạt giới hạn tối đa {self.config.max_concurrent_positions} vị thế cùng lúc!"}

        side = side.upper()
        if side not in ["BUY", "SELL"]:
            return {"success": False, "message": "Chiều lệnh phải là BUY hoặc SELL"}

        # Lấy giá hiện tại
        ltf_df = self.client.get_klines_df(symbol, interval=self.config.ltf, limit=10)
        if ltf_df.empty:
            return {"success": False, "message": f"Không lấy được giá thị trường cho {symbol}"}

        cur_price = float(ltf_df.iloc[-1]['close'])
        filter_info = self.client.get_symbol_filter_info(symbol)

        # Tính khoảng cách Stop Loss (1.5% mặc định) và Take Profit (1:2 R:R)
        sl_pct = 0.015
        if side == "BUY":
            stop_loss = round(cur_price * (1 - sl_pct), 4)
            take_profit = round(cur_price * (1 + sl_pct * self.config.risk_reward_ratio), 4)
        else:
            stop_loss = round(cur_price * (1 + sl_pct), 4)
            take_profit = round(cur_price * (1 - sl_pct * self.config.risk_reward_ratio), 4)

        # Tính khối lượng
        used_risk = risk_percent if (risk_percent and risk_percent > 0) else self.config.risk_per_trade_percent
        risk_amount = balance * (used_risk / 100.0)
        risk_distance = abs(cur_price - stop_loss)
        if risk_distance <= 0:
            return {"success": False, "message": "Khoảng cách SL không hợp lệ"}

        raw_qty = risk_amount / risk_distance
        step = filter_info.get("step_size", 0.001)
        precision = 0
        if "." in str(step):
            precision = len(str(step).split(".")[1].rstrip("0"))
        qty = round(round(raw_qty / step) * step, precision)

        min_qty = filter_info.get("min_qty", 0.001)
        if qty < min_qty:
            qty = min_qty

        margin = (qty * cur_price) / (leverage or self.config.leverage)

        success = self.execute_entry(
            symbol=symbol,
            side=side,
            entry_price=cur_price,
            qty=qty,
            stop_loss=stop_loss,
            take_profit=take_profit,
            margin=margin,
            risk_amount=risk_amount
        )

        if success:
            if simulated_balance_holder:
                self.save_state(simulated_balance_holder.get("balance"))
            self.notifier.notify_signal(
                symbol=symbol,
                signal=side,
                entry=cur_price,
                sl=stop_loss,
                tp=take_profit,
                reason="Lệnh bán tự động 1-Click (Manual Trigger)"
            )
            return {
                "success": True,
                "symbol": symbol,
                "side": side,
                "entry_price": cur_price,
                "qty": qty,
                "margin": round(margin, 2),
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "message": f"Đã khớp lệnh {side} {symbol} thành công tại giá ${cur_price:,.4f}!"
            }
        return {"success": False, "message": "Không thể khớp lệnh vào hệ thống"}


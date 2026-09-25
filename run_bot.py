import time
import sys
import os
import logging

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import utils.network_fix
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live

from config.settings import config
from core.binance_client import BinanceFuturesClient
from core.order_manager import OrderManager
from risk.risk_manager import RiskManager
from strategy.trend_pullback import TrendPullbackStrategy
from strategy.base_strategy import Signal
from scanner.market_scanner import MarketScanner
from notifier.telegram_bot import TelegramNotifier
from utils.watchdog import SystemWatchdog
from core.ai_copilot import AICopilot

# Cấu hình logging ra cả Console và File bot.log
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

# File handler (tự động ghi mọi nhật ký vào bot.log)
try:
    file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
except Exception as e:
    print(f"Không thể mở file log: {e}")

logger = logging.getLogger("BotBinance")
console = Console()


def print_banner():
    mode_text = "[bold yellow]DRY-RUN (GIẢ LẬP / PAPER TRADING)[/bold yellow]" if config.dry_run else (
        "[bold cyan]BINANCE TESTNET[/bold cyan]" if config.use_testnet else "[bold red]BINANCE LIVE REAL[/bold red]"
    )
    # Market Scanner
    enable_scanner_str = f"[green]BẬT (Vol > ${config.min_24h_volume_usdt:,.0f})[/green]" if config.enable_scanner else f"[yellow]TẮT ({config.target_symbols})[/yellow]"
    partial_tp_text = f"[green]Chốt {int(config.partial_tp_ratio * 100)}% @ 1R + Gồng {int((1 - config.partial_tp_ratio) * 100)}%[/green]" if config.use_partial_tp else "[white]TẮT[/white]"
    web_text = f"[green]http://localhost:{config.web_port}[/green]" if config.enable_web else "[white]TẮT[/white]"

    banner = Panel(
        f"[bold green]=====================================================\n"
        f"          BINANCE FUTURES QUANT TRADING BOT          \n"
        f"=====================================================[/bold green]\n"
        f"• Chế độ vận hành: {mode_text}\n"
        f"• Đòn bẩy (Leverage): [bold cyan]{config.leverage}x ({config.margin_type})[/bold cyan]\n"
        f"• Cơ chế Quản lý vốn: [bold magenta]{config.sizing_mode} (Risk: {config.risk_per_trade_percent}%/lệnh)[/bold magenta]\n"
        f"• Chốt lời từng phần: {partial_tp_text}\n"
        f"• Tỷ lệ R:R mục tiêu: [bold]{config.risk_reward_ratio}:1[/bold] | Dời SL hòa vốn (Breakeven): [bold green]{config.use_breakeven_stop}[/bold green]\n"
        f"• Giới hạn lỗ ngày (Max Daily Loss): [bold red]{config.max_daily_loss_percent}%[/bold red]\n"
        f"• Vị thế mở tối đa: [bold]{config.max_concurrent_positions} cặp[/bold]\n"
        f"• Market Scanner: {enable_scanner_str}\n"
        f"• Bộ lọc Institutional: [green]ADX ≥ {config.adx_min}[/green] | BTC Crash: {'[green]BẬT (-' + str(config.btc_crash_threshold_percent) + '%)[/green]' if config.enable_btc_crash_protection else '[yellow]TẮT[/yellow]'} | News Filter: {'[green]BẬT (Né tin Mỹ)[/green]' if config.enable_news_filter else '[yellow]TẮT[/yellow]'}\n"
        f"• Web Dashboard: {web_text}\n"
        f"• Nhật ký & Trạng thái: [cyan]{config.log_file}[/cyan] | [cyan]{config.state_file}[/cyan] | [cyan]{config.trade_history_file}[/cyan]\n"
        f"• Telegram Controller: {'[green]BẬT (2-Way Interactive)[/green]' if config.telegram_enabled else '[white]TẮT[/white]'}\n",
        title="[bold yellow]HỆ THỐNG GIAO DỊCH TỰ ĐỘNG QUANT AI[/bold yellow]",
        expand=False
    )
    console.print(banner)


class BotContext:
    """Đối tượng chia sẻ ngữ cảnh giữa Trading Engine, Telegram Bot và Web Dashboard"""
    def __init__(self, order_manager, client, simulated_balance_holder, watchdog=None, risk_manager=None, scanner=None, strategy=None, config=None, ai_copilot=None):
        self.order_manager = order_manager
        self.client = client
        self.simulated_balance_holder = simulated_balance_holder
        self.watchdog = watchdog
        self.risk_manager = risk_manager
        self.scanner = scanner
        self.strategy = strategy
        self.config = config or getattr(order_manager, "config", None)
        self.ai_copilot = ai_copilot or AICopilot(self.config)
        self.current_prices = {}
        self.is_paused = False

        # Wire authoritative IPC Execution Service Client (Hard Cutover)
        try:
            from core.execution_service.client import ExecutionServiceClient
            svc_port = getattr(self.config, "execution_service_port", 50051)
            svc_host = getattr(self.config, "execution_service_host", "127.0.0.1")
            svc_token = str(getattr(self.config, "ipc_token_strategy", "") or "").strip()
            if not svc_token:
                raise RuntimeError("Strategy IPC credential is not configured")
            self.execution_service_client = ExecutionServiceClient(
                host=svc_host, port=svc_port, auth_token=svc_token, principal="strategy-client"
            )
            if self.order_manager and getattr(self.order_manager, "execution_service_client", None) is None:
                self.order_manager.execution_service_client = self.execution_service_client
            if self.risk_manager:
                self.risk_manager.execution_service_client = self.execution_service_client
                self.risk_manager._load_circuit_breaker()
        except Exception:
            self.execution_service_client = None
            if self.risk_manager:
                self.risk_manager.execution_service_client = None

    def get_current_balance(self) -> float:
        if config.dry_run:
            return float(self.simulated_balance_holder.get("balance", 1000.0))
        return self.client.get_available_balance()

    def get_current_prices(self) -> Dict[str, float]:
        return self.current_prices

    def get_total_unrealized_pnl(self) -> float:
        total = 0.0
        for sym, pos in self.order_manager.active_positions.items():
            cur_p = self.current_prices.get(sym, pos["entry_price"])
            if pos["side"] == "BUY":
                total += (cur_p - pos["entry_price"]) * pos["qty"]
            else:
                total += (pos["entry_price"] - cur_p) * pos["qty"]
        return round(total, 2)


def main():
    import argparse
    import threading
    parser = argparse.ArgumentParser(description="Binance Futures Trading Bot")
    parser.add_argument("--test-once", action="store_true", help="Chạy đúng 1 chu kỳ quét để test hệ thống rồi thoát")
    args = parser.parse_args()

    print_banner()

    # 1. Khởi tạo các thành phần
    client = BinanceFuturesClient(config)
    notifier = TelegramNotifier(config)
    risk_manager = RiskManager(config)
    strategy = TrendPullbackStrategy(rr_ratio=config.risk_reward_ratio, atr_multiplier=1.5, adx_min=config.adx_min)
    scanner = MarketScanner(config, client, strategy)
    order_manager = OrderManager(config, client, notifier)
    watchdog = SystemWatchdog(config, notifier)
    ai_copilot = AICopilot(config)

    # Phục hồi vốn mô phỏng từ file bot_state.json nếu có
    saved_balance = order_manager.load_state()
    initial_balance = saved_balance if saved_balance is not None else 1000.0
    simulated_balance_holder = {"balance": initial_balance}
    logger.info("Vốn khởi điểm: $%.2f USDT (Phục hồi từ state: %s)", initial_balance, saved_balance is not None)

    # 2. Khởi tạo BotContext
    bot_context = BotContext(
        order_manager,
        client,
        simulated_balance_holder,
        watchdog=watchdog,
        risk_manager=risk_manager,
        scanner=scanner,
        strategy=strategy,
        config=config,
        ai_copilot=ai_copilot
    )

    # 3. Kích hoạt Bộ điều khiển Telegram 2 chiều (nếu bật)
    if config.telegram_enabled:
        notifier.start_listener(bot_context)

    # 4. Kích hoạt SystemWatchdog giám sát máy chủ VPS
    if not args.test_once:
        watchdog.start_monitoring()

    # 5. Khởi chạy Web Dashboard chạy ngầm (nếu bật)
    if config.enable_web and not args.test_once:
        from web.app import app, set_bot_context
        set_bot_context(bot_context)

        def start_web():
            import uvicorn
            uvicorn.run(app, host="0.0.0.0", port=config.web_port, log_level="warning")

        web_thread = threading.Thread(target=start_web, daemon=True, name="WebDashboard")
        web_thread.start()
        logger.info("Web Dashboard đang chạy tại: http://127.0.0.1:%d", config.web_port)

    # Kiểm tra kết nối sàn
    if not client.test_connection():
        console.print("[yellow][!] Cảnh báo: Không thể kết nối tới Binance Futures. Đang chạy ở chế độ offline data.[/yellow]")
    else:
        # Kiểm tra chiết khấu phí BNB
        client.check_fee_discount_recommendation()

    # Tự động huấn luyện mô hình AI từ lịch sử giao dịch ngay khi khởi động
    try:
        from core.ai_trade_trainer import AITradeTrainer
        trainer = AITradeTrainer()
        trainer.train_from_history()
        logger.info("🧠 [AI AUTO-TRAIN] Đã hoàn tất huấn luyện khởi động từ lịch sử lệnh.")
    except Exception as e:
        logger.debug("Lỗi khởi động AI Trainer: %s", e)

    console.print("[green][✓] Bot đã khởi động thành công. Bắt đầu vòng lặp quét thị trường...[/green]")
    notifier.send_message("🚀 <b>Hệ thống Bot Binance Futures đã khởi động thành công!</b>\nGõ <code>/help</code> để xem các lệnh điều khiển.")

    loop_count = 0
    vn_tz = timezone(timedelta(hours=7))
    last_backup_day = datetime.now(vn_tz).date()

    try:
        while True:
            loop_count += 1
            now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S (VN)")

            # Tự động huấn luyện AI định kỳ mỗi 30 chu kỳ (khoảng 15 phút)
            if loop_count % 30 == 0:
                try:
                    import threading
                    from core.ai_trade_trainer import AITradeTrainer
                    threading.Thread(target=lambda: AITradeTrainer().train_from_history(), daemon=True).start()
                except Exception:
                    pass

            # 0. Kiểm tra sao lưu tự động ngày mới (00:00 VN)
            current_day = datetime.now(vn_tz).date()
            if current_day != last_backup_day:
                last_backup_day = current_day
                if config.enable_daily_backup:
                    logger.info("Thực hiện gửi báo cáo tổng kết và sao lưu dữ liệu ngày mới...")
                    notifier.send_daily_backup_and_report()

            # 1. Lấy số dư hiện tại
            if config.dry_run:
                balance = simulated_balance_holder["balance"]
            else:
                balance = client.get_available_balance()

            # 2. Thu thập giá hiện tại của các cặp đang có vị thế để cập nhật
            current_prices = {}
            for sym in list(order_manager.active_positions.keys()):
                info = client.get_symbol_filter_info(sym)
                ltf_df = client.get_klines_df(sym, interval=config.ltf, limit=5)
                if not ltf_df.empty:
                    current_prices[sym] = float(ltf_df.iloc[-1]['close'])

            bot_context.current_prices = current_prices

            # Cập nhật vị thế, dời SL về breakeven hoặc đóng lệnh nếu chạm SL/TP
            order_manager.check_and_update_positions(current_prices, simulated_balance_holder)

            # 3. Hiển thị bảng trạng thái vị thế
            open_count = order_manager.get_open_position_count()
            console.print(f"\n[bold cyan]--- [Chu kỳ #{loop_count}] {now_str} | Vốn: ${balance:,.2f} USDT | Vị thế mở: {open_count}/{config.max_concurrent_positions} ---[/bold cyan]")

            if open_count > 0:
                pos_table = Table(title="CÁC VỊ THẾ ĐANG MỞ (LIVE POSITIONS)")
                pos_table.add_column("Symbol", style="cyan")
                pos_table.add_column("Side", style="bold")
                pos_table.add_column("Entry", justify="right")
                pos_table.add_column("Giá hiện tại", justify="right")
                pos_table.add_column("Stop Loss", justify="right", style="red")
                pos_table.add_column("Take Profit", justify="right", style="green")
                pos_table.add_column("Ký quỹ", justify="right")
                pos_table.add_column("PnL Tạm Tính", justify="right")
                pos_table.add_column("Trạng thái", justify="center")

                total_unrealized_pnl = 0.0

                for sym, pos in order_manager.active_positions.items():
                    cur_p = current_prices.get(sym, pos["entry_price"])
                    side_color = "green" if pos["side"] == "BUY" else "red"

                    # Tính PnL tạm tính theo thời gian thực
                    if pos["side"] == "BUY":
                        u_pnl = (cur_p - pos["entry_price"]) * pos["qty"]
                    else:
                        u_pnl = (pos["entry_price"] - cur_p) * pos["qty"]
                    u_pct = (u_pnl / pos["margin"]) * 100.0 if pos["margin"] > 0 else 0.0
                    total_unrealized_pnl += u_pnl

                    pnl_color = "bold green" if u_pnl >= 0 else "bold red"
                    pnl_str = f"[{pnl_color}]{u_pnl:+.2f} ({u_pct:+.2f}%)[/{pnl_color}]"

                    if pos.get("partial_tp_activated"):
                        status_str = "[bold green]🎯 Đã chốt 50% (SL Hòa)[/bold green]"
                    elif pos.get("breakeven_activated"):
                        status_str = "[bold yellow]🛡️ Dời SL Hòa vốn[/bold yellow]"
                    else:
                        status_str = "[cyan]⚡ Đang chạy[/cyan]"

                    pos_table.add_row(
                        sym,
                        f"[{side_color}]{pos['side']}[/{side_color}]",
                        f"${pos['entry_price']:,.4f}",
                        f"${cur_p:,.4f}",
                        f"${pos['stop_loss']:,.4f}",
                        f"${pos['take_profit']:,.4f}",
                        f"${pos['margin']:.2f}",
                        pnl_str,
                        status_str
                    )

                tot_color = "bold green" if total_unrealized_pnl >= 0 else "bold red"
                pos_table.caption = f"Tổng PnL Tạm Tính (Unrealized PnL): [{tot_color}]{total_unrealized_pnl:+.2f} USDT[/{tot_color}]"
                console.print(pos_table)

            # 4. Kiểm tra xem có đang tạm dừng từ Telegram / Web hay không
            if bot_context.is_paused:
                console.print("[yellow]⏸️ [Bot Controller]: Bot đang ở trạng thái TẠM DỪNG (PAUSED). Không mở thêm vị thế mới.[/yellow]")
                time.sleep(15)
                continue

            # 5. Kiểm tra điều kiện mở lệnh mới từ Risk Manager
            can_open, risk_reason = risk_manager.can_open_new_position(open_count, balance)

            # Luôn quét thị trường để cập nhật Radar hiển thị trên Web Dashboard
            console.print("[blue][*] Đang quét thị trường cập nhật Live Radar & tìm setup...[/blue]")
            setups = scanner.scan_for_setups(max_pairs=20)

            if not can_open:
                console.print(f"[yellow][Risk Manager]: {risk_reason}. Tạm dừng vào lệnh mới (Live Radar vẫn quét 24/7).[/yellow]")
            else:
                if not setups:
                    console.print("[dim]Chưa có cặp nào xuất hiện tín hiệu đảo chiều pullback chuẩn. Tiếp tục chờ...[/dim]")
                else:
                    for setup in setups:
                        if order_manager.get_open_position_count() >= config.max_concurrent_positions:
                            break

                        sym = setup["symbol"]
                        if sym in order_manager.active_positions:
                            continue

                        # Lấy bộ lọc của symbol (step_size, min_qty, min_notional)
                        filter_info = client.get_symbol_filter_info(sym)

                        # Tính toán Position Size động
                        sizing = risk_manager.calculate_position_size(
                            balance=balance,
                            entry_price=setup["entry_price"],
                            stop_loss_price=setup["stop_loss"],
                            step_size=filter_info["step_size"],
                            min_qty=filter_info["min_qty"],
                            min_notional=filter_info["min_notional"]
                        )

                        if not sizing["valid"]:
                            logger.info(f"[{sym}] Bỏ qua setup: {sizing['reason']}")
                            continue

                        # AI Gatekeeper (Thẩm định định lượng AI trước khi mở lệnh)
                        ai_score = None
                        if getattr(config, "ai_trade_audit", True) and bot_context.ai_copilot:
                            ind = setup.get("indicators", {})
                            audit_sig = {
                                "symbol": sym,
                                "side": setup["signal"],
                                "entry_price": setup["entry_price"],
                                "stop_loss": setup["stop_loss"],
                                "take_profit": setup["take_profit"],
                                "leverage": sizing.get("leverage"),
                                "adx": ind.get("adx", 25.0) if isinstance(ind, dict) else 25.0,
                                "rsi": ind.get("rsi", 50.0) if isinstance(ind, dict) else 50.0,
                                "strategy": setup.get("reason", "TREND_PULLBACK")
                            }
                            audit_res = bot_context.ai_copilot.audit_trade_signal(audit_sig, bot_context=bot_context)
                            ai_score = audit_res.get("score")
                            if not audit_res.get("approved", True):
                                logger.info(f"🛡️ [AI Gatekeeper] TỪ CHỐI setup {sym} ({setup['signal']}): Điểm {ai_score}/10 < {config.ai_min_audit_score}. Lý do: {audit_res.get('reason')}")
                                continue
                            else:
                                logger.info(f"🛡️ [AI Gatekeeper] DUYỆT setup {sym} ({setup['signal']}): Điểm {ai_score}/10 ({audit_res.get('provider_used')}). Lý do: {audit_res.get('reason')}")

                        # Thông báo tín hiệu (kèm vẽ ảnh biểu đồ nến Bản 5.0)
                        notifier.notify_signal(
                            symbol=sym,
                            signal=setup["signal"],
                            entry=setup["entry_price"],
                            sl=setup["stop_loss"],
                            tp=setup["take_profit"],
                            reason=setup["reason"],
                            df=setup.get("df")
                        )

                        # Thực thi mở lệnh
                        success = order_manager.execute_entry(
                            symbol=sym,
                            side=setup["signal"],
                            entry_price=setup["entry_price"],
                            qty=sizing["qty"],
                            stop_loss=setup["stop_loss"],
                            take_profit=setup["take_profit"],
                            margin=sizing["margin"],
                            risk_amount=sizing["risk_amount"],
                            leverage=sizing.get("leverage"),
                            ai_score=ai_score
                        )

                        if success:
                            console.print(f"[bold green][✓] ĐÃ MỞ VỊ THẾ {setup['signal']} CHO {sym}:[/bold green] "
                                          f"Qty: {sizing['qty']} | Đòn bẩy: {sizing.get('leverage')}x | Ký quỹ: ${sizing['margin']:.2f} | Rủi ro: ${sizing.get('risk_amount', 0.0):.2f} ({sizing.get('risk_percent_actual', sizing.get('risk_percent', 1.0))}%)")

            if args.test_once:
                console.print("\n[bold green][✓] Hoàn thành 1 chu kỳ quét kiểm thử (--test-once) thành công![/bold green]")
                break

            # Nghỉ 30 giây giữa các chu kỳ quét
            time.sleep(30)

    except KeyboardInterrupt:
        console.print("\n[yellow][!] Nhận lệnh dừng từ bàn phím (Ctrl+C). Đang tắt bot an toàn...[/yellow]")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Lỗi không mong muốn trong vòng lặp chính: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

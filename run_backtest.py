import sys
import os
import argparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import utils.network_fix
from binance.client import Client
from config.settings import config
from core.binance_client import BinanceFuturesClient
from backtest.backtester import FuturesBacktester
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def run_backtest_cli():
    parser = argparse.ArgumentParser(description="Chạy kiểm thử (Backtest) Chiến lược Binance Futures")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Cặp giao dịch (mặc định BTCUSDT)")
    parser.add_argument("--balance", type=float, default=1000.0, help="Vốn ban đầu ($ USDT)")
    parser.add_argument("--risk", type=float, default=1.0, help="Rủi ro mỗi lệnh (% vốn)")
    parser.add_argument("--rr", type=float, default=1.5, help="Tỷ lệ Risk:Reward (ví dụ 1.5)")
    parser.add_argument("--limit", type=int, default=500, help="Số nến cần lấy (tối đa 1500)")
    args = parser.parse_args()

    console.print(Panel(f"[bold cyan]CHẠY KIỂM THỬ CHIẾN LƯỢC (BACKTEST) - {args.symbol}[/bold cyan]\n"
                        f"Vốn: [green]${args.balance:,.2f}[/green] | Risk/Trade: [yellow]{args.risk}%[/yellow] | R:R: [magenta]1:{args.rr}[/magenta]"))

    client = BinanceFuturesClient(config)

    console.print(f"[*] Đang tải dữ liệu nến Binance {args.symbol} (HTF: 1h, LTF: 15m)...")
    htf_df = client.get_klines_df(args.symbol, interval="1h", limit=min(args.limit, 1000))
    ltf_df = client.get_klines_df(args.symbol, interval="15m", limit=min(args.limit * 4, 1500))

    if htf_df.empty or ltf_df.empty:
        console.print("[red][!] Không thể tải dữ liệu nến từ sàn Binance. Vui lòng kiểm tra kết nối mạng.[/red]")
        sys.exit(1)

    console.print(f"[green][✓] Đã tải thành công {len(htf_df)} nến 1H và {len(ltf_df)} nến 15m.[/green]")

    backtester = FuturesBacktester(
        initial_balance=args.balance,
        risk_percent=args.risk,
        rr_ratio=args.rr,
        fee_rate=0.0005,
        use_breakeven=True
    )

    results = backtester.run(htf_df, ltf_df)

    if "error" in results or results.get("total_trades", 0) == 0:
        console.print(f"[yellow]{results.get('message', results.get('error'))}[/yellow]")
        return

    # In kết quả dạng bảng đẹp mắt
    table = Table(title=f"KẾT QUẢ KIỂM THỬ (BACKTEST SUMMARY) - {args.symbol}")
    table.add_column("Chỉ số", style="cyan", no_wrap=True)
    table.add_column("Giá trị", style="bold")

    pnl_color = "green" if results["net_profit"] >= 0 else "red"
    win_color = "green" if results["win_rate"] >= 50 else "yellow"

    table.add_row("Vốn ban đầu", f"${results['initial_balance']:,.2f}")
    table.add_row("Vốn kết thúc", f"${results['final_balance']:,.2f}")
    table.add_row("Lợi nhuận ròng (Net Profit)", f"[{pnl_color}]${results['net_profit']:+,.2f} ({results['net_profit_percent']:+.2f}%)[/{pnl_color}]")
    table.add_row("Tổng số lệnh kích hoạt", str(results["total_trades"]))
    table.add_row("Lệnh Thắng / Thua / Hòa", f"[green]{results['winning_trades']}[/green] / [red]{results['losing_trades']}[/red] / [blue]{results['breakeven_trades']}[/blue]")
    table.add_row("Tỷ lệ thắng (Win Rate)", f"[{win_color}]{results['win_rate']}%[/{win_color}]")
    table.add_row("Hệ số Lãi/Lỗ (Profit Factor)", f"{results['profit_factor']}")
    table.add_row("Mức sụt giảm tối đa (Max Drawdown)", f"[red]{results['max_drawdown_percent']}%[/red]")

    console.print(table)


if __name__ == "__main__":
    run_backtest_cli()

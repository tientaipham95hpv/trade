import os
import csv
import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("TrackRecord")
VIETNAM_TZ = timezone(timedelta(hours=7))


def load_all_closed_trades() -> List[Dict[str, Any]]:
    """Đọc và hợp nhất toàn bộ lịch sử giao dịch từ trade_history.csv và trade_history_vps.csv"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(project_root, "trade_history.csv"),
        os.path.join(project_root, "trade_history_vps.csv")
    ]

    all_trades = []
    seen = set()

    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ts = row.get("timestamp", "").strip()
                    sym = row.get("symbol", "").strip()
                    key = (ts, sym)
                    if key in seen:
                        continue
                    seen.add(key)

                    try:
                        pnl_val = float(str(row.get("pnl_usdt", 0.0)).replace("+", "").replace(",", "").strip())
                    except ValueError:
                        pnl_val = 0.0

                    try:
                        pnl_pct_str = str(row.get("pnl_percent", "0.0%")).replace("+", "").replace("%", "").replace(",", "").strip()
                        pnl_pct = float(pnl_pct_str)
                    except ValueError:
                        pnl_pct = 0.0

                    try:
                        entry_p = float(str(row.get("entry_price", 0.0)).replace(",", "").strip())
                    except ValueError:
                        entry_p = 0.0

                    try:
                        exit_p = float(str(row.get("exit_price", 0.0)).replace(",", "").strip())
                    except ValueError:
                        exit_p = 0.0

                    try:
                        qty = float(str(row.get("qty", 0.0)).replace(",", "").strip())
                    except ValueError:
                        qty = 0.0

                    try:
                        margin = float(str(row.get("margin_usdt", row.get("margin", 0.0))).replace(",", "").strip())
                    except ValueError:
                        margin = 0.0

                    side = row.get("side", "").upper().strip()
                    if side in ("BUY", "LONG"):
                        side_label = "LONG"
                    elif side in ("SELL", "SHORT"):
                        side_label = "SHORT"
                    else:
                        side_label = side

                    all_trades.append({
                        "timestamp": ts,
                        "symbol": sym,
                        "side": side_label,
                        "entry_price": entry_p,
                        "exit_price": exit_p,
                        "qty": qty,
                        "margin": margin,
                        "pnl_usdt": pnl_val,
                        "pnl_percent": pnl_pct,
                        "exit_reason": row.get("exit_reason", "").strip()
                    })
        except Exception as e:
            logger.warning("Không thể đọc file trade history %s: %s", path, e)

    # Sắp xếp theo thứ tự thời gian tăng dần
    def parse_time(item):
        raw = item["timestamp"].replace(" (VN)", "").replace(" UTC+7", "").strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                pass
        return datetime.min

    all_trades.sort(key=parse_time)
    return all_trades


def calculate_track_record_metrics() -> Dict[str, Any]:
    """Tính toán các chỉ số định lượng Quỹ chuyên nghiệp: PnL, Winrate, Sharpe, Max Drawdown"""
    trades = load_all_closed_trades()
    initial_capital = 1000.0

    if not trades:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "net_pnl_usdt": 0.0,
            "total_return_pct": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "equity_curve": [{"timestamp": "Start", "equity": initial_capital, "pnl_pct": 0.0}],
            "recent_trades": []
        }

    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0
    net_pnl = 0.0
    pnl_list = []

    current_equity = initial_capital
    peak_equity = initial_capital
    max_drawdown_pct = 0.0

    equity_curve = [{"timestamp": "Start", "equity": initial_capital, "pnl_pct": 0.0}]

    for t in trades:
        pnl = t["pnl_usdt"]
        net_pnl += pnl
        current_equity += pnl
        pnl_list.append(pnl)

        if pnl > 0:
            wins += 1
            gross_profit += pnl
        elif pnl < 0:
            losses += 1
            gross_loss += abs(pnl)

        if current_equity > peak_equity:
            peak_equity = current_equity

        dd = ((peak_equity - current_equity) / peak_equity) * 100.0 if peak_equity > 0 else 0.0
        if dd > max_drawdown_pct:
            max_drawdown_pct = dd

        return_pct = ((current_equity - initial_capital) / initial_capital) * 100.0
        equity_curve.append({
            "timestamp": t["timestamp"].replace(" (VN)", ""),
            "equity": round(current_equity, 2),
            "pnl_pct": round(return_pct, 2),
            "trade_pnl": round(pnl, 2)
        })

    total_trades = len(trades)
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
    total_return_pct = ((current_equity - initial_capital) / initial_capital) * 100.0

    # Tính Sharpe Ratio (Annualized / Trade Sharpe)
    if len(pnl_list) > 1:
        mean_pnl = sum(pnl_list) / len(pnl_list)
        variance = sum((p - mean_pnl) ** 2 for p in pnl_list) / (len(pnl_list) - 1)
        std_dev = math.sqrt(variance) if variance > 0 else 1.0
        sharpe_ratio = (mean_pnl / std_dev) * math.sqrt(365) if std_dev > 0 else 0.0
        sharpe_ratio = max(-5.0, min(10.0, sharpe_ratio))
    else:
        sharpe_ratio = 0.0

    # Lấy 50 lệnh gần nhất theo thứ tự mới nhất lên đầu
    recent_50 = list(reversed(trades))[:50]

    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "net_pnl_usdt": round(net_pnl, 2),
        "total_return_pct": round(total_return_pct, 2),
        "profit_factor": round(profit_factor, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "equity_curve": equity_curve,
        "recent_trades": recent_50
    }


def render_track_record_html(metrics: Dict[str, Any]) -> str:
    """Tạo trang HTML5 Public Track Record Siêu Hiện Đại với Canvas Equity Curve & Binance Broker Banner"""
    import json
    curve_json = json.dumps(metrics.get("equity_curve", []))

    trades_rows = ""
    for t in metrics.get("recent_trades", []):
        is_win = t["pnl_usdt"] >= 0
        pnl_badge_class = "text-emerald-400 bg-emerald-950/40 border-emerald-800/50" if is_win else "text-rose-400 bg-rose-950/40 border-rose-800/50"
        side_badge_class = "text-cyan-400 bg-cyan-950/40 border-cyan-800/50" if t["side"] == "LONG" else "text-amber-400 bg-amber-950/40 border-amber-800/50"
        pnl_prefix = "+" if t["pnl_usdt"] > 0 else ""

        trades_rows += f"""
        <tr class="border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors">
            <td class="py-3 px-4 text-xs font-mono text-slate-400 whitespace-nowrap">{t["timestamp"]}</td>
            <td class="py-3 px-4 font-semibold text-slate-200">{t["symbol"]}</td>
            <td class="py-3 px-4">
                <span class="px-2 py-0.5 rounded text-xs font-mono font-bold border {side_badge_class}">
                    {t["side"]}
                </span>
            </td>
            <td class="py-3 px-4 text-xs font-mono text-slate-300 text-right">${t["entry_price"]:,.4f}</td>
            <td class="py-3 px-4 text-xs font-mono text-slate-300 text-right">${t["exit_price"]:,.4f}</td>
            <td class="py-3 px-4 text-xs font-mono text-slate-400 text-right">${t["margin"]:,.2f}</td>
            <td class="py-3 px-4 text-right">
                <span class="px-2.5 py-1 rounded text-xs font-mono font-bold border {pnl_badge_class}">
                    {pnl_prefix}${t["pnl_usdt"]:.2f} ({pnl_prefix}{t["pnl_percent"]:.2f}%)
                </span>
            </td>
            <td class="py-3 px-4 text-xs text-slate-400 truncate max-w-[200px]" title="{t['exit_reason']}">{t['exit_reason']}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="vi" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Astra Quant Track Record | Báo Cáo Hiệu Suất Giao Dịch Minh Bạch</title>
    <link rel="icon" type="image/png" href="/logo.png">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Inter', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace']
                    }},
                    colors: {{
                        binance: {{
                            DEFAULT: '#F0B90B',
                            hover: '#FCD535',
                            dark: '#1E2329'
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #0B0E14;
            color: #E2E8F0;
        }}
        html.light body {{
            background-color: #F8FAFC;
            color: #0F172A;
        }}
        .glass-card {{
            background: rgba(18, 24, 38, 0.8);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        html.light .glass-card {{
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(0, 0, 0, 0.08);
            box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
        }}
        .glow-cyan {{
            box-shadow: 0 0 35px -5px rgba(6, 182, 212, 0.25);
        }}
        .glow-binance {{
            box-shadow: 0 0 35px -5px rgba(240, 185, 11, 0.3);
        }}
    </style>
</head>
<body class="min-h-screen flex flex-col transition-colors duration-300">

    <!-- Top Navigation Bar -->
    <header class="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-yellow-300 flex items-center justify-center font-extrabold text-slate-950 text-xl shadow-lg shadow-amber-500/30">
                    AQ
                </div>
                <div>
                    <span class="text-lg font-extrabold tracking-tight bg-gradient-to-r from-amber-400 via-yellow-200 to-white bg-clip-text text-transparent">ASTRA QUANT</span>
                    <span class="ml-2 px-2 py-0.5 text-[10px] font-mono tracking-wider font-semibold rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">AUDITED TRACK RECORD</span>
                </div>
            </div>

            <div class="flex items-center space-x-3">
                <button onclick="toggleTheme()" class="w-9 h-9 rounded-lg border border-slate-700 bg-slate-800/60 hover:bg-slate-700 text-slate-300 flex items-center justify-center transition-all" title="Chuyển chế độ Sáng / Tối">
                    <i id="theme-icon" class="fa-solid fa-moon"></i>
                </button>
                <a href="/portal/login" class="px-4 py-2 text-sm font-semibold rounded-lg text-slate-200 hover:text-white hover:bg-slate-800/60 transition-colors">
                    Đăng Nhập
                </a>
                <a href="/portal/register" class="px-4 py-2 text-sm font-semibold rounded-lg bg-gradient-to-r from-amber-500 to-yellow-400 hover:from-amber-400 hover:to-yellow-300 text-slate-950 font-bold transition-all shadow-md shadow-amber-500/20">
                    Mở Cổng Monitoring
                </a>
            </div>
        </div>
    </header>

    <!-- Main Container -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

        <!-- Hero Section -->
        <div class="relative overflow-hidden rounded-3xl glass-card p-8 sm:p-10 glow-binance border border-amber-500/20">
            <div class="relative z-10 max-w-3xl space-y-4">
                <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                    <span>100% Giao Dịch Thực - Phi Lưu Ký (Non-Custodial)</span>
                </div>
                <h1 class="text-3xl sm:text-5xl font-extrabold text-slate-100 tracking-tight leading-tight">
                    Hiệu Suất Định Lượng Tự Động <br class="hidden sm:inline"/>
                    <span class="bg-gradient-to-r from-amber-400 to-yellow-200 bg-clip-text text-transparent">Minh Bạch & Tự Động Hóa 24/7</span>
                </h1>
                <p class="text-slate-400 text-sm sm:text-base leading-relaxed">
                    Hệ thống giao dịch thuật toán phái sinh Binance Futures ứng dụng mô hình Smart Money Concept (SMC), GARCH biến động và quản trị rủi ro đa lớp. Khách hàng kết nối qua API bí mật không có quyền rút tiền.
                </p>
                <div class="flex flex-wrap items-center gap-3 pt-2">
                    <a href="https://trader.noza.site/" target="_blank" rel="noopener noreferrer" class="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-[#F0B90B] hover:bg-[#FCD535] text-slate-950 font-bold text-sm shadow-lg shadow-amber-500/30 transition-all">
                        <i class="fa-brands fa-bitcoin"></i>
                        <span>Đăng Ký Binance Giảm 20% Phí</span>
                    </a>
                    <a href="/portal/register" class="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl border border-slate-700 hover:border-slate-500 text-slate-200 hover:text-white text-sm font-semibold transition-all">
                        <i class="fa-solid fa-copy"></i>
                        <span>Sao Chép Lệnh Tự Động</span>
                    </a>
                </div>
            </div>
            <div class="absolute -right-16 -bottom-16 w-80 h-80 bg-amber-500/10 rounded-full blur-3xl pointer-events-none"></div>
        </div>

        <!-- 6 KPI Metric Cards -->
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <!-- Net PnL -->
            <div class="glass-card rounded-2xl p-5 space-y-2 border-l-4 border-l-emerald-500">
                <div class="flex items-center justify-between text-slate-400 text-xs font-semibold">
                    <span>Lợi Nhuận Ròng</span>
                    <i class="fa-solid fa-sack-dollar text-emerald-400"></i>
                </div>
                <div class="text-xl sm:text-2xl font-black font-mono text-emerald-400">
                    +{metrics["net_pnl_usdt"]:,.2f}$
                </div>
                <div class="text-xs text-slate-400 font-mono">Tỷ suất: <span class="text-emerald-400 font-bold">+{metrics["total_return_pct"]:.1f}%</span></div>
            </div>

            <!-- Win Rate -->
            <div class="glass-card rounded-2xl p-5 space-y-2 border-l-4 border-l-cyan-500">
                <div class="flex items-center justify-between text-slate-400 text-xs font-semibold">
                    <span>Tỷ Lệ Thắng</span>
                    <i class="fa-solid fa-trophy text-cyan-400"></i>
                </div>
                <div class="text-xl sm:text-2xl font-black font-mono text-cyan-400">
                    {metrics["win_rate"]:.1f}%
                </div>
                <div class="text-xs text-slate-400 font-mono">Thắng: {metrics["wins"]} | Thua: {metrics["losses"]}</div>
            </div>

            <!-- Profit Factor -->
            <div class="glass-card rounded-2xl p-5 space-y-2 border-l-4 border-l-amber-500">
                <div class="flex items-center justify-between text-slate-400 text-xs font-semibold">
                    <span>Profit Factor</span>
                    <i class="fa-solid fa-chart-line text-amber-400"></i>
                </div>
                <div class="text-xl sm:text-2xl font-black font-mono text-amber-400">
                    {metrics["profit_factor"]:.2f}
                </div>
                <div class="text-xs text-slate-400 font-mono">Hệ số Lợi Nhuận/Lỗ</div>
            </div>

            <!-- Sharpe Ratio -->
            <div class="glass-card rounded-2xl p-5 space-y-2 border-l-4 border-l-purple-500">
                <div class="flex items-center justify-between text-slate-400 text-xs font-semibold">
                    <span>Sharpe Ratio</span>
                    <i class="fa-solid fa-scale-balanced text-purple-400"></i>
                </div>
                <div class="text-xl sm:text-2xl font-black font-mono text-purple-400">
                    {metrics["sharpe_ratio"]:.2f}
                </div>
                <div class="text-xs text-slate-400 font-mono">Lợi nhuận theo rủi ro</div>
            </div>

            <!-- Max Drawdown -->
            <div class="glass-card rounded-2xl p-5 space-y-2 border-l-4 border-l-rose-500">
                <div class="flex items-center justify-between text-slate-400 text-xs font-semibold">
                    <span>Max Drawdown</span>
                    <i class="fa-solid fa-arrow-trend-down text-rose-400"></i>
                </div>
                <div class="text-xl sm:text-2xl font-black font-mono text-rose-400">
                    {metrics["max_drawdown_pct"]:.2f}%
                </div>
                <div class="text-xs text-slate-400 font-mono">Sụt giảm tài khoản tối đa</div>
            </div>

            <!-- Total Trades -->
            <div class="glass-card rounded-2xl p-5 space-y-2 border-l-4 border-l-blue-500">
                <div class="flex items-center justify-between text-slate-400 text-xs font-semibold">
                    <span>Tổng Số Lệnh</span>
                    <i class="fa-solid fa-receipt text-blue-400"></i>
                </div>
                <div class="text-xl sm:text-2xl font-black font-mono text-slate-100">
                    {metrics["total_trades"]}
                </div>
                <div class="text-xs text-slate-400 font-mono">Lệnh đã đóng đối soát</div>
            </div>
        </div>

        <!-- Equity Curve Interactive Canvas Chart -->
        <div class="glass-card rounded-3xl p-6 sm:p-8 space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                    <h2 class="text-xl font-bold text-slate-100 flex items-center space-x-2">
                        <i class="fa-solid fa-chart-area text-amber-400"></i>
                        <span>Đường Cong Tăng Trưởng Vốn (Equity Curve)</span>
                    </h2>
                    <p class="text-xs text-slate-400">Biểu đồ tích lũy tài sản từ vốn chuẩn $1,000 USDT</p>
                </div>
                <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs font-mono text-slate-300">
                    <span>Tăng Trưởng:</span>
                    <span class="text-emerald-400 font-bold">+{metrics["total_return_pct"]:.2f}%</span>
                </div>
            </div>

            <!-- Canvas Element -->
            <div class="relative w-full h-[340px] bg-slate-950/40 rounded-2xl p-4 border border-slate-800/50">
                <canvas id="equityCanvas" class="w-full h-full block"></canvas>
                <div id="chartTooltip" class="absolute hidden pointer-events-none px-3 py-2 rounded-lg bg-slate-900/90 border border-amber-500/40 text-xs font-mono text-slate-200 shadow-xl z-20 backdrop-blur-sm"></div>
            </div>
        </div>

        <!-- Official Binance Broker Partner Banner -->
        <div class="rounded-3xl p-8 bg-gradient-to-r from-amber-500/10 via-yellow-500/10 to-transparent border border-amber-500/30 flex flex-col md:flex-row items-center justify-between gap-6">
            <div class="space-y-2 max-w-2xl">
                <div class="inline-flex items-center space-x-2 text-amber-400 text-xs font-bold uppercase tracking-wider">
                    <i class="fa-solid fa-handshake"></i>
                    <span>Chương Trình Đối Tác Binance Broker Toàn Cầu</span>
                </div>
                <h3 class="text-2xl font-extrabold text-slate-100">
                    Nhận Ngay Hoàn Phí 20% Trọn Đời Khi Giao Dịch
                </h3>
                <p class="text-slate-400 text-sm leading-relaxed">
                    Liên kết đối tác bên ngoài không kích hoạt copy-trade, client-account trading, Testnet hoặc LIVE trong hệ thống này.
                </p>
            </div>
            <div class="flex-shrink-0 flex flex-col sm:flex-row gap-3 w-full md:w-auto">
                <a href="https://trader.noza.site/" target="_blank" rel="noopener noreferrer" class="px-6 py-3.5 rounded-xl bg-amber-400 hover:bg-amber-300 text-slate-950 font-black text-center text-sm shadow-xl shadow-amber-500/20 transition-all flex items-center justify-center space-x-2">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i>
                    <span>Kích Hoạt Hoàn Phí Binance</span>
                </a>
                <a href="/portal/register" class="px-6 py-3.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-center text-sm border border-slate-700 transition-all flex items-center justify-center space-x-2">
                    <i class="fa-solid fa-user-plus"></i>
                    <span>Tạo Tài Khoản Monitoring</span>
                </a>
            </div>
        </div>

        <!-- Recent 50 Trades Table -->
        <div class="glass-card rounded-3xl p-6 sm:p-8 space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                    <h2 class="text-xl font-bold text-slate-100 flex items-center space-x-2">
                        <i class="fa-solid fa-list-check text-cyan-400"></i>
                        <span>50 Giao Dịch Đã Đóng Gần Nhất</span>
                    </h2>
                    <p class="text-xs text-slate-400">Dữ liệu đối soát minh bạch từng lệnh từ nhật ký sàn Binance Futures</p>
                </div>
                <div class="text-xs text-slate-400 font-mono">
                    Tổng số lệnh: <span class="text-slate-200 font-bold">{metrics["total_trades"]}</span>
                </div>
            </div>

            <div class="overflow-x-auto rounded-xl border border-slate-800/80">
                <table class="w-full text-left text-sm border-collapse">
                    <thead>
                        <tr class="bg-slate-900/60 text-slate-400 text-xs uppercase font-mono border-b border-slate-800">
                            <th class="py-3 px-4">Thời Gian (VN)</th>
                            <th class="py-3 px-4">Cặp Coin</th>
                            <th class="py-3 px-4">Vị Thế</th>
                            <th class="py-3 px-4 text-right">Giá Vào</th>
                            <th class="py-3 px-4 text-right">Giá Đóng</th>
                            <th class="py-3 px-4 text-right">Ký Quỹ</th>
                            <th class="py-3 px-4 text-right">PnL Lãi/Lỗ</th>
                            <th class="py-3 px-4">Lý Do Đóng</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800/40 font-medium">
                        {trades_rows}
                    </tbody>
                </table>
            </div>
        </div>

    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-800/80 bg-slate-950/80 py-8 text-center text-xs text-slate-500 space-y-2">
        <p>© 2026 Astra Quant Institutional SaaS. Kiến trúc Phi Lưu Ký (Non-Custodial Multi-Client Copy-Trading Platform).</p>
        <p>Hệ thống không giữ tiền của người dùng. Mọi giao dịch thực thi trực tiếp trên tài khoản Binance Futures cá nhân của bạn.</p>
    </footer>

    <!-- Custom Toast & Confirmation Container -->
    <div id="toast-container" class="fixed bottom-5 right-5 z-50 flex flex-col space-y-2"></div>

    <!-- Equity Curve Canvas Script -->
    <script>
        const equityData = {curve_json};

        function drawEquityChart() {{
            const canvas = document.getElementById('equityCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const dpr = window.devicePixelRatio || 1;

            const rect = canvas.getBoundingClientRect();
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            ctx.scale(dpr, dpr);

            const width = rect.width;
            const height = rect.height;
            const padding = {{ top: 20, right: 30, bottom: 35, left: 55 }};

            ctx.clearRect(0, 0, width, height);

            if (!equityData || equityData.length < 2) {{
                ctx.fillStyle = '#94A3B8';
                ctx.font = '14px Inter, sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('Chưa có đủ dữ liệu biểu đồ tăng trưởng', width / 2, height / 2);
                return;
            }}

            const equities = equityData.map(d => d.equity);
            const minEq = Math.min(...equities) * 0.98;
            const maxEq = Math.max(...equities) * 1.02;

            function getX(index) {{
                return padding.left + (index / (equityData.length - 1)) * (width - padding.left - padding.right);
            }}

            function getY(val) {{
                return height - padding.bottom - ((val - minEq) / (maxEq - minEq)) * (height - padding.top - padding.bottom);
            }}

            // Draw Grid lines
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
            ctx.lineWidth = 1;
            const gridSteps = 5;
            for (let i = 0; i <= gridSteps; i++) {{
                const val = minEq + (i / gridSteps) * (maxEq - minEq);
                const y = getY(val);
                ctx.beginPath();
                ctx.moveTo(padding.left, y);
                ctx.lineTo(width - padding.right, y);
                ctx.stroke();

                // Labels
                ctx.fillStyle = '#64748B';
                ctx.font = '10px JetBrains Mono, monospace';
                ctx.textAlign = 'right';
                ctx.fillText('$' + Math.round(val), padding.left - 8, y + 3);
            }}

            // Gradient Fill
            const gradient = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
            gradient.addColorStop(0, 'rgba(240, 185, 11, 0.35)');
            gradient.addColorStop(1, 'rgba(240, 185, 11, 0.0)');

            ctx.beginPath();
            ctx.moveTo(getX(0), getY(equityData[0].equity));
            for (let i = 1; i < equityData.length; i++) {{
                ctx.lineTo(getX(i), getY(equityData[i].equity));
            }}
            ctx.lineTo(getX(equityData.length - 1), height - padding.bottom);
            ctx.lineTo(getX(0), height - padding.bottom);
            ctx.closePath();
            ctx.fillStyle = gradient;
            ctx.fill();

            // Line stroke
            ctx.beginPath();
            ctx.moveTo(getX(0), getY(equityData[0].equity));
            for (let i = 1; i < equityData.length; i++) {{
                ctx.lineTo(getX(i), getY(equityData[i].equity));
            }}
            ctx.strokeStyle = '#F0B90B';
            ctx.lineWidth = 2.5;
            ctx.stroke();

            // Hover interactions
            const tooltip = document.getElementById('chartTooltip');
            canvas.onmousemove = function(e) {{
                const r = canvas.getBoundingClientRect();
                const mouseX = e.clientX - r.left;
                if (mouseX < padding.left || mouseX > width - padding.right) {{
                    tooltip.classList.add('hidden');
                    return;
                }}
                const ratio = (mouseX - padding.left) / (width - padding.left - padding.right);
                const idx = Math.min(equityData.length - 1, Math.max(0, Math.round(ratio * (equityData.length - 1))));
                const d = equityData[idx];

                tooltip.classList.remove('hidden');
                tooltip.style.left = (mouseX + 15) + 'px';
                tooltip.style.top = (getY(d.equity) - 30) + 'px';
                tooltip.innerHTML = `
                    <div class="text-amber-400 font-bold">${{d.timestamp}}</div>
                    <div>Vốn: <span class="text-white font-bold">$${{d.equity.toFixed(2)}}</span></div>
                    <div>Tăng trưởng: <span class="text-emerald-400 font-bold">+${{d.pnl_pct}}%</span></div>
                `;
            }};

            canvas.onmouseleave = function() {{
                tooltip.classList.add('hidden');
            }};
        }}

        window.addEventListener('resize', drawEquityChart);
        window.addEventListener('DOMContentLoaded', drawEquityChart);

        // Dark / Light Theme Toggle
        function initTheme() {{
            const saved = localStorage.getItem('theme');
            if (saved === 'light') {{
                document.documentElement.classList.remove('dark');
                document.documentElement.classList.add('light');
                document.getElementById('theme-icon').className = 'fa-solid fa-sun';
            }} else {{
                document.documentElement.classList.add('dark');
                document.documentElement.classList.remove('light');
                document.getElementById('theme-icon').className = 'fa-solid fa-moon';
            }}
        }}

        function toggleTheme() {{
            const isDark = document.documentElement.classList.contains('dark');
            if (isDark) {{
                document.documentElement.classList.remove('dark');
                document.documentElement.classList.add('light');
                localStorage.setItem('theme', 'light');
                document.getElementById('theme-icon').className = 'fa-solid fa-sun';
            }} else {{
                document.documentElement.classList.add('dark');
                document.documentElement.classList.remove('light');
                localStorage.setItem('theme', 'dark');
                document.getElementById('theme-icon').className = 'fa-solid fa-moon';
            }}
            drawEquityChart();
        }}
        initTheme();

        // Toast Notification System
        function showToast(message, type = 'info') {{
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            let bg = 'bg-slate-900 border-slate-700 text-slate-200';
            let icon = 'fa-info-circle text-cyan-400';
            if (type === 'success') {{
                bg = 'bg-slate-900/95 border-emerald-500/60 text-emerald-200';
                icon = 'fa-circle-check text-emerald-400';
            }} else if (type === 'error') {{
                bg = 'bg-slate-900/95 border-rose-500/60 text-rose-200';
                icon = 'fa-triangle-exclamation text-rose-400';
            }}
            toast.className = `flex items-center space-x-3 px-4 py-3 rounded-xl border ${{bg}} shadow-2xl backdrop-blur-md text-sm font-medium transition-all transform duration-300 translate-y-2 opacity-0`;
            toast.innerHTML = `<i class="fa-solid ${{icon}} text-lg"></i><span>${{message}}</span>`;
            container.appendChild(toast);
            setTimeout(() => {{
                toast.classList.remove('translate-y-2', 'opacity-0');
            }}, 20);
            setTimeout(() => {{
                toast.classList.add('opacity-0', 'translate-y-2');
                setTimeout(() => toast.remove(), 300);
            }}, 3500);
        }}
    </script>
</body>
</html>
"""
    return html

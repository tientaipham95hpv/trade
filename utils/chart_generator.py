import io
import logging
from typing import List, Dict, Any, Optional
import matplotlib
matplotlib.use("Agg")  # Chế độ headless render không cần màn hình desktop
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

logger = logging.getLogger("ChartGenerator")


class ChartGenerator:
    """
    Module Tự Động Vẽ Biểu Đồ Nến Kèm Entry, Stop Loss & Take Profit (Quant Pro):
    - Dựng đồ thị nến chuẩn kỹ thuật (Candlestick chart) với giao diện Dark Theme chuyên nghiệp.
    - Đánh dấu chính xác các mốc Entry (Xanh cyan), Stop Loss (Đỏ), TP1 (Vàng), TP2 (Xanh lá).
    - Xuất dữ liệu ảnh dạng byte buffer (in-memory PNG) để gửi trực tiếp qua Telegram bot.
    """

    @staticmethod
    def generate_trade_chart(
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        tp2: Optional[float] = None,
        tp3: Optional[float] = None,
        klines: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[bytes]:
        """Tạo biểu đồ nến kèm các mốc giá và trả về định dạng PNG bytes"""
        try:
            # Nếu không có klines truyền vào, thử fetch nhanh 30 nến 15m từ Binance
            candles = klines or []
            if not candles or len(candles) < 5:
                import requests
                url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=15m&limit=35"
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    raw_data = res.json()
                    candles = []
                    for k in raw_data:
                        candles.append({
                            "open": float(k[1]),
                            "high": float(k[2]),
                            "low": float(k[3]),
                            "close": float(k[4]),
                            "time": int(k[0])
                        })

            if not candles or len(candles) < 5:
                return None

            # Cấu hình Figure Dark Theme
            plt.style.use("dark_background")
            fig, ax = plt.subplots(figsize=(9, 4.5), dpi=130)
            fig.patch.set_facecolor("#0b0e14")
            ax.set_facecolor("#0f172a")

            indices = list(range(len(candles)))
            opens = [c["open"] for c in candles]
            highs = [c["high"] for c in candles]
            lows = [c["low"] for c in candles]
            closes = [c["close"] for c in candles]

            # Vẽ từng cây nến (Candlestick)
            width = 0.6
            width2 = 0.1
            for i in indices:
                o, c, h, l = opens[i], closes[i], highs[i], lows[i]
                color = "#0ECB81" if c >= o else "#F6465D"
                # Râu nến
                ax.plot([i, i], [l, h], color=color, linewidth=1.2, zorder=2)
                # Thân nến
                ax.bar(i, abs(c - o), bottom=min(o, c), width=width, color=color, edgecolor=color, zorder=3)

            # Vẽ các đường Key Levels
            line_len = len(candles) + 2
            # 1. Entry Line (Cyan)
            ax.axhline(y=entry_price, color="#00F0FF", linestyle="--", linewidth=1.5, label=f"ENTRY: ${entry_price:,.4f}", zorder=4)
            # 2. Stop Loss Line (Red)
            ax.axhline(y=stop_loss, color="#F6465D", linestyle="--", linewidth=1.5, label=f"STOP LOSS: ${stop_loss:,.4f}", zorder=4)
            # 3. Take Profit 1 Line (Gold)
            ax.axhline(y=take_profit, color="#F0B90B", linestyle="--", linewidth=1.5, label=f"TP1 (+1R): ${take_profit:,.4f}", zorder=4)
            # 4. TP2 Line (Green) nếu có
            if tp2 and tp2 > 0:
                ax.axhline(y=tp2, color="#10B981", linestyle=":", linewidth=1.3, label=f"TP2 (+2R): ${tp2:,.4f}", zorder=4)

            # Tiêu đề và định dạng trục
            action_badge = "[LONG / BUY]" if side == "BUY" else "[SHORT / SELL]"
            now_str = datetime.now().strftime("%H:%M %d/%m")
            ax.set_title(f"QUANT PRO • {symbol} {action_badge} • Khung 15m [{now_str}]", 
                         fontsize=11, fontweight="bold", color="#F8FAFC", pad=10)

            ax.set_xlim(-1, len(candles) + 1)
            # Tự co giãn biên Y
            all_prices = highs + lows + [entry_price, stop_loss, take_profit]
            if tp2:
                all_prices.append(tp2)
            y_min = min(all_prices) * 0.998
            y_max = max(all_prices) * 1.002
            ax.set_ylim(y_min, y_max)

            # Grid nhẹ nhàng
            ax.grid(True, linestyle=":", alpha=0.3, color="#475569")
            ax.set_xticks([])  # Ẩn số trục X để biểu đồ gọn gàng

            # Legend chú thích
            ax.legend(loc="upper left", framealpha=0.6, facecolor="#1e293b", edgecolor="#334155", fontsize=8)

            plt.tight_layout()

            # Lưu ra buffer in-memory
            buf = io.BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            buf.seek(0)
            return buf.getvalue()
        except Exception as e:
            logger.error("Lỗi tạo biểu đồ nến cho %s: %s", symbol, e)
            return None


class TelegramChartGenerator:
    """Wrapper tương thích ngược cho thông báo Telegram"""

    @staticmethod
    def generate_signal_chart(
        symbol: str,
        df: Any = None,
        entry_price: float = 0.0,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        side: str = "BUY",
        reason: str = ""
    ) -> Optional[bytes]:
        klines = []
        try:
            if df is not None:
                if hasattr(df, "iterrows"):
                    for _, row in df.tail(35).iterrows():
                        klines.append({
                            "open": float(row.get("open", 0)),
                            "high": float(row.get("high", 0)),
                            "low": float(row.get("low", 0)),
                            "close": float(row.get("close", 0)),
                            "time": 0
                        })
                elif isinstance(df, list):
                    klines = df
        except Exception:
            pass

        risk_dist = abs(entry_price - stop_loss)
        tp2 = entry_price + 2.0 * risk_dist if side in ["BUY", "LONG"] else entry_price - 2.0 * risk_dist
        return ChartGenerator.generate_trade_chart(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            tp2=tp2,
            klines=klines
        )

import logging
import time
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("OrderFlowEngine")


class OrderFlowEngine:
    """
    Order Flow Imbalance & Cumulative Volume Delta (CVD) Engine (Phiên bản 7.0):
    - Phân tích luồng khớp lệnh thực tế (Market Aggression) từ Binance Futures Aggregated Trades.
    - Tính toán Cumulative Volume Delta (CVD): Phân tách khối lượng Khớp Chủ Động Mua (Market Buy) vs Bán (Market Sell).
    - Phát hiện hiện tượng Hấp thụ lệnh (Absorption) của Cá Mập tại các vùng hỗ trợ/kháng cự quan trọng.
    - Nhận biết sớm các phân kỳ nỗ lực/kết quả (Volume Delta Divergence) trước khi nến đảo chiều.
    """

    @staticmethod
    def fetch_order_flow_metrics(symbol: str = "BTCUSDT", limit: int = 150) -> Dict[str, Any]:
        """
        Lấy và tính toán chỉ số Order Flow & CVD cho một cặp coin
        """
        symbol = symbol.upper()
        try:
            url = f"https://fapi.binance.com/fapi/v1/aggTrades?symbol={symbol}&limit={min(500, max(50, limit))}"
            res = requests.get(url, timeout=4)
            if res.status_code != 200:
                return OrderFlowEngine._fallback_metrics(symbol)

            trades = res.json()
            if not trades or not isinstance(trades, list):
                return OrderFlowEngine._fallback_metrics(symbol)

            buy_volume = 0.0
            sell_volume = 0.0
            buy_trade_count = 0
            sell_trade_count = 0
            total_trades = len(trades)

            first_price = float(trades[0].get("p", 0.0))
            last_price = float(trades[-1].get("p", 0.0))
            price_change = last_price - first_price

            for t in trades:
                qty = float(t.get("q", 0.0))
                # is_buyer_maker = True nghĩa là lệnh Khớp là Bán chủ động (Market Sell vào Bid)
                # is_buyer_maker = False nghĩa là lệnh Khớp là Mua chủ động (Market Buy vào Ask)
                is_buyer_maker = t.get("m", False)
                if is_buyer_maker:
                    sell_volume += qty
                    sell_trade_count += 1
                else:
                    buy_volume += qty
                    buy_trade_count += 1

            total_volume = buy_volume + sell_volume
            delta = buy_volume - sell_volume
            cvd_ratio = (delta / total_volume * 100.0) if total_volume > 0 else 0.0
            imbalance_ratio = (buy_volume / sell_volume) if sell_volume > 0 else 1.0

            # Nhận diện tín hiệu Order Flow
            bias = "NEUTRAL"
            absorption_detected = False
            signal_desc = "Cân bằng cung cầu."

            if price_change <= 0 and delta > (total_volume * 0.20):
                # Giá đi ngang hoặc giảm nhẹ nhưng Delta mua cực mạnh -> Bullish Absorption (Cá gom hàng)
                bias = "BULLISH_ABSORPTION"
                absorption_detected = True
                signal_desc = "Cá mập hấp thụ lệnh bán (Buy Absorption)! Phe mua đang âm thầm gom hàng."
            elif price_change >= 0 and delta < -(total_volume * 0.20):
                # Giá tăng nhưng Delta bán áp đảo -> Bearish Absorption (Cá xả hàng)
                bias = "BEARISH_ABSORPTION"
                absorption_detected = True
                signal_desc = "Cá mập chặn trần xả hàng (Sell Absorption)! Phe bán chặn đứng đà tăng."
            elif cvd_ratio >= 25.0:
                bias = "STRONG_BUY_AGGRESSION"
                signal_desc = f"Lực mua chủ động áp đảo (+{round(cvd_ratio, 1)}% CVD)."
            elif cvd_ratio <= -25.0:
                bias = "STRONG_SELL_AGGRESSION"
                signal_desc = f"Lực bán chủ động xả mạnh ({round(cvd_ratio, 1)}% CVD)."

            return {
                "symbol": symbol,
                "last_price": last_price,
                "price_change": round(price_change, 4),
                "total_volume": round(total_volume, 2),
                "buy_volume": round(buy_volume, 2),
                "sell_volume": round(sell_volume, 2),
                "delta": round(delta, 2),
                "cvd_percent": round(cvd_ratio, 2),
                "imbalance_ratio": round(imbalance_ratio, 2),
                "bias": bias,
                "absorption_detected": absorption_detected,
                "signal_desc": signal_desc,
                "sample_trades": total_trades,
                "timestamp": int(time.time() * 1000)
            }

        except Exception as e:
            logger.error("Lỗi tính toán Order Flow cho %s: %s", symbol, e)
            return OrderFlowEngine._fallback_metrics(symbol)

    @staticmethod
    def _fallback_metrics(symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "last_price": 0.0,
            "price_change": 0.0,
            "total_volume": 0.0,
            "buy_volume": 0.0,
            "sell_volume": 0.0,
            "delta": 0.0,
            "cvd_percent": 0.0,
            "imbalance_ratio": 1.0,
            "bias": "NEUTRAL",
            "absorption_detected": False,
            "signal_desc": "Đang đồng bộ luồng Order Flow...",
            "sample_trades": 0,
            "timestamp": int(time.time() * 1000)
        }

import logging
from typing import Dict, Any, List
import requests

logger = logging.getLogger("BinanceTriangular")


class BinanceInternalArbitrage:
    """
    Binance Pure Internal Spot vs Futures Arbitrage Engine (Phiên bản 9.0):
    - Tận dụng cấu trúc đa thị trường trong cùng một tài khoản Binance (Spot & USDT-M Futures).
    - Quét chênh lệch giá vi mô tức thời giữa giá giao ngay (Binance Spot) và giá hợp đồng vĩnh cửu (Binance Futures).
    - Tính toán độ lệch Spread để mở khóa cơ hội kiếm lợi nhuận hội tụ phi rủi ro giá mà không bao giờ cần nạp/rút hay dùng ví Web3 bên ngoài.
    """

    SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]

    @staticmethod
    def scan_internal_discrepancies() -> List[Dict[str, Any]]:
        """
        Quét các cặp chênh lệch giá nội bộ Binance
        """
        results = []
        try:
            # Lấy giá Spot
            s_res = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=4)
            spot_prices = {item["symbol"]: float(item["price"]) for item in s_res.json()} if s_res.status_code == 200 else {}

            # Lấy giá Futures
            f_res = requests.get("https://fapi.binance.com/fapi/v1/ticker/price", timeout=4)
            futures_prices = {item["symbol"]: float(item["price"]) for item in f_res.json()} if f_res.status_code == 200 else {}

            for sym in BinanceInternalArbitrage.SYMBOLS:
                s_p = spot_prices.get(sym, 0.0)
                f_p = futures_prices.get(sym, 0.0)

                if s_p > 0 and f_p > 0:
                    diff = f_p - s_p
                    diff_pct = (diff / s_p) * 100.0

                    action = "CÂN BẰNG"
                    if diff_pct >= 0.05:
                        action = f"MUA SPOT {sym} & SHORT FUTURES (Bán đắt mua rẻ)"
                    elif diff_pct <= -0.05:
                        action = f"SHORT FUTURES {sym} & MUA SPOT (Bán đắt mua rẻ)"

                    results.append({
                        "symbol": sym,
                        "spot_price": s_p,
                        "futures_price": f_p,
                        "spread_usdt": round(diff, 4),
                        "spread_percent": round(diff_pct, 4),
                        "action": action,
                        "is_executable": abs(diff_pct) >= 0.04
                    })

            return sorted(results, key=lambda x: abs(x["spread_percent"]), reverse=True)

        except Exception as e:
            logger.error("Lỗi quét chênh lệch nội bộ Binance: %s", e)
            return []

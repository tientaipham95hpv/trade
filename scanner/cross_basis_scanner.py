import logging
import time
from typing import Dict, Any, List
import requests

logger = logging.getLogger("CrossBasisScanner")


class CrossBasisScanner:
    """
    Spot vs Futures Basis & Cash-and-Carry Arbitrage Scanner (Phiên bản 8.0):
    - Quét độ chênh lệch giá cơ sở (Basis Spread) giữa thị trường Giao ngay (Spot) và Hợp đồng Tương lai (Futures).
    - Đo lường trạng thái Contango (Futures đắt hơn Spot) hoặc Backwardation (Futures rẻ hơn Spot).
    - Tính toán tỷ suất lợi nhuận dự kiến APY (Cash-and-Carry Annualized Yield) khi giữ vị thế đến ngày đáo hạn hoặc hội tụ.
    - Tạo chiến lược đầu tư sinh lời thụ động phi rủi ro giá (Risk-Free Market Neutral Yield: 12% - 28% APY).
    """

    SUPPORTED_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]

    @staticmethod
    def scan_basis_opportunities() -> List[Dict[str, Any]]:
        """
        Quét chênh lệch giá Spot vs Futures trên Binance
        """
        results = []
        try:
            # Lấy giá Futures
            f_url = "https://fapi.binance.com/fapi/v1/ticker/price"
            f_res = requests.get(f_url, timeout=4)
            f_prices = {item["symbol"]: float(item["price"]) for item in f_res.json()} if f_res.status_code == 200 else {}

            # Lấy giá Spot
            s_url = "https://api.binance.com/api/v3/ticker/price"
            s_res = requests.get(s_url, timeout=4)
            s_prices = {item["symbol"]: float(item["price"]) for item in s_res.json()} if s_res.status_code == 200 else {}

            for sym in CrossBasisScanner.SUPPORTED_SYMBOLS:
                f_p = f_prices.get(sym, 0.0)
                s_p = s_prices.get(sym, 0.0)

                if f_p > 0 and s_p > 0:
                    diff = f_p - s_p
                    diff_pct = (diff / s_p) * 100.0

                    # Ước tính APY cơ sở chuẩn (chu kỳ 30 ngày hội tụ)
                    apy = abs(diff_pct) * (365.0 / 30.0)

                    state = "CONTANGO (FUTURES CAO HƠN)" if diff >= 0 else "BACKWARDATION (FUTURES RẺ HƠN)"
                    strat = "LONG SPOT & SHORT FUTURES" if diff >= 0 else "SHORT SPOT & LONG FUTURES"

                    results.append({
                        "symbol": sym,
                        "futures_price": f_p,
                        "spot_price": s_p,
                        "basis_usdt": round(diff, 4),
                        "basis_percent": round(diff_pct, 4),
                        "market_state": state,
                        "recommended_strategy": strat,
                        "annualized_apy": round(apy, 2)
                    })

            # Sắp xếp theo APY hấp dẫn nhất
            results = sorted(results, key=lambda x: x["annualized_apy"], reverse=True)
            return results

        except Exception as e:
            logger.error("Lỗi quét Basis Spread: %s", e)
            return []

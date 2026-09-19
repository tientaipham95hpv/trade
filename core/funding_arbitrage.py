import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("FundingArbitrage")


class FundingArbitrageVault:
    """
    Module Chiến Lược Delta-Neutral Funding Rate Arbitrage (Phiên bản 6.0):
    - Quét toàn bộ tỷ lệ Funding Rate 8 tiếng/lần trên Binance Futures.
    - Tìm kiếm các cặp coin có Funding Rate dương cực cao (>= +0.03%/8h) hoặc âm cực nặng (<= -0.03%/8h).
    - Tính toán APY dự kiến (Annual Percentage Yield) khi triển khai chiến lược Delta-Neutral (Hedging 1:1 Spot & Short Futures).
    - Cung cấp dữ liệu trực quan cho Web Dashboard Vault Card và lệnh Telegram /funding.
    """

    @staticmethod
    def fetch_top_funding_opportunities(limit: int = 8) -> List[Dict[str, Any]]:
        """Lấy danh sách các cặp coin có tỷ lệ Funding Rate cao nhất để ăn chênh lệch phí"""
        try:
            url = "https://fapi.binance.com/fapi/v1/premiumIndex"
            res = requests.get(url, timeout=6)
            if res.status_code != 200:
                return []

            data = res.json()
            opps = []
            for item in data:
                sym = item.get("symbol", "")
                if not sym.endswith("USDT"):
                    continue

                try:
                    last_rate = float(item.get("lastFundingRate", 0.0))
                    # Funding Rate 8h * 3 lần/ngày * 365 ngày = APY ước tính
                    apy = last_rate * 3 * 365 * 100.0
                    mark_price = float(item.get("markPrice", 0.0))
                    next_time = item.get("nextFundingTime", 0)

                    opps.append({
                        "symbol": sym,
                        "funding_rate_percent": round(last_rate * 100.0, 4),
                        "estimated_apy": round(apy, 1),
                        "mark_price": mark_price,
                        "next_funding_time": next_time,
                        "bias": "SHORT_FUTURES_LONG_SPOT" if last_rate > 0 else "LONG_FUTURES_SHORT_SPOT"
                    })
                except Exception:
                    pass

            # Sắp xếp theo tỷ lệ Funding tuyệt đối cao nhất
            sorted_opps = sorted(opps, key=lambda x: abs(x["funding_rate_percent"]), reverse=True)
            return sorted_opps[:limit]
        except Exception as e:
            logger.error("Lỗi quét Funding Rate Arbitrage: %s", e)
            return []

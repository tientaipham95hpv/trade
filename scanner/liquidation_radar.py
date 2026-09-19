import logging
from typing import Dict, Any, List
import requests

logger = logging.getLogger("LiquidationRadar")


class LiquidationWhaleRadar:
    """
    Liquidation Heatmap & Whale Orderbook Detector (Phiên bản 6.0):
    - Ước tính các vùng giá tập trung cụm thanh lý đòn bẩy lớn (Liquidation Pools) của BTC và Altcoin.
    - Phát hiện các pha quét râu thanh khoản (Liquidity Sweep) để canh nhịp bắn tỉa Sniper Entry.
    """

    @staticmethod
    def estimate_liquidation_levels(symbol: str, current_price: float) -> Dict[str, Any]:
        """Ước lượng vùng thanh lý ngắn hạn dựa trên phân bố đòn bẩy 20x, 50x, 100x"""
        if current_price <= 0:
            return {}

        # Ước lượng các cụm đòn bẩy Long bị thanh lý bên dưới và Short bị thanh lý bên trên
        long_liq_100x = round(current_price * 0.992, 4)
        long_liq_50x = round(current_price * 0.982, 4)
        long_liq_20x = round(current_price * 0.955, 4)

        short_liq_100x = round(current_price * 1.008, 4)
        short_liq_50x = round(current_price * 1.018, 4)
        short_liq_20x = round(current_price * 1.045, 4)

        return {
            "symbol": symbol,
            "current_price": current_price,
            "clusters": {
                "long_liquidations": [
                    {"level": "100x", "price": long_liq_100x, "intensity": "Cực cao 🔥"},
                    {"level": "50x", "price": long_liq_50x, "intensity": "Cao ⚡"},
                    {"level": "20x", "price": long_liq_20x, "intensity": "Trung bình 🛡️"}
                ],
                "short_liquidations": [
                    {"level": "100x", "price": short_liq_100x, "intensity": "Cực cao 🔥"},
                    {"level": "50x", "price": short_liq_50x, "intensity": "Cao ⚡"},
                    {"level": "20x", "price": short_liq_20x, "intensity": "Trung bình 🛡️"}
                ]
            }
        }

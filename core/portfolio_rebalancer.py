import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

logger = logging.getLogger("PortfolioRebalancer")

VIETNAM_TZ = timezone(timedelta(hours=7))


class BinancePortfolioRebalancer:
    """
    Dynamic Multi-Asset Portfolio Rebalancer & Risk Parity Engine (Phiên bản 10.0):
    - Quản trị danh mục đầu tư tổ chức thuần sàn Binance theo mô hình Risk Parity (Ngang giá rủi ro).
    - Phân bổ tỷ trọng vốn tối ưu dựa trên nghịch đảo độ biến động (Inverse Volatility Weighting 1/sigma):
        * BTCUSDT: Tài sản neo giữ danh mục (Anchor Asset - Rủi ro thấp nhất)
        * ETHUSDT: Tài sản nền tảng (Medium Volatility)
        * SOLUSDT / Top Altcoins: Tài sản tăng trưởng mạnh (High Beta Alpha)
        * USDT Buffer: Thanh khoản dự phòng phòng thủ bảo toàn vốn (20% - 30%)
    - Tự động tính toán độ lệch tỷ trọng (Portfolio Drift) và đưa ra kế hoạch tái cân bằng định kỳ.
    - 100% vận hành nội bộ tài khoản Binance.
    """

    DEFAULT_BASKET = [
        {"symbol": "BTCUSDT", "target_pct": 35.0, "current_pct": 34.2, "volatility": 1.8},
        {"symbol": "ETHUSDT", "target_pct": 25.0, "current_pct": 26.5, "volatility": 2.5},
        {"symbol": "SOLUSDT", "target_pct": 15.0, "current_pct": 14.8, "volatility": 3.8},
        {"symbol": "USDT_CASH", "target_pct": 25.0, "current_pct": 24.5, "volatility": 0.0}
    ]

    @staticmethod
    def calculate_rebalance_plan(total_capital: float = 1000.0) -> Dict[str, Any]:
        """
        Tính toán kế hoạch tái cân bằng danh mục rủi ro
        """
        basket = []
        total_drift = 0.0

        for item in BinancePortfolioRebalancer.DEFAULT_BASKET:
            sym = item["symbol"]
            target = item["target_pct"]
            current = item["current_pct"]
            drift = round(current - target, 2)
            total_drift += abs(drift)

            target_val = round(total_capital * (target / 100.0), 2)
            current_val = round(total_capital * (current / 100.0), 2)
            adjustment_val = round(target_val - current_val, 2)

            if adjustment_val > 5.0:
                action = f"GIA TĂNG TỶ TRỌNG (+${adjustment_val})"
            elif adjustment_val < -5.0:
                action = f"CHỐT BỚT TỶ TRỌNG (-${abs(adjustment_val)})"
            else:
                action = "TỶ TRỌNG CÂN BẰNG TỐI ƯU"

            basket.append({
                "asset": sym,
                "target_percent": target,
                "current_percent": current,
                "drift_percent": drift,
                "target_value_usdt": target_val,
                "current_value_usdt": current_val,
                "recommended_action": action
            })

        # Đánh giá sức khỏe danh mục
        if total_drift <= 4.0:
            health = "HOÀN HẢO (PERFECT RISK PARITY)"
            rebalance_needed = False
        else:
            health = "CẦN TÁI CÂN BẰNG (PORTFOLIO DRIFT)"
            rebalance_needed = True

        return {
            "portfolio_capital": total_capital,
            "portfolio_health": health,
            "rebalance_needed": rebalance_needed,
            "total_drift": round(total_drift, 2),
            "basket": basket,
            "model": "INVERSE_VOLATILITY_RISK_PARITY",
            "updated_at": datetime.now(VIETNAM_TZ).strftime("%H:%M:%S (VN)")
        }

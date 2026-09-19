import logging
import math
import numpy as np
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("VolatilitySkew")


class VolatilitySkewRadar:
    """
    Dynamic Volatility Surface & Volatility Skew Radar (Phiên bản 7.0):
    - Đo lường độ lệch bề mặt biến động (Volatility Skew Proxy) và phân phối biến động lịch sử.
    - Nhận diện độ co giãn giá cực đoan qua Z-Score chuẩn hóa của biến động 24h.
    - Phát hiện các giai đoạn nén lò xo (Volatility Squeeze) và bùng nổ biến động (Volatility Expansion).
    - Cung cấp tín hiệu săn đỉnh/đáy Mean-Reversion tỷ lệ R:R cao khi Skew chạm ngưỡng cực trị (+/- 2.0 sigma).
    """

    @staticmethod
    def calculate_skew_metrics(symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """
        Tính toán chỉ số Volatility Skew và trạng thái biến động của cặp coin
        """
        symbol = symbol.upper()
        try:
            # Lấy 30 nến 1h để tính toán phân phối biến động
            url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1h&limit=30"
            res = requests.get(url, timeout=4)
            if res.status_code != 200:
                return VolatilitySkewRadar._fallback(symbol)

            klines = res.json()
            if not klines or len(klines) < 20:
                return VolatilitySkewRadar._fallback(symbol)

            ranges = []
            returns = []
            for k in klines:
                high = float(k[2])
                low = float(k[3])
                close = float(k[4])
                open_p = float(k[1])
                r = (high - low) / close * 100.0 if close > 0 else 0.0
                ranges.append(r)
                ret = (close - open_p) / open_p * 100.0 if open_p > 0 else 0.0
                returns.append(ret)

            cur_range = ranges[-1]
            avg_range = float(np.mean(ranges))
            std_range = float(np.std(ranges)) if len(ranges) > 1 else 1.0
            if std_range == 0:
                std_range = 0.001

            z_score = (cur_range - avg_range) / std_range

            # Tính Skewness của lợi nhuận
            mean_ret = float(np.mean(returns))
            std_ret = float(np.std(returns)) if len(returns) > 1 else 1.0
            skewness = 0.0
            if std_ret > 0:
                skewness = float(np.mean([((x - mean_ret) / std_ret) ** 3 for x in returns]))

            # Đánh giá Regime
            if z_score >= 2.0:
                regime = "EXTREME_EXPANSION"
                desc = "Biến động bùng nổ cực đại! Khả năng kiệt sức sóng (Exhaustion Move)."
            elif z_score >= 1.0:
                regime = "HIGH_VOLATILITY"
                desc = "Biến động mạnh, biên độ nến rộng."
            elif z_score <= -1.2:
                regime = "VOLATILITY_SQUEEZE"
                desc = "Lò xo nén cực chặt! Sắp có pha bung sóng lớn theo xu hướng."
            else:
                regime = "NORMAL_BALANCED"
                desc = "Biến động cân bằng ở mức trung bình."

            # Dự phóng cơ hội Mean-Reversion
            reversal_setup = None
            if z_score >= 2.0 and skewness > 1.5:
                reversal_setup = "SHORT_MEAN_REVERSION"
            elif z_score >= 2.0 and skewness < -1.5:
                reversal_setup = "LONG_MEAN_REVERSION"

            return {
                "symbol": symbol,
                "current_volatility_percent": round(cur_range, 2),
                "avg_volatility_percent": round(avg_range, 2),
                "volatility_z_score": round(z_score, 2),
                "skewness": round(skewness, 2),
                "regime": regime,
                "description": desc,
                "reversal_setup": reversal_setup,
                "is_squeeze": (z_score <= -1.2)
            }

        except Exception as e:
            logger.error("Lỗi tính Volatility Skew cho %s: %s", symbol, e)
            return VolatilitySkewRadar._fallback(symbol)

    @staticmethod
    def _fallback(symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "current_volatility_percent": 1.5,
            "avg_volatility_percent": 1.5,
            "volatility_z_score": 0.0,
            "skewness": 0.0,
            "regime": "NORMAL_BALANCED",
            "description": "Đang phân tích bề mặt biến động...",
            "reversal_setup": None,
            "is_squeeze": False
        }

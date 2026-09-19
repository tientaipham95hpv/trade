import logging
import numpy as np
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger("AutoTuner")


class StrategyAutoTuner:
    """
    AI Auto-Tuning Strategy Optimizer (Module Tối Ưu Hóa Tham Số Động):
    - Đo lường độ biến động thực tế (Realized & Historical Volatility, ATR%) của 100 nến gần nhất.
    - Tự động phân loại trạng thái thị trường của từng cặp coin thành HIGH, NORMAL, hoặc LOW Volatility.
    - Tự động điều chỉnh động ngưỡng RSI (Oversold/Overbought) và hệ số nhân ATR Stop Loss.
    - Giúp triệt tiêu hiện tượng quét râu nến (Stop Hunt) trên các coin biến động mạnh, 
      đồng thời tối ưu hóa tỷ lệ R:R trên các coin biến động hẹp.
    """

    @staticmethod
    def calculate_adaptive_params(symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Tính toán bộ tham số thích ứng cho cặp coin dựa trên dữ liệu nến.
        Trả về:
            - volatility_level: 'HIGH' | 'NORMAL' | 'LOW'
            - atr_percent: Độ giãn nến trung bình (%)
            - rsi_oversold: Ngưỡng quá bán thích ứng (22 - 35)
            - rsi_overbought: Ngưỡng quá mua thích ứng (65 - 78)
            - sl_atr_multiplier: Hệ số nhân Stop Loss theo ATR (1.2x - 2.2x)
            - target_rr_ratio: Tỷ lệ Risk:Reward mục tiêu (1.4x - 2.0x)
            - volatility_score: Điểm biến động thang 100
        """
        if df is None or len(df) < 30:
            return {
                "symbol": symbol,
                "volatility_level": "NORMAL",
                "atr_percent": 1.2,
                "rsi_oversold": 30.0,
                "rsi_overbought": 70.0,
                "sl_atr_multiplier": 1.5,
                "target_rr_ratio": 1.5,
                "volatility_score": 50
            }

        try:
            closes = df["close"].values
            highs = df["high"].values
            lows = df["low"].values

            # 1. Tính ATR 14
            tr_list = []
            for i in range(1, len(df)):
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1])
                )
                tr_list.append(tr)

            atr_14 = float(np.mean(tr_list[-14:])) if len(tr_list) >= 14 else float(np.mean(tr_list))
            cur_price = float(closes[-1])
            atr_pct = (atr_14 / cur_price * 100.0) if cur_price > 0 else 1.0

            # 2. Tính Historical Volatility (Độ lệch chuẩn log returns của 30 nến gần nhất)
            log_ret = np.diff(np.log(closes[-31:]))
            hv_score = float(np.std(log_ret) * 100.0) if len(log_ret) > 1 else 1.0

            # 3. Phân loại Volatility Level
            if atr_pct >= 1.6 or hv_score >= 1.8:
                level = "HIGH"
                rsi_os = 24.0
                rsi_ob = 76.0
                sl_mult = 2.0
                rr = 1.6
                vol_score = min(100, int(50 + (atr_pct * 25)))
            elif atr_pct <= 0.75 and hv_score <= 0.8:
                level = "LOW"
                rsi_os = 34.0
                rsi_ob = 66.0
                sl_mult = 1.2
                rr = 1.8
                vol_score = max(10, int(atr_pct * 40))
            else:
                level = "NORMAL"
                rsi_os = 30.0
                rsi_ob = 70.0
                sl_mult = 1.5
                rr = 1.5
                vol_score = int(35 + (atr_pct * 20))

            return {
                "symbol": symbol,
                "volatility_level": level,
                "atr_percent": round(atr_pct, 2),
                "rsi_oversold": rsi_os,
                "rsi_overbought": rsi_ob,
                "sl_atr_multiplier": sl_mult,
                "target_rr_ratio": rr,
                "volatility_score": vol_score
            }
        except Exception as e:
            logger.warning("Lỗi tính toán AutoTuner cho %s: %s", symbol, e)
            return {
                "symbol": symbol,
                "volatility_level": "NORMAL",
                "atr_percent": 1.2,
                "rsi_oversold": 30.0,
                "rsi_overbought": 70.0,
                "sl_atr_multiplier": 1.5,
                "target_rr_ratio": 1.5,
                "volatility_score": 50
            }

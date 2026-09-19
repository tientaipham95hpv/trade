from typing import Dict, Any
import pandas as pd
from .base_strategy import BaseStrategy, Signal
from .indicators import TechnicalIndicators


class MeanReversionStrategy(BaseStrategy):
    """
    Chiến lược Đảo Chiều Vùng Sideway (Mean Reversion / Range Bound):
    - Hoạt động tối ưu khi thị trường không có xu hướng mạnh (ADX < 20).
    - Mua ở dải Bollinger Band dưới (quá bán RSI < 32) và bán ở dải Bollinger Band trên (quá mua RSI > 68).
    - Chốt lời tại đường trung bình giữa (SMA 20) của dải Bollinger Bands.
    """

    def __init__(self, rr_ratio: float = 1.3, rsi_oversold: float = 32.0, rsi_overbought: float = 68.0):
        super().__init__(name="Sideway Mean Reversion")
        self.rr_ratio = rr_ratio
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def generate_signal(self, htf_df: pd.DataFrame, ltf_df: pd.DataFrame) -> Dict[str, Any]:
        default_res = {
            "signal": Signal.HOLD,
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "reason": "Chưa chạm biên dải Bollinger Bands Sideway",
            "indicators": {}
        }

        if htf_df.empty or ltf_df.empty or len(ltf_df) < 30:
            default_res["reason"] = "Không đủ nến để tính Bollinger Bands"
            return default_res

        ltf = TechnicalIndicators.populate_all(ltf_df)
        htf = TechnicalIndicators.populate_all(htf_df)

        last_ltf = ltf.iloc[-1]
        prev_ltf = ltf.iloc[-2]
        last_htf = htf.iloc[-1] if not htf.empty else last_ltf

        cur_close = float(last_ltf['close'])
        cur_low = float(last_ltf['low'])
        cur_high = float(last_ltf['high'])
        rsi = float(last_ltf.get('rsi', 50.0))
        bb_lower = float(last_ltf.get('bb_lower', cur_close * 0.98))
        bb_upper = float(last_ltf.get('bb_upper', cur_close * 1.02))
        bb_mid = float(last_ltf.get('bb_middle', (bb_lower + bb_upper) / 2))
        atr = float(last_ltf.get('atr', cur_close * 0.01))
        if atr <= 0:
            atr = cur_close * 0.01

        htf_adx = float(last_htf.get('adx', 15.0))

        indicators_snapshot = {
            "cur_close": round(cur_close, 4),
            "rsi": round(rsi, 1),
            "bb_lower": round(bb_lower, 4),
            "bb_middle": round(bb_mid, 4),
            "bb_upper": round(bb_upper, 4),
            "atr": round(atr, 4),
            "htf_adx": round(htf_adx, 1)
        }
        default_res["indicators"] = indicators_snapshot

        # 1. Tín hiệu BUY: Giá chạm/xuyên dải BB Dưới và RSI < 32
        if (cur_low <= bb_lower or cur_close <= bb_lower) and rsi <= self.rsi_oversold:
            stop_loss = cur_close - 1.2 * atr
            take_profit = bb_mid if bb_mid > cur_close else (cur_close + 1.5 * atr)
            return {
                "signal": Signal.BUY,
                "entry_price": cur_close,
                "stop_loss": round(stop_loss, 4),
                "take_profit": round(take_profit, 4),
                "reason": f"Sideway chạm đáy Bollinger ({cur_close:,.4f} <= {bb_lower:,.4f}) + RSI quá bán ({rsi:.1f})",
                "indicators": indicators_snapshot
            }

        # 2. Tín hiệu SELL: Giá chạm/xuyên dải BB Trên và RSI > 68
        if (cur_high >= bb_upper or cur_close >= bb_upper) and rsi >= self.rsi_overbought:
            stop_loss = cur_close + 1.2 * atr
            take_profit = bb_mid if bb_mid < cur_close else (cur_close - 1.5 * atr)
            return {
                "signal": Signal.SELL,
                "entry_price": cur_close,
                "stop_loss": round(stop_loss, 4),
                "take_profit": round(take_profit, 4),
                "reason": f"Sideway chạm đỉnh Bollinger ({cur_close:,.4f} >= {bb_upper:,.4f}) + RSI quá mua ({rsi:.1f})",
                "indicators": indicators_snapshot
            }

        default_res["reason"] = f"Sideway an toàn, RSI: {rsi:.1f}, BB: [${bb_lower:,.2f} - ${bb_upper:,.2f}]"
        return default_res

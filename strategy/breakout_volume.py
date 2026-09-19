from typing import Dict, Any
import pandas as pd
from .base_strategy import BaseStrategy, Signal
from .indicators import TechnicalIndicators


class BreakoutVolumeStrategy(BaseStrategy):
    """
    Chiến lược Đột Phá Khối Lượng (Breakout Volume Spike):
    - Nhận diện các cú bứt phá cản (20 nến gần nhất) kèm khối lượng bùng nổ (Volume Spike > 2.0x SMA20).
    - Rất hiệu quả khi săn sóng lớn trên Altcoin và Meme coin.
    """

    def __init__(self, rr_ratio: float = 2.0, volume_spike_threshold: float = 2.0, lookback_candles: int = 20):
        super().__init__(name="Breakout Volume Spike")
        self.rr_ratio = rr_ratio
        self.volume_spike_threshold = volume_spike_threshold
        self.lookback_candles = lookback_candles

    def generate_signal(self, htf_df: pd.DataFrame, ltf_df: pd.DataFrame) -> Dict[str, Any]:
        default_res = {
            "signal": Signal.HOLD,
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "reason": "Chưa có tín hiệu Breakout thỏa mãn",
            "indicators": {}
        }

        if htf_df.empty or ltf_df.empty or len(ltf_df) < (self.lookback_candles + 10):
            default_res["reason"] = "Không đủ nến để xác định cản Breakout"
            return default_res

        ltf = TechnicalIndicators.populate_all(ltf_df)
        htf = TechnicalIndicators.populate_all(htf_df)

        last_candle = ltf.iloc[-1]
        prev_candles = ltf.iloc[-(self.lookback_candles + 1):-1]

        cur_close = float(last_candle['close'])
        cur_volume = float(last_candle['volume'])
        atr = float(last_candle.get('atr', cur_close * 0.01))
        if atr <= 0:
            atr = cur_close * 0.01

        # Tính khối lượng trung bình 20 nến trước
        avg_volume = float(prev_candles['volume'].mean()) if len(prev_candles) > 0 else 1.0
        vol_ratio = (cur_volume / avg_volume) if avg_volume > 0 else 1.0

        # Mức kháng cự và hỗ trợ trong 20 nến trước
        resistance = float(prev_candles['high'].max())
        support = float(prev_candles['low'].min())

        htf_last = htf.iloc[-1] if not htf.empty else last_candle
        htf_adx = float(htf_last.get('adx', 20.0))

        indicators_snapshot = {
            "cur_close": round(cur_close, 4),
            "resistance": round(resistance, 4),
            "support": round(support, 4),
            "cur_volume": round(cur_volume, 2),
            "avg_volume": round(avg_volume, 2),
            "vol_spike_ratio": round(vol_ratio, 2),
            "atr": round(atr, 4),
            "htf_adx": round(htf_adx, 1)
        }
        default_res["indicators"] = indicators_snapshot

        # 1. Tín hiệu Breakout LONG: Đóng nến vượt cản trên + Volume Spike >= 2.0x
        if cur_close > resistance and vol_ratio >= self.volume_spike_threshold:
            stop_loss = max(support, cur_close - 1.5 * atr)
            risk_dist = cur_close - stop_loss
            if risk_dist <= 0:
                stop_loss = cur_close - 1.5 * atr
                risk_dist = 1.5 * atr

            take_profit = cur_close + (risk_dist * self.rr_ratio)
            return {
                "signal": Signal.BUY,
                "entry_price": cur_close,
                "stop_loss": round(stop_loss, 4),
                "take_profit": round(take_profit, 4),
                "reason": f"Breakout cản trên (${resistance:,.4f}) + Volume Spike {vol_ratio:.1f}x (R:R 1:{self.rr_ratio})",
                "indicators": indicators_snapshot
            }

        # 2. Tín hiệu Breakdown SHORT: Đóng nến thủng hỗ trợ dưới + Volume Spike >= 2.0x
        if cur_close < support and vol_ratio >= self.volume_spike_threshold:
            stop_loss = min(resistance, cur_close + 1.5 * atr)
            risk_dist = stop_loss - cur_close
            if risk_dist <= 0:
                stop_loss = cur_close + 1.5 * atr
                risk_dist = 1.5 * atr

            take_profit = cur_close - (risk_dist * self.rr_ratio)
            return {
                "signal": Signal.SELL,
                "entry_price": cur_close,
                "stop_loss": round(stop_loss, 4),
                "take_profit": round(take_profit, 4),
                "reason": f"Breakdown hỗ trợ (${support:,.4f}) + Volume Spike {vol_ratio:.1f}x (R:R 1:{self.rr_ratio})",
                "indicators": indicators_snapshot
            }

        default_res["reason"] = f"Đang theo dõi cản [${support:,.2f} - ${resistance:,.2f}], Volume: {vol_ratio:.1f}x"
        return default_res

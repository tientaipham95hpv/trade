from typing import Dict, Any
import pandas as pd
from .base_strategy import BaseStrategy, Signal
from .indicators import TechnicalIndicators


class TrendPullbackStrategy(BaseStrategy):
    """
    Chiến lược Đa Khung Thời Gian:
    - HTF (1h): Xác định Trend bằng EMA 50 / EMA 200.
    - LTF (15m): Bắt nhịp hồi (Pullback) bằng RSI + Bollinger Bands + ATR Stop Loss.
    """

    def __init__(self, rr_ratio: float = 1.5, atr_multiplier: float = 1.5, adx_min: float = 20.0):
        super().__init__(name="Multi-Timeframe Trend Pullback")
        self.rr_ratio = rr_ratio
        self.atr_multiplier = atr_multiplier
        self.adx_min = adx_min

    def generate_signal(self, htf_df: pd.DataFrame, ltf_df: pd.DataFrame) -> Dict[str, Any]:
        default_res = {
            "signal": Signal.HOLD,
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "reason": "Chưa có tín hiệu thỏa mãn điều kiện",
            "indicators": {}
        }

        if htf_df.empty or ltf_df.empty or len(htf_df) < 50 or len(ltf_df) < 30:
            default_res["reason"] = "Không đủ dữ liệu nến để tính toán chỉ báo"
            return default_res

        # Tính toán chỉ báo cho HTF và LTF
        htf = TechnicalIndicators.populate_all(htf_df)
        ltf = TechnicalIndicators.populate_all(ltf_df)

        # Lấy các nến gần nhất
        htf_last = htf.iloc[-1]
        ltf_last = ltf.iloc[-1]
        ltf_prev = ltf.iloc[-2]

        htf_adx = float(htf_last.get('adx', 25.0))

        # 1. Xác định xu hướng HTF (1H)
        htf_uptrend = (htf_last['ema_50'] > htf_last['ema_200']) and (htf_last['close'] > htf_last['ema_50'])
        htf_downtrend = (htf_last['ema_50'] < htf_last['ema_200']) and (htf_last['close'] < htf_last['ema_50'])

        current_price = float(ltf_last['close'])
        atr = float(ltf_last['atr']) if ltf_last['atr'] > 0 else (current_price * 0.01)

        indicators_snapshot = {
            "htf_close": round(float(htf_last['close']), 4),
            "htf_ema50": round(float(htf_last['ema_50']), 4),
            "htf_ema200": round(float(htf_last['ema_200']), 4),
            "htf_adx": round(htf_adx, 2),
            "ltf_rsi": round(float(ltf_last['rsi']), 2),
            "ltf_bb_lower": round(float(ltf_last['bb_lower']), 4),
            "ltf_bb_upper": round(float(ltf_last['bb_upper']), 4),
            "atr": round(atr, 4)
        }

        # Bộ lọc ADX Trend Strength: Nếu ADX < adx_min, thị trường sideway yếu, bỏ qua setup
        if htf_adx < self.adx_min:
            default_res["reason"] = f"HTF Trend yếu (ADX={htf_adx:.1f} < {self.adx_min}), thị trường sideway tích lũy"
            default_res["indicators"] = indicators_snapshot
            return default_res

        # 2. Điều kiện LONG
        # - HTF là Uptrend
        # - LTF có nhịp điều chỉnh: nến vừa chạm/xuyên dưới BB Lower hoặc RSI < 38
        # - Nến LTF hiện tại bắt đầu hồi phục (close > open hoặc rsi > rsi_prev)
        long_pullback = (
            (ltf_prev['low'] <= ltf_prev['bb_lower'] or ltf_last['low'] <= ltf_last['bb_lower'] or ltf_last['rsi'] < 38)
            and (ltf_last['close'] >= ltf_last['open'] or ltf_last['rsi'] > ltf_prev['rsi'])
            and ltf_last['close'] > ltf_last['bb_lower']
        )

        if htf_uptrend and long_pullback:
            # Stop loss đặt dưới đáy nến gần nhất kết hợp ATR
            recent_low = float(ltf.iloc[-5:]['low'].min())
            sl_distance = max(current_price - recent_low, atr * self.atr_multiplier)
            # Giới hạn SL không quá sát (tối thiểu 0.4%) và không quá xa (tối đa 4%)
            sl_distance = max(sl_distance, current_price * 0.004)
            sl_distance = min(sl_distance, current_price * 0.04)

            stop_loss = current_price - sl_distance
            take_profit = current_price + (sl_distance * self.rr_ratio)

            return {
                "signal": Signal.BUY,
                "entry_price": current_price,
                "stop_loss": round(stop_loss, 4),
                "take_profit": round(take_profit, 4),
                "reason": f"LONG: HTF Uptrend (EMA50 > EMA200) + LTF Pullback chạm BB/RSI quá bán và bật lại (R:R 1:{self.rr_ratio})",
                "indicators": indicators_snapshot
            }

        # 3. Điều kiện SHORT
        # - HTF là Downtrend
        # - LTF có nhịp hồi kỹ thuật: nến chạm/xuyên trên BB Upper hoặc RSI > 62
        # - Nến LTF hiện tại bắt đầu đảo chiều giảm (close < open hoặc rsi < rsi_prev)
        short_pullback = (
            (ltf_prev['high'] >= ltf_prev['bb_upper'] or ltf_last['high'] >= ltf_last['bb_upper'] or ltf_last['rsi'] > 62)
            and (ltf_last['close'] <= ltf_last['open'] or ltf_last['rsi'] < ltf_prev['rsi'])
            and ltf_last['close'] < ltf_last['bb_upper']
        )

        if htf_downtrend and short_pullback:
            recent_high = float(ltf.iloc[-5:]['high'].max())
            sl_distance = max(recent_high - current_price, atr * self.atr_multiplier)
            sl_distance = max(sl_distance, current_price * 0.004)
            sl_distance = min(sl_distance, current_price * 0.04)

            stop_loss = current_price + sl_distance
            take_profit = current_price - (sl_distance * self.rr_ratio)

            return {
                "signal": Signal.SELL,
                "entry_price": current_price,
                "stop_loss": round(stop_loss, 4),
                "take_profit": round(take_profit, 4),
                "reason": f"SHORT: HTF Downtrend (EMA50 < EMA200) + LTF Pullback chạm BB Upper/RSI quá mua và đảo chiều (R:R 1:{self.rr_ratio})",
                "indicators": indicators_snapshot
            }

        trend_desc = "Uptrend" if htf_uptrend else ("Downtrend" if htf_downtrend else "Sideway")
        default_res["reason"] = f"HTF đang {trend_desc} nhưng LTF chưa có điểm hồi pullback chuẩn"
        default_res["indicators"] = indicators_snapshot
        return default_res

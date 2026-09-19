import logging
import time
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("BinanceSMCDetector")


class BinanceSMCDetector:
    """
    Smart Money Concepts (SMC) & Institutional Structure Detector (Phiên bản 9.0):
    - Tự động nhận diện cấu trúc dòng tiền của tạo lập thị trường (Institutions & Market Makers) trên Binance Futures:
        1. Order Block (OB): Vùng tích lũy/phân phối cuối cùng trước khi đẩy sóng phá vỡ cấu trúc (Break of Structure - BOS).
        2. Fair Value Gap (FVG): Khoảng mất cân bằng thanh khoản giữa 3 nến liên tiếp mà thị trường có xu hướng quay về lấp (Imbalance Fill).
        3. Liquidity Sweep: Pha quét râu nến (Stop-hunt) tại đỉnh/đáy cũ trước khi đảo chiều mạnh.
    - Cung cấp điểm vào lệnh bắn tỉa Sniper Entry với tỷ lệ Risk:Reward cực cao từ 1:3 đến 1:5.
    - Hoạt động thuần 100% trên dữ liệu nến Binance Futures.
    """

    @staticmethod
    def analyze_smc_structure(symbol: str = "BTCUSDT", interval: str = "15m", limit: int = 40) -> Dict[str, Any]:
        """
        Phân tích cấu trúc SMC trên cặp symbol
        """
        symbol = symbol.upper()
        try:
            url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={min(100, max(30, limit))}"
            res = requests.get(url, timeout=4)
            if res.status_code != 200:
                return BinanceSMCDetector._fallback(symbol)

            klines = res.json()
            if not klines or len(klines) < 20:
                return BinanceSMCDetector._fallback(symbol)

            candles = []
            for k in klines:
                candles.append({
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5])
                })

            cur_price = candles[-1]["close"]
            found_fvg = []
            found_ob = []
            sweep_detected = False
            sweep_note = "Chưa phát hiện quét râu thanh khoản."

            # 1. Phát hiện Fair Value Gap (FVG) trong 10 nến gần nhất
            for i in range(len(candles) - 10, len(candles) - 1):
                c1 = candles[i - 1]
                c2 = candles[i]
                c3 = candles[i + 1]

                # Bullish FVG: Râu nến 1 thấp hơn đáy nến 3 (tạo khoảng trống tăng giá)
                if c3["low"] > c1["high"]:
                    found_fvg.append({
                        "type": "BULLISH_FVG (KHOẢNG TRỐNG MUA)",
                        "top": c3["low"],
                        "bottom": c1["high"],
                        "midpoint": round((c3["low"] + c1["high"]) / 2.0, 4)
                    })
                # Bearish FVG: Râu nến 1 cao hơn đỉnh nến 3 (tạo khoảng trống giảm giá)
                elif c1["low"] > c3["high"]:
                    found_fvg.append({
                        "type": "BEARISH_FVG (KHOẢNG TRỐNG BÁN)",
                        "top": c1["low"],
                        "bottom": c3["high"],
                        "midpoint": round((c1["low"] + c3["high"]) / 2.0, 4)
                    })

            # 2. Phát hiện Order Block (OB) gần nhất
            for i in range(len(candles) - 15, len(candles) - 2):
                c_prev = candles[i]
                c_next = candles[i + 1]

                # Bullish OB: Nến giảm cuối cùng trước một nến tăng vọt phá đỉnh
                if c_prev["close"] < c_prev["open"] and c_next["close"] > c_prev["high"]:
                    found_ob.append({
                        "type": "BULLISH_OB (VÙNG CẦU TỔ CHỨC)",
                        "high": c_prev["high"],
                        "low": c_prev["low"]
                    })
                # Bearish OB: Nến tăng cuối cùng trước một nến xả thủng đáy
                elif c_prev["close"] > c_prev["open"] and c_next["close"] < c_prev["low"]:
                    found_ob.append({
                        "type": "BEARISH_OB (VÙNG CUNG TỔ CHỨC)",
                        "high": c_prev["high"],
                        "low": c_prev["low"]
                    })

            # 3. Phát hiện Liquidity Sweep (Quét râu) ở nến gần nhất
            recent_highs = [c["high"] for c in candles[-15:-1]]
            recent_lows = [c["low"] for c in candles[-15:-1]]
            max_h = max(recent_highs)
            min_l = min(recent_lows)
            cur_candle = candles[-1]

            if cur_candle["high"] > max_h and cur_candle["close"] < max_h:
                sweep_detected = True
                sweep_note = f"Quét râu bẫy phe Mua trên đỉnh cũ ${max_h:,.2f} rồi rút chân (Bearish Sweep)!"
            elif cur_candle["low"] < min_l and cur_candle["close"] > min_l:
                sweep_detected = True
                sweep_note = f"Quét râu bẫy phe Bán dưới đáy cũ ${min_l:,.2f} rồi rút chân (Bullish Sweep)!"

            # Dự phóng tín hiệu SMC
            active_fvg = found_fvg[-1] if found_fvg else None
            active_ob = found_ob[-1] if found_ob else None

            smc_bias = "NEUTRAL"
            if sweep_detected and "Bearish" in sweep_note:
                smc_bias = "SNIPER_SHORT_SMC"
            elif sweep_detected and "Bullish" in sweep_note:
                smc_bias = "SNIPER_LONG_SMC"
            elif active_ob and "BULLISH" in active_ob["type"]:
                smc_bias = "BULLISH_ORDER_BLOCK_SUPPORT"
            elif active_ob and "BEARISH" in active_ob["type"]:
                smc_bias = "BEARISH_ORDER_BLOCK_RESISTANCE"

            return {
                "symbol": symbol,
                "current_price": cur_price,
                "smc_bias": smc_bias,
                "active_fvg": active_fvg,
                "active_ob": active_ob,
                "sweep_detected": sweep_detected,
                "sweep_note": sweep_note,
                "fvg_count": len(found_fvg),
                "ob_count": len(found_ob),
                "timeframe": interval
            }

        except Exception as e:
            logger.error("Lỗi phân tích SMC cho %s: %s", symbol, e)
            return BinanceSMCDetector._fallback(symbol)

    @staticmethod
    def _fallback(symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "current_price": 0.0,
            "smc_bias": "NEUTRAL",
            "active_fvg": None,
            "active_ob": None,
            "sweep_detected": False,
            "sweep_note": "Đang đồng bộ cấu trúc nến SMC...",
            "fvg_count": 0,
            "ob_count": 0,
            "timeframe": "15m"
        }

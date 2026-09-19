import logging
import math
import numpy as np
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("PairsTrading")


class StatisticalPairsTrading:
    """
    Multi-Asset Statistical Pairs Trading & Cointegration Engine (Phiên bản 7.0):
    - Khai thác tính đồng liên kết (Cointegration) và hồi quy trung bình chênh lệch giá (Spread Mean Reversion).
    - Phân tích các cặp tài sản có mối liên hệ bền vững: BTC/ETH, SOL/AVAX, BTC/SOL...
    - Tính toán độ lệch chuẩn hóa Z-Score của tỷ số Spread = Price(A) / Price(B).
    - Tạo tín hiệu giao dịch chênh lệch Delta-Neutral:
        * Khi Z >= +2.0: Coin A đắt tương đối so với Coin B -> SHORT A & LONG B.
        * Khi Z <= -2.0: Coin A rẻ tương đối so với Coin B -> LONG A & SHORT B.
        * Khi |Z| <= 0.5: Chốt lời khi Spread hội tụ về điểm cân bằng thống kê.
    """

    SUPPORTED_PAIRS = [
        ("ETHUSDT", "BTCUSDT", "ETH/BTC Synthetic Ratio"),
        ("SOLUSDT", "ETHUSDT", "SOL/ETH Layer-1 Ratio"),
        ("AVAXUSDT", "SOLUSDT", "AVAX/SOL Alternative L1 Ratio"),
        ("BNBUSDT", "BTCUSDT", "BNB/BTC Exchange Ecosystem Ratio")
    ]

    @staticmethod
    def scan_all_pairs() -> List[Dict[str, Any]]:
        """
        Quét toàn bộ các cặp thống kê để tìm kiếm cơ hội chênh lệch giá
        """
        results = []
        for sym_a, sym_b, label in StatisticalPairsTrading.SUPPORTED_PAIRS:
            try:
                metrics = StatisticalPairsTrading.calculate_pair_spread(sym_a, sym_b, label)
                if metrics:
                    results.append(metrics)
            except Exception as e:
                logger.error("Lỗi quét cặp %s vs %s: %s", sym_a, sym_b, e)
        return results

    @staticmethod
    def calculate_pair_spread(symbol_a: str, symbol_b: str, label: str = "") -> Optional[Dict[str, Any]]:
        """
        Tính toán Spread, Mean, Std Dev và Z-Score cho cặp symbol_a và symbol_b
        """
        try:
            # Lấy 30 nến 1h của cả 2 coin
            url_a = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol_a}&interval=1h&limit=30"
            url_b = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol_b}&interval=1h&limit=30"

            res_a = requests.get(url_a, timeout=4)
            res_b = requests.get(url_b, timeout=4)

            if res_a.status_code != 200 or res_b.status_code != 200:
                return None

            klines_a = res_a.json()
            klines_b = res_b.json()

            min_len = min(len(klines_a), len(klines_b))
            if min_len < 20:
                return None

            spreads = []
            for i in range(-min_len, 0):
                c_a = float(klines_a[i][4])
                c_b = float(klines_b[i][4])
                if c_b > 0:
                    spreads.append(c_a / c_b)

            if not spreads:
                return None

            cur_spread = spreads[-1]
            mean_spread = float(np.mean(spreads))
            std_spread = float(np.std(spreads)) if len(spreads) > 1 else 0.001
            if std_spread == 0:
                std_spread = 0.001

            z_score = (cur_spread - mean_spread) / std_spread

            # Xác định tín hiệu Delta-Neutral
            action = "NEUTRAL"
            signal_detail = "Khoảng chênh lệch nằm trong biên độ cân bằng."

            if z_score >= 2.0:
                action = "SHORT_A_LONG_B"
                signal_detail = f"SHORT {symbol_a} & LONG {symbol_b} (Z-Score = +{round(z_score, 2)}: {symbol_a} đang lệch dương quá mức)."
            elif z_score <= -2.0:
                action = "LONG_A_SHORT_B"
                signal_detail = f"LONG {symbol_a} & SHORT {symbol_b} (Z-Score = {round(z_score, 2)}: {symbol_a} đang lệch âm quá mức)."
            elif abs(z_score) <= 0.5:
                signal_detail = "Hội tụ cân bằng (Spread Convergence). Vùng chốt lời lý tưởng."

            return {
                "pair_name": f"{symbol_a} / {symbol_b}",
                "label": label or f"{symbol_a} vs {symbol_b}",
                "symbol_a": symbol_a,
                "symbol_b": symbol_b,
                "current_spread": round(cur_spread, 6),
                "mean_spread": round(mean_spread, 6),
                "std_spread": round(std_spread, 6),
                "z_score": round(z_score, 2),
                "action": action,
                "signal_detail": signal_detail,
                "is_divergent": abs(z_score) >= 1.8
            }

        except Exception as e:
            logger.error("Lỗi tính toán Pairs Trading: %s", e)
            return None

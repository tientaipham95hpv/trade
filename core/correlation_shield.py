import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

logger = logging.getLogger("CorrelationShield")


class PortfolioCorrelationShield:
    """
    Khiên Quản Trị Rủi Ro Tương Quan Danh Mục (Portfolio Correlation Risk Shield):
    - Tính toán ma trận hệ số tương quan Pearson giữa các cặp coin.
    - Ngăn chặn việc bot mở cùng lúc các vị thế cùng chiều trên các cặp coin có độ tương quan cao (đồng pha >= 0.75).
    - Ví dụ: Tránh việc bot đồng thời Short BTC, Short ETH và Short SOL, dẫn đến nguy cơ nhân ba thua lỗ khi thị trường bật tăng mạnh.
    - Giúp đa dạng hóa rủi ro danh mục tuyệt đối (Basket Diversification).
    """

    def __init__(self, max_correlation_threshold: float = 0.75):
        self.max_correlation_threshold = max_correlation_threshold
        self._price_history_cache: Dict[str, pd.Series] = {}

    def update_price_cache(self, symbol: str, closes: List[float]):
        """Cập nhật chuỗi đóng nến lịch sử cho coin"""
        if closes and len(closes) >= 20:
            self._price_history_cache[symbol] = pd.Series(closes)

    def check_correlation_risk(
        self,
        candidate_symbol: str,
        candidate_side: str,
        candidate_closes: List[float],
        active_positions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Kiểm tra xem việc mở thêm candidate_symbol có gây rủi ro tương quan quá mức hay không.
        Trả về:
            - is_safe: True/False
            - max_correlation: Hệ số tương quan cao nhất tìm thấy
            - correlated_with: Tên cặp coin bị trùng pha
            - warning_message: Thông điệp cảnh báo
        """
        if not active_positions:
            return {
                "is_safe": True,
                "max_correlation": 0.0,
                "correlated_with": None,
                "warning_message": "Danh mục an toàn (Hiện chưa có vị thế mở khác)."
            }

        cand_series = pd.Series(candidate_closes)
        if len(cand_series) < 20:
            return {"is_safe": True, "max_correlation": 0.0, "correlated_with": None, "warning_message": "Không đủ dữ liệu nến để đo tương quan."}

        cand_returns = cand_series.pct_change().dropna()
        highest_corr = 0.0
        most_correlated_symbol = None

        for open_sym, pos in active_positions.items():
            # Chỉ kiểm tra rủi ro tương quan nếu cùng phe (Cùng Long hoặc Cùng Short)
            pos_side = pos.get("side", "")
            if pos_side != candidate_side:
                continue

            open_series = self._price_history_cache.get(open_sym)
            if open_series is None or len(open_series) < 20:
                continue

            open_returns = open_series.pct_change().dropna()
            min_len = min(len(cand_returns), len(open_returns))
            if min_len < 15:
                continue

            r1 = cand_returns.iloc[-min_len:]
            r2 = open_returns.iloc[-min_len:]

            try:
                corr = float(np.corrcoef(r1, r2)[0, 1])
                if not np.isnan(corr) and corr > highest_corr:
                    highest_corr = corr
                    most_correlated_symbol = open_sym
            except Exception:
                pass

        highest_corr = round(highest_corr, 2)
        if highest_corr >= self.max_correlation_threshold:
            msg = f"🛡️ [CORRELATION SHIELD] Từ chối mở thêm {candidate_side} {candidate_symbol}! Cực kỳ đồng pha với vị thế {most_correlated_symbol} đang chạy (Hệ số tương quan r = {highest_corr} >= {self.max_correlation_threshold})."
            logger.warning(msg)
            return {
                "is_safe": False,
                "max_correlation": highest_corr,
                "correlated_with": most_correlated_symbol,
                "warning_message": msg
            }

        return {
            "is_safe": True,
            "max_correlation": highest_corr,
            "correlated_with": most_correlated_symbol,
            "warning_message": f"Tương quan an toàn ({highest_corr} < {self.max_correlation_threshold})"
        }

    def get_matrix_data(self) -> Dict[str, Any]:
        """Trả về dữ liệu ma trận tương quan giữa các coin đang được cache"""
        symbols = list(self._price_history_cache.keys())[:10]
        matrix = []
        for s1 in symbols:
            row = []
            s1_series = self._price_history_cache[s1].pct_change().dropna()
            for s2 in symbols:
                if s1 == s2:
                    row.append(1.0)
                else:
                    s2_series = self._price_history_cache[s2].pct_change().dropna()
                    min_len = min(len(s1_series), len(s2_series))
                    if min_len >= 15:
                        try:
                            c = float(np.corrcoef(s1_series.iloc[-min_len:], s2_series.iloc[-min_len:])[0, 1])
                            row.append(round(c, 2) if not np.isnan(c) else 0.0)
                        except Exception:
                            row.append(0.0)
                    else:
                        row.append(0.0)
            matrix.append({"symbol": s1, "correlations": row})
        return {"symbols": symbols, "matrix": matrix}


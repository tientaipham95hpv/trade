"""
Dynamic Fractional Kelly Criterion Position Sizer (Bản 13.0)
Tối ưu hóa quy mô vị thế theo công thức toán học Kelly Criterion phân đoạn.
Tự động tăng quy mô vốn khi xác suất thắng cao (SMC + CVD đồng thuận) và giảm xuống khi thị trường nhiễu.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("FractionalKelly")

class FractionalKellySizer:
    @staticmethod
    def calculate_kelly_position_size(
        account_capital: float = 1000.0,
        win_rate: float = 0.55,
        risk_reward_ratio: float = 1.5,
        confluence_score: int = 3 # 1 -> 5 điểm đồng thuận
    ) -> Dict[str, Any]:
        """
        Tính toán tỷ lệ % vốn vào lệnh tối ưu theo Fractional Kelly.
        """
        try:
            b = risk_reward_ratio
            p = max(0.40, min(0.85, win_rate))
            q = 1.0 - p

            # Công thức Kelly nguyên bản: K = (p*b - q) / b
            full_kelly = (p * b - q) / b if b > 0 else 0.0

            # Áp dụng hệ số an toàn (Safety Fraction: 1/4 Kelly hoặc 1/3 Kelly)
            # Dựa trên điểm hội tụ kỹ thuật (Confluence Score)
            safety_fraction = 0.25 + (confluence_score / 5.0) * 0.15 # 0.28 -> 0.40
            optimal_kelly_pct = max(0.005, min(0.035, full_kelly * safety_fraction))

            allocated_margin = round(account_capital * optimal_kelly_pct, 2)
            pct_display = round(optimal_kelly_pct * 100.0, 2)

            if pct_display >= 2.0:
                tier_label = "VỊ THẾ LỚN (HIGH CONFLUENCE APEX)"
            elif pct_display >= 1.2:
                tier_label = "VỊ THẾ TIÊU CHUẨN (BALANCED OPTIMAL)"
            else:
                tier_label = "VỊ THẾ THẬN TRỌNG (DEFENSIVE PROBING)"

            return {
                "account_capital": round(account_capital, 2),
                "estimated_win_rate": f"{round(p * 100.0, 1)}%",
                "target_risk_reward": f"1:{b}",
                "confluence_score": f"{confluence_score}/5 Điểm Đồng Thuận",
                "full_kelly_raw": f"{round(full_kelly * 100.0, 2)}%",
                "optimal_fractional_kelly_pct": f"{pct_display}%",
                "recommended_margin_usdt": allocated_margin,
                "position_tier": tier_label,
                "mathematical_edge": "Tối đa hóa tốc độ tăng trưởng vốn hình học (Geometric Capital Growth) và triệt tiêu rủi ro cháy tài khoản!"
            }
        except Exception as e:
            logger.error("Lỗi tính Fractional Kelly: %s", e)
            return {
                "account_capital": account_capital,
                "optimal_fractional_kelly_pct": "1.0%",
                "recommended_margin_usdt": 10.0,
                "position_tier": "TIÊU CHUẨN"
            }

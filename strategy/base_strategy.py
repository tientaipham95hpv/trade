from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd


class Signal:
    BUY = "BUY"       # Mở lệnh LONG
    SELL = "SELL"     # Mở lệnh SHORT
    HOLD = "HOLD"     # Không có tín hiệu


class BaseStrategy(ABC):
    """Lớp chiến lược giao dịch trừu tượng"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signal(self, htf_df: pd.DataFrame, ltf_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Phân tích nến HTF (Trend) và LTF (Entry) để đưa ra tín hiệu:
        Trả về dict:
        {
            "signal": Signal.BUY / Signal.SELL / Signal.HOLD,
            "entry_price": float,
            "stop_loss": float,
            "take_profit": float,
            "reason": str,
            "indicators": dict
        }
        """
        pass

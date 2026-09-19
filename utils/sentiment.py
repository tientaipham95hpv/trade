import time
import logging
import urllib.request
import json
from typing import Dict, Any

logger = logging.getLogger("Sentiment")


class CryptoSentiment:
    """
    Module phân tích Tâm Lý Thị Trường Tiền Số (Crypto Fear and Greed Index):
    - Thu thập dữ liệu thời gian thực từ Alternative.me API
    - Lưu bộ nhớ đệm (Cache) 10 phút chống nghẽn mạng
    - Cung cấp thiên hướng (Market Bias) và lời khuyên định lượng
    """
    _cached_data: Dict[str, Any] = {}
    _last_fetch_time: float = 0
    _cache_ttl_seconds: int = 600  # 10 phút

    @classmethod
    def get_fear_and_greed(cls) -> Dict[str, Any]:
        now = time.time()
        if cls._cached_data and (now - cls._last_fetch_time < cls._cache_ttl_seconds):
            return cls._cached_data

        try:
            url = "https://api.alternative.me/fng/?limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "BinanceQuantBot/3.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = json.loads(resp.read().decode("utf-8"))

            data_entry = raw.get("data", [{}])[0]
            val = int(data_entry.get("value", 50))
            cls_en = data_entry.get("value_classification", "Neutral")

            if val <= 25:
                cls_vi = "Sợ Hãi Cực Độ"
                color = "#EA3943"
                bias = "LONG_REVERSAL"
                advice = "Thị trường hoảng loạn cực độ! Thích hợp chiến lược Mean Reversion bắt đáy Long khi có tín hiệu đảo chiều, cẩn trọng bán đuổi Short."
            elif val <= 45:
                cls_vi = "Sợ Hãi"
                color = "#F6851B"
                bias = "CAUTIOUS_BEARISH"
                advice = "Tâm lý bi quan bao trùm. Ưu tiên bám sát Trend Pullback Short hoặc chốt lời từng phần nhanh."
            elif val <= 55:
                cls_vi = "Trung Lập"
                color = "#38BDF8"
                bias = "NEUTRAL"
                advice = "Thị trường cân bằng cung cầu. Phù hợp cả Breakout lẫn Trend Pullback theo đà bứt phá khối lượng."
            elif val <= 75:
                cls_vi = "Tham Lam"
                color = "#10B981"
                bias = "BULLISH_MOMENTUM"
                advice = "Dòng tiền hưng phấn, ưu tiên Trend Following và dời Stop Loss dương để gồng lãi."
            else:
                cls_vi = "Tham Lam Cực Độ"
                color = "#0ECB81"
                bias = "OVERHEATED_RISK"
                advice = "Thị trường quá nóng! Cảnh giác rủi ro phân kỳ xả hàng (Dump), siết chặt Trailing Stop bảo vệ thành quả."

            result = {
                "value": val,
                "classification": cls_en,
                "classification_vi": cls_vi,
                "color": color,
                "bias": bias,
                "advice": advice,
                "timestamp": data_entry.get("timestamp", str(int(now))),
                "status": "ONLINE"
            }
            cls._cached_data = result
            cls._last_fetch_time = now
            return result
        except Exception as e:
            logger.warning("Không thể lấy Fear and Greed Index: %s", e)
            if cls._cached_data:
                return cls._cached_data
            return {
                "value": 50,
                "classification": "Neutral",
                "classification_vi": "Trung Lập",
                "color": "#38BDF8",
                "bias": "NEUTRAL",
                "advice": "Tâm lý thị trường cân bằng. Bot vận hành theo chỉ báo định lượng chuẩn mực.",
                "timestamp": str(int(now)),
                "status": "DEFAULT"
            }

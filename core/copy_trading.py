import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("CopyTrading")


class CopyTradingRelay:
    """
    Multi-Account Copy-Trading Webhook Relay (Phiên bản 6.0):
    - Cho phép phân phối lệnh 1-Click hoặc lệnh tự động từ tài khoản Master
      sang danh sách các tài khoản Sub-Account hoặc Webhook của người thân/nhóm quỹ.
    - Hỗ trợ nhân tỷ lệ vốn (Multiplier) linh hoạt cho từng tài khoản follower.
    """

    def __init__(self, followers: Optional[List[Dict[str, Any]]] = None):
        self.followers = followers or []

    def dispatch_signal(self, signal_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Phát tán lệnh tới các tài khoản đính kèm"""
        if not self.followers:
            return {"success": True, "dispatched_count": 0, "message": "Chưa cài đặt follower webhook"}

        success_count = 0
        for f in self.followers:
            wh_url = f.get("webhook_url")
            if not wh_url:
                continue
            try:
                multiplier = f.get("multiplier", 1.0)
                data = {**signal_payload, "allocated_multiplier": multiplier}
                res = requests.post(wh_url, json=data, timeout=3)
                if res.status_code in [200, 201]:
                    success_count += 1
            except Exception as e:
                logger.error("Lỗi dispatch webhook copy trade: %s", e)

        return {
            "success": True,
            "dispatched_count": success_count,
            "total_followers": len(self.followers),
            "message": f"Đã bắn lệnh đồng bộ thành công tới {success_count}/{len(self.followers)} tài khoản."
        }

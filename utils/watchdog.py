import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import psutil
import requests
import utils.network_fix

logger = logging.getLogger("Watchdog")


class SystemWatchdog:
    """
    Module Giám sát Sức khỏe Máy chủ VPS & Kết nối Sàn Binance:
    - Theo dõi CPU, RAM, Dung lượng ổ cứng (Disk).
    - Đo độ trễ (Latency ping) tới Binance Futures API.
    - Tự động phát cảnh báo khẩn qua Telegram nếu tài nguyên cạn kiệt hoặc mất mạng.
    """

    def __init__(self, config, notifier=None):
        self.config = config
        self.notifier = notifier
        self.start_time = time.time()
        self.last_alert_time = 0.0
        self.alert_cooldown_seconds = 1800  # 30 phút giữa các lần cảnh báo
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def get_uptime_str(self) -> str:
        uptime_seconds = int(time.time() - self.start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        return f"{hours}h {minutes}m {seconds}s"

    def check_binance_ping(self) -> Dict[str, Any]:
        """Đo độ trễ ping tới Binance Futures Public API"""
        url = "https://fapi.binance.com/fapi/v1/ping"
        try:
            t0 = time.time()
            r = utils.network_fix.http_session.get(url, timeout=5)
            latency_ms = (time.time() - t0) * 1000.0
            if r.status_code == 200:
                return {"online": True, "latency_ms": round(latency_ms, 1), "error": None}
            return {"online": False, "latency_ms": 0.0, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"online": False, "latency_ms": 0.0, "error": str(e)}

    def get_health_metrics(self) -> Dict[str, Any]:
        """Thu thập các chỉ số tài nguyên hệ thống"""
        cpu_pct = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        ping_res = self.check_binance_ping()

        return {
            "uptime": self.get_uptime_str(),
            "cpu_percent": cpu_pct,
            "ram_percent": mem.percent,
            "ram_used_mb": round(mem.used / (1024 * 1024), 1),
            "ram_total_mb": round(mem.total / (1024 * 1024), 1),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 1),
            "binance_online": ping_res["online"],
            "binance_latency_ms": ping_res["latency_ms"],
            "binance_error": ping_res["error"],
            "timestamp": datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M:%S (VN)")
        }

    def format_telegram_report(self) -> str:
        """Định dạng báo cáo sức khỏe máy chủ đẹp mắt gửi về Telegram"""
        h = self.get_health_metrics()
        status_icon = "🟢" if (h["ram_percent"] < 85 and h["binance_online"]) else "🔴"
        binance_status = f"✅ Online ({h['binance_latency_ms']}ms)" if h["binance_online"] else f"❌ Mất kết nối ({h['binance_error']})"

        return (
            f"{status_icon} <b>TÌNH TRẠNG MÁY CHỦ VPS & HỆ THỐNG</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ <b>Thời gian chạy (Uptime):</b> <code>{h['uptime']}</code>\n"
            f"💻 <b>CPU:</b> <code>{h['cpu_percent']}%</code>\n"
            f"🧠 <b>RAM:</b> <code>{h['ram_percent']}%</code> ({h['ram_used_mb']:.0f}MB / {h['ram_total_mb']:.0f}MB)\n"
            f"💾 <b>Ổ cứng (Disk):</b> <code>{h['disk_percent']}%</code> (Trống {h['disk_free_gb']} GB)\n"
            f"🌐 <b>Binance Futures API:</b> {binance_status}\n"
            f"🕒 <i>Cập nhật: {h['timestamp']}</i>"
        )

    def start_monitoring(self):
        """Khởi động luồng giám sát định kỳ trong background"""
        if self._running:
            return
        self._running = True

        def monitor_loop():
            logger.info("Watchdog đã khởi động vòng lặp giám sát máy chủ...")
            while self._running:
                try:
                    time.sleep(self.config.watchdog_interval_seconds)
                    metrics = self.get_health_metrics()

                    # Kiểm tra các điều kiện nguy cấp
                    alerts = []
                    if metrics["ram_percent"] >= 88.0:
                        alerts.append(f"RAM quá tải ({metrics['ram_percent']}%!)")
                    if metrics["disk_percent"] >= 92.0:
                        alerts.append(f"Ổ cứng sắp đầy ({metrics['disk_percent']}%!)")
                    if not metrics["binance_online"]:
                        alerts.append(f"Mất kết nối Binance Futures ({metrics['binance_error']})")

                    if alerts and (time.time() - self.last_alert_time > self.alert_cooldown_seconds):
                        self.last_alert_time = time.time()
                        alert_msg = " | ".join(alerts)
                        logger.warning(f"🚨 [WATCHDOG ALERT] {alert_msg}")
                        if self.notifier:
                            self.notifier.send_message(
                                f"🚨 <b>CẢNH BÁO KHẨN CẤP MÁY CHỦ VPS!</b>\n"
                                f"⚠️ {alert_msg}\n\n"
                                f"Gõ <code>/health</code> để kiểm tra chi tiết thông số."
                            )
                except Exception as e:
                    logger.debug(f"Lỗi vòng lặp watchdog: {e}")

        self._thread = threading.Thread(target=monitor_loop, daemon=True, name="SystemWatchdog")
        self._thread.start()

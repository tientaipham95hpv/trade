import os
import sys
import json
import webview

# Thư mục cấu hình người dùng
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", "."), "BinanceQuantPro")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, "desktop_config.json")


class DesktopAPI:
    """API Cầu nối giữa Python và JavaScript Frontend"""
    def get_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print("Error loading config:", e)
        return {
            "serverUrl": "https://trader.noza.site",
            "authToken": "",
            "soundEnabled": True,
            "minimizeToTray": True,
            "hotkeyEmergency": "Ctrl+Shift+K"
        }

    def save_config(self, cfg):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print("Error saving config:", e)
            return False


def main():
    api = DesktopAPI()
    # Xác định đường dẫn file giao diện HTML
    if getattr(sys, 'frozen', False):
        # Đang chạy từ file .exe đã build
        base_dir = sys._MEIPASS
    else:
        # Đang chạy từ mã nguồn Python
        base_dir = os.path.dirname(os.path.abspath(__file__))

    html_path = os.path.join(base_dir, "index.html")
    icon_path = os.path.join(base_dir, "assets", "icon.ico")

    # Khởi tạo cửa sổ Desktop Native Hardware-Accelerated (Edge WebView2)
    window = webview.create_window(
        title="Binance Futures Institutional Quant Pro Terminal",
        url=html_path,
        js_api=api,
        width=1420,
        height=900,
        min_size=(1050, 720),
        background_color="#080A0F"
    )

    webview.start(debug=False, gui="edgechromium")


if __name__ == "__main__":
    main()

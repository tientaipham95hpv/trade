#!/bin/bash
# ==============================================================================
# SCRIPT CÀI ĐẶT BOT TỰ ĐỘNG LÊN CLOUD VPS (UBUNTU / DEBIAN)
# ==============================================================================

set -e

echo "=========================================================="
echo "    BẮT ĐẦU CÀI ĐẶT BINANCE FUTURES BOT LÊN VPS LINUX    "
echo "=========================================================="

# 1. Cập nhật hệ điều hành & cài đặt gói cần thiết
echo "[1/5] Đang cập nhật gói hệ thống..."
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv git curl tmux ufw htop

# 2. Tạo môi trường ảo Python (Virtual Environment)
echo "[2/5] Đang thiết lập môi trường ảo Python venv..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 3. Cài đặt các thư viện phụ thuộc
echo "[3/5] Đang cài đặt thư viện requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt
pip install fastapi uvicorn

# 4. Mở cổng Firewall cho Web Dashboard (Cổng 8088)
echo "[4/5] Mở cổng 8088 cho Web Dashboard..."
sudo ufw allow 8088/tcp || true
sudo ufw allow 22/tcp || true

# 5. Cấu hình Systemd Service chạy ngầm 24/7 và tự khởi động lại khi sập nguồn
echo "[5/5] Cấu hình Systemd Service..."
CURRENT_DIR=$(pwd)
SERVICE_FILE="/etc/systemd/system/binance-bot.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Binance Futures Quantitative Trading Bot Service
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python run_bot.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable binance-bot.service
sudo systemctl restart binance-bot.service

echo "=========================================================="
echo "   [✓] CÀI ĐẶT HOÀN TẤT! BOT ĐANG CHẠY NGẦM 24/7        "
echo "=========================================================="
echo "• Xem trạng thái dịch vụ:   sudo systemctl status binance-bot"
echo "• Xem nhật ký live:         journalctl -u binance-bot -f"
echo "• Khởi động lại bot:        sudo systemctl restart binance-bot"
echo "• Dừng bot:                 sudo systemctl stop binance-bot"
echo "• Web Dashboard:            http://$(curl -s ifconfig.me):8088"
echo "=========================================================="

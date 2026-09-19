# BINANCE FUTURES QUANTITATIVE TRADING BOT

Hệ thống bot giao dịch phái sinh (Futures) tự động trên sàn Binance, được thiết kế theo chuẩn của các quỹ định lượng (Quantitative Hedge Funds) với trọng tâm là **Bảo Toàn Vốn (Risk Management)**, **Tỷ lệ Lợi Nhuận/Rủi Ro (R:R) Dương**, và **Quét Thanh Khoản Động (Smart Market Scanner)**.

---

## 🌟 Điểm Nổi Bật Của Hệ Thống

1. **Chiến Lược Đa Khung Thời Gian (Multi-Timeframe Trend Pullback)**:
   - **Khung 1H (HTF)**: Xác định xu hướng vĩ mô với EMA 50 / EMA 200. Chỉ đánh theo hướng thuận xu hướng (Trend Following).
   - **Khung 15m (LTF)**: Bắt điểm hồi kỹ thuật (Mean Reversion Pullback) khi giá chạm dải Bollinger Bands hoặc RSI quá bán/quá mua và có tín hiệu đảo chiều.
   - Tránh đu đỉnh/bán đáy và tránh đánh ngược xu hướng lớn.

2. **Quản Trị Rủi Ro Cốt Lõi (Dynamic Position Sizing)**:
   - **Rủi ro cố định mỗi lệnh (Fixed Risk %)**: Mặc định mỗi lệnh chỉ chấp nhận lỗ tối đa **1% vốn** nếu chạm Stop Loss.
   - **Tự động co giãn khối lượng (Position Sizing)**: Tự động tính số lượng coin (Qty) dựa trên khoảng cách Stop Loss. Stop Loss xa thì giảm Qty, Stop Loss gần thì tăng Qty \(\rightarrow\) **Dù đánh coin nào, nếu dính SL bạn chỉ mất đúng 1% vốn**.
   - **Tự động Lãi kép (Compounding)**: Khi tài khoản tăng, bot tự nâng volume. Khi gặp chuỗi thua lỗ, bot tự thu nhỏ volume để bảo vệ tài khoản.

3. **Cơ Chế Bảo Vệ Vốn Sống Còn & Chốt Lời Từng Phần (Partial TP)**:
   - **Chốt lời 50% tại 1R (Partial Take Profit)**: Khi giá đạt +1R lợi nhuận, bot tự động bán chốt lời 50% khối lượng để bỏ túi lợi nhuận chắc chắn.
   - **Dời SL về hòa vốn (Breakeven Trailing)**: Đồng thời dời Stop Loss của 50% khối lượng còn lại về đúng giá vào lệnh (Risk-Free Trade), gồng lãi tự do đến mục tiêu 1.5R - 2R mà không bao giờ bị lỗ ngược.
   - **Hard Stop-Loss & Take-Profit tự động**: Luôn gắn lệnh `STOP_MARKET` ngay khi khớp Entry trên sàn.
   - **Ngắt mạch khẩn cấp (Daily Circuit Breaker)**: Nếu tổng mức lỗ trong ngày chạm ngưỡng 5%, bot sẽ tự ngắt mở lệnh mới trong 24 giờ.
   - **Ký quỹ ISOLATED**: Cô lập rủi ro theo từng vị thế, bảo vệ số dư tài khoản chính.

4. **Bền Bỉ & Lưu Trữ Dữ Liệu Tự Động (Persistence & Logging)**:
   - **Lưu trạng thái (`bot_state.json`)**: Tự động lưu các vị thế đang mở và số dư ra file JSON, chống mất dữ liệu khi mất điện hoặc máy tính khởi động lại.
   - **Xuất nhật ký giao dịch (`trade_history.csv`)**: Mỗi lệnh đóng (hoặc chốt lời 50%) được tự động ghi vào file CSV chuẩn Excel để theo dõi PnL, Winrate.
   - **Nhật ký hoạt động (`bot.log`)**: Ghi nhận toàn bộ biến động quét và lệnh ra file log.

5. **Bộ Lọc Thị Trường Thông Minh (Market Scanner)**:
   - Tự động lọc ra các cặp có Volume 24h > **50 triệu USDT** (chống trượt giá, sổ lệnh dày).
   - Bắt trọn sóng các Meme coin hot nhất (DOGE, PEPE, SHIB...) và Top Altcoin (SOL, NEAR, SUI...) khi dòng tiền đổ vào.
   - Lọc bỏ các coin có Funding Rate bất thường.
   - Giới hạn số lệnh mở đồng thời (mặc định tối đa 3 vị thế cùng lúc).

6. **An Toàn Tuyệt Đối**:
   - Hỗ trợ **Paper Trading (Dry-Run)**: Chạy thử nghiệm phân tích và khớp lệnh giả lập theo giá thị trường thực mà không rủi ro tiền thật.
   - Hỗ trợ **Binance Testnet** và **Binance Live**.
   - Thông báo thời gian thực về **Telegram**.

---

## 📁 Cấu Trúc Dự Án

```
bot_binance/
│── config/
│   ├── __init__.py
│   └── settings.py          # Quản lý cấu hình tập trung từ file .env
│── core/
│   ├── __init__.py
│   ├── binance_client.py    # Kết nối Binance Futures REST API
│   └── order_manager.py     # Quản lý vòng đời lệnh, Breakeven Stop, Paper Trading
│── strategy/
│   ├── __init__.py
│   ├── base_strategy.py     # Khung chuẩn lớp chiến lược
│   ├── indicators.py        # Tính toán EMA, RSI, ATR, Bollinger Bands, MACD
│   └── trend_pullback.py    # Logic chiến lược MTF Trend Pullback
│── risk/
│   ├── __init__.py
│   └── risk_manager.py      # Module tính toán Position Sizing và Circuit Breaker
│── scanner/
│   ├── __init__.py
│   └── market_scanner.py    # Bộ lọc quét toàn thị trường Futures theo Volume & Funding
│── notifier/
│   ├── __init__.py
│   └── telegram_bot.py      # Gửi thông báo tín hiệu, khớp lệnh, PnL qua Telegram
│── backtest/
│   ├── __init__.py
│   └── backtester.py        # Bộ máy kiểm thử chiến lược với dữ liệu lịch sử
│── .env                     # File cấu hình bí mật (API key, đòn bẩy, chế độ)
│── .env.example             # File mẫu hướng dẫn cấu hình
│── requirements.txt         # Danh sách thư viện Python
│── run_backtest.py          # Script chạy kiểm thử chiến lược (Backtest)
└── run_bot.py               # Script khởi chạy bot giao dịch chính thức
```

---

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### 1. Cài đặt môi trường Python
Dự án yêu cầu Python 3.10 trở lên. Cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```

### 2. Cấu hình file `.env`
Mở file `.env` và thiết lập các thông số:
```ini
# Chế độ thử nghiệm an toàn (Mặc định: BẬT)
DRY_RUN=True
USE_TESTNET=True

# Binance API (Khi muốn kết nối thật)
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Quản lý vốn
SIZING_MODE=risk_percent
RISK_PER_TRADE_PERCENT=1.0
LEVERAGE=5
MARGIN_TYPE=ISOLATED
RISK_REWARD_RATIO=1.5
USE_BREAKEVEN_STOP=True
MAX_DAILY_LOSS_PERCENT=5.0
MAX_CONCURRENT_POSITIONS=3

# Bộ lọc quét thị trường
ENABLE_SCANNER=True
MIN_24H_VOLUME_USDT=50000000

# Telegram (Tùy chọn)
TELEGRAM_ENABLED=False
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. Chạy Kiểm Thử Chiến Lược (Backtest)
Trước khi chạy bot thực tế, bạn có thể kiểm thử hiệu năng chiến lược trên dữ liệu lịch sử của bất kỳ cặp coin nào:
```bash
# Kiểm thử với BTCUSDT
python run_backtest.py --symbol BTCUSDT --balance 1000 --risk 1.0 --rr 1.5

# Kiểm thử với SOLUSDT
python run_backtest.py --symbol SOLUSDT --balance 1000 --risk 1.0 --rr 1.5

# Kiểm thử với ETHUSDT
python run_backtest.py --symbol ETHUSDT --balance 1000 --risk 1.0 --rr 1.5
```

### 4. Khởi chạy Bot Giao Dịch
```bash
python run_bot.py
```
- Khi chạy ở chế độ `DRY_RUN=True`, bot sẽ tự động lấy giá live từ Binance, quét thị trường, phát hiện tín hiệu, ghi nhận lệnh và giả lập khớp SL/TP với số vốn ban đầu 1,000 USDT mà **hoàn toàn không rủi ro tiền thật**.
- Khi sẵn sàng kết nối tài khoản thật:
  1. Cài `DRY_RUN=False`
  2. Cài `USE_TESTNET=False`
  3. Điền `BINANCE_API_KEY` và `BINANCE_API_SECRET` (chỉ cấp quyền *Enable Futures*, KHÔNG cấp quyền *Withdraw*).

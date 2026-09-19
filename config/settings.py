import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()


BOT_VERSION = ""


@dataclass
class BotConfig:
    # Versioning
    app_version: str = ""

    # Binance API
    api_key: str = os.getenv("BINANCE_API_KEY", "")
    api_secret: str = os.getenv("BINANCE_API_SECRET", "")
    use_testnet: bool = os.getenv("USE_TESTNET", "True").lower() == "true"
    dry_run: bool = os.getenv("DRY_RUN", "True").lower() == "true"

    # Capital & Risk Management
    sizing_mode: str = os.getenv("SIZING_MODE", "risk_percent").lower()
    risk_per_trade_percent: float = float(os.getenv("RISK_PER_TRADE_PERCENT", "1.0"))
    margin_percent_per_trade: float = float(os.getenv("MARGIN_PERCENT_PER_TRADE", "5.0"))
    fixed_usdt_per_trade: float = float(os.getenv("FIXED_USDT_PER_TRADE", "50.0"))

    leverage: int = int(os.getenv("LEVERAGE", "5"))
    margin_type: str = os.getenv("MARGIN_TYPE", "ISOLATED").upper()
    risk_reward_ratio: float = float(os.getenv("RISK_REWARD_RATIO", "1.5"))
    use_breakeven_stop: bool = os.getenv("USE_BREAKEVEN_STOP", "True").lower() == "true"
    use_partial_tp: bool = os.getenv("USE_PARTIAL_TP", "True").lower() == "true"
    partial_tp_ratio: float = float(os.getenv("PARTIAL_TP_RATIO", "0.33"))  # Mặc định 33% cho nấc 1
    use_multi_tp: bool = os.getenv("USE_MULTI_TP", "True").lower() == "true"  # Chốt lời 3 nấc (TP1: 33% @ 1R, TP2: 33% @ 2R, TP3: 34% Trailing)
    fear_greed_enabled: bool = os.getenv("FEAR_GREED_ENABLED", "True").lower() == "true"
    max_daily_loss_percent: float = float(os.getenv("MAX_DAILY_LOSS_PERCENT", "5.0"))
    max_concurrent_positions: int = int(os.getenv("MAX_CONCURRENT_POSITIONS", "3"))

    # File Persistence & Logging
    state_file: str = os.getenv("STATE_FILE", "bot_state.json")
    trade_history_file: str = os.getenv("TRADE_HISTORY_FILE", "trade_history.csv")
    log_file: str = os.getenv("LOG_FILE", "bot.log")

    # Web Dashboard & Security
    enable_web: bool = os.getenv("ENABLE_WEB", "True").lower() == "true"
    web_port: int = int(os.getenv("WEB_PORT", "8088"))
    web_auth_enabled: bool = os.getenv("WEB_AUTH_ENABLED", "True").lower() == "true"
    web_username: str = os.getenv("WEB_USERNAME", "admin")
    web_password: str = os.getenv("WEB_PASSWORD", "admin123456")

    # Server Watchdog & Daily Backup
    watchdog_interval_seconds: int = int(os.getenv("WATCHDOG_INTERVAL_SECONDS", "60"))
    enable_daily_backup: bool = os.getenv("ENABLE_DAILY_BACKUP", "True").lower() == "true"

    # Market Scanner & Institutional Protection Filters
    enable_scanner: bool = os.getenv("ENABLE_SCANNER", "True").lower() == "true"
    min_24h_volume_usdt: float = float(os.getenv("MIN_24H_VOLUME_USDT", "50000000.0"))
    max_funding_rate: float = float(os.getenv("MAX_FUNDING_RATE", "0.0005"))
    target_symbols: str = os.getenv("TARGET_SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT")

    # Trading Modes & Dynamic Trailing Stop
    trading_mode: str = os.getenv("TRADING_MODE", "MARKET_ALL").upper()  # "MARKET_ALL" | "BLUECHIP_ONLY" | "CUSTOM"
    bluechip_symbols: str = "BTCUSDT,ETHUSDT"
    active_strategy: str = os.getenv("ACTIVE_STRATEGY", "AUTO_DYNAMIC").upper()  # "AUTO_DYNAMIC" | "TREND_PULLBACK" | "BREAKOUT" | "MEAN_REVERSION"
    real_trading_hard_cap: float = float(os.getenv("REAL_TRADING_HARD_CAP", "100.0"))  # Giới hạn vốn tối đa được phép dùng khi đánh thật
    use_trailing_stop: bool = os.getenv("USE_TRAILING_STOP", "True").lower() == "true"
    trailing_activation_rr: float = float(os.getenv("TRAILING_ACTIVATION_RR", "1.2"))  # Kích hoạt Trailing khi đạt 1.2R
    trailing_step_percent: float = float(os.getenv("TRAILING_STEP_PERCENT", "0.4"))  # Khoảng cách lùi theo giá đỉnh
    max_scan_pairs: int = int(os.getenv("MAX_SCAN_PAIRS", "80"))  # Quét top 80 cặp thanh khoản và biến động lớn nhất
    enable_web_audio: bool = True

    # Institutional Strategy Filters
    adx_min: float = float(os.getenv("ADX_MIN", "20.0"))  # Ngưỡng ADX tối thiểu để xác nhận trend mạnh
    enable_btc_crash_protection: bool = os.getenv("ENABLE_BTC_CRASH_PROTECTION", "True").lower() == "true"
    btc_crash_threshold_percent: float = float(os.getenv("BTC_CRASH_THRESHOLD_PERCENT", "1.5"))  # % giảm nến 15m của BTC để kích hoạt chặn Long
    enable_news_filter: bool = os.getenv("ENABLE_NEWS_FILTER", "True").lower() == "true"  # Chặn mở lệnh vào giờ tin tức Mỹ biến động cao

    # BTC Macro Market Regime Alignment Shield (Bộ lọc xu hướng vĩ mô BTC)
    enable_btc_regime_filter: bool = os.getenv("ENABLE_BTC_REGIME_FILTER", "True").lower() == "true"
    btc_regime_htf: str = os.getenv("BTC_REGIME_HTF", "1h")  # Khung nến phân tích xu hướng BTC (1h / 4h)
    trade_direction: str = os.getenv("TRADE_DIRECTION", "AUTO").upper()  # AUTO | LONG_ONLY | SHORT_ONLY | BOTH

    # Dynamic / Volatility-Adjusted Leverage (Đòn bẩy thích ứng tự động)
    enable_dynamic_leverage: bool = os.getenv("ENABLE_DYNAMIC_LEVERAGE", "True").lower() == "true"
    min_leverage: int = int(os.getenv("MIN_LEVERAGE", "2"))
    max_leverage: int = int(os.getenv("MAX_LEVERAGE", "10"))

    # Timeframes
    htf: str = "1h"   # Khung thời gian cao (High Time Frame) để xác định xu hướng chính
    ltf: str = "15m"  # Khung thời gian thấp (Low Time Frame) để tìm điểm vào lệnh

    # Telegram Notifier
    telegram_enabled: bool = os.getenv("TELEGRAM_ENABLED", "False").lower() == "true"
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # AI Copilot & Trade Auditor (Dual Engine: DeepSeek V4.1 Flash via TokenHarbor & Google Gemini 2.5 Flash)
    ai_enabled: bool = os.getenv("AI_ENABLED", "True").lower() == "true"
    ai_provider: str = os.getenv("AI_PROVIDER", "dual").lower()  # "dual" (khuyên dùng) | "deepseek" | "gemini"
    
    # TokenHarbor DeepSeek
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://tokenharbor.ai/v1/chat/completions")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4.1-flash:free")

    # Google Gemini
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", os.getenv("AI_API_KEY", ""))
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Backward compatibility
    ai_api_key: str = os.getenv("AI_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "deepseek-v4.1-flash:free")

    # Quant Pro Features (AI Gatekeeper, Multi-Stage TP, Smart Scaling, Circuit Breaker, Webhook)
    ai_trade_audit: bool = os.getenv("AI_TRADE_AUDIT", "True").lower() == "true"
    ai_min_audit_score: float = float(os.getenv("AI_MIN_AUDIT_SCORE", "7.5"))
    enable_multi_stage_tp: bool = os.getenv("ENABLE_MULTI_STAGE_TP", "True").lower() == "true"
    enable_smart_scaling: bool = os.getenv("ENABLE_SMART_SCALING", "False").lower() == "true"
    enable_circuit_breaker: bool = os.getenv("ENABLE_CIRCUIT_BREAKER", "True").lower() == "true"
    circuit_breaker_max_daily_loss: float = float(os.getenv("CIRCUIT_BREAKER_MAX_DAILY_LOSS", "30.0"))  # USDT ($30 or 3%)
    circuit_breaker_cooldown_hours: int = int(os.getenv("CIRCUIT_BREAKER_COOLDOWN_HOURS", "12"))
    webhook_passphrase: str = os.getenv("WEBHOOK_PASSPHRASE", "quant_pro_secret_2026")

    @property
    def symbol_list(self) -> List[str]:
        if self.trading_mode == "BLUECHIP_ONLY":
            return [s.strip().upper() for s in self.bluechip_symbols.split(",") if s.strip()]
        return [s.strip().upper() for s in self.target_symbols.split(",") if s.strip()]


config = BotConfig()

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from config.settings import BotConfig
from core.binance_client import BinanceFuturesClient
from strategy.base_strategy import BaseStrategy, Signal
from strategy.trend_pullback import TrendPullbackStrategy
from strategy.breakout_volume import BreakoutVolumeStrategy
from strategy.mean_reversion import MeanReversionStrategy
from strategy.auto_tuner import StrategyAutoTuner
from core.correlation_shield import PortfolioCorrelationShield

logger = logging.getLogger("MarketScanner")

VIETNAM_TZ = timezone(timedelta(hours=7))


class MarketScanner:
    """
    Module Quét Thị Trường Thông Minh:
    - Quét toàn bộ cặp Futures USDT trên Binance.
    - Lọc các cặp có Volume 24h > MIN_24H_VOLUME_USDT (chống trượt giá/spread).
    - Lọc loại bỏ coin có Funding Rate bất thường.
    - Tìm kiếm coin có setup giao dịch thỏa mãn chiến lược.
    """

    def __init__(self, config: BotConfig, client: BinanceFuturesClient, strategy: BaseStrategy):
        self.config = config
        self.client = client
        self.strategy = strategy
        self.pullback_strategy = strategy if isinstance(strategy, TrendPullbackStrategy) else TrendPullbackStrategy(rr_ratio=config.risk_reward_ratio, adx_min=config.adx_min)
        self.breakout_strategy = BreakoutVolumeStrategy(rr_ratio=config.risk_reward_ratio)
        self.mean_reversion_strategy = MeanReversionStrategy()
        self.correlation_shield = PortfolioCorrelationShield(max_correlation_threshold=0.75)
        self._cached_symbols: List[str] = []
        self._last_scan_time: float = 0
        self._cache_duration_seconds: float = 300  # Quét lại danh sách symbol mỗi 5 phút
        self.last_scanned_radar: List[Dict[str, Any]] = []
        self.last_btc_regime: str = "UNKNOWN"
        self.last_btc_regime_desc: str = "Đang khởi tạo"
        self.last_btc_regime_info: Dict[str, Any] = {}

    def get_liquid_symbols(self, max_pairs: int = 30) -> List[str]:
        """Lọc ra top các cặp coin thanh khoản cao nhất và đạt chuẩn an toàn"""
        now = time.time()
        if self._cached_symbols and (now - self._last_scan_time < self._cache_duration_seconds):
            return self._cached_symbols

        logger.info("Đang quét toàn thị trường Binance Futures để lọc các cặp thanh khoản cao...")
        all_tickers = self.client.get_all_24h_tickers()
        if not all_tickers:
            logger.warning("Không lấy được tickers, sử dụng danh sách target_symbols mặc định")
            return self.config.symbol_list

        qualified_pairs = []
        for t in all_tickers:
            symbol = t.get("symbol", "")
            if not symbol.endswith("USDT"):
                continue

            # Bỏ qua các token đòn bẩy hoặc chỉ số đặc biệt
            if "_" in symbol or "FOOTBALL" in symbol:
                continue

            volume_usdt = float(t.get("quoteVolume", 0.0))
            if volume_usdt >= self.config.min_24h_volume_usdt:
                qualified_pairs.append({
                    "symbol": symbol,
                    "volume": volume_usdt
                })

        # Sắp xếp theo khối lượng giảm dần và lấy top `max_pairs`
        qualified_pairs.sort(key=lambda x: x["volume"], reverse=True)
        top_symbols = [item["symbol"] for item in qualified_pairs[:max_pairs]]

        if not top_symbols:
            logger.warning("Không tìm thấy cặp nào đạt đủ volume > 50M USDT, dùng danh sách fallback.")
            top_symbols = self.config.symbol_list

        logger.info(f"Đã lọc được {len(top_symbols)} cặp thanh khoản lớn: {', '.join(top_symbols[:10])}...")
        self._cached_symbols = top_symbols
        self._last_scan_time = now
        return self._cached_symbols

    def get_btc_regime(self) -> Tuple[str, str, Dict[str, Any]]:
        """
        Nhận diện Chế độ Xu hướng Vĩ mô Bitcoin (BTC Market Regime Alignment):
        - Khung nến: 1h (mặc định)
        - Uptrend (BULL): Giá > EMA50 > EMA200 & ADX >= 20.0
          -> CẤM 100% lệnh Short (SELL) trên toàn thị trường, chỉ đánh Long.
        - Downtrend (BEAR): Giá < EMA50 < EMA200
          -> CẤM 100% lệnh Long (BUY), chỉ đánh Short.
        - Sideway: Các trường hợp còn lại (cho phép giao dịch 2 chiều).
        """
        if not getattr(self.config, "enable_btc_regime_filter", True):
            return "SIDEWAY", "Bộ lọc chế độ BTC đang TẮT (Cho phép 2 chiều)", {}

        try:
            from strategy.indicators import TechnicalIndicators
            htf_interval = getattr(self.config, "btc_regime_htf", "1h")
            btc_df = self.client.get_klines_df("BTCUSDT", interval=htf_interval, limit=120)
            if btc_df.empty or len(btc_df) < 50:
                return "SIDEWAY", "Không đủ dữ liệu nến BTC để xác định Regime", {}

            btc_df = TechnicalIndicators.populate_all(btc_df)
            last = btc_df.iloc[-1]

            close = float(last['close'])
            ema_50 = float(last.get('ema_50', 0.0))
            ema_200 = float(last.get('ema_200', 0.0))
            adx = float(last.get('adx', 20.0))

            info = {
                "btc_close": close,
                "ema_50": ema_50,
                "ema_200": ema_200,
                "adx": adx,
                "interval": htf_interval
            }

            # 1. Kiểm tra BULL Regime
            if close > ema_50 and ema_50 > ema_200 and adx >= getattr(self.config, "adx_min", 20.0):
                desc = f"BULL: BTC Uptrend mạnh ({htf_interval}: Giá ${close:,.0f} > EMA50 ${ema_50:,.0f} > EMA200 ${ema_200:,.0f} | ADX={adx:.1f}) -> CẤM SHORT"
                return "BULL", desc, info

            # 2. Kiểm tra BEAR Regime
            if close < ema_50 and ema_50 < ema_200:
                desc = f"BEAR: BTC Downtrend mạnh ({htf_interval}: Giá ${close:,.0f} < EMA50 ${ema_50:,.0f} < EMA200 ${ema_200:,.0f}) -> CẤM LONG"
                return "BEAR", desc, info

            # 3. SIDEWAY Regime
            desc = f"SIDEWAY: BTC dao động tích lũy (Giá ${close:,.0f}, EMA50 ${ema_50:,.0f}, ADX={adx:.1f}) -> Cho phép 2 chiều"
            return "SIDEWAY", desc, info
        except Exception as e:
            logger.debug(f"Lỗi khi phân tích BTC regime: {e}")
            return "SIDEWAY", f"Lỗi phân tích BTC: {e}", {}

    def check_btc_flash_crash(self) -> Tuple[bool, float, str]:
        """
        Kiểm tra độ rớt giá của BTC trong nến 15m gần nhất.
        Nếu BTC sụt giảm vượt ngưỡng cấu hình (ví dụ -1.5% trong 15m),
        toàn bộ thị trường altcoin thường sụp đổ hàng loạt => Kích hoạt bảo vệ chặn Long.
        """
        if not self.config.enable_btc_crash_protection:
            return False, 0.0, "BTC Protection Tắt"

        try:
            btc_df = self.client.get_klines_df("BTCUSDT", interval="15m", limit=5)
            if btc_df.empty or len(btc_df) < 2:
                return False, 0.0, "Không lấy được nến BTC"

            last_candle = btc_df.iloc[-1]
            prev_candle = btc_df.iloc[-2]

            o = float(last_candle['open'])
            c = float(last_candle['close'])
            prev_c = float(prev_candle['close'])

            # Tính mức thay đổi giá nến hiện tại và so với nến trước
            change_current = ((c - o) / o) * 100.0 if o > 0 else 0.0
            change_prev = ((c - prev_c) / prev_c) * 100.0 if prev_c > 0 else 0.0
            worst_change = min(change_current, change_prev)

            threshold = -abs(self.config.btc_crash_threshold_percent)
            if worst_change <= threshold:
                msg = f"CẢNH BÁO SỤP ĐỔ: BTC sụt giảm mạnh {worst_change:.2f}% (ngưỡng: {threshold:.2f}%)!"
                logger.warning(f"🚨 [BTC FLASH-CRASH TRIGGERED] {msg}")
                return True, worst_change, msg

            return False, worst_change, f"BTC ổn định ({worst_change:+.2f}%)"
        except Exception as e:
            logger.debug(f"Lỗi kiểm tra nến BTC: {e}")
            return False, 0.0, str(e)

    def scan_for_setups(self, max_pairs: int = 25) -> List[Dict[str, Any]]:
        """
        Quét các cặp thanh khoản để tìm setup vào lệnh:
        Trả về danh sách các cơ hội có Signal.BUY hoặc Signal.SELL.
        Tự động chặn lệnh BUY trên altcoin nếu phát hiện BTC đang sụt giảm khẩn cấp.
        Tự động áp dụng Bộ lọc Chế độ Xu hướng Vĩ mô Bitcoin (BTC Market Regime Alignment).
        """
        # 1. Nhận diện Chế độ Xu hướng Vĩ mô Bitcoin
        btc_regime, btc_regime_desc, btc_regime_info = self.get_btc_regime()
        self.last_btc_regime = btc_regime
        self.last_btc_regime_desc = btc_regime_desc
        self.last_btc_regime_info = btc_regime_info
        direction_mode = getattr(self.config, "trade_direction", "AUTO").upper()
        logger.info(f"🌐 [BTC REGIME SHIELD] {btc_regime_desc} | Chiều đánh cấu hình: {direction_mode}")

        # 2. Kiểm tra Flash-Crash khẩn cấp nến 15m
        btc_crashing, btc_change, crash_msg = self.check_btc_flash_crash()
        if btc_crashing:
            logger.warning(f"🛡️ [QUỸ BẢO VỆ VỐN] {crash_msg} -> Tạm thời LOẠI BỎ toàn bộ tín hiệu BUY Altcoin!")

        if self.config.trading_mode == "BLUECHIP_ONLY":
            symbols_to_scan = [s.strip() for s in self.config.bluechip_symbols.split(",") if s.strip()]
        elif self.config.enable_scanner:
            symbols_to_scan = self.get_liquid_symbols(max_pairs=self.config.max_scan_pairs)
        else:
            symbols_to_scan = self.config.symbol_list

        opportunities = []
        radar_items = []

        for symbol in symbols_to_scan:
            try:
                # 1. Kiểm tra Funding Rate (nếu quá cao thì bỏ qua)
                funding_rate = self.client.get_funding_rate(symbol)
                if abs(funding_rate) > self.config.max_funding_rate:
                    logger.debug(f"Bỏ qua {symbol} do funding rate cao ({funding_rate:.4%})")
                    continue

                # 2. Lấy dữ liệu nến HTF và LTF
                htf_df = self.client.get_klines_df(symbol, interval=self.config.htf, limit=120)
                time.sleep(0.04)  # Tránh dồn rate limit
                ltf_df = self.client.get_klines_df(symbol, interval=self.config.ltf, limit=80)
                time.sleep(0.04)

                if htf_df.empty or ltf_df.empty:
                    continue

                # 3. Chạy chiến lược theo cấu hình Multi-Strategy Engine
                strat_mode = getattr(self.config, "active_strategy", "AUTO_DYNAMIC").upper()
                strategy_tag = "Pullback"

                if strat_mode == "BREAKOUT":
                    analysis = self.breakout_strategy.generate_signal(htf_df, ltf_df)
                    strategy_tag = "Breakout"
                elif strat_mode == "MEAN_REVERSION":
                    analysis = self.mean_reversion_strategy.generate_signal(htf_df, ltf_df)
                    strategy_tag = "Sideway"
                elif strat_mode == "TREND_PULLBACK":
                    analysis = self.pullback_strategy.generate_signal(htf_df, ltf_df)
                    strategy_tag = "Pullback"
                else:
                    # AUTO_DYNAMIC: Tự động điều phối theo nhịp thị trường
                    analysis = self.pullback_strategy.generate_signal(htf_df, ltf_df)
                    strategy_tag = "Pullback"
                    # Nếu đang Sideway (ADX < adx_min) và Pullback không có lệnh, kích hoạt Mean Reversion
                    ind = analysis.get("indicators", {})
                    adx_tmp = float(ind.get("htf_adx", 20.0))
                    if analysis["signal"] == Signal.HOLD and adx_tmp < self.config.adx_min:
                        mr_res = self.mean_reversion_strategy.generate_signal(htf_df, ltf_df)
                        if mr_res["signal"] in [Signal.BUY, Signal.SELL]:
                            analysis = mr_res
                            strategy_tag = "Sideway"
                    # Kiểm tra thêm đột phá khối lượng (Breakout)
                    if analysis["signal"] == Signal.HOLD:
                        bo_res = self.breakout_strategy.generate_signal(htf_df, ltf_df)
                        if bo_res["signal"] in [Signal.BUY, Signal.SELL]:
                            analysis = bo_res
                            strategy_tag = "Breakout"

                sig = analysis["signal"]
                cur_price = float(ltf_df.iloc[-1]['close'])
                ind = analysis.get("indicators", {})
                rsi_val = float(ind.get("ltf_rsi", ind.get("rsi", 50.0)))
                adx_val = float(ind.get("htf_adx", 20.0))
                trend_str = "Uptrend 📈" if ind.get("htf_trend") == "UP" else ("Downtrend 📉" if ind.get("htf_trend") == "DOWN" else "Sideway ⏸️")

                # Cập nhật cache nến cho Khiên tương quan và Tính toán tham số thích ứng (Bản 5.0)
                self.correlation_shield.update_price_cache(symbol, ltf_df['close'].tolist())
                adaptive = StrategyAutoTuner.calculate_adaptive_params(symbol, ltf_df)

                radar_status = f"Đang chờ ({strategy_tag})"
                if sig in [Signal.BUY, Signal.SELL]:
                    radar_status = f"{strategy_tag} {sig.value if hasattr(sig, 'value') else sig} 🎯"
                elif adx_val < self.config.adx_min and strat_mode == "TREND_PULLBACK":
                    radar_status = f"ADX yếu ({adx_val:.1f} < {self.config.adx_min})"

                radar_items.append({
                    "symbol": symbol,
                    "price": cur_price,
                    "trend": trend_str,
                    "rsi": round(rsi_val, 1),
                    "adx": round(adx_val, 1),
                    "funding_rate": round(funding_rate * 100, 4),
                    "signal": sig.value if hasattr(sig, "value") else str(sig),
                    "status": radar_status,
                    "volatility": adaptive.get("volatility_level", "NORMAL"),
                    "volatility_score": adaptive.get("volatility_score", 50),
                    "updated_at": datetime.now(VIETNAM_TZ).strftime("%H:%M:%S (VN)")
                })
                self.last_scanned_radar = list(radar_items)

                if sig in [Signal.BUY, Signal.SELL]:
                    # 1. Kiểm tra cấu hình chiều đánh cố định (TRADE_DIRECTION)
                    direction = getattr(self.config, "trade_direction", "AUTO").upper()
                    if direction == "LONG_ONLY" and sig == Signal.SELL:
                        logger.info(f"🚫 [CHẶN SHORT {symbol}] Bỏ qua lệnh SELL vì cấu hình TRADE_DIRECTION = LONG_ONLY")
                        continue
                    if direction == "SHORT_ONLY" and sig == Signal.BUY:
                        logger.info(f"🚫 [CHẶN LONG {symbol}] Bỏ qua lệnh BUY vì cấu hình TRADE_DIRECTION = SHORT_ONLY")
                        continue

                    # 2. Bộ Lọc Xu Hướng Chế Độ Thị Trường Bitcoin (BTC Regime Alignment Filter)
                    if getattr(self.config, "enable_btc_regime_filter", True) and direction == "AUTO":
                        if btc_regime == "BULL" and sig == Signal.SELL:
                            logger.warning(f"🚫 [CHẶN SHORT {symbol}] BTC đang UPTREND mạnh ({btc_regime_desc}) -> Khóa 100% lệnh SELL để chống Short Squeeze!")
                            continue
                        if btc_regime == "BEAR" and sig == Signal.BUY:
                            logger.warning(f"🚫 [CHẶN LONG {symbol}] BTC đang DOWNTREND mạnh ({btc_regime_desc}) -> Khóa 100% lệnh BUY để tránh bắt dao rơi!")
                            continue

                    # 3. Nếu BTC đang Flash-Crash, chặn toàn bộ lệnh BUY trên Altcoin (tránh bắt dao rơi)
                    if btc_crashing and sig == Signal.BUY and symbol != "BTCUSDT":
                        logger.info(f"🚫 [BỎ QUA BUY {symbol}] Đã chặn lệnh LONG do BTC đang sụt giảm bất thường ({btc_change:.2f}%)")
                        continue

                    # 4. Kiểm tra Khiên Quản Trị Rủi Ro Tương Quan (Portfolio Correlation Shield - Bản 5.0)
                    active_positions = getattr(self.config, "active_positions", {})
                    corr_check = self.correlation_shield.check_correlation_risk(
                        candidate_symbol=symbol,
                        candidate_side=sig.value if hasattr(sig, "value") else str(sig),
                        candidate_closes=ltf_df['close'].tolist(),
                        active_positions=active_positions
                    )
                    if not corr_check.get("is_safe", True):
                        logger.warning(corr_check.get("warning_message"))
                        continue

                    opportunities.append({
                        "symbol": symbol,
                        "signal": sig,
                        "entry_price": analysis["entry_price"],
                        "stop_loss": analysis["stop_loss"],
                        "take_profit": analysis["take_profit"],
                        "reason": analysis["reason"],
                        "funding_rate": funding_rate,
                        "indicators": analysis.get("indicators", {}),
                        "df": ltf_df,
                        "adaptive": adaptive
                    })
                    logger.info(f"==> TÌM THẤY SETUP: {symbol} - {sig} @ {analysis['entry_price']} [Vol: {adaptive['volatility_level']}]")
            except Exception as e:
                logger.debug(f"Lỗi khi quét {symbol}: {e}")
                continue

        # Sắp xếp cơ hội vào lệnh theo Trọng số tối ưu từ AI Self-Training Engine
        try:
            from core.ai_trade_trainer import AITradeTrainer
            trainer = AITradeTrainer()
            opportunities.sort(key=lambda op: trainer.get_coin_bias_weight(op.get("symbol", "")), reverse=True)
        except Exception as e:
            logger.debug(f"Lỗi sắp xếp cơ hội theo AI conviction: {e}")

        self.last_scanned_radar = radar_items
        return opportunities

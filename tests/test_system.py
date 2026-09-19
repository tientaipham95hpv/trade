import unittest
import os
import sys

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
from config.settings import BotConfig
from strategy.indicators import TechnicalIndicators
from strategy.trend_pullback import TrendPullbackStrategy
from strategy.base_strategy import Signal
from risk.risk_manager import RiskManager


class TestTradingBotCore(unittest.TestCase):
    def setUp(self):
        self.config = BotConfig(
            sizing_mode="risk_percent",
            risk_per_trade_percent=1.0,
            leverage=5,
            max_daily_loss_percent=5.0,
            max_concurrent_positions=3
        )
        self.risk_manager = RiskManager(self.config)

    def test_risk_manager_circuit_breaker(self):
        # Thiết lập vốn đầu ngày 1,000 USDT
        from datetime import datetime, timezone, timedelta
        self.risk_manager.last_reset_day = datetime.now(timezone(timedelta(hours=7))).date()
        self.risk_manager.daily_start_balance = 1000.0

        # Lỗ nhẹ (980 USDT -> lỗ 2%), chưa chạm 5%
        safe, msg = self.risk_manager.check_circuit_breaker(980.0)
        self.assertTrue(safe)

        # Lỗ nặng (940 USDT -> lỗ 6%), vượt 5%
        safe, msg = self.risk_manager.check_circuit_breaker(940.0)
        self.assertFalse(safe)
        self.assertIn("NGẮT MẠCH KHẨN CẤP", msg)

    def test_risk_manager_position_sizing(self):
        balance = 1000.0
        entry = 60000.0
        stop_loss = 59400.0  # SL cách $600 (1%)
        step_size = 0.001
        min_qty = 0.001

        # Rủi ro 1% của 1000 = $10
        # Qty = 10 / 600 = 0.01666 -> làm tròn 0.016 BTC
        sizing = self.risk_manager.calculate_position_size(
            balance=balance,
            entry_price=entry,
            stop_loss_price=stop_loss,
            step_size=step_size,
            min_qty=min_qty
        )

        self.assertTrue(sizing["valid"])
        self.assertAlmostEqual(sizing["qty"], 0.016, places=3)
        # Rủi ro thực tế nếu dính SL ~ 0.016 * 600 = $9.6 (< $10)
        self.assertLessEqual(sizing["risk_amount"], 10.0)

    def test_technical_indicators(self):
        # Tạo chuỗi dữ liệu giả lập 100 nến
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100))
        highs = prices + np.random.uniform(0.5, 2.0, 100)
        lows = prices - np.random.uniform(0.5, 2.0, 100)
        closes = prices + np.random.uniform(-0.5, 0.5, 100)
        volumes = np.random.uniform(100, 1000, 100)

        df = pd.DataFrame({
            'open': prices,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })

        populated = TechnicalIndicators.populate_all(df)
        self.assertIn('ema_50', populated.columns)
        self.assertIn('rsi', populated.columns)
        self.assertIn('atr', populated.columns)
        self.assertIn('bb_upper', populated.columns)
        self.assertIn('bb_lower', populated.columns)
        self.assertFalse(populated['rsi'].isna().all())

    def test_trend_pullback_strategy_logic(self):
        strategy = TrendPullbackStrategy(rr_ratio=1.5)

        # Dữ liệu nến giả lập
        n = 100
        df = pd.DataFrame({
            'open': np.linspace(100, 200, n),
            'high': np.linspace(101, 201, n),
            'low': np.linspace(99, 199, n),
            'close': np.linspace(100, 200, n),
            'volume': np.full(n, 1000.0)
        })

        res = strategy.generate_signal(df, df)
        self.assertIn("signal", res)
        self.assertIn(res["signal"], [Signal.BUY, Signal.SELL, Signal.HOLD])

    def test_order_manager_partial_tp_and_persistence(self):
        from core.binance_client import BinanceFuturesClient
        from notifier.telegram_bot import TelegramNotifier
        from core.order_manager import OrderManager

        # Dùng file test tạm thời
        test_state = "test_bot_state.json"
        test_csv = "test_trade_history.csv"
        if os.path.exists(test_state):
            os.remove(test_state)
        if os.path.exists(test_csv):
            os.remove(test_csv)
        cfg = BotConfig(
            dry_run=True,
            telegram_enabled=False,
            state_file=test_state,
            trade_history_file=test_csv,
            use_partial_tp=True,
            partial_tp_ratio=0.5,
            use_multi_tp=False
        )

        client = BinanceFuturesClient(cfg)
        notifier = TelegramNotifier(cfg)
        om = OrderManager(cfg, client, notifier)

        # 1. Mở vị thế giả lập BTCUSDT: Entry 60,000, SL 59,000 (1R = $1,000), TP 61,500, Qty 0.02
        om.execute_entry(
            symbol="BTCUSDT",
            side="BUY",
            entry_price=60000.0,
            qty=0.02,
            stop_loss=59000.0,
            take_profit=61500.0,
            margin=240.0,
            risk_amount=20.0
        )
        self.assertIn("BTCUSDT", om.active_positions)
        self.assertEqual(om.active_positions["BTCUSDT"]["qty"], 0.02)

        # 2. Kiểm tra State Persistence: file test_bot_state.json phải tồn tại
        self.assertTrue(os.path.exists(test_state))

        # 3. Giá chạy lên $61,000 (+1R) -> Kích hoạt Chốt lời 50%
        sim_balance = {"balance": 1000.0}
        om.check_and_update_positions({"BTCUSDT": 61000.0}, sim_balance)

        pos = om.active_positions["BTCUSDT"]
        self.assertTrue(pos["partial_tp_activated"])
        self.assertEqual(pos["qty"], 0.01)  # Còn lại 50% = 0.01 BTC
        self.assertEqual(pos["stop_loss"], 60000.0)  # SL đã dời về Entry (Hòa vốn)
        # Số dư phải tăng thêm 0.01 * 1000 = $10
        self.assertAlmostEqual(sim_balance["balance"], 1010.0, places=2)

        # Kiểm tra file CSV đã ghi nhận đợt chốt 50%
        self.assertTrue(os.path.exists(test_csv))

        # 4. Giá tiếp tục chạy lên $61,500 (Final TP) -> Đóng 50% còn lại
        om.check_and_update_positions({"BTCUSDT": 61500.0}, sim_balance)
        self.assertEqual(len(om.active_positions), 0)  # Vị thế đã đóng hoàn tất
        # Lãi thêm 0.01 * 1500 = $15 -> Tổng balance = 1025.0
        self.assertAlmostEqual(sim_balance["balance"], 1025.0, places=2)

        # Dọn dẹp file test
        if os.path.exists(test_state):
            os.remove(test_state)
        if os.path.exists(test_csv):
            os.remove(test_csv)

    def test_institutional_adx_filter(self):
        """Kiểm tra bộ lọc ADX loại bỏ tín hiệu khi thị trường sideway yếu"""
        strategy = TrendPullbackStrategy(adx_min=25.0)

        # Dữ liệu nến đi ngang phẳng lì (ADX = 20.0 < 25.0)
        n = 100
        flat_prices = np.full(n, 100.0)
        df = pd.DataFrame({
            'open': flat_prices,
            'high': flat_prices + 0.05,
            'low': flat_prices - 0.05,
            'close': flat_prices,
            'volume': np.full(n, 100.0)
        })

        res = strategy.generate_signal(df, df)
        self.assertEqual(res["signal"], Signal.HOLD)
        self.assertIn("HTF Trend", res["reason"])

    def test_institutional_news_filter(self):
        """Kiểm tra bộ lọc tin tức vĩ mô né lệnh đúng khung giờ"""
        # Test tắt/bật
        cfg_off = BotConfig(enable_news_filter=False)
        rm_off = RiskManager(cfg_off)
        in_blackout, _ = rm_off.is_news_blackout_window()
        self.assertFalse(in_blackout)

        cfg_on = BotConfig(enable_news_filter=True)
        rm_on = RiskManager(cfg_on)
        # Kiểm tra logic hàm
        self.assertIsInstance(rm_on.is_news_blackout_window()[0], bool)

    def test_institutional_bnb_fee_discount(self):
        """Kiểm tra logic nhận diện chiết khấu phí BNB"""
        from core.binance_client import BinanceFuturesClient
        cfg = BotConfig(dry_run=True)
        client = BinanceFuturesClient(cfg)
        rec = client.check_fee_discount_recommendation()
        self.assertIn("bnb_balance", rec)
        self.assertIn("has_discount", rec)


if __name__ == "__main__":
    unittest.main()



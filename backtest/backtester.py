import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from strategy.indicators import TechnicalIndicators
from strategy.base_strategy import Signal

logger = logging.getLogger("Backtester")


class FuturesBacktester:
    """
    Bộ máy Backtest Chiến lược Futures:
    - Giả lập đa khung thời gian HTF (1H) và LTF (15m).
    - Tính trượt giá và phí giao dịch (Taker Fee 0.05%).
    - Mô phỏng Dynamic Position Sizing (Risk % per trade).
    - Đo lường Winrate, Profit Factor, Max Drawdown.
    """

    def __init__(
        self,
        initial_balance: float = 1000.0,
        risk_percent: float = 1.0,
        rr_ratio: float = 1.5,
        fee_rate: float = 0.0005,  # 0.05% Taker Fee
        use_breakeven: bool = True
    ):
        self.initial_balance = initial_balance
        self.risk_percent = risk_percent
        self.rr_ratio = rr_ratio
        self.fee_rate = fee_rate
        self.use_breakeven = use_breakeven

    def run(self, htf_df: pd.DataFrame, ltf_df: pd.DataFrame, strategy_name: str = "AUTO_DYNAMIC") -> Dict[str, Any]:
        """Chạy backtest trên cặp dữ liệu HTF và LTF kèm đa chiến lược"""
        if htf_df.empty or ltf_df.empty or len(ltf_df) < 80:
            return {"error": "Dữ liệu nến không đủ để backtest"}

        # 1. Tính toán chỉ báo
        htf = TechnicalIndicators.populate_all(htf_df.copy())
        ltf = TechnicalIndicators.populate_all(ltf_df.copy())

        # Gộp xu hướng HTF sang LTF theo open_time
        htf_cols = ['open_time', 'ema_50', 'ema_200', 'close']
        if 'close_time' in htf.columns:
            htf_cols.append('close_time')
        for col in ['ema_50', 'ema_200']:
            if col not in htf.columns:
                htf[col] = htf['close']

        htf_sub = htf[htf_cols].rename(
            columns={'ema_50': 'htf_ema50', 'ema_200': 'htf_ema200', 'close': 'htf_close'}
        )

        ltf = ltf.sort_values('open_time').reset_index(drop=True)
        htf_sub = htf_sub.sort_values('open_time').reset_index(drop=True)

        if 'close_time' in ltf.columns:
            ltf['ltf_close_time'] = ltf['close_time']
        else:
            ltf['ltf_close_time'] = ltf['open_time'] + pd.Timedelta(minutes=15)

        if 'close_time' in htf_sub.columns:
            htf_sub['htf_close_time'] = htf_sub['close_time']
        else:
            htf_sub['htf_close_time'] = htf_sub['open_time'] + pd.Timedelta(hours=1)

        merged = pd.merge_asof(
            ltf.sort_values('ltf_close_time'),
            htf_sub.sort_values('htf_close_time'),
            left_on='ltf_close_time',
            right_on='htf_close_time',
            direction='backward',
            suffixes=('', '_htf_dup')
        )
        if 'ltf_close_time' in merged.columns:
            merged.drop(columns=['ltf_close_time'], inplace=True)
        if 'htf_close_time' in merged.columns:
            merged.drop(columns=['htf_close_time'], inplace=True)

        balance = self.initial_balance
        peak_balance = balance
        max_drawdown_pct = 0.0

        trades: List[Dict[str, Any]] = []
        equity_curve: List[Dict[str, Any]] = []
        in_trade = False
        current_pos = None

        first_time = str(merged.iloc[60]["open_time"])
        first_label = first_time.split()[0] if " " in first_time else first_time
        equity_curve.append({"time": first_label, "balance": round(balance, 2)})

        # Bỏ qua 60 nến đầu để các chỉ báo ổn định
        for i in range(60, len(merged)):
            row = merged.iloc[i]
            prev_row = merged.iloc[i - 1]

            # Kiểm tra drawdown tài khoản
            if balance > peak_balance:
                peak_balance = balance
            dd = peak_balance - balance
            dd_pct = (dd / peak_balance) * 100.0 if peak_balance > 0 else 0.0
            if dd_pct > max_drawdown_pct:
                max_drawdown_pct = dd_pct

            # Nếu đang có vị thế mở, kiểm tra nến này có chạm SL/TP không
            if in_trade and current_pos is not None:
                side = current_pos["side"]
                entry = current_pos["entry_price"]
                sl = current_pos["stop_loss"]
                tp = current_pos["take_profit"]
                qty = current_pos["qty"]
                high = float(row["high"])
                low = float(row["low"])

                # Dời SL về hòa vốn nếu đạt 1R
                initial_risk_dist = abs(entry - current_pos["initial_sl"])
                if self.use_breakeven and not current_pos["breakeven_activated"]:
                    if side == "BUY" and high >= entry + initial_risk_dist:
                        current_pos["stop_loss"] = entry
                        current_pos["breakeven_activated"] = True
                    elif side == "SELL" and low <= entry - initial_risk_dist:
                        current_pos["stop_loss"] = entry
                        current_pos["breakeven_activated"] = True

                closed = False
                exit_price = 0.0
                exit_reason = ""

                if side == "BUY":
                    if low <= current_pos["stop_loss"]:
                        closed = True
                        exit_price = current_pos["stop_loss"]
                        exit_reason = "STOP_LOSS"
                    elif high >= tp:
                        closed = True
                        exit_price = tp
                        exit_reason = "TAKE_PROFIT"
                else:  # SELL
                    if high >= current_pos["stop_loss"]:
                        closed = True
                        exit_price = current_pos["stop_loss"]
                        exit_reason = "STOP_LOSS"
                    elif low <= tp:
                        closed = True
                        exit_price = tp
                        exit_reason = "TAKE_PROFIT"

                if closed:
                    # Tính PnL và trừ phí sàn
                    if side == "BUY":
                        gross_pnl = (exit_price - entry) * qty
                    else:
                        gross_pnl = (entry - exit_price) * qty

                    fee = (entry * qty * self.fee_rate) + (exit_price * qty * self.fee_rate)
                    net_pnl = gross_pnl - fee
                    balance += net_pnl

                    t_time = str(row["open_time"])
                    t_label = t_time.split()[0] if " " in t_time else t_time
                    trades.append({
                        "side": side,
                        "entry_time": str(current_pos["entry_time"]),
                        "exit_time": t_time,
                        "entry_price": round(entry, 4),
                        "exit_price": round(exit_price, 4),
                        "exit_reason": exit_reason,
                        "net_pnl": round(net_pnl, 2),
                        "balance_after": round(balance, 2)
                    })
                    equity_curve.append({"time": t_label, "balance": round(balance, 2)})
                    in_trade = False
                    current_pos = None

            # Nếu chưa có vị thế, tìm tín hiệu vào lệnh theo chiến lược được chọn
            if not in_trade:
                cur_price = float(row["close"])
                atr = float(row.get("atr", cur_price * 0.01))
                adx = float(row.get("adx", 25.0))
                strat = strategy_name.upper()

                use_pullback = (strat in ["AUTO_DYNAMIC", "TREND_PULLBACK"] and (strat != "AUTO_DYNAMIC" or adx >= 20.0))
                use_mean_rev = (strat == "MEAN_REVERSION" or (strat == "AUTO_DYNAMIC" and adx < 20.0))
                use_breakout = (strat == "BREAKOUT")

                long_cond = False
                short_cond = False

                # 1. Chi nhánh Trend Pullback
                if use_pullback:
                    htf_uptrend = (row["htf_ema50"] > row["htf_ema200"]) and (row["htf_close"] > row["htf_ema50"])
                    htf_downtrend = (row["htf_ema50"] < row["htf_ema200"]) and (row["htf_close"] < row["htf_ema50"])
                    long_cond = (
                        htf_uptrend and
                        (prev_row["low"] <= prev_row.get("bb_lower", 0) or row["low"] <= row.get("bb_lower", 0) or row.get("rsi", 50) < 40) and
                        (row["close"] >= row["open"] or row.get("rsi", 50) > prev_row.get("rsi", 50))
                    )
                    short_cond = (
                        htf_downtrend and
                        (prev_row["high"] >= prev_row.get("bb_upper", 999999) or row["high"] >= row.get("bb_upper", 999999) or row.get("rsi", 50) > 60) and
                        (row["close"] <= row["open"] or row.get("rsi", 50) < prev_row.get("rsi", 50))
                    )

                # 2. Chi nhánh Mean Reversion (Biên Bollinger Bands khi thị trường Sideway)
                elif use_mean_rev:
                    long_cond = (row["low"] <= row.get("bb_lower", 0)) and (row.get("rsi", 50) < 32) and (row["close"] > row["open"])
                    short_cond = (row["high"] >= row.get("bb_upper", 999999)) and (row.get("rsi", 50) > 68) and (row["close"] < row["open"])

                # 3. Chi nhánh Breakout Volume
                elif use_breakout:
                    rolling_high = merged.iloc[max(0, i-20):i]['high'].max()
                    rolling_low = merged.iloc[max(0, i-20):i]['low'].min()
                    vol_sma = merged.iloc[max(0, i-20):i]['volume'].mean()
                    cur_vol = float(row.get('volume', 0))
                    vol_surge = (cur_vol >= vol_sma * 1.5) if vol_sma > 0 else True
                    long_cond = (cur_price > rolling_high) and vol_surge
                    short_cond = (cur_price < rolling_low) and vol_surge

                if long_cond:
                    recent_low = float(merged.iloc[max(0, i-5):i+1]['low'].min())
                    sl_dist = max(cur_price - recent_low, atr * 1.5)
                    sl_dist = max(sl_dist, cur_price * 0.005)
                    sl_dist = min(sl_dist, cur_price * 0.05)
                    sl = cur_price - sl_dist
                    tp = cur_price + (sl_dist * self.rr_ratio)

                    risk_dollars = balance * (self.risk_percent / 100.0)
                    qty = risk_dollars / sl_dist if sl_dist > 0 else 0.01

                    current_pos = {
                        "side": "BUY",
                        "entry_price": cur_price,
                        "stop_loss": sl,
                        "initial_sl": sl,
                        "take_profit": tp,
                        "qty": qty,
                        "entry_time": row["open_time"],
                        "breakeven_activated": False
                    }
                    in_trade = True

                elif short_cond:
                    recent_high = float(merged.iloc[max(0, i-5):i+1]['high'].max())
                    sl_dist = max(recent_high - cur_price, atr * 1.5)
                    sl_dist = max(sl_dist, cur_price * 0.005)
                    sl_dist = min(sl_dist, cur_price * 0.05)
                    sl = cur_price + sl_dist
                    tp = cur_price - (sl_dist * self.rr_ratio)

                    risk_dollars = balance * (self.risk_percent / 100.0)
                    qty = risk_dollars / sl_dist if sl_dist > 0 else 0.01

                    current_pos = {
                        "side": "SELL",
                        "entry_price": cur_price,
                        "stop_loss": sl,
                        "initial_sl": sl,
                        "take_profit": tp,
                        "qty": qty,
                        "entry_time": row["open_time"],
                        "breakeven_activated": False
                    }
                    in_trade = True

        # Đảm bảo điểm kết thúc cho Equity Curve
        last_time = str(merged.iloc[-1]["open_time"])
        last_label = last_time.split()[0] if " " in last_time else last_time
        if not equity_curve or equity_curve[-1]["time"] != last_label:
            equity_curve.append({"time": last_label, "balance": round(balance, 2)})

        total_trades = len(trades)
        if total_trades == 0:
            return {
                "initial_balance": self.initial_balance,
                "final_balance": round(balance, 2),
                "net_profit": 0.0,
                "net_profit_percent": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_percent": 0.0,
                "equity_curve": equity_curve,
                "trades": []
            }

        winning_trades = [t for t in trades if t["net_pnl"] > 0]
        losing_trades = [t for t in trades if t["net_pnl"] < 0]
        gross_profit = sum(t["net_pnl"] for t in winning_trades)
        gross_loss = abs(sum(t["net_pnl"] for t in losing_trades))

        win_rate = (len(winning_trades) / total_trades) * 100.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        net_profit = balance - self.initial_balance
        net_profit_pct = (net_profit / self.initial_balance) * 100.0

        return {
            "initial_balance": self.initial_balance,
            "final_balance": round(balance, 2),
            "net_profit": round(net_profit, 2),
            "net_profit_percent": round(net_profit_pct, 2),
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_percent": round(max_drawdown_pct, 2),
            "equity_curve": equity_curve,
            "trades": trades[-20:]  # 20 lệnh gần nhất
        }

    @classmethod
    def run_simulation_for_symbol(
        cls,
        client: Any,
        symbol: str = "BTCUSDT",
        strategy_name: str = "AUTO_DYNAMIC",
        days: int = 14,
        timeframe: str = "15m",
        initial_balance: float = 1000.0,
        risk_percent: float = 1.0,
        rr_ratio: float = 1.5
    ) -> Dict[str, Any]:
        """Phương thức tĩnh chạy toàn trình mô phỏng kiểm thử trên dữ liệu Binance"""
        try:
            limit_ltf = min(1500, max(150, days * 96))
            limit_htf = min(500, max(80, days * 24))

            ltf_df = client.get_klines_df(symbol, interval=timeframe, limit=limit_ltf)
            htf_df = client.get_klines_df(symbol, interval="1h", limit=limit_htf)

            if ltf_df.empty or len(ltf_df) < 80:
                return {"success": False, "message": f"Không tải đủ dữ liệu nến lịch sử cho {symbol}"}

            tester = cls(
                initial_balance=initial_balance,
                risk_percent=risk_percent,
                rr_ratio=rr_ratio
            )
            res = tester.run(htf_df, ltf_df, strategy_name=strategy_name)
            if "error" in res:
                return {"success": False, "message": res["error"]}

            res["success"] = True
            res["symbol"] = symbol
            res["strategy"] = strategy_name
            res["days"] = days
            res["timeframe"] = timeframe
            return res
        except Exception as e:
            logger.error("Lỗi khi chạy backtest cho %s: %s", symbol, e)
            return {"success": False, "message": f"Lỗi hệ thống backtest: {e}"}

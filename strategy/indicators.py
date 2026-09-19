import numpy as np
import pandas as pd


class TechnicalIndicators:
    """
    Bộ tính toán các chỉ báo kỹ thuật cốt lõi: EMA, RSI, Bollinger Bands, ATR, MACD
    Đảm bảo tốc độ tính toán nhanh và không bị phụ thuộc quá mức vào thư viện ngoài.
    """

    @staticmethod
    def calculate_ema(series: pd.Series, period: int) -> pd.Series:
        """Tính Exponential Moving Average (EMA)"""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Tính Relative Strength Index (RSI) chuẩn Wilder"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0.0)).copy()
        loss = (-delta.where(delta < 0, 0.0)).copy()

        # Wilder's Smoothing
        avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi.fillna(50.0)

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Tính Average True Range (ATR) để xác định độ biến động và đặt SL/TP"""
        high = df['high']
        low = df['low']
        close = df['close']
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        return atr

    @staticmethod
    def calculate_bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0):
        """Tính dải Bollinger Bands (Middle, Upper, Lower)"""
        sma = series.rolling(window=period).mean()
        rstd = series.rolling(window=period).std()
        upper = sma + (rstd * std_dev)
        lower = sma - (rstd * std_dev)
        return sma, upper, lower

    @staticmethod
    def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """Tính MACD, MACD Signal và MACD Histogram"""
        fast_ema = series.ewm(span=fast, adjust=False).mean()
        slow_ema = series.ewm(span=slow, adjust=False).mean()
        macd = fast_ema - slow_ema
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist

    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Tính Average Directional Index (ADX) để đo sức mạnh xu hướng"""
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        up_move = high.diff()
        down_move = -low.diff()

        pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        tr_smooth = pd.Series(tr).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        pos_dm_smooth = pd.Series(pos_dm, index=df.index).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        neg_dm_smooth = pd.Series(neg_dm, index=df.index).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

        pos_di = 100.0 * (pos_dm_smooth / tr_smooth.replace(0, np.nan))
        neg_di = 100.0 * (neg_dm_smooth / tr_smooth.replace(0, np.nan))

        dx = 100.0 * (abs(pos_di - neg_di) / (pos_di + neg_di).replace(0, np.nan))
        adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        return adx.fillna(20.0)

    @classmethod
    def populate_all(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Tính toán và gán toàn bộ chỉ báo vào DataFrame klines"""
        if df.empty or len(df) < 50:
            return df

        df = df.copy()
        # Đảm bảo các cột có kiểu float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df[col].astype(float)

        # EMA Trend
        df['ema_50'] = cls.calculate_ema(df['close'], 50)
        df['ema_200'] = cls.calculate_ema(df['close'], 200) if len(df) >= 200 else cls.calculate_ema(df['close'], len(df) // 2)

        # RSI
        df['rsi'] = cls.calculate_rsi(df['close'], 14)

        # ATR
        df['atr'] = cls.calculate_atr(df, 14)

        # ADX (Sức mạnh xu hướng)
        df['adx'] = cls.calculate_adx(df, 14)

        # Bollinger Bands
        df['bb_mid'], df['bb_upper'], df['bb_lower'] = cls.calculate_bollinger_bands(df['close'], 20, 2.0)

        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = cls.calculate_macd(df['close'], 12, 26, 9)

        return df


# Alias tương thích ngược
Indicators = TechnicalIndicators


import time
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import utils.network_fix

from config.settings import BotConfig


class BinanceAPIException(Exception):
    """Compatibility exception without importing the mutation-capable Binance SDK."""


class _PublicBinanceTransport:
    """Credential-free public Futures transport exposed through the read-only facade."""

    def __init__(self, testnet: bool = False):
        self.base = "https://testnet.binancefuture.com/fapi/v1" if testnet else "https://fapi.binance.com/fapi/v1"

    def _get(self, path: str, **params):
        response = utils.network_fix.http_session.get(f"{self.base}/{path}", params=params, timeout=8)
        response.raise_for_status()
        return response.json()

    def futures_ping(self):
        return self._get("ping")

    def futures_symbol_ticker(self, **params):
        return self._get("ticker/price", **params)

    def futures_exchange_info(self):
        return self._get("exchangeInfo")

    def futures_klines(self, **params):
        return self._get("klines", **params)

    def futures_historical_klines(self, **params):
        return self.futures_klines(**params)

    def get_exchange_info(self):
        return self.futures_exchange_info()

    def futures_account(self):
        raise RuntimeError("Application has no account credential authority")

    def futures_position_information(self):
        raise RuntimeError("Application has no account credential authority")

    def futures_get_order(self, **params):
        raise RuntimeError("Application has no authenticated order-read authority")

    def futures_get_open_orders(self, **params):
        raise RuntimeError("Application has no authenticated order-read authority")

    def futures_get_open_algo_orders(self, **params):
        raise RuntimeError("Application has no authenticated order-read authority")
logger = logging.getLogger("BinanceClient")


READ_ONLY_SDK_METHODS = {
    "futures_ping",
    "futures_account",
    "futures_position_information",
    "futures_symbol_ticker",
    "futures_get_order",
    "futures_get_open_orders",
    "futures_get_open_algo_orders",
    "futures_exchange_info",
    "futures_klines",
    "futures_historical_klines",
    "get_exchange_info",
}


def _build_read_only_facade_type():
    # The wrapped SDK lives only in a closure; facade instances have no raw-client field or dict.
    import weakref

    wrapped_sdks = weakref.WeakKeyDictionary()

    class _ReadOnlyBinanceSDKFacade:
        __slots__ = ("__weakref__",)

        def __init__(self, raw_sdk: Any):
            wrapped_sdks[self] = raw_sdk

        def __getattr__(self, name: str):
            if name in READ_ONLY_SDK_METHODS:
                return getattr(wrapped_sdks[self], name)
            raise AttributeError(
                f"Operation '{name}' is unavailable on ReadOnlyBinanceSDKFacade: "
                "Application client mutation surface is 0."
            )

        def __dir__(self):
            return sorted(READ_ONLY_SDK_METHODS)

    _ReadOnlyBinanceSDKFacade.__name__ = "ReadOnlyBinanceSDKFacade"
    _ReadOnlyBinanceSDKFacade.__qualname__ = "ReadOnlyBinanceSDKFacade"
    return _ReadOnlyBinanceSDKFacade


ReadOnlyBinanceSDKFacade = _build_read_only_facade_type()


class BinanceFuturesClient:
    """Wrapper kết nối Binance Futures API (REST) - Pure Read-Only for Application processes"""

    def __init__(self, config: BotConfig):
        self.config = config
        self.is_testnet = config.use_testnet
        self.is_dry_run = config.dry_run
        market_data_environment = str(
            getattr(config, "market_data_environment", "PRODUCTION") or "PRODUCTION"
        ).upper()
        self.market_data_environment = market_data_environment
        market_data_testnet = market_data_environment == "TESTNET"

        # The application owns only a credential-free public transport.
        self.client = ReadOnlyBinanceSDKFacade(_PublicBinanceTransport(market_data_testnet))
        self.public_fapi_base = (
            "https://testnet.binancefuture.com/fapi/v1"
            if market_data_testnet
            else "https://fapi.binance.com/fapi/v1"
        )
        # Compatibility alias; application code has no authenticated mutation transport.
        self.fapi_base = self.public_fapi_base

        # Bộ nhớ đệm thông tin symbol (step_size, tick_size, v.v.)
        self._exchange_info_cache: Dict[str, Any] = {}

    def test_connection(self) -> bool:
        """Kiểm tra kết nối tới server Binance"""
        try:
            self.client.futures_ping()
            logger.info(f"Kết nối Binance Futures thành công (Testnet={self.is_testnet})")
            return True
        except Exception as e:
            logger.warning(f"Lỗi ping Binance Futures: {e}")
            return False

    def get_available_balance(self) -> float:
        """Lấy số dư USDT khả dụng trong ví Futures"""
        if self.is_dry_run:
            # Nếu chạy Dry-Run không có API key, gán vốn giả lập 1,000 USDT
            return 1000.0

        try:
            account = self.client.futures_account()
            for asset in account.get("assets", []):
                if asset.get("asset") == "USDT":
                    return float(asset.get("availableBalance", 0.0))
            return 0.0
        except BinanceAPIException as e:
            logger.error(f"Lỗi truy vấn số dư: {e}")
            return 1000.0 if self.is_dry_run else 0.0

    def get_bnb_balance(self) -> float:
        """Lấy số dư BNB trong ví Futures để kiểm tra điều kiện giảm 10% phí sàn"""
        if self.is_dry_run:
            return 0.5  # Giả lập có BNB khi dry-run không API key

        try:
            account = self.client.futures_account()
            for asset in account.get("assets", []):
                if asset.get("asset") == "BNB":
                    return float(asset.get("availableBalance", 0.0))
            return 0.0
        except Exception as e:
            logger.debug(f"Không lấy được số dư BNB: {e}")
            return 0.0

    def check_fee_discount_recommendation(self) -> Dict[str, Any]:
        """Kiểm tra và khuyến nghị người dùng giữ BNB để tối ưu 10% phí giao dịch"""
        bnb = self.get_bnb_balance()
        has_discount = bnb >= 0.02
        if has_discount:
            msg = f"Số dư BNB: {bnb:.4f} BNB (Đủ điều kiện chiết khấu 10% phí Binance Futures)."
            logger.info(f"✨ [BNB FEE DISCOUNT] {msg}")
        else:
            msg = f"Số dư BNB hiện tại: {bnb:.4f} BNB. Khuyến nghị nạp ~0.05 BNB vào ví Futures để tự động được giảm 10% phí giao dịch!"
            logger.warning(f"💡 [TỐI ƯU PHÍ GIAO DỊCH] {msg}")
        return {"bnb_balance": bnb, "has_discount": has_discount, "message": msg}

    def get_open_positions(self, symbol: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Lấy danh sách các vị thế đang mở (positionAmt != 0)"""
        if self.is_dry_run:
            return []

        try:
            positions = self.client.futures_position_information()
            if not isinstance(positions, list):
                return None
            open_pos = []
            for pos in positions:
                if not isinstance(pos, dict):
                    return None
                if "symbol" in pos and "positionAmt" not in pos and "amount" not in pos:
                    # Malformed record without quantity
                    return None
                try:
                    amt = float(pos.get("positionAmt", pos.get("amount", 0.0)))
                except (ValueError, TypeError):
                    return None
                if amt != 0:
                    if symbol and pos.get("symbol") != symbol:
                        continue
                    open_pos.append({
                        "symbol": pos["symbol"],
                        "amount": amt,
                        "positionAmt": amt,
                        "side": "LONG" if amt > 0 else "SHORT",
                        "entry_price": float(pos.get("entryPrice", pos.get("entry_price", 0.0))),
                        "mark_price": float(pos.get("markPrice", pos.get("mark_price", 0.0))),
                        "unRealizedProfit": float(pos.get("unRealizedProfit", 0.0)),
                        "leverage": int(pos.get("leverage", 1)),
                        "liquidationPrice": float(pos.get("liquidationPrice", 0.0))
                    })
            return open_pos
        except BinanceAPIException as e:
            logger.error(f"Lỗi lấy danh sách vị thế: {e}")
            return None
        except Exception as e:
            logger.error(f"Lỗi không xác định lấy danh sách vị thế: {e}")
    def get_symbol_filter_info(self, symbol: str) -> Dict[str, float]:
        """Lấy step_size, min_qty, min_notional, tick_size của symbol"""
        cache = getattr(self, "_exchange_info_cache", None)
        if cache is None:
            self._exchange_info_cache = {}
            cache = self._exchange_info_cache

        if symbol in cache:
            return cache[symbol]

        default_info = {
            "step_size": 0.001,
            "min_qty": 0.001,
            "min_notional": 5.0,
            "tick_size": 0.01
        }

        try:
            # Lấy thông tin từ public production API để đảm bảo tốc độ và độ chính xác
            base_url = getattr(self, "public_fapi_base", "https://fapi.binance.com/fapi/v1")
            url = f"{base_url}/exchangeInfo"
            r = utils.network_fix.http_session.get(url, timeout=8)
            exchange_info = r.json()
            for s in exchange_info.get("symbols", []):
                sym_name = s.get("symbol")
                info = default_info.copy()
                for f in s.get("filters", []):
                    if f.get("filterType") == "LOT_SIZE":
                        info["step_size"] = float(f.get("stepSize", 0.001))
                        info["min_qty"] = float(f.get("minQty", 0.001))
                    elif f.get("filterType") == "MIN_NOTIONAL":
                        info["min_notional"] = float(f.get("notional", 5.0))
                    elif f.get("filterType") == "PRICE_FILTER":
                        info["tick_size"] = float(f.get("tickSize", 0.01))
                self._exchange_info_cache[sym_name] = info

            return self._exchange_info_cache.get(symbol, default_info)
        except Exception as e:
            logger.warning(f"Lỗi lấy symbol filter info: {e}")
            return default_info

    def get_klines_df(self, symbol: str, interval: str, limit: int = 150) -> pd.DataFrame:
        """Lấy dữ liệu nến Klines từ public Binance Futures API và chuẩn hóa thành pandas DataFrame"""
        try:
            # Luôn lấy nến từ fapi.binance.com thật để có dữ liệu chính xác nhất và không bao giờ bị nghẽn Testnet
            url = f"{self.public_fapi_base}/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            res = utils.network_fix.http_session.get(url, params=params, timeout=10)
            if res.status_code != 200:
                logger.error(f"Binance API lỗi HTTP {res.status_code} khi lấy nến {symbol}")
                return pd.DataFrame()

            klines = res.json()
            if not isinstance(klines, list) or len(klines) == 0:
                return pd.DataFrame()

            columns = [
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ]
            df = pd.DataFrame(klines, columns=columns)
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume']:
                df[col] = df[col].astype(float)
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Lỗi lấy dữ liệu nến cho {symbol} ({interval}): {e}")
            return pd.DataFrame()

    def get_all_24h_tickers(self) -> List[Dict[str, Any]]:
        """Lấy dữ liệu 24h ticker của tất cả cặp Futures USDT từ public production API"""
        try:
            url = f"{self.public_fapi_base}/ticker/24hr"
            res = utils.network_fix.http_session.get(url, timeout=10)
            if res.status_code == 200:
                tickers = res.json()
                return [t for t in tickers if t.get("symbol", "").endswith("USDT")]
            return []
        except Exception as e:
            logger.error(f"Lỗi lấy 24h tickers: {e}")
            return []

    def get_funding_rate(self, symbol: str) -> float:
        """Lấy tỷ lệ Funding Rate hiện tại của symbol từ public production API"""
        try:
            url = f"{self.public_fapi_base}/premiumIndex"
            res = utils.network_fix.http_session.get(url, params={"symbol": symbol}, timeout=8)
            if res.status_code == 200:
                info = res.json()
                return float(info.get("lastFundingRate", 0.0))
            return 0.0
        except Exception as e:
            logger.debug(f"Lỗi lấy funding rate {symbol}: {e}")
            return 0.0

    def get_symbol_price(self, symbol: str) -> float:
        """Lấy giá thị trường hiện tại của symbol từ ticker hoặc klines"""
        try:
            if hasattr(self, "client") and self.client:
                if hasattr(self.client, "price"):
                    try:
                        return float(self.client.price)
                    except Exception:
                        pass
                try:
                    res = self.client.futures_symbol_ticker(symbol=symbol)
                    if res and "price" in res:
                        return float(res["price"])
                except Exception:
                    pass
            df = self.get_klines_df(symbol, interval="1m", limit=1)
            if df is not None and not df.empty and "close" in df.columns:
                return float(df["close"].iloc[-1])
            return 0.0
        except Exception as e:
            logger.debug(f"Lỗi lấy giá {symbol}: {e}")
            return 0.0

    def get_order(self, symbol: str, client_order_id: Optional[str] = None, order_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Truy vấn trạng thái lệnh theo client_order_id hoặc order_id"""
        try:
            params: Dict[str, Any] = {"symbol": symbol}
            if client_order_id:
                params["origClientOrderId"] = client_order_id
            if order_id:
                params["orderId"] = order_id
            return self.client.futures_get_order(**params)
        except Exception as e:
            logger.debug(f"Lỗi truy vấn lệnh {symbol} ({client_order_id or order_id}): {e}")
            return None

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lấy danh sách lệnh thường đang chờ khớp trên sàn (R5-014)"""
        try:
            params = {"symbol": symbol} if symbol else {}
            if hasattr(self.client, "futures_get_open_orders"):
                return self.client.futures_get_open_orders(**params)
            return []
        except Exception as e:
            logger.error(f"Lỗi truy vấn futures_get_open_orders: {e}")
            raise

    def get_open_algo_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lấy danh sách lệnh algo/conditional đang chờ khớp trên sàn (R5-014)"""
        try:
            params = {"symbol": symbol} if symbol else {}
            if hasattr(self.client, "futures_get_open_algo_orders"):
                return self.client.futures_get_open_algo_orders(**params)
            return []
        except Exception as e:
            logger.error(f"Lỗi truy vấn futures_get_open_algo_orders: {e}")
            raise


class MarketDataClient:
    """
    Read-Only Market Data Client for Application Surfaces (Strategy, Scanner, Web).
    Contains ZERO mutating methods and requires NO Binance trading credentials.
    """

    def __init__(self, config: Optional[BotConfig] = None):
        self.config = config or BotConfig()
        self._inner = BinanceFuturesClient(self.config)

    def get_klines_df(self, symbol: str, interval: str = "15m", limit: int = 100) -> pd.DataFrame:
        return self._inner.get_klines_df(symbol, interval, limit)

    def get_symbol_price(self, symbol: str) -> Optional[float]:
        return self._inner.get_symbol_price(symbol)

    def get_symbol_filter_info(self, symbol: str) -> Dict[str, Any]:
        return self._inner.get_symbol_filter_info(symbol)

    def get_funding_rate(self, symbol: str) -> float:
        return self._inner.get_funding_rate(symbol)

    def get_top_volume_symbols(self, limit: int = 50) -> List[str]:
        return self._inner.get_top_volume_symbols(limit)

    def test_connection(self) -> bool:
        return self._inner.test_connection()

    def get_available_balance(self) -> float:
        return self._inner.get_available_balance()


PublicMarketDataClient = BinanceFuturesClient

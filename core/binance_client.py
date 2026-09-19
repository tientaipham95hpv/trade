import logging
import socket
import requests
from typing import Dict, Any, List, Optional
import pandas as pd
import utils.network_fix

from binance.client import Client
from binance.exceptions import BinanceAPIException
from config.settings import BotConfig

logger = logging.getLogger("BinanceClient")


class BinanceFuturesClient:
    """Wrapper kết nối Binance Futures API (REST)"""

    def __init__(self, config: BotConfig):
        self.config = config
        self.is_testnet = config.use_testnet
        self.is_dry_run = config.dry_run

        api_key = config.api_key if config.api_key else None
        api_secret = config.api_secret if config.api_secret else None

        # Khởi tạo Client python-binance (ping=False để không bị block ở spot testnet)
        try:
            self.client = Client(
                api_key=api_key,
                api_secret=api_secret,
                testnet=self.is_testnet,
                ping=False
            )
        except Exception as e:
            logger.warning(f"Khởi tạo client testnet thất bại ({e}), chuyển sang client thông thường: {e}")
            self.client = Client(api_key=api_key, api_secret=api_secret, ping=False)

        # Base URL cho Futures
        self.fapi_base = "https://testnet.binancefuture.com/fapi/v1" if self.is_testnet else "https://fapi.binance.com/fapi/v1"
        self.public_fapi_base = "https://fapi.binance.com/fapi/v1"

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
        if self.is_dry_run and not (self.config.api_key and self.config.api_secret):
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
        if self.is_dry_run and not (self.config.api_key and self.config.api_secret):
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

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Lấy danh sách các vị thế đang mở (positionAmt != 0)"""
        if self.is_dry_run and not (self.config.api_key and self.config.api_secret):
            return []

        try:
            positions = self.client.futures_position_information()
            open_pos = []
            for pos in positions:
                amt = float(pos.get("positionAmt", 0.0))
                if amt != 0:
                    open_pos.append({
                        "symbol": pos["symbol"],
                        "amount": amt,
                        "side": "LONG" if amt > 0 else "SHORT",
                        "entry_price": float(pos.get("entryPrice", 0.0)),
                        "mark_price": float(pos.get("markPrice", 0.0)),
                        "unRealizedProfit": float(pos.get("unRealizedProfit", 0.0)),
                        "leverage": int(pos.get("leverage", 1)),
                        "liquidationPrice": float(pos.get("liquidationPrice", 0.0))
                    })
            return open_pos
        except BinanceAPIException as e:
            logger.error(f"Lỗi lấy danh sách vị thế: {e}")
            return []

    def set_leverage_and_margin(self, symbol: str, leverage: int, margin_type: str = "ISOLATED"):
        """Thiết lập đòn bẩy và chế độ ký quỹ (ISOLATED)"""
        if self.is_dry_run and not (self.config.api_key and self.config.api_secret):
            logger.info(f"[Dry Run] Đã cấu hình {symbol} sang {margin_type} và Đòn bẩy {leverage}x")
            return

        try:
            # 1. Đặt Margin Type (ISOLATED / CROSSED)
            try:
                self.client.futures_change_margin_type(symbol=symbol, marginType=margin_type)
            except BinanceAPIException as e:
                # Bỏ qua nếu đã là ISOLATED từ trước (code -4046)
                if e.code != -4046:
                    logger.debug(f"Margin type setting: {e.message}")

            # 2. Đặt Leverage
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            logger.info(f"Đã đặt {symbol}: Đòn bẩy {leverage}x, Margin {margin_type}")
        except BinanceAPIException as e:
            logger.warning(f"Không thể chỉnh đòn bẩy cho {symbol}: {e.message}")

    def get_symbol_filter_info(self, symbol: str) -> Dict[str, float]:
        """Lấy step_size, min_qty, min_notional, tick_size của symbol"""
        if symbol in self._exchange_info_cache:
            return self._exchange_info_cache[symbol]

        default_info = {
            "step_size": 0.001,
            "min_qty": 0.001,
            "min_notional": 5.0,
            "tick_size": 0.01
        }

        try:
            # Lấy thông tin từ public production API để đảm bảo tốc độ và độ chính xác
            url = f"{self.public_fapi_base}/exchangeInfo"
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

    def place_market_order(self, symbol: str, side: str, quantity: float) -> Optional[Dict[str, Any]]:
        """Gửi lệnh Market vào sàn"""
        if self.is_dry_run:
            logger.info(f"[DRY RUN ORDER] Market {side} {quantity} {symbol}")
            return {"status": "FILLED", "symbol": symbol, "side": side, "origQty": str(quantity)}

        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=quantity
            )
            logger.info(f"Lệnh Market thành công: {order.get('orderId')}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Lỗi đặt lệnh Market {symbol}: {e.message}")
            return None

    def place_stop_loss_order(self, symbol: str, side: str, stop_price: float) -> Optional[Dict[str, Any]]:
        """Đặt lệnh Hard Stop Loss (STOP_MARKET) trên sàn"""
        if self.is_dry_run:
            logger.info(f"[DRY RUN ORDER] Stop Loss {side} @ ${stop_price}")
            return {"status": "NEW", "type": "STOP_MARKET", "stopPrice": str(stop_price)}

        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="STOP_MARKET",
                stopPrice=stop_price,
                closePosition=True
            )
            return order
        except BinanceAPIException as e:
            logger.error(f"Lỗi đặt lệnh Stop Loss {symbol}: {e.message}")
            return None

    def place_take_profit_order(self, symbol: str, side: str, tp_price: float) -> Optional[Dict[str, Any]]:
        """Đặt lệnh Chốt lời (TAKE_PROFIT_MARKET) trên sàn"""
        if self.is_dry_run:
            logger.info(f"[DRY RUN ORDER] Take Profit {side} @ ${tp_price}")
            return {"status": "NEW", "type": "TAKE_PROFIT_MARKET", "stopPrice": str(tp_price)}

        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="TAKE_PROFIT_MARKET",
                stopPrice=tp_price,
                closePosition=True
            )
            return order
        except BinanceAPIException as e:
            logger.error(f"Lỗi đặt lệnh Take Profit {symbol}: {e.message}")
            return None

    def cancel_all_symbol_orders(self, symbol: str):
        """Hủy toàn bộ lệnh chờ của symbol (khi đóng vị thế)"""
        if self.is_dry_run:
            return

        try:
            self.client.futures_cancel_all_open_orders(symbol=symbol)
        except BinanceAPIException as e:
            logger.debug(f"Lỗi hủy lệnh chờ {symbol}: {e.message}")

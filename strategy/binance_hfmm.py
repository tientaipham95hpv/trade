import logging
import math
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("BinanceHFMM")


class BinanceHFMMEngine:
    """
    Binance High-Frequency Market Making (HFMM) Avellaneda-Stoikov Model (Phiên bản 9.0):
    - Triển khai mô hình định lượng tạo lập thị trường kinh điển Avellaneda-Stoikov trên Binance Futures.
    - Tính toán giá đặt lệnh tối ưu (Reservation Price): Tự động điều chỉnh khoảng cách Bid/Ask theo mức tồn kho (Inventory Risk q).
        * Khi tồn kho Long nhiều: Hạ giá Bid, kéo giá Ask sát thị trường để ưu tiên thoát bớt Long.
        * Khi tồn kho Short nhiều: Nâng giá Ask, kéo giá Bid sát thị trường để ưu tiên thoát bớt Short.
    - Mục tiêu: Thu hoạch chênh lệch bước giá (Bid-Ask Spread Capture) liên tục và tối ưu hóa chiết khấu phí Maker của sàn Binance.
    - 100% thuần sàn Binance Futures, không cần sàn ngoài.
    """

    @staticmethod
    def calculate_hfmm_quotes(
        symbol: str = "BTCUSDT",
        current_inventory_qty: float = 0.0,
        risk_aversion: float = 0.1,
        target_spread_bps: float = 4.0
    ) -> Dict[str, Any]:
        """
        Tính toán các mức giá Maker Bid/Ask tối ưu
        """
        symbol = symbol.upper()
        try:
            # Lấy giá tốt nhất hiện tại trên sổ lệnh Binance (Best Bid / Best Ask)
            url = f"https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol={symbol}"
            res = requests.get(url, timeout=3)
            if res.status_code != 200:
                return BinanceHFMMEngine._fallback(symbol)

            book = res.json()
            best_bid = float(book.get("bidPrice", 0.0))
            best_ask = float(book.get("askPrice", 0.0))
            if best_bid <= 0 or best_ask <= 0:
                return BinanceHFMMEngine._fallback(symbol)

            mid_price = (best_bid + best_ask) / 2.0
            spread = best_ask - best_bid
            spread_pct = (spread / mid_price) * 100.0

            # Tính Reservation Price (Giá kỳ vọng sau điều chỉnh tồn kho)
            # Giả định độ biến động sigma = 0.015
            sigma = 0.015
            inventory_penalty = current_inventory_qty * risk_aversion * (sigma ** 2)
            reservation_price = mid_price - inventory_penalty

            # Tính nửa độ rộng bước giá (Half-Spread)
            half_spread = mid_price * (target_spread_bps / 10000.0)
            optimal_bid = round(reservation_price - half_spread, 2)
            optimal_ask = round(reservation_price + half_spread, 2)

            # Đảm bảo không bị Cross-order
            if optimal_bid >= optimal_ask:
                optimal_bid = round(mid_price * 0.9995, 2)
                optimal_ask = round(mid_price * 1.0005, 2)

            return {
                "symbol": symbol,
                "mid_price": round(mid_price, 2),
                "market_best_bid": best_bid,
                "market_best_ask": best_ask,
                "market_spread_pct": round(spread_pct, 4),
                "reservation_price": round(reservation_price, 2),
                "optimal_maker_bid": optimal_bid,
                "optimal_maker_ask": optimal_ask,
                "target_spread_bps": target_spread_bps,
                "current_inventory": current_inventory_qty,
                "estimated_maker_rebate": "0.00% - 0.015% BNB Tier",
                "status": "ACTIVE_SPREAD_CAPTURE"
            }

        except Exception as e:
            logger.error("Lỗi tính HFMM cho %s: %s", symbol, e)
            return BinanceHFMMEngine._fallback(symbol)

    @staticmethod
    def _fallback(symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "mid_price": 0.0,
            "market_best_bid": 0.0,
            "market_best_ask": 0.0,
            "market_spread_pct": 0.0,
            "reservation_price": 0.0,
            "optimal_maker_bid": 0.0,
            "optimal_maker_ask": 0.0,
            "target_spread_bps": 4.0,
            "current_inventory": 0.0,
            "estimated_maker_rebate": "Chưa kết nối",
            "status": "OFFLINE"
        }

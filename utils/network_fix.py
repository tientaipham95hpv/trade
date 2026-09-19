import socket
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3.util.connection as urllib_util

logger = logging.getLogger("NetworkFix")

# 1. Ép urllib3 luôn dùng IPv4 (tránh độ trễ timeout của IPv6 NAT64 trên Windows)
try:
    urllib_util.allowed_gai_family = lambda: socket.AF_INET
except Exception as e:
    logger.debug(f"Không thể đặt IPv4 force: {e}")


def get_resilient_session(retries: int = 3, backoff: float = 0.5) -> requests.Session:
    """
    Tạo session HTTP có cơ chế Retry tự động khi gặp lỗi mạng/DNS chập chờn
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# Khởi tạo session toàn cục dùng chung
http_session = get_resilient_session()

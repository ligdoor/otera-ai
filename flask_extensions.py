import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("REDIS_URL", "memory://"),
    storage_options={"socket_connect_timeout": 5},  # Redis接続タイムアウト5秒
    default_limits=["2000 per day", "500 per hour"],
    headers_enabled=True,
    swallow_errors=True,              # Redis障害時にエラーを飲み込みアプリを止めない
    in_memory_fallback_enabled=True,  # Redis障害時にメモリへ自動フォールバック
)

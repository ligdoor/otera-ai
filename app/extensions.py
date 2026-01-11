import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("REDIS_URL", "memory://"),
    default_limits=["200 per day", "50 per hour"],
    headers_enabled=True
)

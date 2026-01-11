import os
import secrets
import datetime
from dotenv import load_dotenv

load_dotenv()

class Config:
    """アプリケーション設定"""
    
    # Flask設定
    SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(minutes=30)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True if os.environ.get('FLASK_ENV') == 'production' else False
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # API Keys
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    
    # Google Sheets設定
    DATA_SPREADSHEET_NAME = "otera_data"
    CONFIG_SPREADSHEET_NAME = "otera_admin_config"
    GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    
    # 通知設定
    SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
    
    # セキュリティ設定
    LOCK_TIME = 300  # ログイン失敗時のロック時間（秒）
    MAX_ATTEMPTS = 5  # 最大ログイン試行回数
    SESSION_TIMEOUT = 1800  # セッションタイムアウト（秒）
    
    # キャッシュ設定（メモリキャッシュ）
    CACHE_TIMEOUT = 300  # キャッシュ有効期限（秒）
    
    # Flask-Caching設定
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "SimpleCache")  # 本番: "RedisCache"
    CACHE_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Redis SSL/TLS設定（Upstash用）
    CACHE_OPTIONS = {
        'ssl_cert_reqs': None  # SSL証明書検証を無効化（Upstash対応）
    } if os.environ.get("REDIS_URL", "").startswith("rediss://") else {}
    
    # Flask-Compress設定
    COMPRESS_MIMETYPES = [
        'text/html',
        'text/css',
        'text/xml',
        'application/json',
        'application/javascript'
    ]
    COMPRESS_LEVEL = 6
    COMPRESS_MIN_SIZE = 500
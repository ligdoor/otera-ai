import os
from flask import Flask, jsonify
from flask_compress import Compress
from flask_caching import Cache
from config import Config
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.temple_routes import temple_bp, init_temple_data
from routes.user_routes import user_bp
from routes.api_routes import api_bp
from flask_extensions import limiter

# Sentry初期化（オプショナル）
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    
    if os.environ.get('SENTRY_DSN'):
        sentry_sdk.init(
            dsn=os.environ.get('SENTRY_DSN'),
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=os.environ.get('FLASK_ENV', 'production'),
        )
        print("✅ Sentry monitoring enabled")
except ImportError:
    print("⚠️ Sentry SDK not installed - monitoring disabled")

# Flaskアプリケーション初期化
app = Flask(__name__)
app.config.from_object(Config)
limiter.init_app(app)

# Flask拡張機能の初期化
compress = Compress(app)  # レスポンス圧縮
cache = Cache(app)  # キャッシング

# キャッシュインスタンスをエクスポート（他のモジュールから使用可能に）
__all__ = ['app', 'cache']

# Blueprintを登録
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(temple_bp)
app.register_blueprint(user_bp)
app.register_blueprint(api_bp)

# 初期データ読み込み
with app.app_context():
    init_temple_data()

# ヘルスチェックエンドポイント（監視用）
@app.route("/health")
def health_check():
    """システムのヘルスチェック"""
    try:
        from routes.temple_routes import otera_database
        from services.spreadsheet import get_spreadsheet_client
        from utils.helpers import get_jst_timestamp
        
        # データベース接続確認
        client = get_spreadsheet_client()
        
        # 寺院データ確認
        temple_count = len(otera_database)
        
        return jsonify({
            "status": "healthy",
            "temple_count": temple_count,
            "timestamp": get_jst_timestamp()
        }), 200
    except Exception as e:
        from utils.helpers import get_jst_timestamp
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": get_jst_timestamp()
        }), 500

# セキュリティヘッダー設定
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5001)),
        debug=os.environ.get("FLASK_ENV") == "development",
        use_reloader=False,
        threaded=True
    )

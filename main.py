import os
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask import Flask
from flask_compress import Compress
from flask_caching import Cache
from config import Config
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.temple_routes import temple_bp, init_temple_data
from routes.user_routes import user_bp
from routes.api_routes import api_bp

# Sentry初期化（本番環境のみ）
if os.environ.get('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,  # パフォーマンス監視（10%サンプリング）
        profiles_sample_rate=0.1,  # プロファイリング
        environment=os.environ.get('FLASK_ENV', 'production'),
        # エラーフィルタリング（不要なエラーを除外）
        before_send=lambda event, hint: event if event.get('level') != 'info' else None
    )
    print("✅ Sentry monitoring enabled")
    
# Flaskアプリケーション初期化
app = Flask(__name__)
app.config.from_object(Config)

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

# セキュリティヘッダー設定
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

if __name__ == "__main__":
    app.run(debug=True, port=5001)
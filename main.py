# main.py - 修正版

import os
import sys
from flask import Flask, jsonify, render_template, request, session
from flask_compress import Compress
from flask_caching import Cache
from config import Config
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.temple_routes import temple_bp, init_temple_data
from routes.user_routes import user_bp
from routes.api_routes import api_bp
from flask_extensions import limiter
from utils.env_checker import check_required_env
# ★ 追加: メンテナンスモードのインポート
from maintenance import MaintenanceMode

print("\n" + "="*60)
print("🔍 環境変数チェック開始")
print("="*60)

if not check_required_env():
    print("\n" + "="*60)
    print("❌ 起動失敗: 必須の環境変数が不足しています")
    print("="*60)
    print("\n【対処方法】")
    print("1. .env ファイルを確認してください")
    print("2. 不足している環境変数を設定してください")
    print("3. 設定例:")
    print("   SECRET_KEY=your-secret-key-here")
    print("   SUPABASE_URL=https://xxxxx.supabase.co")
    print("   SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1...")
    print("\n環境変数を設定してから再度起動してください\n")
    sys.exit(1)

print("✅ 環境変数チェック完了\n")

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
compress = Compress(app)
cache = Cache(app)

# キャッシュインスタンスをエクスポート
__all__ = ['app', 'cache']

# ============================================================
# ★★★ メンテナンスモードのチェック（ここに追加） ★★★
# ============================================================
@app.before_request
def check_maintenance():
    """
    メンテナンスモードのチェック（セキュア版）
    全てのリクエストの前に実行される
    """
    # メンテナンス中でも常にアクセス可能なパス（認証不要）
    always_allowed = [
        '/static/',      # 静的ファイル（CSS/JS/画像）
        '/health',       # ヘルスチェック
        '/admin'         # 管理画面（ログインページ含む）
    ]
    
    # 管理者専用パス（ログインしていればアクセス可能）
    admin_only_paths = [
        '/api/maintenance/',    # メンテナンスモードAPI
        '/get_current_user',    # ユーザー情報取得
        '/get_fields',          # フィールド情報取得
        '/get_all_data',        # 全データ取得
        '/get_temple_names',    # 寺院名取得
        '/get_sects',           # 宗派取得
        '/logout',              # ログアウト
        '/api/favorites',       # お気に入り管理（管理者用）
        '/api/notifications',   # 通知管理（管理者用）
        '/api/user-settings'    # ユーザー設定（管理者用）
    ]
    
    # 1. 常にアクセス可能なパスのチェック
    for path in always_allowed:
        if request.path.startswith(path):
            return None
    
    # 2. 管理者専用パスのチェック（ログイン状態で判断）
    for path in admin_only_paths:
        if request.path.startswith(path):
            # ログインしているユーザーのみ通す
            if session.get('user_id'):
                return None
            # ログインしていない場合は、メンテナンスモードでなければ通常処理
            # メンテナンスモード中の場合は下の処理に進む
            break
    
    # 3. メンテナンスモードが有効な場合
    if MaintenanceMode.is_enabled():
        return render_template('maintenance.html', 
                             message=MaintenanceMode.get_message())    
# ============================================================
# Blueprint登録（メンテナンスチェックの後に配置）
# ============================================================
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
        from utils.helpers import get_jst_timestamp
        from config import Config
        
        # データベース接続確認
        if Config.USE_SUPABASE:
            from services.supabase_db import get_supabase_client
            client = get_supabase_client()
        else:
            from services.spreadsheet import get_spreadsheet_client
            client = get_spreadsheet_client()
        
        # 寺院データ確認
        temple_count = len(otera_database)
        
        return jsonify({
            "status": "healthy",
            "data_source": "Supabase" if Config.USE_SUPABASE else "Google Sheets",
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
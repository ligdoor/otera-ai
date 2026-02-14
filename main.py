"""
AI寺院案内サイト メインアプリケーション

リファクタリング済みモジュールを使用したFlaskアプリケーション。
全てのBlueprintとミドルウェアを統合します。
"""

import os
import sys
from flask import Flask, jsonify, render_template, request, session
from flask_compress import Compress
from flask_caching import Cache
from config import Config
from flask_extensions import limiter
from utils.env_checker import check_required_env
from maintenance import MaintenanceMode

# ============================================
# 環境変数チェック
# ============================================

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

# ============================================
# Sentry初期化（オプショナル）
# ============================================

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

# ============================================
# Flaskアプリケーション初期化
# ============================================

app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static')
app.config.from_object(Config)
limiter.init_app(app)

# Flask拡張機能の初期化
compress = Compress(app)
cache = Cache(app)

# キャッシュインスタンスをエクスポート（他のモジュールから使用可能に）
__all__ = ['app', 'cache']

# ============================================
# メンテナンスモードチェック
# ============================================

@app.before_request
def check_maintenance():
    """
    メンテナンスモードのチェック
    
    全てのリクエストの前に実行され、メンテナンスモードが有効な場合は
    メンテナンス画面を表示します。管理者は常にアクセス可能です。
    """
    # 常にアクセス可能なパス（認証不要）
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
        '/api/favorites',       # お気に入り管理
        '/api/notifications',   # 通知管理
        '/api/user-settings'    # ユーザー設定
    ]
    
    # 1. 常にアクセス可能なパスのチェック
    for path in always_allowed:
        if request.path.startswith(path):
            return None
    
    # 2. 管理者専用パスのチェック
    for path in admin_only_paths:
        if request.path.startswith(path):
            # ログインしているユーザーのみ通す
            if session.get('user_id'):
                return None
            break
    
    # 3. メンテナンスモードが有効な場合
    if MaintenanceMode.is_enabled():
        return render_template(
            'maintenance.html',
            message=MaintenanceMode.get_message()
        )

# ============================================
# Blueprint登録（リファクタリング済みモジュール）
# ============================================

print("📦 Blueprintを登録中...")

# 認証ルート（Phase 3でリファクタリング）
from routes.auth import (
    auth_login_bp,
    auth_register_bp,
    auth_password_bp
)

app.register_blueprint(auth_login_bp)
app.register_blueprint(auth_register_bp)
app.register_blueprint(auth_password_bp)
print("  ✅ 認証ルート登録完了")

# 寺院ルート（Phase 2でリファクタリング）
from routes.temple import (
    temple_view_bp,
    temple_search_bp,
    temple_ai_bp,
    temple_crud_bp,
    temple_data_bp,
    init_temple_data
)

app.register_blueprint(temple_view_bp)
app.register_blueprint(temple_search_bp)
app.register_blueprint(temple_ai_bp)
app.register_blueprint(temple_crud_bp)
app.register_blueprint(temple_data_bp)
print("  ✅ 寺院ルート登録完了")

# 管理ルート（Phase 4でリファクタリング）
from routes.admin import (
    admin_system_bp,
    admin_items_bp,
    admin_data_bp
)

app.register_blueprint(admin_system_bp)
app.register_blueprint(admin_items_bp)
app.register_blueprint(admin_data_bp)
print("  ✅ 管理ルート登録完了")

# その他のルート（未リファクタリング）
from routes.user_routes import user_bp
from routes.api_routes import api_bp
from routes.items_routes import items_bp

app.register_blueprint(user_bp)
app.register_blueprint(api_bp)
app.register_blueprint(items_bp)
print("  ✅ その他のルート登録完了")

print("✅ 全Blueprintの登録完了\n")

# ============================================
# 初期データ読み込み
# ============================================

print("📚 初期データを読み込み中...")
with app.app_context():
    init_temple_data()
print("✅ 初期データ読み込み完了\n")

# ============================================
# ヘルスチェックエンドポイント
# ============================================

@app.route("/health")
def health_check():
    """
    システムのヘルスチェック
    
    監視システムやロードバランサーからの死活監視に使用します。
    データベース接続と寺院データの状態を確認します。
    
    Returns:
        JSON: システムの状態
            status (str): "healthy" | "unhealthy"
            data_source (str): "Supabase" | "Google Sheets"
            temple_count (int): 読み込まれた寺院数
            timestamp (str): チェック実行時刻
    
    Example Response (正常):
        {
            "status": "healthy",
            "data_source": "Supabase",
            "temple_count": 150,
            "timestamp": "2024-02-13T14:30:00+09:00"
        }
    
    Example Response (異常):
        {
            "status": "unhealthy",
            "error": "Database connection failed",
            "timestamp": "2024-02-13T14:30:00+09:00"
        }
    """
    try:
        from routes.temple.common import get_otera_database
        from utils.helpers import get_jst_timestamp
        
        # データベース接続確認
        if Config.USE_SUPABASE:
            from services.database import get_supabase_client
            client = get_supabase_client()
        else:
            from services.spreadsheet import get_spreadsheet_client
            client = get_spreadsheet_client()
        
        # 寺院データ確認
        otera_database = get_otera_database()
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

# ============================================
# セキュリティヘッダー設定
# ============================================

@app.after_request
def set_security_headers(response):
    """
    セキュリティヘッダーを設定
    
    全てのレスポンスにセキュリティ関連のHTTPヘッダーを追加します。
    
    設定されるヘッダー:
        - X-Content-Type-Options: コンテンツタイプのスニッフィング防止
        - X-Frame-Options: クリックジャッキング攻撃防止
        - X-XSS-Protection: XSS攻撃検出・防止
        - Strict-Transport-Security: HTTPS通信の強制
    """
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# ============================================
# アプリケーション起動
# ============================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 AI寺院案内サイト起動中...")
    print("="*60)
    print(f"環境: {os.environ.get('FLASK_ENV', 'production')}")
    print(f"ポート: {int(os.environ.get('PORT', 5001))}")
    print(f"データソース: {'Supabase' if Config.USE_SUPABASE else 'Google Sheets'}")
    print("="*60 + "\n")
    
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5001)),
        debug=os.environ.get("FLASK_ENV") == "development",
        use_reloader=False,
        threaded=True
    )

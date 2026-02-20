"""
AI寺院案内サイト メインアプリケーション（エラーハンドリング適用版）

リファクタリング済みモジュールを使用したFlaskアプリケーション。
全てのBlueprintとミドルウェアを統合します。

【改善点】
✅ エラーハンドリングシステムを統合
✅ 構造化ロギングを実装
✅ Flaskエラーハンドラーを自動登録
✅ 全処理にtry-exceptを追加
✅ セキュリティイベントのログ記録
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
from routes.log_viewer_html import log_viewer_html_bp

# ============================================
# セキュリティミドルウェア
# ============================================
from middleware.security_headers import init_security_headers
from middleware.csrf_protection import init_csrf

# ============================================
# エラーハンドリングシステムの初期化（NEW!）
# ============================================

from modules.error_handler import ErrorHandler
from modules.error_logger import ErrorLogger
from modules.decorators import handle_errors

# ログシステムをセットアップ
ErrorLogger.setup(
    log_level='INFO',
    log_dir='logs',
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=30,              # 30世代保持
    json_format=False             # JSON形式: True/False
)
logger = ErrorLogger.get_logger(__name__)

logger.info("="*60)
logger.info("AI寺院案内サイト 起動プロセス開始")
logger.info("="*60)

# ============================================
# 環境変数チェック
# ============================================

print("\n" + "="*60)
print("🔍 環境変数チェック開始")
print("="*60)

if not check_required_env():
    # エラーログに記録
    logger.critical("起動失敗: 必須の環境変数が不足しています")
    
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
logger.info("環境変数チェック完了")

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
        logger.info("Sentry monitoring enabled")
except ImportError:
    print("⚠️ Sentry SDK not installed - monitoring disabled")
    logger.warning("Sentry SDK not installed - monitoring disabled")
except Exception as e:
    logger.error(f"Sentry initialization failed: {str(e)}")

# ============================================
# Flaskアプリケーション初期化
# ============================================

app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static')
app.config.from_object(Config)
limiter.init_app(app)

# ============================================
# ★ セキュリティミドルウェアを有効化
# ============================================
init_security_headers(app)  # X-Frame-Options, X-Content-Type-Options 等
init_csrf(app)               # CSRFトークン（テンプレートで {{ csrf_token() }} が使える）

# Flask拡張機能の初期化
compress = Compress(app)
cache = Cache(app)

# キャッシュインスタンスをエクスポート
__all__ = ['app', 'cache']

# ============================================
# エラーハンドラーの登録（NEW!）
# ============================================

logger.info("Flaskエラーハンドラーを登録中...")
ErrorHandler.register_flask_handlers(app)
logger.info("✅ Flaskエラーハンドラー登録完了")

# ============================================
# メンテナンスモードチェック
# ============================================

@app.before_request
def check_maintenance():
    """
    メンテナンスモードのチェック（エラーハンドリング強化版）
    """
    try:
        # 常にアクセス可能なパス
        always_allowed = [
            '/static/',
            '/health',
            '/admin'
        ]
        
        # 管理者専用パス
        admin_only_paths = [
            '/api/maintenance/',
            '/get_current_user',
            '/get_fields',
            '/get_all_data',
            '/get_temple_names',
            '/get_sects',
            '/logout',
            '/api/favorites',
            '/api/notifications',
            '/api/user-settings'
        ]
        
        # 1. 常にアクセス可能なパスのチェック
        for path in always_allowed:
            if request.path.startswith(path):
                return None
        
        # 2. 管理者専用パスのチェック
        for path in admin_only_paths:
            if request.path.startswith(path):
                if session.get('user_id'):
                    return None
                break
        
        # 3. メンテナンスモードが有効な場合
        if MaintenanceMode.is_enabled():
            logger.info(f"Maintenance mode: access blocked for {request.path}")
            return render_template(
                'maintenance.html',
                message=MaintenanceMode.get_message()
            )
    
    except Exception as e:
        # メンテナンスチェックでエラーが起きても処理を続行
        logger.error(f"Error in maintenance check: {str(e)}", exc_info=True)
        return None

# ============================================
# Blueprint登録
# ============================================

print("📦 Blueprintを登録中...")
logger.info("Blueprint登録開始")

try:
    # 認証ルート
    from routes.auth import (
        auth_login_bp,
        auth_register_bp,
        auth_password_bp
    )
    
    app.register_blueprint(auth_login_bp)
    app.register_blueprint(auth_register_bp)
    app.register_blueprint(auth_password_bp)
    app.register_blueprint(log_viewer_html_bp)
    print("  ✅ 認証ルート登録完了")
    logger.info("認証ルート登録完了")
    
except Exception as e:
    logger.error(f"認証ルート登録失敗: {str(e)}", exc_info=True)
    raise

try:
    # 寺院ルート
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
    logger.info("寺院ルート登録完了")
    
except Exception as e:
    logger.error(f"寺院ルート登録失敗: {str(e)}", exc_info=True)
    raise

try:
    # 管理ルート
    from routes.admin import (
        admin_system_bp,
        admin_items_bp,
        admin_data_bp
    )
    
    app.register_blueprint(admin_system_bp)
    app.register_blueprint(admin_items_bp)
    app.register_blueprint(admin_data_bp)
    print("  ✅ 管理ルート登録完了")
    logger.info("管理ルート登録完了")
    
except Exception as e:
    logger.error(f"管理ルート登録失敗: {str(e)}", exc_info=True)
    raise

try:
    # その他のルート
    from routes.user_routes import user_bp
    from routes.api_routes import api_bp
    from routes.items_routes import items_bp
    from routes.log_viewer import log_viewer_bp
    
    app.register_blueprint(log_viewer_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(items_bp)
    print("  ✅ その他のルート登録完了")
    logger.info("その他のルート登録完了")
    
except Exception as e:
    logger.error(f"その他のルート登録失敗: {str(e)}", exc_info=True)
    raise

print("✅ 全Blueprintの登録完了\n")
logger.info("全Blueprintの登録完了")

# ============================================
# 初期データ読み込み
# ============================================

print("📚 初期データを読み込み中...")
logger.info("初期データ読み込み開始")

try:
    with app.app_context():
        init_temple_data()
    print("✅ 初期データ読み込み完了\n")
    logger.info("初期データ読み込み完了")
    
except Exception as e:
    logger.error(f"初期データ読み込み失敗: {str(e)}", exc_info=True)
    print(f"⚠️ 初期データ読み込みに失敗しました: {str(e)}")
    # データ読み込み失敗は警告のみで継続

# ============================================
# ヘルスチェックエンドポイント
# ============================================

@app.route("/health")
def health_check():
    """
    システムのヘルスチェック（エラーハンドリング強化版）
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
        # ヘルスチェック失敗はログに記録
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        
        from utils.helpers import get_jst_timestamp
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": get_jst_timestamp()
        }), 500

# ============================================
# セキュリティヘッダー設定
# ★ middleware/security_headers.py で統合管理
#   (init_security_headers(app) 呼び出し済み)
# ============================================

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
    
    logger.info("="*60)
    logger.info("AI寺院案内サイト起動")
    logger.info(f"環境: {os.environ.get('FLASK_ENV', 'production')}")
    logger.info(f"ポート: {int(os.environ.get('PORT', 5001))}")
    logger.info(f"データソース: {'Supabase' if Config.USE_SUPABASE else 'Google Sheets'}")
    logger.info("="*60)
    
    try:
        # ★ debug は環境変数 FLASK_DEBUG で制御（本番では 0 を設定）
        _debug = os.environ.get("FLASK_ENV") == "development" and \
                 os.environ.get("FLASK_DEBUG", "0") == "1"
        app.run(
            host="0.0.0.0",
            port=int(os.environ.get("PORT", 5001)),
            debug=_debug,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        logger.critical(f"アプリケーション起動失敗: {str(e)}", exc_info=True)
        raise
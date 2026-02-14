"""
認証ルートパッケージ

ユーザー認証関連の全ルート機能を提供します。

モジュール構成:
    - login_routes: ログイン・ログアウト
    - register_routes: 新規登録・承認
    - password_routes: パスワード変更・リセット

使用例（main.pyでの登録）:
    from routes.auth import (
        auth_login_bp,
        auth_register_bp,
        auth_password_bp
    )
    
    # Blueprintを登録
    app.register_blueprint(auth_login_bp)
    app.register_blueprint(auth_register_bp)
    app.register_blueprint(auth_password_bp)
"""

# ============================================
# Blueprintのインポート
# ============================================
from .login_routes import auth_login_bp        # ログイン・ログアウト
from .register_routes import auth_register_bp  # 新規登録・承認
from .password_routes import auth_password_bp  # パスワード管理

# ============================================
# ヘルパー関数のエクスポート
# ============================================
from .login_routes import render_login_page    # ログインページレンダリング

# ============================================
# パッケージ情報
# ============================================
__all__ = [
    # Blueprints
    'auth_login_bp',
    'auth_register_bp',
    'auth_password_bp',
    
    # ヘルパー関数
    'render_login_page',
]

__version__ = '2.0.0'
__author__ = 'Temple Site Team'

# ============================================
# モジュール説明
# ============================================

# 各Blueprintの責務:
#
# auth_login_bp (login_routes.py):
#   - ログイン処理（GET /admin, POST /admin）
#   - ログアウト処理（GET /logout）
#   - セッション管理
#   - ログイン試行回数制限
#   - ログイン履歴記録
#
# auth_register_bp (register_routes.py):
#   - 新規登録画面表示（GET /register）
#   - 新規登録申請（POST /register）
#   - 承認待ちユーザー一覧（GET /pending-users）
#   - ユーザー承認（POST /approve-user/<id>）
#   - ユーザー却下（POST /reject-user/<id>）
#   - 承認待ち件数取得（GET /api/pending-users-count）
#
# auth_password_bp (password_routes.py):
#   - パスワード変更（POST /change_password）
#   - パスワードリセットリクエスト（GET/POST /password-reset-request）
#   - パスワードリセット実行（GET/POST /password-reset/<token>）

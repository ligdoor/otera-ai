"""
管理ルートパッケージ

管理者向けの全管理機能を提供します。

モジュール構成:
    - system_routes: システム管理（メンテナンス、ログ、項目設定）
    - items_routes: 仏教用品管理（CRUD、カテゴリ、画像アップロード）
    - data_routes: データ管理（CSV入出力）

使用例（main.pyでの登録）:
    from routes.admin import (
        admin_system_bp,
        admin_items_bp,
        admin_data_bp
    )
    
    # Blueprintを登録
    app.register_blueprint(admin_system_bp)
    app.register_blueprint(admin_items_bp)
    app.register_blueprint(admin_data_bp)
"""

# ============================================
# Blueprintのインポート
# ============================================
from .system_routes import admin_system_bp  # システム管理
from .items_routes import admin_items_bp    # 仏教用品管理
from .data_routes import admin_data_bp      # データ管理

# ============================================
# パッケージ情報
# ============================================
__all__ = [
    # Blueprints
    'admin_system_bp',
    'admin_items_bp',
    'admin_data_bp',
]

__version__ = '2.0.0'
__author__ = 'Temple Site Team'

# ============================================
# モジュール説明
# ============================================

# 各Blueprintの責務:
#
# admin_system_bp (system_routes.py):
#   - メンテナンスモード管理
#     - GET /api/maintenance/status: メンテナンス状態取得
#     - POST /api/maintenance/toggle: メンテナンス切り替え
#   - ログ管理
#     - GET /get_logs: ログ一覧取得
#   - 項目設定管理
#     - GET /admin/fields: 項目設定画面
#     - GET /get_fields: 項目設定取得
#     - POST /update_fields: 項目設定更新
#
# admin_items_bp (items_routes.py):
#   - 仏具管理画面
#     - GET /admin/items: 仏具管理画面表示
#   - 仏具CRUD
#     - GET /api/admin/items: 仏具一覧取得
#     - GET /api/admin/items/<id>: 仏具詳細取得
#     - POST /api/admin/items: 仏具作成
#     - PUT /api/admin/items/<id>: 仏具更新
#     - DELETE /api/admin/items/<id>: 仏具削除
#   - カテゴリ管理
#     - GET /api/admin/categories: カテゴリ一覧取得
#   - 画像アップロード
#     - POST /api/admin/upload-image: 画像アップロード（WebP圧縮）
#
# admin_data_bp (data_routes.py):
#   - CSV入出力
#     - POST /import_csv: CSVインポート
#     - GET /export_csv: CSVエクスポート

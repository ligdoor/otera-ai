"""
寺院ルートパッケージ

寺院関連の全ルート機能を提供します。

モジュール構成:
    - common: 共通データとユーティリティ
    - view_routes: 画面表示ルート
    - search_routes: 検索機能ルート
    - ai_routes: AI質問応答ルート
    - crud_routes: CRUD操作ルート
    - data_routes: データ入出力・統計ルート

使用例（main.pyでの登録）:
    from routes.temple import (
        temple_view_bp,
        temple_search_bp,
        temple_ai_bp,
        temple_crud_bp,
        temple_data_bp,
        init_temple_data
    )
    
    # Blueprintを登録
    app.register_blueprint(temple_view_bp)
    app.register_blueprint(temple_search_bp)
    app.register_blueprint(temple_ai_bp)
    app.register_blueprint(temple_crud_bp)
    app.register_blueprint(temple_data_bp)
    
    # データ初期化
    init_temple_data()
"""

# ============================================
# 共通モジュール
# ============================================
from .common import (
    init_temple_data,           # データ初期化関数
    get_otera_database,          # 寺院データ取得
    get_field_config,            # フィールド設定取得
    reload_temple_data,          # データ再読み込み
    otera_database,              # グローバル寺院データ
    field_config                 # グローバルフィールド設定
)

# ============================================
# Blueprintのインポート
# ============================================
from .view_routes import temple_view_bp      # 画面表示
from .search_routes import temple_search_bp  # 検索機能
from .ai_routes import temple_ai_bp          # AI質問応答
from .crud_routes import temple_crud_bp      # CRUD操作
from .data_routes import temple_data_bp      # データ入出力・統計

# ============================================
# ヘルパー関数のエクスポート
# ============================================
from .search_routes import (
    calculate_search_score,     # 検索スコア計算
    find_best_match              # 最適な寺院を検索
)

# ============================================
# パッケージ情報
# ============================================
__all__ = [
    # データ初期化・管理
    'init_temple_data',
    'get_otera_database',
    'get_field_config',
    'reload_temple_data',
    'otera_database',
    'field_config',
    
    # Blueprints
    'temple_view_bp',
    'temple_search_bp',
    'temple_ai_bp',
    'temple_crud_bp',
    'temple_data_bp',
    
    # ヘルパー関数
    'calculate_search_score',
    'find_best_match',
]

__version__ = '2.0.0'
__author__ = 'Temple Site Team'

# ============================================
# モジュール説明
# ============================================

# 各Blueprintの責務:
#
# temple_view_bp (view_routes.py):
#   - メイン画面表示
#   - データ再読み込み
#   - データ・フィールド取得API
#
# temple_search_bp (search_routes.py):
#   - 寺院名検索（完全一致・曖昧検索）
#   - スコアベースのサジェスト機能
#
# temple_ai_bp (ai_routes.py):
#   - AI質問応答
#   - 質問文から寺院名の自動抽出
#   - サマリー生成
#
# temple_crud_bp (crud_routes.py):
#   - 寺院データの追加
#   - 寺院データの更新
#   - 寺院データの削除
#
# temple_data_bp (data_routes.py):
#   - CSVエクスポート
#   - CSVインポート
#   - アクセス統計
#   - コメント機能

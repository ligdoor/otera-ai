"""
寺院ルート共通モジュール

全ての寺院関連ルートで使用する共通データとユーティリティ関数を提供します。
グローバル変数の管理、データ初期化などを担当します。
"""

from services.data_source import load_data_from_sheet, load_fields_config
from services.cache import cache_manager

# ============================================
# グローバル変数
# ============================================

# 寺院データベース（メモリキャッシュ）
# 寺院名をキーとした辞書形式で全寺院データを保持
otera_database = {}

# フィールド設定
# 寺院データの項目定義（key, label, orderなど）を保持
field_config = []


# ============================================
# キャッシュ取得ヘルパー
# ============================================

def get_cache():
    """
    Flask-Cachingインスタンスを取得
    
    循環インポートを回避するため、遅延インポートを使用しています。
    この関数は必要な時にのみキャッシュインスタンスを取得します。
    
    Returns:
        Cache: Flask-Cachingインスタンス
    
    Note:
        main.pyからのインポートを遅延させることで、
        モジュール間の循環依存を防ぎます。
    """
    from main import cache
    return cache


# ============================================
# データ初期化
# ============================================

def init_temple_data():
    """
    寺院データを初期化
    
    Google SheetsまたはSupabaseから寺院データとフィールド設定を読み込み、
    グローバル変数に格納します。アプリケーション起動時に1回実行されます。
    
    グローバル変数の更新:
        - otera_database: 全寺院データ
        - field_config: フィールド定義
    
    Example:
        # アプリケーション起動時
        init_temple_data()
        
        # データにアクセス
        from routes.temple.common import otera_database
        temple = otera_database.get("東大寺")
    """
    global otera_database, field_config
    
    # データソースから寺院データを読み込み
    otera_database = load_data_from_sheet(cache_manager)
    
    # フィールド設定を読み込み
    field_config = load_fields_config(cache_manager)
    
    print(f"✅ 寺院データ初期化完了: {len(otera_database)}件")


# ============================================
# データアクセスヘルパー
# ============================================

def get_otera_database():
    """
    寺院データベースを取得
    
    Returns:
        dict: 寺院データベース（寺院名: 寺院情報）
    
    Example:
        database = get_otera_database()
        for name, temple in database.items():
            print(f"{name}: {temple.get('address')}")
    """
    return otera_database


def get_field_config():
    """
    フィールド設定を取得
    
    Returns:
        list: フィールド設定のリスト
    
    Example:
        fields = get_field_config()
        for field in fields:
            print(f"{field['label']}: {field['key']}")
    """
    return field_config


def reload_temple_data():
    """
    寺院データを再読み込み
    
    キャッシュをクリアして、最新のデータを読み込みます。
    管理画面からのデータ更新後などに使用します。
    
    Returns:
        bool: 成功した場合True
    
    Example:
        success = reload_temple_data()
        if success:
            print("データを更新しました")
    """
    try:
        # キャッシュをクリア
        cache_manager.clear_cache('temples')
        cache_manager.clear_cache('fields')
        
        # データを再読み込み
        init_temple_data()
        
        return True
    
    except Exception as e:
        print(f"❌ データ再読み込みエラー: {e}")
        return False

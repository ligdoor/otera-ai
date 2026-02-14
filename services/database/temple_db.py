"""
寺院データベース操作モジュール

寺院情報の取得、作成、更新、削除などのCRUD操作と
項目設定（フィールド定義）の管理を提供します。
"""

from typing import Dict, List, Optional
from .base import get_supabase_client, retry_on_failure


# ============================================
# 寺院データCRUD操作
# ============================================

@retry_on_failure(max_retries=3)
def get_all_temples() -> Dict[str, Dict]:
    """
    すべての寺院データを取得
    
    データベースから全寺院情報を取得し、寺院名をキーとした辞書形式で返します。
    名前順（昇順）にソートされています。
    
    Returns:
        Dict[str, Dict]: 寺院名をキーとした寺院データの辞書
            例: {
                "東大寺": {"name": "東大寺", "address": "奈良県...", ...},
                "清水寺": {"name": "清水寺", "address": "京都府...", ...}
            }
    
    Example:
        temples = get_all_temples()
        todaiji = temples.get("東大寺")
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # templesテーブルから全データを取得（名前順）
    response = client.table('temples').select('*').order('name').execute()
    
    # 寺院名をキーにした辞書に変換
    temples = {}
    for temple in response.data:
        temple_name = temple['name']
        temples[temple_name] = temple
    
    return temples


@retry_on_failure(max_retries=3)
def get_temple_by_name(name: str) -> Optional[Dict]:
    """
    寺院名で寺院データを取得
    
    指定された寺院名に完全一致する寺院情報を取得します。
    
    Args:
        name: 寺院名（例: "東大寺"）
    
    Returns:
        Optional[Dict]: 寺院データ（見つからない場合はNone）
            例: {"name": "東大寺", "address": "奈良県...", ...}
    
    Example:
        temple = get_temple_by_name("東大寺")
        if temple:
            print(temple['address'])
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # 寺院名で検索（完全一致）
    response = client.table('temples').select('*').eq('name', name).execute()
    
    # データが存在する場合は最初の要素を返す
    if response.data:
        return response.data[0]
    
    # 見つからない場合はNone
    return None


@retry_on_failure(max_retries=3)
def create_temple(temple_data: Dict) -> Dict:
    """
    新しい寺院を追加
    
    寺院データをデータベースに追加します。
    id、created_at、updated_atは自動生成されるため、
    temple_dataに含めないでください。
    
    Args:
        temple_data: 寺院データの辞書
            必須フィールド: name（寺院名）
            任意フィールド: address, description, など
    
    Returns:
        Dict: 作成された寺院データ（自動生成フィールドを含む）
    
    Raises:
        Exception: 寺院の追加に失敗した場合
    
    Example:
        new_temple = {
            "name": "新寺",
            "address": "東京都...",
            "description": "説明文"
        }
        result = create_temple(new_temple)
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # 自動生成フィールドを除外したデータを準備
    # id, created_at, updated_atは自動的に設定される
    insert_data = {
        key: value for key, value in temple_data.items() 
        if key not in ['id', 'created_at', 'updated_at']
    }
    
    # データベースに挿入
    response = client.table('temples').insert(insert_data).execute()
    
    # 挿入結果を確認
    if response.data:
        return response.data[0]
    else:
        raise Exception("寺院の追加に失敗しました")


@retry_on_failure(max_retries=3)
def update_temple(name: str, temple_data: Dict) -> Dict:
    """
    寺院データを更新
    
    指定された寺院名の寺院情報を更新します。
    nameフィールド自体を変更する場合も、temple_dataに含めてください。
    
    Args:
        name: 更新対象の寺院名
        temple_data: 更新するフィールドの辞書
    
    Returns:
        Dict: 更新された寺院データ
    
    Raises:
        Exception: 更新に失敗した場合
    
    Example:
        update_data = {
            "address": "新しい住所",
            "description": "更新された説明"
        }
        result = update_temple("東大寺", update_data)
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # 自動生成フィールドを除外したデータを準備
    update_data = {
        key: value for key, value in temple_data.items() 
        if key not in ['id', 'created_at', 'updated_at']
    }
    
    # 指定された寺院名のレコードを更新
    response = client.table('temples').update(update_data).eq('name', name).execute()
    
    # 更新結果を確認
    if response.data:
        return response.data[0]
    else:
        raise Exception("寺院の更新に失敗しました")


@retry_on_failure(max_retries=3)
def delete_temple(name: str) -> bool:
    """
    寺院を削除
    
    指定された寺院名の寺院をデータベースから削除します。
    
    Args:
        name: 削除対象の寺院名
    
    Returns:
        bool: 削除成功した場合True、失敗した場合False
    
    Example:
        success = delete_temple("削除対象寺")
        if success:
            print("削除成功")
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # 指定された寺院名のレコードを削除
    response = client.table('temples').delete().eq('name', name).execute()
    
    # 削除されたレコード数を確認
    return len(response.data) > 0


# ============================================
# 項目設定（フィールド定義）操作
# ============================================

@retry_on_failure(max_retries=3)
def get_fields_config() -> List[Dict]:
    """
    項目設定を取得
    
    寺院データのフィールド定義（項目名、表示ラベル、表示順序など）を取得します。
    order（表示順序）の昇順でソートされています。
    
    Returns:
        List[Dict]: 項目設定のリスト
            例: [
                {"key": "name", "label": "寺院名", "order": 1},
                {"key": "address", "label": "住所", "order": 2},
                ...
            ]
    
    Example:
        fields = get_fields_config()
        for field in fields:
            print(f"{field['label']}: {field['key']}")
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # fieldsテーブルから全データを取得（order順）
    response = client.table('fields').select('*').order('order').execute()
    
    return response.data


@retry_on_failure(max_retries=3)
def update_fields_config(fields: List[Dict]) -> bool:
    """
    項目設定を更新
    
    寺院データのフィールド定義を一括更新します。
    既存の設定を全て削除してから、新しい設定を追加します。
    
    Args:
        fields: 新しい項目設定のリスト
            各要素は key、label、order を含む辞書
            例: [
                {"key": "name", "label": "寺院名", "order": 1},
                {"key": "address", "label": "住所", "order": 2}
            ]
    
    Returns:
        bool: 更新成功した場合True、失敗した場合False
    
    Example:
        new_fields = [
            {"key": "name", "label": "寺院名", "order": 1},
            {"key": "address", "label": "住所", "order": 2}
        ]
        success = update_fields_config(new_fields)
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    try:
        # 既存の設定を全て削除（id=0以外）
        # id=0は存在しないため、実質的に全削除
        client.table('fields').delete().neq('id', 0).execute()
        
        # 新しい設定を準備
        insert_data = [
            {
                'key': field['key'],        # フィールド名
                'label': field['label'],    # 表示ラベル
                'order': field['order']     # 表示順序
            }
            for field in fields
        ]
        
        # 新しい設定を一括追加
        client.table('fields').insert(insert_data).execute()
        
        return True
    
    except Exception as e:
        print(f"❌ 項目設定の更新エラー: {e}")
        return False

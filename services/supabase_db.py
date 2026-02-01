"""
Supabaseデータベース接続サービス

Google SheetsからSupabaseへの移行のための
データベース接続とCRUD操作を提供します。
"""

from supabase import create_client, Client
from config import Config
from typing import List, Dict, Optional, Any
from datetime import datetime
import pytz

# グローバルクライアント
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Supabaseクライアントを取得（シングルトン）
    
    Returns:
        Client: Supabaseクライアント
    
    Raises:
        ValueError: 設定が不足している場合
    """
    global _supabase_client
    
    if _supabase_client is None:
        if not Config.SUPABASE_URL or not Config.SUPABASE_SERVICE_KEY:
            raise ValueError(
                "Supabase設定が不足しています。"
                "環境変数 SUPABASE_URL と SUPABASE_SERVICE_KEY を設定してください。"
            )
        
        _supabase_client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_SERVICE_KEY
        )
        print("✅ Supabase接続完了")
    
    return _supabase_client


def get_jst_timestamp() -> str:
    """
    日本時間のタイムスタンプを取得
    
    Returns:
        str: ISO形式のタイムスタンプ
    """
    jst = pytz.timezone('Asia/Tokyo')
    return datetime.now(jst).isoformat()


# ============================================
# 寺院データ操作
# ============================================

def get_all_temples() -> Dict[str, Dict]:
    """
    すべての寺院データを取得
    
    Returns:
        Dict[str, Dict]: 寺院名をキーとした辞書
    """
    client = get_supabase_client()
    response = client.table('temples').select('*').order('name').execute()
    
    # 寺院名をキーにした辞書に変換
    temples = {}
    for temple in response.data:
        temples[temple['name']] = temple
    
    return temples


def get_temple_by_name(name: str) -> Optional[Dict]:
    """
    寺院名で寺院データを取得
    
    Args:
        name: 寺院名
    
    Returns:
        Optional[Dict]: 寺院データ（存在しない場合はNone）
    """
    client = get_supabase_client()
    response = client.table('temples').select('*').eq('name', name).execute()
    
    if response.data:
        return response.data[0]
    return None


def create_temple(temple_data: Dict) -> Dict:
    """
    新しい寺院を追加
    
    Args:
        temple_data: 寺院データ
    
    Returns:
        Dict: 作成された寺院データ
    
    Raises:
        Exception: 追加に失敗した場合
    """
    client = get_supabase_client()
    
    # timestampフィールドを除外（自動生成されるため）
    insert_data = {k: v for k, v in temple_data.items() 
                   if k not in ['id', 'created_at', 'updated_at']}
    
    response = client.table('temples').insert(insert_data).execute()
    
    if response.data:
        return response.data[0]
    else:
        raise Exception("寺院の追加に失敗しました")


def update_temple(name: str, temple_data: Dict) -> Dict:
    """
    寺院データを更新
    
    Args:
        name: 寺院名（更新対象）
        temple_data: 更新データ
    
    Returns:
        Dict: 更新された寺院データ
    
    Raises:
        Exception: 更新に失敗した場合
    """
    client = get_supabase_client()
    
    # timestampフィールドを除外
    update_data = {k: v for k, v in temple_data.items() 
                   if k not in ['id', 'created_at', 'updated_at']}
    
    response = client.table('temples').update(update_data).eq('name', name).execute()
    
    if response.data:
        return response.data[0]
    else:
        raise Exception("寺院の更新に失敗しました")


def delete_temple(name: str) -> bool:
    """
    寺院を削除
    
    Args:
        name: 寺院名
    
    Returns:
        bool: 削除成功した場合True
    """
    client = get_supabase_client()
    response = client.table('temples').delete().eq('name', name).execute()
    return len(response.data) > 0


# ============================================
# 項目設定操作
# ============================================

def get_fields_config() -> List[Dict]:
    """
    項目設定を取得
    
    Returns:
        List[Dict]: 項目設定のリスト（order順）
    """
    client = get_supabase_client()
    response = client.table('fields').select('*').order('order').execute()
    return response.data


def update_fields_config(fields: List[Dict]) -> bool:
    """
    項目設定を更新
    
    Args:
        fields: 項目設定のリスト
    
    Returns:
        bool: 更新成功した場合True
    """
    client = get_supabase_client()
    
    try:
        # 既存の設定を削除
        client.table('fields').delete().neq('id', 0).execute()
        
        # 新しい設定を追加
        insert_data = [
            {
                'key': field['key'],
                'label': field['label'],
                'order': field['order']
            }
            for field in fields
        ]
        client.table('fields').insert(insert_data).execute()
        return True
    except Exception as e:
        print(f"項目設定の更新エラー: {e}")
        return False

# ============================================
# ログ操作
# ============================================

def add_log(user_name: str = None, user_id: str = None, action: str = '', details: str = '', ip_address: str = '') -> bool:
    from utils.helpers import get_jst_timestamp
    from flask import session
    
    if not user_name:
        user_name = session.get('user_name') or session.get('name', '不明')
    if not user_id:
        user_id = session.get('user_id', 'unknown')
    
    client = get_supabase_client()
    
    try:
        log_data = {
            'timestamp': get_jst_timestamp(),
            'user': user_name,
            'user_id': user_id,
            'action': action,
            'details': details,
            'ip_address': ip_address
        }
        client.table('logs').insert(log_data).execute()
        print(f"✅ ログ記録: {user_name} ({user_id}) - {action}")
        return True
    except Exception as e:
        print(f"❌ ログ記録エラー: {e}")
        return False
            
def get_recent_logs(limit: int = 100) -> List[Dict]:
    """
    最近のログを取得
    
    Args:
        limit: 取得件数
    
    Returns:
        List[Dict]: ログのリスト
    """
    client = get_supabase_client()
    response = client.table('logs').select('*').order('timestamp', desc=True).limit(limit).execute()
    return response.data


# ============================================
# アクセスログ操作
# ============================================

def add_access_log(temple_name: str, question: str = "", user_name: str = "") -> bool:
    """
    アクセスログを記録
    
    Google Sheets access_log列: timestamp, temple_name, query
    Supabase access_logs列: timestamp, temple_name, query
    
    Args:
        temple_name: 寺院名
        question: 質問内容（query列に格納）
        user_name: 使用しない（互換性のため残す）
    
    Returns:
        bool: 記録成功した場合True
    """
    from utils.helpers import get_jst_timestamp
    client = get_supabase_client()
    
    try:
        log_data = {
            'timestamp': get_jst_timestamp(),
            'temple_name': temple_name,
            'query': question  # ★修正: question → query列、user_name削除
        }
        client.table('access_logs').insert(log_data).execute()
        return True
    except Exception as e:
        print(f"アクセスログ記録エラー: {e}")
        return False


def get_access_logs(temple_name: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """
    アクセスログを取得
    
    Args:
        temple_name: 寺院名（指定した場合、その寺院のログのみ）
        limit: 取得件数
    
    Returns:
        List[Dict]: アクセスログのリスト
    """
    client = get_supabase_client()
    query = client.table('access_logs').select('*')
    
    if temple_name:
        query = query.eq('temple_name', temple_name)
    
    response = query.order('timestamp', desc=True).limit(limit).execute()
    return response.data


# ============================================
# コメント操作
# ============================================

def add_comment(temple_name: str, user_name: str, comment: str) -> bool:
    """
    コメントを追加
    
    Google Sheets comments列: timestamp, temple_name, user_name, comment
    Supabase comments列: timestamp, temple_name, user_name, comment
    
    Args:
        temple_name: 寺院名
        user_name: ユーザー名
        comment: コメント内容
    
    Returns:
        bool: 追加成功した場合True
    """
    from utils.helpers import get_jst_timestamp
    client = get_supabase_client()
    
    try:
        comment_data = {
            'timestamp': get_jst_timestamp(),  # ★追加: timestamp
            'temple_name': temple_name,
            'user_name': user_name,
            'comment': comment
        }
        client.table('comments').insert(comment_data).execute()
        return True
    except Exception as e:
        print(f"コメント追加エラー: {e}")
        return False


def get_comments(temple_name: str) -> List[Dict]:
    """
    寺院のコメントを取得
    
    Args:
        temple_name: 寺院名
    
    Returns:
        List[Dict]: コメントのリスト
    """
    client = get_supabase_client()
    response = client.table('comments').select('*').eq('temple_name', temple_name).order('timestamp', desc=True).execute()
    return response.data


# ============================================
# ユーザー操作
# ============================================

def get_user_by_id(user_id: str) -> Optional[Dict]:
    """
    ユーザーIDでユーザーを取得
    
    Args:
        user_id: ユーザーID
    
    Returns:
        Optional[Dict]: ユーザーデータ（存在しない場合はNone）
    """
    client = get_supabase_client()
    response = client.table('users').select('*').eq('user_id', user_id).execute()
    
    if response.data:
        return response.data[0]
    return None


def get_all_users() -> List[Dict]:
    """
    すべてのユーザーを取得
    
    Returns:
        List[Dict]: ユーザーのリスト
    """
    client = get_supabase_client()
    response = client.table('users').select('*').order('name').execute()  # ★修正: user_name → name
    return response.data


def create_user(user_data: Dict) -> Dict:
    """
    新しいユーザーを作成
    
    Args:
        user_data: ユーザーデータ
    
    Returns:
        Dict: 作成されたユーザーデータ
    """
    client = get_supabase_client()
    response = client.table('users').insert(user_data).execute()
    return response.data[0]


def update_user(user_id: str, user_data: Dict) -> Dict:
    """
    ユーザー情報を更新
    
    Args:
        user_id: ユーザーID
        user_data: 更新データ
    
    Returns:
        Dict: 更新されたユーザーデータ
    """
    client = get_supabase_client()
    response = client.table('users').update(user_data).eq('user_id', user_id).execute()
    return response.data[0]


def delete_user(user_id: str) -> bool:
    """
    ユーザーを削除
    
    Args:
        user_id: ユーザーID
    
    Returns:
        bool: 削除成功した場合True
    """
    client = get_supabase_client()
    response = client.table('users').delete().eq('user_id', user_id).execute()
    return len(response.data) > 0

# ========================================
# お気に入り機能
# ========================================

def get_user_favorites(user_id):
    """ユーザーのお気に入りリストを取得"""
    try:
        response = get_supabase_client().table('favorites').select('temple_name').eq('user_id', user_id).execute()
        return [item['temple_name'] for item in response.data]
    except Exception as e:
        print(f"❌ お気に入り取得エラー: {e}")
        return []

def add_favorite(user_id, temple_name):
    """お気に入りに追加"""
    try:
        get_supabase_client().table('favorites').insert({
            'user_id': user_id,
            'temple_name': temple_name
        }).execute()
        print(f"⭐ お気に入り追加: {temple_name} (ユーザー: {user_id})")
        return True
    except Exception as e:
        print(f"❌ お気に入り追加エラー: {e}")
        return False

def remove_favorite(user_id, temple_name):
    """お気に入りから削除"""
    try:
        get_supabase_client().table('favorites').delete().eq('user_id', user_id).eq('temple_name', temple_name).execute()
        print(f"☆ お気に入り削除: {temple_name} (ユーザー: {user_id})")
        return True
    except Exception as e:
        print(f"❌ お気に入り削除エラー: {e}")
        return False
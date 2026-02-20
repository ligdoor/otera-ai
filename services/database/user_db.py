"""
ユーザーデータベース操作モジュール

ユーザー情報の取得、作成、更新、削除などのCRUD操作と
お気に入り機能、通知機能を提供します。
"""

import logging
from typing import Dict, List, Optional
from .base import get_supabase_client, retry_on_failure

logger = logging.getLogger(__name__)


# ============================================
# ユーザーCRUD操作
# ============================================

@retry_on_failure(max_retries=3)
def get_user_by_id(user_id: str) -> Optional[Dict]:
    """
    ユーザーIDでユーザーを取得
    
    指定されたユーザーIDに一致するユーザー情報を取得します。
    
    Args:
        user_id: ユーザーID（例: "user001"）
    
    Returns:
        Optional[Dict]: ユーザーデータ（見つからない場合はNone）
            例: {
                "user_id": "user001",
                "name": "山田太郎",
                "email": "yamada@example.com",
                "role": "admin"
            }
    
    Example:
        user = get_user_by_id("user001")
        if user:
            logger.debug(user['name'])
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # ユーザーIDで検索
    response = client.table('users').select('*').eq('user_id', user_id).execute()
    
    # データが存在する場合は最初の要素を返す
    if response.data:
        return response.data[0]
    
    return None


@retry_on_failure(max_retries=3)
def get_user_by_email(email: str) -> Optional[Dict]:
    """
    メールアドレスでユーザーを取得
    
    指定されたメールアドレスに一致するユーザー情報を取得します。
    パスワードリセットやメール認証などで使用されます。
    
    Args:
        email: メールアドレス（例: "user@example.com"）
    
    Returns:
        Optional[Dict]: ユーザーデータ（見つからない場合はNone）
            例: {
                "user_id": "user001",
                "name": "山田太郎",
                "email": "yamada@example.com",
                "role": "admin"
            }
    
    Example:
        user = get_user_by_email("user@example.com")
        if user:
            logger.debug(user['name'])
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # メールアドレスで検索
    response = client.table('users').select('*').eq('email', email).execute()
    
    # データが存在する場合は最初の要素を返す
    if response.data:
        return response.data[0]
    
    return None


@retry_on_failure(max_retries=3)
def get_all_users() -> List[Dict]:
    """
    すべてのユーザーを取得
    
    データベースから全ユーザー情報を取得します。
    名前順（昇順）にソートされています。
    
    Returns:
        List[Dict]: ユーザーデータのリスト
            例: [
                {"user_id": "user001", "name": "山田太郎", ...},
                {"user_id": "user002", "name": "佐藤花子", ...}
            ]
    
    Example:
        users = get_all_users()
        for user in users:
            logger.debug(user['name'])
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # usersテーブルから全データを取得（名前順）
    response = client.table('users').select('*').order('name').execute()
    
    return response.data


@retry_on_failure(max_retries=3)
def create_user(user_data: Dict) -> Dict:
    """
    新しいユーザーを作成
    
    ユーザーデータをデータベースに追加します。
    
    Args:
        user_data: ユーザーデータの辞書
            必須フィールド: user_id, name, email, password_hash, role
            任意フィールド: department, last_login など
    
    Returns:
        Dict: 作成されたユーザーデータ
    
    Example:
        new_user = {
            "user_id": "user003",
            "name": "鈴木一郎",
            "email": "suzuki@example.com",
            "password_hash": "...",
            "role": "editor"
        }
        result = create_user(new_user)
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # データベースに挿入
    response = client.table('users').insert(user_data).execute()
    
    return response.data[0]


@retry_on_failure(max_retries=3)
def update_user(user_id: str, user_data: Dict) -> Dict:
    """
    ユーザー情報を更新
    
    指定されたユーザーIDのユーザー情報を更新します。
    
    Args:
        user_id: 更新対象のユーザーID
        user_data: 更新するフィールドの辞書
    
    Returns:
        Dict: 更新されたユーザーデータ
    
    Example:
        update_data = {
            "email": "new_email@example.com",
            "role": "admin"
        }
        result = update_user("user001", update_data)
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # 指定されたユーザーIDのレコードを更新
    response = client.table('users').update(user_data).eq('user_id', user_id).execute()
    
    return response.data[0]


@retry_on_failure(max_retries=3)
def delete_user(user_id: str) -> bool:
    """
    ユーザーを削除
    
    指定されたユーザーIDのユーザーをデータベースから削除します。
    
    Args:
        user_id: 削除対象のユーザーID
    
    Returns:
        bool: 削除成功した場合True
    
    Example:
        success = delete_user("user003")
        if success:
            logger.debug("削除成功")
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # 指定されたユーザーIDのレコードを削除
    response = client.table('users').delete().eq('user_id', user_id).execute()
    
    return len(response.data) > 0


# ============================================
# お気に入り機能
# ============================================

@retry_on_failure(max_retries=3)
def get_user_favorites(user_id: str) -> List[str]:
    """
    ユーザーのお気に入りリストを取得
    
    指定されたユーザーがお気に入りに登録している寺院名のリストを取得します。
    
    Args:
        user_id: ユーザーID
    
    Returns:
        List[str]: お気に入り寺院名のリスト
            例: ["東大寺", "清水寺", "金閣寺"]
    
    Example:
        favorites = get_user_favorites("user001")
        logger.debug(f"お気に入り数: {len(favorites)}")
    """
    try:
        # Supabaseクライアントを取得
        client = get_supabase_client()
        
        # ユーザーIDで検索してtemple_nameカラムのみ取得
        response = client.table('favorites').select('temple_name').eq('user_id', user_id).execute()
        
        # temple_nameのリストを作成
        return [item['temple_name'] for item in response.data]
    
    except Exception as e:
        logger.error(f"❌ お気に入り取得エラー: {e}")
        return []


@retry_on_failure(max_retries=3)
def add_favorite(user_id: str, temple_name: str) -> bool:
    """
    お気に入りに追加
    
    指定された寺院をユーザーのお気に入りに追加します。
    
    Args:
        user_id: ユーザーID
        temple_name: 寺院名
    
    Returns:
        bool: 追加成功した場合True
    
    Example:
        success = add_favorite("user001", "東大寺")
        if success:
            logger.debug("お気に入りに追加しました")
    """
    try:
        # Supabaseクライアントを取得
        client = get_supabase_client()
        
        # お気に入りレコードを追加
        client.table('favorites').insert({
            'user_id': user_id,
            'temple_name': temple_name
        }).execute()
        
        logger.debug(f"⭐ お気に入り追加: {temple_name} (ユーザー: {user_id})")
        return True
    
    except Exception as e:
        logger.error(f"❌ お気に入り追加エラー: {e}")
        return False


@retry_on_failure(max_retries=3)
def remove_favorite(user_id: str, temple_name: str) -> bool:
    """
    お気に入りから削除
    
    指定された寺院をユーザーのお気に入りから削除します。
    
    Args:
        user_id: ユーザーID
        temple_name: 寺院名
    
    Returns:
        bool: 削除成功した場合True
    
    Example:
        success = remove_favorite("user001", "東大寺")
        if success:
            logger.debug("お気に入りから削除しました")
    """
    try:
        # Supabaseクライアントを取得
        client = get_supabase_client()
        
        # ユーザーIDと寺院名が一致するレコードを削除
        client.table('favorites').delete().eq('user_id', user_id).eq('temple_name', temple_name).execute()
        
        logger.debug(f"☆ お気に入り削除: {temple_name} (ユーザー: {user_id})")
        return True
    
    except Exception as e:
        logger.error(f"❌ お気に入り削除エラー: {e}")
        return False


# ============================================
# 通知機能
# ============================================

@retry_on_failure(max_retries=3)
def get_user_notifications(user_id: str, unread_only: bool = False) -> List[Dict]:
    """
    ユーザーの通知を取得
    
    指定されたユーザー宛の通知と全体通知を取得します。
    作成日時の新しい順にソートされ、最大50件まで取得します。
    
    Args:
        user_id: ユーザーID
        unread_only: True の場合、未読通知のみ取得（デフォルト: False）
    
    Returns:
        List[Dict]: 通知データのリスト
            例: [
                {
                    "id": 1,
                    "title": "お知らせ",
                    "message": "新機能が追加されました",
                    "is_read": False,
                    ...
                }
            ]
    
    Example:
        notifications = get_user_notifications("user001", unread_only=True)
        logger.debug(f"未読通知: {len(notifications)}件")
    """
    try:
        # Supabaseクライアントを取得
        client = get_supabase_client()
        
        # 通知テーブルから取得開始
        query = client.table('notifications').select('*')
        
        # 自分宛の通知 OR 全体通知（user_id が null）
        query = query.or_(f'user_id.eq.{user_id},user_id.is.null')
        
        # 未読のみフィルター（オプション）
        if unread_only:
            query = query.eq('is_read', False)
        
        # 作成日時の新しい順で最大50件取得
        response = query.order('created_at', desc=True).limit(50).execute()
        
        return response.data
    
    except Exception as e:
        logger.error(f"❌ 通知取得エラー: {e}")
        return []


@retry_on_failure(max_retries=3)
def get_unread_count(user_id: str) -> int:
    """
    未読通知数を取得
    
    指定されたユーザーの未読通知件数を取得します。
    
    Args:
        user_id: ユーザーID
    
    Returns:
        int: 未読通知の件数
    
    Example:
        count = get_unread_count("user001")
        logger.debug(f"未読通知: {count}件")
    """
    try:
        # Supabaseクライアントを取得
        client = get_supabase_client()
        
        # 件数のみ取得するクエリ
        query = client.table('notifications').select('id', count='exact')
        
        # 自分宛の通知 OR 全体通知
        query = query.or_(f'user_id.eq.{user_id},user_id.is.null')
        
        # 未読のみ
        query = query.eq('is_read', False)
        
        response = query.execute()
        
        return response.count
    
    except Exception as e:
        logger.error(f"❌ 未読数取得エラー: {e}")
        return 0


@retry_on_failure(max_retries=3)
def mark_notification_read(notification_id: int) -> bool:
    """
    通知を既読にする
    
    指定されたIDの通知を既読状態に更新します。
    
    Args:
        notification_id: 通知ID
    
    Returns:
        bool: 更新成功した場合True
    
    Example:
        success = mark_notification_read(123)
    """
    try:
        # Supabaseクライアントを取得
        client = get_supabase_client()
        
        # 既読フラグを更新
        client.table('notifications').update({
            'is_read': True
        }).eq('id', notification_id).execute()
        
        return True
    
    except Exception as e:
        logger.error(f"❌ 通知既読エラー: {e}")
        return False


@retry_on_failure(max_retries=3)
def mark_all_notifications_read(user_id: str) -> bool:
    """
    すべての通知を既読にする
    
    指定されたユーザーの全ての通知（個人宛 + 全体通知）を既読状態にします。
    
    Args:
        user_id: ユーザーID
    
    Returns:
        bool: 更新成功した場合True
    
    Example:
        success = mark_all_notifications_read("user001")
    """
    try:
        # Supabaseクライアントを取得
        client = get_supabase_client()
        
        # 自分宛の通知を既読に
        client.table('notifications').update({
            'is_read': True
        }).eq('user_id', user_id).execute()
        
        # 全体通知も既読に
        client.table('notifications').update({
            'is_read': True
        }).is_('user_id', 'null').execute()
        
        return True
    
    except Exception as e:
        logger.error(f"❌ 一括既読エラー: {e}")
        return False


@retry_on_failure(max_retries=3)
def create_notification(
    title: str, 
    message: str, 
    user_id: Optional[str] = None, 
    notification_type: str = 'info', 
    related_temple: Optional[str] = None
) -> bool:
    """
    通知を作成（管理者用）
    
    新しい通知をデータベースに追加します。
    user_idを指定すると個人宛通知、Noneの場合は全体通知になります。
    
    Args:
        title: 通知タイトル
        message: 通知メッセージ
        user_id: 宛先ユーザーID（Noneの場合は全体通知）
        notification_type: 通知タイプ（'info', 'warning', 'success', 'error'）
        related_temple: 関連する寺院名（任意）
    
    Returns:
        bool: 作成成功した場合True
    
    Example:
        # 個人宛通知
        create_notification(
            title="承認完了",
            message="アカウントが承認されました",
            user_id="user001",
            notification_type="success"
        )
        
        # 全体通知
        create_notification(
            title="メンテナンスのお知らせ",
            message="明日午前2時からメンテナンスを行います"
        )
    """
    try:
        # Supabaseクライアントを取得
        client = get_supabase_client()
        
        # 通知データを作成
        notification_data = {
            'user_id': user_id,  # Noneの場合は全体通知
            'title': title,
            'message': message,
            'type': notification_type,
            'related_temple': related_temple
        }
        
        # データベースに追加
        client.table('notifications').insert(notification_data).execute()
        
        logger.info(f"✅ 通知作成: {title}")
        return True
    
    except Exception as e:
        logger.error(f"❌ 通知作成エラー: {e}")
        return False

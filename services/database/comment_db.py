"""
コメントデータベース操作モジュール

寺院に対するユーザーコメントの追加、取得、削除機能を提供します。
"""

from typing import List, Dict
from .base import get_supabase_client, get_jst_timestamp, retry_on_failure


# ============================================
# コメントCRUD操作
# ============================================

@retry_on_failure(max_retries=3)
def add_comment(temple_name: str, user_name: str, comment: str) -> bool:
    """
    コメントを追加
    
    指定された寺院に対してユーザーコメントを追加します。
    タイムスタンプは自動的に設定されます。
    
    Args:
        temple_name: 寺院名
        user_name: コメント投稿者のユーザー名
        comment: コメント内容
    
    Returns:
        bool: 追加成功した場合True
    
    Example:
        success = add_comment(
            temple_name="東大寺",
            user_name="山田太郎",
            comment="とても美しいお寺でした"
        )
        if success:
            print("コメントを投稿しました")
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    try:
        # コメントデータを準備
        # Google Sheets版と互換: timestamp, temple_name, user_name, comment
        comment_data = {
            'timestamp': get_jst_timestamp(),  # 日本時間のタイムスタンプを追加
            'temple_name': temple_name,
            'user_name': user_name,
            'comment': comment
        }
        
        # commentsテーブルに挿入
        client.table('comments').insert(comment_data).execute()
        
        print(f"✅ コメント追加: {temple_name} - {user_name}")
        return True
    
    except Exception as e:
        print(f"❌ コメント追加エラー: {e}")
        return False


@retry_on_failure(max_retries=3)
def get_comments(temple_name: str) -> List[Dict]:
    """
    寺院のコメントを取得
    
    指定された寺院に投稿されたコメントを全て取得します。
    タイムスタンプの新しい順（降順）にソートされています。
    
    Args:
        temple_name: 寺院名
    
    Returns:
        List[Dict]: コメントデータのリスト
            例: [
                {
                    "id": 123,
                    "timestamp": "2024-01-15T10:30:00+09:00",
                    "temple_name": "東大寺",
                    "user_name": "山田太郎",
                    "comment": "素晴らしいお寺でした"
                },
                ...
            ]
    
    Example:
        comments = get_comments("東大寺")
        
        print(f"コメント数: {len(comments)}件")
        for comment in comments:
            print(f"{comment['user_name']}: {comment['comment']}")
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # 指定された寺院名のコメントを新しい順で取得
    response = client.table('comments').select('*').eq('temple_name', temple_name).order('timestamp', desc=True).execute()
    
    return response.data


@retry_on_failure(max_retries=3)
def get_all_comments(limit: int = 100) -> List[Dict]:
    """
    全てのコメントを取得
    
    全寺院のコメントを取得します。
    管理画面での全体的なコメント管理などに使用します。
    
    Args:
        limit: 取得件数（デフォルト: 100）
    
    Returns:
        List[Dict]: コメントデータのリスト（タイムスタンプ降順）
    
    Example:
        all_comments = get_all_comments(limit=50)
        for comment in all_comments:
            print(f"{comment['temple_name']} - {comment['user_name']}")
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # 全コメントを新しい順で取得
    response = client.table('comments').select('*').order('timestamp', desc=True).limit(limit).execute()
    
    return response.data


@retry_on_failure(max_retries=3)
def delete_comment(comment_id: int) -> bool:
    """
    コメントを削除
    
    指定されたIDのコメントをデータベースから削除します。
    管理者がコメントを管理する際に使用します。
    
    Args:
        comment_id: コメントID（データベースの主キー）
    
    Returns:
        bool: 削除成功した場合True
    
    Example:
        success = delete_comment(123)
        if success:
            print("コメントを削除しました")
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    try:
        # 指定されたIDのコメントを削除
        response = client.table('comments').delete().eq('id', comment_id).execute()
        
        # 削除されたレコード数を確認
        if len(response.data) > 0:
            print(f"✅ コメント削除: ID {comment_id}")
            return True
        else:
            print(f"⚠️ コメントが見つかりませんでした: ID {comment_id}")
            return False
    
    except Exception as e:
        print(f"❌ コメント削除エラー: {e}")
        return False


@retry_on_failure(max_retries=3)
def delete_temple_comments(temple_name: str) -> int:
    """
    特定寺院の全コメントを削除
    
    指定された寺院に関連する全てのコメントを削除します。
    寺院削除時のクリーンアップなどに使用します。
    
    Args:
        temple_name: 寺院名
    
    Returns:
        int: 削除されたコメント数
    
    Example:
        deleted_count = delete_temple_comments("削除対象寺")
        print(f"{deleted_count}件のコメントを削除しました")
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    try:
        # 指定された寺院名の全コメントを削除
        response = client.table('comments').delete().eq('temple_name', temple_name).execute()
        
        # 削除されたレコード数
        deleted_count = len(response.data)
        
        print(f"✅ {temple_name}のコメント削除: {deleted_count}件")
        return deleted_count
    
    except Exception as e:
        print(f"❌ コメント一括削除エラー: {e}")
        return 0


# ============================================
# コメント統計
# ============================================

def get_comment_statistics() -> Dict[str, int]:
    """
    寺院別のコメント数統計を取得
    
    各寺院に投稿されたコメント数を集計します。
    
    Returns:
        Dict[str, int]: 寺院名をキー、コメント数を値とする辞書
            例: {"東大寺": 25, "清水寺": 18, ...}
    
    Example:
        stats = get_comment_statistics()
        
        # コメント数でソート
        sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        
        # トップ10を表示
        print("コメントが多い寺院トップ10:")
        for temple, count in sorted_stats[:10]:
            print(f"{temple}: {count}件")
    """
    # 全コメントを取得（多めに取得）
    all_comments = get_all_comments(limit=10000)
    
    # 寺院名ごとにカウント
    temple_comment_counts = {}
    
    for comment in all_comments:
        temple_name = comment.get('temple_name', '')
        
        # 寺院名が存在する場合のみカウント
        if temple_name:
            temple_comment_counts[temple_name] = temple_comment_counts.get(temple_name, 0) + 1
    
    return temple_comment_counts


def get_recent_comments_all_temples(limit: int = 10) -> List[Dict]:
    """
    全寺院の最新コメントを取得
    
    全ての寺院から最新のコメントを取得します。
    トップページでの「最新のコメント」表示などに使用します。
    
    Args:
        limit: 取得件数（デフォルト: 10）
    
    Returns:
        List[Dict]: 最新コメントのリスト（タイムスタンプ降順）
    
    Example:
        recent = get_recent_comments_all_temples(limit=5)
        
        print("最新のコメント:")
        for comment in recent:
            print(f"{comment['temple_name']} - {comment['user_name']}: {comment['comment'][:30]}...")
    """
    return get_all_comments(limit=limit)

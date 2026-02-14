"""
データベースパッケージ

Supabaseデータベースへのアクセスを提供するモジュール群です。

モジュール構成:
    - base: 基本接続とユーティリティ
    - temple_db: 寺院データ操作
    - user_db: ユーザー管理・お気に入り・通知
    - log_db: ログ・統計
    - comment_db: コメント管理

使用例:
    from services.database import get_all_temples, add_log, get_comments
    
    # 寺院データ取得
    temples = get_all_temples()
    
    # ログ記録
    add_log(action="ログイン", details="正常にログインしました")
    
    # コメント取得
    comments = get_comments("東大寺")
"""

# ============================================
# 基本接続・ユーティリティ
# ============================================
from .base import (
    get_supabase_client,
    get_jst_timestamp,
    retry_on_failure,
    reset_client
)

# ============================================
# 寺院データ操作
# ============================================
from .temple_db import (
    # 寺院CRUD
    get_all_temples,
    get_temple_by_name,
    create_temple,
    update_temple,
    delete_temple,
    
    # 項目設定
    get_fields_config,
    update_fields_config
)

# ============================================
# ユーザー管理
# ============================================
from .user_db import (
    # ユーザーCRUD
    get_user_by_id,
    get_user_by_email,
    get_all_users,
    create_user,
    update_user,
    delete_user,
    
    # お気に入り機能
    get_user_favorites,
    add_favorite,
    remove_favorite,
    
    # 通知機能
    get_user_notifications,
    get_unread_count,
    mark_notification_read,
    mark_all_notifications_read,
    create_notification
)

# ============================================
# ログ・統計
# ============================================
from .log_db import (
    # システムログ
    add_log,
    get_recent_logs,
    
    # アクセスログ
    add_access_log,
    get_access_logs,
    
    # 統計
    get_access_statistics,
    get_top_accessed_temples
)

# ============================================
# コメント管理
# ============================================
from .comment_db import (
    # コメントCRUD
    add_comment,
    get_comments,
    get_all_comments,
    delete_comment,
    delete_temple_comments,
    
    # コメント統計
    get_comment_statistics,
    get_recent_comments_all_temples
)

# ============================================
# パッケージ情報
# ============================================
__all__ = [
    # 基本
    'get_supabase_client',
    'get_jst_timestamp',
    'retry_on_failure',
    'reset_client',
    
    # 寺院
    'get_all_temples',
    'get_temple_by_name',
    'create_temple',
    'update_temple',
    'delete_temple',
    'get_fields_config',
    'update_fields_config',
    
    # ユーザー
    'get_user_by_id',
    'get_user_by_email',
    'get_all_users',
    'create_user',
    'update_user',
    'delete_user',
    'get_user_favorites',
    'add_favorite',
    'remove_favorite',
    'get_user_notifications',
    'get_unread_count',
    'mark_notification_read',
    'mark_all_notifications_read',
    'create_notification',
    
    # ログ
    'add_log',
    'get_recent_logs',
    'add_access_log',
    'get_access_logs',
    'get_access_statistics',
    'get_top_accessed_temples',
    
    # コメント
    'add_comment',
    'get_comments',
    'get_all_comments',
    'delete_comment',
    'delete_temple_comments',
    'get_comment_statistics',
    'get_recent_comments_all_temples',
]

__version__ = '1.0.0'
__author__ = 'Temple Site Team'

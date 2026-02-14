"""
Supabaseデータベースモジュール - 後方互換性レイヤー

⚠️ 非推奨: このモジュールは後方互換性のためのみ提供されています。
新しいコードでは services.database を使用してください。

移行ガイド:
    Before: from services.supabase_db import get_supabase_client
    After:  from services.database import get_supabase_client

このファイルは将来のバージョンで削除される予定です。
"""

import warnings

# 非推奨警告を表示
warnings.warn(
    "\n"
    "=" * 70 + "\n"
    "⚠️  services.supabase_db は非推奨です\n"
    "=" * 70 + "\n"
    "このモジュールは後方互換性のためのみ提供されています。\n"
    "新しいコードでは services.database を使用してください。\n"
    "\n"
    "移行方法:\n"
    "  Before: from services.supabase_db import xxx\n"
    "  After:  from services.database import xxx\n"
    "\n"
    "詳細は MIGRATION_GUIDE.md を参照してください。\n"
    "=" * 70,
    DeprecationWarning,
    stacklevel=2
)

# ============================================
# 新しいモジュールから全てをインポート
# ============================================

# 基本機能
from services.database.base import (
    get_supabase_client,
    get_jst_timestamp,
    reset_client
)

# 寺院関連
from services.database.temple_db import (
    get_all_temples,
    get_temple_by_name,
    create_temple,
    update_temple,
    delete_temple,
    get_fields_config,
    update_fields_config
)

# ユーザー関連
from services.database.user_db import (
    get_user_by_id,
    get_user_by_email,
    get_all_users,
    create_user,
    update_user,
    delete_user,
    get_user_favorites,
    add_favorite,
    remove_favorite,
    get_user_notifications,
    mark_notification_read,
    mark_all_notifications_read,
    create_notification,
    get_unread_count
)

# 後方互換性のためのエイリアス
get_unread_notification_count = get_unread_count

# ログ関連
from services.database.log_db import (
    add_log,
    get_recent_logs,
    add_access_log,
    get_access_logs,
    get_access_statistics,
    get_top_accessed_temples
)

# コメント関連
from services.database.comment_db import (
    add_comment,
    get_comments,
    delete_comment,
    delete_temple_comments,
    get_comment_statistics
)

# ============================================
# エクスポートリスト
# ============================================

__all__ = [
    # 基本
    'get_supabase_client',
    'get_jst_timestamp',
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
    'mark_notification_read',
    'mark_all_notifications_read',
    'create_notification',
    'get_unread_count',
    'get_unread_notification_count',  # エイリアス
    
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
    'delete_comment',
    'delete_temple_comments',
    'get_comment_statistics',
]

"""
ログ・統計データベース操作モジュール

システムログ、アクセスログの記録と取得、
統計情報の集計機能を提供します。
"""

import logging
from typing import List, Dict, Optional
from .base import get_supabase_client, get_jst_timestamp, retry_on_failure

logger = logging.getLogger(__name__)


# ============================================
# システムログ操作
# ============================================

@retry_on_failure(max_retries=3)
def add_log(
    user_name: Optional[str] = None, 
    user_id: Optional[str] = None, 
    action: str = '', 
    details: str = '', 
    ip_address: str = ''
) -> bool:
    """
    システムログを記録
    
    ユーザーの操作履歴（ログイン、データ更新など）を記録します。
    user_nameとuser_idが指定されていない場合は、セッション情報から自動取得を試みます。
    
    Args:
        user_name: ユーザー名（未指定の場合はセッションから取得）
        user_id: ユーザーID（未指定の場合はセッションから取得）
        action: 操作内容（例: "ログイン", "データ更新"）
        details: 操作の詳細情報
        ip_address: アクセス元IPアドレス
    
    Returns:
        bool: 記録成功した場合True
    
    Example:
        add_log(
            user_name="山田太郎",
            user_id="user001",
            action="寺院データ更新",
            details="東大寺の住所を変更",
            ip_address="192.168.1.1"
        )
    """
    # セッション情報から取得を試みる
    if not user_name or not user_id:
        from flask import session
        
        if not user_name:
            user_name = session.get('user_name') or session.get('name', '不明')
        
        if not user_id:
            user_id = session.get('user_id', 'unknown')
    
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    try:
        # ログデータを準備
        log_data = {
            'timestamp': get_jst_timestamp(),  # 日本時間のタイムスタンプ
            'user': user_name,
            'user_id': user_id,
            'action': action,
            'details': details,
            'ip_address': ip_address
        }
        
        # logsテーブルに挿入
        client.table('logs').insert(log_data).execute()
        
        logger.info(f"✅ ログ記録: {user_name} ({user_id}) - {action}")
        return True
    
    except Exception as e:
        logger.error(f"❌ ログ記録エラー: {e}")
        return False


@retry_on_failure(max_retries=3)
def get_recent_logs(limit: int = 100) -> List[Dict]:
    """
    最近のシステムログを取得
    
    タイムスタンプの新しい順にログを取得します。
    管理画面でのログ表示などに使用します。
    
    Args:
        limit: 取得件数（デフォルト: 100）
    
    Returns:
        List[Dict]: ログデータのリスト
            例: [
                {
                    "timestamp": "2024-01-15T10:30:00+09:00",
                    "user": "山田太郎",
                    "action": "ログイン",
                    ...
                }
            ]
    
    Example:
        logs = get_recent_logs(limit=50)
        for log in logs:
            logger.debug(f"{log['timestamp']}: {log['action']}")
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # logsテーブルから最新データを取得
    response = client.table('logs').select('*').order('timestamp', desc=True).limit(limit).execute()
    
    return response.data


# ============================================
# アクセスログ操作
# ============================================

@retry_on_failure(max_retries=3)
def add_access_log(temple_name: str, question: str = "", user_name: str = "") -> bool:
    """
    アクセスログを記録
    
    寺院情報へのアクセス履歴を記録します。
    どの寺院がどのような質問で閲覧されたかを追跡します。
    
    Note:
        user_name パラメータは互換性のため残していますが、現在は使用されません。
        Google Sheets版との互換性を保つための措置です。
    
    Args:
        temple_name: 閲覧された寺院名
        question: 質問内容（AI質問応答で使用された質問文）
        user_name: （非推奨・互換性のため残存）
    
    Returns:
        bool: 記録成功した場合True
    
    Example:
        add_access_log(
            temple_name="東大寺",
            question="東大寺の大仏について教えてください"
        )
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    try:
        # アクセスログデータを準備
        # Google Sheets版: timestamp, temple_name, query
        # Supabase版: timestamp, temple_name, query
        log_data = {
            'timestamp': get_jst_timestamp(),
            'temple_name': temple_name,
            'query': question  # questionをquery列に格納
        }
        
        # access_logsテーブルに挿入
        client.table('access_logs').insert(log_data).execute()
        
        return True
    
    except Exception as e:
        logger.error(f"❌ アクセスログ記録エラー: {e}")
        return False


@retry_on_failure(max_retries=3)
def get_access_logs(temple_name: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """
    アクセスログを取得
    
    寺院へのアクセス履歴を取得します。
    特定寺院のログのみ、または全寺院のログを取得できます。
    
    Args:
        temple_name: 寺院名（指定した場合、その寺院のログのみ取得）
        limit: 取得件数（デフォルト: 100）
    
    Returns:
        List[Dict]: アクセスログのリスト
            例: [
                {
                    "timestamp": "2024-01-15T10:30:00+09:00",
                    "temple_name": "東大寺",
                    "query": "大仏について"
                }
            ]
    
    Example:
        # 特定寺院のログ
        logs = get_access_logs(temple_name="東大寺", limit=50)
        
        # 全寺院のログ
        all_logs = get_access_logs(limit=200)
    """
    # Supabaseクライアントを取得
    client = get_supabase_client()
    
    # クエリを開始
    query = client.table('access_logs').select('*')
    
    # 寺院名でフィルター（指定されている場合）
    if temple_name:
        query = query.eq('temple_name', temple_name)
    
    # タイムスタンプの新しい順で取得
    response = query.order('timestamp', desc=True).limit(limit).execute()
    
    return response.data


# ============================================
# 統計情報集計
# ============================================

def get_access_statistics(limit: int = 1000) -> Dict[str, int]:
    """
    寺院別のアクセス統計を取得
    
    各寺院へのアクセス回数を集計します。
    管理画面での人気寺院ランキング表示などに使用します。
    
    Args:
        limit: 集計対象とするアクセスログの件数（デフォルト: 1000）
    
    Returns:
        Dict[str, int]: 寺院名をキー、アクセス回数を値とする辞書
            例: {"東大寺": 150, "清水寺": 120, ...}
    
    Example:
        stats = get_access_statistics(limit=500)
        
        # アクセス数でソート
        sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        
        # トップ10を表示
        for temple, count in sorted_stats[:10]:
            logger.debug(f"{temple}: {count}回")
    """
    # 最新のアクセスログを取得
    logs = get_access_logs(limit=limit)
    
    # 寺院名ごとにカウント
    temple_counts = {}
    
    for log in logs:
        temple_name = log.get('temple_name', '')
        
        # 寺院名が存在する場合のみカウント
        if temple_name:
            # 既存カウントに+1、初回は1
            temple_counts[temple_name] = temple_counts.get(temple_name, 0) + 1
    
    return temple_counts


def get_top_accessed_temples(top_n: int = 10, days: int = 30) -> List[Dict]:
    """
    人気寺院ランキングを取得
    
    指定期間内のアクセス回数が多い寺院をランキング形式で返します。
    
    Args:
        top_n: 取得する寺院数（デフォルト: 10）
        days: 集計対象期間（日数、デフォルト: 30日）
    
    Returns:
        List[Dict]: ランキングデータのリスト
            例: [
                {"rank": 1, "temple_name": "東大寺", "access_count": 150},
                {"rank": 2, "temple_name": "清水寺", "access_count": 120},
                ...
            ]
    
    Example:
        # トップ10を取得
        ranking = get_top_accessed_temples(top_n=10)
        
        for item in ranking:
            logger.debug(f"{item['rank']}位: {item['temple_name']} - {item['access_count']}回")
    """
    # 統計を取得（多めに取得して確実にカバー）
    stats = get_access_statistics(limit=days * 100)
    
    # アクセス回数でソート（降順）
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    
    # トップN件を取得
    top_temples = sorted_stats[:top_n]
    
    # ランキング形式に変換
    ranking = [
        {
            'rank': i + 1,
            'temple_name': temple_name,
            'access_count': count
        }
        for i, (temple_name, count) in enumerate(top_temples)
    ]
    
    return ranking

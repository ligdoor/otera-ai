"""
Supabase対応版 スプレッドシートサービス

既存のspreadsheet.pyのインターフェースを維持しつつ、
バックエンドをSupabaseに切り替えます。
"""

import logging
from flask import request, session
from config import Config
from utils.helpers import get_jst_timestamp
from services.notification import notify_data_update
from services import supabase_db



logger = logging.getLogger(__name__)

def add_log(action, details, ip_address=None):
    """
    操作ログを記録（Supabase版）
    
    Args:
        action: 操作種別
        details: 詳細情報
        ip_address: IPアドレス（省略可）
    """
    try:
        user_name = session.get('user_name', '不明')
        user_id = session.get('user_id', '不明')
        ip = ip_address or request.remote_addr
        
        # Supabaseにログ記録
        supabase_db.add_log(
            user_name=user_name,
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip
        )
        
        # データ更新系の操作はSlack通知
        if action in ['追加', '編集', '削除', 'データ更新']:
            notify_data_update(user_name, action, details)
            
    except Exception as e:
        logger.debug(f"ログ記録エラー: {e}")


def load_fields_config(cache_manager):
    """
    項目設定を読み込み（Supabase版・キャッシュ対応）
    
    Args:
        cache_manager: キャッシュマネージャー
    
    Returns:
        list: 項目設定のリスト
    """
    def fetch():
        try:
            fields = supabase_db.get_fields_config()
            if not fields:
                # デフォルト設定
                fields = [{'key': 'name', 'label': '寺院名', 'order': 1}]
            return fields
        except Exception as e:
            logger.debug(f"項目設定読み込みエラー: {e}")
            return [{'key': 'name', 'label': '寺院名', 'order': 1}]
    
    return cache_manager.get_cached_or_fetch('fields', fetch)


def load_data_from_sheet(cache_manager):
    """
    寺院データを読み込み（Supabase版・キャッシュ対応）
    
    Args:
        cache_manager: キャッシュマネージャー
    
    Returns:
        dict: 寺院名をキーとした寺院データ辞書
    """
    def fetch():
        try:
            data = supabase_db.get_all_temples()
            logger.debug(f"★データ更新完了: {len(data)}件")
            return data
        except Exception as e:
            logger.debug(f"読み込みエラー: {e}")
            return {}
    
    return cache_manager.get_cached_or_fetch('temples', fetch)


def get_data_sheet_and_headers():
    """
    データのヘッダー情報を取得（Supabase版）
    
    Returns:
        tuple: (None, headers_list)
        
    Note:
        Supabaseでは「シート」の概念がないため、
        ヘッダー情報のみを返します
    """
    # 項目設定から動的にヘッダーを生成
    try:
        fields = supabase_db.get_fields_config()
        headers = [field['key'] for field in fields]
        return None, headers
    except Exception as e:
        logger.debug(f"ヘッダー取得エラー: {e}")
        # デフォルトヘッダー
        return None, ['name', 'sect', 'address', 'nokanshiyo', 'kakimono', 
                      'flow', 'caution', 'transport']

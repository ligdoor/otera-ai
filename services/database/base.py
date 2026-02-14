"""
データベース基本接続モジュール

Supabaseへの接続、共通ユーティリティ関数を提供します。
他のデータベースモジュールはこのモジュールを基盤として使用します。
"""

from supabase import create_client, Client
from config import Config
from typing import Optional
from datetime import datetime
import pytz
import time
from functools import wraps

# ============================================
# グローバル変数
# ============================================

# Supabaseクライアントのシングルトンインスタンス
_supabase_client: Optional[Client] = None


# ============================================
# デコレーター関数
# ============================================

def retry_on_failure(max_retries: int = 3, delay: int = 1):
    """
    データベース操作失敗時の自動リトライデコレーター
    
    ネットワークエラーや一時的なデータベース障害に対して
    自動的に再試行を行います。リトライ間隔は指数的に増加します。
    接続エラーの場合は自動的にクライアントを再接続します。
    
    Args:
        max_retries: 最大リトライ回数（デフォルト: 3）
        delay: 初回リトライまでの待機秒数（デフォルト: 1）
              2回目以降は delay * (試行回数) 秒待機
    
    Returns:
        デコレートされた関数
    
    Example:
        @retry_on_failure(max_retries=3, delay=1)
        def get_data():
            return client.table('users').select('*').execute()
    
    Note:
        - "Server disconnected"などの接続エラー時は自動的にクライアントを再接続
        - リトライ間隔は指数バックオフ（1秒、2秒、3秒...）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global _supabase_client
            
            # 指定回数までリトライを試みる
            for attempt in range(max_retries):
                try:
                    # 関数を実行
                    return func(*args, **kwargs)
                except Exception as e:
                    error_message = str(e).lower()
                    
                    # 接続エラーの場合はクライアントをリセット
                    if 'disconnected' in error_message or 'connection' in error_message or 'timeout' in error_message:
                        print(f"🔄 接続エラーを検出、クライアントをリセット中... ({e})")
                        _supabase_client = None  # グローバルクライアントをリセット
                    
                    # 最後の試行で失敗した場合は例外を再発生
                    if attempt == max_retries - 1:
                        print(f"❌ 最大リトライ回数到達 ({max_retries}回): {e}")
                        raise
                    
                    # リトライメッセージを表示
                    print(f"⚠️ リトライ {attempt + 1}/{max_retries}: {e}")
                    
                    # 指数バックオフで待機（1秒、2秒、3秒...）
                    wait_time = delay * (attempt + 1)
                    print(f"⏳ {wait_time}秒待機してから再試行...")
                    time.sleep(wait_time)
        return wrapper
    return decorator


# ============================================
# クライアント接続
# ============================================

def get_supabase_client() -> Client:
    """
    Supabaseクライアントを取得（シングルトンパターン）
    
    アプリケーション全体で1つのクライアントインスタンスを共有します。
    初回呼び出し時にクライアントを生成し、以降は同じインスタンスを返します。
    
    Returns:
        Client: Supabaseクライアントインスタンス
    
    Raises:
        ValueError: Supabase接続情報が環境変数に設定されていない場合
    
    Example:
        client = get_supabase_client()
        response = client.table('users').select('*').execute()
    """
    global _supabase_client
    
    # すでにクライアントが作成されている場合はそれを返す
    if _supabase_client is None:
        # 環境変数が設定されているか確認
        if not Config.SUPABASE_URL or not Config.SUPABASE_SERVICE_KEY:
            raise ValueError(
                "Supabase設定が不足しています。"
                "環境変数 SUPABASE_URL と SUPABASE_SERVICE_KEY を設定してください。"
            )
        
        # Supabaseクライアントを作成
        _supabase_client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_SERVICE_KEY
        )
        print("✅ Supabase接続完了")
    
    return _supabase_client


# ============================================
# ユーティリティ関数
# ============================================

def get_jst_timestamp() -> str:
    """
    日本標準時（JST）のタイムスタンプを取得
    
    データベースに保存する際の統一的なタイムスタンプ形式を提供します。
    ISO 8601形式（例: 2024-01-15T10:30:00+09:00）で返されます。
    
    Returns:
        str: ISO形式のタイムスタンプ文字列
    
    Example:
        timestamp = get_jst_timestamp()
        # "2024-01-15T10:30:00+09:00"
    """
    # 日本のタイムゾーンを設定
    jst = pytz.timezone('Asia/Tokyo')
    
    # 現在時刻を日本時間で取得し、ISO形式に変換
    return datetime.now(jst).isoformat()


# ============================================
# クライアントリセット（テスト用）
# ============================================

def reset_client():
    """
    Supabaseクライアントをリセット（主にテスト用）
    
    グローバルクライアントインスタンスをクリアします。
    次回get_supabase_client()呼び出し時に新しいインスタンスが作成されます。
    
    Note:
        本番環境では通常使用しません。テストやデバッグ目的で使用します。
    """
    global _supabase_client
    _supabase_client = None
    print("🔄 Supabaseクライアントをリセットしました")

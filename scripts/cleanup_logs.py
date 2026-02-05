"""
古いログを削除するスクリプト
cron等で定期実行: 0 0 * * 0 python scripts/cleanup_logs.py
"""
from config import Config
from datetime import datetime, timedelta

def cleanup_old_logs(days=90):
    """指定日数より古いログを削除"""
    if not Config.USE_SUPABASE:
        print("⚠️ Supabase使用時のみ実行可能")
        return
    
    from services.supabase_db import get_supabase_client
    
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime('%Y-%m-%d')
    
    client = get_supabase_client()
    result = client.table('logs').delete().lt('timestamp', cutoff_str).execute()
    
    print(f"✅ {days}日より古いログを削除しました")

if __name__ == "__main__":
    cleanup_old_logs()
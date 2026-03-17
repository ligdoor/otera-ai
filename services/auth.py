"""
認証サービス（Supabase/Google Sheets 両対応版）

データソースを自動切り替えする認証処理
Config.USE_SUPABASE で切り替え
"""

import logging
import datetime
import bcrypt
from flask import request
from config import Config
from services.notification import notify_suspicious_login
from utils.helpers import get_jst_now, get_jst_timestamp

# ログイン試行管理
login_attempts = {}

logger = logging.getLogger(__name__)


def check_login_attempts(user_id):
    """ログイン試行回数をチェック"""
    if user_id in login_attempts:
        attempts = login_attempts[user_id]
        if attempts['locked_until'] and datetime.datetime.now() < attempts['locked_until']:
            remaining = int((attempts['locked_until'] - get_jst_now()).total_seconds())
            return False, f"アカウントがロックされています。{remaining}秒後に再試行してください。"
        elif attempts['count'] >= Config.MAX_ATTEMPTS:
            login_attempts[user_id]['locked_until'] = get_jst_now() + datetime.timedelta(seconds=Config.LOCK_TIME)
            add_log("ログイン制限", f"user_id: {user_id} が{Config.MAX_ATTEMPTS}回失敗したためロック")
            
            # 異常ログイン通知
            notify_suspicious_login(user_id, request.remote_addr, f"{Config.MAX_ATTEMPTS}回連続失敗")
            return False, f"試行回数が上限に達しました。{Config.LOCK_TIME}秒間ロックされます。"
    return True, ""

def record_login_attempt(user_id, success):
    """ログイン試行を記録"""
    if success:
        if user_id in login_attempts:
            del login_attempts[user_id]
    else:
        if user_id not in login_attempts:
            login_attempts[user_id] = {'count': 0, 'locked_until': None}
        login_attempts[user_id]['count'] += 1
        
        # 3回失敗で警告通知
        if login_attempts[user_id]['count'] == 3:
            notify_suspicious_login(user_id, request.remote_addr, "3回連続失敗（警告）")

def add_log(action, details, ip_address=None):
    """操作ログを記録（データソース自動切り替え）"""
    if Config.USE_SUPABASE:
        from services import database as supabase_db
        from flask import session
        user_name = session.get('name', '不明')  # ★修正: user_name → name
        user_id_val = session.get('user_id', '不明')
        ip = ip_address or request.remote_addr
        supabase_db.add_log(user_name, user_id_val, action, details, ip)
    else:
        from services.spreadsheet import add_log as sheets_add_log
        sheets_add_log(action, details, ip_address)

def authenticate_user(user_id, password):
    """
    ユーザー認証（データソース自動切り替え）
    
    Args:
        user_id: ユーザーID
        password: パスワード
    
    Returns:
        tuple: (user_name, role) 認証失敗時は (None, None)
    """
    if Config.USE_SUPABASE:
        return _authenticate_user_supabase(user_id, password)
    else:
        return _authenticate_user_sheets(user_id, password)

def _authenticate_user_supabase(user_id, password):
    """
    Supabase版の認証
    
    Supabaseのusersテーブル構造:
    - user_id: TEXT (主キー)
    - user_name: TEXT (ユーザー名)
    - password_hash: TEXT (bcryptハッシュ)
    - permission: TEXT (権限: admin/editor/viewer)
    - created_at: TIMESTAMPTZ (作成日時)
    - last_login: TIMESTAMPTZ (最終ログイン)
    """
    try:
        from services import database as supabase_db
        
        # ユーザーを取得
        user = supabase_db.get_user_by_id(user_id)
        
        if not user:
            logger.error(f"⚠️ ユーザーが見つかりません: {user_id}")
            return None, None
        
        # パスワードハッシュを取得
        stored_hash = user.get('password_hash', '')
        
        if not stored_hash:
            logger.error(f"⚠️ パスワードハッシュが存在しません: {user_id}")
            return None, None
        
        authenticated = False
        
        # パスワード検証
        if stored_hash.startswith('$2b$'):
            # bcryptハッシュの場合
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                authenticated = True
        else:
            # 平文パスワードの場合（旧形式からの移行対応）
            if str(stored_hash) == password:
                # bcryptハッシュに変換して更新
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                supabase_db.update_user(user_id, {'password_hash': hashed})
                logger.info(f"✅ {user_id} のパスワードをbcryptハッシュに更新しました")
                authenticated = True
        
        # 認証成功時の処理
        if authenticated:
            try:
                # 最終ログイン時刻を更新
                supabase_db.update_user(user_id, {'last_login': get_jst_timestamp()})
                logger.info(f"✅ {user_id} の最終ログイン時刻を更新しました（Supabase）")
            except Exception as e:
                logger.error(f"⚠️ 最終ログイン時刻の更新に失敗: {e}")
            
            # ★重要: Google Sheetsと同じ列名を返す
            # name と role を返す（user_nameではなくname）
            user_name = user.get('name', '')
            role = user.get('role', 'viewer')
            
            return user_name, role
        else:
            logger.error(f"⚠️ パスワードが一致しません: {user_id}")
        
        return None, None
        
    except Exception as e:
        logger.error(f"❌ 認証エラー（Supabase）: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def _authenticate_user_sheets(user_id, password):
    """
    Google Sheets版の認証
    
    Google Sheetsのusersシート構造:
    列1: user_id (ユーザーID)
    列2: password_hash (パスワードハッシュ)
    列3: name (ユーザー名)
    列4: role (権限)
    列5: created_at (作成日時)
    列6: last_login (最終ログイン)
    """
    try:
        from services.spreadsheet import get_spreadsheet_client
        
        client = get_spreadsheet_client()
        sheet = client.open(Config.CONFIG_SPREADSHEET_NAME).worksheet('users')
        records = sheet.get_all_records()
        
        for user in records:
            if str(user.get('user_id')) == user_id:
                # password_hash 列または password 列を取得（互換性のため）
                stored_hash = user.get('password_hash', user.get('password', ''))
                
                if not stored_hash:
                    logger.error(f"⚠️ パスワードハッシュが存在しません: {user_id}")
                    continue
                
                authenticated = False
                
                # パスワード検証
                if stored_hash.startswith('$2b$'):
                    # bcryptハッシュの場合
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                        authenticated = True
                else:
                    # 平文パスワードの場合（旧形式からの移行対応）
                    if str(stored_hash) == password:
                        # bcryptハッシュに変換して更新
                        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        cell = sheet.find(user_id, in_column=1)
                        if cell:
                            sheet.update_cell(cell.row, 2, hashed)
                            logger.info(f"✅ {user_id} のパスワードをbcryptハッシュに更新しました")
                        authenticated = True
                
                # 認証成功時の処理
                if authenticated:
                    # 最終ログイン時刻を更新
                    cell = sheet.find(user_id, in_column=1)
                    if cell:
                        try:
                            sheet.update_cell(cell.row, 6, get_jst_timestamp())
                            logger.info(f"✅ {user_id} の最終ログイン時刻を更新しました（Google Sheets）")
                        except Exception as e:
                            logger.error(f"⚠️ 最終ログイン時刻の更新に失敗: {e}")
                    
                    # name と role を返す
                    user_name = user.get('name', '')
                    role = user.get('role', 'viewer')
                    
                    return user_name, role
                else:
                    logger.error(f"⚠️ パスワードが一致しません: {user_id}")
        
        logger.error(f"⚠️ ユーザーが見つかりません: {user_id}")
        return None, None
        
    except Exception as e:
        logger.error(f"❌ 認証エラー（Google Sheets）: {e}")
        import traceback
        traceback.print_exc()
        return None, None
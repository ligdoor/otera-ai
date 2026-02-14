"""
認証サービス�E�Eupabase対応版�E�E
Google SheetsとSupabaseの両方に対応した認証処琁E"""

import datetime
import bcrypt
from flask import request
from config import Config
from services.notification import notify_suspicious_login
from utils.helpers import get_jst_now, get_jst_timestamp

# ログイン試行管琁Elogin_attempts = {}

def check_login_attempts(user_id):
    """ログイン試行回数をチェチE��"""
    if user_id in login_attempts:
        attempts = login_attempts[user_id]
        if attempts['locked_until'] and datetime.datetime.now() < attempts['locked_until']:
            remaining = int((attempts['locked_until'] - get_jst_now()).total_seconds())
            return False, f"アカウントがロチE��されてぁE��す、Eremaining}秒後に再試行してください、E
        elif attempts['count'] >= Config.MAX_ATTEMPTS:
            login_attempts[user_id]['locked_until'] = get_jst_now() + datetime.timedelta(seconds=Config.LOCK_TIME)
            add_log("ログイン制陁E, f"user_id: {user_id} が{Config.MAX_ATTEMPTS}回失敗したためロチE��")
            
            # 異常ログイン通知
            notify_suspicious_login(user_id, request.remote_addr, f"{Config.MAX_ATTEMPTS}回連続失敁E)
            return False, f"試行回数が上限に達しました、EConfig.LOCK_TIME}秒間ロチE��されます、E
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
            notify_suspicious_login(user_id, request.remote_addr, "3回連続失敗（警告！E)

def add_log(action, details, ip_address=None):
    """操作ログを記録�E�データソース自動�Eり替え！E""
    if Config.USE_SUPABASE:
        from services import supabase_db
        from flask import session
        user_name = session.get('user_name', '不�E')
        user_id_val = session.get('user_id', '不�E')
        ip = ip_address or request.remote_addr
        supabase_db.add_log(user_name, user_id_val, action, details, ip)
    else:
        from services.spreadsheet import add_log as sheets_add_log
        sheets_add_log(action, details, ip_address)

def authenticate_user(user_id, password):
    """
    ユーザー認証�E�データソース自動�Eり替え！E    
    Args:
        user_id: ユーザーID
        password: パスワーチE    
    Returns:
        tuple: (user_name, role) 認証失敗時は (None, None)
    """
    if Config.USE_SUPABASE:
        return _authenticate_user_supabase(user_id, password)
    else:
        return _authenticate_user_sheets(user_id, password)

def _authenticate_user_supabase(user_id, password):
    """Supabase版�E認証"""
    try:
        from services import supabase_db
        
        # ユーザーを取征E        user = supabase_db.get_user_by_id(user_id)
        
        if not user:
            return None, None
        
        stored_hash = user.get('password_hash', '')
        authenticated = False
        
        # パスワード検証
        if stored_hash.startswith('$2b$'):
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                authenticated = True
        else:
            # 旧形式�Eパスワード（平斁E���E場合�Eハッシュ化して更新
            if str(user.get('password')) == password:
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                supabase_db.update_user(user_id, {'password_hash': hashed})
                authenticated = True
        
        # 認証成功時に最終ログイン時刻を更新
        if authenticated:
            try:
                supabase_db.update_user(user_id, {'last_login': get_jst_timestamp()})
                print(f"✁E{user_id} の最終ログイン時刻を更新しました�E�Eupabase�E�E)
            except Exception as e:
                print(f"⚠�E�E最終ログイン時刻の更新に失敁E {e}")
            
            return user.get('user_name'), user.get('permission', user.get('role', 'viewer'))
        
        return None, None
    except Exception as e:
        print(f"認証エラー�E�Eupabase�E�E {e}")
        import traceback
        traceback.print_exc()
        return None, None

def _authenticate_user_sheets(user_id, password):
    """Google Sheets版�E認証"""
    try:
        from services.spreadsheet import get_spreadsheet_client
        
        client = get_spreadsheet_client()
        sheet = client.open(Config.CONFIG_SPREADSHEET_NAME).worksheet('users')
        records = sheet.get_all_records()
        
        for user in records:
            if str(user.get('user_id')) == user_id:
                stored_hash = user.get('password_hash', user.get('password', ''))
                authenticated = False
                
                if stored_hash.startswith('$2b$'):
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                        authenticated = True
                else:
                    # 旧形式�Eパスワード（平斁E���E場合�Eハッシュ化して更新
                    if str(user.get('password')) == password:
                        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        cell = sheet.find(user_id, in_column=1)
                        if cell:
                            sheet.update_cell(cell.row, 2, hashed)
                        authenticated = True
                
                # 認証成功時に最終ログイン時刻を更新
                if authenticated:
                    cell = sheet.find(user_id, in_column=1)
                    if cell:
                        try:
                            sheet.update_cell(cell.row, 6, get_jst_timestamp())
                            print(f"✁E{user_id} の最終ログイン時刻を更新しました�E�Eoogle Sheets�E�E)
                        except Exception as e:
                            print(f"⚠�E�E最終ログイン時刻の更新に失敁E {e}")
                    
                    return user.get('name'), user.get('role', 'staff')
        
        return None, None
    except Exception as e:
        print(f"認証エラー�E�Eoogle Sheets�E�E {e}")
        return None, None

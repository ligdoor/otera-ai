import datetime
import bcrypt
from flask import request
from config import Config
from services.spreadsheet import get_spreadsheet_client, add_log
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

def authenticate_user(user_id, password):
    """ユーザー認証"""
    try:
        client = get_spreadsheet_client()
        sheet = client.open(Config.CONFIG_SPREADSHEET_NAME).worksheet('users')
        records = sheet.get_all_records()
        
        for user in records:
            if str(user.get('user_id')) == user_id:
                stored_hash = user.get('password_hash', '')
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
                
                # ☁E認証成功時に最終ログイン時刻を更新 ☁E                if authenticated:
                    cell = sheet.find(user_id, in_column=1)
                    if cell:
                        # 刁EぁElast_login 列！Eser_id, password_hash, name, role, created_at, last_login�E�E                        try:
                            sheet.update_cell(cell.row, 6, get_jst_timestamp())
                            print(f"✁E{user_id} の最終ログイン時刻を更新しました")
                        except Exception as e:
                            print(f"⚠�E�E最終ログイン時刻の更新に失敁E {e}")
                    
                    return user.get('name'), user.get('role', 'staff')
        
        return None, None
    except Exception as e:
        print(f"認証エラー: {e}")
        return None, None
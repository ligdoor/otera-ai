from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from utils.helpers import get_jst_now

def check_session_timeout():
    """セッションタイムアウトをチェック"""
    if 'last_activity' in session:
        elapsed = get_jst_now().timestamp() - session['last_activity']
        if elapsed > 1800:  # 30分
            session.clear()
            return False
    return True

def update_session_activity():
    """セッションアクティビティを更新"""
    session['last_activity'] = get_jst_now().timestamp()
    session.permanent = True

def login_required(f):
    """ログイン必須デコレーター"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            # HTML画面へのアクセスの場合はログインページにリダイレクト
            if request.path.startswith('/admin'):
                return redirect(url_for('auth.admin'))
            # API呼び出しの場合はJSONエラーを返す
            return jsonify({"message": "認証が必要です"}), 401
        
        if not check_session_timeout():
            session.clear()
            if request.path.startswith('/admin'):
                return redirect(url_for('auth.admin'))
            return jsonify({"message": "セッションがタイムアウトしました"}), 401
        
        update_session_activity()
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """指定された権限を持つユーザーのみアクセス可能"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('is_admin'):
                return jsonify({"message": "認証が必要です"}), 401
            
            user_role = session.get('role', 'viewer')
            if user_role not in allowed_roles:
                return jsonify({"message": "この操作を行う権限がありません"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
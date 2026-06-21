"""
デコレータモジュール

認証、権限チェック、セッション管理などのデコレータを提供します。
リファクタリング後のBlueprint名に対応しています。
"""

from functools import wraps
from flask import session, redirect, url_for, jsonify
from datetime import datetime, timedelta
from config import Config


# ============================================
# セッション管理
# ============================================

def update_session_activity():
    """
    セッションの最終アクティビティ時刻を更新
    
    ユーザーのアクティビティを記録し、セッションタイムアウトの
    基準時刻として使用します。
    """
    session['last_activity'] = datetime.now().isoformat()


def check_session_timeout():
    """
    セッションタイムアウトをチェック
    
    最終アクティビティから一定時間が経過している場合、
    セッションを無効と判定します。
    
    Returns:
        bool: セッションが有効な場合True、タイムアウトの場合False
    """
    if 'last_activity' not in session:
        return False
    
    last_activity = datetime.fromisoformat(session['last_activity'])
    
    # Config.SESSION_TIMEOUT_MINUTESが定義されていない場合はデフォルト30分
    timeout_minutes = getattr(Config, 'SESSION_TIMEOUT_MINUTES', 30)
    
    # タイムアウト時間を経過しているかチェック
    if datetime.now() - last_activity > timedelta(minutes=timeout_minutes):
        return False
    
    return True


# ============================================
# 認証デコレータ
# ============================================

def login_required(f):
    """
    ログイン必須デコレータ
    
    ビュー関数にこのデコレータを適用すると、ログインしていない
    ユーザーはログイン画面にリダイレクトされます。
    
    セッションタイムアウトもチェックされ、タイムアウトしている
    場合もログイン画面にリダイレクトされます。
    
    Usage:
        @app.route('/protected')
        @login_required
        def protected_page():
            return 'Protected content'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        # ログインチェック
        if 'user_id' not in session:
            # どのページからのログインか next パラメータで伝える
            next_url = request.path
            return redirect(url_for('auth_login.admin', next=next_url))
        
        # セッションタイムアウトチェック
        if not check_session_timeout():
            session.clear()
            from flask import request as req
            next_url = req.path
            return redirect(url_for('auth_login.admin', next=next_url))
        
        # セッションアクティビティを更新
        update_session_activity()
        
        return f(*args, **kwargs)
    
    return decorated_function


# ============================================
# 権限チェックデコレータ
# ============================================

def role_required(allowed_roles):
    """
    権限チェックデコレータ
    
    指定された権限を持つユーザーのみがアクセスできるようにします。
    権限がない場合は403エラーを返します。
    
    Args:
        allowed_roles: 許可する権限のリスト
            例: ['admin', 'editor']
    
    Usage:
        @app.route('/admin-only')
        @login_required
        @role_required(['admin'])
        def admin_only_page():
            return 'Admin only content'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # ログインチェック（念のため）
            if 'user_id' not in session:
                # ★修正: auth.admin → auth_login.admin
                return redirect(url_for('auth_login.admin'))
            
            # 権限チェック
            user_role = session.get('role', 'viewer')
            
            if user_role not in allowed_roles:
                return jsonify({
                    'error': 'Forbidden',
                    'message': 'この操作を行う権限がありません'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


# ============================================
# 管理者専用デコレータ
# ============================================

def admin_required(f):
    """
    管理者専用デコレータ
    
    管理者（admin）のみがアクセスできるようにします。
    role_required(['admin'])のショートカットです。
    
    Usage:
        @app.route('/admin-panel')
        @login_required
        @admin_required
        def admin_panel():
            return 'Admin panel'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # ログインチェック
        if 'user_id' not in session:
            # ★修正: auth.admin → auth_login.admin
            return redirect(url_for('auth_login.admin'))
        
        # 管理者権限チェック
        if session.get('role') != 'admin':
            return jsonify({
                'error': 'Forbidden',
                'message': '管理者権限が必要です'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


# ============================================
# API認証デコレータ
# ============================================

def api_login_required(f):
    """
    API用ログイン必須デコレータ
    
    API エンドポイント用のログインチェックデコレータです。
    通常のlogin_requiredとの違いは、認証エラー時にリダイレクトではなく
    JSONエラーレスポンスを返す点です。
    
    Usage:
        @app.route('/api/data')
        @api_login_required
        def get_data():
            return jsonify({'data': 'value'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # ログインチェック
        if 'user_id' not in session:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'ログインが必要です'
            }), 401
        
        # セッションタイムアウトチェック
        if not check_session_timeout():
            session.clear()
            return jsonify({
                'error': 'Unauthorized',
                'message': 'セッションがタイムアウトしました'
            }), 401
        
        # セッションアクティビティを更新
        update_session_activity()
        
        return f(*args, **kwargs)
    
    return decorated_function

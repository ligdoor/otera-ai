"""
認証ログインルート

ユーザーのログイン・ログアウト機能を提供します。
セッション管理、ログイン試行制限、ログ記録を含みます。
"""

from flask import Blueprint, render_template, request, session, redirect, url_for
from services.auth import check_login_attempts, record_login_attempt, authenticate_user
from utils.decorators import update_session_activity, check_session_timeout
from config import Config
from flask_extensions import limiter
from utils.session_utils import regenerate_session  # ★追加: セッション固定攻撃対策

# ============================================
# Blueprintの定義
# ============================================

auth_login_bp = Blueprint('auth_login', __name__)


# ============================================
# ログインページレンダリング
# ============================================

def render_login_page():
    """
    ログインページをレンダリング
    
    管理画面のログインフォームを表示します。
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    
    Template:
        login.html (既存プロジェクトのテンプレート名に合わせる)
    
    Note:
        プロジェクトによってテンプレート名が異なる場合があります：
        - login.html
        - admin_login.html
        - auth/login.html
    """
    return render_template('login.html')


# ============================================
# ログイン処理
# ============================================

@auth_login_bp.route("/admin", methods=["GET", "POST"], strict_slashes=False)
@limiter.limit("10 per minute")
def admin():
    """
    管理画面ログイン
    
    ログインフォームの表示とログイン処理を担当します。
    レート制限（10回/分）が適用されます。
    
    GET:
        ログインフォームを表示
        既にログイン済みの場合は管理画面を表示
    
    POST:
        ログイン処理を実行
        認証成功時はメイン画面にリダイレクト
        失敗時はエラーメッセージを表示
    
    Form Data (POST):
        user_id: ユーザーID
        password: パスワード
    
    Session Variables (設定):
        is_admin: True（管理者フラグ）
        user_name: ユーザー名
        user_id: ユーザーID
        role: ユーザーの権限（admin/editor/viewer）
    
    Returns:
        GET: ログインフォームまたは管理画面
        POST: メイン画面へのリダイレクトまたはエラーメッセージ
    
    Route:
        GET/POST /admin
    
    Rate Limit:
        10回/分（IPアドレスごと）
    
    Security Features:
        - ログイン試行回数制限
        - セッションタイムアウト
        - ログイン履歴の記録
        - IPアドレスの記録
    
    Example Flow:
        1. ユーザーがログインフォームにアクセス
        2. user_idとpasswordを入力して送信
        3. ログイン試行回数をチェック
        4. 認証を実行
        5. 成功時: セッションを設定してメイン画面へ
        6. 失敗時: エラーメッセージを表示
    """
    # ============================================
    # POST: ログイン処理
    # ============================================
    
    if request.method == "POST":
        # フォームデータを取得
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        
        print(f"📝 ログイン試行: user_id={user_id}")
        
        # ============================================
        # ログイン試行回数チェック
        # ============================================
        
        can_login, error_msg = check_login_attempts(user_id)
        
        if not can_login:
            # ログイン試行回数超過
            if Config.USE_SUPABASE:
                from services.database import add_log
                add_log(
                    user_name='不明',
                    user_id=user_id,
                    action='ログイン失敗',
                    details=error_msg,
                    ip_address=request.remote_addr or ''
                )
            
            # ★修正: alert()廃止 → フォームにエラーメッセージを表示
            return render_template('login.html', error=error_msg), 429
        
        # ============================================
        # 認証実行
        # ============================================
        
        user_name, role = authenticate_user(user_id, password)
        
        if user_name:
            # ============================================
            # 認証成功
            # ============================================
            
            # 成功した試行を記録
            record_login_attempt(user_id, True)
            
            # ★修正: セッション固定攻撃対策
            # session.clear()だけでは古いセッションIDが再利用される可能性がある
            # ログイン前後でセッションIDを切り替えて攻撃を防ぐ
            regenerate_session()
            
            session['is_admin'] = True
            session['user_name'] = user_name
            session['user_id'] = user_id
            session['role'] = role
            
            # セッションアクティビティを更新
            update_session_activity()
            
            # ログを記録
            if Config.USE_SUPABASE:
                from services.database import add_log, update_user, get_jst_timestamp
                
                # 権限の日本語表示
                role_display = {
                    'admin': '管理者',
                    'editor': '編集者',
                    'viewer': '閲覧者'
                }.get(role, role)
                
                # ログイン成功ログ
                add_log(
                    user_name=user_name,
                    user_id=user_id,
                    action='ログイン',
                    details=f"ログイン成功 ({role_display})",
                    ip_address=request.remote_addr or ''
                )
                
                # 最終ログイン時刻を更新
                print(f"✅ {user_name} の最終ログイン時刻を更新しました")
                update_user(user_id, {
                    'last_login': get_jst_timestamp()
                })
            
            print(f"✅ ログイン成功: {user_id} ({user_name}) - 権限: {role}")
            
            # メイン画面にリダイレクト
            return redirect('/')
        
        else:
            # ============================================
            # 認証失敗
            # ============================================
            
            # 失敗した試行を記録
            record_login_attempt(user_id, False)
            
            # ログを記録
            if Config.USE_SUPABASE:
                from services.database import add_log
                add_log(
                    user_name='不明',
                    user_id=user_id,
                    action='ログイン失敗',
                    details='認証エラー',
                    ip_address=request.remote_addr or ''
                )
            
            print(f"❌ ログイン失敗: {user_id}")
            
            # ★修正: alert()廃止 → フォームにエラーメッセージを表示
            return render_template('login.html', error='IDまたはパスワードが違います'), 401
    
    # ============================================
    # GET: ログインフォーム表示
    # ============================================
    
    # 既にログイン済みか確認
    if session.get('is_admin'):
        # セッションタイムアウトチェック
        if not check_session_timeout():
            # タイムアウトしている場合はセッションをクリア
            session.clear()
            return redirect(url_for('auth_login.admin'))
        
        # セッションアクティビティを更新
        update_session_activity()
        
        # 管理画面を表示
        return render_template("admin.html", user_name=session.get('user_name'))
    
    else:
        # ログインページを表示
        return render_login_page()


# ============================================
# ログアウト処理
# ============================================

@auth_login_bp.route("/logout")
def logout():
    """
    ログアウト処理
    
    ユーザーをログアウトさせ、セッションをクリアします。
    ログアウト履歴を記録し、ログイン画面にリダイレクトします。
    
    Returns:
        Redirect: ログイン画面（/admin）へのリダイレクト
    
    Route:
        GET /logout
    
    Authentication:
        不要（誰でもアクセス可能）
    
    Process:
        1. セッションから現在のユーザー情報を取得
        2. ログアウトログを記録
        3. セッションをクリア
        4. ログイン画面にリダイレクト
    
    Example:
        GET /logout
        
        → セッションがクリアされ、/admin にリダイレクト
    """
    # セッションから現在のユーザー情報を取得
    user_name = session.get('user_name', '不明')
    user_id = session.get('user_id', 'unknown')
    
    # ログアウトログを記録
    if Config.USE_SUPABASE:
        from services.database import add_log
        add_log(
            user_name=user_name,
            user_id=user_id,
            action='ログアウト',
            details='ログアウトしました',
            ip_address=request.remote_addr or ''
        )
    
    print(f"👋 ログアウト: {user_id} ({user_name})")
    
    # セッションをクリア
    session.clear()
    
    # ログイン画面にリダイレクト
    return redirect('/admin')

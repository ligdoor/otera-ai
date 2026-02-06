from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import bcrypt
from services.auth import check_login_attempts, record_login_attempt, authenticate_user
from utils.decorators import login_required, update_session_activity, check_session_timeout
from config import Config
from flask_extensions import limiter

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/admin", methods=["GET", "POST"], strict_slashes=False)
@limiter.limit("10 per minute")
def admin():
    """管理画面ログイン"""
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        
        print(f"📝 ログイン試行: user_id={user_id}")
        
        can_login, error_msg = check_login_attempts(user_id)
        if not can_login:
            if Config.USE_SUPABASE:
                from services import supabase_db
                supabase_db.add_log(
                    user_name='不明',
                    user_id=user_id,
                    action='ログイン失敗',
                    details=error_msg,
                    ip_address=request.remote_addr or ''
                )
            return f"""<script>alert('{error_msg}'); window.location.href='/admin';</script>"""
        
        user_name, role = authenticate_user(user_id, password)
        
        if user_name:
            record_login_attempt(user_id, True)
            session.clear()
            session['is_admin'] = True
            session['user_name'] = user_name
            session['user_id'] = user_id
            session['role'] = role
            update_session_activity()
            
            if Config.USE_SUPABASE:
                from services import supabase_db
                
                role_display = {
                    'admin': '管理者',
                    'editor': '編集者',
                    'viewer': '閲覧者'
                }.get(role, role)
                
                supabase_db.add_log(
                    user_name=user_name,
                    user_id=user_id,
                    action='ログイン',
                    details=f"ログイン成功 ({role_display})",
                    ip_address=request.remote_addr or ''
                )
                
                print(f"✅ {user_name} の最終ログイン時刻を更新しました（Supabase）")
                supabase_db.update_user(user_id, {
                    'last_login': supabase_db.get_jst_timestamp()
                })
            
            print(f"✅ ログイン成功: {user_id} ({user_name}) - 権限: {role}")
            
            # ★ 修正: メイン画面にリダイレクト
            return redirect('/')
        else:
            record_login_attempt(user_id, False)
            
            if Config.USE_SUPABASE:
                from services import supabase_db
                supabase_db.add_log(
                    user_name='不明',
                    user_id=user_id,
                    action='ログイン失敗',
                    details='認証エラー',
                    ip_address=request.remote_addr or ''
                )
            
            print(f"❌ ログイン失敗: {user_id}")
            return """<script>alert('IDまたはパスワードが違います'); window.location.href='/admin';</script>"""
    
    if session.get('is_admin'):
        if not check_session_timeout():
            session.clear()
            return redirect(url_for('auth.admin'))
        update_session_activity()
        # ★ 修正: 管理画面を表示（すでにログイン済みの場合）
        return render_template("admin.html", user_name=session.get('user_name'))
    else:
        # ログインページを表示
        return render_login_page()
    
@auth_bp.route("/logout")
def logout():
    """ログアウト - ログイン画面にリダイレクト"""
    user_name = session.get('user_name', '不明')
    user_id = session.get('user_id', 'unknown')
    
    if Config.USE_SUPABASE:
        from services import supabase_db
        supabase_db.add_log(
            user_name=user_name,
            user_id=user_id,
            action='ログアウト',
            details='ログアウトしました',
            ip_address=request.remote_addr or ''
        )
    
    session.clear()
    return redirect('/admin')  # ★ 修正: / → /admin に変更

@auth_bp.route("/change_password", methods=["POST"])
@limiter.limit("3 per hour")
@login_required
def change_password():
    """パスワード変更（Supabase/Google Sheets両対応）"""
    current_pass = request.json['current_pass']
    new_pass = request.json['new_pass']
    user_id = session.get('user_id')
    
    if len(new_pass) < 8:
        return jsonify({"message": "パスワードは8文字以上必要です"}), 400
    if not any(c.isdigit() for c in new_pass):
        return jsonify({"message": "パスワードには数字を含めてください"}), 400
    if not any(c.isalpha() for c in new_pass):
        return jsonify({"message": "パスワードには英字を含めてください"}), 400
    
    try:
        if Config.USE_SUPABASE:
            return _change_password_supabase(user_id, current_pass, new_pass)
        else:
            return _change_password_sheets(user_id, current_pass, new_pass)
    except Exception as e:
        print(f"❌ パスワード変更エラー: {e}")
        return jsonify({"message": str(e)}), 500

def _change_password_supabase(user_id, current_pass, new_pass):
    """Supabase版のパスワード変更"""
    from services import supabase_db
    
    user = supabase_db.get_user_by_id(user_id)
    
    if not user:
        return jsonify({"message": "ユーザーが見つかりません"}), 404
    
    stored_hash = user.get('password_hash', '')
    is_valid = False
    
    if stored_hash.startswith('$2b$'):
        is_valid = bcrypt.checkpw(current_pass.encode('utf-8'), stored_hash.encode('utf-8'))
    else:
        is_valid = (str(stored_hash) == current_pass)
    
    if is_valid:
        new_hash = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        supabase_db.update_user(user_id, {'password_hash': new_hash})
        
        # ★ 修正: ログ記録を改善
        supabase_db.add_log(
            action='パスワード変更',
            details='自身のパスワードを変更しました'
        )
        
        return jsonify({"status": "success"})
    else:
        # ★ 修正: ログ記録を改善
        supabase_db.add_log(
            action='パスワード変更失敗',
            details='現在のパスワードが間違っています'
        )
        
        return jsonify({"message": "現在のパスワードが間違っています"}), 400

def _change_password_sheets(user_id, current_pass, new_pass):
    """Google Sheets版のパスワード変更"""
    from services.spreadsheet import get_spreadsheet_client
    from services.data_source import add_log
    
    client = get_spreadsheet_client()
    sheet = client.open(Config.CONFIG_SPREADSHEET_NAME).worksheet('users')
    cell = sheet.find(user_id, in_column=1)
    
    if cell:
        row_idx = cell.row
        stored_hash = sheet.cell(row_idx, 2).value
        is_valid = False
        if stored_hash.startswith('$2b$'):
            is_valid = bcrypt.checkpw(current_pass.encode('utf-8'), stored_hash.encode('utf-8'))
        else:
            is_valid = (str(stored_hash) == current_pass)
        
        if is_valid:
            new_hash = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            sheet.update_cell(row_idx, 2, new_hash)
            add_log("パスワード変更", "自身のパスワードを変更しました")
            return jsonify({"status": "success"})
        else:
            add_log("パスワード変更失敗", "現在のパスワードが間違っています")
            return jsonify({"message": "現在のパスワードが間違っています"}), 400
    else:
        return jsonify({"message": "ユーザーが見つかりません"}), 404

def render_login_page():
    """ログインページのHTMLを返す（連打防止機能付き）"""
    return render_template('login.html')
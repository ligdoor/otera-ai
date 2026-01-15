from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import bcrypt
from services.auth import check_login_attempts, record_login_attempt, authenticate_user
from services.spreadsheet import add_log, get_spreadsheet_client
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
        
        can_login, error_msg = check_login_attempts(user_id)
        if not can_login:
            add_log("ログイン失敗", f"user_id: {user_id} - {error_msg}", request.remote_addr)
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
            add_log("ログイン成功", f"user_id: {user_id}", request.remote_addr)
            return redirect(url_for('auth.admin'))
        else:
            record_login_attempt(user_id, False)
            add_log("ログイン失敗", f"user_id: {user_id} - 認証エラー", request.remote_addr)
            return """<script>alert('IDまたはパスワードが違います'); window.location.href='/admin';</script>"""
    
    if session.get('is_admin'):
        if not check_session_timeout():
            session.clear()
            return redirect(url_for('auth.admin'))
        update_session_activity()
        # 管理画面を表示
        return render_template("admin.html", user_name=session.get('user_name'))
    else:
        # ログインページを表示
        return render_login_page()

@auth_bp.route("/logout")
def logout():
    """ログアウト"""
    user_name = session.get('user_name', '不明')
    add_log("ログアウト", f"{user_name} がログアウトしました")
    session.clear()
    return redirect(url_for('auth.admin'))

@auth_bp.route("/change_password", methods=["POST"])
@limiter.limit("3 per hour")  # パスワード変更は1時間に3回まで
@login_required
def change_password():
    """パスワード変更"""
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
    except Exception as e:
        return jsonify({"message": str(e)}), 500

"""
ログインボタン連打防止パッチ

routes/auth_routes.py の render_login_page() 関数を
このコードに置き換えてください（104行目付近）
"""

def render_login_page():
    """ログインページのHTMLを返す（連打防止機能付き）"""
    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
        <style>
            body {{ font-family: -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
            .login-container {{ background: white; padding: 40px 30px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); width: 90%; max-width: 400px; text-align: center; }}
            h2 {{ color: #1a237e; margin-top: 0; margin-bottom: 30px; font-size: 1.8rem; }}
            .lock-icon {{ font-size: 3rem; margin-bottom: 20px; }}
            input {{ width: 100%; padding: 15px; margin: 10px 0; border: 2px solid #ddd; border-radius: 8px; font-size: 18px; box-sizing: border-box; transition: border-color 0.3s; }}
            input:focus {{ outline: none; border-color: #667eea; }}
            button {{ width: 100%; padding: 15px; margin-top: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-size: 18px; font-weight: bold; cursor: pointer; transition: transform 0.2s; }}
            button:hover {{ transform: translateY(-2px); }}
            button:active {{ transform: translateY(0); }}
            button:disabled {{ opacity: 0.5; cursor: not-allowed; transform: none; }}
            .back-link {{ display: block; margin-top: 20px; color: #666; text-decoration: none; font-size: 0.9rem; }}
            .security-note {{ margin-top: 20px; padding: 10px; background: #fff3cd; border-left: 4px solid #ffc107; text-align: left; font-size: 0.85rem; color: #856404; }}
            .loading-spinner {{ display: none; margin-top: 10px; }}
            .loading-spinner.show {{ display: block; }}
            .spinner {{ border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="lock-icon">🔐</div>
            <form method="post" id="login-form">
                <h2>セキュアログイン</h2>
                <input type="text" name="user_id" placeholder="ログインID" required autocomplete="username" id="user-id-input">
                <input type="password" name="password" placeholder="パスワード" required autocomplete="current-password" id="password-input">
                <button type="submit" id="login-button">ログイン</button>
                <div class="loading-spinner" id="loading-spinner">
                    <div class="spinner"></div>
                    <p style="margin-top:10px; color:#666;">ログイン中...</p>
                </div>
            </form>
            <div class="security-note">
                <strong>⚠️ セキュリティ</strong><br>
                3回失敗で警告通知<br>
                5回失敗で5分間ロック<br>
                30分無操作で自動ログアウト
            </div>
            <a href="/" class="back-link">← アプリへ戻る</a>
        </div>
        
        <script>
            // ★ ログインボタンの連打防止 ★
            document.getElementById('login-form').addEventListener('submit', function(e) {{
                const button = document.getElementById('login-button');
                const spinner = document.getElementById('loading-spinner');
                const userIdInput = document.getElementById('user-id-input');
                const passwordInput = document.getElementById('password-input');
                
                // ボタンを無効化
                button.disabled = true;
                button.textContent = '処理中...';
                
                // 入力欄も無効化
                userIdInput.disabled = true;
                passwordInput.disabled = true;
                
                // ローディング表示
                spinner.classList.add('show');
            }});
        </script>
    </body>
    </html>
    """
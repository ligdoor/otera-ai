import logging
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
import bcrypt
from services.auth import check_login_attempts, record_login_attempt, authenticate_user
from utils.decorators import login_required, update_session_activity, check_session_timeout
from config import Config
from flask_extensions import limiter
from werkzeug.security import generate_password_hash, check_password_hash
from services.supabase_db import get_supabase_client
from utils.email_service import email_service
import uuid
from datetime import datetime, timedelta
import secrets

auth_bp = Blueprint('auth', __name__)

logger = logging.getLogger(__name__)

def render_login_page():
    """ログインページのHTMLを返す"""
    return render_template('login.html')


@auth_bp.route("/admin", methods=["GET", "POST"], strict_slashes=False)
@limiter.limit("10 per minute")
def admin():
    """管理画面ログイン"""
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        
        logger.debug(f"📝 ログイン試行: user_id={user_id}")
        
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
            # ★修正: XSS脆弱性のあるalert()を廃止 → テンプレートにエラーメッセージを渡す
            return render_template('login.html', error=error_msg), 429
        
        user_name, role = authenticate_user(user_id, password)
        
        if user_name:
            record_login_attempt(user_id, True)
            # ★修正: セッション固定攻撃対策 - ログイン前後でセッションIDを切り替え
            old_session_data = dict(session)
            session.clear()
            # セッションIDを再生成（Flaskはclear後に新IDが発行される）
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
                
                logger.info(f"✅ {user_name} の最終ログイン時刻を更新しました（Supabase）")
                supabase_db.update_user(user_id, {
                    'last_login': supabase_db.get_jst_timestamp()
                })
            
            logger.info(f"✅ ログイン成功: {user_id} ({user_name}) - 権限: {role}")
            
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
            
            logger.error(f"❌ ログイン失敗: {user_id}")
            # ★修正: XSS脆弱性のあるalert()を廃止 → テンプレートにエラーメッセージを渡す
            return render_template('login.html', error='IDまたはパスワードが違います'), 401
    
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

# ========== 新規登録画面表示 ==========
@auth_bp.route('/register', methods=['GET'])
def register_page():
    """新規登録画面を表示"""
    return render_template('register.html')


# routes/auth_routes.pyの該当部分を修正

# ========== 新規登録申請処理 ==========
@auth_bp.route('/register', methods=['POST'])
def register():
    """新規登録申請を受け付ける"""
    try:
        data = request.get_json()
        
        # 入力検証
        required_fields = ['user_id', 'name', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field}は必須です'}), 400
        
        user_id = data['user_id'].strip()
        name = data['name'].strip()
        email = data['email'].strip()
        password = data['password']
        department = data.get('department', '').strip()
        notes = data.get('notes', '').strip()
        
        client = get_supabase_client()
        
        # ユーザーID重複チェック（既存ユーザー）
        result = client.table('users').select('user_id').eq('user_id', user_id).execute()
        if result.data:
            return jsonify({'success': False, 'message': 'このユーザーIDは既に使用されています'}), 400
        
        # ユーザーID重複チェック（申請中）
        result = client.table('pending_users').select('user_id').eq('user_id', user_id).eq('status', 'pending').execute()
        if result.data:
            return jsonify({'success': False, 'message': 'このユーザーIDで申請中のリクエストがあります'}), 400
        
        # メールアドレス重複チェック（既存ユーザー）
        result = client.table('users').select('email').eq('email', email).execute()
        if result.data:
            return jsonify({'success': False, 'message': 'このメールアドレスは既に登録されています'}), 400
        
        # パスワードハッシュ化
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # pending_usersテーブルに保存
        pending_user = {
            'user_id': user_id,
            'password_hash': password_hash,
            'name': name,
            'email': email,
            'department': department,
            'notes': notes,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = client.table('pending_users').insert(pending_user).execute()
        
        if not result.data:
            return jsonify({'success': False, 'message': 'データベースエラーが発生しました'}), 500
        
        # ★★★ 管理者にメール通知（辞書形式で渡す） ★★★
        email_service.send_registration_notification({
            'user_id': user_id,
            'name': name,
            'email': email,
            'department': department,
            'notes': notes
        })
        
        return jsonify({
            'success': True,
            'message': '登録申請を受け付けました'
        }), 200
        
    except Exception as e:
        logger.debug(f"Registration error: {e}")
        return jsonify({'success': False, 'message': '登録処理中にエラーが発生しました'}), 500
    

# ========== 承認待ち一覧画面表示 ==========
@auth_bp.route('/pending-users', methods=['GET'])
def pending_users_page():
    """承認待ちユーザー一覧画面"""
    # ログインチェック
    if 'user_id' not in session:
        return redirect(url_for('auth.admin_login'))
    
    # 管理者権限チェック
    if session.get('role') != 'admin':
        return redirect(url_for('temple.index'))
    
    try:
        client = get_supabase_client()  # ★修正
        
        # 承認待ちユーザー取得
        result = client.table('pending_users')\
            .select('*')\
            .eq('status', 'pending')\
            .order('created_at', desc=True)\
            .execute()
        
        pending_users = result.data if result.data else []
        
        return render_template('pending_users.html', pending_users=pending_users)
        
    except Exception as e:
        logger.debug(f"Pending users page error: {e}")
        return render_template('pending_users.html', pending_users=[])


# ========== 承認処理 ==========
@auth_bp.route('/approve-user/<int:pending_id>', methods=['POST'])
def approve_user(pending_id):
    """ユーザー登録申請を承認"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '権限がありません'}), 403
    
    try:
        data = request.get_json()
        role = data.get('role', 'viewer')
        
        client = get_supabase_client()
        
        # pending_usersから情報取得
        result = client.table('pending_users')\
            .select('*')\
            .eq('id', pending_id)\
            .eq('status', 'pending')\
            .execute()
        
        if not result.data:
            return jsonify({'success': False, 'message': 'ユーザーが見つかりません'}), 404
        
        pending_user = result.data[0]
        
        # usersテーブルに登録
        new_user = {
            'user_id': pending_user['user_id'],
            'password_hash': pending_user['password_hash'],
            'name': pending_user['name'],
            'email': pending_user['email'],
            'department': pending_user['department'],
            'role': role,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = client.table('users').insert(new_user).execute()
        
        if not result.data:
            return jsonify({'success': False, 'message': 'ユーザー作成に失敗しました'}), 500
        
        # pending_usersのステータス更新
        client.table('pending_users')\
            .update({'status': 'approved', 'updated_at': datetime.utcnow().isoformat()})\
            .eq('id', pending_id)\
            .execute()
        
        # ★★★ 承認メール送信（引数を修正） ★★★
        email_service.send_approval_notification(
            pending_user['email'],
            pending_user['name']
        )
        
        return jsonify({
            'success': True,
            'message': f'{pending_user["name"]}さんを承認しました'
        }), 200
        
    except Exception as e:
        logger.debug(f"Approve user error: {e}")
        return jsonify({'success': False, 'message': '承認処理中にエラーが発生しました'}), 500


# ========== 却下処理 ==========
@auth_bp.route('/reject-user/<int:pending_id>', methods=['POST'])
def reject_user(pending_id):
    """ユーザー登録申請を却下"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '権限がありません'}), 403
    
    try:
        data = request.get_json()
        reason = data.get('reason', '')
        
        client = get_supabase_client()
        
        # pending_usersから情報取得
        result = client.table('pending_users')\
            .select('*')\
            .eq('id', pending_id)\
            .eq('status', 'pending')\
            .execute()
        
        if not result.data:
            return jsonify({'success': False, 'message': 'ユーザーが見つかりません'}), 404
        
        pending_user = result.data[0]
        
        # pending_usersのステータス更新
        client.table('pending_users')\
            .update({'status': 'rejected', 'updated_at': datetime.utcnow().isoformat()})\
            .eq('id', pending_id)\
            .execute()
        
        # ★★★ 却下メール送信（引数を修正） ★★★
        email_service.send_rejection_notification(
            pending_user['email'],
            pending_user['name'],
            reason
        )
        
        return jsonify({
            'success': True,
            'message': f'{pending_user["name"]}さんの申請を却下しました'
        }), 200
        
    except Exception as e:
        logger.debug(f"Reject user error: {e}")
        return jsonify({'success': False, 'message': '却下処理中にエラーが発生しました'}), 500
    

# ========== 承認待ち件数API ==========
@auth_bp.route('/api/pending-users-count', methods=['GET'])
def get_pending_users_count():
    """承認待ちユーザーの件数を取得"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'count': 0}), 200
    
    try:
        client = get_supabase_client()  # ★修正
        
        result = client.table('pending_users')\
            .select('id', count='exact')\
            .eq('status', 'pending')\
            .execute()
        
        count = result.count if result.count else 0
        
        return jsonify({'count': count}), 200
        
    except Exception as e:
        logger.debug(f"Get pending users count error: {e}")
        return jsonify({'count': 0}), 200
            
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
        logger.error(f"❌ パスワード変更エラー: {e}")
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


# ============================================================
# ★★★ パスワードリセット機能（ここから追加） ★★★
# ============================================================

@auth_bp.route('/password-reset-request', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def password_reset_request():
    """パスワードリセットリクエスト画面"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        if not email:
            return render_template('password_reset_request.html', 
                                 error='メールアドレスを入力してください')
        
        try:
            client = get_supabase_client()
            
            # ユーザーを検索
            response = client.table('users').select('*').eq('email', email).execute()
            
            # セキュリティのため、ユーザーが存在しない場合でも同じメッセージを表示
            # （悪意のある人がメールアドレスの存在確認をできないようにする）
            if response.data and len(response.data) > 0:
                user = response.data[0]
                
                # リセットトークンを生成（推測不可能なランダム文字列）
                token = secrets.token_urlsafe(32)
                
                # 有効期限を設定（1時間後）
                expires_at = datetime.utcnow() + timedelta(hours=1)
                
                # トークンをデータベースに保存
                client.table('password_reset_tokens').insert({
                    'user_id': user['id'],
                    'token': token,
                    'expires_at': expires_at.isoformat(),
                    'used': False
                }).execute()
                
                # リセットリンクを生成
                reset_link = url_for('auth.password_reset', 
                                   token=token, 
                                   _external=True)  # _external=True で完全なURLを生成
                
                # メールを送信
                email_service.send_password_reset_email(
                    to_email=email,
                    reset_link=reset_link,
                    user_name=user.get('name')
                )
            
            # 成功メッセージ（ユーザーの存在に関わらず同じメッセージ）
            return render_template('password_reset_request.html', 
                                 success='パスワードリセット用のメールを送信しました。メールをご確認ください。')
            
        except Exception as e:
            logger.debug(f"パスワードリセットリクエストエラー: {str(e)}")
            return render_template('password_reset_request.html', 
                                 error='エラーが発生しました。もう一度お試しください。')
    
    return render_template('password_reset_request.html')


@auth_bp.route('/password-reset/<token>', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def password_reset(token):
    """パスワードリセット実行画面"""
    try:
        client = get_supabase_client()
        
        # トークンの有効性を確認
        response = client.table('password_reset_tokens')\
            .select('*')\
            .eq('token', token)\
            .eq('used', False)\
            .execute()
        
        if not response.data or len(response.data) == 0:
            return render_template('password_reset.html', 
                                 token=token,
                                 error='無効なリセットリンクです。')
        
        token_data = response.data[0]
        
        # 有効期限を確認
        expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
        now = datetime.now(expires_at.tzinfo)
        
        if now > expires_at:
            return render_template('password_reset.html', 
                                 token=token,
                                 error='リセットリンクの有効期限が切れています。もう一度リクエストしてください。')
        
        # POSTリクエスト（パスワード変更実行）
        if request.method == 'POST':
            password = request.form.get('password', '').strip()
            password_confirm = request.form.get('password_confirm', '').strip()
            
            # バリデーション
            if not password or not password_confirm:
                return render_template('password_reset.html', 
                                     token=token,
                                     error='パスワードを入力してください。')
            
            if password != password_confirm:
                return render_template('password_reset.html', 
                                     token=token,
                                     error='パスワードが一致しません。')
            
            if len(password) < 8:
                return render_template('password_reset.html', 
                                     token=token,
                                     error='パスワードは8文字以上で設定してください。')
            
            # パスワードをハッシュ化
            hashed_password = bcrypt.hashpw(
                password.encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # パスワードを更新
            client.table('users').update({
                'password_hash': hashed_password
            }).eq('id', token_data['user_id']).execute()
            
            # トークンを使用済みにする
            client.table('password_reset_tokens').update({
                'used': True
            }).eq('id', token_data['id']).execute()
            
            # ログインページにリダイレクト（成功メッセージ付き）
            return render_template('login.html', 
                                 success='パスワードを変更しました。新しいパスワードでログインしてください。')
        
        # GETリクエスト（パスワード入力画面を表示）
        return render_template('password_reset.html', token=token)
        
    except Exception as e:
        logger.debug(f"パスワードリセットエラー: {str(e)}")
        return render_template('password_reset.html', 
                             token=token,
                             error='エラーが発生しました。もう一度お試しください。')


def render_login_page():
    """ログインページのHTMLを返す（連打防止機能付き）"""
    return render_template('login.html')
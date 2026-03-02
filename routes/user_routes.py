"""
ユーザー管理ルート（Supabase/Google Sheets 両対応版）

データソースを自動切り替えするユーザー管理
"""

import logging
from flask import Blueprint, render_template, jsonify, request, session
import bcrypt
from utils.decorators import login_required, role_required
from utils.helpers import get_jst_timestamp
from config import Config

user_bp = Blueprint('user', __name__)

logger = logging.getLogger(__name__)

def add_log(action, details):
    """ログ記録（データソース自動切り替え）"""
    if Config.USE_SUPABASE:
        from services import database as supabase_db
        from flask import request as flask_request
        user_name = session.get('name', '不明')  # ★修正: user_name → name
        user_id = session.get('user_id', '不明')
        ip = flask_request.remote_addr
        supabase_db.add_log(user_name, user_id, action, details, ip)
    else:
        from services.spreadsheet import add_log as sheets_add_log
        sheets_add_log(action, details)

@user_bp.route("/admin/users")
@login_required
@role_required(['admin'])
def admin_users():
    """ユーザー管理画面（管理者のみ）"""
    return render_template("admin_users.html")

@user_bp.route("/get_current_user")
@login_required
def get_current_user():
    """現在ログイン中のユーザー情報を取得"""
    return jsonify({
        "user_id": session.get('user_id'),
        "user_name": session.get('name'),  # ★修正: user_name → name（フロント側はuser_nameを期待）
        "role": session.get('role', 'viewer')
    })

@user_bp.route("/get_users")
@login_required
@role_required(['admin'])
def get_users():
    """ユーザー一覧取得（管理者のみ）"""
    try:
        if Config.USE_SUPABASE:
            return _get_users_supabase()
        else:
            return _get_users_sheets()
    except Exception as e:
        logger.error(f"❌ ユーザー一覧取得エラー: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def _get_users_supabase():
    """
    Supabase版のユーザー一覧取得
    
    Supabaseのusersテーブル構造:
    - user_id: TEXT
    - name: TEXT
    - email: TEXT  ★追加
    - department: TEXT  ★追加
    - password_hash: TEXT
    - role: TEXT
    - status: TEXT  ★追加
    - created_at: TEXT
    - last_login: TEXT
    """
    from services import database as supabase_db
    
    all_users = supabase_db.get_all_users()
    
    # パスワードハッシュを除外してフロントエンドに返す
    users = []
    for user in all_users:
        users.append({
            'user_id': user.get('user_id'),
            'name': user.get('name'),
            'email': user.get('email', ''),  # ★追加
            'department': user.get('department', ''),  # ★追加
            'role': user.get('role', 'viewer'),
            'status': user.get('status', 'active'),  # ★追加
            'created_at': user.get('created_at', ''),
            'last_login': user.get('last_login', '')
        })
    
    logger.info(f"✅ Supabaseからユーザー取得: {len(users)}件")
    return jsonify({"users": users})

def _get_users_sheets():
    """
    Google Sheets版のユーザー一覧取得
    
    Google Sheetsのusersシート構造:
    列1: user_id
    列2: password_hash
    列3: name
    列4: role
    列5: created_at
    列6: last_login
    """
    from services.spreadsheet import get_spreadsheet_client
    
    client = get_spreadsheet_client()
    sheet = client.open(Config.CONFIG_SPREADSHEET_NAME).worksheet('users')
    records = sheet.get_all_records()
    
    # パスワードハッシュを除外してフロントエンドに返す
    users = []
    for user in records:
        users.append({
            'user_id': user.get('user_id'),
            'name': user.get('name'),  # Google Sheetsでは name
            'role': user.get('role', 'viewer'),  # role列
            'created_at': user.get('created_at', ''),
            'last_login': user.get('last_login', '')
        })
    
    logger.info(f"✅ Google Sheetsからユーザー取得: {len(users)}件")
    return jsonify({"users": users})

@user_bp.route("/add_user", methods=["POST"])
@login_required
@role_required(['admin'])
def add_user():
    """ユーザー追加（管理者のみ）"""
    data = request.json
    user_id = data.get('user_id', '').strip()
    name = data.get('name', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'viewer')
    
    # バリデーション
    if not user_id or not name or not password:
        return jsonify({"message": "必須項目が入力されていません"}), 400
    
    if role not in ['admin', 'editor', 'viewer']:
        return jsonify({"message": "無効な権限レベルです"}), 400
    
    if len(password) < 8:
        return jsonify({"message": "パスワードは8文字以上必要です"}), 400
    
    try:
        if Config.USE_SUPABASE:
            return _add_user_supabase(user_id, name, password, role)
        else:
            return _add_user_sheets(user_id, name, password, role)
    except Exception as e:
        logger.error(f"❌ ユーザー追加エラー: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500

def _add_user_supabase(user_id, name, password, role):
    """Supabase版のユーザー追加"""
    from services import database as supabase_db
    
    # 重複チェック
    existing_user = supabase_db.get_user_by_id(user_id)
    if existing_user:
        return jsonify({"message": "このユーザーIDは既に使用されています"}), 400
    
    # パスワードハッシュ化
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # ユーザーデータ作成（Google Sheetsと同じ列名）
    timestamp = get_jst_timestamp()
    user_data = {
        'user_id': user_id,
        'password_hash': hashed,
        'name': name,  # ★修正: user_name → name
        'role': role,  # ★修正: permission → role
        'created_at': timestamp,
        'last_login': ''
    }
    
    supabase_db.create_user(user_data)
    add_log("ユーザー追加", f"{name}（{role}）を追加")
    
    logger.info(f"✅ Supabaseにユーザー追加: {user_id} ({name})")
    return jsonify({"status": "success"})

def _add_user_sheets(user_id, name, password, role):
    """Google Sheets版のユーザー追加"""
    from services.spreadsheet import get_spreadsheet_client
    
    client = get_spreadsheet_client()
    sheet = client.open(Config.CONFIG_SPREADSHEET_NAME).worksheet('users')
    
    # 重複チェック
    records = sheet.get_all_records()
    if any(str(u.get('user_id')) == user_id for u in records):
        return jsonify({"message": "このユーザーIDは既に使用されています"}), 400
    
    # パスワードハッシュ化
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # 追加
    timestamp = get_jst_timestamp()
    # 列順: user_id, password_hash, name, role, created_at, last_login
    sheet.append_row([user_id, hashed, name, role, timestamp, ''])
    
    add_log("ユーザー追加", f"{name}（{role}）を追加")
    
    logger.info(f"✅ Google Sheetsにユーザー追加: {user_id} ({name})")
    return jsonify({"status": "success"})

@user_bp.route("/update_user_role", methods=["POST"])
@login_required
@role_required(['admin'])
def update_user_role():
    """ユーザー情報更新（管理者のみ）"""
    data = request.json
    user_id = data.get('user_id')
    
    # 更新するフィールドを収集
    updates = {}
    
    if 'role' in data:
        new_role = data['role']
        if new_role not in ['admin', 'editor', 'viewer']:
            return jsonify({"message": "無効な権限レベルです"}), 400
        updates['role'] = new_role
    
    if 'name' in data:
        updates['name'] = data['name'].strip()
    
    if 'email' in data:
        updates['email'] = data['email'].strip()
    
    if 'department' in data:
        updates['department'] = data['department'].strip()
    
    if 'status' in data:
        if data['status'] not in ['active', 'inactive']:
            return jsonify({"message": "無効なステータスです"}), 400
        updates['status'] = data['status']
    
    # 自分自身の権限変更を防止
    if session.get('user_id') == user_id and 'role' in updates:
        return jsonify({"message": "自分自身の権限は変更できません"}), 400
    
    try:
        if Config.USE_SUPABASE:
            return _update_user_supabase(user_id, updates)
        else:
            return _update_user_sheets(user_id, updates)
    except Exception as e:
        logger.error(f"❌ ユーザー更新エラー: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500

def _update_user_supabase(user_id, updates):
    """Supabase版のユーザー更新（複数フィールド対応）"""
    from services import database as supabase_db
    
    user = supabase_db.get_user_by_id(user_id)
    if not user:
        return jsonify({"message": "ユーザーが見つかりません"}), 404
    
    supabase_db.update_user(user_id, updates)
    
    # ログ記録
    details = ', '.join([f"{k}={v}" for k, v in updates.items()])
    add_log("ユーザー情報更新", f"{user_id} の情報を更新: {details}")
    
    logger.info(f"✅ Supabaseでユーザー更新: {user_id} → {updates}")
    return jsonify({"status": "success"})

def _update_user_sheets(user_id, updates):
    """Google Sheets版のユーザー更新（複数フィールド対応）"""
    from services.spreadsheet import get_spreadsheet_client
    
    client = get_spreadsheet_client()
    sheet = client.open(Config.CONFIG_SPREADSHEET_NAME).worksheet('users')
    
    cell = sheet.find(user_id, in_column=1)
    if not cell:
        return jsonify({"message": "ユーザーが見つかりません"}), 404
    
    # 列マッピング（Google Sheets）
    # 列1: user_id, 列2: password_hash, 列3: name, 列4: role, 
    # 列5: created_at, 列6: last_login
    column_map = {
        'name': 3,
        'role': 4,
        # email, departmentは現状のSheetsにはないので、追加する場合は列を増やす必要あり
    }
    
    for field, value in updates.items():
        if field in column_map:
            sheet.update_cell(cell.row, column_map[field], value)
    
    details = ', '.join([f"{k}={v}" for k, v in updates.items()])
    add_log("ユーザー情報更新", f"{user_id} の情報を更新: {details}")
    
    logger.info(f"✅ Google Sheetsでユーザー更新: {user_id} → {updates}")
    return jsonify({"status": "success"})

@user_bp.route("/delete_user", methods=["POST"])
@login_required
@role_required(['admin'])
def delete_user():
    """ユーザー削除（管理者のみ）"""
    user_id = request.json.get('user_id')
    
    # 自分自身の削除を防止
    if session.get('user_id') == user_id:
        return jsonify({"message": "自分自身は削除できません"}), 400
    
    try:
        if Config.USE_SUPABASE:
            return _delete_user_supabase(user_id)
        else:
            return _delete_user_sheets(user_id)
    except Exception as e:
        logger.error(f"❌ ユーザー削除エラー: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500

def _delete_user_supabase(user_id):
    """Supabase版のユーザー削除"""
    from services import database as supabase_db
    
    user = supabase_db.get_user_by_id(user_id)
    if not user:
        return jsonify({"message": "ユーザーが見つかりません"}), 404
    
    user_name = user.get('name')
    supabase_db.delete_user(user_id)
    add_log("ユーザー削除", f"{user_name}（{user_id}）を削除")
    
    logger.info(f"✅ Supabaseでユーザー削除: {user_id} ({user_name})")
    return jsonify({"status": "success"})

def _delete_user_sheets(user_id):
    """Google Sheets版のユーザー削除"""
    from services.spreadsheet import get_spreadsheet_client
    
    client = get_spreadsheet_client()
    sheet = client.open(Config.CONFIG_SPREADSHEET_NAME).worksheet('users')
    
    cell = sheet.find(user_id, in_column=1)
    if cell:
        user_name = sheet.cell(cell.row, 3).value  # 列3が name列
        sheet.delete_rows(cell.row)
        add_log("ユーザー削除", f"{user_name}（{user_id}）を削除")
        logger.info(f"✅ Google Sheetsでユーザー削除: {user_id} ({user_name})")
        return jsonify({"status": "success"})
    else:
        return jsonify({"message": "ユーザーが見つかりません"}), 404
from flask import Blueprint, render_template, jsonify, request, session
import bcrypt
from utils.decorators import login_required, role_required
from services.spreadsheet import add_log, get_spreadsheet_client
from utils.helpers import get_jst_timestamp
from config import Config

user_bp = Blueprint('user', __name__)

@user_bp.route("/admin/users")
@login_required
@role_required('admin')
def admin_users():
    """ユーザー管理画面（管理者のみ）"""
    return render_template("admin_users.html")

@user_bp.route("/get_current_user")
@login_required
def get_current_user():
    """現在ログイン中のユーザー情報を取得"""
    return jsonify({
        "user_id": session.get('user_id'),
        "user_name": session.get('user_name'),
        "role": session.get('role', 'viewer')
    })

@user_bp.route("/get_users")
@login_required
@role_required('admin')
def get_users():
    """ユーザー一覧取得（管理者のみ）"""
    try:
        client = get_spreadsheet_client()
        sheet = client.open(Config.CONFIG_SPREADSHEET_NAME).worksheet('users')
        records = sheet.get_all_records()
        
        # パスワードハッシュを除外
        users = []
        for user in records:
            users.append({
                'user_id': user.get('user_id'),
                'name': user.get('name'),
                'role': user.get('role', 'viewer'),
                'created_at': user.get('created_at', ''),
                'last_login': user.get('last_login', '')
            })
        
        return jsonify({"users": users})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@user_bp.route("/add_user", methods=["POST"])
@login_required
@role_required('admin')
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
        sheet.append_row([user_id, hashed, name, role, timestamp, ''])
        
        add_log("ユーザー追加", f"{name}（{role}）を追加")
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@user_bp.route("/update_user_role", methods=["POST"])
@login_required
@role_required('admin')
def update_user_role():
    """ユーザー権限変更（管理者のみ）"""
    data = request.json
    user_id = data.get('user_id')
    new_role = data.get('role')
    
    if new_role not in ['admin', 'editor', 'viewer']:
        return jsonify({"message": "無効な権限レベルです"}), 400
    
    # 自分自身の権限変更を防止
    if session.get('user_id') == user_id:
        return jsonify({"message": "自分自身の権限は変更できません"}), 400
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(Config.CONFIG_SPREADSHEET_NAME).worksheet('users')
        
        cell = sheet.find(user_id, in_column=1)
        if cell:
            sheet.update_cell(cell.row, 4, new_role)  # role列を更新
            add_log("権限変更", f"{user_id} の権限を {new_role} に変更")
            return jsonify({"status": "success"})
        else:
            return jsonify({"message": "ユーザーが見つかりません"}), 404
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@user_bp.route("/delete_user", methods=["POST"])
@login_required
@role_required('admin')
def delete_user():
    """ユーザー削除（管理者のみ）"""
    user_id = request.json.get('user_id')
    
    # 自分自身の削除を防止
    if session.get('user_id') == user_id:
        return jsonify({"message": "自分自身は削除できません"}), 400
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(Config.CONFIG_SPREADSHEET_NAME).worksheet('users')
        
        cell = sheet.find(user_id, in_column=1)
        if cell:
            user_name = sheet.cell(cell.row, 3).value
            sheet.delete_rows(cell.row)
            add_log("ユーザー削除", f"{user_name}（{user_id}）を削除")
            return jsonify({"status": "success"})
        else:
            return jsonify({"message": "ユーザーが見つかりません"}), 404
    except Exception as e:
        return jsonify({"message": str(e)}), 500
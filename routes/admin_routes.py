from flask import Blueprint, render_template, jsonify, request
from utils.decorators import login_required, role_required
from services.data_source import add_log
from services.temple_crud import update_fields_data
from services.cache import cache_manager
from config import Config

admin_bp = Blueprint('admin_routes', __name__)

@admin_bp.route("/admin/fields")
@login_required
def admin_fields():
    """項目設定画面"""
    return render_template("admin_fields.html")

@admin_bp.route("/get_logs")
@login_required
def get_logs():
    """ログ一覧を取得"""
    if Config.USE_SUPABASE:
        # Supabase版
        from services import supabase_db
        try:
            logs = supabase_db.get_recent_logs(limit=50)
            # タイムスタンプでソート（新しい順）
            logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return jsonify(logs)
        except Exception as e:
            print(f"ログ取得エラー: {e}")
            return jsonify([])
    else:
        # Google Sheets版
        from services.spreadsheet import get_spreadsheet_client
        try:
            client = get_spreadsheet_client()
            sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('logs')
            records = sheet.get_all_records()
            return jsonify(records[-50:][::-1])
        except:
            return jsonify([])

@admin_bp.route("/update_fields", methods=["POST"])
@login_required
def update_fields():
    """項目設定を更新"""
    new_fields = request.json['fields']
    
    # CRUD操作実行
    success, message = update_fields_data(new_fields)
    
    if success:
        add_log("項目設定変更", f"{len(new_fields)}個の項目を更新")
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": message}), 500

@admin_bp.route("/get_fields")
def get_fields():
    """項目設定を取得"""
    from routes.temple_routes import field_config
    return jsonify(field_config)
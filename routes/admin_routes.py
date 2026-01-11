from flask import Blueprint, render_template, jsonify, request
from utils.decorators import login_required, role_required
from services.spreadsheet import add_log, get_spreadsheet_client
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
    try:
        client = get_spreadsheet_client()
        sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('fields')
        sheet.clear()
        sheet.append_row(['key', 'label', 'order'])
        rows = [[f['key'], f['label'], f['order']] for f in new_fields]
        sheet.append_rows(rows)
        
        # キャッシュクリア
        cache_manager.clear_cache('fields')
        
        add_log("項目設定変更", f"{len(new_fields)}個の項目を更新")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@admin_bp.route("/get_fields")
def get_fields():
    """項目設定を取得"""
    from routes.temple_routes import field_config
    return jsonify(field_config)
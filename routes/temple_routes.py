from flask import Blueprint, jsonify, request, send_file
import csv
import io
from utils.decorators import login_required, role_required
from services.spreadsheet import (
    add_log, 
    get_spreadsheet_client, 
    get_data_sheet_and_headers,
    load_data_from_sheet,
    load_fields_config
)
from services.cache import cache_manager
from utils.helpers import get_jst_now
from config import Config

temple_bp = Blueprint('temple', __name__)

# グローバルデータ（main.pyから移行）
otera_database = {}
field_config = []

def init_temple_data():
    """寺院データを初期化"""
    global otera_database, field_config
    otera_database = load_data_from_sheet(cache_manager)
    field_config = load_fields_config(cache_manager)

@temple_bp.route("/reload_data", methods=["POST"])
@login_required
def reload_data():
    """データを強制リロード（キャッシュクリア）"""
    global otera_database, field_config
    
    try:
        # キャッシュをクリア
        cache_manager.clear_cache()
        
        otera_database = load_data_from_sheet(cache_manager)
        field_config = load_fields_config(cache_manager)
        add_log("データ更新", f"管理画面からリロードを実行（{len(otera_database)}件）")
        return jsonify({"status": "success", "count": len(otera_database)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@temple_bp.route("/get_all_data")
@login_required
def get_all_data():
    """全寺院データを取得（キャッシュ使用）"""
    try:
        # 最新データを取得（キャッシュがあれば使用）
        data = load_data_from_sheet(cache_manager)
        return jsonify(data)
    except Exception as e:
        print(f"データ取得エラー: {e}")
        return jsonify({"error": "データの読み込みに失敗しました"}), 500

@temple_bp.route("/get_fields")
def get_fields():
    """項目設定を取得"""
    global field_config
    return jsonify(field_config)

@temple_bp.route("/update_temple", methods=["POST"])
@login_required
@role_required('admin', 'editor')
def update_temple():
    """寺院情報を更新"""
    req = request.json
    original_name = req['original_name']
    new_data = req['data']
    
    if not new_data.get('name'):
        return jsonify({"status": "error", "message": "寺院名は必須です"}), 400
    
    try:
        sheet, headers = get_data_sheet_and_headers()
        current_headers = headers
        for key in new_data.keys():
            if key not in current_headers:
                sheet.update_cell(1, len(current_headers) + 1, key)
                current_headers.append(key)
        headers = current_headers

        cell = sheet.find(original_name, in_column=1)
        if cell:
            row_idx = cell.row
            row_data = [new_data.get(h, "") for h in headers]
            sheet.update(f"A{row_idx}", [row_data])
            if original_name in otera_database:
                del otera_database[original_name]
            otera_database[new_data['name']] = new_data
            
            # キャッシュクリア
            cache_manager.clear_cache('temples')
            
            add_log("編集", f"{original_name} の情報を更新 → {new_data['name']}")
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "not_found"}), 404
    except Exception as e:
        add_log("編集エラー", f"エラー: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@temple_bp.route("/add_temple", methods=["POST"])
@login_required
@role_required('admin', 'editor')
def add_temple():
    """新規寺院を追加"""
    req = request.json
    new_data = req['data']
    name = new_data.get('name')
    
    if not name:
        return jsonify({"status": "error", "message": "寺院名は必須です"}), 400
    if name in otera_database:
        return jsonify({"status": "error", "message": "その名前は既に存在します"}), 400
    
    try:
        sheet, headers = get_data_sheet_and_headers()
        current_headers = headers
        for key in new_data.keys():
            if key not in current_headers:
                sheet.update_cell(1, len(current_headers) + 1, key)
                current_headers.append(key)
        headers = current_headers

        row_data = [new_data.get(h, "") for h in headers]
        sheet.append_row(row_data)
        otera_database[name] = new_data
        
        # キャッシュクリア
        cache_manager.clear_cache('temples')
        
        add_log("追加", f"{name} を新規追加")
        return jsonify({"status": "success"})
    except Exception as e:
        add_log("追加エラー", f"エラー: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
# routes/temple_routes.py (Part 2) - 続き

@temple_bp.route("/delete_temple", methods=["POST"])
@login_required
@role_required('admin', 'editor')
def delete_temple():
    """寺院を削除"""
    name = request.json.get('name')
    try:
        sheet, headers = get_data_sheet_and_headers()
        cell = sheet.find(name, in_column=1)
        if cell:
            sheet.delete_rows(cell.row)
            if name in otera_database:
                del otera_database[name]
            
            # キャッシュクリア
            cache_manager.clear_cache('temples')
            
            add_log("削除", f"{name} を削除")
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "not_found"}), 404
    except Exception as e:
        add_log("削除エラー", f"エラー: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@temple_bp.route("/export_csv")
@login_required
def export_csv():
    """CSVエクスポート"""
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        headers = [f['key'] for f in field_config]
        writer.writerow(headers)
        
        # データ
        for temple in otera_database.values():
            row = [temple.get(h, '') for h in headers]
            writer.writerow(row)
        
        # バイナリに変換
        output.seek(0)
        byte_output = io.BytesIO()
        byte_output.write(output.getvalue().encode('utf-8-sig'))  # BOM付きUTF-8
        byte_output.seek(0)
        
        add_log("CSVエクスポート", f"{len(otera_database)}件のデータをエクスポート")
        
        return send_file(
            byte_output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'temples_{get_jst_now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@temple_bp.route("/import_csv", methods=["POST"])
@login_required
@role_required('admin', 'editor')
def import_csv():
    """CSVインポート"""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "ファイルが選択されていません"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "ファイルが選択されていません"}), 400
    
    try:
        # CSVを読み込み
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
        csv_reader = csv.DictReader(stream)
        
        imported_count = 0
        updated_count = 0
        errors = []
        
        sheet, headers = get_data_sheet_and_headers()
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                name = row.get('name', '').strip()
                if not name:
                    continue
                
                # 既存データか確認
                existing = name in otera_database
                
                # スプレッドシートに書き込み
                if existing:
                    cell = sheet.find(name, in_column=1)
                    if cell:
                        row_data = [row.get(h, '') for h in headers]
                        sheet.update(f"A{cell.row}", [row_data])
                        updated_count += 1
                else:
                    row_data = [row.get(h, '') for h in headers]
                    sheet.append_row(row_data)
                    imported_count += 1
                
                otera_database[name] = dict(row)
                
            except Exception as e:
                errors.append(f"行{row_num}: {str(e)}")
        
        # キャッシュクリア
        cache_manager.clear_cache('temples')
        
        add_log("CSVインポート", f"新規{imported_count}件、更新{updated_count}件")
        
        return jsonify({
            "status": "success",
            "imported": imported_count,
            "updated": updated_count,
            "errors": errors
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@temple_bp.route("/get_access_stats")
@login_required
def get_access_stats():
    """閲覧回数統計"""
    try:
        client = get_spreadsheet_client()
        sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('access_log')
        records = sheet.get_all_records()
        
        # 集計
        temple_counts = {}
        for record in records:
            temple_name = record.get('temple_name', '')
            if temple_name:
                temple_counts[temple_name] = temple_counts.get(temple_name, 0) + 1
        
        # ソート
        sorted_stats = sorted(temple_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify({
            "stats": [{"name": name, "count": count} for name, count in sorted_stats]
        })
    except Exception as e:
        print(f"統計取得エラー: {e}")
        return jsonify({"stats": []})

@temple_bp.route("/get_comments/<temple_name>")
def get_comments(temple_name):
    """特定寺院のコメント取得"""
    try:
        client = get_spreadsheet_client()
        sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('comments')
        records = sheet.get_all_records()
        
        comments = [r for r in records if r.get('temple_name') == temple_name]
        comments.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({"comments": comments})
    except Exception as e:
        print(f"コメント取得エラー: {e}")
        return jsonify({"comments": []})

@temple_bp.route("/add_comment", methods=["POST"])
@login_required
def add_comment():
    """コメント追加"""
    from flask import session
    from utils.helpers import get_jst_timestamp
    
    temple_name = request.json.get('temple_name')
    comment_text = request.json.get('comment')
    
    if not temple_name or not comment_text:
        return jsonify({"status": "error", "message": "必須項目が入力されていません"}), 400
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('comments')
        
        timestamp = get_jst_timestamp()
        user_name = session.get('user_name', '不明')
        
        sheet.append_row([timestamp, temple_name, user_name, comment_text])
        
        add_log("コメント追加", f"{temple_name} にコメントを追加")
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"コメント追加エラー: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@temple_bp.route("/delete_comment", methods=["POST"])
@login_required
def delete_comment():
    """コメント削除"""
    row_number = request.json.get('row_number')
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('comments')
        sheet.delete_rows(row_number)
        
        add_log("コメント削除", f"行{row_number}のコメントを削除")
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"コメント削除エラー: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500    
from flask import Blueprint, jsonify, request, send_file
import csv
import io
from utils.decorators import login_required, role_required
from services.data_source import (
    add_log,
    load_data_from_sheet,
    load_fields_config,
    get_data_sheet_and_headers
)
from services.temple_crud import (
    update_temple_data,
    add_temple_data,
    delete_temple_data,
    update_fields_data
)
from services.cache import cache_manager
from utils.helpers import get_jst_now
from config import Config

temple_bp = Blueprint('temple', __name__)

# グローバルデータ（main.pyから移行）
otera_database = {}
field_config = []

# Flask-Cachingのインポート（循環インポート回避のため遅延インポート）
def get_cache():
    from main import cache
    return cache

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
        # 独自キャッシュをクリア
        cache_manager.clear_cache()
        
        # Flask-Cachingのキャッシュもクリア
        cache = get_cache()
        cache.delete('all_temples_data')
        cache.delete('temple_fields')
        
        otera_database = load_data_from_sheet(cache_manager)
        field_config = load_fields_config(cache_manager)
        add_log("データ更新", f"管理画面からリロードを実行（{len(otera_database)}件）")
        return jsonify({"status": "success", "count": len(otera_database)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@temple_bp.route("/get_all_data")
@login_required
def get_all_data():
    """全寺院データを取得（Flask-Cachingでキャッシュ）"""
    cache = get_cache()
    
    # キャッシュから取得を試みる
    @cache.cached(timeout=300, key_prefix='all_temples_data')
    def fetch_data():
        print("✅ データベースから取得（キャッシュなし）")
        return load_data_from_sheet(cache_manager)
    
    try:
        data = fetch_data()
        return jsonify(data)
    except Exception as e:
        print(f"データ取得エラー: {e}")
        return jsonify({"error": "データの読み込みに失敗しました"}), 500

@temple_bp.route("/get_fields")
def get_fields():
    """項目設定を取得（Flask-Cachingでキャッシュ）"""
    cache = get_cache()
    
    @cache.cached(timeout=300, key_prefix='temple_fields')
    def fetch_fields():
        print("✅ 項目設定を取得（キャッシュなし）")
        global field_config
        return field_config
    
    return jsonify(fetch_fields())

@temple_bp.route("/update_temple", methods=["POST"])
@login_required
@role_required('admin', 'editor')
def update_temple():
    """寺院情報を更新"""
    global otera_database
    
    req = request.json
    original_name = req['original_name']
    new_data = req['data']
    
    if not new_data.get('name'):
        return jsonify({"status": "error", "message": "寺院名は必須です"}), 400
    
    # CRUD操作実行
    success, message = update_temple_data(original_name, new_data, otera_database)
    
    if success:
        # Flask-Cachingのキャッシュもクリア
        cache = get_cache()
        cache.delete('all_temples_data')
        
        add_log("編集", f"{original_name} の情報を更新 → {new_data['name']}")
        return jsonify({"status": "success"})
    else:
        add_log("編集エラー", f"エラー: {message}")
        return jsonify({"status": "error", "message": message}), 500

@temple_bp.route("/add_temple", methods=["POST"])
@login_required
@role_required('admin', 'editor')
def add_temple():
    """新規寺院を追加"""
    global otera_database
    
    req = request.json
    new_data = req['data']
    name = new_data.get('name')
    
    # CRUD操作実行
    success, message = add_temple_data(new_data, otera_database)
    
    if success:
        # Flask-Cachingのキャッシュもクリア
        cache = get_cache()
        cache.delete('all_temples_data')
        
        add_log("追加", f"{name} を新規追加")
        return jsonify({"status": "success"})
    else:
        add_log("追加エラー", f"エラー: {message}")
        return jsonify({"status": "error", "message": message}), 400
# routes/temple_routes.py (Part 2) - 続き

@temple_bp.route("/delete_temple", methods=["POST"])
@login_required
@role_required('admin', 'editor')
def delete_temple():
    """寺院を削除"""
    global otera_database
    
    name = request.json.get('name')
    
    # CRUD操作実行
    success, message = delete_temple_data(name, otera_database)
    
    if success:
        # Flask-Cachingのキャッシュもクリア
        cache = get_cache()
        cache.delete('all_temples_data')
        
        add_log("削除", f"{name} を削除")
        return jsonify({"status": "success"})
    else:
        add_log("削除エラー", f"エラー: {message}")
        return jsonify({"status": "error", "message": message}), 404 if "見つかりません" in message else 500

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
        if Config.USE_SUPABASE:
            # Supabase版
            from services import supabase_db
            records = supabase_db.get_access_logs(limit=1000)
        else:
            # Google Sheets版
            from services.spreadsheet import get_spreadsheet_client
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
        if Config.USE_SUPABASE:
            # Supabase版
            from services import supabase_db
            comments = supabase_db.get_comments(temple_name)
        else:
            # Google Sheets版
            from services.spreadsheet import get_spreadsheet_client
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
        user_name = session.get('user_name', '不明')
        
        if Config.USE_SUPABASE:
            # Supabase版
            from services import supabase_db
            supabase_db.add_comment(temple_name, user_name, comment_text)
        else:
            # Google Sheets版
            from services.spreadsheet import get_spreadsheet_client
            client = get_spreadsheet_client()
            sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('comments')
            
            timestamp = get_jst_timestamp()
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
    if Config.USE_SUPABASE:
        # Supabase版では、コメントIDで削除
        comment_id = request.json.get('comment_id')
        if not comment_id:
            return jsonify({"status": "error", "message": "コメントIDが必要です"}), 400
        
        try:
            from services import supabase_db
            client = supabase_db.get_supabase_client()
            client.table('comments').delete().eq('id', comment_id).execute()
            
            add_log("コメント削除", f"コメントID {comment_id} を削除")
            return jsonify({"status": "success"})
        except Exception as e:
            print(f"コメント削除エラー: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        # Google Sheets版
        row_number = request.json.get('row_number')
        
        try:
            from services.spreadsheet import get_spreadsheet_client
            client = get_spreadsheet_client()
            sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('comments')
            sheet.delete_rows(row_number)
            
            add_log("コメント削除", f"行{row_number}のコメントを削除")
            
            return jsonify({"status": "success"})
        except Exception as e:
            print(f"コメント削除エラー: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500    
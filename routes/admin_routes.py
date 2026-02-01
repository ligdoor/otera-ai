from flask import Blueprint, render_template, jsonify, request, session, make_response
from utils.decorators import login_required, role_required
from services.data_source import add_log
from services.temple_crud import update_fields_data
from config import Config
import csv
import io

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
        from services import supabase_db
        try:
            logs = supabase_db.get_recent_logs(limit=50)
            logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return jsonify(logs)
        except Exception as e:
            print(f"ログ取得エラー: {e}")
            return jsonify([])
    else:
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

# ★ CSVインポート機能 ★
@admin_bp.route('/import_csv', methods=['POST'])
@login_required
@role_required('admin', 'editor')  # ★ 修正: リストではなく引数として渡す
def import_csv():
    """CSVインポート機能（Supabase専用）"""
    if not Config.USE_SUPABASE:
        return jsonify({'success': False, 'message': 'この機能はSupabase使用時のみ利用可能です'}), 400
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'ファイルが選択されていません'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'ファイルが選択されていません'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'message': 'CSVファイルを選択してください'}), 400
    
    try:
        # CSVをメモリで読み込み
        stream = io.StringIO(file.stream.read().decode('utf-8-sig'), newline=None)
        csv_reader = csv.DictReader(stream)
        
        imported = 0
        updated = 0
        errors = []
        
        # 項目設定を取得
        from routes.temple_routes import field_config
        from services import supabase_db
        from services.data_manager import data_manager
        
        # ユーザー情報を取得
        user_name = session.get('user_name', 'unknown')
        user_id = session.get('user_id', 'unknown')
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                temple_name = row.get('name', '').strip()
                if not temple_name:
                    errors.append(f"行{row_num}: 寺院名が空です")
                    continue
                
                # データを整形
                temple_data = {}
                for field in field_config:
                    key = field['key']
                    value = row.get(key, '')
                    temple_data[key] = value if value else ''
                
                # 既存データをチェック
                existing = data_manager.get_temple_by_name(temple_name)
                
                if existing:
                    # 更新
                    data_manager.update_temple(temple_name, temple_data)
                    updated += 1
                    
                    # ログ記録
                    supabase_db.add_log(
                        user_name=user_name,
                        user_id=user_id,
                        action='更新',
                        details=f"{temple_name}をCSVから更新",
                        ip_address=request.remote_addr or ''
                    )
                else:
                    # 新規追加
                    data_manager.create_temple(temple_data)
                    imported += 1
                    
                    # ログ記録
                    supabase_db.add_log(
                        user_name=user_name,
                        user_id=user_id,
                        action='追加',
                        details=f"{temple_name}をCSVから追加",
                        ip_address=request.remote_addr or ''
                    )
                
            except Exception as e:
                errors.append(f"行{row_num}: {str(e)}")
                print(f"行{row_num}のインポートエラー: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # キャッシュをクリア
        data_manager.clear_cache()
        
        # グローバルキャッシュもクリア
        from services.cache import cache_manager
        cache_manager.clear_cache()
        
        return jsonify({
            'success': True,
            'imported': imported,
            'updated': updated,
            'errors': errors
        })
        
    except Exception as e:
        print(f"CSVインポートエラー: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'インポート処理中にエラーが発生しました: {str(e)}'}), 500

# ★ CSVエクスポート機能 ★
@admin_bp.route('/export_csv')
@login_required
def export_csv():
    """CSVエクスポート機能"""
    try:
        from routes.temple_routes import field_config
        from services.data_manager import data_manager
        
        all_temples = data_manager.get_all_temples()
        
        # CSVを生成
        output = io.StringIO()
        
        # ヘッダー行（項目のキー）
        fieldnames = [field['key'] for field in field_config]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # データ行（辞書をリストに変換）
        temple_list = list(all_temples.values()) if isinstance(all_temples, dict) else all_temples
        
        for temple in temple_list:
            row = {}
            for key in fieldnames:
                row[key] = temple.get(key, '')
            writer.writerow(row)
        
        # レスポンスを作成
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
        response.headers['Content-Disposition'] = 'attachment; filename=temples_export.csv'
        
        return response
        
    except Exception as e:
        print(f"CSVエクスポートエラー: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
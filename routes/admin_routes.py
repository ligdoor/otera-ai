from flask import Blueprint, render_template, jsonify, request, session, make_response
from utils.decorators import login_required, role_required
from services.data_source import add_log
from services.temple_crud import update_fields_data
from config import Config
from maintenance import MaintenanceMode
from datetime import datetime
from services.supabase_db import get_supabase_client
import csv
import io

admin_bp = Blueprint('admin_routes', __name__)

# ============================================================
# メンテナンスモード管理API
# ============================================================

@admin_bp.route('/api/maintenance/status', methods=['GET'])
def get_maintenance_status():
    """メンテナンスモードの状態を取得"""
    try:
        enabled = MaintenanceMode.is_enabled()
        return jsonify({'enabled': enabled})
        
    except Exception as e:
        print(f"メンテナンス状態取得エラー: {e}")
        return jsonify({'enabled': False})


@admin_bp.route('/api/maintenance/toggle', methods=['POST'])
def toggle_maintenance():
    """メンテナンスモードの切り替え"""
    try:
        # セッションからユーザーIDを取得
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
        
        supabase = get_supabase_client()
        
        # ユーザーの権限と名前を確認
        user_result = supabase.table('users').select('role, name').eq('user_id', user_id).single().execute()
        
        if not user_result.data or user_result.data.get('role') != 'admin':
            return jsonify({'success': False, 'message': '管理者権限が必要です'}), 403
        
        # ユーザー名を取得
        user_name = user_result.data.get('name', user_id)
        
        # MaintenanceModeクラスのtoggleメソッドを使用
        result = MaintenanceMode.toggle(user_id)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'message': result.get('error', '切り替えに失敗しました')
            }), 500
        
        # 新しい状態を取得
        new_enabled = result.get('maintenance_mode', False)
        
        # ログ記録
        supabase.table('logs').insert({
            'user_id': user_id,
            'user': user_name,
            'action': f'メンテナンスモード{"有効化" if new_enabled else "無効化"}',
            'timestamp': datetime.now().isoformat()
        }).execute()
        
        return jsonify({
            'success': True,
            'enabled': new_enabled,
            'message': f'メンテナンスモードを{"有効" if new_enabled else "無効"}にしました'
        })
        
    except Exception as e:
        print(f"メンテナンスモード切り替えエラー: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500            
@admin_bp.route("/admin/fields")
@login_required
def admin_fields():
    """項目設定画面"""
    return render_template("admin_fields.html")

# ============================================================
# 使い方ガイドページ（編集者・管理者のみ）
# ============================================================

@admin_bp.route("/admin/guide/admin")
@login_required
@role_required(['admin', 'editor'])
def guide_admin():
    """寺院データ管理の使い方ガイド"""
    return render_template("guide/guide_admin.html")

@admin_bp.route("/admin/guide/fields")
@login_required
@role_required(['admin', 'editor'])
def guide_fields():
    """項目設定の使い方ガイド"""
    return render_template("guide/guide_fields.html")

@admin_bp.route("/admin/guide/items")
@login_required
@role_required(['admin', 'editor'])
def guide_items():
    """仏具管理の使い方ガイド"""
    return render_template("guide/guide_items.html")

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

@admin_bp.route('/import_csv', methods=['POST'])
@login_required
@role_required(['admin', 'editor'])
def import_csv():
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    if request.content_length > MAX_FILE_SIZE:
        return jsonify({'error': 'ファイルサイズが大きすぎます（10MB以下）'}), 413
    
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
        stream = io.StringIO(file.stream.read().decode('utf-8-sig'), newline=None)
        csv_reader = csv.DictReader(stream)
        
        imported = 0
        updated = 0
        errors = []
        
        from routes.temple_routes import field_config
        from services import supabase_db
        from services.data_manager import data_manager
        
        user_name = session.get('user_name', 'unknown')
        user_id = session.get('user_id', 'unknown')
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                temple_name = row.get('name', '').strip()
                if not temple_name:
                    errors.append(f"行{row_num}: 寺院名が空です")
                    continue
                
                temple_data = {}
                for field in field_config:
                    key = field['key']
                    value = row.get(key, '')
                    temple_data[key] = value if value else ''
                
                existing = data_manager.get_temple_by_name(temple_name)
                
                if existing:
                    data_manager.update_temple(temple_name, temple_data)
                    updated += 1
                    
                    supabase_db.add_log(
                        user_name=user_name,
                        user_id=user_id,
                        action='更新',
                        details=f"{temple_name}をCSVから更新",
                        ip_address=request.remote_addr or ''
                    )
                else:
                    data_manager.create_temple(temple_data)
                    imported += 1
                    
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
        
        data_manager.clear_cache()
        
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

@admin_bp.route('/export_csv')
@login_required
def export_csv():
    try:
        from routes.temple_routes import field_config
        from services.data_manager import data_manager
        
        all_temples = data_manager.get_all_temples()
        
        output = io.StringIO()
        
        fieldnames = [field['key'] for field in field_config]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        temple_list = list(all_temples.values()) if isinstance(all_temples, dict) else all_temples
        
        for temple in temple_list:
            row = {}
            for key in fieldnames:
                row[key] = temple.get(key, '')
            writer.writerow(row)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
        response.headers['Content-Disposition'] = 'attachment; filename=temples_export.csv'
        
        return response
        
    except Exception as e:
        print(f"CSVエクスポートエラー: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
# ============================================================
# 仏具管理
# ============================================================

@admin_bp.route('/admin/items')
@login_required
def admin_items():
    """仏具管理画面"""
    try:
        user_id = session.get('user_id')
        user_name = session.get('user_name', 'ゲスト')
        
        # DBから権限を取得
        supabase = get_supabase_client()
        user_result = supabase.table('users').select('role').eq('user_id', user_id).single().execute()
        
        if not user_result.data:
            return jsonify({"message": "ユーザー情報が見つかりません"}), 404
        
        user_role = user_result.data.get('role', 'viewer')
        
        # 権限チェック
        if user_role not in ['admin', 'editor']:
            return jsonify({"message": "この操作を行う権限がありません"}), 403
        
        print(f"[DEBUG] admin_items: user_name={user_name}, user_role={user_role}")
        return render_template('admin_items.html', user_name=user_name, user_role=user_role)
    
    except Exception as e:
        print(f"Error in admin_items: {e}")
        return jsonify({"message": "エラーが発生しました"}), 500

@admin_bp.route('/api/admin/items', methods=['GET'])
@login_required
def get_admin_items():
    """仏具一覧取得API"""
    try:
        supabase = get_supabase_client()
        items_response = supabase.table('buddhist_items').select('*').order('created_at', desc=True).execute()
        items = items_response.data if items_response.data else []
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        print(f"Error in get_admin_items: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/items/<item_id>', methods=['GET'])
@login_required
def get_admin_item(item_id):
    """仏具詳細取得API"""
    try:
        supabase = get_supabase_client()
        item_response = supabase.table('buddhist_items').select('*').eq('id', item_id).single().execute()
        if not item_response.data:
            return jsonify({'success': False, 'error': '仏具が見つかりません'}), 404
        return jsonify({'success': True, 'item': item_response.data})
    except Exception as e:
        print(f"Error in get_admin_item: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/items', methods=['POST'])
@login_required
def create_admin_item():
    """仏具作成API"""
    try:
        # 権限チェック
        user_id = session.get('user_id')
        supabase = get_supabase_client()
        user_result = supabase.table('users').select('role').eq('user_id', user_id).single().execute()
        
        if not user_result.data or user_result.data.get('role') not in ['admin', 'editor']:
            return jsonify({'success': False, 'error': '権限がありません'}), 403
        
        data = request.json
        if not data.get('name') or not data.get('category'):
            return jsonify({'success': False, 'error': '名前とカテゴリは必須です'}), 400
        item_data = {
            'name': data.get('name'), 'name_kana': data.get('name_kana'),
            'category': data.get('category'), 'description': data.get('description'),
            'usage': data.get('usage'), 'material': data.get('material'),
            'size': data.get('size'), 'main_image_url': data.get('main_image_url'),
            'stock_quantity': data.get('stock_quantity', 1),
            'display_order': data.get('display_order', 0),
            'is_public': data.get('is_public', True)
        }
        item_response = supabase.table('buddhist_items').insert(item_data).execute()
        if not item_response.data:
            return jsonify({'success': False, 'error': '作成に失敗しました'}), 500
        return jsonify({'success': True, 'item': item_response.data[0]})
    except Exception as e:
        print(f"Error in create_admin_item: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/items/<item_id>', methods=['PUT'])
@login_required
def update_admin_item(item_id):
    """仏具更新API"""
    try:
        # 権限チェック
        user_id = session.get('user_id')
        supabase = get_supabase_client()
        user_result = supabase.table('users').select('role').eq('user_id', user_id).single().execute()
        
        if not user_result.data or user_result.data.get('role') not in ['admin', 'editor']:
            return jsonify({'success': False, 'error': '権限がありません'}), 403
        
        data = request.json
        update_data = {k: v for k, v in {
            'name': data.get('name'), 'name_kana': data.get('name_kana'),
            'category': data.get('category'), 'description': data.get('description'),
            'usage': data.get('usage'), 'material': data.get('material'),
            'size': data.get('size'), 'main_image_url': data.get('main_image_url'),
            'stock_quantity': data.get('stock_quantity'),
            'display_order': data.get('display_order'),
            'is_public': data.get('is_public')
        }.items() if v is not None}
        item_response = supabase.table('buddhist_items').update(update_data).eq('id', item_id).execute()
        if not item_response.data:
            return jsonify({'success': False, 'error': '更新に失敗しました'}), 500
        return jsonify({'success': True, 'item': item_response.data[0]})
    except Exception as e:
        print(f"Error in update_admin_item: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/items/<item_id>', methods=['DELETE'])
@login_required
def delete_admin_item(item_id):
    """仏具削除API（管理者のみ）"""
    try:
        # 権限チェック（管理者のみ）
        user_id = session.get('user_id')
        supabase = get_supabase_client()
        user_result = supabase.table('users').select('role').eq('user_id', user_id).single().execute()
        
        if not user_result.data or user_result.data.get('role') != 'admin':
            return jsonify({'success': False, 'error': '管理者権限が必要です'}), 403
        
        supabase.table('buddhist_items').delete().eq('id', item_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in delete_admin_item: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/categories', methods=['GET'])
@login_required
def get_admin_categories():
    """カテゴリ一覧取得API"""
    try:
        supabase = get_supabase_client()
        categories_response = supabase.table('item_categories').select('*').order('display_order').execute()
        categories = categories_response.data if categories_response.data else []
        return jsonify({'success': True, 'categories': categories})
    except Exception as e:
        print(f"Error in get_admin_categories: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/upload-image', methods=['POST'])
@login_required
def upload_image():
    """画像アップロードAPI（WebP圧縮）"""
    try:
        # 権限チェック
        user_id = session.get('user_id')
        supabase = get_supabase_client()
        user_result = supabase.table('users').select('role').eq('user_id', user_id).single().execute()
        
        if not user_result.data or user_result.data.get('role') not in ['admin', 'editor']:
            return jsonify({'success': False, 'error': '権限がありません'}), 403
        
        # ファイルチェック
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'ファイルがありません'}), 400
        
        file = request.files['file']
        original_filename = request.form.get('filename', 'image.jpg')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400
        
        # 画像をWebP形式に圧縮
        from PIL import Image
        import io
        
        # 元のファイルサイズを先に取得
        file.stream.seek(0, 2)  # ファイルの末尾に移動
        original_size = file.stream.tell()
        file.stream.seek(0)  # ファイルの先頭に戻す
        
        # 画像を読み込み
        image = Image.open(file.stream)
        
        # RGBAの場合はRGBに変換（WebPはRGBAもサポートするが、lossyの場合はRGBが推奨）
        if image.mode in ('RGBA', 'LA', 'P'):
            # 透明度がある場合は白背景で合成
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # WebP形式で圧縮（lossy, quality=80）
        webp_buffer = io.BytesIO()
        image.save(webp_buffer, format='WebP', quality=80, method=6)
        webp_bytes = webp_buffer.getvalue()
        
        # ファイル名を.webpに変更
        filename_without_ext = original_filename.rsplit('.', 1)[0]
        storage_path = f"{filename_without_ext}.webp"
        
        # Supabase Storageにアップロード
        upload_result = supabase.storage.from_('temple-images').upload(
            storage_path,
            webp_bytes,
            file_options={"content-type": "image/webp"}
        )
        
        # 公開URLを取得
        public_url = supabase.storage.from_('temple-images').get_public_url(storage_path)
        
        # 圧縮情報をログ出力
        compressed_size = len(webp_bytes)
        if original_size > 0:
            compression_ratio = (1 - compressed_size / original_size) * 100
            print(f"[Image Upload] Original: {original_size:,} bytes → WebP: {compressed_size:,} bytes (圧縮率: {compression_ratio:.1f}%)")
        else:
            print(f"[Image Upload] WebP: {compressed_size:,} bytes")
        
        return jsonify({'success': True, 'url': public_url})
    
    except Exception as e:
        print(f"Error in upload_image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
"""
データ管理ルート

寺院データのCSV入出力機能を提供します。
データのインポート・エクスポートを担当します。
"""

from flask import Blueprint, jsonify, request, session, make_response
from utils.decorators import login_required, role_required
from config import Config
import csv
import io

# ============================================
# Blueprintの定義
# ============================================

admin_data_bp = Blueprint('admin_data', __name__)


# ============================================
# CSVインポート
# ============================================

@admin_data_bp.route('/import_csv', methods=['POST'])
@login_required
@role_required(['admin', 'editor'])
def import_csv():
    """
    CSVインポート
    
    CSVファイルから寺院データを一括インポートします。
    既存データは更新、新規データは追加されます。
    
    Form Data:
        file: CSVファイル（UTF-8 or UTF-8 with BOM）
    
    Returns:
        JSON: インポート結果
            success (bool): 成功した場合True
            imported (int): 新規追加件数
            updated (int): 更新件数
            errors (list): エラーのリスト
    
    Route:
        POST /import_csv
    
    Authentication:
        @login_required: ログイン必須
        @role_required: admin または editor 権限が必要
    
    Validation:
        - ファイルサイズ: 10MB以下
        - 拡張子: .csv
        - Supabase使用時のみ利用可能
    
    Process:
        1. ファイルをバリデーション
        2. CSVを読み込み
        3. 各行を処理
        4. 既存データは更新、新規データは追加
        5. ログを記録
        6. キャッシュをクリア
    
    Example Response:
        {
            "success": true,
            "imported": 5,
            "updated": 3,
            "errors": ["行10: 寺院名が空です"]
        }
    """
    # ファイルサイズ制限（10MB）
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    if request.content_length > MAX_FILE_SIZE:
        return jsonify({
            'error': 'ファイルサイズが大きすぎます（10MB以下）'
        }), 413
    
    # Supabase使用チェック
    if not Config.USE_SUPABASE:
        return jsonify({
            'success': False,
            'message': 'この機能はSupabase使用時のみ利用可能です'
        }), 400
    
    # ============================================
    # ファイル存在チェック
    # ============================================
    
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'message': 'ファイルが選択されていません'
        }), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'message': 'ファイルが選択されていません'
        }), 400
    
    # 拡張子チェック
    if not file.filename.endswith('.csv'):
        return jsonify({
            'success': False,
            'message': 'CSVファイルを選択してください'
        }), 400
    
    try:
        # ============================================
        # CSVファイルを読み込み
        # ============================================
        
        # BOM対応のUTF-8デコード
        stream = io.StringIO(
            file.stream.read().decode('utf-8-sig'),
            newline=None
        )
        csv_reader = csv.DictReader(stream)
        
        # カウンター初期化
        imported = 0  # 新規追加件数
        updated = 0   # 更新件数
        errors = []   # エラーリスト
        
        # 必要なモジュールをインポート
        from routes.temple.common import get_field_config
        from services.database import add_log
        from services.data_manager import data_manager
        
        # ユーザー情報を取得
        user_name = session.get('user_name', 'unknown')
        user_id = session.get('user_id', 'unknown')
        
        # フィールド設定を取得
        field_config = get_field_config()
        
        # ============================================
        # 各行を処理
        # ============================================
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # 寺院名を取得
                temple_name = row.get('name', '').strip()
                
                # 寺院名が空の場合はスキップ
                if not temple_name:
                    errors.append(f"行{row_num}: 寺院名が空です")
                    continue
                
                # 寺院データを構築
                temple_data = {}
                for field in field_config:
                    key = field['key']
                    value = row.get(key, '')
                    temple_data[key] = value if value else ''
                
                # 既存データか確認
                existing = data_manager.get_temple_by_name(temple_name)
                
                if existing:
                    # 更新
                    data_manager.update_temple(temple_name, temple_data)
                    updated += 1
                    
                    # ログを記録
                    add_log(
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
                    
                    # ログを記録
                    add_log(
                        user_name=user_name,
                        user_id=user_id,
                        action='追加',
                        details=f"{temple_name}をCSVから追加",
                        ip_address=request.remote_addr or ''
                    )
            
            except Exception as e:
                # エラーを記録
                errors.append(f"行{row_num}: {str(e)}")
                print(f"❌ 行{row_num}のインポートエラー: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # ============================================
        # キャッシュをクリア
        # ============================================
        
        data_manager.clear_cache()
        
        from services.cache import cache_manager
        cache_manager.clear_cache()
        
        print(f"✅ CSVインポート完了: 新規{imported}件、更新{updated}件")
        
        return jsonify({
            'success': True,
            'imported': imported,
            'updated': updated,
            'errors': errors
        })
    
    except Exception as e:
        print(f"❌ CSVインポートエラー: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'インポート処理中にエラーが発生しました: {str(e)}'
        }), 500


# ============================================
# CSVエクスポート
# ============================================

@admin_data_bp.route('/export_csv')
@login_required
def export_csv():
    """
    CSVエクスポート
    
    全寺院データをCSV形式でエクスポートします。
    Excel互換のBOM付きUTF-8エンコーディングを使用します。
    
    Returns:
        File: CSVファイル（temples_export.csv）
    
    Route:
        GET /export_csv
    
    Authentication:
        @login_required: ログイン必須
    
    CSV Format:
        - 1行目: ヘッダー（フィールド名）
        - 2行目以降: 寺院データ
        - エンコーディング: UTF-8 with BOM
    
    Example:
        GET /export_csv
        
        → temples_export.csv がダウンロードされる
    """
    try:
        # ============================================
        # データを取得
        # ============================================
        
        from routes.temple.common import get_field_config
        from services.data_manager import data_manager
        
        # 全寺院データを取得
        all_temples = data_manager.get_all_temples()
        
        # フィールド設定を取得
        field_config = get_field_config()
        
        # ============================================
        # CSVを生成
        # ============================================
        
        output = io.StringIO()
        
        # ヘッダー行を作成
        fieldnames = [field['key'] for field in field_config]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # 寺院データをリスト化
        temple_list = list(all_temples.values()) if isinstance(all_temples, dict) else all_temples
        
        # 各寺院のデータを書き込み
        for temple in temple_list:
            row = {}
            for key in fieldnames:
                row[key] = temple.get(key, '')
            writer.writerow(row)
        
        # ============================================
        # レスポンスを作成
        # ============================================
        
        response = make_response(output.getvalue())
        
        # BOM付きUTF-8（Excelで正しく開ける）
        response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
        response.headers['Content-Disposition'] = 'attachment; filename=temples_export.csv'
        
        print(f"📤 CSVエクスポート: {len(temple_list)}件")
        
        return response
    
    except Exception as e:
        print(f"❌ CSVエクスポートエラー: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

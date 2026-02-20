"""
寺院データ入出力・統計ルート

CSV入出力、アクセス統計、コメント機能を提供します。
データのインポート/エクスポートと統計情報の取得を担当します。
"""

import logging
from flask import Blueprint, jsonify, request, send_file, session
import csv
import io
from utils.decorators import login_required, role_required
from utils.helpers import get_jst_now, get_jst_timestamp
from services.data_source import add_log, get_data_sheet_and_headers
from services.cache import cache_manager
from .common import get_otera_database, get_field_config
from config import Config

# ============================================
# Blueprintの定義
# ============================================

temple_data_bp = Blueprint('temple_data', __name__)

logger = logging.getLogger(__name__)


# ============================================
# CSVエクスポート
# ============================================

@temple_data_bp.route("/export_csv")
@login_required
def export_csv():
    """
    CSVエクスポート
    
    全寺院データをCSV形式でエクスポートします。
    Excelで開くためにBOM付きUTF-8エンコーディングを使用します。
    
    Returns:
        ファイル: CSVファイル（temples_YYYYMMDD_HHMMSS.csv）
    
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
        
        → temples_20240213_150530.csv がダウンロードされる
    """
    try:
        # StringIOで文字列として構築
        output = io.StringIO()
        writer = csv.writer(output)
        
        # フィールド設定を取得
        field_config = get_field_config()
        
        # ヘッダー行を書き込み
        headers = [f['key'] for f in field_config]
        writer.writerow(headers)
        
        # 寺院データを取得
        otera_database = get_otera_database()
        
        # 各寺院のデータを書き込み
        for temple in otera_database.values():
            # ヘッダー順にデータを取得
            row = [temple.get(h, '') for h in headers]
            writer.writerow(row)
        
        # BytesIOに変換（BOM付きUTF-8）
        output.seek(0)
        byte_output = io.BytesIO()
        # BOM (Byte Order Mark) を追加してExcelで正しく開けるように
        byte_output.write(output.getvalue().encode('utf-8-sig'))
        byte_output.seek(0)
        
        # ログを記録
        add_log("CSVエクスポート", f"{len(otera_database)}件のデータをエクスポート")
        
        # ファイル名にタイムスタンプを付与
        filename = f'temples_{get_jst_now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        # ファイルとして送信
        return send_file(
            byte_output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"❌ CSVエクスポートエラー: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ============================================
# CSVインポート
# ============================================

@temple_data_bp.route("/import_csv", methods=["POST"])
@login_required
@role_required(['admin', 'editor'])
def import_csv():
    """
    CSVインポート
    
    CSVファイルから寺院データを一括インポートします。
    既存データは更新、新規データは追加されます。
    
    Request:
        Form Data:
            file: CSVファイル（UTF-8 or UTF-8 with BOM）
    
    Returns:
        JSON: インポート結果
            status (str): "success" | "error"
            imported (int): 新規追加件数
            updated (int): 更新件数
            errors (list): エラーのリスト
    
    Route:
        POST /import_csv
    
    Authentication:
        @login_required: ログイン必須
        @role_required: admin または editor 権限が必要
    
    CSV Format:
        - 1行目: ヘッダー（フィールド名）
        - 2行目以降: 寺院データ
        - name列は必須
    
    Example Response:
        {
            "status": "success",
            "imported": 5,
            "updated": 3,
            "errors": ["行10: 寺院名が空です"]
        }
    """
    # ファイルの存在確認
    if 'file' not in request.files:
        return jsonify({
            "status": "error",
            "message": "ファイルが選択されていません"
        }), 400
    
    file = request.files['file']
    
    # ファイル名の確認
    if file.filename == '':
        return jsonify({
            "status": "error",
            "message": "ファイルが選択されていません"
        }), 400
    
    try:
        # CSVファイルを読み込み（BOM対応）
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
        csv_reader = csv.DictReader(stream)
        
        # カウンター初期化
        imported_count = 0  # 新規追加件数
        updated_count = 0   # 更新件数
        errors = []         # エラーリスト
        
        # データソースを取得（Google Sheets）
        sheet, headers = get_data_sheet_and_headers()
        
        # 寺院データベースを取得
        otera_database = get_otera_database()
        
        # 各行を処理
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # 寺院名を取得
                name = row.get('name', '').strip()
                
                # 寺院名が空の場合はスキップ
                if not name:
                    continue
                
                # 既存データか確認
                existing = name in otera_database
                
                # Google Sheetsに書き込み
                if existing:
                    # 更新: 既存行を探して更新
                    cell = sheet.find(name, in_column=1)
                    if cell:
                        row_data = [row.get(h, '') for h in headers]
                        sheet.update(f"A{cell.row}", [row_data])
                        updated_count += 1
                else:
                    # 新規追加: 末尾に行を追加
                    row_data = [row.get(h, '') for h in headers]
                    sheet.append_row(row_data)
                    imported_count += 1
                
                # メモリ内のデータベースも更新
                otera_database[name] = dict(row)
            
            except Exception as e:
                # エラーを記録
                errors.append(f"行{row_num}: {str(e)}")
        
        # キャッシュをクリア
        cache_manager.clear_cache('temples')
        
        # ログを記録
        add_log("CSVインポート", f"新規{imported_count}件、更新{updated_count}件")
        
        return jsonify({
            "status": "success",
            "imported": imported_count,
            "updated": updated_count,
            "errors": errors
        })
    
    except Exception as e:
        logger.error(f"❌ CSVインポートエラー: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ============================================
# アクセス統計
# ============================================

@temple_data_bp.route("/get_access_stats")
@login_required
def get_access_stats():
    """
    アクセス統計を取得
    
    寺院ごとの閲覧回数を集計し、上位10件を返します。
    管理画面での人気寺院ランキング表示に使用します。
    
    Returns:
        JSON: アクセス統計
            stats (list): 寺院名と閲覧回数のリスト
    
    Route:
        GET /get_access_stats
    
    Authentication:
        @login_required: ログイン必須
    
    Example Response:
        {
            "stats": [
                {"name": "東大寺", "count": 150},
                {"name": "清水寺", "count": 120},
                {"name": "金閣寺", "count": 95}
            ]
        }
    """
    try:
        # データソースに応じて取得方法を変更
        if Config.USE_SUPABASE:
            # Supabase版
            from services.database import get_access_logs
            records = get_access_logs(limit=1000)
        else:
            # Google Sheets版
            from services.spreadsheet import get_spreadsheet_client
            client = get_spreadsheet_client()
            sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('access_log')
            records = sheet.get_all_records()
        
        # 寺院ごとにカウント
        temple_counts = {}
        for record in records:
            temple_name = record.get('temple_name', '')
            if temple_name:
                temple_counts[temple_name] = temple_counts.get(temple_name, 0) + 1
        
        # カウント順にソート（降順）して上位10件
        sorted_stats = sorted(
            temple_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # レスポンス形式に変換
        stats = [
            {"name": name, "count": count}
            for name, count in sorted_stats
        ]
        
        return jsonify({"stats": stats})
    
    except Exception as e:
        logger.error(f"❌ 統計取得エラー: {e}")
        return jsonify({"stats": []})


# ============================================
# コメント機能
# ============================================

@temple_data_bp.route("/get_comments/<temple_name>")
def get_comments(temple_name):
    """
    特定寺院のコメントを取得
    
    指定された寺院に投稿されたコメントを全て取得します。
    タイムスタンプの新しい順に並べられます。
    
    Args:
        temple_name: 寺院名（URLパラメータ）
    
    Returns:
        JSON: コメントリスト
            comments (list): コメントの配列
    
    Route:
        GET /get_comments/<temple_name>
    
    Authentication:
        不要（公開API）
    
    Example:
        GET /get_comments/東大寺
        
        {
            "comments": [
                {
                    "id": 123,
                    "temple_name": "東大寺",
                    "user_name": "山田太郎",
                    "comment": "素晴らしいお寺でした",
                    "timestamp": "2024-01-15T10:30:00+09:00"
                }
            ]
        }
    """
    try:
        # データソースに応じて取得方法を変更
        if Config.USE_SUPABASE:
            # Supabase版
            from services.database import get_comments as db_get_comments
            comments = db_get_comments(temple_name)
        else:
            # Google Sheets版
            from services.spreadsheet import get_spreadsheet_client
            client = get_spreadsheet_client()
            sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('comments')
            records = sheet.get_all_records()
            
            # 指定寺院のコメントをフィルター
            comments = [
                r for r in records
                if r.get('temple_name') == temple_name
            ]
            
            # タイムスタンプでソート（降順）
            comments.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({"comments": comments})
    
    except Exception as e:
        logger.error(f"❌ コメント取得エラー: {e}")
        return jsonify({"comments": []})


@temple_data_bp.route("/add_comment", methods=["POST"])
@login_required
def add_comment():
    """
    コメントを追加
    
    指定された寺院に新しいコメントを投稿します。
    
    Request Body:
        {
            "temple_name": "寺院名",
            "comment": "コメント内容"
        }
    
    Returns:
        JSON: 処理結果
            status (str): "success" | "error"
            message (str): エラーメッセージ（エラー時のみ）
    
    Route:
        POST /add_comment
    
    Authentication:
        @login_required: ログイン必須
    
    Example Request:
        POST /add_comment
        {
            "temple_name": "東大寺",
            "comment": "とても美しいお寺でした"
        }
    """
    # リクエストデータを取得
    temple_name = request.json.get('temple_name')
    comment_text = request.json.get('comment')
    
    # バリデーション
    if not temple_name or not comment_text:
        return jsonify({
            "status": "error",
            "message": "必須項目が入力されていません"
        }), 400
    
    try:
        # セッションからユーザー名を取得
        user_name = session.get('user_name', '不明')
        
        # データソースに応じて保存方法を変更
        if Config.USE_SUPABASE:
            # Supabase版
            from services.database import add_comment as db_add_comment
            db_add_comment(temple_name, user_name, comment_text)
        else:
            # Google Sheets版
            from services.spreadsheet import get_spreadsheet_client
            client = get_spreadsheet_client()
            sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('comments')
            
            # タイムスタンプを生成
            timestamp = get_jst_timestamp()
            
            # 行を追加
            sheet.append_row([timestamp, temple_name, user_name, comment_text])
        
        # ログを記録
        add_log("コメント追加", f"{temple_name} にコメントを追加")
        
        return jsonify({"status": "success"})
    
    except Exception as e:
        logger.error(f"❌ コメント追加エラー: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@temple_data_bp.route("/delete_comment", methods=["POST"])
@login_required
def delete_comment():
    """
    コメントを削除
    
    指定されたコメントをデータベースから削除します。
    Supabase版とGoogle Sheets版で削除方法が異なります。
    
    Request Body (Supabase):
        {
            "comment_id": 123
        }
    
    Request Body (Google Sheets):
        {
            "row_number": 5
        }
    
    Returns:
        JSON: 処理結果
            status (str): "success" | "error"
            message (str): エラーメッセージ（エラー時のみ）
    
    Route:
        POST /delete_comment
    
    Authentication:
        @login_required: ログイン必須
    """
    # データソースに応じて削除方法を変更
    if Config.USE_SUPABASE:
        # Supabase版: コメントIDで削除
        comment_id = request.json.get('comment_id')
        
        if not comment_id:
            return jsonify({
                "status": "error",
                "message": "コメントIDが必要です"
            }), 400
        
        try:
            from services.database import get_supabase_client
            client = get_supabase_client()
            
            # コメントを削除
            client.table('comments').delete().eq('id', comment_id).execute()
            
            # ログを記録
            add_log("コメント削除", f"コメントID {comment_id} を削除")
            
            return jsonify({"status": "success"})
        
        except Exception as e:
            logger.error(f"❌ コメント削除エラー: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    
    else:
        # Google Sheets版: 行番号で削除
        row_number = request.json.get('row_number')
        
        try:
            from services.spreadsheet import get_spreadsheet_client
            client = get_spreadsheet_client()
            sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('comments')
            
            # 行を削除
            sheet.delete_rows(row_number)
            
            # ログを記録
            add_log("コメント削除", f"行{row_number}のコメントを削除")
            
            return jsonify({"status": "success"})
        
        except Exception as e:
            logger.error(f"❌ コメント削除エラー: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

from flask import Blueprint, jsonify, request, send_file, render_template, session
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
from utils.helpers import get_jst_now, get_jst_timestamp
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

# ============================================
# フロント画面ルート
# ============================================

@temple_bp.route('/')
@login_required
def index():
    """メイン画面（ログイン必須）"""
    from flask import session
    user_name = session.get('user_name', 'ゲスト')
    return render_template('index.html', user_name=user_name)

# temple_routes.py の /ask エンドポイント（デバッグ版）

# temple_routes.py の /search_temple_by_name（最終修正版）

@temple_bp.route('/search_temple_by_name', methods=['POST'])
def search_temple_by_name():
    """
    寺院名で検索（曖昧検索対応・最終版）
    """
    data = request.json
    query = data.get('name', '').strip()
    
    print("========== /search_temple_by_name デバッグ開始 ==========")
    print(f"1. 検索クエリ: {query}")
    
    if not query:
        print("2. クエリが空です")
        return jsonify({'exact_match': None, 'suggestions': []})
    
    from services.data_manager import data_manager
    
    # 完全一致を探す
    exact_match = data_manager.get_temple_by_name(query)
    print(f"2. 完全一致検索結果: {exact_match}")
    
    if exact_match:
        print("3. 完全一致が見つかりました")
        return jsonify({
            'exact_match': exact_match,
            'suggestions': []
        })
    
    print("3. 完全一致なし、曖昧検索を開始")
    
    # 完全一致がない場合、似た名前を探す
    all_temples = data_manager.get_all_temples()
    
    if isinstance(all_temples, dict):
        temples_list = list(all_temples.values())
    else:
        temples_list = all_temples
    
    print(f"4. 全寺院数: {len(temples_list)}")
    
    # スコアベースで候補を抽出
    scored_suggestions = []
    
    for temple in temples_list:
        if not isinstance(temple, dict):
            continue
        
        temple_name = temple.get('name', '')
        if not temple_name:
            continue
        
        score = 0
        
        # 1. 完全一致（スコア100）
        if query == temple_name:
            score = 100
        # 2. 前方一致（スコア80）
        elif temple_name.startswith(query):
            score = 80
        # 3. 含まれる（スコア60）
        elif query in temple_name:
            score = 60
        # 4. 最後の1文字を除いて前方一致（スコア50）
        elif len(query) >= 2 and temple_name.startswith(query[:-1]):
            score = 50
        # 5. 最後の1文字を除いて含まれる（スコア40）
        elif len(query) >= 2 and query[:-1] in temple_name:
            score = 40
        # 6. 最初の2文字が一致（スコア30）
        elif len(query) >= 2 and len(temple_name) >= 2 and query[:2] == temple_name[:2]:
            score = 30
        # ★★★ 追加: 最初の1文字が一致（スコア20）★★★
        elif len(query) >= 1 and len(temple_name) >= 1 and query[0] == temple_name[0]:
            score = 20
        
        # ★★★ 修正: スコア20以上なら候補に追加 ★★★
        if score >= 20:
            scored_suggestions.append({
                'temple': temple,
                'score': score
            })
            print(f"   候補追加: {temple_name} (スコア: {score})")
    
    # スコア順にソート
    scored_suggestions.sort(key=lambda x: x['score'], reverse=True)
    
    # 上位5件を返す
    suggestions = [item['temple'] for item in scored_suggestions[:5]]
    
    print(f"5. 見つかった候補数: {len(suggestions)}")
    for i, s in enumerate(suggestions, 1):
        print(f"   候補{i}: {s.get('name', '')} (スコア: {scored_suggestions[i-1]['score']})")
    
    print("========== /search_temple_by_name デバッグ終了 ==========")
    
    return jsonify({
        'exact_match': None,
        'suggestions': suggestions
    })


# /ask エンドポイントも同様に修正

@temple_bp.route("/ask", methods=["POST"])
def ask():
    """AI質問応答（最終版）"""
    from services.ai import generate_answer_with_ai, generate_static_summary
    from services.data_manager import data_manager
    import re
    
    question = request.json.get("question", "")
    mode = request.json.get("mode", "qa")
    
    print("========== /ask エンドポイント デバッグ開始 ==========")
    print(f"1. 受信した質問: {question}")
    
    # 寺院名を抽出（完全一致を試す）
    temple_name = None
    for name in otera_database.keys():
        if name in question:
            temple_name = name
            print(f"2. 完全一致で見つかりました: {temple_name}")
            break
    
    # 完全一致しない場合、曖昧検索を試す
    if not temple_name:
        print("3. 完全一致なし、曖昧検索を開始")
        
        match = re.search(r'([^のは？\s]+)の', question)
        print(f"4. 正規表現マッチ結果: {match}")
        
        if match:
            candidate = match.group(1)
            print(f"5. 抽出された候補: {candidate}")
            
            all_temples = data_manager.get_all_temples()
            if isinstance(all_temples, dict):
                temples_list = list(all_temples.values())
            else:
                temples_list = all_temples
            
            print(f"6. 全寺院数: {len(temples_list)}")
            
            # 候補を探す - スコアベース検索
            best_match = None
            best_score = 0
            
            for temple in temples_list:
                temple_name_db = temple.get('name', '')
                score = 0
                
                # スコア計算（上と同じ）
                if candidate == temple_name_db:
                    score = 100
                elif temple_name_db.startswith(candidate):
                    score = 80
                elif candidate in temple_name_db:
                    score = 60
                elif len(candidate) >= 2 and temple_name_db.startswith(candidate[:-1]):
                    score = 50
                elif len(candidate) >= 2 and candidate[:-1] in temple_name_db:
                    score = 40
                elif len(candidate) >= 2 and len(temple_name_db) >= 2 and candidate[:2] == temple_name_db[:2]:
                    score = 30
                # ★★★ 追加: 最初の1文字が一致（スコア20）★★★
                elif len(candidate) >= 1 and len(temple_name_db) >= 1 and candidate[0] == temple_name_db[0]:
                    score = 20
                
                if score > best_score:
                    best_score = score
                    best_match = temple_name_db
                    print(f"   新しいベストマッチ: {temple_name_db} (スコア: {score})")
            
            print(f"7. 最終的なベストマッチ: {best_match} (スコア: {best_score})")
            
            # ★★★ 修正: スコア20以上なら採用 ★★★
            if best_match and best_score >= 20:
                temple_name = best_match
                question = question.replace(candidate, temple_name)
                print(f"8. 寺院名確定: {temple_name}")
    
    if not temple_name:
        print("9. 寺院名が見つかりませんでした")
        return jsonify({"answer": "⚠️ 寺院名が見つかりませんでした。正確な寺院名を入力してください。"})
    
    print(f"10. 最終的な寺院名: {temple_name}")
    
    temple_info = otera_database.get(temple_name)
    
    if not temple_info:
        return jsonify({"answer": f"❌ {temple_name} の情報が見つかりませんでした。"})
    
    # アクセスログを記録
    if Config.USE_SUPABASE:
        from services import supabase_db
        supabase_db.add_access_log(temple_name, question)
    
    # モードに応じて回答生成
    if mode == "summary":
        answer = generate_static_summary(temple_info, field_config)
    else:
        answer = generate_answer_with_ai(temple_info, question, field_config)
    
    print(f"11. 回答生成完了")
    print("========== /ask エンドポイント デバッグ終了 ==========")
    
    return jsonify({"answer": answer})

# ============================================
# データ管理ルート
# ============================================

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

# ============================================
# CRUD操作ルート
# ============================================

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
        # キャッシュクリアを修正
        try:
            cache = get_cache()
            cache.clear()
        except:
            pass
        
        from services.cache import cache_manager
        cache_manager.clear_cache()
        
        # ★ 修正: add_log の呼び出しを supabase_db に変更
        if Config.USE_SUPABASE:
            from services import supabase_db
            supabase_db.add_log(
                action='編集',
                details=f"{original_name} の情報を更新 → {new_data['name']}"
            )
        else:
            from services.data_source import add_log
            add_log("編集", f"{original_name} の情報を更新 → {new_data['name']}")
        
        return jsonify({"status": "success"})
    else:
        # ★ 修正: エラーログも同様に
        if Config.USE_SUPABASE:
            from services import supabase_db
            supabase_db.add_log(
                action='編集エラー',
                details=f"エラー: {message}"
            )
        else:
            from services.data_source import add_log
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
        # キャッシュクリア
        try:
            cache = get_cache()
            cache.clear()
        except:
            pass
        
        from services.cache import cache_manager
        cache_manager.clear_cache()
        
        # ★ 修正: add_log の呼び出しを supabase_db に変更
        if Config.USE_SUPABASE:
            from services import supabase_db
            supabase_db.add_log(
                action='追加',
                details=f"{name} を新規追加"
            )
        else:
            from services.data_source import add_log
            add_log("追加", f"{name} を新規追加")
        
        return jsonify({"status": "success"})
    else:
        # ★ 修正: エラーログも同様に
        if Config.USE_SUPABASE:
            from services import supabase_db
            supabase_db.add_log(
                action='追加エラー',
                details=f"エラー: {message}"
            )
        else:
            from services.data_source import add_log
            add_log("追加エラー", f"エラー: {message}")
        
        return jsonify({"status": "error", "message": message}), 400

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
        # キャッシュクリア
        try:
            cache = get_cache()
            cache.clear()
        except:
            pass
        
        from services.cache import cache_manager
        cache_manager.clear_cache()
        
        # ★ 修正: add_log の呼び出しを supabase_db に変更
        if Config.USE_SUPABASE:
            from services import supabase_db
            supabase_db.add_log(
                action='削除',
                details=f"{name} を削除"
            )
        else:
            from services.data_source import add_log
            add_log("削除", f"{name} を削除")
        
        return jsonify({"status": "success"})
    else:
        # ★ 修正: エラーログも同様に
        if Config.USE_SUPABASE:
            from services import supabase_db
            supabase_db.add_log(
                action='削除エラー',
                details=f"エラー: {message}"
            )
        else:
            from services.data_source import add_log
            add_log("削除エラー", f"エラー: {message}")
        
        return jsonify({"status": "error", "message": message}), 404 if "見つかりません" in message else 500

# ============================================
# CSV入出力ルート
# ============================================

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

# ============================================
# 統計・コメント機能
# ============================================

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
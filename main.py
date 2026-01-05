import os
import json
import datetime
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

load_dotenv()

# --- 設定 ---
GOOGL_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GOOGL_API_KEY:
    genai.configure(api_key=GOOGL_API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')

app = Flask(__name__)
app.secret_key = 'secret_key_for_session'

DATA_SPREADSHEET_NAME = "otera_data"
CONFIG_SPREADSHEET_NAME = "otera_admin_config"

gc = None 

# スプレッドシート接続（リトライ機能付き）
def get_spreadsheet_client():
    global gc
    if gc is None:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        
        # 3回までリトライする
        for i in range(3):
            try:
                if creds_json_str:
                    creds_dict = json.loads(creds_json_str)
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                else:
                    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
                
                gc = gspread.authorize(creds)
                return gc
            except Exception as e:
                print(f"接続リトライ中({i+1}/3): {e}")
                time.sleep(2) # 2秒待つ
                
    return gc

def get_admin_password():
    try:
        client = get_spreadsheet_client()
        sheet = client.open(CONFIG_SPREADSHEET_NAME).sheet1
        records = sheet.get_all_records()
        for row in records:
            if row.get('key') == 'admin_password':
                return str(row.get('value'))
        return "admin1234"
    except: return "admin1234"

# ★項目定義(fields)を読み込む
def load_fields_config():
    fields = []
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('fields')
        records = sheet.get_all_records()
        # order順に並び替え
        records.sort(key=lambda x: x['order'])
        fields = records
    except Exception as e:
        print(f"項目設定読み込みエラー: {e}")
        # エラー時はデフォルト設定
        fields = [
            {'key': 'name', 'label': '寺院名', 'order': 1},
            {'key': 'sect', 'label': '宗派', 'order': 2},
            {'key': 'address', 'label': '住所', 'order': 3},
            {'key': 'transport', 'label': '搬送持ち物', 'order': 4},
            {'key': 'nokanshiyo', 'label': '納棺仕様', 'order': 5},
            {'key': 'kakimono', 'label': '書き物', 'order': 6},
            {'key': 'flow', 'label': '式の流れ', 'order': 7},
            {'key': 'caution', 'label': '注意事項', 'order': 8}
        ]
    return fields

# データ読み込み
def load_data_from_sheet():
    data = {}
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).sheet1
        records = sheet.get_all_records()
        for row in records:
            if 'name' in row and row['name']:
                clean_row = {k: str(v).strip() for k, v in row.items()}
                data[clean_row['name']] = clean_row
        print("★データ更新完了")
    except Exception as e:
        print(f"読み込みエラー: {e}")
    return data

# グローバル変数で保持
otera_database = load_data_from_sheet()
field_config = load_fields_config()

# --- ルーティング ---

@app.route("/")
def index():
    return render_template("index.html")

# ★項目設定ページ
@app.route("/admin/fields")
def admin_fields():
    if not session.get('is_admin'): return redirect(url_for('admin'))
    return render_template("admin_fields.html")

# ★項目設定の更新API
@app.route("/update_fields", methods=["POST"])
def update_fields():
    if not session.get('is_admin'): return "Unauthorized", 401
    new_fields = request.json['fields']
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('fields')
        sheet.clear()
        # ヘッダー書き込み
        sheet.append_row(['key', 'label', 'order'])
        # データ書き込み
        rows = [[f['key'], f['label'], f['order']] for f in new_fields]
        sheet.append_rows(rows)
        
        # メモリ更新
        global field_config
        field_config = new_fields
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/reload_data", methods=["POST"])
def reload_data():
    if not session.get('is_admin'): return "Unauthorized", 401
    global otera_database, field_config
    otera_database = load_data_from_sheet()
    field_config = load_fields_config() # 設定もリロード
    return jsonify({"status": "success"})

@app.route("/admin", methods=["GET", "POST"])
def admin():
    current_password = get_admin_password()
    if request.method == "POST":
        input_password = request.form.get("password")
        if input_password == current_password:
            session['is_admin'] = True
            return render_template("admin.html")
        else:
            return """<script>alert('パスワードが違います'); window.location.href='/admin';</script>"""
    
    if session.get('is_admin'):
        return render_template("admin.html")
    else:
        return f"""
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f4f6f8; }}
                form {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; width: 300px; }}
                input {{ padding: 10px; width: 100%; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }}
                button {{ padding: 10px 20px; background: #1a237e; color: white; border: none; border-radius: 4px; cursor: pointer; width: 100%; font-weight: bold; }}
            </style>
        </head>
        <body>
            <form method="post">
                <h2 style="color:#1a237e; margin-top:0;">管理者ログイン</h2>
                <input type="password" name="password" placeholder="パスワード" required>
                <button type="submit">ログイン</button>
            </form>
        </body>
        </html>
        """

@app.route("/get_all_data")
def get_all_data():
    if not session.get('is_admin'): return "Unauthorized", 401
    return jsonify(otera_database)

@app.route("/get_fields")
def get_fields():
    # フロントエンドに設定を渡す
    return jsonify(field_config)

def get_data_sheet_and_headers():
    client = get_spreadsheet_client()
    sheet = client.open(DATA_SPREADSHEET_NAME).sheet1
    headers = sheet.row_values(1) 
    return sheet, headers

@app.route("/update_temple", methods=["POST"])
def update_temple():
    if not session.get('is_admin'): return "Unauthorized", 401
    req = request.json
    original_name = req['original_name']
    new_data = req['data']
    try:
        sheet, headers = get_data_sheet_and_headers()
        # ★新機能：もし新しい項目(key)がスプレッドシートの1行目に無ければ自動追加する
        # (これでアプリから項目追加した時に、データシート側も自動で列が増える)
        current_headers = headers
        for key in new_data.keys():
            if key not in current_headers:
                # 最終列に追加
                sheet.update_cell(1, len(current_headers) + 1, key)
                current_headers.append(key)
        
        headers = current_headers # 更新後のヘッダーを使う

        cell = sheet.find(original_name, in_column=1)
        if cell:
            row_idx = cell.row
            row_data = [new_data.get(h, "") for h in headers]
            sheet.update(f"A{row_idx}", [row_data])
            if original_name in otera_database: del otera_database[original_name]
            otera_database[new_data['name']] = new_data
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "not_found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/add_temple", methods=["POST"])
def add_temple():
    if not session.get('is_admin'): return "Unauthorized", 401
    req = request.json
    new_data = req['data']
    name = new_data.get('name')
    if name in otera_database:
        return jsonify({"status": "error", "message": "その名前は既に存在します"}), 400
    try:
        sheet, headers = get_data_sheet_and_headers()
        # ヘッダー自動追加ロジック
        current_headers = headers
        for key in new_data.keys():
            if key not in current_headers:
                sheet.update_cell(1, len(current_headers) + 1, key)
                current_headers.append(key)
        headers = current_headers

        row_data = [new_data.get(h, "") for h in headers]
        sheet.append_row(row_data)
        otera_database[name] = new_data
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/delete_temple", methods=["POST"])
def delete_temple():
    if not session.get('is_admin'): return "Unauthorized", 401
    name = request.json.get('name')
    try:
        sheet, headers = get_data_sheet_and_headers()
        cell = sheet.find(name, in_column=1)
        if cell:
            sheet.delete_rows(cell.row)
            if name in otera_database: del otera_database[name]
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "not_found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- アプリ機能（動的生成に変更）---

def generate_static_summary(temple_info):
    def get(key): return temple_info.get(key) or '記載なし'
    map_url = f"https://www.google.com/maps/search/?api=1&query={temple_info.get('address','')}"
    copy_btn = f"""<button class="copy-btn" onclick="copyToClipboard('{temple_info.get('address','')}')">📋</button>"""
    
    # ★ここが重要：設定(field_config)に基づいてHTMLを動的に作る
    html = f"""<div style="font-size:1.1em; font-weight:bold; color:#1a237e; margin-bottom:10px;">{get('name')} 情報</div>"""
    
    # 基本情報（固定）
    html += f"""<b>【基本情報】</b><br>"""
    # name以外の項目をループで表示
    for field in field_config:
        key = field['key']
        label = field['label']
        if key == 'name': continue
        
        val = get(key)
        
        # 住所の場合の特別扱い
        if key == 'address':
            html += f"""{label}: {val} {copy_btn}<br>
            <a href="{map_url}" target="_blank" style="color:#1a237e; font-weight:bold; text-decoration:underline;">📍Googleマップを開く</a><br>"""
        # 搬送持ち物の場合の特別扱い(赤字)
        elif key == 'transport':
            html += f"""{label}: <span style="color:#c62828; font-weight:bold;">{val}</span><br>"""
        else:
            html += f"""{label}: {val}<br>"""
            
    return html

def generate_answer_with_ai(temple_info, user_question):
    # プロンプトも動的に生成
    info_text = ""
    for field in field_config:
        key = field['key']
        label = field['label']
        val = temple_info.get(key, '記載なし')
        info_text += f"{label}: {val}\n"

    prompt = f"""
    【役割】葬儀施行スタッフ専用の業務支援AI
    【参照データ】
    {info_text}
    
    ユーザーの質問: 「{user_question}」
    【指示】質問に対する答えのみを簡潔に。挨拶不要。
    """
    try:
        if not GOOGL_API_KEY: return "AI機能は現在利用できません。"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"エラー: {e}"

@app.route("/get_temple_names", methods=["GET"])
def get_temple_names():
    return jsonify({"names": sorted(list(otera_database.keys()))})

@app.route("/get_sects", methods=["GET"])
def get_sects():
    sects = set()
    for t in otera_database.values():
        if 'sect' in t and t['sect']:
            sects.add(t['sect'])
    return jsonify({"sects": sorted(list(sects))})

@app.route("/search_by_sect", methods=["POST"])
def search_by_sect():
    target_sect = request.json['sect']
    result_list = []
    for temple in otera_database.values():
        if temple.get('sect') == target_sect:
            result_list.append({
                "name": temple['name'],
                "address": temple['address']
            })
    return jsonify({"results": result_list})

@app.route("/ask", methods=["POST"])
def ask():
    user_question = request.json['question']
    found_temple = None
    if user_question in otera_database:
        found_temple = otera_database[user_question]
    else:
        for name in otera_database.keys():
            if name in user_question:
                found_temple = otera_database[name]
                break
    if not found_temple: return jsonify({"answer": "データが見つかりません。"})
    if user_question == found_temple['name']:
        answer = generate_static_summary(found_temple)
    else:
        answer = generate_answer_with_ai(found_temple, user_question)
    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
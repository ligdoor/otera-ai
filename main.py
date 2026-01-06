import os
import json
import datetime
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

def get_spreadsheet_client():
    global gc
    if gc is None:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if creds_json_str:
            creds_dict = json.loads(creds_json_str)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        gc = gspread.authorize(creds)
    return gc

# ログ記録
def add_log(action, details):
    try:
        user_name = session.get('user_name', '不明')
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('logs')
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sheet.append_row([timestamp, user_name, action, details])
    except Exception as e:
        print(f"ログ記録エラー: {e}")

# ユーザー認証（ログイン用）
def authenticate_user(user_id, password):
    try:
        client = get_spreadsheet_client()
        sheet = client.open(CONFIG_SPREADSHEET_NAME).worksheet('users')
        records = sheet.get_all_records()
        for user in records:
            if str(user.get('user_id')) == user_id and str(user.get('password')) == password:
                return user.get('name')
        return None
    except Exception as e:
        print(f"認証エラー: {e}")
        return None

# ★パスワード変更処理
@app.route("/change_password", methods=["POST"])
def change_password():
    if not session.get('is_admin'): return jsonify({"message": "ログインしていません"}), 401
    
    current_pass = request.json['current_pass']
    new_pass = request.json['new_pass']
    user_name = session.get('user_name') # セッションから名前を取得
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(CONFIG_SPREADSHEET_NAME).worksheet('users')
        
        # 名前（またはID）でユーザーを探す
        # ※本来はuser_idをセッションに保存すべきだが、今回はnameで検索してみる
        # もし同姓同名がいるならuser_idをセッションに入れる修正が必要
        cell = sheet.find(user_name, in_column=3) # C列(name)を検索
        
        if cell:
            row_idx = cell.row
            # 現在のパスワード確認（B列）
            current_pass_in_db = sheet.cell(row_idx, 2).value
            
            if str(current_pass_in_db) == current_pass:
                # パスワード更新
                sheet.update_cell(row_idx, 2, new_pass)
                add_log("パスワード変更", "自身のパスワードを変更しました")
                return jsonify({"status": "success"})
            else:
                return jsonify({"message": "現在のパスワードが間違っています"}), 400
        else:
            return jsonify({"message": "ユーザーが見つかりません"}), 404

    except Exception as e:
        return jsonify({"message": str(e)}), 500


# 項目定義
def load_fields_config():
    fields = []
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('fields')
        records = sheet.get_all_records()
        records.sort(key=lambda x: x['order'])
        fields = records
    except:
        fields = [{'key': 'name', 'label': '寺院名', 'order': 1}]
    return fields

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

otera_database = load_data_from_sheet()
field_config = load_fields_config()


# --- ルーティング ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        user_name = authenticate_user(user_id, password)
        
        if user_name:
            session['is_admin'] = True
            session['user_name'] = user_name
            return redirect(url_for('admin'))
        else:
            return """<script>alert('IDまたはパスワードが違います'); window.location.href='/admin';</script>"""
    
    if session.get('is_admin'):
        return render_template("admin.html", user_name=session.get('user_name'))
    else:
            return f"""
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
                <style>
                    body {{ font-family: -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #eef2f6; }}
                    .login-container {{ background: white; padding: 40px 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 90%; max-width: 400px; text-align: center; }}
                   h2 {{ color: #1a237e; margin-top: 0; }}
                    input {{ width: 100%; padding: 15px; margin: 10px 0; border: 2px solid #ddd; border-radius: 8px; font-size: 18px; box-sizing: border-box; appearance: none; }}
                    button {{ width: 100%; padding: 15px; margin-top: 20px; background-color: #1a237e; color: white; border: none; border-radius: 8px; font-size: 18px; font-weight: bold; cursor: pointer; }}
                    /* 戻るリンクのデザイン */
                    .back-link {{ display: block; margin-top: 20px; color: #666; text-decoration: none; font-size: 0.9rem; }}
                </style>
            </head>
            <body>
                <div class="login-container">
                    <form method="post">
                        <h2>スタッフログイン</h2>
                        <input type="text" name="user_id" placeholder="ログインID" required>
                        <input type="password" name="password" placeholder="パスワード" required>
                        <button type="submit">ログイン</button>
                    </form>
                    <!-- ここに追加 -->
                    <a href="/" class="back-link">← アプリへ戻る</a>
                </div>
            </body>
            </html>
            """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('admin'))

@app.route("/reload_data", methods=["POST"])
def reload_data():
    if not session.get('is_admin'): return "Unauthorized", 401
    global otera_database, field_config
    otera_database = load_data_from_sheet()
    field_config = load_fields_config()
    add_log("データ更新", "管理画面からリロードを実行")
    return jsonify({"status": "success"})

@app.route("/get_all_data")
def get_all_data():
    if not session.get('is_admin'): return "Unauthorized", 401
    return jsonify(otera_database)

@app.route("/get_fields")
def get_fields():
    return jsonify(field_config)

@app.route("/get_logs")
def get_logs():
    if not session.get('is_admin'): return "Unauthorized", 401
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('logs')
        records = sheet.get_all_records()
        return jsonify(records[-20:][::-1]) 
    except: return jsonify([])

@app.route("/admin/fields")
def admin_fields():
    if not session.get('is_admin'): return redirect(url_for('admin'))
    return render_template("admin_fields.html")

@app.route("/update_fields", methods=["POST"])
def update_fields():
    if not session.get('is_admin'): return "Unauthorized", 401
    new_fields = request.json['fields']
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('fields')
        sheet.clear()
        sheet.append_row(['key', 'label', 'order'])
        rows = [[f['key'], f['label'], f['order']] for f in new_fields]
        sheet.append_rows(rows)
        global field_config
        field_config = new_fields
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
            if original_name in otera_database: del otera_database[original_name]
            otera_database[new_data['name']] = new_data
            
            add_log("編集", f"{original_name} の情報を更新")
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
        current_headers = headers
        for key in new_data.keys():
            if key not in current_headers:
                sheet.update_cell(1, len(current_headers) + 1, key)
                current_headers.append(key)
        headers = current_headers

        row_data = [new_data.get(h, "") for h in headers]
        sheet.append_row(row_data)
        otera_database[name] = new_data
        
        add_log("追加", f"{name} を新規追加")
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
            add_log("削除", f"{name} を削除")
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "not_found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- アプリ機能 ---

def generate_static_summary(temple_info):
    def get(key): return temple_info.get(key) or '記載なし'
    map_url = f"https://www.google.com/maps/search/?api=1&query={temple_info.get('address','')}"
    copy_btn = f"""<button class="copy-btn" onclick="copyToClipboard('{temple_info.get('address','')}')">📋</button>"""
    
    html = f"""<div style="font-size:1.1em; font-weight:bold; color:#1a237e; margin-bottom:10px;">{get('name')} 情報</div>"""
    html += f"""<b>【基本情報】</b><br>"""
    
    for field in field_config:
        key = field['key']
        label = field['label']
        if key == 'name': continue
        val = get(key)
        
        if key == 'address':
            html += f"""{label}: {val} {copy_btn}<br>
            <a href="{map_url}" target="_blank" style="color:#1a237e; font-weight:bold; text-decoration:underline;">📍Googleマップを開く</a><br>"""
        elif key == 'transport':
            html += f"""{label}: <span style="color:#c62828; font-weight:bold;">{val}</span><br>"""
        else:
            html += f"""{label}: {val}<br>"""
    return html

def generate_answer_with_ai(temple_info, user_question):
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
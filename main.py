import os
import json
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

# --- 設定 ---
GOOGL_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GOOGL_API_KEY:
    raise ValueError("APIキーが設定されていません")

# 管理画面のパスワード（環境変数になければ 'admin1234'）
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin1234")

genai.configure(api_key=GOOGL_API_KEY)
model = genai.GenerativeModel('gemini-3-flash-preview')

app = Flask(__name__)
app.secret_key = 'secret_key_for_session' # セッション利用に必要（適当でOK）

SPREADSHEET_NAME = "otera_data"

# スプレッドシート接続オブジェクトをグローバルで保持
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

def load_data_from_sheet():
    data = {}
    try:
        client = get_spreadsheet_client()
        sheet = client.open(SPREADSHEET_NAME).sheet1
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


# --- ルーティング ---

@app.route("/")
def index():
    return render_template("index.html")

# --- 管理画面関連 ---

# ログイン画面兼、管理画面
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return render_template("admin.html")
        else:
            return "パスワードが違います", 403
    
    # ログイン済みなら画面表示、でなければパスワード入力
    if session.get('is_admin'):
        return render_template("admin.html")
    else:
        # 簡易ログインフォームを表示
        return """
        <form method="post" style="text-align:center; margin-top:50px;">
            <h2>管理者パスワードを入力</h2>
            <input type="password" name="password" style="padding:10px;">
            <button type="submit" style="padding:10px;">ログイン</button>
        </form>
        """

# 全データを返す（管理画面用）
@app.route("/get_all_data")
def get_all_data():
    if not session.get('is_admin'): return "Unauthorized", 401
    return jsonify(otera_database)

# データ更新API
@app.route("/update_temple", methods=["POST"])
def update_temple():
    if not session.get('is_admin'): return "Unauthorized", 401
    
    req = request.json
    original_name = req['original_name']
    new_data = req['data']
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(SPREADSHEET_NAME).sheet1
        
        # 名前（A列）で該当行を探す
        cell = sheet.find(original_name, in_column=1)
        if cell:
            row_idx = cell.row
            # 列の順番に合わせてリストを作成
            # (name, sect, address, nokanshiyo, kakimono, flow, caution, transport)
            # ※スプレッドシートの列順序と完全に一致させる必要があります！
            headers = sheet.row_values(1) # 1行目の項目名を取得
            
            row_data = []
            for col_name in headers:
                # フォームから送られてきたデータに対応する値を入れる
                val = new_data.get(col_name, "")
                row_data.append(val)
            
            # 行を更新
            sheet.update(range_name=f"A{row_idx}:H{row_idx}", values=[row_data])
            
            # メモリ上のデータも更新
            otera_database[new_data['name']] = new_data
            
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "not_found"}), 404

    except Exception as e:
        print(f"更新エラー: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# --- 以下、通常のアプリ機能 ---

def generate_static_summary(temple_info):
    def get(key): return temple_info.get(key) or '記載なし'
    map_url = f"https://www.google.com/maps/search/?api=1&query={temple_info['address']}"
    copy_btn = f"""<button class="copy-btn" onclick="copyToClipboard('{temple_info['address']}')">📋</button>"""
    summary = f"""<div style="font-size:1.1em; font-weight:bold; color:#1a237e; margin-bottom:10px;">{get('name')} 情報</div>
<b>【基本情報】</b>
宗派: {get('sect')}
住所: {get('address')} {copy_btn}
<a href="{map_url}" target="_blank" style="color:#1a237e; font-weight:bold; text-decoration:underline;">📍Googleマップを開く</a>
<b>【搬送・納棺】</b>
搬送持ち物: <span style="color:#c62828; font-weight:bold;">{get('transport')}</span>
納棺仕様　: {get('nokanshiyo')}
<b>【施行仕様】</b>
書き物　　: {get('kakimono')}
<b>【進行・注意】</b>
式の流れ　: {get('flow')}
注意事項　: {get('caution')}"""
    return summary

def generate_answer_with_ai(temple_info, user_question):
    def get(key): return temple_info.get(key) or '記載なし'
    prompt = f"""
    【役割】葬儀施行スタッフ専用の業務支援AI
    【参照データ】
    寺院名: {get('name')}
    搬送時の持ち物: {get('transport')}
    納棺仕様: {get('nokanshiyo')}
    書き物: {get('kakimono')}
    式の流れ: {get('flow')}
    注意事項: {get('caution')}
    住所: {get('address')}
    ユーザーの質問: 「{user_question}」
    【指示】質問に対する答えのみを簡潔に。挨拶不要。
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"エラー: {e}"

@app.route("/get_temple_names", methods=["GET"])
def get_temple_names():
    global otera_database
    otera_database = load_data_from_sheet()
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
    # 毎回ロードは重いので、更新APIが呼ばれた時だけメモリ更新するようにしているが、
    # 念のためここでもロードするなら global otera_database; otera_database = load_data_from_sheet()
    user_question = request.json['question']
    client_mode = request.json.get('mode')
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
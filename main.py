import os
import json
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# .envファイルを読み込む
load_dotenv()

# --- 設定 ---
GOOGL_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GOOGL_API_KEY:
    # Renderなどの設定ミス以外でここに来ることはないはず
    raise ValueError("APIキーが見つかりません。.envファイルか環境変りを確認してください")

genai.configure(api_key=GOOGL_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__)

# --- スプレッドシート設定 ---
SPREADSHEET_NAME = "otera_data" 

def load_data_from_sheet():
    data = {}
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if creds_json_str:
            creds_dict = json.loads(creds_json_str)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)

        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        records = sheet.get_all_records()

        for row in records:
            if 'name' in row and row['name']:
                clean_row = {k: str(v).strip() for k, v in row.items()}
                data[clean_row['name']] = clean_row
                
        print("★データ更新完了")
    except Exception as e:
        print(f"スプレッドシート読み込みエラー: {e}")
    return data

# 初期ロード
otera_database = load_data_from_sheet()


# --- 【ここを修正】AIを使わずに高速表示する関数 ---
def generate_static_summary(temple_info):
    def get(key): return temple_info.get(key) or '記載なし'

    map_url = f"https://www.google.com/maps/search/?api=1&query={temple_info['address']}"
    copy_btn = f"""<button class="copy-btn" onclick="copyToClipboard('{temple_info['address']}')">📋</button>"""

    # H列の「transport」を追加しました
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


# --- 【ここも修正】QAモード用 ---
def generate_answer_with_ai(temple_info, user_question):
    def get(key): return temple_info.get(key) or '記載なし'
    
    # プロンプトにも transport を追加
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
    
    【指示】
    ・質問に対する答えのみを、データから抜き出して簡潔に答えること。
    ・挨拶や「承知しました」などの前置きは禁止。
    ・データにない場合は「記載がありません」と答えること。
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"エラー: {e}"

# --- ルーティング ---

@app.route("/")
def index():
    return render_template("index.html")

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
    # 質問のたびにデータを最新にする
    global otera_database
    otera_database = load_data_from_sheet()

    user_question = request.json['question']
    client_mode = request.json.get('mode')
    
    # 検索ロジック
    found_temple = None
    if user_question in otera_database:
        found_temple = otera_database[user_question]
    else:
        for name in otera_database.keys():
            if name in user_question:
                found_temple = otera_database[name]
                break
    
    if not found_temple:
         return jsonify({"answer": "データが見つかりません。"})

    # --- モード分岐 ---
    # 1. お寺の名前と完全一致なら「概要モード」
    #    → AIを使わず、Pythonで即座に文字を返す！
    if user_question == found_temple['name']:
        answer = generate_static_summary(found_temple)
        
    # 2. それ以外なら「QAモード」
    #    → AIを使って賢く検索する！
    else:
        answer = generate_answer_with_ai(found_temple, user_question)

    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
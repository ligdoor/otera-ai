import os
import json
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
    raise ValueError("APIキーが見つかりません")

genai.configure(api_key=GOOGL_API_KEY)
model = genai.GenerativeModel('gemini-3-flash-preview')

app = Flask(__name__)

# --- 【変更点】Googleスプレッドシートの設定 ---
# あなたが作ったスプレッドシートの名前に書き換えてください
SPREADSHEET_NAME = "otera_data" 

# スプレッドシートからデータを読み込む関数
def load_data_from_sheet():
    data = {}
    try:
        # 認証情報の設定
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Render環境（環境変数）か、ローカル（JSONファイル）かで分岐
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if creds_json_str:
            # Render環境：環境変数からJSON文字列を読み込む
            creds_dict = json.loads(creds_json_str)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # ローカル環境：credentials.jsonファイルを読み込む
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)

        client = gspread.authorize(creds)

        # シートを開く
        sheet = client.open(SPREADSHEET_NAME).sheet1
        # 全データを辞書リストとして取得
        records = sheet.get_all_records()

        for row in records:
            # 空行対策
            if 'name' in row and row['name']:
                # 全て文字列に変換して空白除去
                clean_row = {k: str(v).strip() for k, v in row.items()}
                data[clean_row['name']] = clean_row
                
        print("★スプレッドシートからデータを更新しました")

    except Exception as e:
        print(f"スプレッドシート読み込みエラー: {e}")
        # エラー時は空のデータを返す（またはキャッシュを使う等の処理）
    
    return data

# 起動時に一度読み込む
otera_database = load_data_from_sheet()


# --- AI回答生成 ---
def generate_answer_with_ai(temple_info, user_question, mode="summary"):
    map_url = f"https://www.google.com/maps/search/?api=1&query={temple_info['address']}"
    copy_btn_html = f"""<button class="copy-btn" onclick="copyToClipboard('{temple_info['address']}')">📋</button>"""

    def get_info(key):
        return temple_info.get(key, '記載なし') or '記載なし'

    if mode == "qa":
        prompt = f"""
        【役割】葬儀施行スタッフ専用の業務支援AI
        【参照データ】
        寺院名: {get_info('name')}
        宗派: {get_info('sect')}
        住所: {get_info('address')}
        納棺仕様: {get_info('nokanshiyo')}
        書き物: {get_info('kakimono')}
        式の流れ: {get_info('flow')}
        注意事項: {get_info('caution')}
        
        ユーザーの質問: 「{user_question}」
        
        【指示】
        ・事実のみを箇条書きや体言止めで簡潔に回答。挨拶不要。
        """
    else:
        prompt = f"""
        【役割】葬儀施行スタッフ専用の業務支援AI
        【出力フォーマット】
        ## {get_info('name')} 情報
        **【基本情報】**
        *   **宗派:** {get_info('sect')}
        *   **住所:** <a href="{map_url}" target="_blank" style="color:#0056b3; text-decoration:underline;">{get_info('address')}</a> {copy_btn_html}
        **【施行仕様】**
        *   **納棺仕様:** {get_info('nokanshiyo')}
        *   **書き物:** {get_info('kakimono')}
        **【進行・注意】**
        *   **式の流れ:** {get_info('flow')}
        *   **注意事項:** {get_info('caution')}
        
        【指示】挨拶不要。Markdown形式。
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

# ★データを強制的に再読み込みする機能（リロード時などに呼ぶ）
@app.before_request
def reload_data_if_needed():
    # 本来は一定時間ごとか、Webhookで更新するのが良いが、
    # 簡易的に「アクセスがあるたび」ではなく「グローバル変数を参照」するだけにする。
    # リアルタイム性を高めるなら、ここ毎回ロードするか、
    # /reload エンドポイントを作って手動更新するなど工夫が必要。
    # 今回はシンプルに「リクエストのたびにロード」は重いので、
    # 検索系APIが呼ばれた時だけリロードするロジックにする手もあるが、
    # アクセス数が少なければ毎回ロードでも許容範囲かも。
    pass 

@app.route("/get_temple_names", methods=["GET"])
def get_temple_names():
    # ★リストを取得するタイミングで最新データを取得しなおす
    global otera_database
    otera_database = load_data_from_sheet()
    
    names = sorted(list(otera_database.keys()))
    return jsonify({"names": names})

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
    # 質問時にもデータを最新にする
    global otera_database
    otera_database = load_data_from_sheet()

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
    
    if not found_temple:
         return jsonify({"answer": "データが見つかりません。"})

    if user_question == found_temple['name']:
        mode = 'summary'
    elif client_mode == 'qa':
        mode = 'qa'
    elif len(user_question) < 30:
        mode = 'qa'
    else:
        mode = 'summary'

    answer = generate_answer_with_ai(found_temple, user_question, mode)
    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
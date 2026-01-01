import os
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify

# .envファイルを読み込む
load_dotenv()

# --- 設定 ---
# 環境変数からキーを読み込む（なければ直接指定）
GOOGL_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GOOGL_API_KEY:
    # Renderなどの設定ミス以外でここに来ることはないはず
    raise ValueError("APIキーが見つかりません。.envファイルか環境変りを確認してください")

genai.configure(api_key=GOOGL_API_KEY)
model = genai.GenerativeModel('gemini-3-flash-preview')

app = Flask(__name__)

# --- データ読み込み関数 ---
def load_otera_data(filename):
    data = {}
    try:
        df = pd.read_excel(filename, keep_default_na=False)
        for index, row in df.iterrows():
            if 'name' in row and row['name']:
                # すべての項目を文字列として取得
                clean_row = {k: str(v).strip() for k, v in row.items()}
                data[clean_row['name']] = clean_row
    except Exception as e:
        print(f"データ読み込みエラー: {e}")
    return data

otera_database = load_otera_data("otera_data.xlsx")


# --- AI回答生成（業務用）---
def generate_answer_with_ai(temple_info, user_question, mode="summary"):
    # マップURL
    map_url = f"https://www.google.com/maps/search/?api=1&query={temple_info['address']}"
    # コピーボタンHTML
    copy_btn_html = f"""<button class="copy-btn" onclick="copyToClipboard('{temple_info['address']}')">📋</button>"""

    # データの取得（空欄の場合は「記載なし」とする）
    def get_info(key):
        return temple_info.get(key, '記載なし') or '記載なし'

    if mode == "qa":
        # 【質問モード】一問一答形式
        prompt = f"""
        【役割】
        あなたは葬儀施行スタッフ専用の業務支援AIです。
        感情や挨拶を排し、質問に対してデータに基づいた事実のみを簡潔に回答してください。
        
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
        ・「です・ます」調は使用せず、「〜あり」「〜不可」など体言止めや箇条書きで簡潔に答えること。
        ・挨拶は一切不要。
        """
    else:
        # 【概要モード】全情報を定型フォーマットで表示
        prompt = f"""
        【役割】
        あなたは葬儀施行スタッフ専用の業務支援AIです。
        選択された寺院の施行情報を、以下の定型フォーマットに従って出力してください。
        
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
        
        【指示】
        ・挨拶や前置きは一切不要。
        ・見やすいように適宜改行を入れること。
        ・HTMLタグはリンクとボタン以外使用しない（Markdown形式で出力）。
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
    names = sorted(list(otera_database.keys()))
    return jsonify({"names": names})

@app.route("/get_sects", methods=["GET"])
def get_sects():
    # データ内に'sect'がない場合の対策
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
    client_mode = request.json.get('mode')
    
    # データ検索
    found_temple = None
    if user_question in otera_database:
        found_temple = otera_database[user_question]
    else:
        for name in otera_database.keys():
            if name in user_question:
                found_temple = otera_database[name]
                break
    
    if not found_temple:
         return jsonify({"answer": "データが見つかりません。寺院名を確認してください。"})

    # モード決定ロジック
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
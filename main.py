import csv
import os
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify

# .envファイルを読み込む（ローカル環境用）
load_dotenv()

# --- 設定 ---
# 環境変数からキーを読み込む（なければ直接指定）
GOOGL_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GOOGL_API_KEY:
    # Renderなどの設定ミス以外でここに来ることはないはず
    raise ValueError("APIキーが見つかりません。.envファイルか環境変りを確認してください")

genai.configure(api_key=GOOGL_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

app = Flask(__name__)

# --- データ読み込み関数 (Excel版) ---
def load_otera_data(filename):
    data = {}
    try:
        # Excelファイルを読み込む
        # keep_default_na=False は、空欄をNaNではなく空文字""として読み込む設定
        df = pd.read_excel(filename, keep_default_na=False)
        
        # 1行ずつ辞書に変換して登録
        for index, row in df.iterrows():
            if 'name' in row and row['name']:
                # データの余分な空白を削除
                clean_row = {k: str(v).strip() for k, v in row.items()}
                
                # 宗派が空欄なら「不明」を入れる
                if not clean_row.get('sect'):
                    clean_row['sect'] = "不明"
                    
                data[clean_row['name']] = clean_row
                
    except FileNotFoundError:
        print(f"エラー: {filename} が見つかりません。")
    except Exception as e:
        print(f"データ読み込みエラー: {e}")
        
    return data

# ★拡張子を .xlsx に変更！
otera_database = load_otera_data("otera_data.xlsx")

# --- AI回答生成 ---
def generate_answer_with_ai(temple_info, user_question):
    # Googleマップの検索用URL
    map_url = f"https://www.google.com/maps/search/?api=1&query={temple_info['address']}"
    
    # 住所コピー用のボタンHTML（JavaScriptの関数を呼び出す）
    copy_btn_html = f"""<button class="copy-btn" onclick="copyToClipboard('{temple_info['address']}')">📋コピー</button>"""
    
    prompt = f"""
    あなたは親切なお寺の案内役です。
    ユーザーから「{user_question}」について聞かれています。
    
    【重要】回答は必ず以下の構成（順番）で作成してください。
    
    1. **基本情報**
       - まず最初に、以下の情報を箇条書きでまとめて表示してください。
       - 寺名: {temple_info['name']}
       - 宗派: {temple_info.get('sect', '不明')}
       - 住所: <a href="{map_url}" target="_blank" style="color:#007bff; text-decoration:underline;">{temple_info['address']} (📍地図)</a> {copy_btn_html}
       - アクセス: {temple_info['access']}
       
    2. **案内と解説**
       - その後に、以下のお寺の魅力や注意点を、親しみやすい文章で解説してください。
       - 見どころ: {temple_info['detail']}
       - 注意点: {temple_info['caution']}
       
    ※見出しや太字を使って、スマホでも読みやすく整形してください。
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"エラーが発生しました: {e}"
    
    # --- ルーティング ---

@app.route("/")
def index():
    return render_template("index.html")

# 【追加】お寺の名前一覧を返す
@app.route("/get_temple_names", methods=["GET"])
def get_temple_names():
    names = sorted(list(otera_database.keys()))
    return jsonify({"names": names})

# 宗派一覧を返す
@app.route("/get_sects", methods=["GET"])
def get_sects():
    sects = sorted(list(set(t['sect'] for t in otera_database.values())))
    return jsonify({"sects": sects})

# 宗派検索
@app.route("/search_by_sect", methods=["POST"])
def search_by_sect():
    target_sect = request.json['sect']
    result_list = []
    for temple in otera_database.values():
        if temple['sect'] == target_sect:
            result_list.append({
                "name": temple['name'],
                "address": temple['address']
            })
    return jsonify({"results": result_list})

# お寺詳細（AI）
@app.route("/ask", methods=["POST"])
def ask():
    # ドロップダウンからお寺名が送られてくる前提
    user_question = request.json['question']
    
    found_temple = None
    # 完全一致で探す（ドロップダウン選択なので名前は正確）
    for name in otera_database.keys():
        if name == user_question or name in user_question:
            found_temple = otera_database[name]
            break
            
    if found_temple:
        answer = generate_answer_with_ai(found_temple, user_question)
        return jsonify({"answer": answer})
    else:
        return jsonify({"answer": "データが見つかりませんでした。"})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
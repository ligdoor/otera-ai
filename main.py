import csv
import os
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

# --- データ読み込み関数 (文字化け対策済み) ---
def load_otera_data(filename):
    data = {}
    try:
        # utf-8-sig でBOM問題を回避
        with open(filename, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            if reader.fieldnames:
                reader.fieldnames = [name.strip() for name in reader.fieldnames]
            
            for row in reader:
                if 'name' in row and row['name']:
                    clean_row = {k: v.strip() if v else v for k, v in row.items()}
                    # 宗派がない場合は「不明」としておく
                    if 'sect' not in clean_row or not clean_row['sect']:
                        clean_row['sect'] = "不明"
                    data[clean_row['name']] = clean_row
    except Exception as e:
        print(f"データ読み込みエラー: {e}")
    return data

otera_database = load_otera_data("otera_data.csv")

# --- AI回答生成関数 ---
def generate_answer_with_ai(temple_info, user_question):
    prompt = f"""
    あなたは親切なお寺の案内役です。以下の情報を元に回答してください。
    
    --- 参照情報 ---
    寺名: {temple_info['name']}
    宗派: {temple_info.get('sect', '不明')}
    住所: {temple_info['address']}
    アクセス: {temple_info['access']}
    見どころ: {temple_info['detail']}
    注意点: {temple_info['caution']}
    ---
    
    質問: {user_question}
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

# 1. 登録されている「宗派の一覧」を返す
@app.route("/get_sects", methods=["GET"])
def get_sects():
    # データベースから宗派だけを取り出して、重複をなくす(set)
    sects = sorted(list(set(t['sect'] for t in otera_database.values())))
    return jsonify({"sects": sects})

# 2. 指定された宗派のお寺リストを返す
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

# 3. お寺の詳細をAIで答える（既存機能）
@app.route("/ask", methods=["POST"])
def ask():
    user_question = request.json['question']
    
    # 質問文にお寺の名前が含まれているか探す
    found_temple = None
    for name in otera_database.keys():
        if name in user_question:
            found_temple = otera_database[name]
            break
            
    if found_temple:
        answer = generate_answer_with_ai(found_temple, user_question)
        return jsonify({"answer": answer})
    else:
        # 見つからない場合
        return jsonify({"answer": "申し訳ありません。そのお寺の情報はデータベースに見当たりませんでした。"})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
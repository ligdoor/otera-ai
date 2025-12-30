import csv
import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify

# --- 設定部分 ---

# ここに取得したGeminiのAPIキーを貼り付けてください
GOOGL_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GOOGL_API_KEY:
    # ローカル（自分のPC）で動かすとき用の予備コード
    # 公開するときはこの行を削除するか無視されます
    GOOGL_API_KEY = "AIzaSyCR42zXt_YfnL7Z7dWP_1lc9SlUlJQLcRU"

# Geminiの設定
genai.configure(api_key=GOOGL_API_KEY)

# 使用するモデルの設定（gemini-1.5-flash は高速で無料枠で使いやすいです）
model = genai.GenerativeModel('gemini-flash-latest')

# ----------------

app = Flask(__name__)

# CSVファイルからお寺のデータを読み込む関数
def load_otera_data(filename):
    data = {}
    try:
        with open(filename, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # 空行やデータ不備の対策
                if 'name' in row and row['name']:
                    data[row['name']] = row
    except FileNotFoundError:
        print(f"エラー: {filename} が見つかりません。")
    except KeyError as e:
        print(f"エラー: CSVファイルの項目名が正しくありません。{e} が見つかりません。")
    return data

# データベースを読み込む
otera_database = load_otera_data("otera_data.csv")


# AIに回答を生成させる関数 (Gemini版)
def generate_answer_with_ai(temple_info, user_question):
    # 指示文（プロンプト）の作成
    prompt = f"""
    あなたは日本のお寺に詳しい、親切な案内役です。
    以下の「参照情報」だけを使って、ユーザーの質問に答えてください。
    フレンドリーで分かりやすい言葉で、箇条書きなどを使いながら情報を整理して回答してください。
    参照情報にないことは「分かりません」と答えてください。

    --- 参照情報 ---
    寺名: {temple_info['name']}
    宗派: {temple_info.get('sect', '不明')} 
    場所: {temple_info['address']}
    アクセス: {temple_info['access']}
    見どころ: {temple_info['detail']}
    気をつける点: {temple_info['caution']}
    ---

    ユーザーの質問: {user_question}
    """

    print("\nAI(Gemini)が回答を作成中です...")

    try:
        # Geminiに質問を投げる
        response = model.generate_content(prompt)
        # 回答のテキストを取り出す
        return response.text
    except Exception as e:
        return f"AIとの通信中にエラーが発生しました: {e}"


# --- Webサーバーの処理 ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    user_question = request.json['question']
    
    # お寺の名前検索
    found_temple_name = None
    for temple_name in otera_database.keys():
        if temple_name in user_question:
            found_temple_name = temple_name
            break
    
    if found_temple_name:
        temple_info = otera_database[found_temple_name]
        ai_answer = generate_answer_with_ai(temple_info, user_question)
        return jsonify({"answer": ai_answer})
    else:
        not_found_message = "すみません、そのお寺の情報はデータベースにないようです。他のお寺（例：清水寺、金閣寺）で試してみてください。"
        return jsonify({"answer": not_found_message})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
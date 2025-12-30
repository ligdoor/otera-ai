import google.generativeai as genai

# ここにあなたのAPIキーを入れてください
GOOGL_API_KEY = "AIzaSyCR42zXt_YfnL7Z7dWP_1lc9SlUlJQLcRU"

genai.configure(api_key=GOOGL_API_KEY)

print("--- 使えるモデルの一覧 ---")
try:
    for m in genai.list_models():
        # チャット（文章生成）に使えるモデルだけを表示
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print("一覧の取得に失敗しました:", e)
print("------------------------")
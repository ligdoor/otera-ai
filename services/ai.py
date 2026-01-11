from google import genai
from google.genai import types
from config import Config

# Gemini クライアント初期化
client = None
if Config.GEMINI_API_KEY:
    client = genai.Client(api_key=Config.GEMINI_API_KEY)

def generate_static_summary(temple_info, field_config):
    """寺院情報の静的サマリーを生成"""
    def get(key):
        return temple_info.get(key) or '記載なし'
    
    temple_name = get('name')
    temple_name_escaped = temple_name.replace("'", "\\'")
    
    map_url = f"https://www.google.com/maps/search/?api=1&query={temple_info.get('address','')}"
    copy_btn = f"""<button class="copy-btn" onclick="copyToClipboard('{temple_info.get('address','')}')">📋</button>"""
    
    html = f"""<div style="font-size:1.1em; font-weight:bold; color:#1a237e; margin-bottom:10px;">{temple_name} 情報</div>"""
    
    html += f"""<div style="margin-bottom:15px;">
        <script>document.write(addFavoriteButton('{temple_name_escaped}'));</script>
    </div>"""
    
    html += f"""<b>【基本情報】</b><br>"""
    
    for field in field_config:
        key = field['key']
        label = field['label']
        if key == 'name':
            continue
        val = get(key)
        
        if key == 'address':
            html += f"""{label}: {val} {copy_btn}<br>
            <a href="{map_url}" target="_blank" style="color:#1a237e; font-weight:bold; text-decoration:underline;">📍Googleマップを開く</a><br>"""
        elif key == 'transport':
            html += f"""{label}: <span style="color:#c62828; font-weight:bold;">{val}</span><br>"""
        else:
            html += f"""{label}: {val}<br>"""
    return html

def generate_answer_with_ai(temple_info, user_question, field_config):
    """AIを使用して質問に回答"""
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
        if not Config.GEMINI_API_KEY:
            return "AI機能は現在利用できません。"
        
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=500
            )
        )
        return response.text
    except Exception as e:
        print(f"AI生成エラー: {e}")
        return f"エラー: AI応答の生成に失敗しました"
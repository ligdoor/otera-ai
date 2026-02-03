from google import genai
from google.genai import types
from config import Config

# Gemini クライアント初期化
client = None
if Config.GEMINI_API_KEY:
    client = genai.Client(api_key=Config.GEMINI_API_KEY)

def generate_static_summary(temple_info, field_config):
    """寺院情報の静的サマリーを生成（アコーディオン対応）"""
    import time

    def get(key):
        return temple_info.get(key) or ''
    
    temple_name = get('name')
    temple_name_escaped = temple_name.replace("'", "\\'")
    timestamp = int(time.time() * 1000)
    
    html = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; padding-bottom:10px; border-bottom:2px solid #1a237e;">
        <div style="font-size:1.1em; font-weight:bold; color:#1a237e;">🏯 {temple_name} 情報</div>
        <button class='favorite-btn-detail' onclick='toggleFavoriteDetail("{temple_name_escaped}")' 
                data-temple='{temple_name}' 
                style='background:none; border:2px solid #ddd; border-radius:50%; 
                    width:40px; height:40px; font-size:20px; cursor:pointer; 
                    transition:all 0.2s;'>
            ☆
        </button>
    </div>
    """    
    # カテゴリ定義
    categories = {
        'basic': {
            'title': '🏯 基本情報',
            'fields': ['sect', 'address', 'transport'],
            'default_open': True
        },
        'tsuya': {
            'title': '🌙 通夜の流れ',
            'fields': ['tsuya_narimono', 'tsuya_ippan_shoko', 'tsuya_shinzoku_shoko', 'tsuya_dokyo_length', 'tsuya_notes'],
            'default_open': False
        },
        'sougi': {
            'title': '☀️ 葬儀の流れ',
            'fields': ['sougi_narimono', 'sougi_ippan_shoko', 'sougi_shinzoku_shoko', 'sougi_dokyo_length', 'sougi_notes'],
            'default_open': False
        },
        'items': {
            'title': '📝 お膳・書き物',
            'fields': ['ozen_type', 'kakimono_detail', 'shonananoka_timing'],
            'default_open': False
        },
        'other': {
            'title': '⚠️ その他・特記事項',
            'fields': ['nokanshiyo', 'kakimono', 'flow', 'caution', 'sonota_tokki'],
            'default_open': False
        }
    }
    
    cat_index = 0
    for cat_key, cat_data in categories.items():
        # このカテゴリに表示する項目を収集
        fields_to_show = []
        for field in field_config:
            if field['key'] in cat_data['fields']:
                value = get(field['key'])
                fields_to_show.append({
                    'key': field['key'],
                    'label': field['label'],
                    'value': value
                })
        
        if len(fields_to_show) == 0:
            continue
        
        is_open = cat_data['default_open']
        active_class = 'active' if is_open else ''
        accordion_id = f"acc-{cat_key}-{cat_index}-{timestamp}"
        cat_index += 1
        
        # アコーディオンヘッダー
        html += f"""
        <div class="accordion-section">
            <div class="accordion-header {active_class}" id="header-{accordion_id}" onclick="toggleAccordionFront('header-{accordion_id}', '{accordion_id}')">
                <div class="accordion-title">
                    <span class="accordion-icon">▶</span>
                    <span>{cat_data['title']}</span>
                </div>
            </div>
            <div class="accordion-content {active_class}" id="{accordion_id}"{' style="max-height: none;"' if is_open else ''}>
                <div style="padding:4px 8px;">
        """
        
        # 各項目を表示
        for idx, item in enumerate(fields_to_show):
            display_value = item['value'] if item['value'].strip() else '記載なし'
            is_empty = not item['value'].strip()
            is_last = (idx == len(fields_to_show) - 1)
            
            if item['key'] == 'address' and not is_empty:
                # 住所の場合
                address_escaped = item['value'].replace("'", "\\'").replace('"', '&quot;')
                map_url = f"https://www.google.com/maps/search/?api=1&query={item['value']}"
                
                html += f"""
                <div style="margin-bottom:{'0' if is_last else '2px'};">
                    <div style="font-size:0.88rem; font-weight:600; color:#555; margin-bottom:2px;">{item['label']}:</div>
                    <span style="font-size:0.9rem;">{display_value}</span>
                    <button class="copy-btn" onclick="event.stopPropagation(); copyToClipboard('{address_escaped}')" style="margin-left:4px; padding:2px 6px; font-size:0.8rem;">📋</button>
                    <br>
                    <a href="{map_url}" target="_blank" style="color:#1a237e; font-weight:bold; text-decoration:underline; margin-top:2px; display:inline-block; font-size:0.85rem;">📍地図を開く</a>
                </div>
                """
            else:
                # その他の項目
                if is_empty:
                    formatted_value = display_value
                else:
                    formatted_value = display_value.replace('<p>', '<div style="margin:0; padding:0;">').replace('</p>', '</div>')
                    formatted_value = formatted_value.replace('<div style="margin:0; padding:0;"><br></div>', '<br>')
                
                if is_empty:
                    value_html = f'<div style="color:#999; font-style:italic; font-size:0.85rem; padding:3px 6px; background:#f9f9f9; border-radius:4px;">{formatted_value}</div>'
                else:
                    value_html = f'<div style="font-size:0.9rem; padding:3px 6px; background:#f9f9f9; border-radius:4px;">{formatted_value}</div>'
                
                html += f"""
                <div style="margin-bottom:{'0' if is_last else '2px'};">
                    <div style="font-size:0.88rem; font-weight:600; color:#555; margin-bottom:2px;">{item['label']}:</div>
                    {value_html}
                </div>
                """
                
        # アコーディオンを閉じる
        html += """
                </div>
            </div>
        </div>
        """
    
    return html
def generate_answer_with_ai(temple_info, user_question, field_config):
    """AIを使用して質問に回答"""
    info_text = ""
    for field in field_config:
        key = field['key']
        label = field['label']
        val = temple_info.get(key, '記載なし')
        info_text += f"{label}: {val}\n"
    
    temple_name = temple_info.get('name', '')

    # ★改善: 寺院名を明示した回答形式を指定
    prompt = f"""
    【役割】葬儀施行スタッフ専用の業務支援AI
    【参照データ】
    寺院名: {temple_name}
    {info_text}
    ユーザーの質問: 「{user_question}」
    
    【回答形式】
    必ず以下の形式で回答してください:
    「{temple_name}の[項目名]は[内容]です」
    
    例:
    - 質問「納棺の注意点は?」→ 「○○寺の納棺仕様は△△です」
    - 質問「書き物は?」→ 「○○寺の書き物は△△です」
    - 質問「住所は?」→ 「○○寺の住所は△△です」
    
    【特別な処理】
    - 住所を回答する場合は、必ず以下のHTMLを含めてください:
    <div style="margin-top:10px;">
    <a href="https://www.google.com/maps/search/?api=1&query={temple_info.get('address','')}" target="_blank" style="color:#1a237e; font-weight:bold; text-decoration:underline;">📍Googleマップを開く</a>
    <button class="copy-btn" onclick="copyToClipboard('{temple_info.get('address','')}')">📋 コピー</button>
    </div>
    
    【指示】
    - 挨拶は不要
    - 簡潔に答える
    - 必ず寺院名を含める
    """
    
    try:
        if not Config.GEMINI_API_KEY:
            return f"{temple_name}の情報: AI機能は現在利用できません。"
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=500
            )
        )
        return response.text
    except Exception as e:
        print(f"AI生成エラー: {e}")
        return f"{temple_name}の情報取得エラー: AI応答の生成に失敗しました"
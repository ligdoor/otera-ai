from google import genai
from google.genai import types
from config import Config

# Gemini クライアント初期化
client = None
if Config.GEMINI_API_KEY:
    client = genai.Client(api_key=Config.GEMINI_API_KEY)

def generate_static_summary(temple_info, field_config):
    """寺院情報の静的サマリーを生成（アコーディオン対応）"""
    def get(key):
        return temple_info.get(key) or ''
    
    temple_name = get('name')
    temple_name_escaped = temple_name.replace("'", "\\'")
    
    html = f"""
    <div style="font-size:1.1em; font-weight:bold; color:#1a237e; margin-bottom:10px;">{temple_name} 情報</div>
    <div style="margin-bottom:15px;">
        <script>
        if (typeof addFavoriteButton !== 'undefined') {{
            document.write(addFavoriteButton('{temple_name_escaped}'));
        }}
        </script>
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
        
        active_class = 'active' if cat_data['default_open'] else ''
        accordion_id = f"acc-{cat_key}-{cat_index}"
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
            <div class="accordion-content {active_class}" id="{accordion_id}">
                <div class="accordion-body">
        """
        
        # 各項目を表示
        for item in fields_to_show:
            display_value = item['value'] if item['value'].strip() else '記載なし'
            is_empty = not item['value'].strip()
            is_long_text = len(display_value) > 30
            
            if item['key'] == 'address' and not is_empty:
                # 住所の場合
                address_escaped = item['value'].replace("'", "\\'").replace('"', '&quot;')
                map_url = f"https://www.google.com/maps/search/?api=1&query={item['value']}"
                
                html += f"""
                <div style="margin-bottom:4px; padding:0; line-height:1.4;">
                    <strong style="font-size:0.88rem; line-height:1.3;">{item['label']}:</strong>
                    <span style="font-size:0.9rem; line-height:1.4;">{display_value}</span>
                    <button class="copy-btn" onclick="event.stopPropagation(); copyToClipboard('{address_escaped}')" style="margin-left:4px; padding:1px 6px; font-size:0.8rem;">📋</button>
                    <br>
                    <a href="{map_url}" target="_blank" style="color:#1a237e; font-weight:bold; text-decoration:underline; margin-top:3px; display:inline-block; font-size:0.85rem;">📍地図を開く</a>
                </div>
                """
            else:
                # その他の項目
                if is_empty:
                    value_html = f'<span class="important-text" style="color:#c62828; font-weight:600; background:#ffebee; padding:1px 4px; border-radius:3px; display:inline-block; font-size:0.9rem; line-height:1.4;">{display_value}</span>'
                elif is_empty:
                    value_html = f'<span class="empty-text" style="color:#999; font-style:italic; font-size:0.85rem; line-height:1.4;">{display_value}</span>'
                elif is_long_text:
                    value_html = f'<span class="long-text" style="display:block; margin-top:2px; line-height:1.5; font-size:0.9rem;">{display_value}</span>'
                else:
                    value_html = f'<span style="font-size:0.9rem; line-height:1.4;">{display_value}</span>'
                
                html += f"""
                <div style="margin-bottom:4px; padding:0; line-height:1.4;">
                    <strong style="font-size:0.88rem; line-height:1.3;">{item['label']}:</strong> {value_html}
                </div>
                """
        
        # アコーディオンを閉じる（★ ここが重要！）
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
        return f"{temple_name}の情報取得エラー: AI応答の生成に失敗しました"
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
    import re

    def get(key):
        value = temple_info.get(key) or ''
        return value
    
    def clean_html_selectively(text):
        """
        HTMLを選択的にクリーンアップ
        - 装飾タグ（太字、色など）は残す
        - インラインスタイルの背景色は削除
        - 不要なタグは削除
        """
        if not text:
            return ''
        
        # 1. 背景色のみ削除（文字色は残す）
        # background-color と background を削除
        text = re.sub(r'background-color\s*:\s*[^;]+;?', '', text)
        text = re.sub(r'background\s*:\s*[^;]+;?', '', text)
        
        # 2. <p>タグを<div>に変換（余白を制御しやすくするため）
        text = re.sub(r'<p([^>]*)>', r'<div\1>', text)
        text = re.sub(r'</p>', '</div>', text)
        
        # 3. 空のスタイル属性を削除
        text = re.sub(r'\s+style\s*=\s*["\'][\s;]*["\']', '', text)
        
        # 4. 連続する改行を整理
        text = re.sub(r'(<br[^>]*>\s*){2,}', '<br>', text)
        
        # 5. 前後の空白を削除
        text = text.strip()
        
        return text
    
    temple_name = get('name')
    temple_name_escaped = temple_name.replace("'", "\\'")
    timestamp = int(time.time() * 1000)
    
    # ヘッダー部分
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
        fieldsToShow = []
        for field in field_config:
            if field['key'] in cat_data['fields']:
                value = temple_info.get(field['key'], '')
                # ★ 装飾を残してクリーンアップ
                clean_value = clean_html_selectively(value)
                fieldsToShow.append({
                    'key': field['key'],
                    'label': field['label'],
                    'value': clean_value
                })
        
        # 表示する項目がない場合はスキップ
        if len(fieldsToShow) == 0:
            continue
        
        is_open = cat_data['default_open']
        active_class = 'active' if is_open else ''
        accordion_id = f"acc-{cat_key}-{cat_index}-{timestamp}"
        cat_index += 1
        
        # アコーディオンセクション
        html += f"""
        <div class="accordion-section">
            <div class="accordion-header {active_class}" id="header-{accordion_id}" onclick="toggleAccordionFront('header-{accordion_id}', '{accordion_id}')">
                <div class="accordion-title">
                    <span class="accordion-icon">▶</span>
                    <span>{cat_data['title']}</span>
                </div>
            </div>
            <div class="accordion-content {active_class}" id="{accordion_id}"{' style="max-height: none;"' if is_open else ''}>
                <div class="accordion-body">
        """
        
        # 各項目を表示
        for idx, item in enumerate(fieldsToShow):
            display_value = item['value'] if item['value'].strip() else '記載なし'
            is_empty = not item['value'].strip()
            is_last = (idx == len(fieldsToShow) - 1)
            
            if item['key'] == 'address' and not is_empty:
                # 住所の場合：地図リンクとコピーボタンを追加
                address_escaped = item['value'].replace("'", "\\'").replace('"', '&quot;')
                # HTMLタグを除去したプレーンテキストを取得（コピー用）
                address_plain = re.sub(r'<[^>]+>', '', item['value'])
                address_plain_escaped = address_plain.replace("'", "\\'").replace('"', '&quot;')
                map_url = f"https://www.google.com/maps/search/?api=1&query={address_plain}"
                
                html += f"""
                <div class="field-item" style="margin-bottom:{'10px' if not is_last else '0'}; padding-bottom:{'10px' if not is_last else '0'}; border-bottom:{'1px solid #e0e0e0' if not is_last else 'none'};">
                    <div class="field-label-display" style="margin-bottom:4px;">{item['label']}:</div>
                    <div class="field-value-display" style="margin-bottom:6px;">{display_value}
                        <button class="copy-btn" onclick="event.stopPropagation(); copyToClipboard('{address_plain_escaped}')">📋</button>
                    </div>
                    <a href="{map_url}" target="_blank" style="color:#1a237e; font-weight:bold; text-decoration:underline; display:inline-block; font-size:0.85rem;">📍地図を開く</a>
                </div>
                """
            else:
                # その他の項目：HTMLタグを残して表示
                value_class = 'field-value-display empty' if is_empty else 'field-value-display'
                
                html += f"""
                <div class="field-item" style="margin-bottom:{'10px' if not is_last else '0'}; padding-bottom:{'10px' if not is_last else '0'}; border-bottom:{'1px solid #e0e0e0' if not is_last else 'none'};">
                    <div class="field-label-display" style="margin-bottom:4px;">{item['label']}:</div>
                    <div class="{value_class}">{display_value}</div>
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
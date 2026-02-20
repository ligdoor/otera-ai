from google import genai
from google.genai import types
from config import Config
import re
import time
import html as html_module  # ★追加: HTMLエスケープ用

# Gemini クライアント初期化
gemini_client = None
if Config.GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)


def _sanitize_text(text: str) -> str:
    """
    テキストの危険なHTMLタグ・スクリプトを除去するサニタイズ関数
    
    ★修正(重要度:中): Geminiの出力やDBデータをHTMLに埋め込む前に
    サニタイズしてXSS攻撃を防ぐ。
    
    許可タグ: <br> <strong> <em> <div> <span>（スタイル付き）
    禁止タグ: <script> <iframe> <object> その他実行系タグ
    
    Args:
        text: サニタイズするテキスト
    
    Returns:
        str: サニタイズ済みテキスト
    """
    if not text:
        return ''
    
    # 1. <script>タグと中身を削除
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. イベントハンドラ属性を削除（onclick, onerror等）
    text = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+on\w+\s*=\s*[^\s>]+', '', text, flags=re.IGNORECASE)
    
    # 3. javascript: href/src を削除
    text = re.sub(r'(href|src)\s*=\s*["\']?\s*javascript:[^"\'>\s]*["\']?', '', text, flags=re.IGNORECASE)
    
    # 4. 危険なタグ（iframe, object, embed, form等）を削除
    dangerous_tags = r'<(iframe|object|embed|form|input|button|select|textarea|link|base|meta)[^>]*/?>'
    text = re.sub(dangerous_tags, '', text, flags=re.IGNORECASE)
    
    return text

def generate_answer_with_ai(temple_info, question, field_config):
    """
    AIを使って質問に回答を生成
    通夜・葬儀の質問には専用フォーマットを適用
    """
    temple_name = temple_info.get('name', '不明な寺院')
    
    # ★★★ 通夜・葬儀の質問かどうか判定 ★★★
    is_tsuya_question = re.search(r'通夜', question)
    is_sougi_question = re.search(r'葬儀|葬式', question)
    
    # ★★★ 通夜の質問の場合、専用フォーマットで応答 ★★★
    if is_tsuya_question:
        # ★修正: DBから来るデータをHTMLエスケープしてXSSを防ぐ
        temple_name_safe = html_module.escape(temple_name)
        response_parts = [f"<div style='font-weight: bold; font-size: 1.1em; margin-bottom: 10px; color: #1a237e;'>🌙 {temple_name_safe}の通夜</div>"]
        
        # 通夜関連の項目を取得（★修正: エスケープ処理）
        narimono = html_module.escape(temple_info.get('tsuya_narimono', '') or '')
        ippan    = html_module.escape(temple_info.get('tsuya_ippan_shoko', '') or '')
        shinzoku = html_module.escape(temple_info.get('tsuya_shinzoku_shoko', '') or '')
        dokyo    = html_module.escape(temple_info.get('tsuya_dokyo_length', '') or '')
        notes    = html_module.escape(temple_info.get('tsuya_notes', '') or '')
        
        response_parts.append("<div style='margin-left: 10px; line-height: 1.8;'>")
        response_parts.append(f"・<strong>鳴物・葬具</strong>: {narimono if narimono else '記載なし'}<br>")
        response_parts.append(f"・<strong>一般焼香</strong>: {ippan if ippan else '記載なし'}<br>")
        response_parts.append(f"・<strong>親族焼香</strong>: {shinzoku if shinzoku else '記載なし'}<br>")
        response_parts.append(f"・<strong>読経の長さ</strong>: {dokyo if dokyo else '記載なし'}<br>")
        response_parts.append(f"・<strong>備考</strong>: {notes if notes else '記載なし'}")
        response_parts.append("</div>")
        
        return "".join(response_parts)
    
    # ★★★ 葬儀の質問の場合、専用フォーマットで応答 ★★★
    if is_sougi_question:
        # ★修正: DBから来るデータをHTMLエスケープしてXSSを防ぐ
        temple_name_safe = html_module.escape(temple_name)
        response_parts = [f"<div style='font-weight: bold; font-size: 1.1em; margin-bottom: 10px; color: #1a237e;'>☀️ {temple_name_safe}の葬儀</div>"]
        
        # 葬儀関連の項目を取得（★修正: エスケープ処理）
        narimono = html_module.escape(temple_info.get('sougi_narimono', '') or '')
        ippan    = html_module.escape(temple_info.get('sougi_ippan_shoko', '') or '')
        shinzoku = html_module.escape(temple_info.get('sougi_shinzoku_shoko', '') or '')
        dokyo    = html_module.escape(temple_info.get('sougi_dokyo_length', '') or '')
        notes    = html_module.escape(temple_info.get('sougi_notes', '') or '')
        
        response_parts.append("<div style='margin-left: 10px; line-height: 1.8;'>")
        response_parts.append(f"・<strong>鳴物・葬具</strong>: {narimono if narimono else '記載なし'}<br>")
        response_parts.append(f"・<strong>一般焼香</strong>: {ippan if ippan else '記載なし'}<br>")
        response_parts.append(f"・<strong>親族焼香</strong>: {shinzoku if shinzoku else '記載なし'}<br>")
        response_parts.append(f"・<strong>読経の長さ</strong>: {dokyo if dokyo else '記載なし'}<br>")
        response_parts.append(f"・<strong>備考</strong>: {notes if notes else '記載なし'}")
        response_parts.append("</div>")
        
        return "".join(response_parts)
    
    # ★★★ その他の質問はGemini AIで生成 ★★★
    
    # 寺院情報を整形
    temple_data = []
    for field in field_config:
        key = field['key']
        label = field['label']
        value = temple_info.get(key, '')
        
        if value:
            temple_data.append(f"{label}: {value}")
    
    temple_context = "\n".join(temple_data)
    
    # プロンプト作成
    prompt = f"""以下の寺院情報をもとに、質問に答えてください。

【寺院情報】
{temple_context}

【質問】
{question}

【回答の指示】
- 質問に対して簡潔に答えてください
- 寺院名を明記してください
- 住所にはGoogleマップリンクと📋コピーボタンを付けてください
  形式: __📍Googleマップを開く__ 📋 コピー
- 情報がない場合は「記載なし」と答えてください
"""
    
    # Gemini APIで回答生成
    try:
        if not gemini_client:
            return "⚠️ Gemini APIが設定されていません。"
        
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        
        response_text = response.text
        
        # ★修正: Geminiの出力をサニタイズ（XSS対策）
        response_text = _sanitize_text(response_text)
        # 住所のリンクを実際に生成
        address = temple_info.get('address', '')
        if address and '📍' in response_text:
            map_url = f"https://www.google.com/maps/search/?api=1&query={address}"
            address_escaped = address.replace("'", "\\'")
            # Markdownリンクをdivタグに変換
            response_text = response_text.replace(
                "📍Googleマップを開く",
                f'<div style="display: inline-block; margin: 5px 0;"><a href="{map_url}" target="_blank" style="text-decoration: none; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 8px 16px; border-radius: 8px; font-weight: bold; display: inline-block;">📍 Googleマップを開く</a> <button class="copy-btn" onclick="copyToClipboard(\'{address_escaped}\')">📋</button></div>'
            )
        
        return response_text
        
    except Exception as e:
        print(f"AI応答生成エラー: {e}")
        return f"申し訳ございません。回答の生成中にエラーが発生しました: {str(e)}"


def generate_static_summary(temple_info, field_config):
    """
    寺院情報のサマリーHTMLを生成（アコーディオン対応）

    ★修正(重要度:中): Pythonでベタ書きしていたHTMLを
    Jinja2テンプレート（templates/components/temple_summary.html）に分離。
    - HTML保守性の向上
    - Jinja2の自動エスケープによるXSS防止
    - デザイン変更がPythonコードを触らずに行える

    Args:
        temple_info (dict): 寺院データ
        field_config (list): フィールド設定のリスト

    Returns:
        str: レンダリング済みHTML文字列
    """
    from flask import render_template
    import urllib.parse

    def get(key):
        return temple_info.get(key) or ''

    def clean_html_selectively(text):
        """
        HTMLを選択的にクリーンアップ
        - 装飾タグ（太字、色など）は残す
        - インラインスタイルの背景色は削除
        """
        if not text:
            return ''
        text = re.sub(r'background-color\s*:\s*[^;]+;?', '', text)
        text = re.sub(r'background\s*:\s*[^;]+;?', '', text)
        text = re.sub(r'<p([^>]*)>', r'<div\1>', text)
        text = re.sub(r'</p>', '</div>', text)
        text = re.sub(r'\s+style\s*=\s*["\'][\s;]*["\']', '', text)
        text = re.sub(r'(<br[^>]*>\s*){2,}', '<br>', text)
        return text.strip()

    # ============================================
    # カテゴリ定義
    # ============================================
    category_definitions = {
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

    # ============================================
    # テンプレートに渡すデータを構築
    # ============================================
    categories = []

    for cat_key, cat_data in category_definitions.items():
        fields_to_show = []

        for field in field_config:
            if field['key'] not in cat_data['fields']:
                continue

            raw_value = temple_info.get(field['key'], '') or ''
            clean_value = clean_html_selectively(raw_value)

            is_address = (field['key'] == 'address')
            field_entry = {
                'key':       field['key'],
                'label':     field['label'],
                'value':     clean_value,
                'is_address': is_address,
            }

            if is_address and clean_value:
                # 住所フィールド用: プレーンテキストとGoogleマップURLを追加
                address_plain = re.sub(r'<[^>]+>', '', clean_value)
                field_entry['address_plain_js'] = address_plain.replace("'", "\\'")  # ★JS用エスケープをPython側で処理
                field_entry['map_url'] = (
                    'https://www.google.com/maps/search/?api=1&query='
                    + urllib.parse.quote(address_plain)
                )

            fields_to_show.append(field_entry)

        if fields_to_show:
            categories.append({
                'key':          cat_key,
                'title':        cat_data['title'],
                'default_open': cat_data['default_open'],
                'fields':       fields_to_show,
            })

    # ============================================
    # Jinja2テンプレートでレンダリング
    # ============================================
    return render_template(
        'components/temple_summary.html',
        temple_name=get('name'),
        temple_name_js=get('name').replace("'", "\\'"),  # ★JS用エスケープをPython側で処理
        categories=categories,
        timestamp=int(time.time() * 1000),
    )
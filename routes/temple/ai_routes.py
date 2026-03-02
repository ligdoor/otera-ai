"""
AI質問応答ルート

寺院に関する質問に対してAIで回答を生成します。
自然言語から寺院名を抽出し、適切な回答を返します。
"""

import logging
from flask import Blueprint, jsonify, request
import re
from .common import get_otera_database, get_field_config
from .search_routes import find_best_match
from config import Config

# ============================================
# Blueprintの定義
# ============================================

temple_ai_bp = Blueprint('temple_ai', __name__)

logger = logging.getLogger(__name__)


# ============================================
# 寺院名抽出
# ============================================

def extract_temple_name_from_question(question: str) -> str:
    """
    質問文から寺院名を抽出
    
    自然言語の質問文から寺院名を抽出します。
    完全一致検索と曖昧検索を組み合わせて、最適な寺院を特定します。
    
    抽出ロジック:
        1. 質問文中に完全一致する寺院名があればそれを返す
        2. 正規表現で「〜の」パターンから候補を抽出
        3. 抽出した候補でスコアベース検索を実行
        4. 最もスコアが高い寺院を返す
    
    Args:
        question: 質問文
            例: "東大寺の大仏について教えてください"
    
    Returns:
        str: 寺院名（見つからない場合はNone）
    
    Example:
        temple = extract_temple_name_from_question("清水寺の歴史を教えて")
        # "清水寺"
        
        temple = extract_temple_name_from_question("東大の大仏はいつ作られた？")
        # "東大寺" (曖昧検索で特定)
    """
    otera_database = get_otera_database()
    
    # ============================================
    # ステップ1: 完全一致検索
    # ============================================
    
    # 質問文中に寺院名が含まれているか確認
    for name in otera_database.keys():
        if name in question:
            logger.info(f"✅ 完全一致で寺院名を抽出: {name}")
            return name
    
    # ============================================
    # ステップ2: 曖昧検索
    # ============================================
    
    logger.debug("完全一致なし、質問文から候補を抽出します")
    
    # 「〜の」パターンで全候補を抽出し、寺院名リストと照合
    # JSのsendChatRequestと同じく「最後の候補を優先」
    all_matches = re.findall(r'([^のは？\s]+)の', question)
    
    if all_matches:
        otera_keys = list(otera_database.keys())
        # 寺院名リストに含まれる候補だけに絞り込む（「搬送」などを除外）
        valid_candidates = [c for c in all_matches
                            if any(k for k in otera_keys if c in k or k in c)]
        # 絞り込み後に候補があれば最後を優先、なければ全候補の最後を使用
        candidate = valid_candidates[-1] if valid_candidates else all_matches[-1]
        logger.debug(f"抽出された候補（最後優先）: {candidate}")
        
        # find_best_match関数で最適な寺院を検索
        temple_name, score = find_best_match(candidate, min_score=20)
        
        if temple_name:
            logger.info(f"✅ 曖昧検索で寺院名を特定: {temple_name} (スコア: {score})")
            return temple_name
    
    # 見つからない
    logger.error("⚠️ 質問文から寺院名を抽出できませんでした")
    return None


# ============================================
# AI質問応答API
# ============================================

@temple_ai_bp.route("/ask", methods=["POST"])
def ask():
    """
    AI質問応答エンドポイント
    
    寺院に関する質問を受け取り、AIで回答を生成して返します。
    質問文から寺院名を自動的に抽出し、その寺院の情報を基に回答します。
    
    Request Body:
        {
            "question": "質問文",
            "mode": "qa" | "summary"  (オプション)
        }
    
    Mode:
        - "qa": 質問応答モード（デフォルト）
                質問に対して詳細な回答を生成
        - "summary": サマリーモード
                寺院の概要を簡潔に要約
    
    Returns:
        JSON: AI生成の回答
            answer (str): 生成された回答文
    
    Route:
        POST /ask
    
    Example Request:
        POST /ask
        {
            "question": "東大寺の大仏はいつ作られましたか？",
            "mode": "qa"
        }
    
    Example Response:
        {
            "answer": "東大寺の大仏は、奈良時代の天平17年（745年）..."
        }
    
    Error Response:
        {
            "answer": "⚠️ 寺院名が見つかりませんでした。正確な寺院名を入力してください。"
        }
    """
    # AIサービスをインポート
    from services.ai import generate_answer_with_ai, generate_static_summary
    
    # リクエストデータを取得
    question = request.json.get("question", "")
    mode = request.json.get("mode", "qa")  # デフォルトはQAモード
    
    logger.debug("========== AI質問応答 開始 ==========")
    logger.debug(f"質問: {question}")
    logger.debug(f"モード: {mode}")
    
    # ============================================
    # 寺院名を抽出
    # ============================================
    
    temple_name = extract_temple_name_from_question(question)
    
    # 寺院名が見つからない場合はエラーを返す
    if not temple_name:
        logger.error("❌ 寺院名を特定できませんでした")
        return jsonify({
            "answer": "⚠️ 寺院名が見つかりませんでした。正確な寺院名を入力してください。"
        })
    
    logger.debug(f"特定された寺院: {temple_name}")
    
    # ============================================
    # 寺院情報を取得
    # ============================================
    
    otera_database = get_otera_database()
    temple_info = otera_database.get(temple_name)
    
    # 寺院情報が存在しない場合（理論上は起こらないはず）
    if not temple_info:
        logger.error(f"❌ 寺院情報が見つかりません: {temple_name}")
        return jsonify({
            "answer": f"❌ {temple_name} の情報が見つかりませんでした。"
        })
    
    # ============================================
    # アクセスログを記録
    # ============================================
    
    # アクセスログを記録（Supabase使用時のみ）
    if Config.USE_SUPABASE:
        from services.database import add_access_log
        add_access_log(temple_name, question)
    
    # ============================================
    # AI回答を生成
    # ============================================
    
    field_config = get_field_config()
    
    # モードに応じて回答を生成
    if mode == "summary":
        # サマリーモード: 寺院の概要を要約
        logger.debug("サマリーモードで回答を生成します")
        answer = generate_static_summary(temple_info, field_config)
    else:
        # QAモード: 質問に対して詳細に回答
        logger.debug("QAモードで回答を生成します")
        answer = generate_answer_with_ai(temple_info, question, field_config)
    
    logger.info("✅ 回答生成完了")
    logger.debug("========== AI質問応答 終了 ==========")
    
    return jsonify({"answer": answer})


# ============================================
# バッチ質問応答（将来の拡張用）
# ============================================

def batch_ask(questions: list) -> list:
    """
    複数の質問に一括で回答
    
    複数の質問を受け取り、それぞれに対する回答を生成します。
    将来的な機能拡張用の関数です。
    
    Args:
        questions: 質問のリスト
            例: ["東大寺の大仏について", "清水寺の歴史は？"]
    
    Returns:
        list: 回答のリスト
    
    Note:
        現在は実装されていません。将来的に実装予定です。
    """
    # TODO: 実装予定
    pass

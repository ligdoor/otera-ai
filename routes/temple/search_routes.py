"""
寺院検索ルート

寺院の検索機能を提供します。
完全一致検索、曖昧検索、スコアベースのサジェスト機能を含みます。
"""

import logging
from flask import Blueprint, jsonify, request
from .common import get_otera_database

# ============================================
# Blueprintの定義
# ============================================


logger = logging.getLogger(__name__)

temple_search_bp = Blueprint('temple_search', __name__)


# ============================================
# 検索スコア計算
# ============================================

def calculate_search_score(query: str, temple_name: str) -> int:
    """
    検索スコアを計算
    
    クエリと寺院名の類似度をスコア化します。
    スコアが高いほど、検索クエリに近い寺院と判定されます。
    
    スコアリングルール:
        100点: 完全一致
        80点: 前方一致（「東大」で「東大寺」を検索）
        60点: 部分一致（「大寺」で「東大寺」を検索）
        50点: 最後の1文字を除いて前方一致
        40点: 最後の1文字を除いて部分一致
        30点: 最初の2文字が一致
        20点: 最初の1文字が一致
        0点: 一致なし
    
    Args:
        query: 検索クエリ
        temple_name: 寺院名
    
    Returns:
        int: スコア（0-100）
    
    Example:
        score = calculate_search_score("東大", "東大寺")
        # 80 (前方一致)
        
        score = calculate_search_score("大寺", "東大寺")
        # 60 (部分一致)
    """
    score = 0
    
    # 1. 完全一致（スコア100）
    if query == temple_name:
        score = 100
    
    # 2. 前方一致（スコア80）
    elif temple_name.startswith(query):
        score = 80
    
    # 3. 含まれる（スコア60）
    elif query in temple_name:
        score = 60
    
    # 4. 最後の1文字を除いて前方一致（スコア50）
    elif len(query) >= 2 and temple_name.startswith(query[:-1]):
        score = 50
    
    # 5. 最後の1文字を除いて含まれる（スコア40）
    elif len(query) >= 2 and query[:-1] in temple_name:
        score = 40
    
    # 6. 最初の2文字が一致（スコア30）
    elif len(query) >= 2 and len(temple_name) >= 2 and query[:2] == temple_name[:2]:
        score = 30
    
    # 7. 最初の1文字が一致（スコア20）
    elif len(query) >= 1 and len(temple_name) >= 1 and query[0] == temple_name[0]:
        score = 20
    
    return score


# ============================================
# 検索API
# ============================================

@temple_search_bp.route('/search_temple_by_name', methods=['POST'])
def search_temple_by_name():
    """
    寺院名で検索（曖昧検索対応）
    
    入力された寺院名で検索を行います。
    完全一致する寺院があればそれを返し、なければ
    類似する寺院名を最大5件サジェストします。
    
    Request Body:
        {
            "name": "検索する寺院名"
        }
    
    Returns:
        JSON: 検索結果
            exact_match (dict|null): 完全一致した寺院データ
            suggestions (list): 類似寺院のリスト（最大5件）
    
    Route:
        POST /search_temple_by_name
    
    Example Request:
        POST /search_temple_by_name
        {
            "name": "東大"
        }
    
    Example Response (完全一致):
        {
            "exact_match": {
                "name": "東大寺",
                "address": "奈良県...",
                ...
            },
            "suggestions": []
        }
    
    Example Response (曖昧検索):
        {
            "exact_match": null,
            "suggestions": [
                {"name": "東大寺", ...},
                {"name": "東福寺", ...}
            ]
        }
    """
    # リクエストボディから検索クエリを取得
    data = request.json
    query = data.get('name', '').strip()
    
    logger.debug("========== /search_temple_by_name 検索開始 ==========")
    logger.debug(f"検索クエリ: {query}")
    
    # 空のクエリの場合は空の結果を返す
    if not query:
        logger.debug("クエリが空です")
        return jsonify({'exact_match': None, 'suggestions': []})
    
    # data_managerから寺院データを取得
    from services.data_manager import data_manager
    
    # ============================================
    # 完全一致検索
    # ============================================
    
    exact_match = data_manager.get_temple_by_name(query)
    logger.debug(f"完全一致検索結果: {exact_match is not None}")
    
    if exact_match:
        logger.debug(f"完全一致: {exact_match.get('name')}")
        return jsonify({
            'exact_match': exact_match,
            'suggestions': []
        })
    
    # ============================================
    # 曖昧検索
    # ============================================
    
    logger.debug("完全一致なし、曖昧検索を開始")
    
    # 全寺院データを取得
    all_temples = data_manager.get_all_temples()
    
    # 辞書形式の場合はリストに変換
    if isinstance(all_temples, dict):
        temples_list = list(all_temples.values())
    else:
        temples_list = all_temples
    
    logger.debug(f"全寺院数: {len(temples_list)}")
    
    # スコアベースで候補を抽出
    scored_suggestions = []
    
    for temple in temples_list:
        # 辞書型でない場合はスキップ
        if not isinstance(temple, dict):
            continue
        
        temple_name = temple.get('name', '')
        if not temple_name:
            continue
        
        # スコアを計算
        score = calculate_search_score(query, temple_name)
        
        # スコア20以上なら候補に追加
        if score >= 20:
            scored_suggestions.append({
                'temple': temple,
                'score': score
            })
            logger.debug(f"  候補追加: {temple_name} (スコア: {score})")
    
    # スコア順にソート（降順）
    scored_suggestions.sort(key=lambda x: x['score'], reverse=True)
    
    # 上位5件を返す
    suggestions = [item['temple'] for item in scored_suggestions[:5]]
    
    logger.debug(f"見つかった候補数: {len(suggestions)}")
    for i, s in enumerate(suggestions, 1):
        score = scored_suggestions[i-1]['score'] if i <= len(scored_suggestions) else 0
        logger.debug(f"  候補{i}: {s.get('name', '')} (スコア: {score})")
    
    logger.debug("========== 検索終了 ==========")
    
    return jsonify({
        'exact_match': None,
        'suggestions': suggestions
    })


# ============================================
# 検索ヘルパー関数（他のモジュールから使用可能）
# ============================================

def find_best_match(query: str, min_score: int = 20):
    """
    最適な寺院を検索
    
    指定されたクエリに最も近い寺院を1件返します。
    AI質問応答などで寺院名を自動抽出する際に使用します。
    
    Args:
        query: 検索クエリ
        min_score: 最低スコア（デフォルト: 20）
    
    Returns:
        tuple: (寺院名, スコア) または (None, 0)
    
    Example:
        temple_name, score = find_best_match("東大")
        if temple_name:
            logger.debug(f"見つかった寺院: {temple_name} (スコア: {score})")
    """
    from services.data_manager import data_manager
    
    # 全寺院データを取得
    all_temples = data_manager.get_all_temples()
    
    if isinstance(all_temples, dict):
        temples_list = list(all_temples.values())
    else:
        temples_list = all_temples
    
    # 最高スコアを記録
    best_match = None
    best_score = 0
    
    for temple in temples_list:
        if not isinstance(temple, dict):
            continue
        
        temple_name = temple.get('name', '')
        if not temple_name:
            continue
        
        # スコアを計算
        score = calculate_search_score(query, temple_name)
        
        # より高いスコアが見つかったら更新
        if score > best_score:
            best_score = score
            best_match = temple_name
    
    # 最低スコア以上の場合のみ返す
    if best_score >= min_score:
        return best_match, best_score
    
    return None, 0

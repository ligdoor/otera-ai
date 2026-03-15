"""
寺院検索ルート

寺院の検索機能を提供します。
完全一致検索、曖昧検索、スコアベースのサジェスト機能を含みます。
ひらがな検索はSupabaseの furigana カラムを使用します。
"""

import logging
from flask import Blueprint, jsonify, request
from .common import get_otera_database

logger = logging.getLogger(__name__)

temple_search_bp = Blueprint('temple_search', __name__)


# ============================================
# ひらがな検索ユーティリティ
# ============================================

def _is_hiragana(text: str) -> bool:
    """文字列がひらがな主体かどうか判定する（50%以上がひらがなならTrue）"""
    hira_chars = sum(1 for c in text if '\u3041' <= c <= '\u3096')
    return len(text) > 0 and hira_chars / len(text) >= 0.5


def _normalize_dakuten(s: str) -> str:
    """
    濁点・半濁点を除去して比較用に正規化する。
    「だいしょう」と「たいしょう」を同じとみなすために使用。
    """
    table = str.maketrans(
        'がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ',
        'かきくけこさしすせそたちつてとはひふへほはひふへほ'
    )
    return s.translate(table)


def _match_furigana(query: str, furigana: str) -> int:
    """
    ひらがなクエリとふりがなを比較してスコアを返す。
    濁点を正規化した上で完全一致・前方一致・部分一致を判定。

    Returns:
        int: スコア（0・40・60・80・100）
    """
    if not furigana:
        return 0

    q = query.strip()
    f = furigana.strip()
    q_norm = _normalize_dakuten(q)
    f_norm = _normalize_dakuten(f)

    if q == f or q_norm == f_norm:
        return 100
    elif f.startswith(q) or f_norm.startswith(q_norm):
        return 80
    elif q in f or q_norm in f_norm:
        return 60
    elif len(q) >= 2 and (f.startswith(q[:-1]) or f_norm.startswith(q_norm[:-1])):
        return 50
    elif len(q) >= 2 and (q[:-1] in f or q_norm[:-1] in f_norm):
        return 40
    return 0


# ============================================
# 検索スコア計算
# ============================================

def calculate_search_score(query: str, temple_name: str, furigana: str = '') -> int:
    """
    検索スコアを計算

    漢字クエリは寺院名と直接比較。
    ひらがなクエリはSupabaseの furigana カラムと照合。

    スコアリングルール:
        100点: 完全一致
        80点: 前方一致
        60点: 部分一致
        50点: 最後の1文字を除いて前方一致
        40点: 最後の1文字を除いて部分一致
        30点: 最初の2文字が一致
        20点: 最初の1文字が一致

    Args:
        query: 検索クエリ（漢字・ひらがなどちらでも可）
        temple_name: 寺院名（漢字）
        furigana: ふりがな（Supabaseの furigana カラム値）

    Returns:
        int: スコア（0-100）
    """
    # ひらがな入力の場合はふりがなカラムと照合
    if _is_hiragana(query):
        return _match_furigana(query, furigana)

    # 漢字・混合入力は従来通り寺院名と直接比較
    score = 0

    if query == temple_name:
        score = 100
    elif temple_name.startswith(query):
        score = 80
    elif query in temple_name:
        score = 60
    elif len(query) >= 2 and temple_name.startswith(query[:-1]):
        score = 50
    elif len(query) >= 2 and query[:-1] in temple_name:
        score = 40
    elif len(query) >= 2 and len(temple_name) >= 2 and query[:2] == temple_name[:2]:
        score = 30
    elif len(query) >= 1 and len(temple_name) >= 1 and query[0] == temple_name[0]:
        score = 20

    return score


# ============================================
# 検索API
# ============================================

@temple_search_bp.route('/search_temple_by_name', methods=['POST'])
def search_temple_by_name():
    """
    寺院名で検索（曖昧検索・ひらがな検索対応）

    漢字・ひらがなどちらでも検索可能。
    ひらがな検索はSupabaseの furigana カラムを使用。

    Request Body:
        {
            "name": "検索する寺院名（漢字・ひらがなどちらでも可）"
        }

    Returns:
        JSON: {
            "exact_match": dict|null,
            "suggestions": list（最大5件）
        }
    """
    data = request.json
    query = data.get('name', '').strip()

    logger.debug(f"検索クエリ: {query}")

    if not query:
        return jsonify({'exact_match': None, 'suggestions': []})

    from services.data_manager import data_manager

    # 完全一致検索（漢字の場合のみ）
    if not _is_hiragana(query):
        exact_match = data_manager.get_temple_by_name(query)
        if exact_match:
            logger.debug(f"完全一致: {exact_match.get('name')}")
            return jsonify({'exact_match': exact_match, 'suggestions': []})

    # 曖昧検索（漢字・ひらがな両対応）
    all_temples = data_manager.get_all_temples()
    temples_list = list(all_temples.values()) if isinstance(all_temples, dict) else all_temples

    scored = []
    for temple in temples_list:
        if not isinstance(temple, dict):
            continue
        temple_name = temple.get('name', '')
        if not temple_name:
            continue

        furigana = temple.get('furigana', '') or ''
        score = calculate_search_score(query, temple_name, furigana)

        if score >= 20:
            scored.append({'temple': temple, 'score': score})

    scored.sort(key=lambda x: x['score'], reverse=True)
    suggestions = [item['temple'] for item in scored[:5]]

    # ひらがな完全一致（score=100）が1件ならexact_matchとして返す
    if suggestions and scored and scored[0]['score'] == 100:
        return jsonify({'exact_match': suggestions[0], 'suggestions': []})

    logger.debug(f"候補数: {len(suggestions)}")
    return jsonify({'exact_match': None, 'suggestions': suggestions})


# ============================================
# 検索ヘルパー関数（他のモジュールから使用可能）
# ============================================

def find_best_match(query: str, min_score: int = 20):
    """
    最適な寺院を1件返す（漢字・ひらがな両対応）

    AI質問応答で寺院名を自動抽出する際に使用。

    Args:
        query: 検索クエリ
        min_score: 最低スコア（デフォルト: 20）

    Returns:
        tuple: (寺院名, スコア) または (None, 0)
    """
    from services.data_manager import data_manager

    all_temples = data_manager.get_all_temples()
    temples_list = list(all_temples.values()) if isinstance(all_temples, dict) else all_temples

    best_match = None
    best_score = 0

    for temple in temples_list:
        if not isinstance(temple, dict):
            continue
        temple_name = temple.get('name', '')
        if not temple_name:
            continue

        furigana = temple.get('furigana', '') or ''
        score = calculate_search_score(query, temple_name, furigana)

        if score > best_score:
            best_score = score
            best_match = temple_name

    if best_score >= min_score:
        return best_match, best_score

    return None, 0

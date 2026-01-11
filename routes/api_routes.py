from flask import Blueprint, render_template, jsonify, request
from services.spreadsheet import get_spreadsheet_client
from services.ai import generate_static_summary, generate_answer_with_ai
from utils.helpers import get_jst_timestamp
from config import Config
from flask_extensions import limiter

api_bp = Blueprint('api', __name__)

# グローバル参照（temple_routesから取得）
def get_temple_data():
    from routes.temple_routes import otera_database, field_config
    return otera_database, field_config

@api_bp.route("/")
def index():
    """フロント画面"""
    return render_template("index.html")

@api_bp.route("/get_temple_names", methods=["GET"])
def get_temple_names():
    """寺院名一覧を取得"""
    otera_database, _ = get_temple_data()
    return jsonify({"names": sorted(list(otera_database.keys()))})

@api_bp.route("/get_sects", methods=["GET"])
def get_sects():
    """宗派一覧を取得"""
    otera_database, _ = get_temple_data()
    sects = set()
    for t in otera_database.values():
        if 'sect' in t and t['sect']:
            sects.add(t['sect'])
    return jsonify({"sects": sorted(list(sects))})

@api_bp.route("/search_by_sect", methods=["POST"])
def search_by_sect():
    """宗派別検索"""
    otera_database, _ = get_temple_data()
    target_sect = request.json['sect']
    result_list = []
    for temple in otera_database.values():
        if temple.get('sect') == target_sect:
            result_list.append({
                "name": temple['name'],
                "address": temple.get('address', '住所未登録')
            })
    return jsonify({"results": result_list})

@api_bp.route("/search_temples", methods=["POST"])
def search_temples():
    """フリーワード検索"""
    otera_database, _ = get_temple_data()
    keyword = request.json.get('keyword', '').strip().lower()
    
    if not keyword:
        return jsonify({"results": []})
    
    results = []
    for temple in otera_database.values():
        # 名前、宗派、住所で検索
        searchable = f"{temple.get('name', '')} {temple.get('sect', '')} {temple.get('address', '')}".lower()
        
        if keyword in searchable:
            results.append({
                "name": temple.get('name'),
                "sect": temple.get('sect', ''),
                "address": temple.get('address', '')
            })
    
    return jsonify({"results": results[:20]})  # 最大20件

@api_bp.route("/ask", methods=["POST"])
@limiter.limit("30 per minute")  # AI質問は1分間に30回まで
def ask():
    """AI質問応答"""
    otera_database, field_config = get_temple_data()
    user_question = request.json['question']
    found_temple = None
    
    if user_question in otera_database:
        found_temple = otera_database[user_question]
    else:
        for name in otera_database.keys():
            if name in user_question:
                found_temple = otera_database[name]
                break
    
    if not found_temple:
        return jsonify({"answer": "データが見つかりません。"})
    
    # 閲覧回数をカウント
    try:
        client = get_spreadsheet_client()
        sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('access_log')
        timestamp = get_jst_timestamp()
        sheet.append_row([timestamp, found_temple['name'], user_question])
    except:
        pass  # ログ失敗してもエラーにしない
    
    if user_question == found_temple['name']:
        answer = generate_static_summary(found_temple, field_config)
    else:
        answer = generate_answer_with_ai(found_temple, user_question, field_config)
    
    return jsonify({"answer": answer})
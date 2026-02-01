from flask import Blueprint, jsonify, request
from services.data_manager import data_manager

api_bp = Blueprint('api_routes', __name__)

@api_bp.route("/get_temple_names")
def get_temple_names():
    """寺院名の一覧を取得"""
    otera_database = data_manager.get_all_temples()
    
    # 辞書とリストの両方に対応
    if isinstance(otera_database, dict):
        names = sorted(list(otera_database.keys()))
    else:
        # リストの場合
        names = sorted([temple.get('name', '') for temple in otera_database if temple.get('name')])
    
    return jsonify({"names": names})

@api_bp.route("/get_sects")
def get_sects():
    """宗派一覧を取得"""
    otera_database = data_manager.get_all_temples()
    
    # 辞書とリストの両方に対応
    if isinstance(otera_database, dict):
        temples = otera_database.values()
    else:
        temples = otera_database
    
    sects = sorted(list(set(
        temple.get('sect', '') 
        for temple in temples 
        if temple.get('sect')
    )))
    
    return jsonify({"sects": sects})

@api_bp.route("/search_by_sect", methods=["POST"])
def search_by_sect():
    """宗派で寺院を検索"""
    data = request.json
    sect_name = data.get("sect", "")
    
    otera_database = data_manager.get_all_temples()
    
    # 辞書とリストの両方に対応
    if isinstance(otera_database, dict):
        temples = otera_database.values()
    else:
        temples = otera_database
    
    results = [
        {"name": temple.get("name", ""), "address": temple.get("address", "")}
        for temple in temples
        if temple.get("sect") == sect_name
    ]
    
    return jsonify({"results": sorted(results, key=lambda x: x["name"])})
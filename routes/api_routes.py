from flask import Blueprint, jsonify, request, session
from utils.decorators import login_required
from config import Config
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

# ========================================
# お気に入り機能API
# ========================================

@api_bp.route('/api/favorites', methods=['GET'])
@login_required
def get_favorites():
    """ユーザーのお気に入りリストを取得"""
    user_id = session.get('user_id')
    
    if Config.USE_SUPABASE:
        from services import supabase_db
        favorites = supabase_db.get_user_favorites(user_id)
        return jsonify({'favorites': favorites})
    else:
        # ローカルストレージのみ（フォールバック）
        return jsonify({'favorites': []})

@api_bp.route('/api/favorites/toggle', methods=['POST'])
@login_required
def toggle_favorite():
    """お気に入りの追加/削除を切り替え"""
    data = request.json
    temple_name = data.get('temple_name')
    user_id = session.get('user_id')
    
    if not temple_name:
        return jsonify({'error': '寺院名が指定されていません'}), 400
    
    if Config.USE_SUPABASE:
        from services import supabase_db
        
        # 現在のお気に入りリストを取得
        favorites = supabase_db.get_user_favorites(user_id)
        
        if temple_name in favorites:
            # 削除
            success = supabase_db.remove_favorite(user_id, temple_name)
            action = 'removed'
        else:
            # 追加
            success = supabase_db.add_favorite(user_id, temple_name)
            action = 'added'
        
        if success:
            return jsonify({
                'status': 'success',
                'action': action,
                'temple_name': temple_name
            })
        else:
            return jsonify({'error': 'お気に入り操作に失敗しました'}), 500
    else:
        return jsonify({'error': 'Supabaseが有効になっていません'}), 500
    
# ========================================
# 通知機能API
# ========================================

@api_bp.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    """ユーザーの通知一覧を取得"""
    user_id = session.get('user_id')
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    if Config.USE_SUPABASE:
        from services import supabase_db
        notifications = supabase_db.get_user_notifications(user_id, unread_only)
        unread_count = supabase_db.get_unread_count(user_id)
        
        return jsonify({
            'notifications': notifications,
            'unread_count': unread_count
        })
    else:
        return jsonify({'notifications': [], 'unread_count': 0})

@api_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    """通知を既読にする"""
    if Config.USE_SUPABASE:
        from services import supabase_db
        success = supabase_db.mark_notification_read(notification_id)
        
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': '既読処理に失敗しました'}), 500
    else:
        return jsonify({'error': 'Supabaseが有効になっていません'}), 500

@api_bp.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    """すべての通知を既読にする"""
    user_id = session.get('user_id')
    
    if Config.USE_SUPABASE:
        from services import supabase_db
        success = supabase_db.mark_all_notifications_read(user_id)
        
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': '一括既読処理に失敗しました'}), 500
    else:
        return jsonify({'error': 'Supabaseが有効になっていません'}), 500    
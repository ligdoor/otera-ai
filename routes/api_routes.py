"""
API Routes - 標準化版

RESTful設計に基づいた統一されたAPIエンドポイント
"""

from flask import Blueprint, request, session
from utils.decorators import login_required
from config import Config
from services.data_manager import data_manager
from modules.api_response import APIResponse, ErrorCode

api_bp = Blueprint('api_routes', __name__, url_prefix='/api/v1')


# ========================================
# 寺院API
# ========================================

@api_bp.route("/temples/names", methods=['GET'])
def get_temple_names():
    """
    寺院名一覧取得
    
    Returns:
        200: 成功
        500: サーバーエラー
    """
    try:
        otera_database = data_manager.get_all_temples()
        
        if isinstance(otera_database, dict):
            names = sorted(list(otera_database.keys()))
        else:
            names = sorted([temple.get('name', '') for temple in otera_database if temple.get('name')])
        
        return APIResponse.success(
            data={"names": names},
            message=f"{len(names)}件の寺院名を取得しました"
        )
    except Exception as e:
        return APIResponse.internal_error("寺院名の取得に失敗しました", error=e)


@api_bp.route("/sects", methods=['GET'])
def get_sects():
    """
    宗派一覧取得
    
    Returns:
        200: 成功
        500: サーバーエラー
    """
    try:
        otera_database = data_manager.get_all_temples()
        
        if isinstance(otera_database, dict):
            temples = otera_database.values()
        else:
            temples = otera_database
        
        sects = sorted(list(set(
            temple.get('sect', '') 
            for temple in temples 
            if temple.get('sect')
        )))
        
        return APIResponse.success(
            data={"sects": sects},
            message=f"{len(sects)}件の宗派を取得しました"
        )
    except Exception as e:
        return APIResponse.internal_error("宗派の取得に失敗しました", error=e)


@api_bp.route("/temples/search/sect", methods=["POST"])
def search_by_sect():
    """
    宗派で寺院を検索
    
    Request Body:
        {"sect": "宗派名"}
    
    Returns:
        200: 成功
        400: リクエストエラー
        422: バリデーションエラー
        500: サーバーエラー
    """
    try:
        data = request.json
        
        if not data:
            return APIResponse.error(
                ErrorCode.VALIDATION_ERROR,
                "リクエストボディが空です",
                status_code=400
            )
        
        sect_name = data.get("sect", "")
        if not sect_name:
            return APIResponse.validation_error(
                field="sect",
                message="宗派名を指定してください"
            )
        
        otera_database = data_manager.get_all_temples()
        
        if isinstance(otera_database, dict):
            temples = otera_database.values()
        else:
            temples = otera_database
        
        results = [
            {"name": temple.get("name", ""), "address": temple.get("address", "")}
            for temple in temples
            if temple.get("sect") == sect_name
        ]
        
        return APIResponse.success(
            data={"results": sorted(results, key=lambda x: x["name"])},
            message=f"{len(results)}件の寺院が見つかりました"
        )
    except Exception as e:
        return APIResponse.internal_error("寺院検索に失敗しました", error=e)


# ========================================
# お気に入りAPI
# ========================================

@api_bp.route('/favorites', methods=['GET'])
@login_required
def get_favorites():
    """
    お気に入り一覧取得
    
    Returns:
        200: 成功
        401: 未認証
        500: サーバーエラー
    """
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return APIResponse.unauthorized("ログインが必要です")
        
        if Config.USE_SUPABASE:
            from services import supabase_db
            favorites = supabase_db.get_user_favorites(user_id)
            
            return APIResponse.success(
                data={"favorites": favorites},
                message=f"{len(favorites)}件のお気に入りを取得しました"
            )
        else:
            return APIResponse.success(
                data={"favorites": []},
                message="お気に入り機能はSupabase使用時のみ利用可能です"
            )
    except Exception as e:
        return APIResponse.internal_error("お気に入りの取得に失敗しました", error=e)


@api_bp.route('/favorites/toggle', methods=['POST'])
@login_required
def toggle_favorite():
    """
    お気に入り追加/削除
    
    Request Body:
        {"temple_name": "寺院名"}
    
    Returns:
        200: 成功
        400: リクエストエラー
        401: 未認証
        422: バリデーションエラー
        500: サーバーエラー
    """
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return APIResponse.unauthorized("ログインが必要です")
        
        data = request.json
        if not data:
            return APIResponse.error(
                ErrorCode.VALIDATION_ERROR,
                "リクエストボディが空です",
                status_code=400
            )
        
        temple_name = data.get('temple_name')
        if not temple_name:
            return APIResponse.validation_error(
                field='temple_name',
                message='寺院名を指定してください'
            )
        
        if not Config.USE_SUPABASE:
            return APIResponse.error(
                ErrorCode.SERVICE_UNAVAILABLE,
                'お気に入り機能はSupabase使用時のみ利用可能です',
                status_code=503
            )
        
        from services import supabase_db
        
        favorites = supabase_db.get_user_favorites(user_id)
        
        if temple_name in favorites:
            success = supabase_db.remove_favorite(user_id, temple_name)
            action = 'removed'
            message = 'お気に入りから削除しました'
        else:
            success = supabase_db.add_favorite(user_id, temple_name)
            action = 'added'
            message = 'お気に入りに追加しました'
        
        if success:
            return APIResponse.success(
                data={
                    'action': action,
                    'temple_name': temple_name
                },
                message=message
            )
        else:
            return APIResponse.internal_error('お気に入り操作に失敗しました')
            
    except Exception as e:
        return APIResponse.internal_error("お気に入り操作に失敗しました", error=e)


# ========================================
# 通知API
# ========================================

@api_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    """
    通知一覧取得
    
    Query Parameters:
        unread_only: true/false (default: false)
    
    Returns:
        200: 成功
        401: 未認証
        500: サーバーエラー
    """
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return APIResponse.unauthorized("ログインが必要です")
        
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        if Config.USE_SUPABASE:
            from services import supabase_db
            notifications = supabase_db.get_user_notifications(user_id, unread_only)
            unread_count = supabase_db.get_unread_count(user_id)
            
            return APIResponse.success(
                data={
                    'notifications': notifications,
                    'unread_count': unread_count
                },
                message=f"{len(notifications)}件の通知を取得しました"
            )
        else:
            return APIResponse.success(
                data={'notifications': [], 'unread_count': 0},
                message="通知機能はSupabase使用時のみ利用可能です"
            )
    except Exception as e:
        return APIResponse.internal_error("通知の取得に失敗しました", error=e)


@api_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    """
    通知を既読にする
    
    Path Parameters:
        notification_id: 通知ID
    
    Returns:
        200: 成功
        401: 未認証
        404: 通知が見つからない
        500: サーバーエラー
    """
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return APIResponse.unauthorized("ログインが必要です")
        
        if not Config.USE_SUPABASE:
            return APIResponse.error(
                ErrorCode.SERVICE_UNAVAILABLE,
                '通知機能はSupabase使用時のみ利用可能です',
                status_code=503
            )
        
        from services import supabase_db
        success = supabase_db.mark_notification_read(notification_id)
        
        if success:
            return APIResponse.success(
                message="通知を既読にしました"
            )
        else:
            return APIResponse.not_found('通知', notification_id)
            
    except Exception as e:
        return APIResponse.internal_error("既読処理に失敗しました", error=e)


@api_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    """
    すべての通知を既読にする
    
    Returns:
        200: 成功
        401: 未認証
        500: サーバーエラー
    """
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return APIResponse.unauthorized("ログインが必要です")
        
        if not Config.USE_SUPABASE:
            return APIResponse.error(
                ErrorCode.SERVICE_UNAVAILABLE,
                '通知機能はSupabase使用時のみ利用可能です',
                status_code=503
            )
        
        from services import supabase_db
        success = supabase_db.mark_all_notifications_read(user_id)
        
        if success:
            return APIResponse.success(
                message="すべての通知を既読にしました"
            )
        else:
            return APIResponse.internal_error("一括既読処理に失敗しました")
            
    except Exception as e:
        return APIResponse.internal_error("一括既読処理に失敗しました", error=e)


# ========================================
# ユーザー設定API
# ========================================

@api_bp.route('/user-settings', methods=['GET'])
@login_required
def get_user_settings():
    """
    ユーザー設定取得
    
    Returns:
        200: 成功
        401: 未認証
        404: 設定が見つからない
        500: サーバーエラー
    """
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return APIResponse.unauthorized("ログインが必要です")
        
        if not Config.USE_SUPABASE:
            return APIResponse.error(
                ErrorCode.SERVICE_UNAVAILABLE,
                'ユーザー設定機能はSupabase使用時のみ利用可能です',
                status_code=503
            )
        
        from services import supabase_db
        client = supabase_db.get_supabase_client()
        
        # user_idからusersテーブルのidを取得
        # ※ single()はデータが存在しない場合に例外を投げるためexecute()を使用
        user_result = client.table('users').select('id').eq('user_id', user_id).execute()
        
        if not user_result.data or len(user_result.data) == 0:
            # ユーザーが見つからない場合はデフォルト設定を返す（500エラー防止）
            return APIResponse.success(
                data={
                    'font_size': 'normal',
                    'theme': 'light',
                    'line_height': 'normal'
                },
                message="デフォルト設定を返しました"
            )
        
        db_user_id = user_result.data[0]['id']
        
        # user_settingsから設定を取得
        result = client.table('user_settings').select('*').eq('user_id', db_user_id).execute()
        
        if result.data and len(result.data) > 0:
            settings = result.data[0]
            return APIResponse.success(
                data={
                    'font_size': settings.get('font_size', 'normal'),
                    'theme': settings.get('theme', 'light'),
                    'line_height': settings.get('line_height', 'normal')
                },
                message="設定を取得しました"
            )
        else:
            # データが存在しない場合はデフォルト値
            return APIResponse.success(
                data={
                    'font_size': 'normal',
                    'theme': 'light',
                    'line_height': 'normal'
                },
                message="デフォルト設定を返しました"
            )
            
    except Exception as e:
        return APIResponse.internal_error("設定の取得に失敗しました", error=e)


@api_bp.route('/user-settings', methods=['POST'])
@login_required
def save_user_settings():
    """
    ユーザー設定保存
    
    Request Body:
        {
            "font_size": "small|normal|large",
            "theme": "light|dark",
            "line_height": "narrow|normal|wide"
        }
    
    Returns:
        200: 成功
        400: リクエストエラー
        401: 未認証
        404: ユーザーが見つからない
        422: バリデーションエラー
        500: サーバーエラー
    """
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return APIResponse.unauthorized("ログインが必要です")
        
        data = request.json
        if not data:
            return APIResponse.error(
                ErrorCode.VALIDATION_ERROR,
                "リクエストボディが空です",
                status_code=400
            )
        
        font_size = data.get('font_size', 'normal')
        theme = data.get('theme', 'light')
        line_height = data.get('line_height', 'normal')
        
        # バリデーション
        if font_size not in ['small', 'normal', 'large']:
            return APIResponse.validation_error(
                field='font_size',
                message='フォントサイズは small, normal, large のいずれかを指定してください',
                value=font_size
            )
        
        if theme not in ['light', 'dark']:
            return APIResponse.validation_error(
                field='theme',
                message='テーマは light, dark のいずれかを指定してください',
                value=theme
            )
        
        if line_height not in ['narrow', 'normal', 'wide']:
            return APIResponse.validation_error(
                field='line_height',
                message='行間は narrow, normal, wide のいずれかを指定してください',
                value=line_height
            )
        
        if not Config.USE_SUPABASE:
            return APIResponse.error(
                ErrorCode.SERVICE_UNAVAILABLE,
                'ユーザー設定機能はSupabase使用時のみ利用可能です',
                status_code=503
            )
        
        from services import supabase_db
        client = supabase_db.get_supabase_client()
        
        # user_idからusersテーブルのidを取得
        # ※ single()はデータが存在しない場合に例外を投げるためexecute()を使用
        user_result = client.table('users').select('id').eq('user_id', user_id).execute()
        
        if not user_result.data or len(user_result.data) == 0:
            # ユーザーが見つからない場合はデフォルト設定を返す（500エラー防止）
            return APIResponse.success(
                data={
                    'font_size': 'normal',
                    'theme': 'light',
                    'line_height': 'normal'
                },
                message="デフォルト設定を返しました"
            )
        
        db_user_id = user_result.data[0]['id']
        
        # upsert（存在すれば更新、なければ挿入）
        client.table('user_settings').upsert({
            'user_id': db_user_id,
            'font_size': font_size,
            'theme': theme,
            'line_height': line_height
        }, on_conflict='user_id').execute()
        
        return APIResponse.success(
            data={
                'font_size': font_size,
                'theme': theme,
                'line_height': line_height
            },
            message="設定を保存しました"
        )
        
    except Exception as e:
        return APIResponse.internal_error("設定の保存に失敗しました", error=e)

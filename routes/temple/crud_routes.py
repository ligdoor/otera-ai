"""
寺院CRUD操作ルート

寺院データの作成（Create）、更新（Update）、削除（Delete）を処理します。
管理者および編集者のみがアクセスできます。
"""

from flask import Blueprint, jsonify, request
from utils.decorators import login_required, role_required
from services.temple_crud import (
    update_temple_data,
    add_temple_data,
    delete_temple_data
)
from services.cache import cache_manager
from .common import get_cache, get_otera_database
from config import Config

# ============================================
# Blueprintの定義
# ============================================

temple_crud_bp = Blueprint('temple_crud', __name__)


# ============================================
# ヘルパー関数
# ============================================

def clear_temple_cache():
    """
    寺院データのキャッシュをクリア
    
    データ更新後にキャッシュを無効化します。
    次回アクセス時に最新データが読み込まれます。
    """
    try:
        # Flask-Cachingのキャッシュをクリア
        cache = get_cache()
        cache.clear()
    except:
        # エラーが発生しても処理は続行
        pass
    
    # CacheManagerのキャッシュもクリア
    cache_manager.clear_cache()


def log_operation(action: str, details: str):
    """
    操作ログを記録
    
    CRUD操作の履歴を記録します。
    
    Args:
        action: 操作名（例: "追加", "更新", "削除"）
        details: 操作の詳細
    """
    if Config.USE_SUPABASE:
        # Supabase版
        from services.database import add_log
        add_log(action=action, details=details)
    else:
        # Google Sheets版
        from services.data_source import add_log
        add_log(action, details)


# ============================================
# 更新API
# ============================================

@temple_crud_bp.route("/update_temple", methods=["POST"])
@login_required
@role_required(['admin', 'editor'])
def update_temple():
    """
    寺院情報を更新
    
    既存の寺院データを新しいデータで更新します。
    寺院名の変更も可能です。
    
    Request Body:
        {
            "original_name": "元の寺院名",
            "data": {
                "name": "新しい寺院名",
                "address": "住所",
                ...
            }
        }
    
    Returns:
        JSON: 処理結果
            status (str): "success" | "error"
            message (str): エラーメッセージ（エラー時のみ）
    
    Route:
        POST /update_temple
    
    Authentication:
        @login_required: ログイン必須
        @role_required: admin または editor 権限が必要
    
    Example Request:
        POST /update_temple
        {
            "original_name": "東大寺",
            "data": {
                "name": "東大寺",
                "address": "奈良県奈良市雑司町406-1"
            }
        }
    
    Example Response (成功):
        {
            "status": "success"
        }
    
    Example Response (エラー):
        {
            "status": "error",
            "message": "寺院名は必須です"
        }
    """
    # リクエストデータを取得
    req = request.json
    original_name = req['original_name']
    new_data = req['data']
    
    # 寺院名のバリデーション
    if not new_data.get('name'):
        return jsonify({
            "status": "error",
            "message": "寺院名は必須です"
        }), 400
    
    # グローバルデータベースを取得
    otera_database = get_otera_database()
    
    # CRUD操作を実行
    success, message = update_temple_data(original_name, new_data, otera_database)
    
    if success:
        # キャッシュをクリア
        clear_temple_cache()
        
        # ログを記録
        log_operation(
            action='編集',
            details=f"{original_name} の情報を更新 → {new_data['name']}"
        )
        
        # アプリ内通知を作成（全体通知）
        if Config.USE_SUPABASE:
            try:
                from flask import session
                from services.database import create_notification
                editor = session.get('user_name', '管理者')
                create_notification(
                    title='寺院情報を更新しました',
                    message=f'「{new_data["name"]}」の情報が {editor} によって更新されました。',
                    notification_type='info',
                    related_temple=new_data['name']
                )
            except Exception as e:
                logger.warning(f"通知作成エラー（無視）: {e}")
        
        return jsonify({"status": "success"})
    
    else:
        # エラーログを記録
        log_operation(
            action='編集エラー',
            details=f"エラー: {message}"
        )
        
        return jsonify({
            "status": "error",
            "message": message
        }), 500


# ============================================
# 追加API
# ============================================

@temple_crud_bp.route("/add_temple", methods=["POST"])
@login_required
@role_required(['admin', 'editor'])
def add_temple():
    """
    新規寺院を追加
    
    新しい寺院をデータベースに追加します。
    
    Request Body:
        {
            "data": {
                "name": "寺院名",
                "address": "住所",
                "description": "説明",
                ...
            }
        }
    
    Returns:
        JSON: 処理結果
            status (str): "success" | "error"
            message (str): エラーメッセージ（エラー時のみ）
    
    Route:
        POST /add_temple
    
    Authentication:
        @login_required: ログイン必須
        @role_required: admin または editor 権限が必要
    
    Example Request:
        POST /add_temple
        {
            "data": {
                "name": "新寺",
                "address": "東京都...",
                "description": "新しく追加された寺院"
            }
        }
    
    Example Response (成功):
        {
            "status": "success"
        }
    
    Example Response (エラー):
        {
            "status": "error",
            "message": "すでに同じ名前の寺院が存在します"
        }
    """
    # リクエストデータを取得
    req = request.json
    new_data = req['data']
    name = new_data.get('name')
    
    # グローバルデータベースを取得
    otera_database = get_otera_database()
    
    # CRUD操作を実行
    success, message = add_temple_data(new_data, otera_database)
    
    if success:
        # キャッシュをクリア
        clear_temple_cache()
        
        # ログを記録
        log_operation(
            action='追加',
            details=f"{name} を新規追加"
        )
        
        # アプリ内通知を作成（全体通知）
        if Config.USE_SUPABASE:
            try:
                from flask import session
                from services.database import create_notification
                editor = session.get('user_name', '管理者')
                create_notification(
                    title='新しい寺院が追加されました',
                    message=f'「{name}」が {editor} によって追加されました。',
                    notification_type='success',
                    related_temple=name
                )
            except Exception as e:
                logger.warning(f"通知作成エラー（無視）: {e}")
        
        return jsonify({"status": "success"})
    
    else:
        # エラーログを記録
        log_operation(
            action='追加エラー',
            details=f"エラー: {message}"
        )
        
        return jsonify({
            "status": "error",
            "message": message
        }), 400


# ============================================
# 削除API
# ============================================

@temple_crud_bp.route("/delete_temple", methods=["POST"])
@login_required
@role_required(['admin', 'editor'])
def delete_temple():
    """
    寺院を削除
    
    指定された寺院をデータベースから削除します。
    この操作は取り消せません。
    
    Request Body:
        {
            "name": "削除する寺院名"
        }
    
    Returns:
        JSON: 処理結果
            status (str): "success" | "error"
            message (str): エラーメッセージ（エラー時のみ）
    
    Route:
        POST /delete_temple
    
    Authentication:
        @login_required: ログイン必須
        @role_required: admin または editor 権限が必要
    
    Example Request:
        POST /delete_temple
        {
            "name": "削除対象寺"
        }
    
    Example Response (成功):
        {
            "status": "success"
        }
    
    Example Response (エラー - 寺院が見つからない):
        {
            "status": "error",
            "message": "寺院が見つかりません"
        }
    """
    # 削除対象の寺院名を取得
    name = request.json.get('name')
    
    # グローバルデータベースを取得
    otera_database = get_otera_database()
    
    # CRUD操作を実行
    success, message = delete_temple_data(name, otera_database)
    
    if success:
        # キャッシュをクリア
        clear_temple_cache()
        
        # ログを記録
        log_operation(
            action='削除',
            details=f"{name} を削除"
        )
        
        # アプリ内通知を作成（全体通知）
        if Config.USE_SUPABASE:
            try:
                from flask import session
                from services.database import create_notification
                editor = session.get('user_name', '管理者')
                create_notification(
                    title='寺院情報が削除されました',
                    message=f'「{name}」が {editor} によって削除されました。',
                    notification_type='warning'
                )
            except Exception as e:
                logger.warning(f"通知作成エラー（無視）: {e}")
        
        return jsonify({"status": "success"})
    
    else:
        # エラーログを記録
        log_operation(
            action='削除エラー',
            details=f"エラー: {message}"
        )
        
        # エラーの種類に応じてステータスコードを変更
        status_code = 404 if "見つかりません" in message else 500
        
        return jsonify({
            "status": "error",
            "message": message
        }), status_code


# ============================================
# 一括操作（将来の拡張用）
# ============================================

def batch_update_temples(updates: list) -> dict:
    """
    複数の寺院を一括更新
    
    将来的な機能拡張用の関数です。
    複数の寺院データを一度に更新します。
    
    Args:
        updates: 更新データのリスト
            例: [
                {"original_name": "東大寺", "data": {...}},
                {"original_name": "清水寺", "data": {...}}
            ]
    
    Returns:
        dict: 処理結果
            success_count (int): 成功件数
            error_count (int): エラー件数
            errors (list): エラー詳細
    
    Note:
        現在は実装されていません。将来的に実装予定です。
    """
    # TODO: 実装予定
    pass

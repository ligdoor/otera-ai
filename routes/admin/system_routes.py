"""
システム管理ルート

メンテナンスモード、ログ管理、項目設定などのシステム管理機能を提供します。
管理者のみがアクセスできます。
"""

import logging
from flask import Blueprint, render_template, jsonify, request, session
from utils.decorators import login_required, role_required
from services.database import get_supabase_client, get_recent_logs, add_log
from services.temple_crud import update_fields_data
from config import Config
from maintenance import MaintenanceMode
from datetime import datetime

# ============================================
# Blueprintの定義
# ============================================

admin_system_bp = Blueprint('admin_system', __name__)

logger = logging.getLogger(__name__)


# ============================================
# メンテナンスモード管理
# ============================================

@admin_system_bp.route('/api/maintenance/status', methods=['GET'])
def get_maintenance_status():
    """
    メンテナンスモードの状態を取得
    
    現在のメンテナンスモードの状態を返します。
    
    Returns:
        JSON: メンテナンスモード状態
            enabled (bool): メンテナンスモードが有効な場合True
    
    Route:
        GET /api/maintenance/status
    
    Authentication:
        不要（公開API）
    
    Example Response:
        {
            "enabled": false
        }
    """
    try:
        # MaintenanceModeクラスから状態を取得
        enabled = MaintenanceMode.is_enabled()
        
        return jsonify({'enabled': enabled})
    
    except Exception as e:
        logger.error(f"❌ メンテナンス状態取得エラー: {e}")
        return jsonify({'enabled': False})


@admin_system_bp.route('/api/maintenance/toggle', methods=['POST'])
def toggle_maintenance():
    """
    メンテナンスモードの切り替え
    
    メンテナンスモードのON/OFFを切り替えます。
    管理者のみが実行できます。
    
    Returns:
        JSON: 処理結果
            success (bool): 成功した場合True
            enabled (bool): 新しいメンテナンスモード状態
            message (str): 結果メッセージ
    
    Route:
        POST /api/maintenance/toggle
    
    Authentication:
        ログイン必須
        管理者権限（admin）が必要
    
    Process:
        1. ユーザー権限を確認
        2. メンテナンスモードを切り替え
        3. ログを記録
        4. 結果を返す
    
    Example Response (成功):
        {
            "success": true,
            "enabled": true,
            "message": "メンテナンスモードを有効にしました"
        }
    
    Example Response (エラー):
        {
            "success": false,
            "message": "管理者権限が必要です"
        }
    """
    try:
        # ============================================
        # 権限チェック
        # ============================================
        
        # セッションからユーザーIDを取得
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'ログインが必要です'
            }), 401
        
        # データベースクライアントを取得
        supabase = get_supabase_client()
        
        # ユーザーの権限と名前を確認
        user_result = supabase.table('users')\
            .select('role, name')\
            .eq('user_id', user_id)\
            .single()\
            .execute()
        
        # 管理者権限チェック
        if not user_result.data or user_result.data.get('role') != 'admin':
            return jsonify({
                'success': False,
                'message': '管理者権限が必要です'
            }), 403
        
        # ユーザー名を取得
        user_name = user_result.data.get('name', user_id)
        
        # ============================================
        # メンテナンスモード切り替え
        # ============================================
        
        # MaintenanceModeクラスのtoggleメソッドを使用
        result = MaintenanceMode.toggle(user_id)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'message': result.get('error', '切り替えに失敗しました')
            }), 500
        
        # 新しい状態を取得
        new_enabled = result.get('maintenance_mode', False)
        
        # ============================================
        # ログ記録
        # ============================================
        
        action = f'メンテナンスモード{"有効化" if new_enabled else "無効化"}'
        
        supabase.table('logs').insert({
            'user_id': user_id,
            'user': user_name,
            'action': action,
            'timestamp': datetime.now().isoformat()
        }).execute()
        
        logger.info(f"✅ {action}: {user_name}")
        
        return jsonify({
            'success': True,
            'enabled': new_enabled,
            'message': f'メンテナンスモードを{"有効" if new_enabled else "無効"}にしました'
        })
    
    except Exception as e:
        logger.error(f"❌ メンテナンスモード切り替えエラー: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================
# ログ管理
# ============================================

@admin_system_bp.route("/get_logs")
@login_required
def get_logs():
    """
    ログ一覧を取得
    
    システムログを最新50件取得します。
    管理画面でのログ表示に使用します。
    
    Returns:
        JSON: ログのリスト（タイムスタンプ降順）
    
    Route:
        GET /get_logs
    
    Authentication:
        @login_required: ログイン必須
    
    Example Response:
        [
            {
                "timestamp": "2024-01-15T10:30:00+09:00",
                "user": "山田太郎",
                "user_id": "user001",
                "action": "ログイン",
                "details": "ログイン成功 (管理者)"
            },
            ...
        ]
    """
    # データソースに応じて処理を分岐
    if Config.USE_SUPABASE:
        # Supabase版
        try:
            # 最新50件のログを取得
            logs = get_recent_logs(limit=50)
            
            # タイムスタンプの降順でソート
            logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return jsonify(logs)
        
        except Exception as e:
            logger.error(f"❌ ログ取得エラー: {e}")
            return jsonify([])
    
    else:
        # Google Sheets版
        from services.spreadsheet import get_spreadsheet_client
        
        try:
            # Google Sheetsクライアントを取得
            client = get_spreadsheet_client()
            sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('logs')
            
            # 全レコードを取得
            records = sheet.get_all_records()
            
            # 最新50件のみ
            logs = records[-50:] if len(records) > 50 else records
            
            # タイムスタンプの降順でソート
            logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return jsonify(logs)
        
        except Exception as e:
            logger.error(f"❌ ログ取得エラー: {e}")
            return jsonify([])


# ============================================
# 項目設定管理
# ============================================

@admin_system_bp.route("/admin/fields")
@login_required
def admin_fields():
    """
    項目設定画面を表示
    
    寺院データの項目設定を管理する画面を表示します。
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    
    Route:
        GET /admin/fields
    
    Authentication:
        @login_required: ログイン必須
    
    Template:
        admin_fields.html
    """
    return render_template("admin_fields.html")


@admin_system_bp.route("/get_fields")
def get_fields():
    """
    項目設定を取得
    
    寺院データのフィールド定義を取得します。
    
    Returns:
        JSON: フィールド設定のリスト
    
    Route:
        GET /get_fields
    
    Authentication:
        不要（公開API）
    
    Example Response:
        [
            {
                "key": "name",
                "label": "寺院名",
                "order": 1
            },
            {
                "key": "address",
                "label": "住所",
                "order": 2
            },
            ...
        ]
    """
    # データソースに応じて処理を分岐
    if Config.USE_SUPABASE:
        # Supabase版
        from services.database import get_fields_config
        
        try:
            fields = get_fields_config()
            return jsonify(fields)
        
        except Exception as e:
            logger.error(f"❌ フィールド設定取得エラー: {e}")
            return jsonify([])
    
    else:
        # Google Sheets版
        from services.data_source import load_fields_config
        from services.cache import cache_manager
        
        try:
            field_config = load_fields_config(cache_manager)
            return jsonify(field_config)
        
        except Exception as e:
            logger.error(f"❌ フィールド設定取得エラー: {e}")
            return jsonify([])


@admin_system_bp.route("/update_fields", methods=["POST"])
@login_required
@role_required(['admin'])
def update_fields():
    """
    項目設定を更新
    
    寺院データのフィールド定義を更新します。
    管理者のみが実行できます。
    
    Request Body (JSON):
        {
            "fields": [
                {"key": "name", "label": "寺院名", "order": 1},
                {"key": "address", "label": "住所", "order": 2},
                ...
            ]
        }
    
    Returns:
        JSON: 処理結果
            status (str): "success" | "error"
            message (str): エラーメッセージ（エラー時のみ）
    
    Route:
        POST /update_fields
    
    Authentication:
        @login_required: ログイン必須
        @role_required: 管理者権限（admin）が必要
    
    Example Request:
        POST /update_fields
        {
            "fields": [
                {"key": "name", "label": "寺院名", "order": 1}
            ]
        }
    
    Example Response:
        {
            "status": "success"
        }
    """
    # リクエストボディを取得
    fields = request.json.get('fields', [])
    
    # フィールド設定を更新
    success, message = update_fields_data(fields)
    
    if success:
        # ログを記録
        add_log(
            action='項目設定変更',
            details=f'{len(fields)}個の項目を設定しました'
        )
        
        return jsonify({"status": "success"})
    else:
        return jsonify({
            "status": "error",
            "message": message
        }), 500

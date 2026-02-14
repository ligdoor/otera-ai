"""
寺院ビュールート

フロントエンド画面の表示を担当するルートです。
メイン画面、寺院詳細画面などの表示を処理します。
"""

from flask import Blueprint, render_template, session, jsonify
from utils.decorators import login_required
from .common import get_otera_database, get_field_config, reload_temple_data
from config import Config

# ============================================
# Blueprintの定義
# ============================================

# 画面表示用のBlueprint
temple_view_bp = Blueprint('temple_view', __name__)


# ============================================
# メイン画面
# ============================================

@temple_view_bp.route('/')
@login_required
def index():
    """
    メイン画面を表示
    
    ログイン済みユーザーに対してアプリケーションのメイン画面を表示します。
    セッションからユーザー名を取得してテンプレートに渡します。
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    
    Template Variables:
        user_name: ログイン中のユーザー名
    
    Route:
        GET /
    
    Authentication:
        @login_required デコレータにより認証が必要
    
    Example:
        ブラウザで / にアクセスすると、index.htmlが表示されます。
    """
    # セッションからユーザー名を取得（未設定の場合は「ゲスト」）
    user_name = session.get('user_name', 'ゲスト')
    
    # index.htmlテンプレートをレンダリング
    return render_template('index.html', user_name=user_name)


# ============================================
# データ管理ルート
# ============================================

@temple_view_bp.route("/reload_data", methods=["POST"])
@login_required
def reload_data():
    """
    寺院データを再読み込み
    
    キャッシュをクリアして、最新のデータソース（Google SheetsまたはSupabase）
    からデータを再取得します。管理画面からのデータ更新後に使用します。
    
    Returns:
        JSON: 処理結果
            success (bool): 成功した場合True
            message (str): 結果メッセージ
    
    Route:
        POST /reload_data
    
    Authentication:
        @login_required デコレータにより認証が必要
    
    Example Request:
        POST /reload_data
        
    Example Response:
        {
            "success": true,
            "message": "データを再読み込みしました"
        }
    """
    try:
        # 共通モジュールのreload関数を呼び出し
        success = reload_temple_data()
        
        if success:
            # ログ記録
            if Config.USE_SUPABASE:
                from services.database import add_log
                add_log(
                    action='データ再読み込み',
                    details='寺院データを再読み込みしました'
                )
            else:
                from services.data_source import add_log
                add_log("データ再読み込み", "寺院データを再読み込みしました")
            
            return jsonify({
                "success": True,
                "message": "データを再読み込みしました"
            })
        else:
            return jsonify({
                "success": False,
                "message": "データの再読み込みに失敗しました"
            }), 500
    
    except Exception as e:
        print(f"❌ データ再読み込みエラー: {e}")
        return jsonify({
            "success": False,
            "message": f"エラー: {str(e)}"
        }), 500


# ============================================
# データ取得API
# ============================================

@temple_view_bp.route("/get_all_data")
@login_required
def get_all_data():
    """
    全寺院データを取得
    
    メモリ内の全寺院データをJSON形式で返します。
    フロントエンドでのデータ一覧表示などに使用します。
    
    Returns:
        JSON: 全寺院データ
    
    Route:
        GET /get_all_data
    
    Authentication:
        @login_required デコレータにより認証が必要
    
    Example Response:
        {
            "東大寺": {
                "name": "東大寺",
                "address": "奈良県奈良市...",
                "description": "...",
                ...
            },
            "清水寺": {
                ...
            }
        }
    """
    # グローバル変数から寺院データを取得
    otera_database = get_otera_database()
    
    # JSON形式で返す
    return jsonify(otera_database)


@temple_view_bp.route("/get_fields")
def get_fields():
    """
    フィールド設定を取得
    
    寺院データのフィールド定義（項目名、ラベル、表示順など）を
    JSON形式で返します。フォーム生成やテーブル表示に使用します。
    
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
    # グローバル変数からフィールド設定を取得
    field_config = get_field_config()
    
    # JSON形式で返す
    return jsonify(field_config)

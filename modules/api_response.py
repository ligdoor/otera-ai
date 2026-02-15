"""
API標準化 - レスポンスフォーマッター

統一されたレスポンス形式を提供
"""

from flask import jsonify
from datetime import datetime
from typing import Any, Dict, Optional, List


class APIResponse:
    """
    標準化されたAPIレスポンスクラス
    
    全てのAPIエンドポイントで統一されたレスポンス形式を返す
    """
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "成功",
        status_code: int = 200
    ):
        """
        成功レスポンス
        
        Args:
            data: レスポンスデータ
            message: 成功メッセージ
            status_code: HTTPステータスコード (default: 200)
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
            
        Example:
            return APIResponse.success(
                data={'id': 1, 'name': '清水寺'},
                message='寺院情報を取得しました'
            )
        """
        response = {
            "success": True,
            "data": data,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(response), status_code
    
    @staticmethod
    def error(
        error_code: str,
        message: str,
        details: Optional[Dict] = None,
        status_code: int = 400
    ):
        """
        エラーレスポンス
        
        Args:
            error_code: エラーコード (例: TEMPLE_NOT_FOUND)
            message: エラーメッセージ
            details: エラー詳細情報
            status_code: HTTPステータスコード (default: 400)
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
            
        Example:
            return APIResponse.error(
                'TEMPLE_NOT_FOUND',
                '指定された寺院が見つかりません',
                {'temple_id': 123},
                404
            )
        """
        response = {
            "success": False,
            "error": {
                "code": error_code,
                "message": message
            },
            "timestamp": datetime.now().isoformat()
        }
        
        if details:
            response["error"]["details"] = details
        
        return jsonify(response), status_code
    
    @staticmethod
    def paginated(
        items: List,
        total: int,
        page: int,
        per_page: int,
        message: str = "データを取得しました",
        status_code: int = 200
    ):
        """
        ページネーション付きレスポンス
        
        Args:
            items: データリスト
            total: 総件数
            page: 現在のページ番号
            per_page: 1ページあたりの件数
            message: 成功メッセージ
            status_code: HTTPステータスコード (default: 200)
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
            
        Example:
            return APIResponse.paginated(
                items=[...],
                total=100,
                page=1,
                per_page=20
            )
        """
        response = {
            "success": True,
            "data": {
                "items": items,
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0
                }
            },
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(response), status_code
    
    @staticmethod
    def created(
        data: Any,
        message: str = "作成しました",
        resource_id: Optional[Any] = None
    ):
        """
        作成成功レスポンス (201 Created)
        
        Args:
            data: 作成されたリソースデータ
            message: 成功メッセージ
            resource_id: 作成されたリソースのID
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
            
        Example:
            return APIResponse.created(
                data={'id': 1, 'name': '新規寺院'},
                message='寺院を作成しました',
                resource_id=1
            )
        """
        response = {
            "success": True,
            "data": data,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if resource_id is not None:
            response["resource_id"] = resource_id
        
        return jsonify(response), 201
    
    @staticmethod
    def no_content(message: str = "削除しました"):
        """
        コンテンツなしレスポンス (204 No Content)
        
        Args:
            message: 成功メッセージ（実際には返されない）
            
        Returns:
            tuple: (空レスポンス, ステータスコード)
            
        Example:
            return APIResponse.no_content()
        """
        return '', 204
    
    @staticmethod
    def validation_error(
        field: str,
        message: str,
        value: Optional[Any] = None
    ):
        """
        バリデーションエラーレスポンス (422 Unprocessable Entity)
        
        Args:
            field: エラーが発生したフィールド名
            message: エラーメッセージ
            value: 不正な値
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
            
        Example:
            return APIResponse.validation_error(
                field='page',
                message='ページ番号は1以上を指定してください',
                value=-1
            )
        """
        details = {"field": field}
        if value is not None:
            details["value"] = value
        
        return APIResponse.error(
            'VALIDATION_ERROR',
            message,
            details,
            422
        )
    
    @staticmethod
    def not_found(
        resource: str,
        resource_id: Optional[Any] = None
    ):
        """
        リソース未検出エラーレスポンス (404 Not Found)
        
        Args:
            resource: リソース名
            resource_id: リソースID
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
            
        Example:
            return APIResponse.not_found('寺院', 123)
        """
        details = {"resource": resource}
        if resource_id is not None:
            details["resource_id"] = resource_id
        
        return APIResponse.error(
            'NOT_FOUND',
            f'{resource}が見つかりません',
            details,
            404
        )
    
    @staticmethod
    def unauthorized(message: str = "認証が必要です"):
        """
        未認証エラーレスポンス (401 Unauthorized)
        
        Args:
            message: エラーメッセージ
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
            
        Example:
            return APIResponse.unauthorized('ログインしてください')
        """
        return APIResponse.error(
            'UNAUTHORIZED',
            message,
            status_code=401
        )
    
    @staticmethod
    def forbidden(message: str = "アクセス権限がありません"):
        """
        権限不足エラーレスポンス (403 Forbidden)
        
        Args:
            message: エラーメッセージ
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
            
        Example:
            return APIResponse.forbidden('管理者権限が必要です')
        """
        return APIResponse.error(
            'FORBIDDEN',
            message,
            status_code=403
        )
    
    @staticmethod
    def internal_error(
        message: str = "サーバーエラーが発生しました",
        error: Optional[Exception] = None
    ):
        """
        サーバーエラーレスポンス (500 Internal Server Error)
        
        Args:
            message: エラーメッセージ
            error: 例外オブジェクト
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
            
        Example:
            return APIResponse.internal_error(
                '処理中にエラーが発生しました',
                error=e
            )
        """
        details = None
        if error:
            details = {"error": str(error)}
        
        return APIResponse.error(
            'INTERNAL_ERROR',
            message,
            details,
            500
        )


# ========================================
# エラーコード定数
# ========================================

class ErrorCode:
    """標準エラーコード定数"""
    
    # 認証関連
    UNAUTHORIZED = 'UNAUTHORIZED'
    FORBIDDEN = 'FORBIDDEN'
    INVALID_TOKEN = 'INVALID_TOKEN'
    TOKEN_EXPIRED = 'TOKEN_EXPIRED'
    
    # バリデーション関連
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    REQUIRED_FIELD = 'REQUIRED_FIELD'
    INVALID_FORMAT = 'INVALID_FORMAT'
    OUT_OF_RANGE = 'OUT_OF_RANGE'
    
    # リソース関連
    NOT_FOUND = 'NOT_FOUND'
    ALREADY_EXISTS = 'ALREADY_EXISTS'
    CONFLICT = 'CONFLICT'
    
    # 寺院関連
    TEMPLE_NOT_FOUND = 'TEMPLE_NOT_FOUND'
    TEMPLE_ALREADY_EXISTS = 'TEMPLE_ALREADY_EXISTS'
    
    # ユーザー関連
    USER_NOT_FOUND = 'USER_NOT_FOUND'
    USER_ALREADY_EXISTS = 'USER_ALREADY_EXISTS'
    
    # データベース関連
    DB_CONNECTION_FAILED = 'DB_CONNECTION_FAILED'
    DB_QUERY_FAILED = 'DB_QUERY_FAILED'
    DB_RECORD_NOT_FOUND = 'DB_RECORD_NOT_FOUND'
    
    # システム関連
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE'

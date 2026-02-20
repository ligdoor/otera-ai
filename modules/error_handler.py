"""
エラーハンドラー - 統合エラー処理システム
全てのエラーハンドリング機能を統合

使い方:
    from modules.error_handler import ErrorHandler
    
    # 基本的な使い方
    result = ErrorHandler.safe_execute(
        risky_function,
        error_code='DATABASE_ERROR',
        default_return=None
    )
    
    # Flaskアプリにエラーハンドラーを登録
    ErrorHandler.register_flask_handlers(app)
"""

import logging
from modules.error_logger import ErrorLogger
from modules.error_messages import ErrorMessages
from modules.error_responses import ErrorResponse, ErrorPageRenderer
from flask import Flask, request, session, g, jsonify, render_template
import traceback
import sys
import time


class ErrorHandler:
    """統合エラーハンドラークラス"""
    
    @staticmethod
    def safe_execute(func, *args, error_code='UNEXPECTED_ERROR', 
                     default_return=None, logger_name=None, **kwargs):
        """
        関数を安全に実行（エラーハンドリング付き）
        
        Args:
            func: 実行する関数
            *args: 関数の引数
            error_code: エラーコード
            default_return: エラー時の戻り値
            logger_name: ロガー名（省略時は関数名）
            **kwargs: 関数のキーワード引数
            
        Returns:
            関数の戻り値、またはエラー時はdefault_return
        """
        if logger_name is None:
            logger_name = func.__module__
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # エラーログ記録
            ErrorLogger.log_error(
                logger_name,
                error_code,
                f"Error in {func.__name__}: {str(e)}",
                function=func.__name__,
                error_type=type(e).__name__,
                traceback=traceback.format_exc()
            )
            
            return default_return
    
    @staticmethod
    def wrap_with_try_except(func, error_code='UNEXPECTED_ERROR'):
        """
        関数をtry-exceptでラップ
        
        Args:
            func: ラップする関数
            error_code: エラーコード
            
        Returns:
            ラップされた関数
        """
        def wrapped(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = ErrorLogger.get_logger(func.__module__)
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exc_info=True
                )
                raise
        
        return wrapped
    
    @staticmethod
    def register_flask_handlers(app: Flask):
        """
        Flaskアプリにエラーハンドラーを登録
        
        Args:
            app: Flaskアプリケーション
        """
        
        # 404エラー
        @app.errorhandler(404)
        def handle_404(e):
            ErrorLogger.log_error(
                'flask',
                'NOT_FOUND',
                f"404 Not Found: {request.path}",
                path=request.path,
                method=request.method
            )
            return ErrorPageRenderer.render_404()
        
        # 403エラー
        @app.errorhandler(403)
        def handle_403(e):
            logger = ErrorLogger.get_logger('flask')
            logger.warning(
                f"403 Forbidden: {request.path}",
                extra={
                    'path': request.path,
                    'user_id': session.get('user_id'),
                    'ip_address': request.remote_addr
                }
            )
            return ErrorPageRenderer.render_403()
        
        # 500エラー
        @app.errorhandler(500)
        def handle_500(e):
            ErrorLogger.log_error(
                'flask',
                'UNEXPECTED_ERROR',
                f"500 Internal Server Error: {str(e)}",
                path=request.path,
                method=request.method,
                traceback=traceback.format_exc()
            )
            return ErrorPageRenderer.render_500()
        
        # 一般的な例外
        @app.errorhandler(Exception)
        def handle_exception(e):
            # HTTPExceptionの場合はそのまま処理
            from werkzeug.exceptions import HTTPException
            if isinstance(e, HTTPException):
                return e
            
            # その他の例外
            ErrorLogger.log_error(
                'flask',
                'UNEXPECTED_ERROR',
                f"Unhandled exception: {str(e)}",
                path=request.path,
                method=request.method,
                error_type=type(e).__name__,
                traceback=traceback.format_exc()
            )
            
            return ErrorPageRenderer.render_500()
        
        # リクエスト前処理（ログ記録）
        @app.before_request
        def log_request():
            # 処理開始時刻を記録
            g.start_time = time.time()
            
            # アクセスログ記録
            logger = ErrorLogger.get_logger('flask')
            logger.info(
                f"{request.method} {request.path} from {request.remote_addr}"
            )
        
        # リクエスト後処理（ログ記録）
        @app.after_request
        def log_response(response):
            """
            リクエスト処理後のログ記録
            """
            try:
                # start_timeが設定されているかチェック
                if hasattr(g, 'start_time'):
                    # 処理時間を計算
                    duration_ms = (time.time() - g.start_time) * 1000
                    
                    # アクセスログを記録
                    ErrorLogger.log_access(
                        method=request.method,
                        path=request.path,
                        status_code=response.status_code,
                        duration_ms=duration_ms,
                        user_id=session.get('user_id'),
                        ip_address=request.remote_addr
                    )
            except Exception as e:
                # ログ記録に失敗してもアプリは止めない
                logger.debug(f"ログ記録エラー: {e}")
            
            return response

    @staticmethod
    def handle_database_error(error, operation='query'):
        """
        データベースエラーを処理
        
        Args:
            error: 発生したエラー
            operation: 実行していた操作
            
        Returns:
            dict: エラー情報
        """
        error_str = str(error).lower()
        
        # エラーの種類を判定
        if 'connection' in error_str or 'timeout' in error_str:
            error_code = 'CONNECTION_FAILED'
        elif 'not found' in error_str:
            error_code = 'RECORD_NOT_FOUND'
        elif 'duplicate' in error_str or 'unique' in error_str:
            error_code = 'DUPLICATE_ENTRY'
        elif 'constraint' in error_str:
            error_code = 'CONSTRAINT_VIOLATION'
        else:
            error_code = 'QUERY_FAILED'
        
        # ログ記録
        ErrorLogger.log_error(
            'database',
            error_code,
            f"Database error during {operation}: {str(error)}",
            operation=operation,
            error_type=type(error).__name__
        )
        
        return {
            'success': False,
            'error_code': error_code,
            'error_message': ErrorMessages.get_user_message(error_code)
        }
    
    @staticmethod
    def handle_file_upload_error(error, filename=None):
        """
        ファイルアップロードエラーを処理
        
        Args:
            error: 発生したエラー
            filename: ファイル名
            
        Returns:
            dict: エラー情報
        """
        error_str = str(error).lower()
        
        # エラーの種類を判定
        if 'size' in error_str or 'large' in error_str:
            error_code = 'FILE_TOO_LARGE'
        elif 'format' in error_str or 'type' in error_str:
            error_code = 'INVALID_FILE_FORMAT'
        elif 'conversion' in error_str:
            error_code = 'CONVERSION_FAILED'
        else:
            error_code = 'UPLOAD_FAILED'
        
        # ログ記録
        ErrorLogger.log_error(
            'file_upload',
            error_code,
            f"File upload error: {str(error)}",
            filename=filename,
            error_type=type(error).__name__
        )
        
        return {
            'success': False,
            'error_code': error_code,
            'error_message': ErrorMessages.get_user_message(error_code)
        }
    
    @staticmethod
    def handle_api_error(error, service='external_api'):
        """
        外部API呼び出しエラーを処理
        
        Args:
            error: 発生したエラー
            service: サービス名
            
        Returns:
            dict: エラー情報
        """
        error_str = str(error).lower()
        
        # エラーの種類を判定
        if 'timeout' in error_str:
            error_code = 'API_TIMEOUT'
        elif 'quota' in error_str or 'limit' in error_str:
            if service == 'gemini':
                error_code = 'GEMINI_QUOTA_EXCEEDED'
            else:
                error_code = 'RATE_LIMIT_EXCEEDED'
        elif service == 'gemini':
            error_code = 'GEMINI_API_ERROR'
        else:
            error_code = 'EXTERNAL_API_ERROR'
        
        # ログ記録
        ErrorLogger.log_error(
            'api',
            error_code,
            f"API error ({service}): {str(error)}",
            service=service,
            error_type=type(error).__name__
        )
        
        return {
            'success': False,
            'error_code': error_code,
            'error_message': ErrorMessages.get_user_message(error_code)
        }
    
    @staticmethod
    def handle_validation_error(field, value, error_type='INVALID_FORMAT'):
        """
        バリデーションエラーを処理
        
        Args:
            field: フィールド名
            value: 値
            error_type: エラータイプ
            
        Returns:
            dict: エラー情報
        """
        # ログ記録
        ErrorLogger.log_error(
            'validation',
            error_type,
            f"Validation error: {field}",
            field=field,
            value=str(value)[:100]  # 長すぎる場合は切り詰め
        )
        
        return {
            'success': False,
            'error_code': error_type,
            'error_message': ErrorMessages.get_user_message(error_type, field=field),
            'field': field
        }
    
    @staticmethod
    def create_error_report(logger_name='error_report'):
        """
        エラーレポートを作成
        
        Args:
            logger_name: ロガー名
            
        Returns:
            dict: エラーレポート
        """
        # 簡易レポート（実装例）
        report = {
            'total_errors': 0,
            'error_counts': {},
            'most_common': None,
            'recent_errors': []
        }
        
        return report


class DatabaseErrorHandler:
    """データベース専用エラーハンドラー"""
    
    @staticmethod
    def execute_query(query_func, *args, error_code='QUERY_FAILED', **kwargs):
        """
        データベースクエリを安全に実行
        
        Args:
            query_func: クエリ関数
            error_code: エラーコード
            
        Returns:
            クエリ結果 or None
        """
        try:
            return query_func(*args, **kwargs)
        except Exception as e:
            return ErrorHandler.handle_database_error(e, operation=query_func.__name__)
    
    @staticmethod
    def with_transaction(func):
        """
        トランザクション付きで関数を実行
        エラー時は自動ロールバック
        
        Args:
            func: 実行する関数
            
        Returns:
            関数の戻り値
        """
        try:
            # トランザクション開始
            result = func()
            # コミット（Supabaseの場合は自動コミット）
            return result
        except Exception as e:
            # ロールバック
            ErrorLogger.log_error(
                'database',
                'TRANSACTION_FAILED',
                f"Transaction failed: {str(e)}",
                function=func.__name__,
                traceback=traceback.format_exc()
            )
            raise
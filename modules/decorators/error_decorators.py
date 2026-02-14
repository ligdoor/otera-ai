"""
エラーハンドリング用デコレーター
関数に簡単にエラーハンドリングを追加できるデコレーター

使い方:
    from modules.decorators.error_decorators import handle_errors, log_errors
    
    @handle_errors
    def my_function():
        # エラーが起きても適切に処理される
        pass
    
    @log_errors('my_module')
    def another_function():
        # エラーがログに記録される
        pass
"""

from functools import wraps
from modules.error_logger import ErrorLogger
from modules.error_responses import ErrorResponse
from modules.error_messages import ErrorMessages
import time


def handle_errors(error_code='UNEXPECTED_ERROR', return_value=None):
    """
    エラーハンドリングデコレーター
    関数内で発生した例外をキャッチし、適切に処理する
    
    Args:
        error_code: デフォルトのエラーコード
        return_value: エラー時の戻り値
        
    使い方:
        @handle_errors(error_code='DATABASE_ERROR', return_value=None)
        def get_temple(temple_id):
            # エラーが起きても適切に処理される
            return supabase.table('temples').select('*').eq('id', temple_id).execute()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # ロガー取得
                logger = ErrorLogger.get_logger(func.__module__, 'error')
                
                # エラーログ記録
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exc_info=True
                )
                
                return return_value
        return wrapper
    return decorator


def log_errors(logger_name, error_code='UNEXPECTED_ERROR'):
    """
    エラーログ記録デコレーター
    関数内で発生した例外をログに記録する（エラーは再送出）
    
    Args:
        logger_name: ロガー名
        error_code: エラーコード
        
    使い方:
        @log_errors('database')
        def update_temple(temple_id, data):
            # エラーが起きたらログに記録され、例外は再送出される
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # エラーログ記録
                ErrorLogger.log_error(
                    logger_name,
                    error_code,
                    f"Error in {func.__name__}: {str(e)}",
                    function=func.__name__,
                    args=str(args)[:100],  # 長すぎる場合は切り詰め
                    error_type=type(e).__name__
                )
                
                # 例外を再送出
                raise
        return wrapper
    return decorator


def retry_on_error(max_retries=3, delay=1, backoff=2):
    """
    リトライデコレーター
    エラーが発生した場合、指定回数まで再試行する
    
    Args:
        max_retries: 最大リトライ回数
        delay: 初回の待機時間（秒）
        backoff: 待機時間の増加率
        
    使い方:
        @retry_on_error(max_retries=3, delay=2, backoff=2)
        def upload_to_storage(file):
            # 失敗しても最大3回リトライ
            # 待機時間: 2秒 → 4秒 → 8秒
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # 最後の試行の場合は例外を再送出
                    if attempt == max_retries - 1:
                        logger = ErrorLogger.get_logger(func.__module__, 'error')
                        logger.error(
                            f"Failed after {max_retries} retries: {func.__name__}",
                            exc_info=True
                        )
                        raise
                    
                    # ログ記録
                    logger = ErrorLogger.get_logger(func.__module__, 'error')
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {str(e)}"
                    )
                    
                    # 待機
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # ここには到達しないはずだが、念のため
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def validate_input(**validators):
    """
    入力値検証デコレーター
    関数の引数を自動的に検証する
    
    Args:
        **validators: {引数名: 検証関数} の辞書
        
    使い方:
        def is_valid_temple_id(value):
            return isinstance(value, int) and value > 0
        
        @validate_input(temple_id=is_valid_temple_id)
        def get_temple(temple_id):
            # temple_idが自動的に検証される
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 引数名取得
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # 各引数を検証
            for arg_name, validator in validators.items():
                if arg_name in bound_args.arguments:
                    value = bound_args.arguments[arg_name]
                    
                    # 検証実行
                    if not validator(value):
                        logger = ErrorLogger.get_logger(func.__module__, 'error')
                        logger.warning(
                            f"Validation failed for {arg_name} in {func.__name__}"
                        )
                        
                        raise ValueError(
                            ErrorMessages.get_user_message(
                                'INVALID_FORMAT',
                                field=arg_name
                            )
                        )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def measure_performance(threshold_seconds=1.0):
    """
    パフォーマンス測定デコレーター
    関数の実行時間を測定し、閾値を超えたら警告ログを記録
    
    Args:
        threshold_seconds: 警告を出す閾値（秒）
        
    使い方:
        @measure_performance(threshold_seconds=0.5)
        def slow_function():
            # 0.5秒以上かかったら警告
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_time = time.time() - start_time
                
                # 閾値を超えた場合、警告ログ
                if elapsed_time > threshold_seconds:
                    logger = ErrorLogger.get_logger(func.__module__, 'app')
                    logger.warning(
                        f"Slow function detected: {func.__name__} "
                        f"took {elapsed_time:.2f}s (threshold: {threshold_seconds}s)"
                    )
        return wrapper
    return decorator


def require_permission(required_role):
    """
    権限チェックデコレーター
    特定のロールを持つユーザーのみ関数を実行できる
    
    Args:
        required_role: 必要なロール（admin, editor, viewer）
        
    使い方:
        @require_permission('admin')
        def delete_temple(temple_id):
            # 管理者のみ実行可能
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import session
            
            # セッションからユーザー情報取得
            user_role = session.get('role')
            
            # ロール階層チェック
            role_hierarchy = {'admin': 3, 'editor': 2, 'viewer': 1}
            
            if not user_role or role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 999):
                # 権限不足
                logger = ErrorLogger.get_logger(func.__module__, 'security')
                logger.warning(
                    f"Permission denied: {func.__name__} requires {required_role}, "
                    f"but user has {user_role}"
                )
                
                raise PermissionError(
                    ErrorMessages.get_user_message('PERMISSION_DENIED')
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def cache_result(ttl_seconds=300):
    """
    結果キャッシュデコレーター
    関数の結果をメモリにキャッシュし、同じ引数での呼び出しを高速化
    
    Args:
        ttl_seconds: キャッシュの有効期限（秒）
        
    使い方:
        @cache_result(ttl_seconds=600)
        def get_temple_list():
            # 10分間キャッシュ
            pass
    """
    def decorator(func):
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # キャッシュキー生成
            cache_key = str(args) + str(kwargs)
            
            # キャッシュチェック
            if cache_key in cache:
                cached_data, cached_time = cache[cache_key]
                
                # 有効期限チェック
                if time.time() - cached_time < ttl_seconds:
                    return cached_data
            
            # 関数実行
            result = func(*args, **kwargs)
            
            # キャッシュに保存
            cache[cache_key] = (result, time.time())
            
            return result
        return wrapper
    return decorator

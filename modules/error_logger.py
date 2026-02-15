"""
エラーロガー - 改善版（ログローテーション対応 + アクセスログ修正）

【改善点】
✅ ログローテーション（日次・サイズ別）
✅ レベル別ファイル分離
✅ JSON形式の構造化ログ
✅ パフォーマンス監視
✅ アクセスログ専用ハンドラー（修正済み）
"""

import logging
import logging.handlers
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class ErrorLogger:
    """
    改善版エラーロガー
    
    特徴:
    - ログローテーション（日次 + サイズ制限）
    - レベル別ファイル分離
    - JSON形式の構造化ログ
    - 自動アーカイブ
    - アクセスログ専用ハンドラー
    """
    
    _loggers: Dict[str, logging.Logger] = {}
    _initialized = False
    
    @classmethod
    def setup(
        cls,
        log_level: str = 'INFO',
        log_dir: str = 'logs',
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 30,  # 30世代保持
        json_format: bool = False
    ):
        """
        ログシステムのセットアップ
        
        Args:
            log_level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: ログディレクトリ
            max_bytes: ログファイルの最大サイズ（バイト）
            backup_count: 保持する世代数
            json_format: JSON形式で出力するか
        """
        if cls._initialized:
            return
        
        # ログディレクトリの作成
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # レベル別ディレクトリの作成
        (log_path / 'info').mkdir(exist_ok=True)
        (log_path / 'error').mkdir(exist_ok=True)
        (log_path / 'debug').mkdir(exist_ok=True)
        (log_path / 'access').mkdir(exist_ok=True)
        
        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # 既存のハンドラーをクリア
        root_logger.handlers.clear()
        
        # フォーマッターの作成
        if json_format:
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        # ========================================
        # 1. 統合ログ（全レベル）
        # ========================================
        all_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_path / 'app.log',
            when='midnight',
            interval=1,
            backupCount=backup_count,
            encoding='utf-8'
        )
        all_handler.setLevel(logging.DEBUG)
        all_handler.setFormatter(formatter)
        root_logger.addHandler(all_handler)
        
        # ========================================
        # 2. エラーログ（ERROR以上）
        # ========================================
        error_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / 'error' / 'error.log',
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
        
        # ========================================
        # 3. 情報ログ（INFO）
        # ========================================
        info_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_path / 'info' / 'info.log',
            when='midnight',
            interval=1,
            backupCount=backup_count,
            encoding='utf-8'
        )
        info_handler.setLevel(logging.INFO)
        info_handler.addFilter(lambda record: record.levelno == logging.INFO)
        info_handler.setFormatter(formatter)
        root_logger.addHandler(info_handler)
        
        # ========================================
        # 4. デバッグログ（DEBUG）
        # ========================================
        debug_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / 'debug' / 'debug.log',
            maxBytes=max_bytes,
            backupCount=10,  # デバッグログは少なめ
            encoding='utf-8'
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.addFilter(lambda record: record.levelno == logging.DEBUG)
        debug_handler.setFormatter(formatter)
        root_logger.addHandler(debug_handler)
        
        # ========================================
        # 5. アクセスログ（独立したロガー）★修正★
        # ========================================
        access_logger = logging.getLogger('access')
        access_logger.setLevel(logging.INFO)
        access_logger.handlers.clear()  # 既存のハンドラーをクリア
        
        access_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_path / 'access' / 'access.log',
            when='midnight',
            interval=1,
            backupCount=backup_count,
            encoding='utf-8'
        )
        access_handler.setLevel(logging.INFO)
        access_handler.setFormatter(formatter)
        access_logger.addHandler(access_handler)
        
        # ルートロガーには伝播させない（重複を防ぐ）
        access_logger.propagate = False
        
        # ========================================
        # 6. コンソール出力
        # ========================================
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        cls._initialized = True
        
        # 起動ログ
        startup_logger = cls.get_logger('system')
        startup_logger.info("="*60)
        startup_logger.info("ログシステム初期化完了")
        startup_logger.info(f"ログレベル: {log_level}")
        startup_logger.info(f"ログディレクトリ: {log_dir}")
        startup_logger.info(f"最大ファイルサイズ: {max_bytes / 1024 / 1024:.1f}MB")
        startup_logger.info(f"保持世代数: {backup_count}")
        startup_logger.info(f"JSON形式: {json_format}")
        startup_logger.info(f"✅ アクセスログハンドラー設定完了")
        startup_logger.info("="*60)
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        名前付きロガーを取得
        
        Args:
            name: ロガー名
            
        Returns:
            logging.Logger: ロガーインスタンス
        """
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        return cls._loggers[name]
    
    @classmethod
    def log_error(
        cls,
        logger_name: str,
        error_code: str,
        message: str,
        **kwargs
    ):
        """
        構造化エラーログの記録
        
        Args:
            logger_name: ロガー名
            error_code: エラーコード
            message: エラーメッセージ
            **kwargs: 追加情報
        """
        logger = cls.get_logger(logger_name)
        
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'error_code': error_code,
            'message': message,
            **kwargs
        }
        
        logger.error(json.dumps(error_data, ensure_ascii=False))
    
    @classmethod
    def log_performance(
        cls,
        logger_name: str,
        operation: str,
        duration_ms: float,
        **kwargs
    ):
        """
        パフォーマンスログの記録
        
        Args:
            logger_name: ロガー名
            operation: 処理名
            duration_ms: 処理時間（ミリ秒）
            **kwargs: 追加情報
        """
        logger = cls.get_logger(logger_name)
        
        perf_data = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'duration_ms': duration_ms,
            'is_slow': duration_ms > 1000,  # 1秒以上はスロー
            **kwargs
        }
        
        if perf_data['is_slow']:
            logger.warning(f"⚠️ Slow operation: {json.dumps(perf_data, ensure_ascii=False)}")
        else:
            logger.info(f"Performance: {json.dumps(perf_data, ensure_ascii=False)}")
    
    @classmethod
    def log_access(
        cls,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        アクセスログの記録（★修正版★）
        
        Args:
            method: HTTPメソッド
            path: リクエストパス
            status_code: ステータスコード
            duration_ms: 処理時間（ミリ秒）
            user_id: ユーザーID
            ip_address: IPアドレス
        """
        # 専用のアクセスロガーを取得
        logger = logging.getLogger('access')
        
        access_data = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'path': path,
            'status_code': status_code,
            'duration_ms': duration_ms,
            'user_id': user_id,
            'ip_address': ip_address
        }
        
        logger.info(json.dumps(access_data, ensure_ascii=False))


class JsonFormatter(logging.Formatter):
    """
    JSON形式のログフォーマッター
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        ログレコードをJSON形式に変換
        
        Args:
            record: ログレコード
            
        Returns:
            str: JSON形式のログ
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 例外情報があれば追加
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # カスタム属性があれば追加
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName',
                          'relativeCreated', 'thread', 'threadName', 'exc_info',
                          'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False)


# ========================================
# デコレーター
# ========================================

def log_execution_time(logger_name: str = 'performance'):
    """
    関数の実行時間を記録するデコレーター
    
    Usage:
        @log_execution_time('my_module')
        def slow_function():
            time.sleep(2)
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000
                ErrorLogger.log_performance(
                    logger_name,
                    f'{func.__module__}.{func.__name__}',
                    duration_ms
                )
        
        return wrapper
    return decorator
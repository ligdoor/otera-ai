"""
エラーログ記録機能
構造化されたログを記録し、エラー追跡を容易にする

使い方:
    from modules.error_logger import ErrorLogger
    
    logger = ErrorLogger.get_logger(__name__)
    logger.error("Database error", error_code="DB_ERROR", user_id=123)
"""

import logging
import os
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


class ErrorLogger:
    """エラーログ記録クラス"""
    
    # ログレベルの定義
    LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    # ログディレクトリ
    LOG_DIR = Path('logs')
    
    # ログファイルの設定
    LOG_FILES = {
        'error': 'error.log',       # エラーログ
        'access': 'access.log',     # アクセスログ
        'security': 'security.log', # セキュリティログ
        'api': 'api.log',          # API呼び出しログ
        'app': 'app.log'           # アプリケーション全般
    }
    
    _loggers = {}  # ロガーのキャッシュ
    
    @classmethod
    def setup(cls, log_level='INFO', log_dir=None):
        """
        ロガーの初期設定
        
        Args:
            log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
            log_dir: ログディレクトリのパス
        """
        if log_dir:
            cls.LOG_DIR = Path(log_dir)
        
        # ログディレクトリ作成
        cls.LOG_DIR.mkdir(exist_ok=True, parents=True)
        
        # ログレベル設定
        logging.basicConfig(
            level=cls.LEVELS.get(log_level, logging.INFO),
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    @classmethod
    def get_logger(cls, name, log_type='app'):
        """
        ロガーインスタンスを取得
        
        Args:
            name: ロガー名（通常は__name__を使用）
            log_type: ログタイプ（error, access, security, api, app）
            
        Returns:
            logging.Logger: ロガーインスタンス
        """
        # キャッシュから取得
        cache_key = f"{name}_{log_type}"
        if cache_key in cls._loggers:
            return cls._loggers[cache_key]
        
        # 新規ロガー作成
        logger = logging.getLogger(name)
        
        # ハンドラーが未設定の場合のみ追加
        if not logger.handlers:
            # ファイルハンドラー追加
            cls._add_file_handler(logger, log_type)
            
            # コンソールハンドラー追加
            cls._add_console_handler(logger)
        
        # キャッシュに保存
        cls._loggers[cache_key] = logger
        
        return logger
    
    @classmethod
    def _add_file_handler(cls, logger, log_type):
        """
        ファイルハンドラーを追加
        
        Args:
            logger: ロガーインスタンス
            log_type: ログタイプ
        """
        log_file = cls.LOG_DIR / cls.LOG_FILES.get(log_type, 'app.log')
        
        # ローテーティングファイルハンドラー
        # 最大10MB、5世代保存
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # フォーマッター設定
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    @classmethod
    def _add_console_handler(cls, logger):
        """
        コンソールハンドラーを追加
        
        Args:
            logger: ロガーインスタンス
        """
        handler = logging.StreamHandler()
        
        # フォーマッター設定
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    @classmethod
    def log_error(cls, logger_name, error_code, message, **context):
        """
        エラーログを記録（構造化）
        
        Args:
            logger_name: ロガー名
            error_code: エラーコード
            message: エラーメッセージ
            **context: 追加のコンテキスト情報
        """
        logger = cls.get_logger(logger_name, 'error')
        
        # 構造化ログデータ作成
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'error_code': error_code,
            'message': message,
            **context
        }
        
        # JSON形式でログ出力
        logger.error(json.dumps(log_data, ensure_ascii=False))
    
    @classmethod
    def log_security(cls, logger_name, event_type, message, **context):
        """
        セキュリティログを記録
        
        Args:
            logger_name: ロガー名
            event_type: イベントタイプ（login_failed, permission_denied等）
            message: メッセージ
            **context: 追加情報（user_id, ip_address等）
        """
        logger = cls.get_logger(logger_name, 'security')
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'message': message,
            **context
        }
        
        logger.warning(json.dumps(log_data, ensure_ascii=False))
    
    @classmethod
    def log_api_call(cls, logger_name, endpoint, method, status_code, **context):
        """
        API呼び出しログを記録
        
        Args:
            logger_name: ロガー名
            endpoint: エンドポイント
            method: HTTPメソッド
            status_code: ステータスコード
            **context: 追加情報（duration, user_id等）
        """
        logger = cls.get_logger(logger_name, 'api')
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            **context
        }
        
        # ステータスコードに応じてログレベル変更
        if status_code >= 500:
            logger.error(json.dumps(log_data, ensure_ascii=False))
        elif status_code >= 400:
            logger.warning(json.dumps(log_data, ensure_ascii=False))
        else:
            logger.info(json.dumps(log_data, ensure_ascii=False))
    
    @classmethod
    def log_access(cls, logger_name, user_id, action, resource, **context):
        """
        アクセスログを記録
        
        Args:
            logger_name: ロガー名
            user_id: ユーザーID
            action: アクション（view, create, update, delete）
            resource: リソース（temple, butsugo等）
            **context: 追加情報
        """
        logger = cls.get_logger(logger_name, 'access')
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': action,
            'resource': resource,
            **context
        }
        
        logger.info(json.dumps(log_data, ensure_ascii=False))
    
    @classmethod
    def get_recent_errors(cls, log_type='error', lines=100):
        """
        最近のエラーログを取得
        
        Args:
            log_type: ログタイプ
            lines: 取得する行数
            
        Returns:
            list: ログエントリのリスト
        """
        log_file = cls.LOG_DIR / cls.LOG_FILES.get(log_type, 'app.log')
        
        if not log_file.exists():
            return []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                # 最後のN行を取得
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                # JSON形式のログをパース
                logs = []
                for line in recent_lines:
                    try:
                        # JSON部分を抽出
                        if '{' in line:
                            json_part = line[line.index('{'):]
                            log_entry = json.loads(json_part)
                            logs.append(log_entry)
                    except json.JSONDecodeError:
                        # JSON形式でない行はスキップ
                        continue
                
                return logs
        except Exception as e:
            print(f"Error reading log file: {e}")
            return []
    
    @classmethod
    def clear_old_logs(cls, days=30):
        """
        古いログファイルを削除
        
        Args:
            days: 保持する日数
        """
        import time
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        for log_file in cls.LOG_DIR.glob('*.log*'):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    print(f"Deleted old log file: {log_file}")
            except Exception as e:
                print(f"Error deleting log file {log_file}: {e}")


# 初期化
ErrorLogger.setup()

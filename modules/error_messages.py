"""
エラーメッセージ定義
全てのエラーメッセージを一元管理

使い方:
    from modules.error_messages import ErrorMessages
    
    error_msg = ErrorMessages.get_user_message('FILE_TOO_LARGE')
"""


class ErrorMessages:
    """エラーメッセージの定義クラス"""
    
    # ========================================
    # 認証関連のエラー
    # ========================================
    AUTH_ERRORS = {
        'INVALID_CREDENTIALS': {
            'user_message': 'ユーザー名またはパスワードが正しくありません',
            'log_message': 'Invalid login credentials provided',
            'status_code': 401
        },
        'ACCOUNT_LOCKED': {
            'user_message': 'ログイン試行回数が上限に達しました。{minutes}分後に再度お試しください',
            'log_message': 'Account locked due to multiple failed login attempts',
            'status_code': 423
        },
        'SESSION_EXPIRED': {
            'user_message': 'セッションの有効期限が切れました。再度ログインしてください',
            'log_message': 'User session expired',
            'status_code': 401
        },
        'UNAUTHORIZED': {
            'user_message': 'ログインが必要です',
            'log_message': 'Unauthorized access attempt',
            'status_code': 401
        },
        'PERMISSION_DENIED': {
            'user_message': 'この操作を行う権限がありません',
            'log_message': 'Permission denied for user',
            'status_code': 403
        },
        'INVALID_TOKEN': {
            'user_message': 'トークンが無効です。再度お試しください',
            'log_message': 'Invalid or expired token',
            'status_code': 401
        }
    }
    
    # ========================================
    # ファイル・画像関連のエラー
    # ========================================
    FILE_ERRORS = {
        'FILE_TOO_LARGE': {
            'user_message': 'ファイルサイズは{max_size}MB以下にしてください（現在: {current_size}MB）',
            'log_message': 'File size exceeds limit: {current_size}MB > {max_size}MB',
            'status_code': 413
        },
        'INVALID_FILE_FORMAT': {
            'user_message': '対応していない形式です。対応形式: {allowed_formats}',
            'log_message': 'Invalid file format: {format}',
            'status_code': 400
        },
        'FILE_NOT_FOUND': {
            'user_message': 'ファイルが見つかりません',
            'log_message': 'File not found: {filepath}',
            'status_code': 404
        },
        'UPLOAD_FAILED': {
            'user_message': 'アップロードに失敗しました。時間をおいて再度お試しください',
            'log_message': 'File upload failed: {reason}',
            'status_code': 500
        },
        'CONVERSION_FAILED': {
            'user_message': '画像の変換に失敗しました。別のファイルをお試しください',
            'log_message': 'Image conversion failed: {reason}',
            'status_code': 500
        },
        'INVALID_IMAGE': {
            'user_message': '画像ファイルが破損しているか、対応していない形式です',
            'log_message': 'Invalid or corrupted image file',
            'status_code': 400
        }
    }
    
    # ========================================
    # データベース関連のエラー
    # ========================================
    DATABASE_ERRORS = {
        'CONNECTION_FAILED': {
            'user_message': 'データベースに接続できません。しばらくお待ちください',
            'log_message': 'Database connection failed: {reason}',
            'status_code': 503
        },
        'QUERY_FAILED': {
            'user_message': 'データの取得に失敗しました',
            'log_message': 'Database query failed: {query}',
            'status_code': 500
        },
        'RECORD_NOT_FOUND': {
            'user_message': 'データが見つかりません',
            'log_message': 'Record not found: {table} id={id}',
            'status_code': 404
        },
        'DUPLICATE_ENTRY': {
            'user_message': 'すでに登録されています',
            'log_message': 'Duplicate entry: {field}={value}',
            'status_code': 409
        },
        'CONSTRAINT_VIOLATION': {
            'user_message': 'データの整合性エラーが発生しました',
            'log_message': 'Database constraint violation: {constraint}',
            'status_code': 400
        },
        'TRANSACTION_FAILED': {
            'user_message': '処理に失敗しました。もう一度お試しください',
            'log_message': 'Transaction failed and rolled back',
            'status_code': 500
        }
    }
    
    # ========================================
    # バリデーション関連のエラー
    # ========================================
    VALIDATION_ERRORS = {
        'REQUIRED_FIELD': {
            'user_message': '{field}は必須項目です',
            'log_message': 'Required field missing: {field}',
            'status_code': 400
        },
        'INVALID_EMAIL': {
            'user_message': '有効なメールアドレスを入力してください',
            'log_message': 'Invalid email format: {email}',
            'status_code': 400
        },
        'INVALID_LENGTH': {
            'user_message': '{field}は{min}〜{max}文字で入力してください',
            'log_message': 'Invalid length for {field}: {length}',
            'status_code': 400
        },
        'WEAK_PASSWORD': {
            'user_message': 'パスワードは8文字以上で、大文字・小文字・数字を含めてください',
            'log_message': 'Weak password provided',
            'status_code': 400
        },
        'INVALID_FORMAT': {
            'user_message': '{field}の形式が正しくありません',
            'log_message': 'Invalid format for {field}',
            'status_code': 400
        },
        'XSS_DETECTED': {
            'user_message': '不正な文字が含まれています',
            'log_message': 'XSS attack detected in {field}',
            'status_code': 400
        },
        'SQL_INJECTION_DETECTED': {
            'user_message': '不正な文字が含まれています',
            'log_message': 'SQL injection attempt detected in {field}',
            'status_code': 400
        }
    }
    
    # ========================================
    # API関連のエラー
    # ========================================
    API_ERRORS = {
        'RATE_LIMIT_EXCEEDED': {
            'user_message': 'リクエストが多すぎます。{retry_after}秒後に再度お試しください',
            'log_message': 'Rate limit exceeded for {identifier}',
            'status_code': 429
        },
        'API_TIMEOUT': {
            'user_message': '処理に時間がかかっています。もう一度お試しください',
            'log_message': 'API request timeout: {endpoint}',
            'status_code': 504
        },
        'EXTERNAL_API_ERROR': {
            'user_message': '外部サービスとの連携に失敗しました。しばらくお待ちください',
            'log_message': 'External API error: {service} - {reason}',
            'status_code': 502
        },
        'GEMINI_API_ERROR': {
            'user_message': 'AI機能が一時的に利用できません。しばらくお待ちください',
            'log_message': 'Gemini API error: {reason}',
            'status_code': 503
        },
        'GEMINI_QUOTA_EXCEEDED': {
            'user_message': 'AI機能の利用制限に達しました。1時間後に再度お試しください',
            'log_message': 'Gemini API quota exceeded',
            'status_code': 429
        }
    }
    
    # ========================================
    # 一般的なエラー
    # ========================================
    GENERAL_ERRORS = {
        'UNEXPECTED_ERROR': {
            'user_message': 'エラーが発生しました。しばらくお待ちください',
            'log_message': 'Unexpected error: {error}',
            'status_code': 500
        },
        'NOT_FOUND': {
            'user_message': 'ページが見つかりません',
            'log_message': 'Resource not found: {path}',
            'status_code': 404
        },
        'METHOD_NOT_ALLOWED': {
            'user_message': '許可されていない操作です',
            'log_message': 'Method not allowed: {method} on {path}',
            'status_code': 405
        },
        'BAD_REQUEST': {
            'user_message': 'リクエストが不正です',
            'log_message': 'Bad request: {reason}',
            'status_code': 400
        },
        'SERVICE_UNAVAILABLE': {
            'user_message': 'サービスが一時的に利用できません。しばらくお待ちください',
            'log_message': 'Service unavailable: {reason}',
            'status_code': 503
        }
    }
    
    @classmethod
    def get_user_message(cls, error_code, **kwargs):
        """
        ユーザー向けのエラーメッセージを取得
        
        Args:
            error_code: エラーコード（例: 'FILE_TOO_LARGE'）
            **kwargs: メッセージに埋め込むパラメータ
            
        Returns:
            str: フォーマット済みのユーザー向けメッセージ
        """
        # 全カテゴリから検索
        for category in [cls.AUTH_ERRORS, cls.FILE_ERRORS, cls.DATABASE_ERRORS, 
                        cls.VALIDATION_ERRORS, cls.API_ERRORS, cls.GENERAL_ERRORS]:
            if error_code in category:
                message = category[error_code]['user_message']
                try:
                    return message.format(**kwargs)
                except KeyError:
                    return message
        
        # エラーコードが見つからない場合
        return cls.GENERAL_ERRORS['UNEXPECTED_ERROR']['user_message']
    
    @classmethod
    def get_log_message(cls, error_code, **kwargs):
        """
        ログ記録用のエラーメッセージを取得
        
        Args:
            error_code: エラーコード
            **kwargs: メッセージに埋め込むパラメータ
            
        Returns:
            str: フォーマット済みのログ用メッセージ
        """
        for category in [cls.AUTH_ERRORS, cls.FILE_ERRORS, cls.DATABASE_ERRORS,
                        cls.VALIDATION_ERRORS, cls.API_ERRORS, cls.GENERAL_ERRORS]:
            if error_code in category:
                message = category[error_code]['log_message']
                try:
                    return message.format(**kwargs)
                except KeyError:
                    return message
        
        return f"Unknown error code: {error_code}"
    
    @classmethod
    def get_status_code(cls, error_code):
        """
        エラーコードに対応するHTTPステータスコードを取得
        
        Args:
            error_code: エラーコード
            
        Returns:
            int: HTTPステータスコード
        """
        for category in [cls.AUTH_ERRORS, cls.FILE_ERRORS, cls.DATABASE_ERRORS,
                        cls.VALIDATION_ERRORS, cls.API_ERRORS, cls.GENERAL_ERRORS]:
            if error_code in category:
                return category[error_code]['status_code']
        
        return 500  # デフォルトは Internal Server Error
    
    @classmethod
    def get_all_error_codes(cls):
        """
        全てのエラーコードのリストを取得（デバッグ用）
        
        Returns:
            list: 全エラーコードのリスト
        """
        codes = []
        for category in [cls.AUTH_ERRORS, cls.FILE_ERRORS, cls.DATABASE_ERRORS,
                        cls.VALIDATION_ERRORS, cls.API_ERRORS, cls.GENERAL_ERRORS]:
            codes.extend(category.keys())
        return codes

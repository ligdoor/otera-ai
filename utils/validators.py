"""
バリデーション用のヘルパー関数
"""
import re


def validate_email(email):
    """
    メールアドレスの検証
    
    Args:
        email: 検証するメールアドレス
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not email or not email.strip():
        return False, "メールアドレスを入力してください"
    
    email = email.strip()
    
    # 基本的なメールアドレスの正規表現
    pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "メールアドレスの形式が正しくありません"
    
    # 長さチェック（最大254文字）
    if len(email) > 254:
        return False, "メールアドレスが長すぎます"
    
    return True, ""


def validate_user_id(user_id):
    """
    ユーザーIDの検証
    
    Args:
        user_id: 検証するユーザーID
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not user_id or not user_id.strip():
        return False, "ユーザーIDを入力してください"
    
    user_id = user_id.strip()
    
    # 長さチェック（3文字以上、50文字以下）
    if len(user_id) < 3:
        return False, "ユーザーIDは3文字以上必要です"
    
    if len(user_id) > 50:
        return False, "ユーザーIDは50文字以内で入力してください"
    
    # 英数字とアンダースコアのみ
    if not re.match(r'^[a-zA-Z0-9_]+$', user_id):
        return False, "ユーザーIDは英数字とアンダースコア（_）のみ使用できます"
    
    # 先頭は英字である必要がある（推奨）
    if not user_id[0].isalpha():
        return False, "ユーザーIDは英字で始まる必要があります"
    
    return True, ""


def validate_password(password):
    """
    パスワードの検証
    
    Args:
        password: 検証するパスワード
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not password:
        return False, "パスワードを入力してください"
    
    # 長さチェック（8文字以上、128文字以下）
    if len(password) < 8:
        return False, "パスワードは8文字以上必要です"
    
    if len(password) > 128:
        return False, "パスワードは128文字以内で入力してください"
    
    # 強度チェック（推奨）
    has_lower = bool(re.search(r'[a-z]', password))
    has_upper = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    strength_count = sum([has_lower, has_upper, has_digit, has_special])
    
    if strength_count < 2:
        return False, "パスワードは英小文字、英大文字、数字、記号のうち2種類以上を含む必要があります"
    
    return True, ""


def validate_name(name):
    """
    名前の検証
    
    Args:
        name: 検証する名前
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not name or not name.strip():
        return False, "名前を入力してください"
    
    name = name.strip()
    
    # 長さチェック（1文字以上、100文字以下）
    if len(name) < 1:
        return False, "名前を入力してください"
    
    if len(name) > 100:
        return False, "名前は100文字以内で入力してください"
    
    return True, ""


def validate_token(token):
    """
    パスワードリセットトークンの検証
    
    Args:
        token: 検証するトークン
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not token or not token.strip():
        return False, "トークンが無効です"
    
    token = token.strip()
    
    # 長さチェック（最低32文字）
    if len(token) < 32:
        return False, "トークンが無効です"
    
    # URL-safeなbase64文字のみ（英数字、-, _）
    if not re.match(r'^[A-Za-z0-9_-]+$', token):
        return False, "トークンが無効です"
    
    return True, ""


def sanitize_input(input_string, max_length=None):
    """
    入力文字列のサニタイゼーション
    
    Args:
        input_string: サニタイズする文字列
        max_length: 最大長（Noneの場合は制限なし）
    
    Returns:
        str: サニタイズされた文字列
    """
    if not input_string:
        return ""
    
    # 前後の空白を削除
    sanitized = input_string.strip()
    
    # 制御文字を削除
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    
    # 長さ制限
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized
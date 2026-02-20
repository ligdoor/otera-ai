"""
環境変数チェックツール
起動時に必要な環境変数が設定されているか確認
"""
import logging
from config import Config


logger = logging.getLogger(__name__)

def check_required_env():
    """必須環境変数のチェック"""
    errors = []
    warnings = []
    
    # 必須項目
    if not Config.SECRET_KEY:
        errors.append("SECRET_KEY が設定されていません")
    
    if Config.USE_SUPABASE:
        if not Config.SUPABASE_URL:
            errors.append("SUPABASE_URL が設定されていません")
        if not Config.SUPABASE_SERVICE_KEY:
            errors.append("SUPABASE_SERVICE_KEY が設定されていません")
    else:
        if not Config.GOOGLE_CREDENTIALS_JSON:
            warnings.append("GOOGLE_CREDENTIALS_JSON が設定されていません")
    
    # 推奨項目
    if not Config.GEMINI_API_KEY:
        warnings.append("GEMINI_API_KEY が未設定 (AI機能が無効)")
    
    if not Config.SLACK_WEBHOOK_URL:
        warnings.append("SLACK_WEBHOOK_URL が未設定 (Slack通知が無効)")
    
    # 結果表示
    if errors:
        logger.error("\n❌ 必須環境変数が不足しています:")
        for err in errors:
            logger.debug(f"  • {err}")
        return False
    
    if warnings:
        logger.error("\n⚠️ 推奨環境変数が未設定です:")
        for warn in warnings:
            logger.debug(f"  • {warn}")
    
    logger.info("\n✅ 環境変数チェック完了")
    return True
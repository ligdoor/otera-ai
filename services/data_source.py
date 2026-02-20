"""
データソース切り替えモジュール

Google SheetsとSupabaseを環境変数で切り替えます。
"""

import logging
from config import Config

logger = logging.getLogger(__name__)


# 設定に基づいてインポート先を切り替え
if Config.USE_SUPABASE:
    logger.info("✅ データソース: Supabase")
    from services.spreadsheet_supabase import (
        add_log,
        load_fields_config,
        load_data_from_sheet,
        get_data_sheet_and_headers
    )
else:
    logger.info("✅ データソース: Google Sheets")
    from services.spreadsheet import (
        add_log,
        load_fields_config,
        load_data_from_sheet,
        get_data_sheet_and_headers
    )

# すべての関数をエクスポート
__all__ = [
    'add_log',
    'load_fields_config',
    'load_data_from_sheet',
    'get_data_sheet_and_headers'
]

from flask import Blueprint, jsonify, session, redirect, url_for
from config import Config
from utils.helpers import get_jst_timestamp

health_bp = Blueprint('health', __name__)

@health_bp.route("/health")
def health_simple():
    """簡易ヘルスチェック（認証不要・公開用）"""
    return jsonify({'status': 'ok'})

@health_bp.route("/health/detailed")
def health_detailed():
    """詳細なヘルスチェック（★修正: 管理者のみアクセス可能）"""
    # ★修正: 認証なしで内部構成が外部に漏れないようにする
    if not session.get('is_admin') or session.get('role') != 'admin':
        return jsonify({'error': '権限がありません'}), 403
    checks = {}
    
    # データベース接続チェック
    try:
        if Config.USE_SUPABASE:
            from services.database import get_supabase_client
            client = get_supabase_client()
            client.table('temples').select('id').limit(1).execute()
            checks['database'] = {'status': 'healthy', 'type': 'Supabase'}
        else:
            from services.spreadsheet import get_spreadsheet_client
            get_spreadsheet_client()
            checks['database'] = {'status': 'healthy', 'type': 'Google Sheets'}
    except Exception as e:
        checks['database'] = {'status': 'unhealthy', 'error': str(e)}
    
    # AI機能チェック
    if Config.GEMINI_API_KEY:
        checks['ai'] = {'status': 'enabled'}
    else:
        checks['ai'] = {'status': 'disabled'}
    
    # 通知機能チェック
    if Config.SLACK_WEBHOOK_URL:
        checks['notifications'] = {'status': 'enabled', 'type': 'Slack'}
    else:
        checks['notifications'] = {'status': 'disabled'}
    
    # 全体のステータス判定
    overall = 'healthy' if checks['database']['status'] == 'healthy' else 'unhealthy'
    
    return jsonify({
        'status': overall,
        'timestamp': get_jst_timestamp(),
        'checks': checks
    })
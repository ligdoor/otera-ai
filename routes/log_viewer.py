"""
ログビューア - Web UI

管理画面からログを確認できるようにします
"""

from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

log_viewer_bp = Blueprint('log_viewer', __name__, url_prefix='/admin/logs')


def _require_admin():
    """管理者権限チェック（デコレータ代わり）"""
    if not session.get('is_admin'):
        return redirect(url_for('auth_login.admin'))
    if session.get('role') not in ('admin',):
        return redirect('/')
    return None


@log_viewer_bp.route('/')
def index():
    """ログビューア画面"""
    # ★修正: 認証なしアクセスを防止
    redirect_response = _require_admin()
    if redirect_response:
        return redirect_response
    return render_template('admin/log_viewer.html')


@log_viewer_bp.route('/api/logs')
def get_logs():
    """
    ログデータを取得するAPI
    
    Query Parameters:
        log_type: ログタイプ (all, error, info, debug, access)
        lines: 取得する行数 (default: 100)
        search: 検索キーワード
    """
    # ★修正: API にも認証チェック追加
    if not session.get('is_admin') or session.get('role') != 'admin':
        return jsonify({'error': '権限がありません'}), 403
    log_type = request.args.get('log_type', 'all')
    lines = int(request.args.get('lines', 100))
    search = request.args.get('search', '')
    
    # ログファイルパスの決定
    log_dir = Path('logs')
    
    if log_type == 'all':
        log_file = log_dir / 'app.log'
    elif log_type == 'error':
        log_file = log_dir / 'error' / 'error.log'
    elif log_type == 'info':
        log_file = log_dir / 'info' / 'info.log'
    elif log_type == 'debug':
        log_file = log_dir / 'debug' / 'debug.log'
    elif log_type == 'access':
        log_file = log_dir / 'access' / 'access.log'
    else:
        return jsonify({'error': 'Invalid log type'}), 400
    
    # ログファイルの読み込み
    if not log_file.exists():
        return jsonify({'logs': [], 'total': 0})
    
    try:
        # 最新N行を取得
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # 検索フィルタ
        if search:
            all_lines = [line for line in all_lines if search in line]
        
        # 最新lines行を取得
        recent_lines = all_lines[-lines:]
        recent_lines.reverse()  # 最新が上に来るように
        
        return jsonify({
            'logs': recent_lines,
            'total': len(all_lines)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@log_viewer_bp.route('/api/stats')
def get_stats():
    """
    ログ統計情報を取得
    
    Returns:
        - エラー数
        - 警告数
        - アクセス数
        - スローリクエスト数
    """
    log_dir = Path('logs')
    
    stats = {
        'errors': 0,
        'warnings': 0,
        'accesses': 0,
        'slow_requests': 0
    }
    
    # エラーログのカウント
    error_log = log_dir / 'error' / 'error.log'
    if error_log.exists():
        with open(error_log, 'r', encoding='utf-8') as f:
            stats['errors'] = sum(1 for _ in f)
    
    # app.logから警告をカウント
    app_log = log_dir / 'app.log'
    if app_log.exists():
        with open(app_log, 'r', encoding='utf-8') as f:
            for line in f:
                if '[WARNING]' in line:
                    stats['warnings'] += 1
                if 'Slow operation' in line:
                    stats['slow_requests'] += 1
    
    # アクセスログのカウント
    access_log = log_dir / 'access' / 'access.log'
    if access_log.exists():
        with open(access_log, 'r', encoding='utf-8') as f:
            stats['accesses'] = sum(1 for _ in f)
    
    return jsonify(stats)


@log_viewer_bp.route('/api/clear/<log_type>')
def clear_logs(log_type):
    """
    ログファイルをクリア
    
    Args:
        log_type: ログタイプ (debug のみ許可)
    """
    # セキュリティ上、DEBUGログのみクリア可能
    if log_type != 'debug':
        return jsonify({'error': 'Only debug logs can be cleared'}), 403
    
    log_file = Path('logs') / 'debug' / 'debug.log'
    
    try:
        if log_file.exists():
            log_file.write_text('')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

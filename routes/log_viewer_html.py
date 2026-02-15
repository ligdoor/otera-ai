"""
ログビューアー - HTMLダッシュボード

日付別・グラフ表示付きのログ閲覧機能
"""

from flask import Blueprint, render_template, request
from pathlib import Path
from datetime import datetime, timedelta
import re
from collections import defaultdict
from modules.api_response import APIResponse

log_viewer_html_bp = Blueprint('log_viewer_html', __name__, url_prefix='/admin/logs')


@log_viewer_html_bp.route('/')
def index():
    """ログビューアーHTMLを表示"""
    return render_template('log_viewer.html')


@log_viewer_html_bp.route('/api')
def get_logs():
    """
    ログデータAPI
    
    Query Parameters:
        type: ログタイプ (app, error, info, debug, access)
        date: 日付フィルタ (YYYY-MM-DD)
        level: レベルフィルタ (ERROR, WARNING, INFO, DEBUG)
    
    Returns:
        200: ログデータとグラフ用統計
    """
    log_type = request.args.get('type', 'app')
    date_filter = request.args.get('date', '')
    level_filter = request.args.get('level', '')
    
    # ログファイルパス
    log_paths = {
        'app': Path('logs/app.log'),
        'error': Path('logs/error/error.log'),
        'info': Path('logs/info/info.log'),
        'debug': Path('logs/debug/debug.log'),
        'access': Path('logs/access/access.log')
    }
    
    log_file = log_paths.get(log_type, log_paths['app'])
    
    if not log_file.exists():
        return APIResponse.error(
            'FILE_NOT_FOUND',
            f'ログファイルが見つかりません: {log_file}',
            {'file': str(log_file)},
            404
        )
    
    try:
        # ログ読み込み
        logs = []
        stats = {
            'total': 0,
            'error': 0,
            'warning': 0,
            'info': 0,
            'debug': 0
        }
        
        # 日別集計（過去7日間）
        daily_data = defaultdict(lambda: {'error': 0, 'warning': 0, 'info': 0})
        today = datetime.now().date()
        for i in range(7):
            date = today - timedelta(days=6-i)
            daily_data[date.strftime('%m/%d')] = {'error': 0, 'warning': 0, 'info': 0}
        
        # 時間帯別集計（今日）
        hourly_data = [0] * 24
        
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # ログパース
                log_entry = parse_log_line(line)
                
                # 日付フィルタ
                if date_filter and log_entry['date'] != date_filter:
                    continue
                
                # レベルフィルタ
                if level_filter and log_entry['level'] != level_filter:
                    continue
                
                logs.append(log_entry)
                stats['total'] += 1
                
                # レベル別カウント
                level = log_entry['level']
                if level == 'ERROR':
                    stats['error'] += 1
                elif level == 'WARNING':
                    stats['warning'] += 1
                elif level == 'INFO':
                    stats['info'] += 1
                elif level == 'DEBUG':
                    stats['debug'] += 1
                
                # 日別集計
                log_date = datetime.strptime(log_entry['date'], '%Y-%m-%d').date()
                if (today - log_date).days < 7:
                    date_key = log_date.strftime('%m/%d')
                    if date_key in daily_data:
                        if level == 'ERROR':
                            daily_data[date_key]['error'] += 1
                        elif level == 'WARNING':
                            daily_data[date_key]['warning'] += 1
                        elif level == 'INFO':
                            daily_data[date_key]['info'] += 1
                
                # 時間帯別集計（今日のみ）
                if log_entry['date'] == today.strftime('%Y-%m-%d'):
                    try:
                        hour = int(log_entry['time'].split(':')[0])
                        if 0 <= hour < 24:
                            hourly_data[hour] += 1
                    except:
                        pass
        
        # 最新順にソート
        logs.reverse()
        
        # グラフデータ整形
        daily_labels = sorted(daily_data.keys())
        charts = {
            'daily': {
                'labels': daily_labels,
                'error': [daily_data[d]['error'] for d in daily_labels],
                'warning': [daily_data[d]['warning'] for d in daily_labels],
                'info': [daily_data[d]['info'] for d in daily_labels]
            },
            'hourly': hourly_data
        }
        
        return APIResponse.success(
            data={
                'logs': logs,
                'stats': stats,
                'charts': charts
            },
            message=f"{stats['total']}件のログを取得しました"
        )
        
    except Exception as e:
        return APIResponse.internal_error(
            'ログの読み込みに失敗しました',
            error=e
        )


def parse_log_line(line):
    """
    ログ行をパース
    
    Args:
        line: ログ行
        
    Returns:
        dict: パース済みログエントリ
    """
    # 標準ログフォーマット: 2026-02-15 12:34:56 [LEVEL] module: message
    pattern = r'^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+(.+?):\s+(.+)$'
    match = re.match(pattern, line)
    
    if match:
        date, time, level, module, message = match.groups()
        return {
            'timestamp': f'{date} {time}',
            'date': date,
            'time': time,
            'level': level,
            'module': module,
            'message': message
        }
    else:
        # パースできない場合はそのまま返す
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'level': 'INFO',
            'module': 'unknown',
            'message': line
        }


@log_viewer_html_bp.route('/download')
def download_log():
    """
    ログファイルダウンロード
    
    Query Parameters:
        type: ログタイプ
        
    Returns:
        ログファイル
    """
    from flask import send_file
    
    log_type = request.args.get('type', 'app')
    
    log_paths = {
        'app': Path('logs/app.log'),
        'error': Path('logs/error/error.log'),
        'info': Path('logs/info/info.log'),
        'debug': Path('logs/debug/debug.log'),
        'access': Path('logs/access/access.log')
    }
    
    log_file = log_paths.get(log_type, log_paths['app'])
    
    if not log_file.exists():
        return APIResponse.not_found('ログファイル')
    
    return send_file(
        log_file,
        as_attachment=True,
        download_name=f'{log_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    )

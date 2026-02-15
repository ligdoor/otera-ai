"""
ログ管理システム - 使用例
"""

from modules.error_logger import ErrorLogger, log_execution_time
import time

# ========================================
# 1. 基本的な使用方法
# ========================================

# ロガーの初期化（main.pyで一度だけ実行）
ErrorLogger.setup(
    log_level='INFO',
    log_dir='logs',
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=30,
    json_format=False  # JSON形式にする場合はTrue
)

# ロガーの取得
logger = ErrorLogger.get_logger('my_module')

# ログの記録
logger.info("アプリケーション起動")
logger.warning("メモリ使用率が高い")
logger.error("データベース接続エラー")

# ========================================
# 2. 構造化エラーログ
# ========================================

ErrorLogger.log_error(
    'auth',
    'LOGIN_FAILED',
    'ログイン失敗',
    user_id='user123',
    ip_address='192.168.1.1',
    reason='パスワードが間違っています'
)

# ========================================
# 3. パフォーマンスログ
# ========================================

start = time.time()
# 何か処理
time.sleep(2)
duration_ms = (time.time() - start) * 1000

ErrorLogger.log_performance(
    'database',
    'query_users',
    duration_ms,
    query='SELECT * FROM users',
    rows_returned=100
)

# ========================================
# 4. アクセスログ
# ========================================

ErrorLogger.log_access(
    method='GET',
    path='/api/temples',
    status_code=200,
    duration_ms=45.2,
    user_id='admin',
    ip_address='127.0.0.1'
)

# ========================================
# 5. デコレーターを使った実行時間計測
# ========================================

@log_execution_time('my_service')
def slow_function():
    """実行時間が自動的にログに記録される"""
    time.sleep(1.5)
    return "完了"

result = slow_function()
# → logs/info/info.log に実行時間が記録される

# ========================================
# 6. Flask統合例
# ========================================

from flask import Flask, request, g
import time

app = Flask(__name__)

# リクエストの開始時間を記録
@app.before_request
def before_request():
    g.start_time = time.time()

# リクエストの終了時にログ記録
@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        duration_ms = (time.time() - g.start_time) * 1000
        
        ErrorLogger.log_access(
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=request.headers.get('X-User-ID'),
            ip_address=request.remote_addr
        )
    
    return response

# ========================================
# 7. エラーハンドリング統合
# ========================================

@app.route('/api/data')
def get_data():
    logger = ErrorLogger.get_logger('api')
    
    try:
        # 処理
        data = fetch_data()
        logger.info(f"データ取得成功: {len(data)}件")
        return jsonify(data)
    
    except Exception as e:
        logger.error(f"データ取得エラー: {str(e)}", exc_info=True)
        
        ErrorLogger.log_error(
            'api',
            'DATA_FETCH_ERROR',
            str(e),
            endpoint='/api/data',
            user_id=request.headers.get('X-User-ID')
        )
        
        return jsonify({'error': 'データ取得に失敗しました'}), 500

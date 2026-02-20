"""
パスワード管理ルート

パスワード変更、パスワードリセット機能を提供します。
セキュリティを重視した実装になっています。
"""

import logging
from flask import Blueprint, render_template, request, session, jsonify, url_for
import bcrypt
from utils.decorators import login_required
from services.database import get_supabase_client, update_user, get_user_by_id, add_log
from utils.email_service import email_service
from config import Config
from flask_extensions import limiter
from datetime import datetime, timedelta
import secrets

# ============================================
# Blueprintの定義
# ============================================

auth_password_bp = Blueprint('auth_password', __name__)

logger = logging.getLogger(__name__)


# ============================================
# パスワード変更
# ============================================

@auth_password_bp.route("/change_password", methods=["POST"])
@limiter.limit("3 per hour")
@login_required
def change_password():
    """
    パスワード変更
    
    ログイン中のユーザーが自分のパスワードを変更します。
    現在のパスワードの確認が必要です。
    
    Request Body (JSON):
        {
            "current_pass": "現在のパスワード",
            "new_pass": "新しいパスワード"
        }
    
    Returns:
        JSON: 処理結果
            status (str): "success"（成功時のみ）
            message (str): エラーメッセージ（エラー時のみ）
    
    Route:
        POST /change_password
    
    Authentication:
        @login_required: ログイン必須
    
    Rate Limit:
        3回/時間
    
    Password Requirements:
        - 8文字以上
        - 数字を含む
        - 英字を含む
    
    Process:
        1. パスワードのバリデーション
        2. 現在のパスワードを確認
        3. 新しいパスワードをハッシュ化
        4. データベースを更新
        5. ログを記録
    
    Example Request:
        POST /change_password
        {
            "current_pass": "oldpass123",
            "new_pass": "newpass456"
        }
    
    Example Response (成功):
        {
            "status": "success"
        }
    
    Example Response (エラー):
        {
            "message": "現在のパスワードが間違っています"
        }
    """
    # リクエストボディを取得
    current_pass = request.json['current_pass']
    new_pass = request.json['new_pass']
    user_id = session.get('user_id')
    
    # ============================================
    # パスワードバリデーション
    # ============================================
    
    # 長さチェック（8文字以上）
    if len(new_pass) < 8:
        return jsonify({
            "message": "パスワードは8文字以上必要です"
        }), 400
    
    # 数字を含むかチェック
    if not any(c.isdigit() for c in new_pass):
        return jsonify({
            "message": "パスワードには数字を含めてください"
        }), 400
    
    # 英字を含むかチェック
    if not any(c.isalpha() for c in new_pass):
        return jsonify({
            "message": "パスワードには英字を含めてください"
        }), 400
    
    try:
        # データソースに応じて処理を分岐
        if Config.USE_SUPABASE:
            return _change_password_supabase(user_id, current_pass, new_pass)
        else:
            return _change_password_sheets(user_id, current_pass, new_pass)
    
    except Exception as e:
        logger.error(f"❌ パスワード変更エラー: {e}")
        return jsonify({"message": str(e)}), 500


def _change_password_supabase(user_id: str, current_pass: str, new_pass: str):
    """
    Supabase版のパスワード変更
    
    Supabaseデータベースでパスワードを変更します。
    
    Args:
        user_id: ユーザーID
        current_pass: 現在のパスワード
        new_pass: 新しいパスワード
    
    Returns:
        JSON: 処理結果
    """
    # ユーザー情報を取得
    user = get_user_by_id(user_id)
    
    if not user:
        return jsonify({"message": "ユーザーが見つかりません"}), 404
    
    # 保存されているパスワードハッシュを取得
    stored_hash = user.get('password_hash', '')
    is_valid = False
    
    # ============================================
    # 現在のパスワードを検証
    # ============================================
    
    # bcryptハッシュの場合（推奨）
    if stored_hash.startswith('$2b$'):
        is_valid = bcrypt.checkpw(
            current_pass.encode('utf-8'),
            stored_hash.encode('utf-8')
        )
    # 平文パスワードの場合（古いデータ）
    else:
        is_valid = (str(stored_hash) == current_pass)
    
    if is_valid:
        # ============================================
        # パスワード変更成功
        # ============================================
        
        # 新しいパスワードをハッシュ化
        new_hash = bcrypt.hashpw(
            new_pass.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # データベースを更新
        update_user(user_id, {'password_hash': new_hash})
        
        # ログを記録
        add_log(
            action='パスワード変更',
            details='自身のパスワードを変更しました'
        )
        
        logger.info(f"✅ パスワード変更成功: {user_id}")
        
        return jsonify({"status": "success"})
    
    else:
        # ============================================
        # パスワード検証失敗
        # ============================================
        
        # ログを記録
        add_log(
            action='パスワード変更失敗',
            details='現在のパスワードが間違っています'
        )
        
        logger.error(f"❌ パスワード変更失敗: {user_id} - 現在のパスワードが不正")
        
        return jsonify({
            "message": "現在のパスワードが間違っています"
        }), 400


def _change_password_sheets(user_id: str, current_pass: str, new_pass: str):
    """
    Google Sheets版のパスワード変更
    
    Google Sheetsでパスワードを変更します。
    
    Args:
        user_id: ユーザーID
        current_pass: 現在のパスワード
        new_pass: 新しいパスワード
    
    Returns:
        JSON: 処理結果
    
    Note:
        将来的に廃止予定。Supabase版への移行を推奨。
    """
    from services.spreadsheet import get_spreadsheet_client
    from services.data_source import add_log as sheets_add_log
    
    # Google Sheetsクライアントを取得
    client = get_spreadsheet_client()
    sheet = client.open(Config.CONFIG_SPREADSHEET_NAME).worksheet('users')
    
    # ユーザーを検索
    cell = sheet.find(user_id, in_column=1)
    
    if cell:
        row_idx = cell.row
        stored_hash = sheet.cell(row_idx, 2).value
        is_valid = False
        
        # パスワード検証
        if stored_hash.startswith('$2b$'):
            is_valid = bcrypt.checkpw(
                current_pass.encode('utf-8'),
                stored_hash.encode('utf-8')
            )
        else:
            is_valid = (str(stored_hash) == current_pass)
        
        if is_valid:
            # 新しいパスワードをハッシュ化
            new_hash = bcrypt.hashpw(
                new_pass.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # シートを更新
            sheet.update_cell(row_idx, 2, new_hash)
            
            # ログを記録
            sheets_add_log("パスワード変更", "自身のパスワードを変更しました")
            
            return jsonify({"status": "success"})
        else:
            # ログを記録
            sheets_add_log("パスワード変更失敗", "現在のパスワードが間違っています")
            
            return jsonify({
                "message": "現在のパスワードが間違っています"
            }), 400
    else:
        return jsonify({"message": "ユーザーが見つかりません"}), 404


# ============================================
# パスワードリセットリクエスト
# ============================================

@auth_password_bp.route('/password-reset-request', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def password_reset_request():
    """
    パスワードリセットリクエスト
    
    ユーザーがパスワードを忘れた場合に、リセット用のメールを送信します。
    
    GET:
        パスワードリセットリクエスト画面を表示
    
    POST:
        リセット用メールを送信
    
    Form Data (POST):
        email: メールアドレス
    
    Returns:
        GET: リセットリクエスト画面
        POST: 成功またはエラーメッセージ付き画面
    
    Route:
        GET/POST /password-reset-request
    
    Authentication:
        不要（パスワードを忘れたユーザー向け）
    
    Rate Limit:
        5回/時間
    
    Security Features:
        - メールアドレスの存在確認を隠蔽（列挙攻撃対策）
        - 推測不可能なトークン生成
        - トークンの有効期限（1時間）
        - レート制限
    
    Process:
        1. メールアドレスを受け取る
        2. ユーザーを検索
        3. リセットトークンを生成
        4. トークンをDBに保存
        5. リセットリンクをメールで送信
        6. 成功メッセージを表示（ユーザーの存在に関わらず）
    
    Example:
        POST /password-reset-request
        Form: email=user@example.com
        
        → リセット用メールが送信される
    """
    if request.method == 'POST':
        # フォームからメールアドレスを取得
        email = request.form.get('email', '').strip()
        
        # メールアドレスの入力チェック
        if not email:
            return render_template(
                'password_reset_request.html',
                error='メールアドレスを入力してください'
            )
        
        try:
            # データベースクライアントを取得
            client = get_supabase_client()
            
            # ユーザーを検索
            response = client.table('users').select('*').eq('email', email).execute()
            
            # ============================================
            # セキュリティ対策: タイミング攻撃防止
            # ============================================
            # ユーザーが存在しない場合でも同じメッセージを表示
            # （悪意のある人がメールアドレスの存在確認をできないようにする）
            
            if response.data and len(response.data) > 0:
                user = response.data[0]
                
                # リセットトークンを生成（推測不可能なランダム文字列）
                token = secrets.token_urlsafe(32)
                
                # 有効期限を設定（1時間後）
                expires_at = datetime.utcnow() + timedelta(hours=1)
                
                # トークンをデータベースに保存
                client.table('password_reset_tokens').insert({
                    'user_id': user['id'],
                    'token': token,
                    'expires_at': expires_at.isoformat(),
                    'used': False
                }).execute()
                
                # リセットリンクを生成（完全なURL）
                reset_link = url_for(
                    'auth_password.password_reset',
                    token=token,
                    _external=True
                )
                
                # メールを送信
                email_service.send_password_reset_email(
                    to_email=email,
                    reset_link=reset_link,
                    user_name=user.get('name')
                )
                
                logger.debug(f"📧 パスワードリセットメール送信: {email}")
            
            # 成功メッセージ（ユーザーの存在に関わらず同じメッセージ）
            return render_template(
                'password_reset_request.html',
                success='パスワードリセット用のメールを送信しました。メールをご確認ください。'
            )
        
        except Exception as e:
            logger.error(f"❌ パスワードリセットリクエストエラー: {str(e)}")
            return render_template(
                'password_reset_request.html',
                error='エラーが発生しました。もう一度お試しください。'
            )
    
    # GET: リセットリクエスト画面を表示
    return render_template('password_reset_request.html')


# ============================================
# パスワードリセット実行
# ============================================

@auth_password_bp.route('/password-reset/<token>', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def password_reset(token):
    """
    パスワードリセット実行
    
    リセットトークンを使用して新しいパスワードを設定します。
    
    GET:
        パスワード入力画面を表示
    
    POST:
        新しいパスワードを設定
    
    Args:
        token: パスワードリセットトークン（URLパラメータ）
    
    Form Data (POST):
        password: 新しいパスワード
        password_confirm: パスワード確認
    
    Returns:
        GET: パスワード入力画面
        POST: ログイン画面（成功時）またはエラーメッセージ
    
    Route:
        GET/POST /password-reset/<token>
    
    Authentication:
        トークンによる認証
    
    Rate Limit:
        5回/時間
    
    Password Requirements:
        - 8文字以上
        - 確認用パスワードと一致
    
    Process:
        1. トークンの有効性を確認
        2. 有効期限をチェック
        3. 新しいパスワードを受け取る
        4. パスワードをバリデーション
        5. パスワードをハッシュ化して保存
        6. トークンを使用済みにする
        7. ログイン画面にリダイレクト
    
    Example:
        GET /password-reset/abc123xyz...
        → パスワード入力画面が表示される
        
        POST /password-reset/abc123xyz...
        Form: password=newpass123, password_confirm=newpass123
        → パスワードが変更され、ログイン画面にリダイレクト
    """
    try:
        # データベースクライアントを取得
        client = get_supabase_client()
        
        # ============================================
        # トークンの有効性を確認
        # ============================================
        
        response = client.table('password_reset_tokens')\
            .select('*')\
            .eq('token', token)\
            .eq('used', False)\
            .execute()
        
        # トークンが存在しない、または既に使用済み
        if not response.data or len(response.data) == 0:
            return render_template(
                'password_reset.html',
                token=token,
                error='無効なリセットリンクです。'
            )
        
        token_data = response.data[0]
        
        # ============================================
        # 有効期限を確認
        # ============================================
        
        expires_at = datetime.fromisoformat(
            token_data['expires_at'].replace('Z', '+00:00')
        )
        now = datetime.now(expires_at.tzinfo)
        
        # 有効期限切れ
        if now > expires_at:
            return render_template(
                'password_reset.html',
                token=token,
                error='リセットリンクの有効期限が切れています。もう一度リクエストしてください。'
            )
        
        # ============================================
        # POST: パスワード変更実行
        # ============================================
        
        if request.method == 'POST':
            # フォームデータを取得
            password = request.form.get('password', '').strip()
            password_confirm = request.form.get('password_confirm', '').strip()
            
            # バリデーション: 入力チェック
            if not password or not password_confirm:
                return render_template(
                    'password_reset.html',
                    token=token,
                    error='パスワードを入力してください。'
                )
            
            # バリデーション: 一致チェック
            if password != password_confirm:
                return render_template(
                    'password_reset.html',
                    token=token,
                    error='パスワードが一致しません。'
                )
            
            # バリデーション: 長さチェック
            if len(password) < 8:
                return render_template(
                    'password_reset.html',
                    token=token,
                    error='パスワードは8文字以上で設定してください。'
                )
            
            # パスワードをハッシュ化
            hashed_password = bcrypt.hashpw(
                password.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # データベースを更新
            client.table('users').update({
                'password_hash': hashed_password
            }).eq('id', token_data['user_id']).execute()
            
            # トークンを使用済みにする
            client.table('password_reset_tokens').update({
                'used': True
            }).eq('id', token_data['id']).execute()
            
            logger.info(f"✅ パスワードリセット成功: user_id={token_data['user_id']}")
            
            # ログイン画面にリダイレクト（成功メッセージ付き）
            return render_template(
                'login.html',
                success='パスワードを変更しました。新しいパスワードでログインしてください。'
            )
        
        # ============================================
        # GET: パスワード入力画面を表示
        # ============================================
        
        return render_template('password_reset.html', token=token)
    
    except Exception as e:
        logger.error(f"❌ パスワードリセットエラー: {str(e)}")
        return render_template(
            'password_reset.html',
            token=token,
            error='エラーが発生しました。もう一度お試しください。'
        )

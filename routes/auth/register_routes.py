"""
新規登録・承認ルート

新規ユーザー登録申請、管理者による承認/却下処理を提供します。
承認待ちユーザーの管理機能を含みます。
"""

from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
import bcrypt
from services.database import get_supabase_client
from utils.email_service import email_service
from datetime import datetime

# ============================================
# Blueprintの定義
# ============================================

auth_register_bp = Blueprint('auth_register', __name__)


# ============================================
# 新規登録画面
# ============================================

@auth_register_bp.route('/register', methods=['GET'])
def register_page():
    """
    新規登録画面を表示
    
    新規ユーザーが登録申請するためのフォームを表示します。
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    
    Route:
        GET /register
    
    Authentication:
        不要（誰でもアクセス可能）
    
    Template:
        register.html
    """
    return render_template('register.html')


# ============================================
# 新規登録申請処理
# ============================================

@auth_register_bp.route('/register', methods=['POST'])
def register():
    """
    新規登録申請を受け付ける
    
    ユーザーからの新規登録申請を受け付け、承認待ちテーブルに保存します。
    管理者にメールで通知します。
    
    Request Body (JSON):
        {
            "user_id": "ユーザーID",
            "name": "氏名",
            "email": "メールアドレス",
            "password": "パスワード",
            "department": "部署（任意）",
            "notes": "備考（任意）"
        }
    
    Returns:
        JSON: 処理結果
            success (bool): 成功した場合True
            message (str): 結果メッセージ
    
    Route:
        POST /register
    
    Authentication:
        不要（誰でも申請可能）
    
    Validation:
        - user_id, name, email, password は必須
        - user_idの重複チェック（既存ユーザーと申請中）
        - emailの重複チェック
    
    Security:
        - パスワードはbcryptでハッシュ化
        - パスワードは平文で保存しない
    
    Process:
        1. 入力値のバリデーション
        2. 重複チェック（user_id, email）
        3. パスワードのハッシュ化
        4. pending_usersテーブルに保存
        5. 管理者にメール通知
    
    Example Request:
        POST /register
        {
            "user_id": "tanaka001",
            "name": "田中太郎",
            "email": "tanaka@example.com",
            "password": "securepass123",
            "department": "総務部"
        }
    
    Example Response (成功):
        {
            "success": true,
            "message": "登録申請を受け付けました"
        }
    
    Example Response (エラー):
        {
            "success": false,
            "message": "このユーザーIDは既に使用されています"
        }
    """
    try:
        # リクエストボディを取得
        data = request.get_json()
        
        # ============================================
        # 入力検証
        # ============================================
        
        required_fields = ['user_id', 'name', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{field}は必須です'
                }), 400
        
        # データを取得
        user_id = data['user_id'].strip()
        name = data['name'].strip()
        email = data['email'].strip()
        password = data['password']
        department = data.get('department', '').strip()
        notes = data.get('notes', '').strip()
        
        # データベースクライアントを取得
        client = get_supabase_client()
        
        # ============================================
        # 重複チェック
        # ============================================
        
        # ユーザーID重複チェック（既存ユーザー）
        result = client.table('users').select('user_id').eq('user_id', user_id).execute()
        if result.data:
            return jsonify({
                'success': False,
                'message': 'このユーザーIDは既に申請が行われている可能性があります'
            }), 400
        
        # ユーザーID重複チェック（申請中）
        result = client.table('pending_users')\
            .select('user_id')\
            .eq('user_id', user_id)\
            .eq('status', 'pending')\
            .execute()
        
        if result.data:
            return jsonify({
                'success': False,
                'message': 'このユーザーIDで申請中のリクエストがあります'
            }), 400
        
        # メールアドレス重複チェック（既存ユーザー）
        result = client.table('users').select('email').eq('email', email).execute()
        if result.data:
            return jsonify({
                'success': False,
                'message': 'このメールアドレスでは既に申請が行われている可能性があります'
            }), 200

            # メールアドレス重複チェック（申請中ユーザー）
        result = client.table('pending_users')\
            .select('email')\
            .eq('email', email)\
            .eq('status', 'pending')\
            .execute()

        if result.data:
            return jsonify({
                'success': False,
                'message': 'このメールアドレスではすでに申請中のリクエストがあります'
            }), 200

        
        # ============================================
        # パスワードハッシュ化
        # ============================================
        
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # ============================================
        # pending_usersテーブルに保存
        # ============================================
        
        pending_user = {
            'user_id': user_id,
            'password_hash': password_hash,
            'name': name,
            'email': email,
            'department': department,
            'notes': notes,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = client.table('pending_users').insert(pending_user).execute()
        
        if not result.data:
            return jsonify({
                'success': False,
                'message': 'データベースエラーが発生しました'
            }), 500
        
        # ============================================
        # 管理者にメール通知
        # ============================================
        
        email_service.send_registration_notification({
            'user_id': user_id,
            'name': name,
            'email': email,
            'department': department,
            'notes': notes
        })
        
        print(f"✅ 新規登録申請: {user_id} ({name})")
        
        return jsonify({
            'success': True,
            'message': '登録申請を受け付けました'
        }), 200
    
    except Exception as e:
        print(f"❌ 登録エラー: {e}")
        return jsonify({
            'success': False,
            'message': '登録処理中にエラーが発生しました'
        }), 500


# ============================================
# 承認待ち一覧画面
# ============================================

@auth_register_bp.route('/admin/pending-users', methods=['GET'])
def pending_users_page():
    """
    承認待ちユーザー一覧画面
    
    管理者が承認待ちユーザーの一覧を確認できる画面を表示します。
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    
    Route:
        GET /admin/pending-users
    
    Authentication:
        ログイン必須
        管理者権限（admin）が必要
    
    Template Variables:
        pending_users: 承認待ちユーザーのリスト
    
    Permissions:
        - 管理者以外はメイン画面にリダイレクト
    """
    # ログインチェック
    if 'user_id' not in session:
        return redirect(url_for('auth_login.admin'))
    
    # 管理者権限チェック
    if session.get('role') != 'admin':
        return redirect(url_for('temple_view.index'))
    
    try:
        # データベースクライアントを取得
        client = get_supabase_client()
        
        # 承認待ちユーザーを取得
        result = client.table('pending_users')\
            .select('*')\
            .eq('status', 'pending')\
            .order('created_at', desc=True)\
            .execute()
        
        pending_users = result.data if result.data else []
        
        return render_template('pending_users.html', pending_users=pending_users)
    
    except Exception as e:
        print(f"❌ 承認待ちユーザー一覧取得エラー: {e}")
        return render_template('pending_users.html', pending_users=[])


# ============================================
# 承認処理
# ============================================

@auth_register_bp.route('/admin/approve-user/<int:pending_id>', methods=['POST'])
def approve_user(pending_id):
    """
    ユーザー登録申請を承認
    
    承認待ちユーザーを正式なユーザーとして登録します。
    ユーザーにメールで通知します。
    
    Args:
        pending_id: 承認待ちユーザーのID
    
    Request Body (JSON):
        {
            "role": "admin" | "editor" | "viewer"
        }
    
    Returns:
        JSON: 処理結果
            success (bool): 成功した場合True
            message (str): 結果メッセージ
    
    Route:
        POST /admin/approve-user/<int:pending_id>
    
    Authentication:
        ログイン必須
        管理者権限（admin）が必要
    
    Process:
        1. pending_usersから申請情報を取得
        2. usersテーブルに新規ユーザーを作成
        3. pending_usersのステータスを'approved'に更新
        4. ユーザーに承認メールを送信
    
    Example Request:
        POST /approve-user/123
        {
            "role": "editor"
        }
    
    Example Response:
        {
            "success": true,
            "message": "田中太郎さんを承認しました"
        }
    """
    # 権限チェック
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({
            'success': False,
            'message': '権限がありません'
        }), 403
    
    try:
        # リクエストボディを取得
        data = request.get_json()
        role = data.get('role', 'viewer')  # デフォルトはviewer
        
        # データベースクライアントを取得
        client = get_supabase_client()
        
        # ============================================
        # pending_usersから情報取得
        # ============================================
        
        result = client.table('pending_users')\
            .select('*')\
            .eq('id', pending_id)\
            .eq('status', 'pending')\
            .execute()
        
        if not result.data:
            return jsonify({
                'success': False,
                'message': 'ユーザーが見つかりません'
            }), 404
        
        pending_user = result.data[0]
        
        # ============================================
        # usersテーブルに登録
        # ============================================
        
        new_user = {
            'user_id': pending_user['user_id'],
            'password_hash': pending_user['password_hash'],
            'name': pending_user['name'],
            'email': pending_user['email'],
            'department': pending_user['department'],
            'role': role,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = client.table('users').insert(new_user).execute()
        
        if not result.data:
            return jsonify({
                'success': False,
                'message': 'ユーザー作成に失敗しました'
            }), 500
        
        # ============================================
        # pending_usersのステータス更新
        # ============================================
        
        client.table('pending_users')\
            .update({
                'status': 'approved',
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id', pending_id)\
            .execute()
        
        # ============================================
        # 承認メール送信
        # ============================================
        
        email_service.send_approval_notification(
            pending_user['email'],
            pending_user['name']
        )
        
        print(f"✅ ユーザー承認: {pending_user['user_id']} ({pending_user['name']}) - 権限: {role}")
        
        return jsonify({
            'success': True,
            'message': f'{pending_user["name"]}さんを承認しました'
        }), 200
    
    except Exception as e:
        print(f"❌ 承認処理エラー: {e}")
        return jsonify({
            'success': False,
            'message': '承認処理中にエラーが発生しました'
        }), 500


# ============================================
# 却下処理
# ============================================

@auth_register_bp.route('/admin/reject-user/<int:pending_id>', methods=['POST'])
def reject_user(pending_id):
    """
    ユーザー登録申請を却下
    
    承認待ちユーザーの申請を却下します。
    ユーザーにメールで通知します。
    
    Args:
        pending_id: 承認待ちユーザーのID
    
    Request Body (JSON):
        {
            "reason": "却下理由"
        }
    
    Returns:
        JSON: 処理結果
            success (bool): 成功した場合True
            message (str): 結果メッセージ
    
    Route:
        POST /admin/reject-user/<int:pending_id>
    
    Authentication:
        ログイン必須
        管理者権限（admin）が必要
    
    Process:
        1. pending_usersから申請情報を取得
        2. pending_usersのステータスを'rejected'に更新
        3. ユーザーに却下メールを送信
    
    Example Request:
        POST /reject-user/123
        {
            "reason": "社内メールアドレスを使用してください"
        }
    
    Example Response:
        {
            "success": true,
            "message": "田中太郎さんの申請を却下しました"
        }
    """
    # 権限チェック
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({
            'success': False,
            'message': '権限がありません'
        }), 403
    
    try:
        # リクエストボディを取得
        data = request.get_json()
        reason = data.get('reason', '')
        
        # データベースクライアントを取得
        client = get_supabase_client()
        
        # ============================================
        # pending_usersから情報取得
        # ============================================
        
        result = client.table('pending_users')\
            .select('*')\
            .eq('id', pending_id)\
            .eq('status', 'pending')\
            .execute()
        
        if not result.data:
            return jsonify({
                'success': False,
                'message': 'ユーザーが見つかりません'
            }), 404
        
        pending_user = result.data[0]
        
        # ============================================
        # pending_usersのステータス更新
        # ============================================
        
        client.table('pending_users')\
            .update({
                'status': 'rejected',
                'updated_at': datetime.utcnow().isoformat()
            })\
            .eq('id', pending_id)\
            .execute()
        
        # ============================================
        # 却下メール送信
        # ============================================
        
        email_service.send_rejection_notification(
            pending_user['email'],
            pending_user['name'],
            reason
        )
        
        print(f"⛔ ユーザー却下: {pending_user['user_id']} ({pending_user['name']})")
        
        return jsonify({
            'success': True,
            'message': f'{pending_user["name"]}さんの申請を却下しました'
        }), 200
    
    except Exception as e:
        print(f"❌ 却下処理エラー: {e}")
        return jsonify({
            'success': False,
            'message': '却下処理中にエラーが発生しました'
        }), 500


# ============================================
# 承認待ち件数API
# ============================================

@auth_register_bp.route('/api/pending-users-count', methods=['GET'])
def get_pending_users_count():
    """
    承認待ちユーザーの件数を取得
    
    管理画面のバッジ表示などに使用します。
    
    Returns:
        JSON: 承認待ち件数
            count (int): 承認待ちユーザー数
    
    Route:
        GET /api/pending-users-count
    
    Authentication:
        ログイン必須
        管理者権限（admin）が必要
    
    Permissions:
        - 管理者以外は常に0を返す
    
    Example Response:
        {
            "count": 3
        }
    """
    # 権限チェック（管理者以外は0を返す）
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'count': 0}), 200
    
    try:
        # データベースクライアントを取得
        client = get_supabase_client()
        
        # 承認待ち件数を取得
        result = client.table('pending_users')\
            .select('id', count='exact')\
            .eq('status', 'pending')\
            .execute()
        
        count = result.count if result.count else 0
        
        return jsonify({'count': count}), 200
    
    except Exception as e:
        print(f"❌ 承認待ち件数取得エラー: {e}")
        return jsonify({'count': 0}), 200

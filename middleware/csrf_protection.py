"""
CSRF (クロスサイトリクエストフォージェリ) 対策ユーティリティ

概要:
    悪意あるサイトからの偽リクエストを防ぐための
    トークンベースのCSRF対策を提供します。

使い方:
    1. main.py でCSRFを初期化:
        from middleware.csrf_protection import init_csrf
        init_csrf(app)

    2. HTMLフォームにCSRFトークンを埋め込む:
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

    3. Jinja2テンプレートで自動的に使えるようになります。

    4. POSTフォームの保護（デコレータを使用）:
        from middleware.csrf_protection import csrf_protect
        
        @app.route('/my-form', methods=['POST'])
        @csrf_protect
        def my_form():
            ...

    5. Ajax/Fetch のときはヘッダーで送る:
        fetch('/api/...', {
            method: 'POST',
            headers: {
                'X-CSRF-Token': document.querySelector('[name=csrf_token]').value,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
"""

import secrets
from functools import wraps
from flask import Flask, session, request, jsonify, abort


# CSRFトークンのセッションキー名
_CSRF_SESSION_KEY = '_csrf_token'


def generate_csrf_token() -> str:
    """
    CSRFトークンを生成または取得する。
    
    セッションに保存済みのトークンがあればそれを返す。
    なければ新規生成してセッションに保存する。
    
    Returns:
        str: CSRFトークン（64文字の16進数文字列）
    """
    if _CSRF_SESSION_KEY not in session:
        session[_CSRF_SESSION_KEY] = secrets.token_hex(32)
    return session[_CSRF_SESSION_KEY]


def validate_csrf_token() -> bool:
    """
    リクエストのCSRFトークンを検証する。
    
    フォームデータまたはヘッダーからトークンを取得して
    セッション内のトークンと比較する。
    
    Returns:
        bool: トークンが有効な場合True
    """
    session_token = session.get(_CSRF_SESSION_KEY)
    if not session_token:
        return False
    
    # フォームデータからトークンを取得
    request_token = request.form.get('csrf_token')
    
    # ない場合はヘッダーから取得（Ajax用）
    if not request_token:
        request_token = request.headers.get('X-CSRF-Token')
    
    if not request_token:
        return False
    
    # timing攻撃を防ぐために secrets.compare_digest を使う
    return secrets.compare_digest(session_token, request_token)


def csrf_protect(f):
    """
    POSTリクエストのCSRFトークンを検証するデコレータ。
    
    APIエンドポイント（JSONを受け取るもの）には
    このデコレータを付けなくてよい（その場合はJWTや
    SameSite Cookieで代替する）。
    
    使い方:
        @app.route('/delete', methods=['POST'])
        @csrf_protect
        def delete_item():
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            # Content-Type が application/json の場合はスキップ
            # （Ajaxは SameSite Cookie で守られるため）
            if request.is_json:
                return f(*args, **kwargs)
            
            if not validate_csrf_token():
                # フォーム送信の場合は403を返す
                abort(403)
        return f(*args, **kwargs)
    return decorated


def init_csrf(app: Flask) -> None:
    """
    CSRFユーティリティをFlaskアプリに登録する。
    
    Jinja2テンプレートで csrf_token() 関数が使えるようになる。
    
    Args:
        app: Flaskアプリケーションインスタンス
    
    Example (login.html):
        <form method="POST">
            {{ csrf_token_field() }}
            ...
        </form>
    """
    # テンプレートで {{ csrf_token() }} として使えるようにする
    app.jinja_env.globals['csrf_token'] = generate_csrf_token
    
    # テンプレートで {{ csrf_token_field() }} として hidden input を出力できるようにする
    def csrf_token_field():
        token = generate_csrf_token()
        return f'<input type="hidden" name="csrf_token" value="{token}">'
    
    app.jinja_env.globals['csrf_token_field'] = csrf_token_field

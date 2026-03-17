"""
セキュリティヘッダーミドルウェア

Webアプリケーションへのよくある攻撃を防ぐために
重要なHTTPセキュリティヘッダーを全レスポンスに追加します。

使い方（main.py / app.py で登録）:
    from middleware.security_headers import init_security_headers
    init_security_headers(app)
"""

from flask import Flask


def init_security_headers(app: Flask) -> None:
    """
    セキュリティヘッダーをFlaskアプリに登録する。

    Args:
        app: Flaskアプリケーションインスタンス
    """

    @app.after_request
    def add_security_headers(response):
        """全レスポンスにセキュリティヘッダーを付与"""

        # ============================================================
        # ★ クリックジャッキング攻撃の防止
        #    他サイトのiframeにこのサイトを埋め込まれることを禁止する
        # ============================================================
        response.headers['X-Frame-Options'] = 'DENY'

        # ============================================================
        # ★ MIMEタイプスニッフィングの防止
        #    ブラウザがファイルの種類を勝手に判断して実行することを禁止する
        # ============================================================
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # ============================================================
        # ★ XSS (クロスサイトスクリプティング) フィルターの有効化
        #    古いブラウザでもXSS攻撃をブロックするようにする
        # ============================================================
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # ============================================================
        # ★ リファラー情報の制限
        #    他サイトへのリンクをクリックしたとき、URLを送らないようにする
        # ============================================================
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # ============================================================
        # ★ 権限ポリシー（カメラ・マイク等へのアクセスを制限）
        # ============================================================
        response.headers['Permissions-Policy'] = (
            'camera=(), microphone=(), geolocation=(), payment=()'
        )

        # ============================================================
        # ★ HTTPS強制（Fly.ioはHTTPSが保証されているため有効）
        #    一度HTTPSでアクセスしたら、1年間はHTTPSのみを使う
        # ============================================================
        response.headers['Strict-Transport-Security'] = (
            'max-age=31536000; includeSubDomains'
        )

        # ============================================================
        # ★ コンテンツセキュリティポリシー（CSP）
        #    スクリプト・スタイル等の読み込み元を制限する
        #    ※ CDNやインラインスクリプトを使っている場合は調整が必要
        # ============================================================
        # 現時点ではレポートのみモード（実際はブロックしない）
        # 本番環境に慣れてきたら Content-Security-Policy に変更してください
        response.headers['Content-Security-Policy-Report-Only'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "  https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' "
            "  https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self';"
        )

        return response

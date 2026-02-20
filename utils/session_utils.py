"""
セッション管理ユーティリティ

セッション固定攻撃（Session Fixation Attack）対策など、
セッションに関するセキュリティ機能を提供します。

【セッション固定攻撃とは】
攻撃者がログイン前のセッションIDを事前に知っておき、
被害者がそのIDでログインするとセッションを乗っ取れてしまう攻撃。

【対策】
ログイン成功時に古いセッションデータを引き継ぎつつ、
新しいセッションIDを発行することで攻撃を無効化する。
"""

from flask import session


def regenerate_session() -> None:
    """
    セッション固定攻撃対策: セッションIDを再生成する

    ログイン成功時に呼び出すことで、ログイン前後でセッションIDを
    切り替え、セッション固定攻撃を防ぐ。

    処理の流れ:
        1. 現在のセッションデータを一時保存
        2. セッションをクリア（古いIDを無効化）
        3. 保存したデータを新しいセッションに書き戻す
        4. session.modified = True でFlaskに新規セッション発行を促す

    Usage:
        # ログイン成功直後に呼び出す
        regenerate_session()
        session['user_id'] = user_id
        session['role'] = role

    Note:
        Flaskは session.modified = True かつ session の内容が変わると
        新しいSet-Cookieヘッダーを返し、実質的に新しいセッションIDが
        発行される。session.clear() だけでは同じIDが再利用される
        可能性があるため、このユーティリティを使用すること。
    """
    # 現在のセッションデータを退避
    old_data = dict(session)

    # セッションをクリア（古いデータを消去）
    session.clear()

    # データを書き戻す（ここで session.modified = True になる）
    for key, value in old_data.items():
        session[key] = value

    # Flaskに「セッションが変更された」と明示的に伝える
    # → レスポンス時に新しいSet-Cookieが発行される
    session.modified = True

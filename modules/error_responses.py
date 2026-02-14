"""
エラーレスポンス生成
API/Web用の統一されたエラーレスポンスを生成

使い方:
    from modules.error_responses import ErrorResponse
    
    # APIレスポンス
    return ErrorResponse.api_error('FILE_TOO_LARGE', current_size=10, max_size=5)
    
    # Webレスポンス（HTMLテンプレート用）
    return ErrorResponse.web_error('PERMISSION_DENIED')
"""

from flask import jsonify, render_template, request
from modules.error_messages import ErrorMessages
from modules.error_logger import ErrorLogger
from datetime import datetime


class ErrorResponse:
    """エラーレスポンス生成クラス"""
    
    @staticmethod
    def api_error(error_code, status_code=None, **kwargs):
        """
        API用のJSONエラーレスポンスを生成
        
        Args:
            error_code: エラーコード
            status_code: HTTPステータスコード（省略時は自動設定）
            **kwargs: エラーメッセージに埋め込むパラメータ
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
        """
        # ステータスコード取得
        if status_code is None:
            status_code = ErrorMessages.get_status_code(error_code)
        
        # エラーメッセージ取得
        user_message = ErrorMessages.get_user_message(error_code, **kwargs)
        
        # レスポンスデータ作成
        response_data = {
            'success': False,
            'error': {
                'code': error_code,
                'message': user_message,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # 追加情報があれば含める
        if kwargs:
            response_data['error']['details'] = kwargs
        
        return jsonify(response_data), status_code
    
    @staticmethod
    def api_success(data=None, message=None):
        """
        API用の成功レスポンスを生成
        
        Args:
            data: レスポンスデータ
            message: 成功メッセージ
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
        """
        response_data = {
            'success': True
        }
        
        if data is not None:
            response_data['data'] = data
        
        if message:
            response_data['message'] = message
        
        response_data['timestamp'] = datetime.now().isoformat()
        
        return jsonify(response_data), 200
    
    @staticmethod
    def web_error(error_code, redirect_to=None, **kwargs):
        """
        Web用のエラーレスポンスを生成
        
        Args:
            error_code: エラーコード
            redirect_to: リダイレクト先URL（省略時はエラーページ表示）
            **kwargs: エラーメッセージに埋め込むパラメータ
            
        Returns:
            レンダリング済みHTMLまたはリダイレクト
        """
        from flask import flash, redirect
        
        # エラーメッセージ取得
        user_message = ErrorMessages.get_user_message(error_code, **kwargs)
        status_code = ErrorMessages.get_status_code(error_code)
        
        # リダイレクトする場合
        if redirect_to:
            flash(user_message, 'error')
            return redirect(redirect_to)
        
        # エラーページを表示
        return render_template(
            'error.html',
            error_code=error_code,
            error_message=user_message,
            status_code=status_code
        ), status_code
    
    @staticmethod
    def validation_error(errors):
        """
        バリデーションエラー用のレスポンス生成
        
        Args:
            errors: エラー辞書 {field_name: error_message}
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
        """
        response_data = {
            'success': False,
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '入力内容に誤りがあります',
                'validation_errors': errors,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return jsonify(response_data), 400
    
    @staticmethod
    def log_and_respond(logger_name, error_code, log_message=None, **kwargs):
        """
        ログ記録とエラーレスポンス生成を同時に行う
        
        Args:
            logger_name: ロガー名
            error_code: エラーコード
            log_message: ログメッセージ（省略時は自動生成）
            **kwargs: コンテキスト情報
            
        Returns:
            tuple: (JSONレスポンス, ステータスコード)
        """
        # ログメッセージ生成
        if log_message is None:
            log_message = ErrorMessages.get_log_message(error_code, **kwargs)
        
        # エラーログ記録
        ErrorLogger.log_error(
            logger_name,
            error_code,
            log_message,
            **kwargs
        )
        
        # エラーレスポンス生成
        return ErrorResponse.api_error(error_code, **kwargs)


class ErrorPageRenderer:
    """エラーページレンダリングクラス"""
    
    @staticmethod
    def render_404():
        """404エラーページをレンダリング"""
        return render_template('errors/404.html'), 404
    
    @staticmethod
    def render_500():
        """500エラーページをレンダリング"""
        return render_template('errors/500.html'), 500
    
    @staticmethod
    def render_403():
        """403エラーページをレンダリング"""
        return render_template('errors/403.html'), 403
    
    @staticmethod
    def render_custom_error(error_code, title, message):
        """
        カスタムエラーページをレンダリング
        
        Args:
            error_code: エラーコード
            title: エラータイトル
            message: エラーメッセージ
            
        Returns:
            レンダリング済みHTML
        """
        return render_template(
            'errors/custom.html',
            error_code=error_code,
            title=title,
            message=message
        ), ErrorMessages.get_status_code(error_code)

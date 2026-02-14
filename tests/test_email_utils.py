"""
メール送信機能のテスト (email_utils.py)
メール送信、テンプレート、パスワードリセットメールを検証
"""

import pytest
from unittest.mock import patch, MagicMock
from modules import email_utils


class TestEmailSending:
    """メール送信のテスト"""
    
    @patch('modules.email_utils.smtplib.SMTP')
    def test_メールを送信(self, mock_smtp):
        """メールが正しく送信される"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        to_email = 'user@example.com'
        subject = 'テストメール'
        body = 'これはテストです'
        
        result = email_utils.send_email(to_email, subject, body)
        
        assert result is True
        mock_server.sendmail.assert_called_once()
    
    @patch('modules.email_utils.smtplib.SMTP')
    def test_送信失敗時のエラーハンドリング(self, mock_smtp):
        """メール送信失敗時にエラーが処理される"""
        mock_server = MagicMock()
        mock_server.sendmail.side_effect = Exception("送信エラー")
        mock_smtp.return_value = mock_server
        
        result = email_utils.send_email('user@example.com', 'テスト', 'ボディ')
        
        assert result is False


class TestPasswordResetEmail:
    """パスワードリセットメールのテスト"""
    
    @patch('modules.email_utils.send_email')
    def test_パスワードリセットメール送信(self, mock_send):
        """パスワードリセットメールが送信される"""
        mock_send.return_value = True
        
        email = 'user@example.com'
        reset_token = 'abc123token'
        
        result = email_utils.send_password_reset_email(email, reset_token)
        
        assert result is True
        # メール本文にリセットリンクが含まれることを確認
        call_args = mock_send.call_args
        body = call_args[0][2]  # 3番目の引数（body）
        assert reset_token in body
    
    @patch('modules.email_utils.send_email')
    def test_リセットリンクの有効期限表示(self, mock_send):
        """リセットリンクの有効期限がメールに記載される"""
        mock_send.return_value = True
        
        email_utils.send_password_reset_email('user@example.com', 'token123')
        
        call_args = mock_send.call_args
        body = call_args[0][2]
        assert '1時間' in body or '60分' in body


class TestEmailTemplates:
    """メールテンプレートのテスト"""
    
    def test_ウェルカムメールテンプレート(self):
        """ウェルカムメールのテンプレートが正しく生成される"""
        username = 'test_user'
        template = email_utils.get_welcome_email_template(username)
        
        assert username in template
        assert 'ようこそ' in template or 'Welcome' in template
    
    def test_通知メールテンプレート(self):
        """通知メールのテンプレートが正しく生成される"""
        message = 'あなたの寺院情報が更新されました'
        template = email_utils.get_notification_email_template(message)
        
        assert message in template
    
    def test_HTMLメールテンプレート(self):
        """HTMLメールが正しく生成される"""
        html_content = email_utils.get_html_email_template(
            title='テスト',
            content='これはHTMLメールです'
        )
        
        assert '<html>' in html_content
        assert '<body>' in html_content
        assert 'これはHTMLメールです' in html_content


class TestEmailValidation:
    """メール送信前の検証テスト"""
    
    def test_無効なメールアドレスを拒否(self):
        """無効なメールアドレスで送信しない"""
        invalid_emails = [
            'invalid',
            '@example.com',
            'user@',
            ''
        ]
        
        for email in invalid_emails:
            result = email_utils.send_email(email, 'テスト', 'ボディ')
            assert result is False
    
    def test_空の件名を拒否(self):
        """空の件名で送信しない"""
        result = email_utils.send_email('user@example.com', '', 'ボディ')
        assert result is False


class TestBulkEmail:
    """一括メール送信のテスト"""
    
    @patch('modules.email_utils.send_email')
    def test_複数ユーザーにメール送信(self, mock_send):
        """複数のユーザーにメールを送信できる"""
        mock_send.return_value = True
        
        recipients = [
            'user1@example.com',
            'user2@example.com',
            'user3@example.com'
        ]
        
        result = email_utils.send_bulk_email(recipients, 'お知らせ', 'テスト内容')
        
        assert result is True
        assert mock_send.call_count == 3
    
    @patch('modules.email_utils.send_email')
    def test_送信失敗した宛先を記録(self, mock_send):
        """送信に失敗した宛先が記録される"""
        # 2番目だけ失敗
        mock_send.side_effect = [True, False, True]
        
        recipients = ['user1@example.com', 'user2@example.com', 'user3@example.com']
        failed = email_utils.send_bulk_email_with_retry(recipients, '件名', '本文')
        
        assert len(failed) == 1
        assert 'user2@example.com' in failed


class TestEmailRateLimit:
    """メール送信レート制限のテスト"""
    
    @patch('modules.email_utils.redis_client')
    @patch('modules.email_utils.send_email')
    def test_短時間の大量送信を制限(self, mock_send, mock_redis):
        """短時間に大量のメールを送信しようとすると制限される"""
        mock_redis.get.return_value = b'100'  # 既に100通送信済み
        
        # 制限: 1時間に100通まで
        result = email_utils.send_email_with_limit(
            'user@example.com',
            '件名',
            '本文'
        )
        
        assert result is False  # 制限により送信されない


# テスト実行時の設定
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

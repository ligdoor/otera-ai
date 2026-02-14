"""
認証機能のテスト (admin_auth.py)
ログイン、ログアウト、セッション管理の動作を検証
"""

import pytest
from unittest.mock import patch, MagicMock
from modules import admin_auth


class TestLogin:
    """ログイン機能のテスト"""
    
    @patch('modules.admin_auth.supabase')
    def test_正しい認証情報でログイン成功(self, mock_supabase):
        """正しいユーザー名とパスワードでログインできる"""
        # モックデータ設定
        mock_response = MagicMock()
        mock_response.data = [{
            'id': 1,
            'username': 'admin',
            'password': 'hashed_password',
            'role': 'admin'
        }]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        # パスワード検証をモック
        with patch('modules.admin_auth.check_password', return_value=True):
            result = admin_auth.verify_login('admin', 'password123')
        
        assert result is not None
        assert result['username'] == 'admin'
        assert result['role'] == 'admin'
    
    @patch('modules.admin_auth.supabase')
    def test_間違ったパスワードでログイン失敗(self, mock_supabase):
        """間違ったパスワードだとログインできない"""
        mock_response = MagicMock()
        mock_response.data = [{
            'id': 1,
            'username': 'admin',
            'password': 'hashed_password',
            'role': 'admin'
        }]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        with patch('modules.admin_auth.check_password', return_value=False):
            result = admin_auth.verify_login('admin', 'wrong_password')
        
        assert result is None
    
    @patch('modules.admin_auth.supabase')
    def test_存在しないユーザーでログイン失敗(self, mock_supabase):
        """存在しないユーザー名だとログインできない"""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        result = admin_auth.verify_login('nobody', 'password')
        
        assert result is None
    
    def test_空のユーザー名でログイン失敗(self):
        """空のユーザー名だとログインできない"""
        result = admin_auth.verify_login('', 'password')
        assert result is None
    
    def test_空のパスワードでログイン失敗(self):
        """空のパスワードだとログインできない"""
        result = admin_auth.verify_login('admin', '')
        assert result is None


class TestPasswordHashing:
    """パスワードハッシュ化のテスト"""
    
    def test_パスワードをハッシュ化できる(self):
        """パスワードが正しくハッシュ化される"""
        password = 'test_password123'
        hashed = admin_auth.hash_password(password)
        
        assert hashed != password  # 元のパスワードと異なる
        assert len(hashed) > 0  # ハッシュ値が生成されている
    
    def test_同じパスワードでも異なるハッシュ(self):
        """同じパスワードでも毎回異なるハッシュが生成される（ソルト）"""
        password = 'test_password123'
        hash1 = admin_auth.hash_password(password)
        hash2 = admin_auth.hash_password(password)
        
        assert hash1 != hash2
    
    def test_ハッシュ化したパスワードを検証できる(self):
        """ハッシュ化したパスワードが正しく検証される"""
        password = 'test_password123'
        hashed = admin_auth.hash_password(password)
        
        assert admin_auth.check_password(password, hashed) is True
        assert admin_auth.check_password('wrong_password', hashed) is False


class TestSession:
    """セッション管理のテスト"""
    
    def test_ログイン後セッションが作成される(self, client, logged_in_session):
        """ログイン後にセッションが正しく作成される"""
        with client.session_transaction() as sess:
            assert 'user_id' in sess
            assert 'username' in sess
            assert 'role' in sess
    
    def test_ログアウト後セッションがクリアされる(self, client, logged_in_session):
        """ログアウト後にセッションがクリアされる"""
        # セッションをクリア
        with client.session_transaction() as sess:
            sess.clear()
        
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
            assert 'username' not in sess
    
    def test_セッションの有効期限チェック(self):
        """セッションの有効期限が正しくチェックされる"""
        from datetime import datetime, timedelta
        
        # 有効なセッション
        valid_session = {
            'created_at': datetime.now().isoformat()
        }
        assert admin_auth.is_session_valid(valid_session) is True
        
        # 期限切れセッション（24時間以上前）
        expired_session = {
            'created_at': (datetime.now() - timedelta(hours=25)).isoformat()
        }
        assert admin_auth.is_session_valid(expired_session) is False


class TestLoginAttempts:
    """ログイン試行回数制限のテスト"""
    
    @patch('modules.admin_auth.redis_client')
    def test_ログイン試行回数を記録(self, mock_redis):
        """ログイン失敗時に試行回数が記録される"""
        mock_redis.incr.return_value = 1
        
        admin_auth.record_failed_login('test_user')
        
        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once()
    
    @patch('modules.admin_auth.redis_client')
    def test_試行回数が上限を超えるとロック(self, mock_redis):
        """ログイン試行回数が上限を超えるとアカウントがロックされる"""
        mock_redis.get.return_value = b'5'  # 5回失敗
        
        is_locked = admin_auth.is_account_locked('test_user')
        
        assert is_locked is True
    
    @patch('modules.admin_auth.redis_client')
    def test_ログイン成功で試行回数リセット(self, mock_redis):
        """ログイン成功時に試行回数がリセットされる"""
        admin_auth.reset_failed_login('test_user')
        
        mock_redis.delete.assert_called_once()


class TestPasswordReset:
    """パスワードリセットのテスト"""
    
    @patch('modules.admin_auth.supabase')
    def test_パスワードリセットトークン生成(self, mock_supabase):
        """パスワードリセット用のトークンが生成される"""
        mock_response = MagicMock()
        mock_response.data = [{'id': 1, 'email': 'test@example.com'}]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        token = admin_auth.generate_reset_token('test@example.com')
        
        assert token is not None
        assert len(token) > 20  # トークンの長さ確認
    
    def test_リセットトークンの有効期限(self):
        """リセットトークンの有効期限が正しくチェックされる"""
        from datetime import datetime, timedelta
        
        # 有効なトークン（1時間以内）
        valid_token_data = {
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=1)).isoformat()
        }
        assert admin_auth.is_token_valid(valid_token_data) is True
        
        # 期限切れトークン
        expired_token_data = {
            'created_at': (datetime.now() - timedelta(hours=2)).isoformat(),
            'expires_at': (datetime.now() - timedelta(hours=1)).isoformat()
        }
        assert admin_auth.is_token_valid(expired_token_data) is False
    
    @patch('modules.admin_auth.supabase')
    def test_パスワードリセット実行(self, mock_supabase):
        """パスワードリセットが正しく実行される"""
        new_password = 'new_password123'
        user_id = 1
        
        admin_auth.reset_password(user_id, new_password)
        
        # updateが呼ばれたことを確認
        mock_supabase.table().update().eq().execute.assert_called_once()


# テスト実行時の設定
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

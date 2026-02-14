"""
セッション管理のテスト (session_management.py)
Flaskセッションの管理機能を検証
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from modules import session_management


class TestSessionCreation:
    """セッション作成のテスト"""
    
    def test_ログイン時にセッション作成(self, client):
        """ログイン成功時にセッションが作成される"""
        with client.session_transaction() as sess:
            session_management.create_session(sess, user_id=1, username='admin', role='admin')
        
        with client.session_transaction() as sess:
            assert 'user_id' in sess
            assert sess['user_id'] == 1
            assert sess['username'] == 'admin'
            assert sess['role'] == 'admin'
    
    def test_セッションに作成時刻を記録(self, client):
        """セッション作成時刻が記録される"""
        with client.session_transaction() as sess:
            session_management.create_session(sess, user_id=1, username='admin', role='admin')
        
        with client.session_transaction() as sess:
            assert 'created_at' in sess
            created_at = datetime.fromisoformat(sess['created_at'])
            assert isinstance(created_at, datetime)


class TestSessionValidation:
    """セッション検証のテスト"""
    
    def test_有効なセッション(self, client):
        """有効なセッションが検証される"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'admin'
            sess['created_at'] = datetime.now().isoformat()
        
        is_valid = session_management.is_session_valid(client)
        assert is_valid is True
    
    def test_期限切れセッション(self, client):
        """24時間以上前のセッションは無効"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['created_at'] = (datetime.now() - timedelta(hours=25)).isoformat()
        
        is_valid = session_management.is_session_valid(client)
        assert is_valid is False
    
    def test_必須情報が欠けたセッション(self, client):
        """必須情報が欠けているセッションは無効"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            # usernameが欠けている
        
        is_valid = session_management.is_session_valid(client)
        assert is_valid is False


class TestSessionRefresh:
    """セッション更新のテスト"""
    
    def test_セッションを更新(self, client):
        """セッションの有効期限を更新できる"""
        # 古いセッション
        with client.session_transaction() as sess:
            old_time = datetime.now() - timedelta(hours=12)
            sess['user_id'] = 1
            sess['created_at'] = old_time.isoformat()
        
        # セッションを更新
        session_management.refresh_session(client)
        
        with client.session_transaction() as sess:
            new_time = datetime.fromisoformat(sess['created_at'])
            assert new_time > old_time


class TestSessionDestruction:
    """セッション破棄のテスト"""
    
    def test_ログアウト時にセッション破棄(self, client):
        """ログアウト時にセッションが完全にクリアされる"""
        # セッション作成
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'admin'
            sess['role'] = 'admin'
        
        # セッション破棄
        session_management.destroy_session(client)
        
        # セッションが空になっていることを確認
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
            assert 'username' not in sess
            assert 'role' not in sess


class TestSessionSecurity:
    """セッションセキュリティのテスト"""
    
    def test_セッションIDがランダム生成(self, client):
        """セッションIDがランダムに生成される"""
        session_ids = []
        
        for _ in range(5):
            with client.session_transaction() as sess:
                session_management.create_session(sess, user_id=1, username='admin', role='admin')
                if 'session_id' in sess:
                    session_ids.append(sess['session_id'])
        
        # 全てのIDが異なることを確認
        assert len(session_ids) == len(set(session_ids))
    
    def test_セッション固定化攻撃対策(self, client):
        """ログイン時にセッションIDが再生成される"""
        # 攻撃者が準備したセッションID
        with client.session_transaction() as sess:
            sess['session_id'] = 'attacker_session_id'
        
        # ログイン
        session_management.create_session(client, user_id=1, username='admin', role='admin')
        
        # セッションIDが変更されている
        with client.session_transaction() as sess:
            assert sess.get('session_id') != 'attacker_session_id'


class TestConcurrentSessions:
    """同時セッションのテスト"""
    
    @patch('modules.session_management.redis_client')
    def test_同一ユーザーの複数セッション管理(self, mock_redis):
        """同じユーザーが複数デバイスからログインできる"""
        user_id = 1
        
        # セッション1（PC）
        session1_id = 'session_pc_123'
        session_management.register_session(user_id, session1_id, device='PC')
        
        # セッション2（スマホ）
        session2_id = 'session_mobile_456'
        session_management.register_session(user_id, session2_id, device='Mobile')
        
        # 両方のセッションが有効
        assert mock_redis.setex.call_count >= 2
    
    @patch('modules.session_management.redis_client')
    def test_古いセッションを無効化(self, mock_redis):
        """ユーザーの古いセッションを無効化できる"""
        user_id = 1
        
        # 全てのセッションを無効化
        session_management.invalidate_all_sessions(user_id)
        
        # Redisのdeleteが呼ばれる
        assert mock_redis.delete.called


class TestSessionData:
    """セッションデータのテスト"""
    
    def test_カスタムデータをセッションに保存(self, client):
        """カスタムデータをセッションに保存できる"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['custom_data'] = {'theme': 'dark', 'language': 'ja'}
        
        with client.session_transaction() as sess:
            assert sess['custom_data']['theme'] == 'dark'
    
    def test_セッションデータサイズ制限(self, client):
        """セッションデータが大きすぎる場合は警告"""
        large_data = 'x' * 1000000  # 1MB
        
        with pytest.raises(ValueError):
            with client.session_transaction() as sess:
                session_management.set_session_data(sess, 'large_key', large_data)


class TestSessionTimeout:
    """セッションタイムアウトのテスト"""
    
    def test_アイドルタイムアウト(self, client):
        """30分間操作がないとセッションが無効"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['last_activity'] = (datetime.now() - timedelta(minutes=31)).isoformat()
        
        is_active = session_management.is_session_active(client)
        assert is_active is False
    
    def test_アクティビティでタイムアウトリセット(self, client):
        """ユーザーの操作でタイムアウトがリセットされる"""
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            old_time = datetime.now() - timedelta(minutes=10)
            sess['last_activity'] = old_time.isoformat()
        
        # アクティビティ記録
        session_management.update_last_activity(client)
        
        with client.session_transaction() as sess:
            new_time = datetime.fromisoformat(sess['last_activity'])
            assert new_time > old_time


class TestRememberMe:
    """Remember Me 機能のテスト"""
    
    @patch('modules.session_management.redis_client')
    def test_Remember_Meトークン生成(self, mock_redis):
        """Remember Me トークンを生成できる"""
        user_id = 1
        
        token = session_management.create_remember_token(user_id)
        
        assert token is not None
        assert len(token) > 20
        mock_redis.setex.assert_called_once()
    
    @patch('modules.session_management.redis_client')
    def test_Remember_Meトークンで自動ログイン(self, mock_redis):
        """Remember Me トークンで自動ログインできる"""
        user_id = 1
        token = 'valid_remember_token'
        
        # トークンが有効
        mock_redis.get.return_value = str(user_id).encode()
        
        auto_user_id = session_management.verify_remember_token(token)
        
        assert auto_user_id == user_id


class TestSessionMiddleware:
    """セッションミドルウェアのテスト"""
    
    def test_リクエスト前にセッションチェック(self, client):
        """各リクエスト前にセッションが検証される"""
        @session_management.require_login
        def protected_route():
            return "Protected content"
        
        # ログインなし
        with pytest.raises(Exception):
            protected_route()
        
        # ログイン後
        with client.session_transaction() as sess:
            sess['user_id'] = 1
        
        result = protected_route()
        assert result == "Protected content"


# テスト実行時の設定
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

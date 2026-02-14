"""
レート制限のテスト (rate_limit.py)
Redis使用の速度制限機能を検証
"""

import pytest
from unittest.mock import patch, MagicMock
from modules import rate_limit


class TestRateLimiting:
    """レート制限の基本テスト"""
    
    @patch('modules.rate_limit.redis_client')
    def test_初回アクセスは許可(self, mock_redis):
        """初回アクセスは制限されない"""
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        
        is_allowed = rate_limit.check_rate_limit('test_user', limit=10, window=60)
        
        assert is_allowed is True
    
    @patch('modules.rate_limit.redis_client')
    def test_制限回数以内は許可(self, mock_redis):
        """制限回数以内のアクセスは許可される"""
        mock_redis.get.return_value = b'5'  # 5回アクセス済み
        mock_redis.incr.return_value = 6
        
        is_allowed = rate_limit.check_rate_limit('test_user', limit=10, window=60)
        
        assert is_allowed is True
    
    @patch('modules.rate_limit.redis_client')
    def test_制限回数を超えると拒否(self, mock_redis):
        """制限回数を超えるとアクセスが拒否される"""
        mock_redis.get.return_value = b'10'  # 既に10回アクセス済み
        
        is_allowed = rate_limit.check_rate_limit('test_user', limit=10, window=60)
        
        assert is_allowed is False
    
    @patch('modules.rate_limit.redis_client')
    def test_カウンターに有効期限が設定される(self, mock_redis):
        """アクセスカウンターに有効期限が設定される"""
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        
        rate_limit.check_rate_limit('test_user', limit=10, window=60)
        
        # expireが呼ばれたことを確認
        mock_redis.expire.assert_called_once()


class TestIPBasedRateLimit:
    """IPアドレスベースのレート制限テスト"""
    
    @patch('modules.rate_limit.redis_client')
    def test_IPアドレスでレート制限(self, mock_redis):
        """IPアドレスごとにレート制限が適用される"""
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        
        ip_address = '192.168.1.1'
        is_allowed = rate_limit.check_ip_rate_limit(ip_address, limit=100, window=3600)
        
        assert is_allowed is True
        # IPアドレスをキーに使用していることを確認
        call_args = mock_redis.incr.call_args[0][0]
        assert ip_address in call_args
    
    @patch('modules.rate_limit.redis_client')
    def test_異なるIPは個別にカウント(self, mock_redis):
        """異なるIPアドレスは個別にカウントされる"""
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        
        # IP1
        rate_limit.check_ip_rate_limit('192.168.1.1', limit=10, window=60)
        
        # IP2（別のIP）
        rate_limit.check_ip_rate_limit('192.168.1.2', limit=10, window=60)
        
        # 両方許可される
        assert mock_redis.incr.call_count == 2


class TestUserBasedRateLimit:
    """ユーザーベースのレート制限テスト"""
    
    @patch('modules.rate_limit.redis_client')
    def test_ユーザーIDでレート制限(self, mock_redis):
        """ユーザーIDごとにレート制限が適用される"""
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        
        user_id = 'user_123'
        is_allowed = rate_limit.check_user_rate_limit(user_id, limit=50, window=60)
        
        assert is_allowed is True
    
    @patch('modules.rate_limit.redis_client')
    def test_異なるユーザーは個別にカウント(self, mock_redis):
        """異なるユーザーは個別にカウントされる"""
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        
        # ユーザー1
        is_allowed1 = rate_limit.check_user_rate_limit('user_1', limit=10, window=60)
        
        # ユーザー2
        is_allowed2 = rate_limit.check_user_rate_limit('user_2', limit=10, window=60)
        
        assert is_allowed1 is True
        assert is_allowed2 is True


class TestEndpointSpecificRateLimit:
    """エンドポイント別レート制限テスト"""
    
    @patch('modules.rate_limit.redis_client')
    def test_ログインエンドポイントのレート制限(self, mock_redis):
        """ログインエンドポイントは厳しい制限"""
        mock_redis.get.return_value = b'5'  # 5回試行済み
        
        is_allowed = rate_limit.check_login_rate_limit('user_123')
        
        # ログインは5回で制限される
        assert is_allowed is False
    
    @patch('modules.rate_limit.redis_client')
    def test_API呼び出しのレート制限(self, mock_redis):
        """API呼び出しの制限"""
        mock_redis.get.return_value = b'50'
        
        is_allowed = rate_limit.check_api_rate_limit('api_key_123', limit=100)
        
        # API呼び出しは100回まで
        assert is_allowed is True
    
    @patch('modules.rate_limit.redis_client')
    def test_画像アップロードのレート制限(self, mock_redis):
        """画像アップロードの制限"""
        mock_redis.get.return_value = b'10'
        
        is_allowed = rate_limit.check_upload_rate_limit('user_123', limit=20)
        
        # 画像アップロードは20回まで
        assert is_allowed is True


class TestRateLimitReset:
    """レート制限リセットのテスト"""
    
    @patch('modules.rate_limit.redis_client')
    def test_カウンターをリセット(self, mock_redis):
        """カウンターを手動でリセットできる"""
        rate_limit.reset_rate_limit('user_123')
        
        mock_redis.delete.assert_called_once()
    
    @patch('modules.rate_limit.redis_client')
    def test_時間経過でカウンターリセット(self, mock_redis):
        """指定時間経過でカウンターが自動リセットされる"""
        import time
        
        # 初回アクセス
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        rate_limit.check_rate_limit('user_123', limit=10, window=1)  # 1秒
        
        # 1秒待機
        time.sleep(1.1)
        
        # カウンターがリセットされている（Redisの有効期限で自動削除）
        mock_redis.get.return_value = None
        is_allowed = rate_limit.check_rate_limit('user_123', limit=10, window=1)
        
        assert is_allowed is True


class TestRateLimitInfo:
    """レート制限情報取得のテスト"""
    
    @patch('modules.rate_limit.redis_client')
    def test_残り回数を取得(self, mock_redis):
        """現在の残り実行可能回数を取得できる"""
        mock_redis.get.return_value = b'7'  # 7回使用済み
        
        remaining = rate_limit.get_remaining_attempts('user_123', limit=10)
        
        assert remaining == 3  # 10 - 7 = 3
    
    @patch('modules.rate_limit.redis_client')
    def test_リセットまでの時間を取得(self, mock_redis):
        """カウンターリセットまでの残り時間を取得できる"""
        mock_redis.ttl.return_value = 45  # 45秒後にリセット
        
        ttl = rate_limit.get_time_until_reset('user_123')
        
        assert ttl == 45
    
    @patch('modules.rate_limit.redis_client')
    def test_制限情報を一括取得(self, mock_redis):
        """レート制限の詳細情報を一括取得できる"""
        mock_redis.get.return_value = b'7'
        mock_redis.ttl.return_value = 45
        
        info = rate_limit.get_rate_limit_info('user_123', limit=10)
        
        assert info['used'] == 7
        assert info['remaining'] == 3
        assert info['reset_in'] == 45


class TestBurstProtection:
    """バースト保護のテスト"""
    
    @patch('modules.rate_limit.redis_client')
    def test_短時間の連続アクセスを制限(self, mock_redis):
        """短時間に大量のアクセスがあると制限される"""
        # 1秒間に10回アクセス
        for i in range(10):
            mock_redis.get.return_value = str(i).encode()
            mock_redis.incr.return_value = i + 1
            is_allowed = rate_limit.check_burst_limit('user_123', limit=5, window=1)
            
            if i < 5:
                assert is_allowed is True
            else:
                assert is_allowed is False


class TestWhitelist:
    """ホワイトリストのテスト"""
    
    @patch('modules.rate_limit.redis_client')
    def test_ホワイトリストIPは制限されない(self, mock_redis):
        """ホワイトリストに登録されたIPは制限されない"""
        whitelist_ips = ['127.0.0.1', '192.168.1.100']
        
        # ホワイトリストIP
        is_allowed = rate_limit.check_rate_limit_with_whitelist(
            '127.0.0.1', 
            limit=10,
            whitelist=whitelist_ips
        )
        
        assert is_allowed is True
        # Redisは呼ばれない（チェックしない）
        mock_redis.get.assert_not_called()
    
    @patch('modules.rate_limit.redis_client')
    def test_通常IPは制限される(self, mock_redis):
        """通常のIPは制限が適用される"""
        whitelist_ips = ['127.0.0.1']
        mock_redis.get.return_value = b'10'
        
        # 通常のIP
        is_allowed = rate_limit.check_rate_limit_with_whitelist(
            '192.168.1.1',
            limit=10,
            whitelist=whitelist_ips
        )
        
        assert is_allowed is False


class TestRateLimitDecorator:
    """レート制限デコレーターのテスト"""
    
    @patch('modules.rate_limit.redis_client')
    def test_デコレーターでレート制限適用(self, mock_redis, client):
        """@rate_limit デコレーターが機能する"""
        from modules.rate_limit import rate_limit_decorator
        
        mock_redis.get.return_value = None
        mock_redis.incr.return_value = 1
        
        @rate_limit_decorator(limit=10, window=60)
        def test_endpoint():
            return "Success"
        
        result = test_endpoint()
        assert result == "Success"
    
    @patch('modules.rate_limit.redis_client')
    def test_制限超過でHTTPエラー(self, mock_redis):
        """制限超過時に429エラーが返される"""
        from modules.rate_limit import rate_limit_decorator
        
        mock_redis.get.return_value = b'10'  # 制限超過
        
        @rate_limit_decorator(limit=10, window=60)
        def test_endpoint():
            return "Success"
        
        with pytest.raises(Exception) as exc_info:
            test_endpoint()
        
        # 429 Too Many Requests エラー
        assert "rate limit" in str(exc_info.value).lower()


# テスト実行時の設定
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

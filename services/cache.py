import datetime
from config import Config

class CacheManager:
    """キャッシュ管理クラス"""
    
    def __init__(self):
        self.cache_data = {
            'temples': {'data': None, 'timestamp': 0},
            'fields': {'data': None, 'timestamp': 0}
        }
    
    def is_cache_valid(self, cache_key):
        """キャッシュが有効か確認"""
        if cache_key not in self.cache_data:
            return False
        if self.cache_data[cache_key]['data'] is None:
            return False
        elapsed = datetime.datetime.now().timestamp() - self.cache_data[cache_key]['timestamp']
        return elapsed < Config.CACHE_TIMEOUT
    
    def get_cached_or_fetch(self, cache_key, fetch_function):
        """キャッシュから取得、期限切れなら再取得"""
        if self.is_cache_valid(cache_key):
            print(f"✅ キャッシュから取得: {cache_key}")
            return self.cache_data[cache_key]['data']
        
        try:
            data = fetch_function()
            self.cache_data[cache_key]['data'] = data
            self.cache_data[cache_key]['timestamp'] = datetime.datetime.now().timestamp()
            print(f"✅ データ取得成功: {cache_key}")
            return data
        except Exception as e:
            print(f"❌ データ取得失敗: {cache_key} - {e}")
            # キャッシュがあれば古いデータでも返す
            if cache_key in self.cache_data and self.cache_data[cache_key]['data'] is not None:
                print(f"⚠️ 古いキャッシュを返却: {cache_key}")
                return self.cache_data[cache_key]['data']
            raise e
    
    def clear_cache(self, cache_key=None):
        """キャッシュをクリア"""
        if cache_key:
            if cache_key in self.cache_data:
                self.cache_data[cache_key]['data'] = None
                self.cache_data[cache_key]['timestamp'] = 0
        else:
            for key in self.cache_data:
                self.cache_data[key]['data'] = None
                self.cache_data[key]['timestamp'] = 0
    
    def clear_all(self):
        """全キャッシュをクリア（別名）"""
        self.clear_cache()

# グローバルインスタンス
cache_manager = CacheManager()

# エクスポート
__all__ = ['CacheManager', 'cache_manager']
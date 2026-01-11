"""
Flask拡張とグローバルオブジェクト
アプリケーション全体で共有するオブジェクトを管理
"""
import json
import os
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google import genai

import config

# === Google Sheets クライアント ===
_gc = None


def get_spreadsheet_client():
    """Google Sheets クライアントを取得（シングルトン）"""
    global _gc
    if _gc is None:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if creds_json_str:
            creds_dict = json.loads(creds_json_str)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        _gc = gspread.authorize(creds)
    return _gc


# === Gemini AI クライアント ===
gemini_client = None
if config.GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)


# === キャッシュ管理 ===
class CacheManager:
    """シンプルなインメモリキャッシュ"""
    
    def __init__(self, timeout=300):
        self.timeout = timeout
        self._cache = {}
    
    def get(self, key):
        """キャッシュから取得"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        elapsed = datetime.datetime.now().timestamp() - entry['timestamp']
        
        if elapsed >= self.timeout:
            return None
        
        return entry['data']
    
    def set(self, key, data):
        """キャッシュに保存"""
        self._cache[key] = {
            'data': data,
            'timestamp': datetime.datetime.now().timestamp()
        }
    
    def clear(self, key=None):
        """キャッシュをクリア"""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
    
    def get_or_fetch(self, key, fetch_func):
        """キャッシュから取得、なければ関数を実行して保存"""
        cached = self.get(key)
        if cached is not None:
            print(f"✅ キャッシュから取得: {key}")
            return cached
        
        try:
            data = fetch_func()
            self.set(key, data)
            print(f"✅ データ取得成功: {key}")
            return data
        except Exception as e:
            print(f"❌ データ取得失敗: {key} - {e}")
            # 古いキャッシュがあれば返す
            if key in self._cache:
                print(f"⚠️ 古いキャッシュを返却: {key}")
                return self._cache[key]['data']
            raise e


# グローバルキャッシュインスタンス
cache = CacheManager(timeout=config.CACHE_TIMEOUT_SECONDS)


# === ログイン試行管理 ===
login_attempts = {}
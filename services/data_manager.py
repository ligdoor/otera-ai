"""
データ管理モジュール

Supabaseのデータ取得を統一的に管理します。
キャッシュ機能も統合しています。
"""

import logging
from config import Config

logger = logging.getLogger(__name__)


class DataManager:
    """データ管理クラス"""
    
    def __init__(self):
        self.use_supabase = Config.USE_SUPABASE
        self._internal_cache = {}  # 簡易内部キャッシュ
    
    def get_all_temples(self):
        """
        全寺院データを取得（キャッシュ付き）
        
        Returns:
            dict: 寺院名をキーとした辞書
        """
        # 簡易キャッシュをチェック
        if 'all_temples' in self._internal_cache:
            logger.info("✅ 内部キャッシュから取得: temples")
            return self._internal_cache['all_temples']
        
        if self.use_supabase:
            from services import database as supabase_db
            
            # データベースから取得
            logger.info("✅ データベースから取得: temples")
            temples = supabase_db.get_all_temples()
            
            # 内部キャッシュに保存
            self._internal_cache['all_temples'] = temples
            
            return temples
        else:
            from services.spreadsheet import get_all_data
            data = get_all_data()
            self._internal_cache['all_temples'] = data
            return data
    
    def get_temple_by_name(self, name):
        """
        寺院名で検索
        
        Args:
            name: 寺院名
        
        Returns:
            dict: 寺院データ（存在しない場合はNone）
        """
        temples = self.get_all_temples()
        
        # 辞書かリストか判定
        if isinstance(temples, dict):
            return temples.get(name)
        else:
            # リストの場合
            for temple in temples:
                if temple.get('name') == name:
                    return temple
            return None
    
    def create_temple(self, temple_data):
        """
        寺院を追加
        
        Args:
            temple_data: 寺院データ
        
        Returns:
            dict: 作成された寺院データ
        """
        if self.use_supabase:
            from services import database as supabase_db
            result = supabase_db.create_temple(temple_data)
            # キャッシュをクリア
            self.clear_cache()
            return result
        else:
            raise NotImplementedError("Google Sheets版は未実装")
    
    def update_temple(self, name, temple_data):
        """
        寺院データを更新
        
        Args:
            name: 寺院名
            temple_data: 更新データ
        
        Returns:
            dict: 更新された寺院データ
        """
        if self.use_supabase:
            from services import database as supabase_db
            result = supabase_db.update_temple(name, temple_data)
            # キャッシュをクリア
            self.clear_cache()
            return result
        else:
            raise NotImplementedError("Google Sheets版は未実装")
    
    def delete_temple(self, name):
        """
        寺院を削除
        
        Args:
            name: 寺院名
        
        Returns:
            bool: 削除成功した場合True
        """
        if self.use_supabase:
            from services import database as supabase_db
            result = supabase_db.delete_temple(name)
            # キャッシュをクリア
            self.clear_cache()
            return result
        else:
            raise NotImplementedError("Google Sheets版は未実装")
    
    def reload_from_db(self):
        """データベースからデータを再読み込み"""
        self.clear_cache()
        return self.get_all_temples()
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self._internal_cache.clear()
        logger.info("✅ DataManagerキャッシュをクリア")
    
    def clear_all(self):
        """全キャッシュをクリア（別名）"""
        self.clear_cache()

# グローバルインスタンス
data_manager = DataManager()

# エクスポート
__all__ = ['DataManager', 'data_manager']
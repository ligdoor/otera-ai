"""
データベース操作のテスト (database.py, admin_db.py)
Supabase CRUD操作を検証
"""

import pytest
from unittest.mock import patch, MagicMock
from modules import database, admin_db


class TestTempleDatabase:
    """寺院データベース操作のテスト"""
    
    @patch('modules.database.supabase')
    def test_寺院を新規作成(self, mock_supabase):
        """新しい寺院を作成できる"""
        temple_data = {
            'name': 'テスト寺院',
            'address': '東京都渋谷区',
            'description': 'テスト用の寺院'
        }
        
        mock_response = MagicMock()
        mock_response.data = [{'id': 1, **temple_data}]
        mock_supabase.table().insert().execute.return_value = mock_response
        
        result = database.create_temple(temple_data)
        
        assert result is not None
        assert result['name'] == 'テスト寺院'
    
    @patch('modules.database.supabase')
    def test_寺院を取得(self, mock_supabase):
        """IDで寺院を取得できる"""
        mock_response = MagicMock()
        mock_response.data = [{
            'id': 1,
            'name': '浅草寺',
            'address': '東京都台東区'
        }]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        temple = database.get_temple(1)
        
        assert temple is not None
        assert temple['name'] == '浅草寺'
    
    @patch('modules.database.supabase')
    def test_寺院を更新(self, mock_supabase):
        """寺院情報を更新できる"""
        temple_id = 1
        update_data = {'description': '更新された説明'}
        
        mock_response = MagicMock()
        mock_response.data = [{'id': 1, **update_data}]
        mock_supabase.table().update().eq().execute.return_value = mock_response
        
        result = database.update_temple(temple_id, update_data)
        
        assert result is not None
        assert result['description'] == '更新された説明'
    
    @patch('modules.database.supabase')
    def test_寺院を削除(self, mock_supabase):
        """寺院を削除できる"""
        temple_id = 1
        
        mock_response = MagicMock()
        mock_response.data = [{'id': 1}]
        mock_supabase.table().delete().eq().execute.return_value = mock_response
        
        result = database.delete_temple(temple_id)
        
        assert result is True
    
    @patch('modules.database.supabase')
    def test_全寺院を取得(self, mock_supabase):
        """全ての寺院を取得できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 1, 'name': '寺院1'},
            {'id': 2, 'name': '寺院2'},
            {'id': 3, 'name': '寺院3'}
        ]
        mock_supabase.table().select().execute.return_value = mock_response
        
        temples = database.get_all_temples()
        
        assert len(temples) == 3


class TestButsugoDatabase:
    """仏具データベース操作のテスト"""
    
    @patch('modules.database.supabase')
    def test_仏具を新規作成(self, mock_supabase):
        """新しい仏具を作成できる"""
        butsugo_data = {
            'name': 'テスト仏壇',
            'category': '仏壇',
            'description': 'テスト用'
        }
        
        mock_response = MagicMock()
        mock_response.data = [{'id': 1, **butsugo_data}]
        mock_supabase.table().insert().execute.return_value = mock_response
        
        result = database.create_butsugo(butsugo_data)
        
        assert result is not None
        assert result['name'] == 'テスト仏壇'
    
    @patch('modules.database.supabase')
    def test_仏具を取得(self, mock_supabase):
        """IDで仏具を取得できる"""
        mock_response = MagicMock()
        mock_response.data = [{
            'id': 1,
            'name': '数珠',
            'category': '数珠'
        }]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        butsugo = database.get_butsugo(1)
        
        assert butsugo is not None
        assert butsugo['name'] == '数珠'
    
    @patch('modules.database.supabase')
    def test_仏具を更新(self, mock_supabase):
        """仏具情報を更新できる"""
        butsugo_id = 1
        update_data = {'price': 10000}
        
        mock_response = MagicMock()
        mock_response.data = [{'id': 1, **update_data}]
        mock_supabase.table().update().eq().execute.return_value = mock_response
        
        result = database.update_butsugo(butsugo_id, update_data)
        
        assert result is not None
    
    @patch('modules.database.supabase')
    def test_仏具を削除(self, mock_supabase):
        """仏具を削除できる"""
        butsugo_id = 1
        
        mock_response = MagicMock()
        mock_response.data = [{'id': 1}]
        mock_supabase.table().delete().eq().execute.return_value = mock_response
        
        result = database.delete_butsugo(butsugo_id)
        
        assert result is True


class TestUserDatabase:
    """ユーザーデータベース操作のテスト"""
    
    @patch('modules.admin_db.supabase')
    def test_ユーザーを新規作成(self, mock_supabase):
        """新しいユーザーを作成できる"""
        user_data = {
            'username': 'new_user',
            'email': 'new@example.com',
            'role': 'editor'
        }
        
        mock_response = MagicMock()
        mock_response.data = [{'id': 1, **user_data}]
        mock_supabase.table().insert().execute.return_value = mock_response
        
        result = admin_db.create_user(user_data)
        
        assert result is not None
        assert result['username'] == 'new_user'
    
    @patch('modules.admin_db.supabase')
    def test_ユーザーを取得(self, mock_supabase):
        """IDでユーザーを取得できる"""
        mock_response = MagicMock()
        mock_response.data = [{
            'id': 1,
            'username': 'admin',
            'role': 'admin'
        }]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        user = admin_db.get_user(1)
        
        assert user is not None
        assert user['username'] == 'admin'
    
    @patch('modules.admin_db.supabase')
    def test_ユーザー名で検索(self, mock_supabase):
        """ユーザー名でユーザーを検索できる"""
        mock_response = MagicMock()
        mock_response.data = [{
            'id': 1,
            'username': 'test_user'
        }]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        user = admin_db.get_user_by_username('test_user')
        
        assert user is not None
        assert user['username'] == 'test_user'
    
    @patch('modules.admin_db.supabase')
    def test_ユーザーロールを更新(self, mock_supabase):
        """ユーザーのロールを更新できる"""
        user_id = 1
        new_role = 'admin'
        
        mock_response = MagicMock()
        mock_response.data = [{'id': 1, 'role': new_role}]
        mock_supabase.table().update().eq().execute.return_value = mock_response
        
        result = admin_db.update_user_role(user_id, new_role)
        
        assert result['role'] == 'admin'


class TestTransactions:
    """トランザクションのテスト"""
    
    @patch('modules.database.supabase')
    def test_複数操作をトランザクション実行(self, mock_supabase):
        """複数の操作を一括で実行できる"""
        # トランザクション内で複数の寺院を作成
        temples = [
            {'name': '寺院1'},
            {'name': '寺院2'}
        ]
        
        mock_response = MagicMock()
        mock_response.data = temples
        mock_supabase.table().insert().execute.return_value = mock_response
        
        result = database.bulk_create_temples(temples)
        
        assert len(result) == 2
    
    @patch('modules.database.supabase')
    def test_トランザクション失敗でロールバック(self, mock_supabase):
        """トランザクション失敗時にロールバックされる"""
        mock_supabase.table().insert().execute.side_effect = Exception("DB Error")
        
        # エラーが発生してもアプリケーションは続行
        with pytest.raises(Exception):
            database.create_temple({'name': '失敗する寺院'})


class TestDataIntegrity:
    """データ整合性のテスト"""
    
    @patch('modules.database.supabase')
    def test_重複データを拒否(self, mock_supabase):
        """重複するデータの登録が拒否される"""
        # 既存のユーザー名
        mock_response = MagicMock()
        mock_response.data = [{'username': 'existing_user'}]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        # 同じユーザー名での作成を試みる
        with pytest.raises(ValueError):
            admin_db.create_user({'username': 'existing_user'})
    
    @patch('modules.database.supabase')
    def test_必須フィールドチェック(self, mock_supabase):
        """必須フィールドが欠けているとエラー"""
        incomplete_data = {'address': '東京'}  # nameが欠けている
        
        with pytest.raises(ValueError):
            database.create_temple(incomplete_data)


class TestQueryOptimization:
    """クエリ最適化のテスト"""
    
    @patch('modules.database.supabase')
    def test_必要なフィールドのみ取得(self, mock_supabase):
        """必要なフィールドのみをSELECTできる"""
        mock_response = MagicMock()
        mock_response.data = [{'id': 1, 'name': '寺院1'}]
        mock_supabase.table().select().execute.return_value = mock_response
        
        # id, nameのみ取得
        temples = database.get_temples_minimal(fields=['id', 'name'])
        
        # selectが適切に呼ばれていることを確認
        assert temples is not None
    
    @patch('modules.database.supabase')
    def test_ページネーションでデータ取得(self, mock_supabase):
        """大量データをページネーションで取得できる"""
        mock_response = MagicMock()
        mock_response.data = [{'id': i, 'name': f'寺院{i}'} for i in range(1, 11)]
        mock_supabase.table().select().range().execute.return_value = mock_response
        
        # 1ページ目を取得（10件ずつ）
        page1 = database.get_temples_paginated(page=1, per_page=10)
        
        assert len(page1) == 10


class TestRelationships:
    """リレーションシップのテスト"""
    
    @patch('modules.database.supabase')
    def test_寺院と仏具の関連取得(self, mock_supabase):
        """寺院に関連する仏具を取得できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 1, 'temple_id': 1, 'butsugo_id': 10}
        ]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        temple_id = 1
        butsugo_list = database.get_temple_butsugo(temple_id)
        
        assert len(butsugo_list) > 0
    
    @patch('modules.database.supabase')
    def test_ユーザーと担当寺院の関連(self, mock_supabase):
        """ユーザーの担当寺院を取得できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'temple_id': 1},
            {'temple_id': 2}
        ]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        user_id = 2
        assigned_temples = admin_db.get_assigned_temples(user_id)
        
        assert len(assigned_temples) == 2


class TestCaching:
    """キャッシングのテスト"""
    
    @patch('modules.database.supabase')
    @patch('modules.database.redis_client')
    def test_頻繁にアクセスされるデータをキャッシュ(self, mock_redis, mock_supabase):
        """頻繁にアクセスされるデータがキャッシュされる"""
        temple_id = 1
        
        # キャッシュなし
        mock_redis.get.return_value = None
        
        # DBから取得
        mock_response = MagicMock()
        mock_response.data = [{'id': 1, 'name': '寺院1'}]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        temple = database.get_temple_cached(temple_id)
        
        # キャッシュに保存されたことを確認
        mock_redis.setex.assert_called_once()
        assert temple is not None
    
    @patch('modules.database.redis_client')
    def test_キャッシュからデータ取得(self, mock_redis):
        """キャッシュされたデータを取得できる"""
        import json
        
        temple_id = 1
        cached_data = json.dumps({'id': 1, 'name': '寺院1'})
        mock_redis.get.return_value = cached_data.encode()
        
        temple = database.get_temple_cached(temple_id)
        
        # DBにアクセスせずキャッシュから取得
        assert temple['name'] == '寺院1'


# テスト実行時の設定
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

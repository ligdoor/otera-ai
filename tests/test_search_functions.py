"""
検索機能のテスト (search_functions.py)
寺院検索、仏具検索、五十音検索の機能を検証
"""

import pytest
from unittest.mock import patch, MagicMock
from modules import search_functions


class TestTempleSearch:
    """寺院検索のテスト"""
    
    @patch('modules.search_functions.supabase')
    def test_キーワードで寺院検索(self, mock_supabase):
        """キーワードで寺院が検索できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 1, 'name': '浅草寺', 'address': '東京都台東区'},
            {'id': 2, 'name': '浅草神社', 'address': '東京都台東区'}
        ]
        mock_supabase.table().select().ilike().execute.return_value = mock_response
        
        results = search_functions.search_temples('浅草')
        
        assert len(results) == 2
        assert results[0]['name'] == '浅草寺'
    
    @patch('modules.search_functions.supabase')
    def test_住所で寺院検索(self, mock_supabase):
        """住所で寺院が検索できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 1, 'name': 'テスト寺', 'address': '東京都渋谷区'}
        ]
        mock_supabase.table().select().ilike().execute.return_value = mock_response
        
        results = search_functions.search_temples('渋谷区')
        
        assert len(results) == 1
        assert '渋谷区' in results[0]['address']
    
    @patch('modules.search_functions.supabase')
    def test_空のキーワードで全件取得(self, mock_supabase):
        """空のキーワードだと空リストを返す"""
        results = search_functions.search_temples('')
        
        assert results == []
    
    @patch('modules.search_functions.supabase')
    def test_検索結果が0件(self, mock_supabase):
        """該当する寺院がない場合空リストを返す"""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table().select().ilike().execute.return_value = mock_response
        
        results = search_functions.search_temples('存在しない寺')
        
        assert results == []
    
    @patch('modules.search_functions.supabase')
    def test_部分一致で検索(self, mock_supabase):
        """部分一致で検索できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 1, 'name': '金閣寺'},
            {'id': 2, 'name': '銀閣寺'}
        ]
        mock_supabase.table().select().ilike().execute.return_value = mock_response
        
        results = search_functions.search_temples('閣寺')
        
        assert len(results) == 2


class TestButsugoSearch:
    """仏具検索のテスト"""
    
    @patch('modules.search_functions.supabase')
    def test_仏具名で検索(self, mock_supabase):
        """仏具名で検索できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 1, 'name': '仏壇', 'category': '仏壇'},
            {'id': 2, 'name': '仏像', 'category': '仏像'}
        ]
        mock_supabase.table().select().ilike().execute.return_value = mock_response
        
        results = search_functions.search_butsugo('仏')
        
        assert len(results) == 2
    
    @patch('modules.search_functions.supabase')
    def test_カテゴリで検索(self, mock_supabase):
        """カテゴリで仏具を検索できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 1, 'name': '数珠A', 'category': '数珠'},
            {'id': 2, 'name': '数珠B', 'category': '数珠'}
        ]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        results = search_functions.search_butsugo_by_category('数珠')
        
        assert len(results) == 2
        assert all(item['category'] == '数珠' for item in results)


class TestKanaSearch:
    """五十音検索のテスト"""
    
    @patch('modules.search_functions.supabase')
    def test_あ行で検索(self, mock_supabase):
        """「あ行」で始まる仏具を検索できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 1, 'name': 'あかり', 'reading': 'あかり'},
            {'id': 2, 'name': '位牌', 'reading': 'いはい'}
        ]
        mock_supabase.table().select().execute.return_value = mock_response
        
        results = search_functions.search_by_kana_group('あ')
        
        assert len(results) == 2
    
    @patch('modules.search_functions.supabase')
    def test_か行で検索(self, mock_supabase):
        """「か行」で始まる仏具を検索できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 1, 'name': '香炉', 'reading': 'こうろ'},
            {'id': 2, 'name': '経本', 'reading': 'きょうほん'}
        ]
        mock_supabase.table().select().execute.return_value = mock_response
        
        results = search_functions.search_by_kana_group('か')
        
        assert len(results) == 2
    
    def test_五十音グループの判定(self):
        """文字が正しい五十音グループに属するか判定できる"""
        assert search_functions.get_kana_group('あ') == 'あ'
        assert search_functions.get_kana_group('か') == 'か'
        assert search_functions.get_kana_group('さ') == 'さ'
        assert search_functions.get_kana_group('た') == 'た'
        assert search_functions.get_kana_group('な') == 'な'
    
    def test_濁音も同じグループ(self):
        """濁音も同じグループに属する"""
        assert search_functions.get_kana_group('が') == 'か'
        assert search_functions.get_kana_group('ざ') == 'さ'
        assert search_functions.get_kana_group('だ') == 'た'


class TestSearchSorting:
    """検索結果の並び替えのテスト"""
    
    @patch('modules.search_functions.supabase')
    def test_名前順で並び替え(self, mock_supabase):
        """検索結果を名前順で並び替えできる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 1, 'name': 'あ寺院'},
            {'id': 2, 'name': 'か寺院'},
            {'id': 3, 'name': 'さ寺院'}
        ]
        mock_supabase.table().select().order().execute.return_value = mock_response
        
        results = search_functions.search_temples_sorted('', sort_by='name')
        
        # 名前順になっているか確認
        assert results[0]['name'] < results[1]['name'] < results[2]['name']
    
    @patch('modules.search_functions.supabase')
    def test_作成日順で並び替え(self, mock_supabase):
        """検索結果を作成日順で並び替えできる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 3, 'name': '新しい寺', 'created_at': '2024-03-01'},
            {'id': 2, 'name': '中間寺', 'created_at': '2024-02-01'},
            {'id': 1, 'name': '古い寺', 'created_at': '2024-01-01'}
        ]
        mock_supabase.table().select().order().execute.return_value = mock_response
        
        results = search_functions.search_temples_sorted('', sort_by='created_at', order='desc')
        
        # 新しい順になっているか確認
        assert results[0]['id'] == 3


class TestSearchPagination:
    """検索結果のページネーションのテスト"""
    
    @patch('modules.search_functions.supabase')
    def test_ページネーション(self, mock_supabase):
        """検索結果がページネーションされる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': i, 'name': f'寺院{i}'} for i in range(1, 11)
        ]
        mock_supabase.table().select().range().execute.return_value = mock_response
        
        # 1ページ目（10件）
        results = search_functions.search_temples_paginated('', page=1, per_page=10)
        
        assert len(results) == 10
    
    @patch('modules.search_functions.supabase')
    def test_2ページ目を取得(self, mock_supabase):
        """2ページ目の検索結果を取得できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': i, 'name': f'寺院{i}'} for i in range(11, 21)
        ]
        mock_supabase.table().select().range().execute.return_value = mock_response
        
        # 2ページ目
        results = search_functions.search_temples_paginated('', page=2, per_page=10)
        
        assert results[0]['id'] == 11


class TestSearchFilter:
    """検索フィルターのテスト"""
    
    @patch('modules.search_functions.supabase')
    def test_地域でフィルター(self, mock_supabase):
        """地域でフィルターできる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 1, 'name': '東京寺', 'address': '東京都渋谷区'}
        ]
        mock_supabase.table().select().ilike().execute.return_value = mock_response
        
        results = search_functions.search_temples_by_region('東京')
        
        assert len(results) == 1
        assert '東京' in results[0]['address']
    
    @patch('modules.search_functions.supabase')
    def test_複数条件でフィルター(self, mock_supabase):
        """複数の条件でフィルターできる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 1, 'name': '浄土寺', 'address': '京都府', 'sect': '浄土宗'}
        ]
        mock_supabase.table().select().ilike().eq().execute.return_value = mock_response
        
        results = search_functions.search_temples_advanced(
            region='京都',
            sect='浄土宗'
        )
        
        assert len(results) == 1
        assert results[0]['sect'] == '浄土宗'


class TestSearchSuggestion:
    """検索候補のテスト"""
    
    @patch('modules.search_functions.supabase')
    def test_検索候補を取得(self, mock_supabase):
        """入力中の文字から検索候補を取得できる"""
        mock_response = MagicMock()
        mock_response.data = [
            {'name': '浅草寺'},
            {'name': '浅草神社'}
        ]
        mock_supabase.table().select().ilike().limit().execute.return_value = mock_response
        
        suggestions = search_functions.get_search_suggestions('浅')
        
        assert len(suggestions) == 2
        assert all('浅' in s['name'] for s in suggestions)
    
    @patch('modules.search_functions.supabase')
    def test_候補は最大10件(self, mock_supabase):
        """検索候補は最大10件まで"""
        mock_response = MagicMock()
        mock_response.data = [
            {'name': f'寺{i}'} for i in range(20)
        ]
        mock_supabase.table().select().ilike().limit().execute.return_value = mock_response
        
        suggestions = search_functions.get_search_suggestions('寺')
        
        # 最大10件に制限される
        assert len(suggestions) <= 10


# テスト実行時の設定
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

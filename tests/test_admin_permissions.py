"""
権限管理のテスト (admin_permissions.py)
管理者・編集者・閲覧者の権限チェック機能を検証
"""

import pytest
from unittest.mock import patch, MagicMock
from modules import admin_permissions


class TestPermissionCheck:
    """権限チェックのテスト"""
    
    def test_管理者は全ての権限を持つ(self):
        """管理者は全ての操作が可能"""
        user = {'role': 'admin', 'id': 1}
        
        assert admin_permissions.can_view(user) is True
        assert admin_permissions.can_edit(user) is True
        assert admin_permissions.can_delete(user) is True
        assert admin_permissions.can_create(user) is True
        assert admin_permissions.can_manage_users(user) is True
    
    def test_編集者は閲覧と編集が可能(self):
        """編集者は閲覧・編集・作成が可能、削除とユーザー管理は不可"""
        user = {'role': 'editor', 'id': 2}
        
        assert admin_permissions.can_view(user) is True
        assert admin_permissions.can_edit(user) is True
        assert admin_permissions.can_create(user) is True
        assert admin_permissions.can_delete(user) is False
        assert admin_permissions.can_manage_users(user) is False
    
    def test_閲覧者は閲覧のみ可能(self):
        """閲覧者は閲覧のみ可能"""
        user = {'role': 'viewer', 'id': 3}
        
        assert admin_permissions.can_view(user) is True
        assert admin_permissions.can_edit(user) is False
        assert admin_permissions.can_create(user) is False
        assert admin_permissions.can_delete(user) is False
        assert admin_permissions.can_manage_users(user) is False
    
    def test_不明なロールは全て拒否(self):
        """不明なロールは全ての権限が拒否される"""
        user = {'role': 'unknown', 'id': 4}
        
        assert admin_permissions.can_view(user) is False
        assert admin_permissions.can_edit(user) is False
        assert admin_permissions.can_delete(user) is False


class TestTemplePermissions:
    """寺院に対する権限のテスト"""
    
    @patch('modules.admin_permissions.supabase')
    def test_管理者は全ての寺院を編集可能(self, mock_supabase):
        """管理者はどの寺院でも編集できる"""
        user = {'role': 'admin', 'id': 1}
        temple_id = 123
        
        can_edit = admin_permissions.can_edit_temple(user, temple_id)
        
        assert can_edit is True
    
    @patch('modules.admin_permissions.supabase')
    def test_編集者は担当寺院のみ編集可能(self, mock_supabase):
        """編集者は自分が担当している寺院のみ編集できる"""
        user = {'role': 'editor', 'id': 2}
        temple_id = 456
        
        # 担当寺院のモックデータ
        mock_response = MagicMock()
        mock_response.data = [{'temple_id': 456}]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        can_edit = admin_permissions.can_edit_temple(user, temple_id)
        
        assert can_edit is True
    
    @patch('modules.admin_permissions.supabase')
    def test_編集者は担当外の寺院を編集不可(self, mock_supabase):
        """編集者は担当していない寺院は編集できない"""
        user = {'role': 'editor', 'id': 2}
        temple_id = 999
        
        # 担当寺院のモックデータ（999は含まれない）
        mock_response = MagicMock()
        mock_response.data = [{'temple_id': 456}]
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        can_edit = admin_permissions.can_edit_temple(user, temple_id)
        
        assert can_edit is False
    
    @patch('modules.admin_permissions.supabase')
    def test_閲覧者は寺院を編集不可(self, mock_supabase):
        """閲覧者はどの寺院も編集できない"""
        user = {'role': 'viewer', 'id': 3}
        temple_id = 123
        
        can_edit = admin_permissions.can_edit_temple(user, temple_id)
        
        assert can_edit is False


class TestButsugoPermissions:
    """仏具に対する権限のテスト"""
    
    def test_管理者は仏具を管理可能(self):
        """管理者は仏具の追加・編集・削除が可能"""
        user = {'role': 'admin', 'id': 1}
        
        assert admin_permissions.can_add_butsugo(user) is True
        assert admin_permissions.can_edit_butsugo(user) is True
        assert admin_permissions.can_delete_butsugo(user) is True
    
    def test_編集者は仏具を管理可能(self):
        """編集者は仏具の追加・編集が可能、削除は不可"""
        user = {'role': 'editor', 'id': 2}
        
        assert admin_permissions.can_add_butsugo(user) is True
        assert admin_permissions.can_edit_butsugo(user) is True
        assert admin_permissions.can_delete_butsugo(user) is False
    
    def test_閲覧者は仏具を管理不可(self):
        """閲覧者は仏具の管理ができない"""
        user = {'role': 'viewer', 'id': 3}
        
        assert admin_permissions.can_add_butsugo(user) is False
        assert admin_permissions.can_edit_butsugo(user) is False
        assert admin_permissions.can_delete_butsugo(user) is False


class TestUserManagementPermissions:
    """ユーザー管理権限のテスト"""
    
    def test_管理者はユーザー管理可能(self):
        """管理者はユーザーの追加・編集・削除が可能"""
        user = {'role': 'admin', 'id': 1}
        
        assert admin_permissions.can_add_user(user) is True
        assert admin_permissions.can_edit_user(user) is True
        assert admin_permissions.can_delete_user(user) is True
    
    def test_編集者はユーザー管理不可(self):
        """編集者はユーザー管理ができない"""
        user = {'role': 'editor', 'id': 2}
        
        assert admin_permissions.can_add_user(user) is False
        assert admin_permissions.can_edit_user(user) is False
        assert admin_permissions.can_delete_user(user) is False
    
    def test_閲覧者はユーザー管理不可(self):
        """閲覧者はユーザー管理ができない"""
        user = {'role': 'viewer', 'id': 3}
        
        assert admin_permissions.can_add_user(user) is False
        assert admin_permissions.can_edit_user(user) is False
        assert admin_permissions.can_delete_user(user) is False
    
    def test_自分自身のプロフィールは編集可能(self):
        """どのロールでも自分自身のプロフィールは編集できる"""
        editor = {'role': 'editor', 'id': 2}
        viewer = {'role': 'viewer', 'id': 3}
        
        assert admin_permissions.can_edit_own_profile(editor, user_id=2) is True
        assert admin_permissions.can_edit_own_profile(viewer, user_id=3) is True
        
        # 他人のプロフィールは編集不可
        assert admin_permissions.can_edit_own_profile(editor, user_id=999) is False


class TestPermissionDecorator:
    """権限チェックデコレーターのテスト"""
    
    def test_権限チェックデコレーターが機能する(self, client, logged_in_session):
        """@require_permission デコレーターが正しく動作する"""
        from modules.admin_permissions import require_permission
        from flask import session
        
        @require_permission('admin')
        def admin_only_function():
            return "Success"
        
        # 管理者でログイン
        with client.session_transaction() as sess:
            sess['role'] = 'admin'
        
        result = admin_only_function()
        assert result == "Success"
    
    def test_権限不足でアクセス拒否(self, client, viewer_session):
        """権限が不足している場合アクセスが拒否される"""
        from modules.admin_permissions import require_permission
        
        @require_permission('admin')
        def admin_only_function():
            return "Success"
        
        # 閲覧者でログイン
        with client.session_transaction() as sess:
            sess['role'] = 'viewer'
        
        with pytest.raises(PermissionError):
            admin_only_function()


class TestRoleHierarchy:
    """ロール階層のテスト"""
    
    def test_ロールの階層が正しい(self):
        """ロールの階層: admin > editor > viewer"""
        assert admin_permissions.get_role_level('admin') > admin_permissions.get_role_level('editor')
        assert admin_permissions.get_role_level('editor') > admin_permissions.get_role_level('viewer')
    
    def test_上位ロールは下位ロールの権限を持つ(self):
        """上位ロールは下位ロールの全ての権限を持つ"""
        admin = {'role': 'admin'}
        editor = {'role': 'editor'}
        
        # 管理者は編集者の権限も持つ
        assert admin_permissions.has_role_or_higher(admin, 'editor') is True
        assert admin_permissions.has_role_or_higher(admin, 'viewer') is True
        
        # 編集者は閲覧者の権限を持つ
        assert admin_permissions.has_role_or_higher(editor, 'viewer') is True
        
        # 逆は不可
        assert admin_permissions.has_role_or_higher(editor, 'admin') is False


# テスト実行時の設定
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

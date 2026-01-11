"""
ユーザーモデル
"""
import bcrypt
from enum import Enum


class UserRole(Enum):
    """ユーザー権限レベル"""
    ADMIN = 'admin'      # 管理者：全機能利用可能
    EDITOR = 'editor'    # 編集者：データ編集可能
    VIEWER = 'viewer'    # 閲覧者：閲覧のみ
    
    @classmethod
    def get_display_name(cls, role_value):
        """
        権限の表示名を取得
        
        Args:
            role_value (str): 権限値
        
        Returns:
            str: 表示名
        """
        display_names = {
            'admin': '🔐 管理者',
            'editor': '✏️ 編集者',
            'viewer': '👁️ 閲覧者'
        }
        return display_names.get(role_value, role_value)
    
    @classmethod
    def get_permissions(cls, role_value):
        """
        権限レベルに応じた許可操作を取得
        
        Args:
            role_value (str): 権限値
        
        Returns:
            dict: 許可操作の辞書
        """
        if role_value == 'admin':
            return {
                'can_view': True,
                'can_edit': True,
                'can_delete': True,
                'can_manage_users': True,
                'can_manage_fields': True,
                'can_export_csv': True,
                'can_import_csv': True
            }
        elif role_value == 'editor':
            return {
                'can_view': True,
                'can_edit': True,
                'can_delete': True,
                'can_manage_users': False,
                'can_manage_fields': False,
                'can_export_csv': True,
                'can_import_csv': True
            }
        else:  # viewer
            return {
                'can_view': True,
                'can_edit': False,
                'can_delete': False,
                'can_manage_users': False,
                'can_manage_fields': False,
                'can_export_csv': True,
                'can_import_csv': False
            }


class User:
    """ユーザークラス"""
    
    def __init__(self, user_id, password_hash, name, role='viewer', created_at='', last_login=''):
        """
        ユーザーを初期化
        
        Args:
            user_id (str): ユーザーID
            password_hash (str): パスワードハッシュ
            name (str): ユーザー名
            role (str): 権限レベル
            created_at (str): 作成日時
            last_login (str): 最終ログイン日時
        """
        self.user_id = user_id
        self.password_hash = password_hash
        self.name = name
        self.role = role
        self.created_at = created_at
        self.last_login = last_login
    
    def verify_password(self, password):
        """
        パスワードを検証
        
        Args:
            password (str): 検証するパスワード
        
        Returns:
            bool: パスワードが一致する場合True
        """
        if self.password_hash.startswith('$2b$'):
            # bcryptハッシュ
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        else:
            # 旧形式（平文）との互換性
            return str(self.password_hash) == password
    
    def set_password(self, password):
        """
        パスワードを設定（ハッシュ化）
        
        Args:
            password (str): 新しいパスワード
        
        Returns:
            str: ハッシュ化されたパスワード
        """
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        return self.password_hash
    
    def has_permission(self, permission):
        """
        特定の権限を持っているか確認
        
        Args:
            permission (str): 権限名（例: 'can_edit'）
        
        Returns:
            bool: 権限を持っている場合True
        """
        permissions = UserRole.get_permissions(self.role)
        return permissions.get(permission, False)
    
    def is_admin(self):
        """管理者かどうか"""
        return self.role == 'admin'
    
    def is_editor(self):
        """編集者かどうか"""
        return self.role == 'editor'
    
    def is_viewer(self):
        """閲覧者かどうか"""
        return self.role == 'viewer'
    
    def can_edit_data(self):
        """データ編集可能か"""
        return self.role in ['admin', 'editor']
    
    def can_manage_users(self):
        """ユーザー管理可能か"""
        return self.role == 'admin'
    
    def to_dict(self, include_password=False):
        """
        辞書形式で取得
        
        Args:
            include_password (bool): パスワードハッシュを含めるか
        
        Returns:
            dict: ユーザーデータ辞書
        """
        data = {
            'user_id': self.user_id,
            'name': self.name,
            'role': self.role,
            'created_at': self.created_at,
            'last_login': self.last_login
        }
        if include_password:
            data['password_hash'] = self.password_hash
        return data
    
    def to_row(self):
        """
        スプレッドシート行データに変換
        
        Returns:
            list: 行データのリスト
        """
        return [
            self.user_id,
            self.password_hash,
            self.name,
            self.role,
            self.created_at,
            self.last_login
        ]
    
    @classmethod
    def from_dict(cls, data_dict):
        """
        辞書からインスタンスを作成
        
        Args:
            data_dict (dict): ユーザーデータ辞書
        
        Returns:
            User: ユーザーインスタンス
        """
        return cls(
            user_id=str(data_dict.get('user_id', '')),
            password_hash=data_dict.get('password_hash', data_dict.get('password', '')),
            name=data_dict.get('name', ''),
            role=data_dict.get('role', 'viewer'),
            created_at=data_dict.get('created_at', ''),
            last_login=data_dict.get('last_login', '')
        )
    
    def __repr__(self):
        return f"<User {self.user_id} ({self.name}, {self.role})>"
    
    def __str__(self):
        return f"{self.name} ({UserRole.get_display_name(self.role)})"


class OperationLog:
    """操作ログクラス"""
    
    def __init__(self, timestamp, user_name, user_id, action, details, ip_address):
        """
        操作ログを初期化
        
        Args:
            timestamp (str): 操作日時
            user_name (str): ユーザー名
            user_id (str): ユーザーID
            action (str): 操作種別
            details (str): 操作詳細
            ip_address (str): IPアドレス
        """
        self.timestamp = timestamp
        self.user_name = user_name
        self.user_id = user_id
        self.action = action
        self.details = details
        self.ip_address = ip_address
    
    def to_dict(self):
        """
        辞書形式で取得
        
        Returns:
            dict: ログデータ辞書
        """
        return {
            'timestamp': self.timestamp,
            'user': self.user_name,
            'user_id': self.user_id,
            'action': self.action,
            'details': self.details,
            'ip': self.ip_address
        }
    
    def to_row(self):
        """
        スプレッドシート行データに変換
        
        Returns:
            list: 行データのリスト
        """
        return [
            self.timestamp,
            self.user_name,
            self.user_id,
            self.action,
            self.details,
            self.ip_address
        ]
    
    @classmethod
    def from_dict(cls, data_dict):
        """
        辞書からインスタンスを作成
        
        Args:
            data_dict (dict): ログデータ辞書
        
        Returns:
            OperationLog: ログインスタンス
        """
        return cls(
            timestamp=data_dict.get('timestamp', ''),
            user_name=data_dict.get('user', ''),
            user_id=data_dict.get('user_id', ''),
            action=data_dict.get('action', ''),
            details=data_dict.get('details', ''),
            ip_address=data_dict.get('ip', '')
        )
    
    def __repr__(self):
        return f"<OperationLog {self.action} by {self.user_name} at {self.timestamp}>"


def validate_password(password):
    """
    パスワードの妥当性をチェック
    
    Args:
        password (str): チェックするパスワード
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if len(password) < 8:
        return False, "パスワードは8文字以上必要です"
    
    if not any(c.isdigit() for c in password):
        return False, "パスワードには数字を含めてください"
    
    if not any(c.isalpha() for c in password):
        return False, "パスワードには英字を含めてください"
    
    return True, ""


def validate_user_id(user_id):
    """
    ユーザーIDの妥当性をチェック
    
    Args:
        user_id (str): チェックするユーザーID
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not user_id or len(user_id.strip()) == 0:
        return False, "ユーザーIDは必須です"
    
    if len(user_id) < 3:
        return False, "ユーザーIDは3文字以上必要です"
    
    # 特殊文字チェック（必要に応じて）
    # if not user_id.replace('_', '').replace('-', '').isalnum():
    #     return False, "ユーザーIDには英数字、アンダースコア、ハイフンのみ使用できます"
    
    return True, ""
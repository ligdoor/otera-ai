"""
寺院データモデル
"""

class Temple:
    """寺院データクラス"""
    
    def __init__(self, data_dict):
        """
        寺院データを初期化
        
        Args:
            data_dict (dict): スプレッドシートから取得した寺院データ辞書
        """
        self.name = data_dict.get('name', '')
        self.sect = data_dict.get('sect', '')
        self.address = data_dict.get('address', '')
        self.transport = data_dict.get('transport', '')
        self._data = data_dict
    
    def get(self, key, default=''):
        """
        項目の値を取得
        
        Args:
            key (str): 項目キー
            default: デフォルト値
        
        Returns:
            項目の値
        """
        return self._data.get(key, default)
    
    def set(self, key, value):
        """
        項目の値を設定
        
        Args:
            key (str): 項目キー
            value: 設定する値
        """
        self._data[key] = value
        if key == 'name':
            self.name = value
        elif key == 'sect':
            self.sect = value
        elif key == 'address':
            self.address = value
        elif key == 'transport':
            self.transport = value
    
    def to_dict(self):
        """
        辞書形式で取得
        
        Returns:
            dict: 寺院データ辞書
        """
        return self._data.copy()
    
    def to_row(self, headers):
        """
        スプレッドシート行データに変換
        
        Args:
            headers (list): ヘッダー行のリスト
        
        Returns:
            list: 行データのリスト
        """
        return [self._data.get(h, '') for h in headers]
    
    def matches_keyword(self, keyword):
        """
        キーワード検索にマッチするか判定
        
        Args:
            keyword (str): 検索キーワード
        
        Returns:
            bool: マッチする場合True
        """
        keyword_lower = keyword.lower()
        searchable = f"{self.name} {self.sect} {self.address}".lower()
        return keyword_lower in searchable
    
    def __repr__(self):
        return f"<Temple {self.name} ({self.sect})>"
    
    def __str__(self):
        return self.name


class TempleField:
    """項目設定クラス"""
    
    def __init__(self, key, label, order):
        """
        項目設定を初期化
        
        Args:
            key (str): 項目キー（内部ID）
            label (str): 項目ラベル（表示名）
            order (int): 表示順序
        """
        self.key = key
        self.label = label
        self.order = order
        self.is_locked = (key == 'name')  # nameは固定項目
    
    def to_dict(self):
        """
        辞書形式で取得
        
        Returns:
            dict: 項目設定辞書
        """
        return {
            'key': self.key,
            'label': self.label,
            'order': self.order
        }
    
    def to_row(self):
        """
        スプレッドシート行データに変換
        
        Returns:
            list: 行データのリスト
        """
        return [self.key, self.label, self.order]
    
    @classmethod
    def from_dict(cls, data_dict):
        """
        辞書からインスタンスを作成
        
        Args:
            data_dict (dict): 項目設定辞書
        
        Returns:
            TempleField: 項目設定インスタンス
        """
        return cls(
            key=data_dict.get('key', ''),
            label=data_dict.get('label', ''),
            order=data_dict.get('order', 0)
        )
    
    def __repr__(self):
        return f"<TempleField {self.key}: {self.label}>"
    
    def __str__(self):
        return f"{self.label} ({self.key})"


class TempleComment:
    """寺院コメント（スタッフメモ）クラス"""
    
    def __init__(self, temple_name, user_name, comment, timestamp):
        """
        コメントを初期化
        
        Args:
            temple_name (str): 寺院名
            user_name (str): 投稿者名
            comment (str): コメント内容
            timestamp (str): 投稿日時
        """
        self.temple_name = temple_name
        self.user_name = user_name
        self.comment = comment
        self.timestamp = timestamp
    
    def to_dict(self):
        """
        辞書形式で取得
        
        Returns:
            dict: コメントデータ辞書
        """
        return {
            'temple_name': self.temple_name,
            'user_name': self.user_name,
            'comment': self.comment,
            'timestamp': self.timestamp
        }
    
    def to_row(self):
        """
        スプレッドシート行データに変換
        
        Returns:
            list: 行データのリスト
        """
        return [self.timestamp, self.temple_name, self.user_name, self.comment]
    
    @classmethod
    def from_dict(cls, data_dict):
        """
        辞書からインスタンスを作成
        
        Args:
            data_dict (dict): コメントデータ辞書
        
        Returns:
            TempleComment: コメントインスタンス
        """
        return cls(
            temple_name=data_dict.get('temple_name', ''),
            user_name=data_dict.get('user_name', ''),
            comment=data_dict.get('comment', ''),
            timestamp=data_dict.get('timestamp', '')
        )
    
    def __repr__(self):
        return f"<TempleComment by {self.user_name} on {self.temple_name}>"


class AccessLog:
    """アクセスログクラス"""
    
    def __init__(self, temple_name, question, timestamp):
        """
        アクセスログを初期化
        
        Args:
            temple_name (str): アクセスされた寺院名
            question (str): 質問内容
            timestamp (str): アクセス日時
        """
        self.temple_name = temple_name
        self.question = question
        self.timestamp = timestamp
    
    def to_row(self):
        """
        スプレッドシート行データに変換
        
        Returns:
            list: 行データのリスト
        """
        return [self.timestamp, self.temple_name, self.question]
    
    @classmethod
    def from_dict(cls, data_dict):
        """
        辞書からインスタンスを作成
        
        Args:
            data_dict (dict): アクセスログ辞書
        
        Returns:
            AccessLog: アクセスログインスタンス
        """
        return cls(
            temple_name=data_dict.get('temple_name', ''),
            question=data_dict.get('question', ''),
            timestamp=data_dict.get('timestamp', '')
        )
    
    def __repr__(self):
        return f"<AccessLog {self.temple_name} at {self.timestamp}>"
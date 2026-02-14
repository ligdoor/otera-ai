"""
バリデーションのテスト (validators.py)
入力値検証、サニタイズ、セキュリティチェックの機能を検証
"""

import pytest
from modules import validators


class TestEmailValidation:
    """メールアドレス検証のテスト"""
    
    def test_有効なメールアドレス(self):
        """正しいフォーマットのメールアドレスが受け入れられる"""
        valid_emails = [
            'test@example.com',
            'user.name@example.co.jp',
            'admin+tag@domain.com',
            'user123@test-domain.com'
        ]
        
        for email in valid_emails:
            assert validators.is_valid_email(email) is True
    
    def test_無効なメールアドレス(self):
        """不正なフォーマットのメールアドレスが拒否される"""
        invalid_emails = [
            'invalid',
            '@example.com',
            'user@',
            'user @example.com',
            'user@exam ple.com',
            'user@@example.com',
            ''
        ]
        
        for email in invalid_emails:
            assert validators.is_valid_email(email) is False


class TestUsernameValidation:
    """ユーザー名検証のテスト"""
    
    def test_有効なユーザー名(self):
        """正しいフォーマットのユーザー名が受け入れられる"""
        valid_usernames = [
            'user123',
            'admin_user',
            'test-user',
            'User2024'
        ]
        
        for username in valid_usernames:
            assert validators.is_valid_username(username) is True
    
    def test_無効なユーザー名(self):
        """不正なフォーマットのユーザー名が拒否される"""
        invalid_usernames = [
            'ab',  # 短すぎる（3文字未満）
            'a' * 51,  # 長すぎる（50文字超）
            'user name',  # スペース含む
            'user@name',  # 特殊文字
            '<script>',  # XSS試行
            '',  # 空
        ]
        
        for username in invalid_usernames:
            assert validators.is_valid_username(username) is False


class TestPasswordValidation:
    """パスワード検証のテスト"""
    
    def test_強固なパスワード(self):
        """十分に強固なパスワードが受け入れられる"""
        strong_passwords = [
            'Password123!',
            'MySecure@Pass2024',
            'Complex#Pass99'
        ]
        
        for password in strong_passwords:
            assert validators.is_strong_password(password) is True
    
    def test_弱いパスワード(self):
        """弱いパスワードが拒否される"""
        weak_passwords = [
            'pass',  # 短すぎる
            'password',  # 数字なし
            '12345678',  # 文字なし
            'Password',  # 数字なし
            'password123',  # 大文字なし
        ]
        
        for password in weak_passwords:
            assert validators.is_strong_password(password) is False
    
    def test_パスワード長チェック(self):
        """パスワードの長さが正しくチェックされる"""
        assert validators.is_valid_password_length('1234567') is False  # 7文字（短い）
        assert validators.is_valid_password_length('12345678') is True  # 8文字（OK）
        assert validators.is_valid_password_length('a' * 100) is True  # 100文字（OK）


class TestInputSanitization:
    """入力サニタイズのテスト"""
    
    def test_XSS対策(self):
        """XSS攻撃を試みる入力がサニタイズされる"""
        dangerous_inputs = [
            '<script>alert("XSS")</script>',
            '<img src=x onerror=alert(1)>',
            'javascript:alert(1)',
            '<iframe src="evil.com"></iframe>'
        ]
        
        for input_text in dangerous_inputs:
            sanitized = validators.sanitize_html(input_text)
            assert '<script>' not in sanitized
            assert '<iframe>' not in sanitized
            assert 'javascript:' not in sanitized
    
    def test_SQL注入対策(self):
        """SQL注入を試みる入力が検出される"""
        sql_injections = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "1; DELETE FROM temples"
        ]
        
        for input_text in sql_injections:
            assert validators.contains_sql_injection(input_text) is True
    
    def test_正常な入力は通過(self):
        """正常な入力はサニタイズされても内容が保たれる"""
        normal_inputs = [
            '普通のテキスト',
            'Normal text with 123',
            'テスト寺院の説明文です。'
        ]
        
        for input_text in normal_inputs:
            sanitized = validators.sanitize_text(input_text)
            assert len(sanitized) > 0


class TestURLValidation:
    """URL検証のテスト"""
    
    def test_有効なURL(self):
        """正しいフォーマットのURLが受け入れられる"""
        valid_urls = [
            'https://example.com',
            'http://test.co.jp',
            'https://sub.domain.com/path',
            'https://example.com/page?param=value'
        ]
        
        for url in valid_urls:
            assert validators.is_valid_url(url) is True
    
    def test_無効なURL(self):
        """不正なフォーマットのURLが拒否される"""
        invalid_urls = [
            'not a url',
            'ftp://example.com',  # httpまたはhttpsのみ許可
            'javascript:alert(1)',
            '//example.com',
            ''
        ]
        
        for url in invalid_urls:
            assert validators.is_valid_url(url) is False


class TestPhoneNumberValidation:
    """電話番号検証のテスト"""
    
    def test_有効な電話番号(self):
        """日本の電話番号フォーマットが受け入れられる"""
        valid_phones = [
            '03-1234-5678',
            '090-1234-5678',
            '0312345678',
            '09012345678'
        ]
        
        for phone in valid_phones:
            assert validators.is_valid_phone(phone) is True
    
    def test_無効な電話番号(self):
        """不正なフォーマットの電話番号が拒否される"""
        invalid_phones = [
            '123',
            'abc-defg-hijk',
            '00-0000-0000',
            ''
        ]
        
        for phone in invalid_phones:
            assert validators.is_valid_phone(phone) is False


class TestPostalCodeValidation:
    """郵便番号検証のテスト"""
    
    def test_有効な郵便番号(self):
        """日本の郵便番号フォーマットが受け入れられる"""
        valid_codes = [
            '100-0001',
            '1000001',
            '123-4567'
        ]
        
        for code in valid_codes:
            assert validators.is_valid_postal_code(code) is True
    
    def test_無効な郵便番号(self):
        """不正なフォーマットの郵便番号が拒否される"""
        invalid_codes = [
            '123',
            '12-3456',
            'abcdefg',
            ''
        ]
        
        for code in invalid_codes:
            assert validators.is_valid_postal_code(code) is False


class TestTextLengthValidation:
    """テキスト長検証のテスト"""
    
    def test_適切な長さのテキスト(self):
        """指定された長さの範囲内のテキストが受け入れられる"""
        text = 'これは適切な長さのテキストです'
        
        assert validators.is_valid_length(text, min_len=5, max_len=50) is True
    
    def test_短すぎるテキスト(self):
        """最小長より短いテキストが拒否される"""
        text = '短い'
        
        assert validators.is_valid_length(text, min_len=10, max_len=50) is False
    
    def test_長すぎるテキスト(self):
        """最大長より長いテキストが拒否される"""
        text = 'あ' * 1000
        
        assert validators.is_valid_length(text, min_len=1, max_len=100) is False


class TestFileValidation:
    """ファイル検証のテスト"""
    
    def test_許可された拡張子(self):
        """許可された拡張子のファイルが受け入れられる"""
        allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
        
        assert validators.is_allowed_file('image.jpg', allowed_extensions) is True
        assert validators.is_allowed_file('photo.png', allowed_extensions) is True
        assert validators.is_allowed_file('pic.webp', allowed_extensions) is True
    
    def test_許可されない拡張子(self):
        """許可されない拡張子のファイルが拒否される"""
        allowed_extensions = ['jpg', 'jpeg', 'png']
        
        assert validators.is_allowed_file('virus.exe', allowed_extensions) is False
        assert validators.is_allowed_file('script.php', allowed_extensions) is False
        assert validators.is_allowed_file('file.gif', allowed_extensions) is False
    
    def test_拡張子の大文字小文字(self):
        """拡張子の大文字小文字が区別されない"""
        allowed_extensions = ['jpg']
        
        assert validators.is_allowed_file('image.JPG', allowed_extensions) is True
        assert validators.is_allowed_file('image.Jpg', allowed_extensions) is True


class TestNumberValidation:
    """数値検証のテスト"""
    
    def test_整数の範囲チェック(self):
        """整数が指定された範囲内かチェックできる"""
        assert validators.is_valid_int_range(50, min_val=1, max_val=100) is True
        assert validators.is_valid_int_range(0, min_val=1, max_val=100) is False
        assert validators.is_valid_int_range(101, min_val=1, max_val=100) is False
    
    def test_正の整数チェック(self):
        """正の整数であることをチェックできる"""
        assert validators.is_positive_int(10) is True
        assert validators.is_positive_int(0) is False
        assert validators.is_positive_int(-5) is False


class TestDateValidation:
    """日付検証のテスト"""
    
    def test_有効な日付フォーマット(self):
        """正しいフォーマットの日付が受け入れられる"""
        valid_dates = [
            '2024-01-01',
            '2024-12-31',
            '2023-06-15'
        ]
        
        for date in valid_dates:
            assert validators.is_valid_date(date, format='%Y-%m-%d') is True
    
    def test_無効な日付フォーマット(self):
        """不正なフォーマットの日付が拒否される"""
        invalid_dates = [
            '2024/01/01',  # スラッシュ区切り
            '01-01-2024',  # 順序が違う
            '2024-13-01',  # 13月は存在しない
            '2024-02-30',  # 2月30日は存在しない
            'invalid'
        ]
        
        for date in invalid_dates:
            assert validators.is_valid_date(date, format='%Y-%m-%d') is False


class TestJapaneseTextValidation:
    """日本語テキスト検証のテスト"""
    
    def test_ひらがな検証(self):
        """ひらがなのみのテキストを検証できる"""
        assert validators.is_hiragana('ひらがな') is True
        assert validators.is_hiragana('カタカナ') is False
        assert validators.is_hiragana('漢字') is False
        assert validators.is_hiragana('English') is False
    
    def test_カタカナ検証(self):
        """カタカナのみのテキストを検証できる"""
        assert validators.is_katakana('カタカナ') is True
        assert validators.is_katakana('ひらがな') is False
        assert validators.is_katakana('漢字') is False
    
    def test_日本語文字列検証(self):
        """日本語が含まれているか検証できる"""
        assert validators.contains_japanese('これは日本語です') is True
        assert validators.contains_japanese('This is English') is False
        assert validators.contains_japanese('日本語 and English') is True


# テスト実行時の設定
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

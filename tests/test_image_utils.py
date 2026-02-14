"""
画像処理のテスト (image_utils.py)
WebP変換、圧縮、リサイズ機能を検証
"""

import pytest
from PIL import Image
import io
from unittest.mock import patch, MagicMock
from modules import image_utils


class TestImageConversion:
    """画像変換のテスト"""
    
    def test_JPEG画像をWebPに変換(self, sample_image):
        """JPEG画像が正しくWebPに変換される"""
        webp_image = image_utils.convert_to_webp(sample_image)
        
        # WebP形式であることを確認
        img = Image.open(webp_image)
        assert img.format == 'WEBP'
    
    def test_PNG画像をWebPに変換(self):
        """PNG画像が正しくWebPに変換される"""
        # PNGテスト画像を作成
        img = Image.new('RGB', (100, 100), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        webp_image = image_utils.convert_to_webp(img_bytes)
        
        img = Image.open(webp_image)
        assert img.format == 'WEBP'
    
    def test_WebP変換で品質80(self, sample_image):
        """WebP変換時の品質が80に設定される"""
        webp_image = image_utils.convert_to_webp(sample_image, quality=80)
        
        # 画像が正しく生成されることを確認
        img = Image.open(webp_image)
        assert img.format == 'WEBP'
    
    def test_WebP変換でファイルサイズ削減(self, sample_image):
        """WebP変換で元のファイルサイズより小さくなる"""
        # 元のサイズ
        original_size = len(sample_image.getvalue())
        sample_image.seek(0)
        
        # WebP変換
        webp_image = image_utils.convert_to_webp(sample_image, quality=80)
        webp_size = len(webp_image.getvalue())
        
        # WebPの方が小さいことを確認（lossy圧縮）
        assert webp_size < original_size


class TestImageResize:
    """画像リサイズのテスト"""
    
    def test_画像を指定サイズにリサイズ(self):
        """画像が指定したサイズにリサイズされる"""
        # 1000x1000の画像を作成
        img = Image.new('RGB', (1000, 1000), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # 500x500にリサイズ
        resized = image_utils.resize_image(img_bytes, max_width=500, max_height=500)
        
        img = Image.open(resized)
        assert img.width <= 500
        assert img.height <= 500
    
    def test_アスペクト比を維持してリサイズ(self):
        """リサイズ時にアスペクト比が維持される"""
        # 1000x500の画像（2:1のアスペクト比）
        img = Image.new('RGB', (1000, 500), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # 600x600にリサイズ指定
        resized = image_utils.resize_image(img_bytes, max_width=600, max_height=600)
        
        img = Image.open(resized)
        # アスペクト比2:1が維持される（600x300になるはず）
        assert img.width == 600
        assert img.height == 300
    
    def test_小さい画像は拡大しない(self):
        """元々小さい画像は拡大しない"""
        # 100x100の画像
        img = Image.new('RGB', (100, 100), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # 500x500にリサイズ指定（拡大はしない）
        resized = image_utils.resize_image(img_bytes, max_width=500, max_height=500)
        
        img = Image.open(resized)
        assert img.width == 100
        assert img.height == 100


class TestImageValidation:
    """画像検証のテスト"""
    
    def test_有効な画像形式を検証(self, sample_image):
        """有効な画像形式（JPEG, PNG, WebP）が受け入れられる"""
        assert image_utils.is_valid_image(sample_image, allowed_formats=['JPEG']) is True
    
    def test_無効な画像形式を拒否(self):
        """無効な画像形式（GIF, BMPなど）が拒否される"""
        # GIF画像を作成
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='GIF')
        img_bytes.seek(0)
        
        assert image_utils.is_valid_image(img_bytes, allowed_formats=['JPEG', 'PNG']) is False
    
    def test_ファイルサイズ制限(self):
        """ファイルサイズが制限を超える場合拒否される"""
        # 10MBの大きな画像を作成
        img = Image.new('RGB', (5000, 5000), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=100)
        img_bytes.seek(0)
        
        # 5MB制限
        assert image_utils.is_valid_size(img_bytes, max_size_mb=5) is False
    
    def test_画像の破損チェック(self):
        """破損した画像ファイルが検出される"""
        # 破損したデータ
        corrupted_data = io.BytesIO(b'This is not an image')
        
        assert image_utils.is_valid_image(corrupted_data) is False


class TestImageUpload:
    """画像アップロードのテスト"""
    
    @patch('modules.image_utils.supabase')
    def test_画像をSupabaseにアップロード(self, mock_supabase, sample_image):
        """画像がSupabase Storageに正しくアップロードされる"""
        mock_response = MagicMock()
        mock_response.public_url = 'https://example.com/image.webp'
        mock_supabase.storage.from_().upload.return_value = mock_response
        
        url = image_utils.upload_image(sample_image, 'butsugo', 'test.webp')
        
        assert url is not None
        assert 'webp' in url
    
    @patch('modules.image_utils.supabase')
    def test_画像アップロード時にWebP変換(self, mock_supabase, sample_image):
        """アップロード時に自動的にWebPに変換される"""
        mock_response = MagicMock()
        mock_response.public_url = 'https://example.com/image.webp'
        mock_supabase.storage.from_().upload.return_value = mock_response
        
        url = image_utils.upload_image(sample_image, 'butsugo', 'test.jpg')
        
        # WebPに変換されてアップロードされる
        call_args = mock_supabase.storage.from_().upload.call_args
        assert '.webp' in str(call_args)
    
    @patch('modules.image_utils.supabase')
    def test_画像削除(self, mock_supabase):
        """Supabase Storageから画像を削除できる"""
        image_url = 'https://example.com/storage/butsugo/test.webp'
        
        result = image_utils.delete_image(image_url)
        
        assert result is True
        mock_supabase.storage.from_().remove.assert_called_once()


class TestImageMetadata:
    """画像メタデータのテスト"""
    
    def test_画像サイズを取得(self, sample_image):
        """画像の幅と高さを取得できる"""
        width, height = image_utils.get_image_dimensions(sample_image)
        
        assert width == 100
        assert height == 100
    
    def test_画像フォーマットを取得(self, sample_image):
        """画像のフォーマットを取得できる"""
        format_name = image_utils.get_image_format(sample_image)
        
        assert format_name == 'JPEG'
    
    def test_画像ファイルサイズを取得(self, sample_image):
        """画像のファイルサイズを取得できる"""
        size = image_utils.get_file_size(sample_image)
        
        assert size > 0


class TestThumbnailGeneration:
    """サムネイル生成のテスト"""
    
    def test_サムネイル生成(self):
        """画像からサムネイルを生成できる"""
        # 1000x1000の画像
        img = Image.new('RGB', (1000, 1000), color='purple')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # 200x200のサムネイル生成
        thumbnail = image_utils.create_thumbnail(img_bytes, size=(200, 200))
        
        img = Image.open(thumbnail)
        assert img.width <= 200
        assert img.height <= 200
    
    def test_正方形サムネイル生成(self):
        """正方形のサムネイルを生成できる（クロップ）"""
        # 1000x500の画像（横長）
        img = Image.new('RGB', (1000, 500), color='purple')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # 200x200の正方形サムネイル生成
        thumbnail = image_utils.create_square_thumbnail(img_bytes, size=200)
        
        img = Image.open(thumbnail)
        assert img.width == 200
        assert img.height == 200


class TestImageOptimization:
    """画像最適化のテスト"""
    
    def test_画像圧縮でファイルサイズ削減(self):
        """画像圧縮でファイルサイズが削減される"""
        # 高品質の大きな画像
        img = Image.new('RGB', (2000, 2000), color='orange')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=100)
        original_size = len(img_bytes.getvalue())
        img_bytes.seek(0)
        
        # 圧縮
        compressed = image_utils.optimize_image(img_bytes, quality=80)
        compressed_size = len(compressed.getvalue())
        
        assert compressed_size < original_size
    
    def test_EXIFデータ削除(self):
        """画像からEXIFデータが削除される"""
        # EXIF付き画像（実際のカメラ画像を想定）
        img = Image.new('RGB', (100, 100), color='red')
        exif = img.getexif()
        exif[0x010F] = 'Test Camera'  # カメラメーカー
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', exif=exif)
        img_bytes.seek(0)
        
        # EXIF削除
        cleaned = image_utils.remove_exif(img_bytes)
        
        cleaned_img = Image.open(cleaned)
        assert len(cleaned_img.getexif()) == 0


# テスト実行時の設定
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

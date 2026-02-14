"""
テスト共通設定ファイル
pytest全体で使用する設定とフィクスチャを定義
"""

import pytest
import os
import sys
from unittest.mock import Mock, MagicMock
from flask import Flask
import tempfile

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ========================================
# Flaskアプリケーションのフィクスチャ
# ========================================

@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False  # テスト時はCSRF無効
    
    return app


@pytest.fixture
def client(app):
    """Flaskテストクライアント"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLIランナー"""
    return app.test_cli_runner()


# ========================================
# データベース関連のフィクスチャ
# ========================================

@pytest.fixture
def mock_supabase():
    """モックSupabaseクライアント"""
    mock = MagicMock()
    
    # table()メソッドのモック
    mock_table = MagicMock()
    mock.table.return_value = mock_table
    
    # select, insert, update, deleteのチェーンメソッド
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.neq.return_value = mock_table
    mock_table.ilike.return_value = mock_table
    mock_table.order.return_value = mock_table
    
    # execute()の戻り値
    mock_response = MagicMock()
    mock_response.data = []
    mock_table.execute.return_value = mock_response
    
    return mock


@pytest.fixture
def sample_user():
    """サンプルユーザーデータ"""
    return {
        'id': 1,
        'username': 'test_admin',
        'email': 'admin@test.com',
        'role': 'admin',
        'created_at': '2024-01-01T00:00:00'
    }


@pytest.fixture
def sample_temple():
    """サンプル寺院データ"""
    return {
        'id': 1,
        'name': 'テスト寺院',
        'address': '東京都渋谷区',
        'description': 'テスト用の寺院です',
        'latitude': 35.6586,
        'longitude': 139.7454,
        'created_at': '2024-01-01T00:00:00'
    }


@pytest.fixture
def sample_butsugo():
    """サンプル仏具データ"""
    return {
        'id': 1,
        'name': 'テスト仏壇',
        'category': '仏壇',
        'description': 'テスト用の仏壇です',
        'image_url': 'https://example.com/image.webp',
        'created_at': '2024-01-01T00:00:00'
    }


# ========================================
# セッション関連のフィクスチャ
# ========================================

@pytest.fixture
def logged_in_session(client):
    """ログイン済みセッション"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'test_admin'
        sess['role'] = 'admin'
    return client


@pytest.fixture
def editor_session(client):
    """編集者セッション"""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['username'] = 'test_editor'
        sess['role'] = 'editor'
    return client


@pytest.fixture
def viewer_session(client):
    """閲覧者セッション"""
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['username'] = 'test_viewer'
        sess['role'] = 'viewer'
    return client


# ========================================
# ファイル/画像関連のフィクスチャ
# ========================================

@pytest.fixture
def sample_image():
    """テスト用画像ファイル"""
    from PIL import Image
    import io
    
    # 100x100の赤い画像を作成
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes


@pytest.fixture
def temp_upload_dir():
    """一時アップロードディレクトリ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ========================================
# Redis/レート制限関連のフィクスチャ
# ========================================

@pytest.fixture
def mock_redis():
    """モックRedisクライアント"""
    mock = MagicMock()
    mock.get.return_value = None
    mock.setex.return_value = True
    mock.incr.return_value = 1
    mock.expire.return_value = True
    return mock


# ========================================
# メール関連のフィクスチャ
# ========================================

@pytest.fixture
def mock_smtp():
    """モックSMTPサーバー"""
    mock = MagicMock()
    mock.sendmail.return_value = {}
    return mock


# ========================================
# AI/Gemini関連のフィクスチャ
# ========================================

@pytest.fixture
def mock_gemini():
    """モックGemini APIクライアント"""
    mock = MagicMock()
    mock_model = MagicMock()
    mock.GenerativeModel.return_value = mock_model
    
    # generate_contentのモック
    mock_response = MagicMock()
    mock_response.text = "これはテスト回答です。"
    mock_model.generate_content.return_value = mock_response
    
    return mock


# ========================================
# テストデータのクリーンアップ
# ========================================

@pytest.fixture(autouse=True)
def cleanup_test_data():
    """各テスト後にテストデータをクリーンアップ"""
    yield
    # テスト後の処理があればここに記述
    pass

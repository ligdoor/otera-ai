"""
仏教用品管理ルート

仏教用品（仏具）カタログの管理機能を提供します。
CRUD操作、カテゴリ管理、画像アップロードを含みます。
"""

import logging
from flask import Blueprint, render_template, jsonify, request, session
from utils.decorators import login_required, role_required, admin_required
from services.database import get_supabase_client
from PIL import Image
import io

# ============================================
# Blueprintの定義
# ============================================

admin_items_bp = Blueprint('admin_items', __name__)

logger = logging.getLogger(__name__)


# ============================================
# 画面表示
# ============================================

@admin_items_bp.route('/admin/items')
@login_required
@role_required(['admin', 'editor'])  # ★修正: デコレータで権限チェック（DB問い合わせ不要に）
def admin_items():
    """
    仏具管理画面を表示
    
    仏教用品カタログの管理画面を表示します。
    admin または editor 権限が必要です。
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    
    Route:
        GET /admin/items
    
    Authentication:
        @login_required: ログイン必須
        @role_required(['admin', 'editor']): admin または editor 権限が必要
    
    Template Variables:
        user_name: ユーザー名
        user_role: ユーザーの権限
    """
    user_name = session.get('user_name', 'ゲスト')
    user_role = session.get('role', 'viewer')
    
    logger.info(f"✅ 仏具管理画面表示: {user_name} ({user_role})")
    
    return render_template(
        'admin_items.html',
        user_name=user_name,
        user_role=user_role
    )


# ============================================
# 仏具CRUD - 一覧取得
# ============================================

@admin_items_bp.route('/api/admin/items', methods=['GET'])
@login_required
def get_admin_items():
    """
    仏具一覧を取得
    
    全ての仏教用品を作成日時の降順で取得します。
    
    Returns:
        JSON: 仏具一覧
            success (bool): 成功した場合True
            items (list): 仏具のリスト
    
    Route:
        GET /api/admin/items
    
    Authentication:
        @login_required: ログイン必須
    
    Example Response:
        {
            "success": true,
            "items": [
                {
                    "id": 123,
                    "name": "線香立て",
                    "category": "供養具",
                    "description": "...",
                    "main_image_url": "https://...",
                    "is_public": true,
                    ...
                }
            ]
        }
    """
    try:
        # データベースクライアントを取得
        supabase = get_supabase_client()
        
        # 仏具一覧を取得（作成日時の降順）
        items_response = supabase.table('buddhist_items')\
            .select('*')\
            .order('created_at', desc=True)\
            .execute()
        
        items = items_response.data if items_response.data else []
        
        return jsonify({
            'success': True,
            'items': items
        })
    
    except Exception as e:
        logger.error(f"❌ 仏具一覧取得エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# 仏具CRUD - 詳細取得
# ============================================

@admin_items_bp.route('/api/admin/items/<item_id>', methods=['GET'])
@login_required
def get_admin_item(item_id):
    """
    仏具詳細を取得
    
    指定されたIDの仏教用品の詳細情報を取得します。
    
    Args:
        item_id: 仏具ID
    
    Returns:
        JSON: 仏具詳細
            success (bool): 成功した場合True
            item (dict): 仏具情報
    
    Route:
        GET /api/admin/items/<item_id>
    
    Authentication:
        @login_required: ログイン必須
    
    Example Response:
        {
            "success": true,
            "item": {
                "id": 123,
                "name": "線香立て",
                "name_kana": "せんこうたて",
                "category": "供養具",
                "description": "...",
                "usage": "...",
                "material": "真鍮",
                "size": "高さ10cm",
                "main_image_url": "https://...",
                "stock_quantity": 5,
                "display_order": 0,
                "is_public": true
            }
        }
    """
    try:
        # データベースクライアントを取得
        supabase = get_supabase_client()
        
        # 仏具詳細を取得
        item_response = supabase.table('buddhist_items')\
            .select('*')\
            .eq('id', item_id)\
            .single()\
            .execute()
        
        if not item_response.data:
            return jsonify({
                'success': False,
                'error': '仏具が見つかりません'
            }), 404
        
        return jsonify({
            'success': True,
            'item': item_response.data
        })
    
    except Exception as e:
        logger.error(f"❌ 仏具詳細取得エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# 仏具CRUD - 作成
# ============================================

@admin_items_bp.route('/api/admin/items', methods=['POST'])
@login_required
@role_required(['admin', 'editor'])  # ★修正: デコレータで権限チェック（DB問い合わせ不要に）
def create_admin_item():
    """
    仏具を作成
    
    新しい仏教用品をカタログに追加します。
    admin または editor 権限が必要です。
    
    Request Body (JSON):
        {
            "name": "仏具名（必須）",
            "name_kana": "ふりがな",
            "category": "カテゴリ（必須）",
            "description": "説明",
            "usage": "使い方",
            "material": "素材",
            "size": "サイズ",
            "main_image_url": "画像URL",
            "stock_quantity": 在庫数,
            "display_order": 表示順,
            "is_public": 公開設定
        }
    
    Returns:
        JSON: 処理結果
            success (bool): 成功した場合True
            item (dict): 作成された仏具情報
    
    Route:
        POST /api/admin/items
    
    Authentication:
        @login_required: ログイン必須
        @role_required(['admin', 'editor']): admin または editor 権限が必要
    
    Example Request:
        POST /api/admin/items
        {
            "name": "線香立て",
            "category": "供養具",
            "description": "真鍮製の線香立て"
        }
    
    Example Response:
        {
            "success": true,
            "item": {
                "id": 123,
                "name": "線香立て",
                ...
            }
        }
    """
    try:
        # ============================================
        # バリデーション
        # ============================================
        
        data = request.json
        
        if not data.get('name') or not data.get('category'):
            return jsonify({
                'success': False,
                'error': '名前とカテゴリは必須です'
            }), 400
        
        # ============================================
        # データ作成
        # ============================================
        
        supabase = get_supabase_client()
        
        item_data = {
            'name': data.get('name'),
            'name_kana': data.get('name_kana'),
            'category': data.get('category'),
            'description': data.get('description'),
            'usage': data.get('usage'),
            'material': data.get('material'),
            'size': data.get('size'),
            'main_image_url': data.get('main_image_url'),
            'stock_quantity': data.get('stock_quantity', 1),
            'display_order': data.get('display_order', 0),
            'is_public': data.get('is_public', True)
        }
        
        # データベースに挿入
        item_response = supabase.table('buddhist_items')\
            .insert(item_data)\
            .execute()
        
        if not item_response.data:
            return jsonify({
                'success': False,
                'error': '作成に失敗しました'
            }), 500
        
        logger.info(f"✅ 仏具作成: {data.get('name')}")
        
        return jsonify({
            'success': True,
            'item': item_response.data[0]
        })
    
    except Exception as e:
        logger.error(f"❌ 仏具作成エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# 仏具CRUD - 更新
# ============================================

@admin_items_bp.route('/api/admin/items/<item_id>', methods=['PUT'])
@login_required
@role_required(['admin', 'editor'])  # ★修正: デコレータで権限チェック（DB問い合わせ不要に）
def update_admin_item(item_id):
    """
    仏具を更新
    
    既存の仏教用品情報を更新します。
    admin または editor 権限が必要です。
    
    Args:
        item_id: 仏具ID
    
    Request Body (JSON):
        更新したいフィールドのみ送信
        {
            "name": "仏具名",
            "category": "カテゴリ",
            ...
        }
    
    Returns:
        JSON: 処理結果
            success (bool): 成功した場合True
            item (dict): 更新された仏具情報
    
    Route:
        PUT /api/admin/items/<item_id>
    
    Authentication:
        @login_required: ログイン必須
        @role_required(['admin', 'editor']): admin または editor 権限が必要
    
    Example Request:
        PUT /api/admin/items/123
        {
            "description": "更新された説明",
            "is_public": false
        }
    
    Example Response:
        {
            "success": true,
            "item": {
                "id": 123,
                "description": "更新された説明",
                "is_public": false,
                ...
            }
        }
    """
    try:
        supabase = get_supabase_client()
        data = request.json
        
        # Noneでないフィールドのみ更新対象とする
        update_data = {
            k: v for k, v in {
                'name': data.get('name'),
                'name_kana': data.get('name_kana'),
                'category': data.get('category'),
                'description': data.get('description'),
                'usage': data.get('usage'),
                'material': data.get('material'),
                'size': data.get('size'),
                'main_image_url': data.get('main_image_url'),
                'stock_quantity': data.get('stock_quantity'),
                'display_order': data.get('display_order'),
                'is_public': data.get('is_public')
            }.items() if v is not None
        }
        
        # データベースを更新
        item_response = supabase.table('buddhist_items')\
            .update(update_data)\
            .eq('id', item_id)\
            .execute()
        
        if not item_response.data:
            return jsonify({
                'success': False,
                'error': '更新に失敗しました'
            }), 500
        
        logger.info(f"✅ 仏具更新: ID={item_id}")
        
        return jsonify({
            'success': True,
            'item': item_response.data[0]
        })
    
    except Exception as e:
        logger.error(f"❌ 仏具更新エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# 仏具CRUD - 削除
# ============================================

@admin_items_bp.route('/api/admin/items/<item_id>', methods=['DELETE'])
@login_required
@admin_required  # ★修正: デコレータで権限チェック（DB問い合わせ不要に）
def delete_admin_item(item_id):
    """
    仏具を削除
    
    指定された仏教用品をカタログから削除します。
    管理者（admin）のみが実行できます。
    
    Args:
        item_id: 仏具ID
    
    Returns:
        JSON: 処理結果
            success (bool): 成功した場合True
    
    Route:
        DELETE /api/admin/items/<item_id>
    
    Authentication:
        @login_required: ログイン必須
        @admin_required: 管理者（admin）権限が必要
    
    Example Response:
        {
            "success": true
        }
    """
    try:
        supabase = get_supabase_client()
        
        supabase.table('buddhist_items')\
            .delete()\
            .eq('id', item_id)\
            .execute()
        
        logger.debug(f"🗑️ 仏具削除: ID={item_id}")
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"❌ 仏具削除エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# カテゴリ管理
# ============================================

@admin_items_bp.route('/api/admin/categories', methods=['GET'])
@login_required
def get_admin_categories():
    """
    カテゴリ一覧を取得
    
    仏教用品のカテゴリ一覧を表示順で取得します。
    
    Returns:
        JSON: カテゴリ一覧
            success (bool): 成功した場合True
            categories (list): カテゴリのリスト
    
    Route:
        GET /api/admin/categories
    
    Authentication:
        @login_required: ログイン必須
    
    Example Response:
        {
            "success": true,
            "categories": [
                {
                    "id": 1,
                    "name": "供養具",
                    "display_order": 1
                },
                {
                    "id": 2,
                    "name": "荘厳具",
                    "display_order": 2
                }
            ]
        }
    """
    try:
        # データベースクライアントを取得
        supabase = get_supabase_client()
        
        # カテゴリ一覧を取得（表示順）
        categories_response = supabase.table('item_categories')\
            .select('*')\
            .order('display_order')\
            .execute()
        
        categories = categories_response.data if categories_response.data else []
        
        return jsonify({
            'success': True,
            'categories': categories
        })
    
    except Exception as e:
        logger.error(f"❌ カテゴリ一覧取得エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# 画像アップロード
# ============================================

@admin_items_bp.route('/api/admin/upload-image', methods=['POST'])
@login_required
@role_required(['admin', 'editor'])  # ★修正: デコレータで権限チェック（DB問い合わせ不要に）
def upload_image():
    """
    画像をアップロード（WebP圧縮）
    
    仏教用品の画像をアップロードします。
    自動的にWebP形式に圧縮されます（quality=80, lossy）。
    admin または editor 権限が必要です。
    
    Form Data:
        file: 画像ファイル
        filename: ファイル名（オプション）
    
    Returns:
        JSON: 処理結果
            success (bool): 成功した場合True
            url (str): アップロードされた画像の公開URL
    
    Route:
        POST /api/admin/upload-image
    
    Authentication:
        @login_required: ログイン必須
        @role_required(['admin', 'editor']): admin または editor 権限が必要
    
    Image Processing:
        - WebP形式に変換
        - 品質: 80（lossy圧縮）
        - RGBA → RGB変換（透明度は白背景で合成）
        - 圧縮率をログ出力
    
    Example Response:
        {
            "success": true,
            "url": "https://...storage.../image.webp"
        }
    """
    try:
        supabase = get_supabase_client()
        
        # ============================================
        # ファイルチェック
        # ============================================
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'ファイルがありません'
            }), 400
        
        file = request.files['file']
        original_filename = request.form.get('filename', 'image.jpg')
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'ファイルが選択されていません'
            }), 400
        
        # ============================================
        # 画像をWebP形式に圧縮
        # ============================================
        
        # 元のファイルサイズを取得
        file.stream.seek(0, 2)  # ファイルの末尾に移動
        original_size = file.stream.tell()
        file.stream.seek(0)  # ファイルの先頭に戻す
        
        # 画像を読み込み
        image = Image.open(file.stream)
        
        # RGBAの場合はRGBに変換
        # （WebPはRGBAもサポートするが、lossyの場合はRGBが推奨）
        if image.mode in ('RGBA', 'LA', 'P'):
            # 透明度がある場合は白背景で合成
            background = Image.new('RGB', image.size, (255, 255, 255))
            
            if image.mode == 'P':
                image = image.convert('RGBA')
            
            # 透明度をマスクとして使用
            mask = image.split()[-1] if image.mode in ('RGBA', 'LA') else None
            background.paste(image, mask=mask)
            image = background
        
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # WebP形式で圧縮（lossy, quality=80）
        webp_buffer = io.BytesIO()
        image.save(webp_buffer, format='WebP', quality=80, method=6)
        webp_bytes = webp_buffer.getvalue()
        
        # ============================================
        # ファイル名を.webpに変更
        # ============================================
        
        filename_without_ext = original_filename.rsplit('.', 1)[0]
        storage_path = f"{filename_without_ext}.webp"
        
        # ============================================
        # Supabase Storageにアップロード
        # ============================================
        
        upload_result = supabase.storage.from_('temple-images').upload(
            storage_path,
            webp_bytes,
            file_options={"content-type": "image/webp"}
        )
        
        # 公開URLを取得
        public_url = supabase.storage.from_('temple-images').get_public_url(storage_path)
        
        # ============================================
        # 圧縮情報をログ出力
        # ============================================
        
        compressed_size = len(webp_bytes)
        
        if original_size > 0:
            compression_ratio = (1 - compressed_size / original_size) * 100
            logger.debug(f"📸 画像アップロード: {original_size:,} bytes → {compressed_size:,} bytes (圧縮率: {compression_ratio:.1f}%)")
        else:
            logger.debug(f"📸 画像アップロード: {compressed_size:,} bytes")
        
        return jsonify({
            'success': True,
            'url': public_url
        })
    
    except Exception as e:
        logger.error(f"❌ 画像アップロードエラー: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

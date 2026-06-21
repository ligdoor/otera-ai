# routes/items_routes.py - 仏具図鑑のルート

import logging
from flask import Blueprint, render_template, request, session
from services.database import get_supabase_client
from utils.decorators import login_required

items_bp = Blueprint('items', __name__)

logger = logging.getLogger(__name__)

# ===================================
# 仏具図鑑のルート（閲覧はログイン不要）
# ===================================

@items_bp.route('/items')
def items_index():
    """仏具図鑑トップページ（ログイン不要）"""
    try:
        supabase = get_supabase_client()
        
        total_count_response = supabase.table('buddhist_items')\
            .select('id', count='exact')\
            .eq('is_public', True)\
            .execute()
        
        total_count = total_count_response.count if total_count_response.count else 0
        
        categories_response = supabase.table('item_categories')\
            .select('*')\
            .order('display_order')\
            .execute()
        
        categories = categories_response.data if categories_response.data else []
        user_name = session.get('user_name', 'ゲスト')
        
        return render_template('items/index.html',
                             total_count=total_count,
                             categories=categories,
                             user_name=user_name)
    
    except Exception as e:
        logger.debug(f"Error in items_index: {e}")
        return render_template('items/index.html',
                             total_count=0,
                             categories=[],
                             user_name=session.get('user_name', 'ゲスト'))

@items_bp.route('/items/gallery')
def items_gallery():
    """画像ギャラリーページ（ログイン不要）"""
    try:
        supabase = get_supabase_client()
        
        category = request.args.get('category', 'all')
        page = int(request.args.get('page', 1))
        per_page = 20
        
        query = supabase.table('buddhist_items')\
            .select('*')\
            .eq('is_public', True)
        
        if category != 'all':
            query = query.eq('category', category)
        
        start = (page - 1) * per_page
        end = start + per_page - 1
        
        items_response = query.range(start, end).order('created_at', desc=True).execute()
        items = items_response.data if items_response.data else []
        
        categories_response = supabase.table('item_categories')\
            .select('*')\
            .order('display_order')\
            .execute()
        categories = categories_response.data if categories_response.data else []
        
        count_response = supabase.table('buddhist_items')\
            .select('id', count='exact')\
            .eq('is_public', True)
        
        if category != 'all':
            count_response = count_response.eq('category', category)
        
        count_result = count_response.execute()
        total_count = count_result.count if count_result.count else 0
        
        user_name = session.get('user_name', 'ゲスト')
        
        return render_template('items/gallery.html',
                             items=items,
                             categories=categories,
                             current_category=category,
                             current_page=page,
                             per_page=per_page,
                             total_count=total_count,
                             user_name=user_name)
    
    except Exception as e:
        logger.debug(f"Error in items_gallery: {e}")
        return render_template('items/gallery.html',
                             items=[],
                             categories=[],
                             current_category='all',
                             current_page=1,
                             per_page=20,
                             total_count=0,
                             user_name=session.get('user_name', 'ゲスト'))

@items_bp.route('/items/search')
def items_search():
    """名前検索ページ（ログイン不要）"""
    try:
        supabase = get_supabase_client()
        
        keyword = request.args.get('q', '')
        
        items = []
        if keyword:
            kana_rows = {
                'あ': ['あ', 'い', 'う', 'え', 'お'],
                'か': ['か', 'き', 'く', 'け', 'こ', 'が', 'ぎ', 'ぐ', 'げ', 'ご'],
                'さ': ['さ', 'し', 'す', 'せ', 'そ', 'ざ', 'じ', 'ず', 'ぜ', 'ぞ'],
                'た': ['た', 'ち', 'つ', 'て', 'と', 'だ', 'ぢ', 'づ', 'で', 'ど'],
                'な': ['な', 'に', 'ぬ', 'ね', 'の'],
                'は': ['は', 'ひ', 'ふ', 'へ', 'ほ', 'ば', 'び', 'ぶ', 'べ', 'ぼ', 'ぱ', 'ぴ', 'ぷ', 'ぺ', 'ぽ'],
                'ま': ['ま', 'み', 'む', 'め', 'も'],
                'や': ['や', 'ゆ', 'よ'],
                'ら': ['ら', 'り', 'る', 'れ', 'ろ'],
                'わ': ['わ', 'を', 'ん']
            }
            
            if len(keyword) == 1 and keyword in kana_rows:
                kana_list = kana_rows[keyword]
                or_conditions = ','.join([f'name_kana.ilike.{kana}%' for kana in kana_list])
                items_response = supabase.table('buddhist_items')\
                    .select('*')\
                    .eq('is_public', True)\
                    .or_(or_conditions)\
                    .order('name_kana')\
                    .execute()
            else:
                items_response = supabase.table('buddhist_items')\
                    .select('*')\
                    .eq('is_public', True)\
                    .or_(f'name.ilike.%{keyword}%,name_kana.ilike.%{keyword}%')\
                    .order('name')\
                    .execute()
            
            items = items_response.data if items_response.data else []
        
        user_name = session.get('user_name', 'ゲスト')
        
        return render_template('items/search.html',
                             items=items,
                             keyword=keyword,
                             user_name=user_name)
    
    except Exception as e:
        logger.debug(f"Error in items_search: {e}")
        import traceback
        traceback.print_exc()
        return render_template('items/search.html',
                             items=[],
                             keyword='',
                             user_name=session.get('user_name', 'ゲスト'))

@items_bp.route('/items/categories')
def items_categories():
    """カテゴリ一覧ページ（ログイン不要）"""
    try:
        supabase = get_supabase_client()
        
        categories_response = supabase.table('item_categories')\
            .select('*')\
            .order('display_order')\
            .execute()
        
        categories = categories_response.data if categories_response.data else []
        
        for category in categories:
            count_response = supabase.table('buddhist_items')\
                .select('id', count='exact')\
                .eq('is_public', True)\
                .eq('category', category['name'])\
                .execute()
            
            category['count'] = count_response.count if count_response.count else 0
        
        user_name = session.get('user_name', 'ゲスト')
        
        return render_template('items/categories.html',
                             categories=categories,
                             user_name=user_name)
    
    except Exception as e:
        logger.debug(f"Error in items_categories: {e}")
        return render_template('items/categories.html',
                             categories=[],
                             user_name=session.get('user_name', 'ゲスト'))

@items_bp.route('/items/category/<category_name>')
def items_category(category_name):
    """カテゴリ別一覧ページ（ログイン不要）"""
    try:
        supabase = get_supabase_client()
        
        items_response = supabase.table('buddhist_items')\
            .select('*')\
            .eq('is_public', True)\
            .eq('category', category_name)\
            .order('name')\
            .execute()
        
        items = items_response.data if items_response.data else []
        user_name = session.get('user_name', 'ゲスト')
        
        return render_template('items/category.html',
                             items=items,
                             category_name=category_name,
                             user_name=user_name)
    
    except Exception as e:
        logger.debug(f"Error in items_category: {e}")
        return render_template('items/category.html',
                             items=[],
                             category_name=category_name,
                             user_name=session.get('user_name', 'ゲスト'))

@items_bp.route('/items/detail/<item_id>')
def item_detail(item_id):
    """仏具詳細ページ（ログイン不要）"""
    try:
        supabase = get_supabase_client()
        
        item_response = supabase.table('buddhist_items')\
            .select('*')\
            .eq('id', item_id)\
            .single()\
            .execute()
        
        item = item_response.data if item_response.data else None
        
        images = []
        if item:
            images_response = supabase.table('item_images')\
                .select('*')\
                .eq('item_id', item_id)\
                .order('display_order')\
                .execute()
            
            images = images_response.data if images_response.data else []
        
        user_name = session.get('user_name', 'ゲスト')
        
        return render_template('items/detail.html',
                             item=item,
                             images=images,
                             user_name=user_name)
    
    except Exception as e:
        logger.debug(f"Error in item_detail: {e}")
        return render_template('items/detail.html',
                             item=None,
                             images=[],
                             user_name=session.get('user_name', 'ゲスト'))

@items_bp.route('/favorites')
@login_required
def favorites():
    """お気に入りページ（ログイン必要）"""
    user_name = session.get('user_name', 'ゲスト')
    return render_template('favorites.html', user_name=user_name)

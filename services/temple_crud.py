"""
Supabase対応のCRUD操作ヘルパー

Google SheetsとSupabaseで共通のインターフェースを提供します。
"""

from config import Config
from services.cache import cache_manager


def update_temple_data(original_name, new_data, otera_database):
    """
    寺院データを更新
    
    Args:
        original_name: 元の寺院名
        new_data: 新しいデータ
        otera_database: グローバルデータベース辞書
        
    Returns:
        tuple: (success: bool, message: str)
    """
    if Config.USE_SUPABASE:
        # Supabase版
        from services import supabase_db
        try:
            supabase_db.update_temple(original_name, new_data)
            
            # メモリ内のデータも更新
            if original_name in otera_database:
                del otera_database[original_name]
            otera_database[new_data['name']] = new_data
            
            # キャッシュクリア
            cache_manager.clear_cache('temples')
            
            return True, "更新成功"
        except Exception as e:
            return False, str(e)
    else:
        # Google Sheets版
        from services.spreadsheet import get_spreadsheet_client, get_data_sheet_and_headers
        try:
            sheet, headers = get_data_sheet_and_headers()
            
            # 新しいキーがあればヘッダーに追加
            current_headers = headers
            for key in new_data.keys():
                if key not in current_headers:
                    sheet.update_cell(1, len(current_headers) + 1, key)
                    current_headers.append(key)
            headers = current_headers
            
            # 該当行を検索して更新
            cell = sheet.find(original_name, in_column=1)
            if cell:
                row_idx = cell.row
                row_data = [new_data.get(h, "") for h in headers]
                sheet.update(f"A{row_idx}", [row_data])
                
                # メモリ内のデータも更新
                if original_name in otera_database:
                    del otera_database[original_name]
                otera_database[new_data['name']] = new_data
                
                # キャッシュクリア
                cache_manager.clear_cache('temples')
                
                return True, "更新成功"
            else:
                return False, "寺院が見つかりません"
        except Exception as e:
            return False, str(e)


def add_temple_data(new_data, otera_database):
    """
    新規寺院を追加
    
    Args:
        new_data: 新しい寺院データ
        otera_database: グローバルデータベース辞書
        
    Returns:
        tuple: (success: bool, message: str)
    """
    name = new_data.get('name')
    
    if not name:
        return False, "寺院名は必須です"
    
    if name in otera_database:
        return False, "その名前は既に存在します"
    
    if Config.USE_SUPABASE:
        # Supabase版
        from services import supabase_db
        try:
            supabase_db.create_temple(new_data)
            
            # メモリ内のデータも更新
            otera_database[name] = new_data
            
            # キャッシュクリア
            cache_manager.clear_cache('temples')
            
            return True, "追加成功"
        except Exception as e:
            return False, str(e)
    else:
        # Google Sheets版
        from services.spreadsheet import get_data_sheet_and_headers
        try:
            sheet, headers = get_data_sheet_and_headers()
            
            # 新しいキーがあればヘッダーに追加
            current_headers = headers
            for key in new_data.keys():
                if key not in current_headers:
                    sheet.update_cell(1, len(current_headers) + 1, key)
                    current_headers.append(key)
            headers = current_headers
            
            # 新しい行を追加
            row_data = [new_data.get(h, "") for h in headers]
            sheet.append_row(row_data)
            
            # メモリ内のデータも更新
            otera_database[name] = new_data
            
            # キャッシュクリア
            cache_manager.clear_cache('temples')
            
            return True, "追加成功"
        except Exception as e:
            return False, str(e)


def delete_temple_data(name, otera_database):
    """
    寺院を削除
    
    Args:
        name: 寺院名
        otera_database: グローバルデータベース辞書
        
    Returns:
        tuple: (success: bool, message: str)
    """
    if name not in otera_database:
        return False, "寺院が見つかりません"
    
    if Config.USE_SUPABASE:
        # Supabase版
        from services import supabase_db
        try:
            supabase_db.delete_temple(name)
            
            # メモリ内のデータも削除
            del otera_database[name]
            
            # キャッシュクリア
            cache_manager.clear_cache('temples')
            
            return True, "削除成功"
        except Exception as e:
            return False, str(e)
    else:
        # Google Sheets版
        from services.spreadsheet import get_spreadsheet_client
        from config import Config as AppConfig
        try:
            client = get_spreadsheet_client()
            sheet = client.open(AppConfig.DATA_SPREADSHEET_NAME).sheet1
            
            # 該当行を検索して削除
            cell = sheet.find(name, in_column=1)
            if cell:
                sheet.delete_rows(cell.row)
                
                # メモリ内のデータも削除
                del otera_database[name]
                
                # キャッシュクリア
                cache_manager.clear_cache('temples')
                
                return True, "削除成功"
            else:
                return False, "寺院が見つかりません"
        except Exception as e:
            return False, str(e)


def update_fields_data(fields):
    """
    項目設定を更新
    
    Args:
        fields: 項目設定のリスト
        
    Returns:
        tuple: (success: bool, message: str)
    """
    if Config.USE_SUPABASE:
        # Supabase版
        from services import supabase_db
        try:
            supabase_db.update_fields_config(fields)
            
            # キャッシュクリア
            cache_manager.clear_cache('fields')
            
            return True, "更新成功"
        except Exception as e:
            return False, str(e)
    else:
        # Google Sheets版
        from services.spreadsheet import get_spreadsheet_client
        from config import Config as AppConfig
        try:
            client = get_spreadsheet_client()
            sheet = client.open(AppConfig.DATA_SPREADSHEET_NAME).worksheet('fields')
            
            # 既存データをクリア
            sheet.clear()
            
            # ヘッダー追加
            sheet.update('A1', [['key', 'label', 'order']])
            
            # データ追加
            rows = [[f['key'], f['label'], f['order']] for f in fields]
            if rows:
                sheet.update(f'A2:C{len(rows) + 1}', rows)
            
            # キャッシュクリア
            cache_manager.clear_cache('fields')
            
            return True, "更新成功"
        except Exception as e:
            return False, str(e)

import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import request, session
from config import Config
from utils.helpers import get_jst_timestamp
from services.notification import notify_data_update

# グローバルクライアント
gc = None

def get_spreadsheet_client():
    """Google Sheetsクライアントを取得"""
    global gc
    if gc is None:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_json_str = Config.GOOGLE_CREDENTIALS_JSON
        if creds_json_str:
            creds_dict = json.loads(creds_json_str)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        gc = gspread.authorize(creds)
    return gc

def add_log(action, details, ip_address=None):
    """操作ログを記録"""
    try:
        user_name = session.get('user_name', '不明')
        user_id = session.get('user_id', '不明')
        client = get_spreadsheet_client()
        sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('logs')
        timestamp = get_jst_timestamp()
        ip = ip_address or request.remote_addr
        sheet.append_row([timestamp, user_name, user_id, action, details, ip])
        
        # データ更新系の操作はSlack通知
        if action in ['追加', '編集', '削除', 'データ更新']:
            notify_data_update(user_name, action, details)
            
    except Exception as e:
        print(f"ログ記録エラー: {e}")

def load_fields_config(cache_manager):
    """項目設定を読み込み（キャッシュ対応）"""
    def fetch():
        fields = []
        try:
            client = get_spreadsheet_client()
            sheet = client.open(Config.DATA_SPREADSHEET_NAME).worksheet('fields')
            records = sheet.get_all_records()
            records.sort(key=lambda x: x['order'])
            fields = records
        except Exception as e:
            print(f"項目設定読み込みエラー: {e}")
            fields = [{'key': 'name', 'label': '寺院名', 'order': 1}]
        return fields
    
    return cache_manager.get_cached_or_fetch('fields', fetch)

def load_data_from_sheet(cache_manager):
    """寺院データを読み込み（キャッシュ対応）"""
    def fetch():
        data = {}
        try:
            client = get_spreadsheet_client()
            sheet = client.open(Config.DATA_SPREADSHEET_NAME).sheet1
            # バッチ取得で高速化
            all_values = sheet.get_all_values()
            if len(all_values) > 0:
                headers = all_values[0]
                for row in all_values[1:]:
                    if len(row) > 0 and row[0]:  # name列が空でない
                        row_dict = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                row_dict[header] = str(row[i]).strip()
                        if 'name' in row_dict and row_dict['name']:
                            data[row_dict['name']] = row_dict
            print(f"★データ更新完了: {len(data)}件")
        except Exception as e:
            print(f"読み込みエラー: {e}")
        return data
    
    return cache_manager.get_cached_or_fetch('temples', fetch)

def get_data_sheet_and_headers():
    """データシートとヘッダーを取得"""
    client = get_spreadsheet_client()
    sheet = client.open(Config.DATA_SPREADSHEET_NAME).sheet1
    headers = sheet.row_values(1)
    return sheet, headers
import datetime
import pytz

# タイムゾーン設定（日本時間）
JST = pytz.timezone('Asia/Tokyo')

def get_jst_now():
    """日本時間の現在時刻を取得"""
    return datetime.datetime.now(JST)

def get_jst_timestamp():
    """日本時間のタイムスタンプ文字列を取得"""
    return get_jst_now().strftime('%Y-%m-%d %H:%M:%S')
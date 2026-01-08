import os
import json
import datetime
import secrets
import csv
import io
from functools import wraps
from dotenv import load_dotenv
from google import genai
from google.genai import types
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import bcrypt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

load_dotenv()

# --- 設定 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

# 通知設定
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True if os.environ.get('FLASK_ENV') == 'production' else False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

DATA_SPREADSHEET_NAME = "otera_data"
CONFIG_SPREADSHEET_NAME = "otera_admin_config"

gc = None 
login_attempts = {}
LOCK_TIME = 300
MAX_ATTEMPTS = 5

# キャッシュ設定
CACHE_TIMEOUT = 300  # 5分間キャッシュ
cache_data = {
    'temples': {'data': None, 'timestamp': 0},
    'fields': {'data': None, 'timestamp': 0}
}

def get_spreadsheet_client():
    global gc
    if gc is None:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if creds_json_str:
            creds_dict = json.loads(creds_json_str)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        gc = gspread.authorize(creds)
    return gc

def is_cache_valid(cache_key):
    """キャッシュが有効か確認"""
    if cache_data[cache_key]['data'] is None:
        return False
    elapsed = datetime.datetime.now().timestamp() - cache_data[cache_key]['timestamp']
    return elapsed < CACHE_TIMEOUT

def get_cached_or_fetch(cache_key, fetch_function):
    """キャッシュから取得、期限切れなら再取得"""
    if is_cache_valid(cache_key):
        print(f"✅ キャッシュから取得: {cache_key}")
        return cache_data[cache_key]['data']
    
    try:
        data = fetch_function()
        cache_data[cache_key]['data'] = data
        cache_data[cache_key]['timestamp'] = datetime.datetime.now().timestamp()
        print(f"✅ データ取得成功: {cache_key}")
        return data
    except Exception as e:
        print(f"❌ データ取得失敗: {cache_key} - {e}")
        # キャッシュがあれば古いデータでも返す
        if cache_data[cache_key]['data'] is not None:
            print(f"⚠️ 古いキャッシュを返却: {cache_key}")
            return cache_data[cache_key]['data']
        raise e

# --- 通知機能 ---

def send_slack_notification(message, emoji=":bell:"):
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        return
    
    try:
        payload = {
            "text": f"{emoji} {message}",
            "username": "寺院管理システム",
            "icon_emoji": ":temple:"
        }
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ Slack通知送信成功: {message}")
        else:
            print(f"❌ Slack通知失敗: {response.status_code}")
    except Exception as e:
        print(f"❌ Slack通知エラー: {e}")

def send_email_alert(subject, body, to_email=None):
    """メール通知を送信"""
    if not SMTP_USER or not SMTP_PASSWORD or not ADMIN_EMAIL:
        return
    
    recipient = to_email or ADMIN_EMAIL
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = recipient
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ メール送信成功: {subject}")
    except Exception as e:
        print(f"❌ メール送信エラー: {e}")

def notify_suspicious_login(user_id, ip_address, reason):
    """異常ログイン時の通知"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Slack通知
    slack_msg = f"""
🚨 *異常ログイン検知*
• 時刻: {timestamp}
• ユーザーID: {user_id}
• IPアドレス: {ip_address}
• 理由: {reason}
    """
    send_slack_notification(slack_msg, emoji=":warning:")
    
    # メール通知
    email_subject = f"【警告】異常ログイン検知 - {user_id}"
    email_body = f"""
寺院管理システムで異常なログイン試行を検知しました。

▼ 詳細情報
━━━━━━━━━━━━━━━━━━━━━━
日時: {timestamp}
ユーザーID: {user_id}
IPアドレス: {ip_address}
検知理由: {reason}
━━━━━━━━━━━━━━━━━━━━━━

必要に応じて以下の対応を検討してください:
1. 該当ユーザーアカウントの一時停止
2. パスワードリセットの実施
3. アクセスログの確認

このメールは自動送信されています。
    """
    send_email_alert(email_subject, email_body)

def notify_data_update(user_name, action, details):
    """データ更新時のSlack通知"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    emoji_map = {
        '追加': ':heavy_plus_sign:',
        '編集': ':pencil2:',
        '削除': ':wastebasket:',
        'データ更新': ':arrows_counterclockwise:'
    }
    emoji = emoji_map.get(action, ':bell:')
    
    slack_msg = f"""
📊 *データ更新通知*
• 時刻: {timestamp}
• 担当者: {user_name}
• 操作: {action}
• 内容: {details}
    """
    send_slack_notification(slack_msg, emoji=emoji)

# --- ログ記録 ---

def add_log(action, details, ip_address=None):
    try:
        user_name = session.get('user_name', '不明')
        user_id = session.get('user_id', '不明')
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('logs')
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ip = ip_address or request.remote_addr
        sheet.append_row([timestamp, user_name, user_id, action, details, ip])
        
        # データ更新系の操作はSlack通知
        if action in ['追加', '編集', '削除', 'データ更新']:
            notify_data_update(user_name, action, details)
            
    except Exception as e:
        print(f"ログ記録エラー: {e}")

def update_session_activity():
    session['last_activity'] = datetime.datetime.now().timestamp()
    session.permanent = True

def check_session_timeout():
    if 'last_activity' in session:
        elapsed = datetime.datetime.now().timestamp() - session['last_activity']
        if elapsed > 1800:
            session.clear()
            return False
    return True

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            # HTML画面へのアクセスの場合はログインページにリダイレクト
            if request.path.startswith('/admin'):
                return redirect(url_for('admin'))
            # API呼び出しの場合はJSONエラーを返す
            return jsonify({"message": "認証が必要です"}), 401
        if not check_session_timeout():
            session.clear()
            if request.path.startswith('/admin'):
                return redirect(url_for('admin'))
            return jsonify({"message": "セッションがタイムアウトしました"}), 401
        update_session_activity()
        return f(*args, **kwargs)
    return decorated_function

def check_login_attempts(user_id):
    if user_id in login_attempts:
        attempts = login_attempts[user_id]
        if attempts['locked_until'] and datetime.datetime.now() < attempts['locked_until']:
            remaining = int((attempts['locked_until'] - datetime.datetime.now()).total_seconds())
            return False, f"アカウントがロックされています。{remaining}秒後に再試行してください。"
        elif attempts['count'] >= MAX_ATTEMPTS:
            login_attempts[user_id]['locked_until'] = datetime.datetime.now() + datetime.timedelta(seconds=LOCK_TIME)
            add_log("ログイン制限", f"user_id: {user_id} が{MAX_ATTEMPTS}回失敗したためロック")
            
            # 異常ログイン通知
            notify_suspicious_login(user_id, request.remote_addr, f"{MAX_ATTEMPTS}回連続失敗")
            return False, f"試行回数が上限に達しました。{LOCK_TIME}秒間ロックされます。"
    return True, ""

def record_login_attempt(user_id, success):
    if success:
        if user_id in login_attempts:
            del login_attempts[user_id]
    else:
        if user_id not in login_attempts:
            login_attempts[user_id] = {'count': 0, 'locked_until': None}
        login_attempts[user_id]['count'] += 1
        
        # 3回失敗で警告通知
        if login_attempts[user_id]['count'] == 3:
            notify_suspicious_login(user_id, request.remote_addr, "3回連続失敗（警告）")

def authenticate_user(user_id, password):
    try:
        client = get_spreadsheet_client()
        sheet = client.open(CONFIG_SPREADSHEET_NAME).worksheet('users')
        records = sheet.get_all_records()
        for user in records:
            if str(user.get('user_id')) == user_id:
                stored_hash = user.get('password_hash', '')
                if stored_hash.startswith('$2b$'):
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                        return user.get('name'), user.get('role', 'staff')
                else:
                    if str(user.get('password')) == password:
                        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        cell = sheet.find(user_id, in_column=1)
                        if cell:
                            sheet.update_cell(cell.row, 2, hashed)
                        return user.get('name'), user.get('role', 'staff')
        return None, None
    except Exception as e:
        print(f"認証エラー: {e}")
        return None, None

@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    current_pass = request.json['current_pass']
    new_pass = request.json['new_pass']
    user_id = session.get('user_id')
    
    if len(new_pass) < 8:
        return jsonify({"message": "パスワードは8文字以上必要です"}), 400
    if not any(c.isdigit() for c in new_pass):
        return jsonify({"message": "パスワードには数字を含めてください"}), 400
    if not any(c.isalpha() for c in new_pass):
        return jsonify({"message": "パスワードには英字を含めてください"}), 400
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(CONFIG_SPREADSHEET_NAME).worksheet('users')
        cell = sheet.find(user_id, in_column=1)
        
        if cell:
            row_idx = cell.row
            stored_hash = sheet.cell(row_idx, 2).value
            is_valid = False
            if stored_hash.startswith('$2b$'):
                is_valid = bcrypt.checkpw(current_pass.encode('utf-8'), stored_hash.encode('utf-8'))
            else:
                is_valid = (str(stored_hash) == current_pass)
            
            if is_valid:
                new_hash = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                sheet.update_cell(row_idx, 2, new_hash)
                add_log("パスワード変更", "自身のパスワードを変更しました")
                return jsonify({"status": "success"})
            else:
                add_log("パスワード変更失敗", "現在のパスワードが間違っています")
                return jsonify({"message": "現在のパスワードが間違っています"}), 400
        else:
            return jsonify({"message": "ユーザーが見つかりません"}), 404
    except Exception as e:
        return jsonify({"message": str(e)}), 500

def load_fields_config():
    """項目設定を読み込み（キャッシュ対応）"""
    def fetch():
        fields = []
        try:
            client = get_spreadsheet_client()
            sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('fields')
            records = sheet.get_all_records()
            records.sort(key=lambda x: x['order'])
            fields = records
        except Exception as e:
            print(f"項目設定読み込みエラー: {e}")
            fields = [{'key': 'name', 'label': '寺院名', 'order': 1}]
        return fields
    
    return get_cached_or_fetch('fields', fetch)

def load_data_from_sheet():
    """寺院データを読み込み（キャッシュ対応）"""
    def fetch():
        data = {}
        try:
            client = get_spreadsheet_client()
            sheet = client.open(DATA_SPREADSHEET_NAME).sheet1
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
    
    return get_cached_or_fetch('temples', fetch)

otera_database = load_data_from_sheet()
field_config = load_fields_config()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        
        can_login, error_msg = check_login_attempts(user_id)
        if not can_login:
            add_log("ログイン失敗", f"user_id: {user_id} - {error_msg}", request.remote_addr)
            return f"""<script>alert('{error_msg}'); window.location.href='/admin';</script>"""
        
        user_name, role = authenticate_user(user_id, password)
        
        if user_name:
            record_login_attempt(user_id, True)
            session.clear()
            session['is_admin'] = True
            session['user_name'] = user_name
            session['user_id'] = user_id
            session['role'] = role
            update_session_activity()
            add_log("ログイン成功", f"user_id: {user_id}", request.remote_addr)
            return redirect(url_for('admin'))
        else:
            record_login_attempt(user_id, False)
            add_log("ログイン失敗", f"user_id: {user_id} - 認証エラー", request.remote_addr)
            return """<script>alert('IDまたはパスワードが違います'); window.location.href='/admin';</script>"""
    
    if session.get('is_admin'):
        if not check_session_timeout():
            session.clear()
            return redirect(url_for('admin'))
        update_session_activity()
        return render_template("admin.html", user_name=session.get('user_name'))
    else:
        return f"""
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
            <style>
                body {{ font-family: -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                .login-container {{ background: white; padding: 40px 30px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); width: 90%; max-width: 400px; text-align: center; }}
                h2 {{ color: #1a237e; margin-top: 0; margin-bottom: 30px; font-size: 1.8rem; }}
                .lock-icon {{ font-size: 3rem; margin-bottom: 20px; }}
                input {{ width: 100%; padding: 15px; margin: 10px 0; border: 2px solid #ddd; border-radius: 8px; font-size: 18px; box-sizing: border-box; transition: border-color 0.3s; }}
                input:focus {{ outline: none; border-color: #667eea; }}
                button {{ width: 100%; padding: 15px; margin-top: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-size: 18px; font-weight: bold; cursor: pointer; transition: transform 0.2s; }}
                button:hover {{ transform: translateY(-2px); }}
                button:active {{ transform: translateY(0); }}
                .back-link {{ display: block; margin-top: 20px; color: #666; text-decoration: none; font-size: 0.9rem; }}
                .security-note {{ margin-top: 20px; padding: 10px; background: #fff3cd; border-left: 4px solid #ffc107; text-align: left; font-size: 0.85rem; color: #856404; }}
            </style>
        </head>
        <body>
            <div class="login-container">
                <div class="lock-icon">🔐</div>
                <form method="post">
                    <h2>セキュアログイン</h2>
                    <input type="text" name="user_id" placeholder="ログインID" required autocomplete="username">
                    <input type="password" name="password" placeholder="パスワード" required autocomplete="current-password">
                    <button type="submit">ログイン</button>
                </form>
                <div class="security-note">
                    <strong>⚠️ セキュリティ</strong><br>
                    3回失敗で警告通知<br>
                    5回失敗で5分間ロック<br>
                    30分無操作で自動ログアウト
                </div>
                <a href="/" class="back-link">← アプリへ戻る</a>
            </div>
        </body>
        </html>
        """

@app.route("/logout")
def logout():
    user_name = session.get('user_name', '不明')
    add_log("ログアウト", f"{user_name} がログアウトしました")
    session.clear()
    return redirect(url_for('admin'))

@app.route("/reload_data", methods=["POST"])
@login_required
def reload_data():
    """データを強制リロード（キャッシュクリア）"""
    global otera_database, field_config
    
    try:
        # キャッシュをクリア
        cache_data['temples']['data'] = None
        cache_data['fields']['data'] = None
        
        otera_database = load_data_from_sheet()
        field_config = load_fields_config()
        add_log("データ更新", f"管理画面からリロードを実行（{len(otera_database)}件）")
        return jsonify({"status": "success", "count": len(otera_database)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get_all_data")
@login_required
def get_all_data():
    """全寺院データを取得（キャッシュ使用）"""
    try:
        # 最新データを取得（キャッシュがあれば使用）
        data = load_data_from_sheet()
        return jsonify(data)
    except Exception as e:
        print(f"データ取得エラー: {e}")
        return jsonify({"error": "データの読み込みに失敗しました"}), 500

@app.route("/get_fields")
def get_fields():
    return jsonify(field_config)

@app.route("/get_logs")
@login_required
def get_logs():
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('logs')
        records = sheet.get_all_records()
        return jsonify(records[-50:][::-1])
    except: 
        return jsonify([])

@app.route("/admin/fields")
@login_required
def admin_fields():
    return render_template("admin_fields.html")

@app.route("/update_fields", methods=["POST"])
@login_required
def update_fields():
    new_fields = request.json['fields']
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('fields')
        sheet.clear()
        sheet.append_row(['key', 'label', 'order'])
        rows = [[f['key'], f['label'], f['order']] for f in new_fields]
        sheet.append_rows(rows)
        global field_config
        field_config = new_fields
        add_log("項目設定変更", f"{len(new_fields)}個の項目を更新")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def get_data_sheet_and_headers():
    client = get_spreadsheet_client()
    sheet = client.open(DATA_SPREADSHEET_NAME).sheet1
    headers = sheet.row_values(1) 
    return sheet, headers

@app.route("/update_temple", methods=["POST"])
@login_required
def update_temple():
    req = request.json
    original_name = req['original_name']
    new_data = req['data']
    
    if not new_data.get('name'):
        return jsonify({"status": "error", "message": "寺院名は必須です"}), 400
    
    try:
        sheet, headers = get_data_sheet_and_headers()
        current_headers = headers
        for key in new_data.keys():
            if key not in current_headers:
                sheet.update_cell(1, len(current_headers) + 1, key)
                current_headers.append(key)
        headers = current_headers

        cell = sheet.find(original_name, in_column=1)
        if cell:
            row_idx = cell.row
            row_data = [new_data.get(h, "") for h in headers]
            sheet.update(f"A{row_idx}", [row_data])
            if original_name in otera_database: 
                del otera_database[original_name]
            otera_database[new_data['name']] = new_data
            
            add_log("編集", f"{original_name} の情報を更新 → {new_data['name']}")
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "not_found"}), 404
    except Exception as e:
        add_log("編集エラー", f"エラー: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/add_temple", methods=["POST"])
@login_required
def add_temple():
    req = request.json
    new_data = req['data']
    name = new_data.get('name')
    
    if not name:
        return jsonify({"status": "error", "message": "寺院名は必須です"}), 400
    if name in otera_database:
        return jsonify({"status": "error", "message": "その名前は既に存在します"}), 400
    
    try:
        sheet, headers = get_data_sheet_and_headers()
        current_headers = headers
        for key in new_data.keys():
            if key not in current_headers:
                sheet.update_cell(1, len(current_headers) + 1, key)
                current_headers.append(key)
        headers = current_headers

        row_data = [new_data.get(h, "") for h in headers]
        sheet.append_row(row_data)
        otera_database[name] = new_data
        
        add_log("追加", f"{name} を新規追加")
        return jsonify({"status": "success"})
    except Exception as e:
        add_log("追加エラー", f"エラー: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/delete_temple", methods=["POST"])
@login_required
def delete_temple():
    name = request.json.get('name')
    try:
        sheet, headers = get_data_sheet_and_headers()
        cell = sheet.find(name, in_column=1)
        if cell:
            sheet.delete_rows(cell.row)
            if name in otera_database: 
                del otera_database[name]
            add_log("削除", f"{name} を削除")
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "not_found"}), 404
    except Exception as e:
        add_log("削除エラー", f"エラー: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def generate_static_summary(temple_info):
    def get(key): return temple_info.get(key) or '記載なし'
    temple_name = get('name')
    temple_name_escaped = temple_name.replace("'", "\\'")
    
    map_url = f"https://www.google.com/maps/search/?api=1&query={temple_info.get('address','')}"
    copy_btn = f"""<button class="copy-btn" onclick="copyToClipboard('{temple_info.get('address','')}')">📋</button>"""
    
    html = f"""<div style="font-size:1.1em; font-weight:bold; color:#1a237e; margin-bottom:10px;">{temple_name} 情報</div>"""
    
    html += f"""<div style="margin-bottom:15px;">
        <script>document.write(addFavoriteButton('{temple_name_escaped}'));</script>
    </div>"""
    
    html += f"""<b>【基本情報】</b><br>"""
    
    for field in field_config:
        key = field['key']
        label = field['label']
        if key == 'name': continue
        val = get(key)
        
        if key == 'address':
            html += f"""{label}: {val} {copy_btn}<br>
            <a href="{map_url}" target="_blank" style="color:#1a237e; font-weight:bold; text-decoration:underline;">📍Googleマップを開く</a><br>"""
        elif key == 'transport':
            html += f"""{label}: <span style="color:#c62828; font-weight:bold;">{val}</span><br>"""
        else:
            html += f"""{label}: {val}<br>"""
    return html

def generate_answer_with_ai(temple_info, user_question):
    info_text = ""
    for field in field_config:
        key = field['key']
        label = field['label']
        val = temple_info.get(key, '記載なし')
        info_text += f"{label}: {val}\n"

    prompt = f"""
    【役割】葬儀施行スタッフ専用の業務支援AI
    【参照データ】
    {info_text}
    ユーザーの質問: 「{user_question}」
    【指示】質問に対する答えのみを簡潔に。挨拶不要。
    """
    try:
        if not GEMINI_API_KEY: 
            return "AI機能は現在利用できません。"
        
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=500
            )
        )
        return response.text
    except Exception as e:
        print(f"AI生成エラー: {e}")
        return f"エラー: AI応答の生成に失敗しました"

@app.route("/get_temple_names", methods=["GET"])
def get_temple_names():
    return jsonify({"names": sorted(list(otera_database.keys()))})

@app.route("/get_sects", methods=["GET"])
def get_sects():
    sects = set()
    for t in otera_database.values():
        if 'sect' in t and t['sect']:
            sects.add(t['sect'])
    return jsonify({"sects": sorted(list(sects))})

@app.route("/search_by_sect", methods=["POST"])
def search_by_sect():
    target_sect = request.json['sect']
    result_list = []
    for temple in otera_database.values():
        if temple.get('sect') == target_sect:
            result_list.append({
                "name": temple['name'],
                "address": temple.get('address', '住所未登録')
            })
    return jsonify({"results": result_list})

@app.route("/ask", methods=["POST"])
def ask():
    user_question = request.json['question']
    found_temple = None
    if user_question in otera_database:
        found_temple = otera_database[user_question]
    else:
        for name in otera_database.keys():
            if name in user_question:
                found_temple = otera_database[name]
                break
    if not found_temple: 
        return jsonify({"answer": "データが見つかりません。"})
    
    # 閲覧回数をカウント
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('access_log')
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sheet.append_row([timestamp, found_temple['name'], user_question])
    except:
        pass  # ログ失敗してもエラーにしない
    
    if user_question == found_temple['name']:
        answer = generate_static_summary(found_temple)
    else:
        answer = generate_answer_with_ai(found_temple, user_question)
    return jsonify({"answer": answer})

# === CSV インポート/エクスポート ===

@app.route("/export_csv")
@login_required
def export_csv():
    """CSVエクスポート"""
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        headers = [f['key'] for f in field_config]
        writer.writerow(headers)
        
        # データ
        for temple in otera_database.values():
            row = [temple.get(h, '') for h in headers]
            writer.writerow(row)
        
        # バイナリに変換
        output.seek(0)
        byte_output = io.BytesIO()
        byte_output.write(output.getvalue().encode('utf-8-sig'))  # BOM付きUTF-8
        byte_output.seek(0)
        
        add_log("CSVエクスポート", f"{len(otera_database)}件のデータをエクスポート")
        
        return send_file(
            byte_output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'temples_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/import_csv", methods=["POST"])
@login_required
def import_csv():
    """CSVインポート"""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "ファイルが選択されていません"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "ファイルが選択されていません"}), 400
    
    try:
        # CSVを読み込み
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
        csv_reader = csv.DictReader(stream)
        
        imported_count = 0
        updated_count = 0
        errors = []
        
        sheet, headers = get_data_sheet_and_headers()
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                name = row.get('name', '').strip()
                if not name:
                    continue
                
                # 既存データか確認
                existing = name in otera_database
                
                # スプレッドシートに書き込み
                if existing:
                    cell = sheet.find(name, in_column=1)
                    if cell:
                        row_data = [row.get(h, '') for h in headers]
                        sheet.update(f"A{cell.row}", [row_data])
                        updated_count += 1
                else:
                    row_data = [row.get(h, '') for h in headers]
                    sheet.append_row(row_data)
                    imported_count += 1
                
                otera_database[name] = dict(row)
                
            except Exception as e:
                errors.append(f"行{row_num}: {str(e)}")
        
        # キャッシュクリア
        cache_data['temples']['data'] = None
        
        add_log("CSVインポート", f"新規{imported_count}件、更新{updated_count}件")
        
        return jsonify({
            "status": "success",
            "imported": imported_count,
            "updated": updated_count,
            "errors": errors
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 権限チェック用デコレーター
def role_required(*allowed_roles):
    """指定された権限を持つユーザーのみアクセス可能"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('is_admin'):
                return jsonify({"message": "認証が必要です"}), 401
            
            user_role = session.get('role', 'viewer')
            if user_role not in allowed_roles:
                return jsonify({"message": "この操作を行う権限がありません"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 既存のエンドポイントに権限制御を追加
@app.route("/update_temple", methods=["POST"])
@login_required
@role_required('admin', 'editor')  # 管理者と編集者のみ
def update_temple():
    # 既存のコード
    pass

@app.route("/add_temple", methods=["POST"])
@login_required
@role_required('admin', 'editor')  # 管理者と編集者のみ
def add_temple():
    # 既存のコード
    pass

@app.route("/delete_temple", methods=["POST"])
@login_required
@role_required('admin', 'editor')  # 管理者と編集者のみ
def delete_temple():
    # 既存のコード
    pass

@app.route("/import_csv", methods=["POST"])
@login_required
@role_required('admin', 'editor')  # 管理者と編集者のみ
def import_csv():
    # 既存のコード
    pass

@app.route("/update_fields", methods=["POST"])
@login_required
@role_required('admin')  # 管理者のみ
def update_fields():
    # 既存のコード
    pass

@app.route("/get_current_user")
@login_required
def get_current_user():
    """現在ログイン中のユーザー情報を取得"""
    return jsonify({
        "user_id": session.get('user_id'),
        "user_name": session.get('user_name'),
        "role": session.get('role', 'viewer')
    })

@app.route("/admin/users")
@login_required
@role_required('admin')
def admin_users():
    """ユーザー管理画面（管理者のみ）"""
    return render_template("admin_users.html")

# ユーザー管理用エンドポイント（新規追加）
@app.route("/get_users")
@login_required
@role_required('admin')
def get_users():
    """ユーザー一覧取得（管理者のみ）"""
    try:
        client = get_spreadsheet_client()
        sheet = client.open(CONFIG_SPREADSHEET_NAME).worksheet('users')
        records = sheet.get_all_records()
        
        # パスワードハッシュを除外
        users = []
        for user in records:
            users.append({
                'user_id': user.get('user_id'),
                'name': user.get('name'),
                'role': user.get('role', 'viewer'),
                'created_at': user.get('created_at', ''),
                'last_login': user.get('last_login', '')
            })
        
        return jsonify({"users": users})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/add_user", methods=["POST"])
@login_required
@role_required('admin')
def add_user():
    """ユーザー追加（管理者のみ）"""
    data = request.json
    user_id = data.get('user_id', '').strip()
    name = data.get('name', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'viewer')
    
    # バリデーション
    if not user_id or not name or not password:
        return jsonify({"message": "必須項目が入力されていません"}), 400
    
    if role not in ['admin', 'editor', 'viewer']:
        return jsonify({"message": "無効な権限レベルです"}), 400
    
    if len(password) < 8:
        return jsonify({"message": "パスワードは8文字以上必要です"}), 400
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(CONFIG_SPREADSHEET_NAME).worksheet('users')
        
        # 重複チェック
        records = sheet.get_all_records()
        if any(str(u.get('user_id')) == user_id for u in records):
            return jsonify({"message": "このユーザーIDは既に使用されています"}), 400
        
        # パスワードハッシュ化
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # 追加
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sheet.append_row([user_id, hashed, name, role, timestamp, ''])
        
        add_log("ユーザー追加", f"{name}（{role}）を追加")
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route("/admin/users")
@login_required
@role_required('admin')
def admin_users():
    """ユーザー管理画面（管理者のみ）"""
    return render_template("admin_users.html")

@app.route("/update_user_role", methods=["POST"])
@login_required
@role_required('admin')
def update_user_role():
    """ユーザー権限変更（管理者のみ）"""
    data = request.json
    user_id = data.get('user_id')
    new_role = data.get('role')
    
    if new_role not in ['admin', 'editor', 'viewer']:
        return jsonify({"message": "無効な権限レベルです"}), 400
    
    # 自分自身の権限変更を防止
    if session.get('user_id') == user_id:
        return jsonify({"message": "自分自身の権限は変更できません"}), 400
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(CONFIG_SPREADSHEET_NAME).worksheet('users')
        
        cell = sheet.find(user_id, in_column=1)
        if cell:
            sheet.update_cell(cell.row, 4, new_role)  # role列を更新
            add_log("権限変更", f"{user_id} の権限を {new_role} に変更")
            return jsonify({"status": "success"})
        else:
            return jsonify({"message": "ユーザーが見つかりません"}), 404
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route("/delete_user", methods=["POST"])
@login_required
@role_required('admin')
def delete_user():
    """ユーザー削除（管理者のみ）"""
    user_id = request.json.get('user_id')
    
    # 自分自身の削除を防止
    if session.get('user_id') == user_id:
        return jsonify({"message": "自分自身は削除できません"}), 400
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(CONFIG_SPREADSHEET_NAME).worksheet('users')
        
        cell = sheet.find(user_id, in_column=1)
        if cell:
            user_name = sheet.cell(cell.row, 3).value
            sheet.delete_rows(cell.row)
            add_log("ユーザー削除", f"{user_name}（{user_id}）を削除")
            return jsonify({"status": "success"})
        else:
            return jsonify({"message": "ユーザーが見つかりません"}), 404
    except Exception as e:
        return jsonify({"message": str(e)}), 500

# 現在のユーザー情報を取得
@app.route("/get_current_user")
@login_required
def get_current_user():
    """現在ログイン中のユーザー情報を取得"""
    return jsonify({
        "user_id": session.get('user_id'),
        "user_name": session.get('user_name'),
        "role": session.get('role', 'viewer')
    })

# === 検索機能 ===

@app.route("/search_temples", methods=["POST"])
def search_temples():
    """フリーワード検索"""
    keyword = request.json.get('keyword', '').strip().lower()
    
    if not keyword:
        return jsonify({"results": []})
    
    results = []
    for temple in otera_database.values():
        # 名前、宗派、住所で検索
        searchable = f"{temple.get('name', '')} {temple.get('sect', '')} {temple.get('address', '')}".lower()
        
        if keyword in searchable:
            results.append({
                "name": temple.get('name'),
                "sect": temple.get('sect', ''),
                "address": temple.get('address', '')
            })
    
    return jsonify({"results": results[:20]})  # 最大20件

# === アクセス統計 ===

@app.route("/get_access_stats")
@login_required
def get_access_stats():
    """閲覧回数統計"""
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('access_log')
        records = sheet.get_all_records()
        
        # 集計
        temple_counts = {}
        for record in records:
            temple_name = record.get('temple_name', '')
            if temple_name:
                temple_counts[temple_name] = temple_counts.get(temple_name, 0) + 1
        
        # ソート
        sorted_stats = sorted(temple_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify({
            "stats": [{"name": name, "count": count} for name, count in sorted_stats]
        })
    except:
        return jsonify({"stats": []})

# === コメント・メモ機能 ===

@app.route("/get_comments/<temple_name>")
def get_comments(temple_name):
    """特定寺院のコメント取得"""
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('comments')
        records = sheet.get_all_records()
        
        comments = [r for r in records if r.get('temple_name') == temple_name]
        comments.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({"comments": comments})
    except:
        return jsonify({"comments": []})

@app.route("/add_comment", methods=["POST"])
@login_required
def add_comment():
    """コメント追加"""
    temple_name = request.json.get('temple_name')
    comment_text = request.json.get('comment')
    
    if not temple_name or not comment_text:
        return jsonify({"status": "error", "message": "必須項目が入力されていません"}), 400
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('comments')
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user_name = session.get('user_name', '不明')
        
        sheet.append_row([timestamp, temple_name, user_name, comment_text])
        
        add_log("コメント追加", f"{temple_name} にコメントを追加")
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/delete_comment", methods=["POST"])
@login_required
def delete_comment():
    """コメント削除"""
    row_number = request.json.get('row_number')
    
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('comments')
        sheet.delete_rows(row_number)
        
        add_log("コメント削除", f"行{row_number}のコメントを削除")
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

if __name__ == "__main__":
    app.run(debug=True, port=5001)
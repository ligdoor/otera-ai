import os
import json
import datetime
import secrets
from functools import wraps
from dotenv import load_dotenv
from google import genai
from google.genai import types
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import bcrypt

load_dotenv()

# --- 設定 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))  # 強力なランダムキー
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=30)  # セッション30分
app.config['SESSION_COOKIE_HTTPONLY'] = True  # XSS対策
app.config['SESSION_COOKIE_SECURE'] = True if os.environ.get('FLASK_ENV') == 'production' else False  # HTTPS強制（本番環境）
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF対策

DATA_SPREADSHEET_NAME = "otera_data"
CONFIG_SPREADSHEET_NAME = "otera_admin_config"

gc = None 

# ログイン試行記録（メモリ内保存、本番ではRedis推奨）
login_attempts = {}
LOCK_TIME = 300  # ロック時間（秒）5分
MAX_ATTEMPTS = 5  # 最大試行回数

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

# ログ記録
def add_log(action, details, ip_address=None):
    try:
        user_name = session.get('user_name', '不明')
        user_id = session.get('user_id', '不明')
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('logs')
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ip = ip_address or request.remote_addr
        sheet.append_row([timestamp, user_name, user_id, action, details, ip])
    except Exception as e:
        print(f"ログ記録エラー: {e}")

# セッション更新（最終アクセス時刻を記録）
def update_session_activity():
    session['last_activity'] = datetime.datetime.now().timestamp()
    session.permanent = True

# セッションタイムアウトチェック
def check_session_timeout():
    if 'last_activity' in session:
        elapsed = datetime.datetime.now().timestamp() - session['last_activity']
        if elapsed > 1800:  # 30分 = 1800秒
            session.clear()
            return False
    return True

# 認証必須デコレータ
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({"message": "認証が必要です"}), 401
        if not check_session_timeout():
            return jsonify({"message": "セッションがタイムアウトしました"}), 401
        update_session_activity()
        return f(*args, **kwargs)
    return decorated_function

# ログイン試行回数チェック
def check_login_attempts(user_id):
    if user_id in login_attempts:
        attempts = login_attempts[user_id]
        if attempts['locked_until'] and datetime.datetime.now() < attempts['locked_until']:
            remaining = int((attempts['locked_until'] - datetime.datetime.now()).total_seconds())
            return False, f"アカウントがロックされています。{remaining}秒後に再試行してください。"
        elif attempts['count'] >= MAX_ATTEMPTS:
            login_attempts[user_id]['locked_until'] = datetime.datetime.now() + datetime.timedelta(seconds=LOCK_TIME)
            add_log("ログイン制限", f"user_id: {user_id} が{MAX_ATTEMPTS}回失敗したためロック")
            return False, f"試行回数が上限に達しました。{LOCK_TIME}秒間ロックされます。"
    return True, ""

# ログイン試行回数を記録
def record_login_attempt(user_id, success):
    if success:
        if user_id in login_attempts:
            del login_attempts[user_id]
    else:
        if user_id not in login_attempts:
            login_attempts[user_id] = {'count': 0, 'locked_until': None}
        login_attempts[user_id]['count'] += 1

# ユーザー認証（ログイン用）
def authenticate_user(user_id, password):
    try:
        client = get_spreadsheet_client()
        sheet = client.open(CONFIG_SPREADSHEET_NAME).worksheet('users')
        records = sheet.get_all_records()
        for user in records:
            if str(user.get('user_id')) == user_id:
                stored_hash = user.get('password_hash', '')
                # 平文パスワードとの互換性チェック（移行期間用）
                if stored_hash.startswith('$2b$'):  # bcryptハッシュ
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                        return user.get('name'), user.get('role', 'staff')
                else:  # 旧形式（平文）
                    if str(user.get('password')) == password:
                        # 初回ログイン時にハッシュ化
                        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        # パスワードハッシュを更新
                        cell = sheet.find(user_id, in_column=1)
                        if cell:
                            sheet.update_cell(cell.row, 2, hashed)
                        return user.get('name'), user.get('role', 'staff')
        return None, None
    except Exception as e:
        print(f"認証エラー: {e}")
        return None, None

# パスワード変更処理
@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    current_pass = request.json['current_pass']
    new_pass = request.json['new_pass']
    user_id = session.get('user_id')
    
    # パスワード強度チェック
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
            
            # 現在のパスワード確認
            is_valid = False
            if stored_hash.startswith('$2b$'):
                is_valid = bcrypt.checkpw(current_pass.encode('utf-8'), stored_hash.encode('utf-8'))
            else:
                is_valid = (str(stored_hash) == current_pass)
            
            if is_valid:
                # 新しいパスワードをハッシュ化
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

# 項目定義
def load_fields_config():
    fields = []
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).worksheet('fields')
        records = sheet.get_all_records()
        records.sort(key=lambda x: x['order'])
        fields = records
    except:
        fields = [{'key': 'name', 'label': '寺院名', 'order': 1}]
    return fields

def load_data_from_sheet():
    data = {}
    try:
        client = get_spreadsheet_client()
        sheet = client.open(DATA_SPREADSHEET_NAME).sheet1
        records = sheet.get_all_records()
        for row in records:
            if 'name' in row and row['name']:
                clean_row = {k: str(v).strip() for k, v in row.items()}
                data[clean_row['name']] = clean_row
        print("★データ更新完了")
    except Exception as e:
        print(f"読み込みエラー: {e}")
    return data

otera_database = load_data_from_sheet()
field_config = load_fields_config()

# --- ルーティング ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        
        # ログイン試行回数チェック
        can_login, error_msg = check_login_attempts(user_id)
        if not can_login:
            add_log("ログイン失敗", f"user_id: {user_id} - {error_msg}", request.remote_addr)
            return f"""<script>alert('{error_msg}'); window.location.href='/admin';</script>"""
        
        user_name, role = authenticate_user(user_id, password)
        
        if user_name:
            record_login_attempt(user_id, True)
            session.clear()  # 既存セッションをクリア
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
                    5回失敗すると5分間ロックされます<br>
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
    global otera_database, field_config
    otera_database = load_data_from_sheet()
    field_config = load_fields_config()
    add_log("データ更新", "管理画面からリロードを実行")
    return jsonify({"status": "success"})

@app.route("/get_all_data")
@login_required
def get_all_data():
    return jsonify(otera_database)

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
        return jsonify(records[-50:][::-1])  # 最新50件
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
    
    # 入力検証
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

# --- アプリ機能 ---

def generate_static_summary(temple_info):
    def get(key): return temple_info.get(key) or '記載なし'
    temple_name = get('name')
    map_url = f"https://www.google.com/maps/search/?api=1&query={temple_info.get('address','')}"
    copy_btn = f"""<button class="copy-btn" onclick="copyToClipboard('{temple_info.get('address','')}')">📋</button>"""
    
    html = f"""<div style="font-size:1.1em; font-weight:bold; color:#1a237e; margin-bottom:10px;">{temple_name} 情報</div>"""
    
    # お気に入りボタンを追加
    html += f"""<div style="margin-bottom:15px;">
        <script>document.write(addFavoriteButton('{temple_name.replace("'", "\\'")}'));</script>
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
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"エラー: {e}"

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
    if user_question == found_temple['name']:
        answer = generate_static_summary(found_temple)
    else:
        answer = generate_answer_with_ai(found_temple, user_question)
    return jsonify({"answer": answer})

# セキュリティヘッダー追加
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

if __name__ == "__main__":
    # 本番環境ではdebug=Falseにすること
    app.run(debug=True, port=5001)
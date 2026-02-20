import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.mail_server = os.getenv('MAIL_SERVER')
        self.mail_port = int(os.getenv('MAIL_PORT', 587))
        self.mail_username = os.getenv('MAIL_USERNAME')
        self.mail_password = os.getenv('MAIL_PASSWORD')
        self.admin_email = os.getenv('ADMIN_EMAIL')
    
    def send_registration_notification(self, user_data):
        """新規登録通知を管理者に送信"""
        try:
            subject = "【寺院管理システム】新規ユーザー登録申請"
            
            body = f"""
新しいユーザーから登録申請がありました。

【申請者情報】
氏名: {user_data.get('name', '未設定')}
メールアドレス: {user_data.get('email', '未設定')}
所属: {user_data.get('department', '未設定')}
備考: {user_data.get('notes', 'なし')}

管理画面から承認または却下の処理をお願いします。

※このメールは自動送信されています
"""
            
            return self._send_email(self.admin_email, subject, body)
        except Exception as e:
            logger.debug(f"メール送信エラー: {e}")
            return False
    
    def send_approval_notification(self, user_email, username):
        """承認通知をユーザーに送信"""
        try:
            subject = "【寺院管理システム】アカウントが承認されました"
            
            body = f"""
{username} 様

アカウントの登録申請が承認されました。
以下のURLからログインしてご利用いただけます。

ログインURL: https://otera-database.fly.dev

※このメールは自動送信されています
"""
            
            return self._send_email(user_email, subject, body)
        except Exception as e:
            logger.debug(f"メール送信エラー: {e}")
            return False
    
    def send_rejection_notification(self, user_email, username, reason=""):
        """却下通知をユーザーに送信"""
        try:
            subject = "【寺院管理システム】アカウント登録申請について"
            
            body = f"""
{username} 様

誠に申し訳ございませんが、アカウントの登録申請を承認することができませんでした。

理由: {reason if reason else '管理者にお問い合わせください'}

ご不明な点がございましたら、管理者までお問い合わせください。

※このメールは自動送信されています
"""
            
            return self._send_email(user_email, subject, body)
        except Exception as e:
            logger.debug(f"メール送信エラー: {e}")
            return False
    
    # ============================================================
    # ★★★ パスワードリセットメール送信機能（ここから追加） ★★★
    # ============================================================
    
    def send_password_reset_email(self, to_email, reset_link, user_name=None):
        """
        パスワードリセットメールを送信
        
        Args:
            to_email: 送信先メールアドレス
            reset_link: パスワードリセット用URL
            user_name: ユーザー名（任意）
        
        Returns:
            bool: 送信成功ならTrue
        """
        try:
            subject = "【寺院管理システム】パスワードリセットのご案内"
            
            # HTMLメール本文
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', 'Hiragino Sans', Meiryo, sans-serif;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f9f9f9;
                    }}
                    .content {{
                        background-color: white;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        text-align: center;
                        color: #4CAF50;
                        margin-bottom: 20px;
                    }}
                    .button {{
                        display: inline-block;
                        padding: 15px 30px;
                        background-color: #4CAF50;
                        color: white !important;
                        text-decoration: none;
                        border-radius: 5px;
                        margin: 20px 0;
                        font-weight: bold;
                    }}
                    .warning {{
                        background-color: #fff3cd;
                        border-left: 4px solid #ffc107;
                        padding: 15px;
                        margin: 20px 0;
                    }}
                    .footer {{
                        text-align: center;
                        color: #666;
                        font-size: 12px;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #ddd;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="content">
                        <h2 class="header">パスワードリセットのご案内</h2>
                        
                        <p>{'こんにちは、' + user_name + '様。' if user_name else 'こんにちは。'}</p>
                        
                        <p>寺院管理システムのパスワードリセットリクエストを受け付けました。</p>
                        
                        <p>以下のボタンをクリックして、新しいパスワードを設定してください：</p>
                        
                        <div style="text-align: center;">
                            <a href="{reset_link}" class="button">パスワードをリセット</a>
                        </div>
                        
                        <p>または、以下のURLをブラウザにコピー&ペーストしてください：</p>
                        <p style="word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
                            {reset_link}
                        </p>
                        
                        <div class="warning">
                            <strong>⚠️ 重要な注意事項</strong>
                            <ul>
                                <li>このリンクの有効期限は <strong>1時間</strong> です</li>
                                <li>このリンクは <strong>1回のみ</strong> 使用可能です</li>
                                <li>心当たりがない場合は、このメールを無視してください</li>
                            </ul>
                        </div>
                        
                        <div class="footer">
                            <p>このメールに心当たりがない場合は、第三者がメールアドレスを誤って入力した可能性があります。<br>
                            その場合は、このメールを破棄していただいて問題ありません。</p>
                            <p>寺院管理システム<br>
                            送信日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # テキスト版（HTMLが表示できない環境用）
            text_body = f"""
寺院管理システム - パスワードリセットのご案内

{'こんにちは、' + user_name + '様。' if user_name else 'こんにちは。'}

パスワードリセットリクエストを受け付けました。

以下のURLにアクセスして、新しいパスワードを設定してください：
{reset_link}

【重要な注意事項】
・このリンクの有効期限は1時間です
・このリンクは1回のみ使用可能です
・心当たりがない場合は、このメールを無視してください

このメールに心当たりがない場合は、第三者がメールアドレスを誤って入力した可能性があります。
その場合は、このメールを破棄していただいて問題ありません。

---
寺院管理システム
送信日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}
            """
            
            # HTMLメール送信
            return self._send_html_email(to_email, subject, html_body, text_body)
            
        except Exception as e:
            logger.debug(f"パスワードリセットメール送信エラー: {e}")
            return False
    
    def _send_email(self, to_email, subject, body):
        """実際のメール送信処理（テキストのみ）"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.mail_username
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.mail_server, self.mail_port)
            server.starttls()
            server.login(self.mail_username, self.mail_password)
            server.send_message(msg)
            server.quit()
            
            logger.debug(f"メール送信成功: {to_email}")
            return True
        except Exception as e:
            logger.debug(f"メール送信失敗: {e}")
            return False
    
    def _send_html_email(self, to_email, subject, html_body, text_body):
        """HTMLメール送信処理（テキスト版も含む）"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.mail_username
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # テキストとHTML両方を添付
            part1 = MIMEText(text_body, 'plain', 'utf-8')
            part2 = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)
            
            server = smtplib.SMTP(self.mail_server, self.mail_port)
            server.starttls()
            server.login(self.mail_username, self.mail_password)
            server.send_message(msg)
            server.quit()
            
            logger.debug(f"パスワードリセットメール送信成功: {to_email}")
            return True
        except Exception as e:
            logger.debug(f"HTMLメール送信失敗: {e}")
            return False

# シングルトンインスタンス
email_service = EmailService()
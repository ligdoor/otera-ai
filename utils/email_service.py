import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

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
            print(f"メール送信エラー: {e}")
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
            print(f"メール送信エラー: {e}")
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
            print(f"メール送信エラー: {e}")
            return False
    
    def _send_email(self, to_email, subject, body):
        """実際のメール送信処理"""
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
            
            print(f"メール送信成功: {to_email}")
            return True
        except Exception as e:
            print(f"メール送信失敗: {e}")
            return False

# シングルトンインスタンス
email_service = EmailService()
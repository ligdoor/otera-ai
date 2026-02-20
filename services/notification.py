import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from config import Config
from utils.helpers import get_jst_timestamp

logger = logging.getLogger(__name__)


def send_slack_notification(message, emoji=":bell:"):
    """Slack通知を送信"""
    if not Config.SLACK_WEBHOOK_URL:
        return
    
    try:
        payload = {
            "text": f"{emoji} {message}",
            "username": "寺院管理システム",
            "icon_emoji": ":temple:"
        }
        response = requests.post(Config.SLACK_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 200:
            logger.info(f"✅ Slack通知送信成功: {message}")
        else:
            logger.error(f"❌ Slack通知失敗: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Slack通知エラー: {e}")

def send_email_alert(subject, body, to_email=None):
    """メール通知を送信"""
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD or not Config.ADMIN_EMAIL:
        return
    
    recipient = to_email or Config.ADMIN_EMAIL
    
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.SMTP_USER
        msg['To'] = recipient
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ メール送信成功: {subject}")
    except Exception as e:
        logger.error(f"❌ メール送信エラー: {e}")

def notify_suspicious_login(user_id, ip_address, reason):
    """異常ログイン時の通知"""
    timestamp = get_jst_timestamp()
    
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
    timestamp = get_jst_timestamp()
    
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
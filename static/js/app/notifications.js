// ========================================
// アプリ - 通知機能
// ========================================

let unreadCount = 0;

// 未読数読み込み
async function loadUnreadCount() {
    try {
        const res = await fetch('/api/notifications?unread_only=true');
        const data = await res.json();
        unreadCount = data.unread_count || 0;
        updateNotificationBadge();
    } catch (e) {
        console.error('未読数取得エラー:', e);
    }
}

// 通知バッジ更新
function updateNotificationBadge() {
    const badge = document.getElementById('notification-badge');
    if (unreadCount > 0) {
        badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
        badge.style.display = 'flex';
    } else {
        badge.style.display = 'none';
    }
}

// 通知モーダルを開く
async function openNotifications() {
    const modal = document.getElementById('notification-modal');
    const list = document.getElementById('notification-list');
    
    modal.classList.add('show');
    list.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">読み込み中...</div>';
    
    try {
        const res = await fetch('/api/notifications');
        const data = await res.json();
        
        if (data.notifications.length === 0) {
            list.innerHTML = '<div class="notification-empty">📭 通知はありません</div>';
            return;
        }
        
        list.innerHTML = data.notifications.map(notif => {
            const isUnread = !notif.is_read;
            const time = formatNotificationTime(notif.created_at);
            const icon = getNotificationIcon(notif.type);
            
            return `
                <div class="notification-item ${isUnread ? 'unread' : ''}" onclick="markNotificationRead(${notif.id})">
                    <div class="notification-item-header">
                        <div class="notification-title">
                            <span class="notification-type-icon">${icon}</span>
                            ${notif.title}
                        </div>
                        <div class="notification-time">${time}</div>
                    </div>
                    <div class="notification-message">${notif.message}</div>
                    ${notif.related_temple ? `<div style="margin-top: 8px; color: #667eea; font-size: 0.85rem;">🏯 ${notif.related_temple}</div>` : ''}
                </div>
            `;
        }).join('');
        
    } catch (e) {
        console.error('通知取得エラー:', e);
        list.innerHTML = '<div class="notification-empty">❌ 通知の取得に失敗しました</div>';
    }
}

// 通知モーダルを閉じる
function closeNotifications(event) {
    if (!event || event.target.id === 'notification-modal') {
        document.getElementById('notification-modal').classList.remove('show');
    }
}

// 通知を既読にする
async function markNotificationRead(notificationId) {
    try {
        await fetch(`/api/notifications/${notificationId}/read`, {
            method: 'POST'
        });
        
        unreadCount = Math.max(0, unreadCount - 1);
        updateNotificationBadge();
        openNotifications();
    } catch (e) {
        console.error('既読処理エラー:', e);
    }
}

// すべて既読にする
async function markAllRead() {
    try {
        await fetch('/api/notifications/read-all', {
            method: 'POST'
        });
        
        unreadCount = 0;
        updateNotificationBadge();
        openNotifications();
    } catch (e) {
        console.error('一括既読エラー:', e);
    }
}

// 通知アイコン取得
function getNotificationIcon(type) {
    const icons = {
        'info': 'ℹ️',
        'success': '✅',
        'warning': '⚠️',
        'update': '🔄'
    };
    return icons[type] || 'ℹ️';
}

// 時刻フォーマット
function formatNotificationTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'たった今';
    if (minutes < 60) return `${minutes}分前`;
    if (hours < 24) return `${hours}時間前`;
    if (days < 7) return `${days}日前`;
    
    return date.toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' });
}
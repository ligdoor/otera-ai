/**
 * メンテナンスモード管理
 */

// ページ読み込み時に状態を取得
document.addEventListener('DOMContentLoaded', function() {
    loadMaintenanceStatus();
    
    // トグルスイッチのイベントリスナーを設定
    const toggleSwitch = document.getElementById('maintenanceToggle');
    if (toggleSwitch) {
        toggleSwitch.addEventListener('change', toggleMaintenance);
    }
});

/**
 * メンテナンスモードの状態を取得して表示
 */
async function loadMaintenanceStatus() {
    try {
        const response = await fetch('/api/maintenance/status');
        const data = await response.json();
        
        console.log('📡 メンテナンス状態取得:', data);
        updateMaintenanceUI(data.enabled);
    } catch (error) {
        console.error('❌ メンテナンス状態の取得に失敗:', error);
        updateMaintenanceStatus('エラー');
    }
}

/**
 * メンテナンスモードのトグル
 */
async function toggleMaintenance() {
    const toggleSwitch = document.getElementById('maintenanceToggle');
    const originalState = !toggleSwitch.checked; // トグル前の状態
    
    try {
        console.log('🔄 メンテナンスモード切り替え開始...');
        
        const response = await fetch('/api/maintenance/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        console.log('📥 レスポンス:', data);
        
        if (data.success) {
            // 成功: UIを更新
            updateMaintenanceUI(data.enabled);
            showNotification(data.message, 'success');
        } else {
            // 失敗: 元の状態に戻す
            toggleSwitch.checked = originalState;
            showNotification(data.message || 'メンテナンスモードの切り替えに失敗しました', 'error');
        }
    } catch (error) {
        console.error('❌ メンテナンスモード切り替えエラー:', error);
        // エラー: 元の状態に戻す
        toggleSwitch.checked = originalState;
        showNotification('メンテナンスモードの切り替えに失敗しました', 'error');
    }
}

/**
 * メンテナンスモードのUIを更新
 * @param {boolean} enabled - メンテナンスモードが有効かどうか
 */
function updateMaintenanceUI(enabled) {
    console.log('🎨 UIを更新:', enabled ? 'ON' : 'OFF');
    
    // トグルスイッチの状態を更新
    const toggleSwitch = document.getElementById('maintenanceToggle');
    if (toggleSwitch) {
        toggleSwitch.checked = enabled;
    }
    
    // ステータステキストを更新
    updateMaintenanceStatus(enabled ? 'ON' : 'OFF');
}

/**
 * メンテナンスステータステキストを更新
 * @param {string} status - 表示するステータス ('ON', 'OFF', 'エラー', '読み込み中...')
 */
function updateMaintenanceStatus(status) {
    const statusElement = document.getElementById('maintenanceStatus');
    if (!statusElement) return;
    
    statusElement.textContent = status;
    
    // ステータスに応じてクラスを設定
    statusElement.className = 'status-text';
    if (status === 'ON') {
        statusElement.classList.add('status-on');
    } else if (status === 'OFF') {
        statusElement.classList.add('status-off');
    } else if (status === 'エラー') {
        statusElement.classList.add('status-error');
    }
}

/**
 * 通知メッセージを表示
 * @param {string} message - 表示するメッセージ
 * @param {string} type - メッセージのタイプ ('success' or 'error')
 */
function showNotification(message, type) {
    console.log(`📢 通知: ${message} (${type})`);
    
    // 既存の通知があれば削除
    const existingNotification = document.querySelector('.maintenance-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 新しい通知を作成
    const notification = document.createElement('div');
    notification.className = `maintenance-notification ${type}`;
    notification.innerHTML = `
        <span class="notification-icon">${type === 'success' ? '✅' : '❌'}</span>
        <span class="notification-message">${message}</span>
    `;
    
    // メンテナンスセクションの後に挿入
    const maintenanceSection = document.getElementById('maintenance-section');
    if (maintenanceSection && maintenanceSection.parentNode) {
        maintenanceSection.parentNode.insertBefore(notification, maintenanceSection.nextSibling);
    } else {
        document.body.insertBefore(notification, document.body.firstChild);
    }
    
    // 3秒後に自動で消す
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}
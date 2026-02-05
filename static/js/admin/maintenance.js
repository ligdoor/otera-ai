// メンテナンスモード管理

// ページロード時にメンテナンスモード状態を取得
async function loadMaintenanceStatus() {
    try {
        const response = await fetch('/api/maintenance/status');
        const data = await response.json();
        
        const toggle = document.getElementById('maintenanceToggle');
        const status = document.getElementById('maintenanceStatus');
        
        toggle.checked = data.maintenance_mode;
        updateStatusText(data.maintenance_mode);
        
    } catch (error) {
        console.error('メンテナンスモード状態取得エラー:', error);
        document.getElementById('maintenanceStatus').textContent = '状態取得エラー';
    }
}

// ステータステキストを更新
function updateStatusText(isMaintenanceMode) {
    const status = document.getElementById('maintenanceStatus');
    status.textContent = isMaintenanceMode ? 'メンテナンスモード: ON' : 'メンテナンスモード: OFF';
    status.style.color = isMaintenanceMode ? '#f44336' : '#4caf50';
}

// トグルスイッチの変更を監視
document.addEventListener('DOMContentLoaded', function() {
    const toggle = document.getElementById('maintenanceToggle');
    
    if (toggle) {
        toggle.addEventListener('change', async function() {
            const status = document.getElementById('maintenanceStatus');
            const originalState = this.checked;
            status.textContent = '切り替え中...';
            status.style.color = '#666';
            
            try {
                const response = await fetch('/api/maintenance/toggle', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    updateStatusText(data.maintenance_mode);
                    
                    const message = data.maintenance_mode ? 
                        '⚠️ メンテナンスモードを有効にしました\n\n一般ユーザーはサイトにアクセスできなくなります。' : 
                        '✅ メンテナンスモードを解除しました\n\nサイトは通常通り利用可能です。';
                    
                    alert(message);
                } else {
                    alert('エラー: ' + data.error);
                    this.checked = !originalState;
                    updateStatusText(!originalState);
                }
            } catch (error) {
                console.error('メンテナンスモード切り替えエラー:', error);
                alert('エラーが発生しました\n\n' + error.message);
                this.checked = !originalState;
                updateStatusText(!originalState);
            }
        });
        
        // 初期状態をロード
        loadMaintenanceStatus();
    }
});

// 管理者権限がある場合のみメンテナンスセクションを表示
// この関数は main.js から呼び出されることを想定
function showMaintenanceSectionIfAdmin(userPermission) {
    const maintenanceSection = document.getElementById('maintenance-section');
    if (maintenanceSection && userPermission === 'admin') {
        maintenanceSection.style.display = 'block';
    }
}
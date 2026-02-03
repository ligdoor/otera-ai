// ログモーダル関連
let currentFilter = 'all';
let allLogs = [];

// ログモーダルを開く
async function openLogModal() {
    document.getElementById('log-modal').classList.add('show');
    await loadLogsForModal();
}

// ログをロード（モーダル用）
async function loadLogsForModal() {
    const tbody = document.getElementById('log-modal-list');
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:40px; color:#999;">読み込み中...</td></tr>';
    
    try {
        const res = await fetch('/get_logs');
        const data = await res.json();
        
        // ★ 修正: レスポンス形式に応じて処理
        if (Array.isArray(data)) {
            allLogs = data;
        } else if (data.logs && Array.isArray(data.logs)) {
            allLogs = data.logs;
        } else {
            allLogs = [];
        }
        
        console.log('取得したログ:', allLogs); // ★ デバッグ用
        displayFilteredLogs();
    } catch (e) {
        console.error('ログ取得エラー:', e);
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:40px; color:#f44336;">❌ ログの取得に失敗しました</td></tr>';
    }
}

// フィルタリングされたログを表示
function displayFilteredLogs() {
    const tbody = document.getElementById('log-modal-list');
    
    let filteredLogs = allLogs;
    if (currentFilter !== 'all') {
        filteredLogs = allLogs.filter(log => {
            const action = (log.action || log.操作 || '').toLowerCase();
            if (currentFilter === 'login') return action.includes('ログイン');
            if (currentFilter === 'edit') return action.includes('編集') || action.includes('更新');
            if (currentFilter === 'delete') return action.includes('削除');
            return true;
        });
    }
    
    if (filteredLogs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:40px; color:#999;">📭 該当するログがありません</td></tr>';
        return;
    }
    
    tbody.innerHTML = '';
    filteredLogs.forEach(log => {
        const tr = document.createElement('tr');
        
        // ★ 修正: 様々なキー名に対応
        const timestamp = log.timestamp || log.日時 || log.created_at || '';
        const user = log.user || log.user_name || log.担当 || '不明';
        const action = log.action || log.操作 || '';
        const details = log.details || log.詳細 || '';
        
        let badgeClass = 'update';
        const actionLower = action.toLowerCase();
        if (actionLower.includes('編集')) badgeClass = 'edit';
        else if (actionLower.includes('追加')) badgeClass = 'add';
        else if (actionLower.includes('削除')) badgeClass = 'delete';
        else if (actionLower.includes('ログイン')) badgeClass = 'update';
        
        tr.innerHTML = `
            <td>${timestamp}</td>
            <td>${user}</td>
            <td><span class="log-badge ${badgeClass}">${action}</span></td>
            <td>${details}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ログをフィルタ
function filterLogs(filter) {
    currentFilter = filter;
    
    // フィルタボタンのアクティブ状態を更新
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.filter === filter) {
            btn.classList.add('active');
        }
    });
    
    displayFilteredLogs();
}

// ログを再読み込み
async function refreshLogs() {
    await loadLogsForModal();
}
// ========================================
// 寺院選択機能
// ========================================

let allTemplesData = {}; // 全寺院データ
let currentUserRole = null; // ユーザー権限

// ページ読み込み時の初期化
document.addEventListener('DOMContentLoaded', function() {
    const templeSelect = document.getElementById('temple-select');
    const displayArea = document.getElementById('temple-list');
    
    // ページ読み込み時に寺院リストを取得
    loadTempleSelectList();
    
    // セレクトボックスの変更イベント
    if (templeSelect) {
        templeSelect.addEventListener('change', async function() {
            const templeName = this.options[this.selectedIndex].text;
            
            if (this.value) {
                // 選択された寺院を表示
                await displaySelectedTemple(templeName);
                displayArea.style.display = 'block';
            } else {
                // 選択解除時は非表示に
                displayArea.style.display = 'none';
                displayArea.innerHTML = '';
            }
        });
    }
});

// 寺院リストを取得してセレクトボックスに設定
async function loadTempleSelectList() {
    try {
        // ユーザー権限を取得
        const userRes = await fetch('/get_current_user');
        const userData = await userRes.json();
        currentUserRole = userData.role;
        
        // 全寺院データを取得
        const res = await fetch('/get_all_data');
        if (!res.ok) throw new Error('データ取得失敗');
        
        allTemplesData = await res.json();
        
        const templeSelect = document.getElementById('temple-select');
        
        if (!templeSelect) {
            console.error('temple-select要素が見つかりません');
            return;
        }
        
        // 既存のオプションをクリア(最初の選択肢は残す)
        while (templeSelect.options.length > 1) {
            templeSelect.remove(1);
        }
        
        // 寺院リストをセレクトボックスに追加
        const temples = Object.values(allTemplesData).sort((a, b) => {
            return a.name.localeCompare(b.name);
        });
        
        if (temples.length > 0) {
            temples.forEach(temple => {
                const option = document.createElement('option');
                option.value = temple.name;
                option.textContent = temple.name;
                templeSelect.appendChild(option);
            });
            console.log(`✅ ${temples.length}件の寺院を読み込みました`);
        } else {
            console.log('⚠️ 寺院が見つかりませんでした');
        }
    } catch (error) {
        console.error('❌ 寺院リスト取得エラー:', error);
        alert('寺院リストの取得に失敗しました');
    }
}

// 選択された寺院を表示
async function displaySelectedTemple(templeName) {
    const list = document.getElementById('temple-list');
    
    // 全寺院データがまだない場合は取得
    if (Object.keys(allTemplesData).length === 0) {
        const res = await fetch('/get_all_data');
        allTemplesData = await res.json();
    }
    
    // ユーザー権限がまだない場合は取得
    if (!currentUserRole) {
        const userRes = await fetch('/get_current_user');
        const userData = await userRes.json();
        currentUserRole = userData.role;
    }
    
    const canEdit = (currentUserRole === 'admin' || currentUserRole === 'editor');
    
    // 指定された寺院を探す
    const t = Object.values(allTemplesData).find(temple => temple.name === templeName);
    
    if (!t) {
        list.innerHTML = '<div style="text-align:center; padding:20px; color:#999;">寺院が見つかりませんでした</div>';
        return;
    }
    
    list.innerHTML = ''; 
    
    const div = document.createElement('div');
    div.className = 'temple-item';
    
    const sectDisplay = t.sect ? `<span class="temple-sect">${t.sect}</span>` : '';
    
    // データをエスケープして保存
    div.dataset.temple = JSON.stringify(t);
    const nameEscaped = t.name.replace(/'/g, "\\'");
    
    // 権限に応じてボタンを表示/非表示
    const editButtons = canEdit ? `
        <button class="btn btn-edit" onclick="openEditModalFromData(this)">
            <span class="icon">✏️</span>
            <span>編集</span>
        </button>
        <button class="btn btn-delete" onclick="deleteTempleFromSelector('${nameEscaped}')">
            <span class="icon">🗑️</span>
        </button>
    ` : '';
    
    div.innerHTML = `
        <div class="temple-header">
            <div class="temple-info">
                <div class="temple-name">${t.name}</div>
                ${sectDisplay}
            </div>
            <div class="temple-actions">
                <button class="btn btn-preview" onclick="openCommentModal('${nameEscaped}')">
                    <span class="icon">💬</span>
                    <span>メモ</span>
                </button>
                <button class="btn btn-preview" onclick="openPreviewModalFromData(this)">
                    <span class="icon">👁️</span>
                    <span>プレビュー</span>
                </button>
                ${editButtons}
            </div>
        </div>
    `;
    list.appendChild(div);
    
    console.log(`✅ ${templeName} を表示しました`);
}

// 寺院削除（セレクトボックス用）
async function deleteTempleFromSelector(name) {
    if (!confirm(`🗑️ 本当に「${name}」を削除してもよろしいですか？\n\nこの操作は取り消せません。`)) return;
    
    try {
        const res = await fetch('/delete_temple', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: name })
        });
        
        if (res.ok) { 
            alert("✅ 削除しました"); 
            // セレクトボックスをリセット
            const templeSelect = document.getElementById('temple-select');
            if (templeSelect) {
                templeSelect.value = '';
            }
            // 表示をクリア
            const list = document.getElementById('temple-list');
            list.innerHTML = '';
            list.style.display = 'none';
            // セレクトボックスのリストを再読み込み
            await loadTempleSelectList();
        } else { 
            alert("❌ 削除に失敗しました"); 
        }
    } catch (e) {
        console.error('削除エラー:', e);
        alert("❌ 通信エラーが発生しました");
    }
}
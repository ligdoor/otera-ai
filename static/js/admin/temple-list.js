// ========================================
// 管理画面 - 寺院リスト
// ========================================

async function loadList() {
    const list = document.getElementById('temple-list');
    list.innerHTML = '<div style="text-align:center; padding:20px; color:#999;">読み込み中...</div>';
    
    try {
        // ユーザー権限を取得
        const userRes = await fetch('/get_current_user');
        const userData = await userRes.json();
        const userRole = userData.role;
        const canEdit = (userRole === 'admin' || userRole === 'editor');
    
        const res = await fetch('/get_all_data');
        if (!res.ok) throw new Error('データ取得失敗');
    
        templeData = await res.json();
        list.innerHTML = ''; 
    
        const sortedKeys = Object.keys(templeData).sort();
    
        if (sortedKeys.length === 0) {
            list.innerHTML = '<div style="text-align:center; padding:40px; color:#999;">登録されている寺院がありません</div>';
            return;
        }
    
        sortedKeys.forEach(key => {
            const t = templeData[key];
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
                <button class="btn btn-delete" onclick="deleteTemple('${nameEscaped}')">
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
        });
    } catch (e) {
        console.error('データ読み込みエラー:', e);
        list.innerHTML = `
            <div style="text-align:center; padding:40px;">
                <p style="color:#d32f2f; font-size:1.1rem; margin-bottom:15px;">❌ データの読み込みに失敗しました</p>
                <button class="btn btn-edit" onclick="location.reload()" style="max-width:200px; margin:0 auto;">
                    <span class="icon">🔄</span>
                    <span>再読み込み</span>
                </button>
            </div>
        `;
    }
}

async function deleteTemple(name) {
    if (!confirm(`🗑️ 本当に「${name}」を削除してもよろしいですか？\n\nこの操作は取り消せません。`)) return;
    
    try {
        const res = await fetch('/delete_temple', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: name })
        });
        
        if (res.ok) { 
            alert("✅ 削除しました"); 
            await loadList(); 
        } else { 
            alert("❌ 削除に失敗しました"); 
        }
    } catch (e) {
        alert("❌ 通信エラーが発生しました");
    }
}
// ========================================
// 管理画面 - CSV機能
// ========================================

async function exportCSV() {
    showLoading();
    try {
        window.location.href = '/export_csv';
        setTimeout(hideLoading, 1000);
    } catch (e) {
        hideLoading();
        alert('❌ エクスポートに失敗しました');
    }
}

async function importCSV() {
    const fileInput = document.getElementById('csv-file');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    if (!confirm(`「${file.name}」をインポートしますか？\n既存データは上書きされます。`)) {
        fileInput.value = '';
        return;
    }
    
    showLoading();
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const res = await fetch('/import_csv', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        
        if (res.ok) {
            let message = `✅ インポート完了\n\n新規: ${data.imported}件\n更新: ${data.updated}件`;
            if (data.errors.length > 0) {
                message += `\n\nエラー:\n${data.errors.join('\n')}`;
            }
            alert(message);
            await loadList();
        } else {
            alert('❌ エラー: ' + data.message);
        }
    } catch (e) {
        alert('❌ インポートに失敗しました: ' + e.message);
    } finally {
        hideLoading();
        fileInput.value = '';
    }
}
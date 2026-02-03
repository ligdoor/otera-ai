// ========================================
// 管理画面 - メイン（初期化・共通関数）
// ========================================

let fieldConfig = [];
let templeData = {};

// ローディング表示制御
function showLoading() {
    document.getElementById('loading-overlay').classList.add('show');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('show');
}

// ボタン無効化（連打防止）
function disableButtons() {
    const buttons = document.querySelectorAll('.header-btn, .add-btn, .btn');
    buttons.forEach(btn => {
        btn.disabled = true;
        btn.style.opacity = '0.5';
        btn.style.cursor = 'not-allowed';
    });
}

function enableButtons() {
    const buttons = document.querySelectorAll('.header-btn, .add-btn, .btn');
    buttons.forEach(btn => {
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.style.cursor = 'pointer';
    });
}

// 初期化
async function init() {
    disableButtons();
    showLoading();
    
    try {
        // 項目設定を取得
        const res = await fetch('/get_fields');
        fieldConfig = await res.json();
        
        // ユーザー権限を取得してUIを制御
        try {
            const userRes = await fetch('/get_current_user');
            const userData = await userRes.json();
            const userRole = userData.role;
            
            // 管理者のみユーザー管理リンクを表示
            if (userRole === 'admin') {
                const userMgmtLink = document.getElementById('user-management-link-dropdown');
                if (userMgmtLink) {
                    userMgmtLink.style.display = 'flex';
                }
            }
            
            // 管理者・編集者のみ編集機能を表示
            if (userRole === 'admin' || userRole === 'editor') {
                document.getElementById('add-temple-btn').style.display = 'flex';
                document.getElementById('csv-import-btn').style.display = 'flex';
            }
        } catch (e) {
            console.log('権限チェックエラー:', e);
        }
        
        // データ読み込み
        await loadList();
        
    } catch (e) {
        console.error('初期化エラー:', e);
        alert('❌ データの読み込みに失敗しました。ページをリロードしてください。');
    } finally {
        hideLoading();
        enableButtons();
    }
}

// ページ読み込み完了後すぐに初期化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// データ更新
async function reloadData() {
    if (!confirm("スプレッドシートから最新データを読み込みますか？")) return;
    try {
        await fetch('/reload_data', { method: 'POST' });
        alert("✅ 更新しました！");
        location.reload();
    } catch (e) {
        alert("❌ 更新に失敗しました");
    }
}

// モーダルを閉じる
function closeModal(id) { 
    document.getElementById(id).classList.remove('show'); 
}

// モーダル外クリックで閉じる
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('show');
            }
        });
    });
});

// コピー機能（管理画面用）
function copyToClipboardAdmin(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            alert('📋 コピーしました: ' + text);
        }).catch(err => {
            alert('📋 コピーに失敗しました');
        });
    } else {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        alert('📋 コピーしました: ' + text);
    }
}
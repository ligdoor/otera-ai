// ========================================
// アプリ - 検索機能（完全版）
// ========================================

// 寺院選択時の処理
async function onTempleSelect() {
    const select = document.getElementById('temple-select');
    const name = select.value;
    if (!name) return;
    
    const quickQaArea = document.getElementById('quick-qa-area');
    
    currentTempleName = name;
    quickQaArea.style.display = "flex";
    select.value = "";
    hideMenu();
    
    // サーバーにリクエスト
    sendChatRequest(name, 'summary', false);
}

// 宗派選択時の処理
async function onSectSelect() {
    const select = document.getElementById('sect-select');
    const sectName = select.value;
    
    console.log('宗派選択:', sectName);
    
    if (!sectName) return;
    
    const quickQaArea = document.getElementById('quick-qa-area');
    
    // ★ 修正: selectをリセットするタイミングを変更
    currentTempleName = "";
    quickQaArea.style.display = "none";
    hideMenu();
    
    addMessage(`📿 【${sectName}】寺院一覧`, 'user');
    const loadingId = addMessage('照会中...', 'ai', true);
    
    try {
        console.log('APIリクエスト送信:', sectName);
        
        const res = await fetch('/search_by_sect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sect: sectName })
        });
        
        console.log('レスポンスステータス:', res.status);
        
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        
        const data = await res.json();
        console.log('取得データ:', data);
        
        document.getElementById(loadingId).remove();
        
        // ★ 成功したらselectをリセット
        select.value = "";
        
        // data.results を使用
        if (!data.results || data.results.length === 0) {
            addMessage("該当する寺院がありません", 'ai');
            return;
        }
        
        let listHtml = `<p><b>${sectName}</b> の寺院（${data.results.length}件）</p>`;
        data.results.forEach(temple => {
            const isFav = favorites.includes(temple.name);
            const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(temple.address)}`;
            listHtml += `<div class="temple-card" onclick="tapTempleList('${temple.name.replace(/'/g, "\\'")}')">
                <button class="favorite-btn" onclick="toggleFavorite('${temple.name.replace(/'/g, "\\'")}', event)">${isFav ? '⭐' : '☆'}</button>
                <div class="card-name">${temple.name}</div>
                <div class="card-addr">${temple.address}
                    <a href="${mapUrl}" target="_blank" onclick="event.stopPropagation()">📍地図</a>
                    <button class="copy-btn" onclick="copyToClipboard('${temple.address.replace(/'/g, "\\'")}')">📋</button>
                </div>
            </div>`;
        });
        
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message ai-message';
        msgDiv.innerHTML = listHtml;
        chatWindow.appendChild(msgDiv);
        msgDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
    } catch (e) {
        console.error('宗派検索エラー:', e);
        document.getElementById(loadingId).remove();
        addMessage("❌ エラーが発生しました: " + e.message, 'ai');
        
        // ★ エラー時もselectをリセット
        select.value = "";
    }
}

// 寺院カードをタップ
function tapTempleList(name) {
    const quickQaArea = document.getElementById('quick-qa-area');
    
    addMessage(name, 'user');
    currentTempleName = name;
    quickQaArea.style.display = "flex";
    hideMenu();
    sendChatRequest(name, 'summary', false);
}

// クイックQ&A
function askQuick(question) {
    if (!currentTempleName) {
        alert("⚠️ まず寺院を選択してください");
        return;
    }
    hideMenu();
    sendChatRequest(`${currentTempleName}の${question}`, 'qa', true);
}

// 自由テキスト送信
function sendFreeChat() {
    const input = document.getElementById('free-input');
    const text = input.value.trim();
    if (!text) return;
    
    let sendText = text;
    if (currentTempleName && !text.includes(currentTempleName)) {
        sendText = `${currentTempleName}の${text}`;
    }
    
    input.value = '';
    hideMenu();
    sendChatRequest(sendText, 'qa', true);
}

// チャットリクエスト送信
async function sendChatRequest(text, mode, showUserMessage = true) {
    if (showUserMessage) {
        addMessage(text, 'user');
    }
    
    const loadingId = addMessage('照会中...', 'ai', true);
    window.scrollTo(0, document.body.scrollHeight);
    
    try {
        const res = await fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: text, mode: mode })
        });
        
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        
        const data = await res.json();
        document.getElementById(loadingId).remove();
        
        const aiMsgId = addMessage(data.answer, 'ai');
        setTimeout(() => {
            document.getElementById(aiMsgId).scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
        
    } catch (e) {
        console.error('チャットリクエストエラー:', e);
        document.getElementById(loadingId).remove();
        addMessage("❌ システムエラーが発生しました", 'ai');
    }
}

// ========================================
// 寺院名での曖昧検索（漢字違い対応）
// ========================================

async function searchTempleByName(templeName) {
    try {
        const res = await fetch('/search_temple_by_name', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: templeName })
        });
        
        const data = await res.json();
        
        if (data.exact_match) {
            // 完全一致があった場合、そのまま表示
            return data.exact_match;
        } else if (data.suggestions && data.suggestions.length > 0) {
            // 候補がある場合、確認ダイアログを表示
            return await showSuggestionDialog(templeName, data.suggestions);
        } else {
            // 見つからない
            alert(`「${templeName}」が見つかりませんでした`);
            return null;
        }
    } catch (e) {
        console.error('検索エラー:', e);
        alert('検索に失敗しました');
        return null;
    }
}

// 確認ダイアログを表示
function showSuggestionDialog(originalQuery, suggestions) {
    return new Promise((resolve) => {
        // オーバーレイを作成
        const overlay = document.createElement('div');
        overlay.className = 'suggestion-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;
        
        // ダイアログを作成
        const dialog = document.createElement('div');
        dialog.className = 'suggestion-dialog';
        dialog.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 16px;
            max-width: 90%;
            width: 400px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        `;
        
        dialog.innerHTML = `
            <h3 style="margin: 0 0 15px 0; color: #1a237e; font-size: 1.2rem;">
                🔍 確認
            </h3>
            <p style="margin-bottom: 20px; color: #555; line-height: 1.6;">
                「<strong>${originalQuery}</strong>」が見つかりませんでした。<br>
                もしかして以下の寺院ですか？
            </p>
            <div class="suggestion-buttons" style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px;">
                ${suggestions.map(temple => `
                    <button class="suggestion-btn" data-temple='${JSON.stringify(temple)}' style="
                        padding: 16px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        border: none;
                        border-radius: 10px;
                        font-size: 1.1rem;
                        font-weight: bold;
                        cursor: pointer;
                        transition: transform 0.2s, box-shadow 0.2s;
                        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
                        text-align: left;
                    ">
                        <div style="font-size: 1.2rem; margin-bottom: 4px;">🏯 ${temple.name}</div>
                        <div style="font-size: 0.85rem; opacity: 0.9;">${temple.sect || ''} ${temple.address || ''}</div>
                    </button>
                `).join('')}
            </div>
            <button class="cancel-btn" style="
                width: 100%;
                padding: 14px;
                background: #f0f0f0;
                color: #666;
                border: none;
                border-radius: 10px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.2s;
            ">
                いいえ、違います
            </button>
        `;
        
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        
        // ボタンホバー効果
        dialog.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
            });
            btn.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.3)';
            });
            
            // クリックイベント
            btn.addEventListener('click', function() {
                const templeData = JSON.parse(this.dataset.temple);
                document.body.removeChild(overlay);
                resolve(templeData);
            });
        });
        
        // キャンセルボタン
        dialog.querySelector('.cancel-btn').addEventListener('mouseenter', function() {
            this.style.background = '#e0e0e0';
        });
        dialog.querySelector('.cancel-btn').addEventListener('mouseleave', function() {
            this.style.background = '#f0f0f0';
        });
        dialog.querySelector('.cancel-btn').addEventListener('click', function() {
            document.body.removeChild(overlay);
            resolve(null);
        });
        
        // オーバーレイクリックで閉じる
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
                resolve(null);
            }
        });
    });
}

// 既存のonTempleSelect関数を修正
async function onTempleSelect() {
    const select = document.getElementById('temple-select');
    const name = select.value;
    if (!name) return;
    
    const quickQaArea = document.getElementById('quick-qa-area');
    
    // 曖昧検索を実行
    const temple = await searchTempleByName(name);
    
    if (temple) {
        currentTempleName = temple.name;
        quickQaArea.style.display = "flex";
        select.value = "";
        hideMenu();
        
        // サーバーにリクエスト
        sendChatRequest(temple.name, 'summary', false);
    } else {
        select.value = "";
    }
}
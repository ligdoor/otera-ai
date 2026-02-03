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
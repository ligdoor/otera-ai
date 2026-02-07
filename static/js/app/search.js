// ========================================
// アプリ - 検索機能（完全版・重複削除）
// ========================================

// 寺院選択時の処理
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

// 宗派選択時の処理
async function onSectSelect() {
    const select = document.getElementById('sect-select');
    const sectName = select.value;
    
    console.log('宗派選択:', sectName);
    
    if (!sectName) return;
    
    const quickQaArea = document.getElementById('quick-qa-area');
    
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
        select.value = "";
        
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

// 自由テキスト送信（修正版）
function sendFreeChat() {
    const input = document.getElementById('free-input');
    const text = input.value.trim();
    if (!text) return;
    
    let sendText = text;
    
    // ★★★ 修正: 入力に寺院名候補が含まれているかチェック ★★★
    const matches = text.matchAll(/([^のは?\s]+)の/g);
    const candidates = Array.from(matches, m => m[1]);
    
    console.log('[sendFreeChat] 入力テキスト:', text);
    console.log('[sendFreeChat] 検出された寺院名候補:', candidates);
    console.log('[sendFreeChat] 現在の寺院名:', currentTempleName);
    
    // 候補が含まれていない場合のみ、currentTempleNameを付ける
    if (candidates.length === 0 && currentTempleName) {
        sendText = `${currentTempleName}の${text}`;
        console.log('[sendFreeChat] 寺院名を自動付与:', sendText);
    } else if (candidates.length > 0) {
        // 候補が含まれている場合はそのまま送信
        console.log('[sendFreeChat] 寺院名候補が含まれているため、そのまま送信');
    } else {
        console.log('[sendFreeChat] 寺院名なしでそのまま送信');
    }
    
    input.value = '';
    hideMenu();
    sendChatRequest(sendText, 'qa', true);
}

// ========================================
// メイン検索機能（複数寺院名対応版）
// ========================================

async function sendChatRequest(text, mode, showUserMessage = true) {
    console.log('========== sendChatRequest デバッグ開始 ==========');
    console.log('1. 入力テキスト:', text);
    console.log('2. 現在の寺院名:', currentTempleName);
    
    if (showUserMessage) {
        addMessage(text, 'user');
    }
    
    let finalText = text;
    let needsSearch = false;
    
    // ★★★ すべての「〇〇の」パターンを検出 ★★★
    const allMatches = text.matchAll(/([^のは?\s]+)の/g);
    const candidates = Array.from(allMatches, m => m[1]);
    
    console.log('3. 検出されたすべての候補:', candidates);
    
    if (candidates.length > 0) {
        // ★★★ 最後の候補を優先 ★★★
        const candidate = candidates[candidates.length - 1];
        console.log('4. 優先候補（最後）:', candidate);
        
        // 現在の寺院名と異なる場合、新規検索が必要
        if (candidate !== currentTempleName) {
            console.log('5. 新しい寺院名が検出されました。検索します...');
            needsSearch = true;
            
            console.log('6. searchTempleByName を呼び出します...');
            const temple = await searchTempleByName(candidate);
            console.log('7. searchTempleByName の結果:', temple);
            
            if (temple) {
                currentTempleName = temple.name;
                console.log('8. 寺院名を更新:', currentTempleName);
                
                // ★★★ 修正: すべての候補を削除し、正しい寺院名だけを残す ★★★
                // 「大正寺の妙法寺の葬儀は？」→「妙法寺の葬儀は？」
                
                // ステップ1: すべての「〇〇の」パターンを削除
                let cleanText = text;
                candidates.forEach(c => {
                    cleanText = cleanText.replace(c + 'の', '');
                });
                console.log('8-1. すべての候補削除後:', cleanText);
                
                // ステップ2: 正しい寺院名を先頭に追加
                finalText = temple.name + 'の' + cleanText;
                
                console.log('9. 置き換え後のテキスト:', finalText);
            } else {
                console.log('8. 寺院が見つかりませんでした');
                currentTempleName = "";
            }
        } else {
            console.log('5. 同じ寺院名です。検索をスキップ');
        }
    } else {
        console.log('4. パターンにマッチしませんでした');
    }
    
    console.log('10. 最終的に送信するテキスト:', finalText);
    console.log('11. 最終的な寺院名:', currentTempleName);
    
    const loadingId = addMessage('照会中...', 'ai', true);
    window.scrollTo(0, document.body.scrollHeight);
    
    try {
        console.log('12. /ask にリクエスト送信中...');
        const res = await fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: finalText, mode: mode })
        });
        
        console.log('13. レスポンスステータス:', res.status);
        
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        
        const data = await res.json();
        console.log('14. 受信データ:', data);
        
        document.getElementById(loadingId).remove();
        
        const aiMsgId = addMessage(data.answer, 'ai');
        setTimeout(() => {
            document.getElementById(aiMsgId).scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
        
        console.log('========== sendChatRequest デバッグ終了 ==========');
        
    } catch (e) {
        console.error('チャットリクエストエラー:', e);
        document.getElementById(loadingId).remove();
        addMessage("❌ システムエラーが発生しました", 'ai');
    }
}

// ========================================
// 寺院名での曖昧検索（重複削除版）
// ========================================

async function searchTempleByName(templeName) {
    console.log('  --- searchTempleByName 開始 ---');
    console.log('  検索する寺院名:', templeName);
    
    try {
        const res = await fetch('/search_temple_by_name', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: templeName })
        });
        
        console.log('  レスポンスステータス:', res.status);
        
        const data = await res.json();
        console.log('  受信データ:', data);
        console.log('  - exact_match:', data.exact_match);
        console.log('  - suggestions:', data.suggestions);
        
        if (data.exact_match) {
            console.log('  完全一致が見つかりました:', data.exact_match.name);
            return data.exact_match;
        } else if (data.suggestions && data.suggestions.length > 0) {
            console.log('  候補が', data.suggestions.length, '件見つかりました');
            console.log('  showSuggestionDialog を呼び出します...');
            const result = await showSuggestionDialog(templeName, data.suggestions);
            console.log('  ユーザーの選択:', result);
            return result;
        } else {
            console.log('  候補が見つかりませんでした');
            alert(`「${templeName}」が見つかりませんでした`);
            return null;
        }
    } catch (e) {
        console.error('  検索エラー:', e);
        alert('検索に失敗しました');
        return null;
    } finally {
        console.log('  --- searchTempleByName 終了 ---');
    }
}

// 確認ダイアログを表示
function showSuggestionDialog(originalQuery, suggestions) {
    return new Promise((resolve) => {
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
        
        dialog.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
            });
            btn.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.3)';
            });
            
            btn.addEventListener('click', function() {
                const templeData = JSON.parse(this.dataset.temple);
                document.body.removeChild(overlay);
                resolve(templeData);
            });
        });
        
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
        
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
                resolve(null);
            }
        });
    });
}
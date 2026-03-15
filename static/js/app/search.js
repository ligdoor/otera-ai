// ========================================
// アプリ - 検索機能（完全版・アコーディオン対応）
// ========================================

// 寺院選択時の処理
async function onTempleSelect() {
    const select = document.getElementById('temple-select');
    const name = select.value;
    if (!name) return;
    
    const quickQaArea = document.getElementById('quick-qa-area');
    
    // ★★★ 元の動作を維持：曖昧検索を実行して詳細表示 ★★★
    const temple = await searchTempleByName(name, false);  // false = 通常の検索
    
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
        
        const res = await fetch('/api/v1/temples/search/sect', {
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
        
        if (!data.success) {
            addMessage(`エラー: ${data.error.message}`, 'ai');
            return;
        }
        
        const results = data.data.results || [];
        
        if (results.length === 0) {
            addMessage("該当する寺院がありません", 'ai');
            return;
        }
        
        // 宗派検索はカード表示のまま
        let listHtml = `<p><b>${sectName}</b> の寺院（${results.length}件）</p>`;
        results.forEach(temple => {
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

// ★★★ 新規追加: セレクトボックスと同じアコーディオン形式で表示 ★★★
async function displayTempleAccordion(temples, searchQuery) {
    addMessage(searchQuery, 'user');
    const loadingId = addMessage('詳細情報を取得中...', 'ai', true);
    
    try {
        // 各寺院の詳細情報を取得
        const promises = temples.map(temple => 
            fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: temple.name, mode: 'summary' })
            })
            .then(res => res.json())
            .then(data => ({
                temple: temple,
                details: data.answer
            }))
        );
        
        const results = await Promise.all(promises);
        document.getElementById(loadingId).remove();
        
        // ★★★ 複数の寺院を表示（お気に入りボタンのみ、寺院名ヘッダーなし） ★★★
        results.forEach((result, index) => {
            const temple = result.temple;
            let details = result.details;
            
            // お気に入りボタンのみのヘッダー（右寄せ）
            const favoriteButton = `<div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
                <button class="favorite-btn" onclick="toggleFavorite('${temple.name.replace(/'/g, "\\'")}', event)">${favorites.includes(temple.name) ? '⭐' : '☆'}</button>
            </div>`;
            
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message ai-message';
            msgDiv.innerHTML = favoriteButton + details;
            chatWindow.appendChild(msgDiv);
            
            if (index < results.length - 1) {
                // 寺院間の区切り線
                const divider = document.createElement('div');
                divider.style.cssText = 'border-top: 3px solid #e0e0e0; margin: 20px 0;';
                chatWindow.appendChild(divider);
            }
        });
        
        chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: 'smooth' });
        
    } catch (e) {
        console.error('詳細情報取得エラー:', e);
        document.getElementById(loadingId).remove();
        addMessage("❌ 詳細情報の取得に失敗しました", 'ai');
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
async function sendFreeChat() {
    const input = document.getElementById('free-input');
    const text = input.value.trim();
    if (!text) return;

    let sendText = text;

    // 「〇〇の」パターンで漢字の寺院名候補を抽出
    const matches = text.matchAll(/([^のは?\s]+)の/g);
    const candidates = Array.from(matches, m => m[1]).filter(c =>
        allTemples.some(t => t.includes(c) || c.includes(t))
    );

    console.log('[sendFreeChat] 入力テキスト:', text);
    console.log('[sendFreeChat] 検出された寺院名候補:', candidates);
    console.log('[sendFreeChat] 現在の寺院名:', currentTempleName);

    // 「〇〇の」パターンがない場合 → 寺院名単体 or ひらがな入力の可能性を確認
    if (candidates.length === 0) {
        console.log('[sendFreeChat] 寺院名のみの可能性をチェック...');

        const result = await searchTempleByName(text, true);

        if (result && Array.isArray(result) && result.length > 0) {
            // 寺院が見つかった → アコーディオン表示して終了
            console.log('[sendFreeChat] アコーディオン表示:', result.length, '件');
            currentTempleName = result[0].name;
            displayTempleAccordion(result, text);
            input.value = '';
            hideMenu();
            return;
        }

        // 見つからなかった場合 → currentTempleNameがあれば付与して送信
        if (currentTempleName) {
            sendText = `${currentTempleName}の${text}`;
            console.log('[sendFreeChat] 寺院名を自動付与:', sendText);
        } else {
            console.log('[sendFreeChat] 寺院名なしでそのまま送信');
        }
    } else {
        // 「〇〇の」パターンあり → そのまま送信
        console.log('[sendFreeChat] 寺院名候補が含まれているため、そのまま送信');
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
    const rawCandidates = Array.from(allMatches, m => m[1]);
    
    // ★★★ 修正: allTemplesに含まれるものだけを寺院名候補とする ★★★
    // 例:「大正寺の搬送の持ち物は？」→「搬送」は寺院名リストにないので除外
    const candidates = rawCandidates.filter(c =>
        allTemples.some(t => t.includes(c) || c.includes(t))
    );
    
    console.log('3. 検出されたすべての候補(絞込前):', rawCandidates);
    console.log('3b. 寺院名リストでフィルタ後:', candidates);
    
    if (candidates.length > 0) {
        // ★★★ 最後の候補を優先 ★★★
        const candidate = candidates[candidates.length - 1];
        console.log('4. 優先候補（最後）:', candidate);
        
        // 現在の寺院名と異なる場合、新規検索が必要
        if (candidate !== currentTempleName) {
            console.log('5. 新しい寺院名が検出されました。検索します...');
            needsSearch = true;
            
            console.log('6. searchTempleByName を呼び出します...');
            const temple = await searchTempleByName(candidate, false);  // false = 詳細質問での検索
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
// 寺院名での曖昧検索（アコーディオン対応版）
// ========================================

async function searchTempleByName(templeName, isTempleNameOnly = false) {
    console.log('  --- searchTempleByName 開始 ---');
    console.log('  検索する寺院名:', templeName);
    console.log('  寺院名のみ検索:', isTempleNameOnly);
    
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
        
        // ★★★ 寺院名のみ検索の場合は候補リストを返す ★★★
        if (isTempleNameOnly) {
            let allResults = [];
            if (data.exact_match) {
                allResults.push(data.exact_match);
            }
            if (data.suggestions && data.suggestions.length > 0) {
                data.suggestions.forEach(s => {
                    if (!data.exact_match || s.name !== data.exact_match.name) {
                        allResults.push(s);
                    }
                });
            }
            
            if (allResults.length === 0) {
                console.log('  候補が見つかりませんでした');
                return null;  // alertは出さずnullを返す（呼び出し元で対処）
            }
            
            console.log('  アコーディオン用候補リストを返します:', allResults.length, '件');
            return allResults;
        }
        
        // ★★★ 詳細質問での検索の場合は従来通り ★★★
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
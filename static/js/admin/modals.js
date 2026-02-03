// ========================================
// 管理画面 - モーダル制御
// ========================================

// パスワード変更
function openPassModal() {
    document.getElementById('pass-modal').classList.add('show');
    document.getElementById('pass-form').reset();
}

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('pass-form').onsubmit = async function(e) {
        e.preventDefault();
        const currentPass = document.getElementById('current-pass').value;
        const newPass = document.getElementById('new-pass').value;
        const confirmPass = document.getElementById('new-pass-confirm').value;

        if (newPass !== confirmPass) {
            alert("❌ 新しいパスワードが一致しません");
            return;
        }

        if (newPass.length < 8) {
            alert("❌ パスワードは8文字以上必要です");
            return;
        }

        try {
            const res = await fetch('/change_password', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ current_pass: currentPass, new_pass: newPass })
            });

            const data = await res.json();
            if (res.ok) {
                alert("✅ パスワードを変更しました！");
                closeModal('pass-modal');
            } else {
                alert("❌ エラー: " + data.message);
            }
        } catch (e) {
            alert("❌ 通信エラーが発生しました");
        }
    };
});

// プレビューモーダル
function openPreviewModal(temple) {
    const content = document.getElementById('preview-content');
    
    const categories = {
        basic: {
            title: '🏯 基本情報',
            fields: ['sect', 'address', 'transport'],
            defaultOpen: true
        },
        tsuya: {
            title: '🌙 通夜の流れ',
            fields: ['tsuya_narimono', 'tsuya_ippan_shoko', 'tsuya_shinzoku_shoko', 'tsuya_dokyo_length', 'tsuya_notes'],
            defaultOpen: false
        },
        sougi: {
            title: '☀️ 葬儀の流れ',
            fields: ['sougi_narimono', 'sougi_ippan_shoko', 'sougi_shinzoku_shoko', 'sougi_dokyo_length', 'sougi_notes'],
            defaultOpen: false
        },
        items: {
            title: '📝 お膳・書き物',
            fields: ['ozen_type', 'kakimono_detail', 'shonananoka_timing'],
            defaultOpen: false
        },
        other: {
            title: '⚠️ その他・特記事項',
            fields: ['nokanshiyo', 'kakimono', 'flow', 'caution', 'sonota_tokki'],
            defaultOpen: false
        }
    };
    
    let html = `<div class="preview-title">${temple.name}</div>`;
    
    let categoryIndex = 0;
    Object.keys(categories).forEach((catKey) => {
        const category = categories[catKey];
        const isOpen = category.defaultOpen;
        const activeClass = isOpen ? 'active' : '';
        
        const fieldsToShow = [];
        category.fields.forEach(fieldKey => {
            const field = fieldConfig.find(f => f.key === fieldKey);
            if (field) {
                const value = temple[fieldKey];
                fieldsToShow.push({
                    key: fieldKey,
                    label: field.label,
                    value: value || ''
                });
            }
        });
        
        if (fieldsToShow.length === 0) return;
        
        const accordionId = `accordion-preview-${categoryIndex}`;
        const headerId = `header-preview-${categoryIndex}`;
        categoryIndex++;
        
        html += `
            <div class="accordion-section">
                <div class="accordion-header ${activeClass}" id="${headerId}" onclick="toggleAccordionPreview('${headerId}', '${accordionId}')">
                    <div class="accordion-title">
                        <span class="accordion-icon">▶</span>
                        <span>${category.title}</span>
                    </div>
                </div>
                <div class="accordion-content ${activeClass}" id="${accordionId}" style="${isOpen ? 'max-height: none;' : ''}">
                    <div class="accordion-body">
        `;
        
        fieldsToShow.forEach(item => {
            const displayValue = item.value && item.value.trim() !== '' ? item.value : '記載なし';
            const isEmpty = !item.value || item.value.trim() === '';
            
            if (item.key === 'address' && !isEmpty) {
                const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(displayValue)}`;
                const addressEscaped = displayValue.replace(/'/g, "\\'").replace(/"/g, "&quot;");
                html += `
                    <div style="margin-bottom:6px;">
                        <div style="font-weight:600; color:#555; font-size:0.88rem; margin-bottom:2px;">${item.label}:</div>
                        <div style="font-size:0.9rem; line-height:1.5;">
                            ${displayValue}
                            <button class="copy-btn" onclick="event.stopPropagation(); copyToClipboardAdmin('${addressEscaped}')" style="margin-left:4px; padding:2px 8px; font-size:0.8rem;">📋</button>
                        </div>
                        <a href="${mapUrl}" target="_blank" style="color:#1a237e; font-weight:bold; text-decoration:underline; margin-top:4px; display:inline-block; font-size:0.85rem;">📍地図を開く</a>
                    </div>
                `;
            } else {
                const valueStyle = isEmpty ? 'color:#999; font-style:italic; font-size:0.85rem;' : 'font-size:0.9rem; line-height:1.5;';
                html += `
                    <div style="margin-bottom:6px;">
                        <div style="font-weight:600; color:#555; font-size:0.88rem; margin-bottom:2px;">${item.label}:</div>
                        <div style="${valueStyle}">${displayValue}</div>
                    </div>
                `;
            }
        });
        
        html += `
                    </div>
                </div>
            </div>
        `;
    });
    
    content.innerHTML = html;
    document.getElementById('preview-modal').classList.add('show');
}

function openPreviewModalFromData(button) {
    const templeItem = button.closest('.temple-item');
    const templeData = JSON.parse(templeItem.dataset.temple);
    openPreviewModal(templeData);
}

function toggleAccordionPreview(headerId, contentId) {
    const header = document.getElementById(headerId);
    const content = document.getElementById(contentId);
    
    if (!header || !content) {
        console.error('要素が見つかりません:', headerId, contentId);
        return;
    }
    
    const isActive = header.classList.contains('active');
    
    if (isActive) {
        const currentHeight = content.scrollHeight;
        content.style.maxHeight = currentHeight + 'px';
        requestAnimationFrame(() => {
            content.style.maxHeight = '0';
            header.classList.remove('active');
            content.classList.remove('active');
        });
    } else {
        header.classList.add('active');
        content.classList.add('active');
        const scrollHeight = content.scrollHeight;
        content.style.maxHeight = scrollHeight + 'px';
        setTimeout(() => {
            if (content.classList.contains('active')) {
                content.style.maxHeight = 'none';
            }
        }, 400);
    }
}

// アクセス統計
async function showAccessStats() {
    document.getElementById('stats-modal').classList.add('show');
    document.getElementById('stats-content').innerHTML = '読み込み中...';
    
    try {
        const res = await fetch('/get_access_stats');
        const data = await res.json();
        
        if (data.stats.length === 0) {
            document.getElementById('stats-content').innerHTML = '<p style="text-align:center; color:#999;">データがありません</p>';
            return;
        }
        
        let html = '<table style="width:100%; border-collapse:collapse;">';
        html += '<thead><tr style="background:#f5f5f5;"><th style="padding:10px; text-align:left;">順位</th><th style="padding:10px; text-align:left;">寺院名</th><th style="padding:10px; text-align:right;">閲覧回数</th></tr></thead>';
        html += '<tbody>';
        
        data.stats.forEach((item, index) => {
            const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}位`;
            html += `<tr style="border-bottom:1px solid #eee;">
                <td style="padding:10px;">${medal}</td>
                <td style="padding:10px; font-weight:600;">${item.name}</td>
                <td style="padding:10px; text-align:right;">${item.count}回</td>
            </tr>`;
        });
        
        html += '</tbody></table>';
        document.getElementById('stats-content').innerHTML = html;
    } catch (e) {
        document.getElementById('stats-content').innerHTML = '<p style="text-align:center; color:#d32f2f;">データの取得に失敗しました</p>';
    }
}

// コメント機能
let currentTempleForComment = '';

async function openCommentModal(templeName) {
    currentTempleForComment = templeName;
    document.getElementById('comment-modal-title').textContent = `💬 ${templeName} のスタッフメモ`;
    document.getElementById('comment-modal').classList.add('show');
    document.getElementById('new-comment').value = '';
    await loadComments(templeName);
}

async function loadComments(templeName) {
    const container = document.getElementById('comments-list');
    container.innerHTML = '読み込み中...';
    
    try {
        const res = await fetch(`/get_comments/${encodeURIComponent(templeName)}`);
        const data = await res.json();
        
        if (data.comments.length === 0) {
            container.innerHTML = '<p style="text-align:center; color:#999; padding:20px;">まだメモがありません</p>';
            return;
        }
        
        let html = '';
        data.comments.forEach(comment => {
            html += `<div style="background:#f9f9f9; padding:12px; border-radius:8px; margin-bottom:10px; border-left:3px solid #1a237e;">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <span style="font-weight:600; color:#1a237e;">${comment.user_name}</span>
                    <span style="font-size:0.85em; color:#666;">${comment.timestamp}</span>
                </div>
                <div style="color:#333; line-height:1.6;">${comment.comment}</div>
            </div>`;
        });
        
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<p style="text-align:center; color:#d32f2f;">読み込みに失敗しました</p>';
    }
}

async function addComment() {
    const commentText = document.getElementById('new-comment').value.trim();
    
    if (!commentText) {
        alert('メモを入力してください');
        return;
    }
    
    try {
        const res = await fetch('/add_comment', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                temple_name: currentTempleForComment,
                comment: commentText
            })
        });
        
        if (res.ok) {
            document.getElementById('new-comment').value = '';
            await loadComments(currentTempleForComment);
        } else {
            const data = await res.json();
            alert('❌ エラー: ' + data.message);
        }
    } catch (e) {
        alert('❌ 送信に失敗しました');
    }
}
// ========================================
// 管理画面 - フォーム処理
// ========================================

let quillEditors = {};

function renderForm(data = {}) {
    const container = document.getElementById('dynamic-form-fields');
    container.innerHTML = ''; 
    quillEditors = {};

    const isMobile = window.innerWidth < 768;

    const toolbarDesktop = [
        ['bold', 'italic', 'underline', 'strike'],
        [{ 'color': [] }, { 'background': [] }],
        [{ 'list': 'ordered' }, { 'list': 'bullet' }],
        ['clean']
    ];

    const toolbarMobile = [
        ['bold', 'underline', 'strike'],
        [{ 'color': [] }],
        ['clean']
    ];

    fieldConfig.forEach(field => {
        const div = document.createElement('div');
        div.className = 'form-group';
        const value = data[field.key] || '';

        if (['name', 'sect', 'address'].includes(field.key)) {
            div.innerHTML = `
                <label class="form-label">${field.label}</label>
                <input type="text" id="input-${field.key}" class="form-input" value="${value}">
            `;
        } else {
            const editorId = `editor-${field.key}`;
            div.innerHTML = `
                <label class="form-label">${field.label}</label>
                <div id="${editorId}" class="quill-editor"></div>
                <input type="hidden" id="input-${field.key}">
            `;
            container.appendChild(div);

            const quill = new Quill(`#${editorId}`, {
                theme: 'snow',
                modules: {
                    toolbar: isMobile ? toolbarMobile : toolbarDesktop
                }
            });

            quill.root.innerHTML = value;
            quillEditors[field.key] = quill;
            return;
        }

        container.appendChild(div);
    });
}

function openAddModal() {
    document.getElementById('modal-title').innerText = "➕ 新規寺院の追加";
    document.getElementById('mode').value = "add";
    document.getElementById('original-name').value = "";
    renderForm({});
    document.getElementById('edit-modal').classList.add('show');
}

function openEditModal(temple) {
    document.getElementById('modal-title').innerText = `✏️ ${temple.name} の編集`;
    document.getElementById('mode').value = "edit";
    document.getElementById('original-name').value = temple.name;
    renderForm(temple);
    document.getElementById('edit-modal').classList.add('show');
}

function openEditModalFromData(button) {
    const templeItem = button.closest('.temple-item');
    const templeData = JSON.parse(templeItem.dataset.temple);
    openEditModal(templeData);
}

// フォーム送信
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('edit-form').onsubmit = async function(e) {
        e.preventDefault();
        const mode = document.getElementById('mode').value;
        const originalName = document.getElementById('original-name').value;
        const formData = {};
        
        fieldConfig.forEach(field => {
            if (quillEditors[field.key]) {
                formData[field.key] = quillEditors[field.key].root.innerHTML;
            } else {
                const el = document.getElementById(`input-${field.key}`);
                if (el) formData[field.key] = el.value.trim();
            }
        });
        
        if (!formData.name) {
            alert("❌ 寺院名は必須です");
            return;
        }
        
        if (!confirm("💾 保存してよろしいですか？")) return;
        
        try {
            let url = mode === 'add' ? '/add_temple' : '/update_temple';
            const res = await fetch(url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ original_name: originalName, data: formData })
            });
            
            if (res.ok) {
                alert("✅ 保存しました！");
                closeModal('edit-modal');
                
                // ⭐ 修正: loadList()の代わりにセレクトボックスを更新
                if (mode === 'add') {
                    // 新規追加の場合はセレクトボックスを再読み込み
                    if (typeof loadTempleSelectList === 'function') {
                        await loadTempleSelectList();
                    }
                    // 追加した寺院を自動選択
                    const templeSelect = document.getElementById('temple-select');
                    if (templeSelect) {
                        // 少し待ってから選択（リストの更新を待つ）
                        setTimeout(() => {
                            const options = Array.from(templeSelect.options);
                            const addedOption = options.find(opt => opt.text === formData.name);
                            if (addedOption) {
                                templeSelect.value = addedOption.value;
                                // 選択イベントを発火
                                templeSelect.dispatchEvent(new Event('change'));
                            }
                        }, 500);
                    }
                } else {
                    // 編集の場合は現在選択中の寺院を再表示
                    const templeSelect = document.getElementById('temple-select');
                    if (templeSelect && templeSelect.value) {
                        // 寺院名が変更された可能性があるので、リストを再読み込み
                        if (typeof loadTempleSelectList === 'function') {
                            await loadTempleSelectList();
                        }
                        // 編集後の寺院名で再選択
                        setTimeout(async () => {
                            const options = Array.from(templeSelect.options);
                            const updatedOption = options.find(opt => opt.text === formData.name);
                            if (updatedOption) {
                                templeSelect.value = updatedOption.value;
                                // 表示を更新
                                if (typeof displaySelectedTemple === 'function') {
                                    await displaySelectedTemple(formData.name);
                                }
                            }
                        }, 500);
                    }
                }
            } else {
                const err = await res.json();
                alert("❌ エラー: " + err.message);
            }
        } catch (e) {
            console.error('保存エラー:', e);
            alert("❌ 通信エラーが発生しました");
        }
    };
});
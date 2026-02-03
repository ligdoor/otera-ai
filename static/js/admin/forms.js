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
                await loadList();
            } else {
                const err = await res.json();
                alert("❌ エラー: " + err.message);
            }
        } catch (e) {
            alert("❌ 通信エラーが発生しました");
        }
    };
});
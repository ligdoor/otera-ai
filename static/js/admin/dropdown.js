// ========================================
// 管理画面 - ドロップダウンメニュー
// ========================================

function toggleDropdown(menuId) {
    const menu = document.getElementById(menuId);
    const dropdown = menu.parentElement;
    const isActive = dropdown.classList.contains('active');
    
    // 他のメニューを閉じる
    closeAllDropdowns();
    
    // このメニューをトグル
    if (!isActive) {
        dropdown.classList.add('active');
        menu.classList.add('show');
    }
}

function closeAllDropdowns() {
    document.querySelectorAll('.dropdown').forEach(dropdown => {
        dropdown.classList.remove('active');
    });
    document.querySelectorAll('.dropdown-menu').forEach(menu => {
        menu.classList.remove('show');
    });
}

// メニュー外をクリックしたら閉じる
document.addEventListener('click', function(e) {
    if (!e.target.closest('.dropdown')) {
        closeAllDropdowns();
    }
});

// ESCキーでメニューを閉じる
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeAllDropdowns();
    }
});
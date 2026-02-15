// ========================================
// アプリ - お気に入り機能
// ========================================

// お気に入りを読み込み
async function loadFavorites() {
    try {
        const res = await fetch('/api/v1/favorites');
        if (res.status === 401) {
            window.location.href = '/admin';
            return;
        }
        const data = await res.json();
        if (data.success) {
            favorites = data.data.favorites || [];
        } else {
            console.error('お気に入り取得エラー:', data.error.message);
            favorites = [];
        }
        updateTempleSelect();
    } catch (e) {
        console.error('お気に入り取得エラー:', e);
        favorites = [];
    }
}

// お気に入りをトグル
async function toggleFavorite(name, event) {
    event.stopPropagation();
    event.preventDefault();
    
    try {
        const res = await fetch('/api/v1/favorites/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ temple_name: name })
        });
        
        const data = await res.json();
        
        if (data.success) {
            // お気に入りリストを更新
            if (data.data.action === 'added') {
                favorites.push(name);
            } else {
                const index = favorites.indexOf(name);
                if (index > -1) favorites.splice(index, 1);
            }
            
            updateTempleSelect();
            event.target.textContent = favorites.includes(name) ? '⭐' : '☆';
        } else {
            alert('お気に入りの更新に失敗しました');
        }
    } catch (e) {
        console.error('お気に入り更新エラー:', e);
        alert('お気に入りの更新に失敗しました');
    }
}
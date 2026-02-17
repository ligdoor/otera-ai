/**
 * header-offset.js
 *
 * ヘッダー・コントロールエリアの実際の高さを取得して
 * 関連要素の位置を動的に設定する
 */

function adjustAll() {
    const header = document.querySelector('header');
    const chatWindow = document.getElementById('chat-window');
    const controlArea = document.querySelector('.control-area');

    if (header) {
        const headerHeight = header.getBoundingClientRect().height;
        const topOffset = Math.ceil(headerHeight) + 8; // 余白8px

        // back-btn / clear-chat-btn の top を更新
        document.querySelectorAll('.back-btn, .clear-chat-btn').forEach(btn => {
            btn.style.top = topOffset + 'px';
        });

        // chat-window の padding-top をヘッダー高さに合わせる
        if (chatWindow) {
            chatWindow.style.paddingTop = (Math.ceil(headerHeight) + 12) + 'px';
        }
    }

    // chat-window の padding-bottom をコントロールエリア高さに合わせる
    if (controlArea && chatWindow) {
        if (!controlArea.classList.contains('minimized')) {
            const controlHeight = controlArea.getBoundingClientRect().height;
            chatWindow.style.paddingBottom = (controlHeight + 16) + 'px';
        }
    }
}

// ページ読み込み時（複数タイミングで実行してレンダリング完了を待つ）
document.addEventListener('DOMContentLoaded', () => {
    adjustAll();
    setTimeout(adjustAll, 100);
    setTimeout(adjustAll, 300);
});

// 画面リサイズ・回転時
window.addEventListener('resize', adjustAll);

// コントロールエリアの開閉監視
document.addEventListener('DOMContentLoaded', () => {
    const controlArea = document.querySelector('.control-area');
    if (controlArea) {
        new MutationObserver(adjustAll).observe(controlArea, {
            attributes: true,
            attributeFilter: ['class']
        });
    }
});

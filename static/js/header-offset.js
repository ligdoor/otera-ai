/**
 * header-offset.js
 * ヘッダーの実際の高さを取得し、
 * back-btn / clear-chat-btn の位置を動的に設定する
 *
 * 理由: ヘッダーはスマホで2行になる場合があり
 *      CSSのtop固定値だとボタンがヘッダーの後ろに隠れてしまう
 */

function adjustHeaderOffset() {
    const header = document.querySelector('header');
    if (!header) return;

    // ヘッダーの実際の高さ（px）を取得
    const headerHeight = header.getBoundingClientRect().height;
    // 少し余白を加える（8px）
    const offset = headerHeight + 8;

    // back-btn の位置を更新
    const backBtns = document.querySelectorAll('.back-btn');
    backBtns.forEach(btn => {
        btn.style.top = offset + 'px';
    });

    // clear-chat-btn の位置を更新
    const clearBtns = document.querySelectorAll('.clear-chat-btn');
    clearBtns.forEach(btn => {
        btn.style.top = offset + 'px';
    });
}

// ページ読み込み時に実行
document.addEventListener('DOMContentLoaded', adjustHeaderOffset);

// 画面リサイズ時にも再計算（横→縦回転など）
window.addEventListener('resize', adjustHeaderOffset);

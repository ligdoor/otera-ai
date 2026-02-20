/**
 * temple-admin.js
 * 寺院管理システム - スタッフ向け管理画面 共通スクリプト
 *
 * 機能:
 *   - 削除確認モーダル（data-confirm 属性で簡単に使える）
 *   - トースト通知（操作結果を右下に表示）
 *   - フォーム送信の二重送信防止
 *   - セッションタイムアウト警告
 *
 * 使い方（admin.html の </body> 直前に追加）:
 *   <script src="/static/js/temple-admin.js"></script>
 */

'use strict';


/* ============================================================
   トースト通知
   ============================================================ */
const Toast = (() => {
  let container = null;

  function getContainer() {
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  /**
   * トーストを表示する
   * @param {string} message - 表示メッセージ
   * @param {'success'|'error'|'info'} type - 種類
   * @param {number} duration - 表示時間（ms）
   */
  function show(message, type = 'info', duration = 3000) {
    const icons = { success: '✅', error: '⚠️', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
    getContainer().appendChild(toast);

    setTimeout(() => {
      toast.addEventListener('animationend', () => toast.remove(), { once: true });
      toast.style.animation = 'toastOut 0.25s ease forwards';
    }, duration);
  }

  return { show,
    success: (msg) => show(msg, 'success'),
    error:   (msg) => show(msg, 'error'),
    info:    (msg) => show(msg, 'info'),
  };
})();

// グローバルに公開
window.Toast = Toast;


/* ============================================================
   削除確認モーダル
   ============================================================ */
const ConfirmModal = (() => {
  let modalEl = null;

  function getModal() {
    if (modalEl) return modalEl;

    modalEl = document.createElement('div');
    modalEl.className = 'modal-overlay';
    modalEl.style.display = 'none';
    modalEl.setAttribute('role', 'dialog');
    modalEl.setAttribute('aria-modal', 'true');
    modalEl.innerHTML = `
      <div class="modal-box">
        <div class="modal-header">
          <h2 id="confirm-modal-title">確認</h2>
          <button class="modal-close" id="confirm-modal-close" aria-label="閉じる">✕</button>
        </div>
        <div class="modal-body">
          <p id="confirm-modal-message"></p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" id="confirm-modal-cancel">キャンセル</button>
          <button class="btn btn-danger" id="confirm-modal-ok">削除する</button>
        </div>
      </div>
    `;
    document.body.appendChild(modalEl);

    // 閉じるボタン
    modalEl.querySelector('#confirm-modal-close').addEventListener('click', close);
    modalEl.querySelector('#confirm-modal-cancel').addEventListener('click', close);

    // オーバーレイクリックで閉じる
    modalEl.addEventListener('click', (e) => { if (e.target === modalEl) close(); });

    // ESCキーで閉じる
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });

    return modalEl;
  }

  function close() {
    const m = getModal();
    m.style.display = 'none';
  }

  /**
   * 確認ダイアログを表示する
   * @param {Object} options
   * @param {string} options.message   - 確認メッセージ
   * @param {string} [options.title]   - ダイアログタイトル
   * @param {string} [options.okLabel] - OKボタンのラベル
   * @param {Function} options.onOk    - OK押下時のコールバック
   */
  function show({ message, title = '操作の確認', okLabel = '実行する', onOk }) {
    const m = getModal();
    m.querySelector('#confirm-modal-title').textContent   = title;
    m.querySelector('#confirm-modal-message').textContent = message;
    m.querySelector('#confirm-modal-ok').textContent      = okLabel;
    m.style.display = 'flex';

    // OKボタン：一度クリックしたら外す（二重実行防止）
    const okBtn = m.querySelector('#confirm-modal-ok');
    const newOkBtn = okBtn.cloneNode(true);
    okBtn.parentNode.replaceChild(newOkBtn, okBtn);
    newOkBtn.textContent = okLabel;
    newOkBtn.addEventListener('click', async () => {
      close();
      if (typeof onOk === 'function') await onOk();
    }, { once: true });
  }

  return { show, close };
})();

window.ConfirmModal = ConfirmModal;


/* ============================================================
   data-confirm 属性による自動削除確認
   ============================================================
   使い方:
     <button
       class="btn btn-danger btn-sm"
       data-confirm="「○○寺」を削除しますか？"
       data-action="/api/temples/1"
       data-method="DELETE"
       data-success="削除しました"
     >
       🗑️ 削除
     </button>
*/
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-confirm]');
  if (!btn) return;
  e.preventDefault();

  const message = btn.dataset.confirm   || '本当に実行しますか？';
  const action  = btn.dataset.action    || '';
  const method  = (btn.dataset.method   || 'POST').toUpperCase();
  const successMsg = btn.dataset.success || '完了しました';
  const errorMsg   = btn.dataset.error  || '操作に失敗しました';
  const okLabel    = btn.dataset.oklabel || (method === 'DELETE' ? '削除する' : '実行する');

  ConfirmModal.show({
    message,
    title: btn.dataset.title || '操作の確認',
    okLabel,
    onOk: async () => {
      if (!action) {
        // action が未指定の場合はカスタムイベントを発火
        btn.dispatchEvent(new CustomEvent('confirmed', { bubbles: true }));
        return;
      }

      btn.disabled = true;
      btn.classList.add('loading');

      try {
        // CSRFトークンを取得
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

        const res = await fetch(action, {
          method,
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken,
          },
        });

        const data = await res.json().catch(() => ({}));

        if (res.ok) {
          Toast.success(data.message || successMsg);
          // 行を削除（テーブル行の場合）
          const row = btn.closest('tr');
          if (row) {
            row.style.transition = 'opacity 0.3s';
            row.style.opacity = '0';
            setTimeout(() => row.remove(), 300);
          }
          // カスタムイベントを発火（親コンポーネントが追加処理できる）
          btn.dispatchEvent(new CustomEvent('deleteSuccess', { bubbles: true, detail: data }));
        } else {
          Toast.error(data.message || errorMsg);
        }
      } catch (err) {
        console.error('操作エラー:', err);
        Toast.error('通信エラーが発生しました。再度お試しください。');
      } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
      }
    },
  });
});


/* ============================================================
   フォームの二重送信防止
   ============================================================ */
document.addEventListener('submit', (e) => {
  const form = e.target;
  if (form.dataset.noDouble === 'false') return; // 明示的に無効化している場合はスキップ

  const submitBtn = form.querySelector('[type="submit"]');
  if (!submitBtn) return;

  const originalText = submitBtn.textContent;
  submitBtn.disabled = true;
  submitBtn.classList.add('loading');
  submitBtn.dataset.originalText = originalText;

  // タイムアウト後に自動復旧（送信が失敗した場合など）
  setTimeout(() => {
    submitBtn.disabled = false;
    submitBtn.classList.remove('loading');
    submitBtn.textContent = submitBtn.dataset.originalText || originalText;
  }, 10000);
});


/* ============================================================
   セッションタイムアウト警告
   ============================================================
   セッション残り5分でモーダル警告を表示
*/
(function initSessionWarning() {
  // サーバー側のタイムアウト設定（分）をmetaタグから取得
  const metaTimeout = document.querySelector('meta[name="session-timeout"]');
  const timeoutMinutes = metaTimeout ? parseInt(metaTimeout.content, 10) : 60;

  if (!timeoutMinutes || timeoutMinutes <= 0) return;

  const warningAt = (timeoutMinutes - 5) * 60 * 1000;  // 残り5分で警告
  const timeoutAt = timeoutMinutes * 60 * 1000;

  // 警告タイマー
  if (warningAt > 0) {
    setTimeout(() => {
      Toast.info(`セッションが5分後に終了します。作業を保存してください。`);
    }, warningAt);
  }

  // タイムアウト時にリダイレクト
  setTimeout(() => {
    Toast.error('セッションが終了しました。ログインページに移動します。');
    setTimeout(() => { window.location.href = '/admin'; }, 2000);
  }, timeoutAt);
})();


/* ============================================================
   ユーティリティ関数
   ============================================================ */

/**
 * 相対時間表示（「3分前」「2時間前」など）
 * @param {string|Date} dateStr
 * @returns {string}
 */
function timeAgo(dateStr) {
  const date = new Date(dateStr);
  const now  = new Date();
  const diffSec = Math.floor((now - date) / 1000);

  if (diffSec <    60) return `${diffSec}秒前`;
  if (diffSec <  3600) return `${Math.floor(diffSec / 60)}分前`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}時間前`;
  const diffDays = Math.floor(diffSec / 86400);
  if (diffDays <  30) return `${diffDays}日前`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}ヶ月前`;
  return `${Math.floor(diffDays / 365)}年前`;
}

/**
 * ページ内のすべての「相対時間」要素を更新する
 * <time data-timeago="2025-01-01T00:00:00Z"> に適用
 */
function updateTimeAgoElements() {
  document.querySelectorAll('time[data-timeago]').forEach((el) => {
    const original = el.dataset.timeago;
    if (original) {
      el.textContent = timeAgo(original);
      el.title = new Date(original).toLocaleString('ja-JP');
    }
  });
}

updateTimeAgoElements();
setInterval(updateTimeAgoElements, 60 * 1000); // 1分ごとに更新

// グローバルに公開
window.timeAgo = timeAgo;

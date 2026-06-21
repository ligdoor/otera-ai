/**
 * ==========================================
 * 設定モーダル管理システム
 * static/js/settings-modal.js
 * ==========================================
 * 
 * 機能:
 * - 設定モーダルの開閉
 * - フォントサイズ・行間・テーマの設定
 * - リアルタイムプレビュー
 * - 設定の保存・適用
 */

class SettingsModal {
    constructor(settingsManager) {
        this.settingsManager = settingsManager;
        this.modal = null;
        this.previewText = null;
        this.tempSettings = {
            fontSize: 'normal',
            lineHeight: 'normal',
            theme: 'light'
        };
        this.initialized = false;
    }

    /**
     * 初期化
     */
    init() {
        if (this.initialized) {
            console.log('[SettingsModal] 既に初期化済み');
            return;
        }

        console.log('[SettingsModal] 初期化開始');

        // DOM要素を取得
        this.modal = document.getElementById('settings-modal');
        this.previewText = document.querySelector('.preview-text');

        if (!this.modal) {
            console.error('[SettingsModal] モーダル要素が見つかりません');
            return;
        }

        // イベントリスナーを設定
        this.setupEventListeners();

        this.initialized = true;
        console.log('[SettingsModal] 初期化完了');
    }

    /**
     * イベントリスナーを設定
     */
    setupEventListeners() {
        // 設定ボタン
        const settingsBtn = document.getElementById('settings-btn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.open());
        }

        // 閉じるボタン
        const closeBtn = document.getElementById('settings-modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        // 背景クリックで閉じる
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.close();
            }
        });

        // ESCキーで閉じる
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.classList.contains('show')) {
                this.close();
            }
        });

        // 保存ボタン
        const saveBtn = document.getElementById('settings-save-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.save());
        }

        // キャンセルボタン
        const cancelBtn = document.getElementById('settings-cancel-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.close());
        }

        // ラジオボタンの変更イベント（リアルタイムプレビュー）
        this.setupRadioListeners();
    }

    /**
     * ラジオボタンのリスナーを設定（プレビュー用）
     */
    setupRadioListeners() {
        // フォントサイズ
        const fontSizeRadios = document.querySelectorAll('input[name="fontSize"]');
        fontSizeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.tempSettings.fontSize = e.target.value;
                this.updatePreview();
            });
        });

        // 行間
        const lineHeightRadios = document.querySelectorAll('input[name="lineHeight"]');
        lineHeightRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.tempSettings.lineHeight = e.target.value;
                this.updatePreview();
            });
        });

        // テーマ
        const themeRadios = document.querySelectorAll('input[name="theme"]');
        themeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.tempSettings.theme = e.target.value;
                this.updatePreview();
            });
        });
    }

    /**
     * ログイン状態をサーバーに確認する
     */
    async checkLogin() {
        try {
            const res = await fetch('/check_login', { credentials: 'same-origin' });
            if (!res.ok) return false;
            const data = await res.json();
            return data.logged_in === true;
        } catch (e) {
            console.error('[SettingsModal] ログイン確認エラー:', e);
            return false;
        }
    }

    /**
     * モーダルを開く（未ログインの場合はログインページへ誘導）
     */
    async open() {
        console.log('[SettingsModal] モーダルを開く');

        // ログインチェック
        const loggedIn = await this.checkLogin();
        if (!loggedIn) {
            console.log('[SettingsModal] 未ログインのためログインページへ誘導');
            // ログイン後に設定を開けるようパラメータ付きで遷移
            window.location.href = '/admin?next=settings';
            return;
        }

        // 現在の設定を取得
        const currentSettings = this.settingsManager.getCurrentSettings();
        this.tempSettings = { ...currentSettings };

        // モーダルに現在の設定を反映
        this.loadCurrentSettings();

        // モーダルを表示
        this.modal.classList.add('show');
        document.body.style.overflow = 'hidden'; // スクロール無効化

        // プレビューを更新
        this.updatePreview();
    }

    /**
     * モーダルを閉じる
     */
    close() {
        console.log('[SettingsModal] モーダルを閉じる');

        this.modal.classList.remove('show');
        document.body.style.overflow = ''; // スクロール有効化

        // 元の設定に戻す（プレビューをクリア）
        this.revertPreview();
    }

    /**
     * 現在の設定をモーダルに読み込み
     */
    loadCurrentSettings() {
        // フォントサイズ
        const fontSizeRadio = document.querySelector(`input[name="fontSize"][value="${this.tempSettings.fontSize}"]`);
        if (fontSizeRadio) fontSizeRadio.checked = true;

        // 行間
        const lineHeightRadio = document.querySelector(`input[name="lineHeight"][value="${this.tempSettings.lineHeight}"]`);
        if (lineHeightRadio) lineHeightRadio.checked = true;

        // テーマ
        const themeRadio = document.querySelector(`input[name="theme"][value="${this.tempSettings.theme}"]`);
        if (themeRadio) themeRadio.checked = true;
    }

    /**
     * プレビューを更新（リアルタイム）
     */
    updatePreview() {
        if (!this.previewText) return;

        // フォントサイズのマッピング
        const fontSizeMap = {
            'small': '14px',
            'normal': '16px',
            'large': '18px'
        };

        // 行間のマッピング
        const lineHeightMap = {
            'narrow': '1.4',
            'normal': '1.6',
            'wide': '1.9'
        };

        // プレビューに適用
        this.previewText.style.fontSize = fontSizeMap[this.tempSettings.fontSize];
        this.previewText.style.lineHeight = lineHeightMap[this.tempSettings.lineHeight];

        // テーマをプレビューエリアに適用
        const previewArea = this.previewText.parentElement;
        if (this.tempSettings.theme === 'dark') {
            previewArea.style.backgroundColor = '#2d2d2d';
            this.previewText.style.color = '#e0e0e0';
        } else {
            previewArea.style.backgroundColor = '#f9f9f9';
            this.previewText.style.color = '#333';
        }

        console.log('[SettingsModal] プレビュー更新:', this.tempSettings);
    }

    /**
     * プレビューを元に戻す
     */
    revertPreview() {
        if (!this.previewText) return;

        // プレビューのスタイルをクリア
        this.previewText.style.fontSize = '';
        this.previewText.style.lineHeight = '';

        const previewArea = this.previewText.parentElement;
        previewArea.style.backgroundColor = '';
        this.previewText.style.color = '';
    }

    /**
     * 設定を保存
     */
    async save() {
        console.log('[SettingsModal] 設定を保存:', this.tempSettings);

        try {
            // フォントサイズを保存
            await this.settingsManager.saveFontSize(this.tempSettings.fontSize);

            // 行間を保存
            await this.settingsManager.saveLineHeight(this.tempSettings.lineHeight);

            // テーマを保存
            await this.settingsManager.saveTheme(this.tempSettings.theme);

            // 成功メッセージ
            this.showToast('設定を保存しました');

            // モーダルを閉じる
            this.close();

        } catch (error) {
            console.error('[SettingsModal] 設定保存エラー:', error);
            this.showToast('設定の保存に失敗しました', 'error');
        }
    }

    /**
     * トースト通知を表示
     */
    showToast(message, type = 'success') {
        // 既存のトースト関数があれば使用
        if (typeof showToast === 'function') {
            showToast(message);
        } else {
            // フォールバック: alertで表示
            alert(message);
        }
    }
}

// ==========================================
// グローバル変数
// ==========================================
let settingsModal;

// ==========================================
// 初期化（settings-manager.js の後に実行）
// ==========================================
document.addEventListener('DOMContentLoaded', function() {
    // settingsManager が初期化されるのを待つ
    const initSettingsModal = setInterval(() => {
        if (typeof settingsManager !== 'undefined' && settingsManager.initialized) {
            console.log('[App] 設定モーダルを初期化');
            
            settingsModal = new SettingsModal(settingsManager);
            settingsModal.init();
            
            clearInterval(initSettingsModal);
        }
    }, 100);

    // 10秒経ってもsettingsManagerが無ければエラー
    setTimeout(() => {
        clearInterval(initSettingsModal);
        if (!settingsModal) {
            console.error('[App] settingsManager が見つかりません');
        }
    }, 10000);
});
// ==========================================
// グローバル関数（ヘッダーから呼び出し用）
// ==========================================
function openSettingsModal() {
    if (settingsModal && settingsModal.initialized) {
        settingsModal.open();
    } else {
        console.error('設定モーダルが初期化されていません');
    }
}

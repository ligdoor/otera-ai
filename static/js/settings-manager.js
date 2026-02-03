/**
 * ==========================================
 * 設定管理システム (Settings Manager) - 修正版
 * 作成日: 2026-02-03
 * 修正日: 2026-02-03
 * 目的: フォントサイズとテーマのハイブリッド管理
 * ==========================================
 * 
 * 機能:
 * - ログイン時: Supabaseでデバイス間同期
 * - 未ログイン時: localStorageでローカル保存
 * - 即座のUI反映
 * 
 * 修正内容:
 * - Supabase Authではなくセッションベース認証に対応
 * - user_idをTEXT型として扱う
 */

class SettingsManager {
    constructor() {
        this.isLoggedIn = false;
        this.userId = null;
        this.currentFontSize = 'normal';
        this.currentTheme = 'light';
        this.initialized = false;
    }
    
    /**
     * 初期化
     * - ログイン状態確認
     * - 設定読み込み
     */
    async init() {
        if (this.initialized) {
            console.log('[SettingsManager] 既に初期化済み');
            return;
        }
        
        console.log('[SettingsManager] 初期化開始');
        
        try {
            // セッションベースの認証: /get_current_user から情報取得
            const userRes = await fetch('/get_current_user');
            
            if (userRes.ok) {
                const userData = await userRes.json();
                this.isLoggedIn = !!userData.user_id;
                this.userId = userData.user_id;
                
                console.log('[SettingsManager] ログイン状態:', this.isLoggedIn, 'user_id:', this.userId);
                
                // 設定を読み込み
                await this.loadSettings();
            } else {
                console.log('[SettingsManager] 未ログイン');
                this.loadFromLocalStorage();
            }
            
            this.initialized = true;
            console.log('[SettingsManager] 初期化完了');
        } catch (error) {
            console.error('[SettingsManager] 初期化エラー:', error);
            // エラー時はlocalStorageから読み込み
            this.loadFromLocalStorage();
            this.initialized = true;
        }
    }
    
    /**
     * 設定を読み込み
     */
    async loadSettings() {
        if (this.isLoggedIn) {
            console.log('[SettingsManager] サーバーから設定を読み込み中...');
            
            try {
                // バックエンドのAPIエンドポイントを呼び出し
                const res = await fetch('/api/user-settings');
                
                if (res.ok) {
                    const data = await res.json();
                    console.log('[SettingsManager] サーバーから読み込み成功:', data);
                    
                    // サーバーの設定を適用
                    this.currentFontSize = data.font_size || 'normal';
                    this.currentTheme = data.theme || 'light';
                    
                    this.applyFontSize(this.currentFontSize);
                    this.applyTheme(this.currentTheme);
                    
                    // localStorageにも保存（オフライン時用）
                    localStorage.setItem('fontSize', this.currentFontSize);
                    localStorage.setItem('theme', this.currentTheme);
                } else if (res.status === 404) {
                    // データが存在しない（初回ログイン）
                    console.log('[SettingsManager] サーバーにデータなし、localStorageから読み込み');
                    this.loadFromLocalStorage();
                    
                    // サーバーに初期データを作成
                    await this.saveToServer(this.currentFontSize, this.currentTheme);
                } else {
                    console.warn('[SettingsManager] サーバー読み込みエラー:', res.status);
                    this.loadFromLocalStorage();
                }
            } catch (error) {
                console.error('[SettingsManager] サーバー読み込み例外:', error);
                this.loadFromLocalStorage();
            }
        } else {
            console.log('[SettingsManager] 未ログイン、localStorageから読み込み');
            this.loadFromLocalStorage();
        }
    }
    
    /**
     * localStorageから読み込み
     */
    loadFromLocalStorage() {
        this.currentFontSize = localStorage.getItem('fontSize') || 'normal';
        this.currentTheme = localStorage.getItem('theme') || 'light';
        
        this.applyFontSize(this.currentFontSize);
        this.applyTheme(this.currentTheme);
        
        console.log('[SettingsManager] localStorageから読み込み:', {
            fontSize: this.currentFontSize,
            theme: this.currentTheme
        });
    }
    
    /**
     * フォントサイズを保存
     */
    async saveFontSize(size) {
        console.log('[SettingsManager] フォントサイズ保存:', size);
        
        this.currentFontSize = size;
        
        // 即座にUIに反映
        this.applyFontSize(size);
        
        // localStorage に保存（即座）
        localStorage.setItem('fontSize', size);
        
        // ログイン中はサーバーにも保存（バックグラウンド）
        if (this.isLoggedIn) {
            await this.saveToServer(size, this.currentTheme);
        }
    }
    
    /**
     * テーマを保存
     */
    async saveTheme(theme) {
        console.log('[SettingsManager] テーマ保存:', theme);
        
        this.currentTheme = theme;
        
        // 即座にUIに反映
        this.applyTheme(theme);
        
        // localStorage に保存
        localStorage.setItem('theme', theme);
        
        // ログイン中はサーバーにも保存
        if (this.isLoggedIn) {
            await this.saveToServer(this.currentFontSize, theme);
        }
    }
    
    /**
     * サーバーに保存
     */
    async saveToServer(fontSize, theme) {
        try {
            const res = await fetch('/api/user-settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    font_size: fontSize,
                    theme: theme
                })
            });
            
            if (!res.ok) {
                console.error('[SettingsManager] サーバー保存エラー:', res.status);
            } else {
                console.log('[SettingsManager] サーバー保存成功');
            }
        } catch (error) {
            console.error('[SettingsManager] サーバー保存例外:', error);
        }
    }
    
    /**
     * フォントサイズを適用
     */
    applyFontSize(size) {
        // クラスを削除
        document.body.classList.remove('font-small', 'font-large');
        
        // 新しいクラスを追加
        if (size === 'small') {
            document.body.classList.add('font-small');
        } else if (size === 'large') {
            document.body.classList.add('font-large');
        }
        
        // ボタンの表示を更新
        const btn = document.getElementById('font-size-toggle');
        if (btn) {
            if (size === 'small') {
                btn.style.fontSize = '16px';
                btn.title = '文字サイズ: 小';
            } else if (size === 'normal') {
                btn.style.fontSize = '20px';
                btn.title = '文字サイズ: 標準';
            } else if (size === 'large') {
                btn.style.fontSize = '24px';
                btn.title = '文字サイズ: 大';
            }
        }
        
        console.log('[SettingsManager] フォントサイズ適用:', size);
    }
    
    /**
     * テーマを適用
     */
    applyTheme(theme) {
        if (theme === 'dark') {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
        
        // テーマ切り替えボタンの更新
        const btn = document.querySelector('.header-btn[onclick*="toggleDarkMode"]');
        if (btn) {
            btn.textContent = theme === 'dark' ? '☀️' : '🌙';
            btn.title = theme === 'dark' ? 'ライトモードに切替' : 'ダークモードに切替';
        }
        
        console.log('[SettingsManager] テーマ適用:', theme);
    }
    
    /**
     * フォントサイズを切り替え
     */
    async toggleFontSize() {
        const sizes = ['small', 'normal', 'large'];
        const currentIndex = sizes.indexOf(this.currentFontSize);
        const nextSize = sizes[(currentIndex + 1) % sizes.length];
        
        await this.saveFontSize(nextSize);
        
        const sizeNames = { 'small': '小', 'normal': '標準', 'large': '大' };
        console.log(`文字サイズ変更: ${sizeNames[nextSize]}`);
    }
    
    /**
     * テーマを切り替え
     */
    async toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        await this.saveTheme(newTheme);
        
        const themeNames = { 'light': 'ライトモード', 'dark': 'ダークモード' };
        console.log(`テーマ変更: ${themeNames[newTheme]}`);
    }
    
    /**
     * 現在の設定を取得
     */
    getCurrentSettings() {
        return {
            fontSize: this.currentFontSize,
            theme: this.currentTheme,
            isLoggedIn: this.isLoggedIn
        };
    }
}

// ==========================================
// グローバルインスタンス
// ==========================================
const settingsManager = new SettingsManager();

// ==========================================
// ページ読み込み時に初期化
// ==========================================
document.addEventListener('DOMContentLoaded', async function() {
    console.log('[App] 設定マネージャー初期化開始');
    
    // 設定マネージャーを初期化
    await settingsManager.init();
    
    // フォントサイズボタンのイベント
    const fontBtn = document.getElementById('font-size-toggle');
    if (fontBtn) {
        fontBtn.addEventListener('click', () => settingsManager.toggleFontSize());
        console.log('[App] フォントサイズボタンのイベント設定完了');
    } else {
        console.warn('[App] フォントサイズボタンが見つかりません');
    }
    
    // 既存のダークモードボタンをラップ
    const darkModeBtn = document.querySelector('.header-btn[onclick*="toggleDarkMode"]');
    if (darkModeBtn) {
        // 既存のonclick属性を削除
        darkModeBtn.removeAttribute('onclick');
        // 新しいイベントを追加
        darkModeBtn.addEventListener('click', () => settingsManager.toggleTheme());
        console.log('[App] ダークモードボタンのイベント設定完了');
    } else {
        console.warn('[App] ダークモードボタンが見つかりません');
    }
    
    console.log('[App] 設定マネージャー初期化完了');
    console.log('[App] 現在の設定:', settingsManager.getCurrentSettings());
});
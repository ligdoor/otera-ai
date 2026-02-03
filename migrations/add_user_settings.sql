-- ==========================================
-- ユーザー設定テーブル作成マイグレーション（修正版）
-- 作成日: 2026-02-03
-- 修正: user_id の型を BIGINT に変更
-- 注意: RLSはアプリ側のセッション認証で制御
-- ==========================================

-- ユーザー設定テーブルを作成
CREATE TABLE IF NOT EXISTS user_settings (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    font_size TEXT DEFAULT 'normal' CHECK (font_size IN ('small', 'normal', 'large')),
    theme TEXT DEFAULT 'light' CHECK (theme IN ('light', 'dark')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- インデックス作成（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);

-- 更新日時の自動更新トリガー関数
CREATE OR REPLACE FUNCTION update_user_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- トリガー設定
DROP TRIGGER IF EXISTS trigger_update_user_settings_updated_at ON user_settings;
CREATE TRIGGER trigger_update_user_settings_updated_at
    BEFORE UPDATE ON user_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_user_settings_updated_at();

-- テーブルとカラムにコメント追加
COMMENT ON TABLE user_settings IS 'ユーザーごとの表示設定（フォントサイズ、テーマなど）';
COMMENT ON COLUMN user_settings.user_id IS 'ユーザーID（usersテーブルのidへの外部キー、BIGINT型）';
COMMENT ON COLUMN user_settings.font_size IS 'フォントサイズ: small（小）, normal（標準）, large（大）';
COMMENT ON COLUMN user_settings.theme IS 'テーマ: light（ライト）, dark（ダーク）';
COMMENT ON COLUMN user_settings.created_at IS '作成日時';
COMMENT ON COLUMN user_settings.updated_at IS '更新日時';

-- 確認用: テーブルが正常に作成されたかチェック
SELECT 
    tablename, 
    schemaname 
FROM pg_tables 
WHERE tablename = 'user_settings';

-- 確認用: カラムの型をチェック
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'user_settings'
ORDER BY ordinal_position;
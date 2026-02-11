-- 1. ユーザー管理テーブル
-- 所持金とVC滞在時間の端数をまとめて管理
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    balance INT DEFAULT 0,
    vc_minutes_total INT DEFAULT 0  -- VC報酬用の累計分数
);

-- 2. サブスクリプション管理テーブル
-- ユーザーごとの有効期限と自動更新状態を管理
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id BIGINT PRIMARY KEY,
    end_date DATETIME NOT NULL,     -- 有効期限
    active TINYINT(1) DEFAULT 1,    -- 1:自動更新あり, 0:解約予約
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

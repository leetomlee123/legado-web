-- Legado Web 数据库 Schema (PostgreSQL)

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          VARCHAR(20) NOT NULL DEFAULT 'user', -- 'admin' / 'user'
    nickname      VARCHAR(100) DEFAULT '',
    create_time   BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_username ON users (username);

-- 用户令牌表
CREATE TABLE IF NOT EXISTS user_tokens (
    token       VARCHAR(128) PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    create_time BIGINT NOT NULL,
    expire_time BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_tokens_user_id ON user_tokens (user_id);

-- 书籍表
CREATE TABLE IF NOT EXISTS book (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER DEFAULT 1,
    uuid           VARCHAR(128) DEFAULT '',
    name           TEXT NOT NULL,
    author         TEXT DEFAULT '',
    cover          TEXT DEFAULT '',
    intro          TEXT DEFAULT '',
    source_type    VARCHAR(20) DEFAULT 'txt',
    source_url     TEXT DEFAULT '',
    source_id      INTEGER DEFAULT 0,
    local_path     TEXT DEFAULT '',
    book_group     VARCHAR(100) DEFAULT '默认分组',
    in_bookcase    INTEGER DEFAULT 1,
    last_read_time BIGINT DEFAULT 0,
    create_time    BIGINT DEFAULT 0,
    has_update     INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_book_name ON book (name);
CREATE INDEX IF NOT EXISTS idx_book_group ON book (book_group);
CREATE INDEX IF NOT EXISTS idx_book_user_shelf ON book (user_id, in_bookcase);
CREATE UNIQUE INDEX IF NOT EXISTS idx_book_uuid ON book (uuid) WHERE uuid != '';

-- 章节表
CREATE TABLE IF NOT EXISTS chapter (
    id           SERIAL PRIMARY KEY,
    book_id      INTEGER NOT NULL REFERENCES book(id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    idx          INTEGER DEFAULT 0,
    content_url  TEXT DEFAULT '',
    content      TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_chapter_book ON chapter (book_id, idx);

-- 书源表（全站共享）
CREATE TABLE IF NOT EXISTS book_source (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    url         TEXT DEFAULT '',
    enabled     INTEGER DEFAULT 1,
    rule        TEXT DEFAULT '',
    create_time BIGINT DEFAULT 0
);

-- 阅读进度（按书籍记忆章节）
CREATE TABLE IF NOT EXISTS read_progress (
    id          SERIAL PRIMARY KEY,
    book_id     INTEGER NOT NULL UNIQUE,
    chapter_id  INTEGER DEFAULT 0,
    chapter_idx INTEGER DEFAULT 0,
    pos         REAL DEFAULT 0,
    update_time BIGINT DEFAULT 0
);

-- 历史记录（最近阅读）
CREATE TABLE IF NOT EXISTS history (
    id        SERIAL PRIMARY KEY,
    book_id   INTEGER NOT NULL UNIQUE,
    read_time BIGINT DEFAULT 0
);

-- 应用设置（key-value）
CREATE TABLE IF NOT EXISTS settings (
    key   VARCHAR(100) PRIMARY KEY,
    value TEXT DEFAULT ''
);

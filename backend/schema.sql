-- Legado Web 数据库 Schema (SQLite)

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user', -- 'admin' / 'user'
    nickname      TEXT DEFAULT '',
    create_time   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_username ON users (username);

-- 用户令牌表
CREATE TABLE IF NOT EXISTS user_tokens (
    token       TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    create_time INTEGER NOT NULL,
    expire_time INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_user_tokens_user_id ON user_tokens (user_id);

-- 书籍表
CREATE TABLE IF NOT EXISTS book (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER DEFAULT 1,           -- 所属用户ID
    uuid          TEXT    DEFAULT '',          -- 前端预生成的 UUID，搜索结果坑位唯一标识
    name          TEXT    NOT NULL,
    author        TEXT    DEFAULT '',
    cover         TEXT    DEFAULT '',          -- 封面URL或本地路径
    intro         TEXT    DEFAULT '',          -- 简介
    source_type   TEXT    DEFAULT 'txt',       -- txt / epub / pdf / web
    source_url    TEXT    DEFAULT '',          -- 书源URL（web书）
    source_id     INTEGER DEFAULT 0,           -- 来源书源id
    local_path    TEXT    DEFAULT '',          -- 本地文件路径（txt/epub/pdf）
    book_group    TEXT    DEFAULT '默认分组',
    in_bookcase   INTEGER DEFAULT 1,           -- 1=显示在书架, 0=预览模式不入架
    last_read_time INTEGER DEFAULT 0,          -- 最近阅读时间戳
    create_time   INTEGER DEFAULT 0,
    has_update    INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_book_name ON book (name);
CREATE INDEX IF NOT EXISTS idx_book_group ON book (book_group);

-- 章节表
CREATE TABLE IF NOT EXISTS chapter (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id      INTEGER NOT NULL,
    title        TEXT NOT NULL,
    idx          INTEGER DEFAULT 0,
    content_url  TEXT DEFAULT '',   -- web章节原文地址
    content      TEXT DEFAULT '',   -- 文本内容（本地书直接存，web书按需加载）
    FOREIGN KEY (book_id) REFERENCES book(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_chapter_book ON chapter (book_id, idx);

-- 书源表（全站共享）
CREATE TABLE IF NOT EXISTS book_source (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    url          TEXT DEFAULT '',             -- 搜索接口（含 {search}）或订阅/首页
    enabled      INTEGER DEFAULT 1,
    rule         TEXT DEFAULT '',             -- 书源规则 JSON（search/detail/toc/content 选择器）
    create_time  INTEGER DEFAULT 0
);

-- 阅读进度（按书籍记忆章节）
CREATE TABLE IF NOT EXISTS read_progress (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL,
    chapter_id  INTEGER DEFAULT 0,
    chapter_idx INTEGER DEFAULT 0,
    pos         REAL DEFAULT 0,
    update_time INTEGER DEFAULT 0,
    UNIQUE (book_id)
);

-- 历史记录（最近阅读）
CREATE TABLE IF NOT EXISTS history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL,
    read_time   INTEGER DEFAULT 0,
    UNIQUE (book_id)
);

-- 应用设置（key-value）
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT DEFAULT ''
);

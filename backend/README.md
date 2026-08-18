# Legado Web Python Backend (Flask + SQLite)
# 替代 Go 后端，使用 curl_cffi 进行网络请求

## 启动方式
1. `cd backend/python`
2. `pip install -r requirements.txt`
3. `python main.py`

## requirements.txt
```txt
flask>=3.0.0
flask-cors>=4.0.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
pdfplumber>=0.10.0
reportlab>=4.0.0
python-magic>=0.4.27
filetype>=1.2.0
```

## 主要文件说明
- `main.py` - 核心 Flask 应用
- `schema.sql` - 数据库表结构
- `types.py` - Python 对应后端类型 (可选)

## 主要变化
- 替换 Go 网络请求为 `curl_cffi`
- 替换 PDF 解析为 `pdfplumber` + `reportlab`
- 替换 EPUB 解析为 `zipfile` + `beautifulsoup4`
- 保持一致的 REST API 和前端兼容

## 推荐使用
```bash
# 替代 Go 后端
PORT=8081 python main.py
```

## 替代方案 (更推荐)
```bash
# 使用 FastAPI + Uvicorn (更现代)
pip install "uvicorn[standard]" fastapi
uvicorn main:app --host 0.0.0.0 --port 8081
```
# -*- coding: utf-8 -*-
"""数据库连接配置。

**这里不存任何口令**。口令按下面的顺序取，取到就用：
  1. 环境变量 DB_PASSWORD（推荐：演示机、老师机器上都用这个）
  2. 同目录下 secrets_local.py 里的 DB_PASSWORD（本地开发用，已在 .gitignore 中）
  3. 都没有 → 留空，启动自检会给出中文提示，而不是抛一堆堆栈

其它参数同样可用环境变量覆盖。
"""
import os

from pymysql.cursors import DictCursor

# 本地口令文件（可选）：secrets_local.py 里写一行 DB_PASSWORD = "..."
try:
    from secrets_local import DB_PASSWORD as _LOCAL_PASSWORD  # type: ignore
except Exception:  # 文件不存在或没定义，都当作没配
    _LOCAL_PASSWORD = ""

DB_PASSWORD = os.environ.get("DB_PASSWORD") or _LOCAL_PASSWORD or ""

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USER", "root"),
    "password": DB_PASSWORD,
    "database": os.environ.get("DB_NAME", "cnev_export_trade_db"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
    "autocommit": False,
}

# 会话签名密钥：优先环境变量，其次本地文件，最后每次启动随机生成。
# 随机只影响「重启后还没读的提示条丢失」，不影响任何功能，但绝不会把密钥写进源码。
SECRET_KEY = os.environ.get("SECRET_KEY") or ""
if not SECRET_KEY:
    try:
        from secrets_local import SECRET_KEY as _LOCAL_SECRET  # type: ignore
        SECRET_KEY = _LOCAL_SECRET
    except Exception:
        SECRET_KEY = ""
if not SECRET_KEY:
    import secrets as _secrets
    SECRET_KEY = _secrets.token_hex(32)

# Web 服务端口
SERVER_PORT = int(os.environ.get("PORT", 5000))
SERVER_HOST = os.environ.get("HOST", "127.0.0.1")

# 系统信息
SYSTEM_NAME = "中国新能源汽车出口贸易数据管理系统"
SYSTEM_SHORT = "NEV 出口贸易数据平台"
GROUP_NAME = "2025级软件工程6班第3小组 · 黑科技小组"
COURSE_NAME = "《数据库原理》三级项目"

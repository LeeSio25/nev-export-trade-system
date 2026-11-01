# -*- coding: utf-8 -*-
"""数据库访问层：连接管理、元数据（表/列/主外键）、通用增删改查 SQL 构造。"""
import pymysql
from flask import g
from config import DB_CONFIG

# ---------------------------------------------------------------- 连接管理
def get_conn():
    if "conn" not in g:
        g.conn = pymysql.connect(**DB_CONFIG)
    return g.conn


def close_conn(e=None):
    conn = g.pop("conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def q(sql, params=None):
    """查询返回 list[dict]"""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params if params else None)
        return cur.fetchall()


def q1(sql, params=None):
    rows = q(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None):
    """增删改，返回影响行数"""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params if params else None)
        n = cur.rowcount
    conn.commit()
    return n


def insert(sql, params=None):
    """新增并返回自增主键（无自增列时返回 0）"""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params if params else None)
        lid = cur.lastrowid or 0
    conn.commit()
    return lid


def query_raw(sql, params=None, limit=300):
    """SQL 演示台用：返回 (columns, rows)"""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params if params else None)
        cols = [d[0] for d in (cur.description or [])]
        rows = cur.fetchmany(limit)
    return cols, rows


# ---------------------------------------------------------------- 表业务标签
TABLE_LABELS = {
    "autoenterprise": "汽车企业",
    "productionbase": "生产基地",
    "exportmodel": "出口车型",
    "country": "目的国",
    "dealer": "海外经销商",
    "exportorder": "出口订单",
    "orderdetail": "订单明细",
    "carrier": "物流承运商",
    "waybill": "物流运单",
    "policy": "贸易政策",
    "policyapply": "政策适用国家",
    "certification": "认证法规",
    "modelcert": "车型认证",
    "customs": "报关单",
    "currency": "币种",
    "exchangerate": "月度汇率",
    "aftersales": "海外售后网点",
    "qualityevent": "质量事件",
}

TABLE_ICONS = {
    "autoenterprise": "factory", "productionbase": "map", "exportmodel": "car",
    "country": "globe", "dealer": "handshake", "exportorder": "doc",
    "orderdetail": "list", "carrier": "truck", "waybill": "ship",
    "policy": "shield", "policyapply": "link", "certification": "badge",
    "modelcert": "check", "customs": "stamp", "currency": "coin",
    "exchangerate": "chart", "aftersales": "wrench", "qualityevent": "alert",
}

# 六大功能模块（对应系统功能图 1~6）
MODULES = [
    {"key": "basic", "title": "基础信息管理", "no": "1", "icon": "grid",
     "tables": ["autoenterprise", "productionbase", "exportmodel", "country", "dealer"]},
    {"key": "order", "title": "出口订单管理", "no": "2", "icon": "doc",
     "tables": ["exportorder", "orderdetail"]},
    {"key": "logistics", "title": "物流履约管理", "no": "3", "icon": "ship",
     "tables": ["carrier", "waybill"]},
    {"key": "policy", "title": "政策与市场准入", "no": "4", "icon": "shield",
     "tables": ["policy", "policyapply", "certification", "modelcert"]},
    {"key": "customs", "title": "报关与结算管理", "no": "5", "icon": "cash",
     "tables": ["customs", "currency", "exchangerate"]},
    {"key": "quality", "title": "售后与质量追溯", "no": "6", "icon": "wrench",
     "tables": ["aftersales", "qualityevent"]},
]

# ---------------------------------------------------------------- 元数据缓存
_META = {"at": 0, "tables": {}}


def load_meta(force=False):
    """从 information_schema 读真实表结构，不写死任何列名"""
    import time
    if not force and _META["at"] and time.time() - _META["at"] < 30:
        return _META["tables"]

    db = DB_CONFIG["database"]
    tables = {}
    for row in q("""SELECT TABLE_NAME AS n, TABLE_COMMENT AS c
                      FROM information_schema.TABLES
                     WHERE TABLE_SCHEMA=%s AND TABLE_TYPE='BASE TABLE'
                     ORDER BY TABLE_NAME""", (db,)):
        tables[row["n"]] = {
            "name": row["n"],
            "label": TABLE_LABELS.get(row["n"], row["n"]),
            "comment": row["c"] or "",
            "icon": TABLE_ICONS.get(row["n"], "table"),
            "columns": [], "pk": [], "fks": [],
        }

    for c in q("""SELECT TABLE_NAME AS t, COLUMN_NAME AS n, DATA_TYPE AS dt, COLUMN_TYPE AS ct,
                         IS_NULLABLE AS nul, COLUMN_KEY AS ck, COLUMN_DEFAULT AS df,
                         EXTRA AS ex, COLUMN_COMMENT AS cm, CHARACTER_MAXIMUM_LENGTH AS len
                    FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA=%s ORDER BY TABLE_NAME, ORDINAL_POSITION""", (db,)):
        t = tables.get(c["t"])
        if not t:
            continue
        full_cm = (c["cm"] or "").strip()
        short_cm = full_cm
        for sep in ("：", ":"):
            if sep in short_cm:
                short_cm = short_cm.split(sep)[0].strip()
                break
        short_cm = short_cm.rstrip("。")
        t["columns"].append({
            "name": c["n"], "type": (c["dt"] or "").lower(), "column_type": c["ct"],
            "short": short_cm,
            "nullable": c["nul"] == "YES", "key": c["ck"] or "",
            "default": c["df"], "extra": c["ex"] or "", "comment": c["cm"] or "",
            "max_len": int(c["len"]) if c["len"] is not None else None,
            "auto": "auto_increment" in (c["ex"] or "").lower(),
        })

    for f in q("""SELECT TABLE_NAME AS t, COLUMN_NAME AS c, REFERENCED_TABLE_NAME AS rt,
                         REFERENCED_COLUMN_NAME AS rc
                    FROM information_schema.KEY_COLUMN_USAGE
                   WHERE TABLE_SCHEMA=%s AND REFERENCED_TABLE_NAME IS NOT NULL""", (db,)):
        t = tables.get(f["t"])
        if not t:
            continue
        t["fks"].append({"col": f["c"], "ref_table": f["rt"], "ref_col": f["rc"]})
        for col in t["columns"]:
            if col["name"] == f["c"]:
                col["fk"] = {"table": f["rt"], "col": f["rc"]}

    for t in tables.values():
        t["pk"] = [c["name"] for c in t["columns"] if c["key"] == "PRI"]
        try:
            cnt = q1("SELECT COUNT(*) AS n FROM `%s`" % t["name"])
            t["row_count"] = int(cnt["n"]) if cnt else 0
        except Exception:
            t["row_count"] = 0

    _META["tables"] = tables
    _META["at"] = __import__("time").time()
    return tables


def get_table(name):
    return load_meta().get(name)


def display_column(tbl):
    """外键下拉要显示的"人话"列：名称类字段优先"""
    if not tbl:
        return None
    cols = tbl["columns"]
    for c in cols:
        if c["name"].lower().endswith("name") and ("char" in c["type"] or "text" in c["type"]):
            return c
    for c in cols:
        if ("名称" in c["comment"]) and ("char" in c["type"] or "text" in c["type"]):
            return c
    for c in cols:
        if ("char" in c["type"] or "text" in c["type"]) and c["name"] not in tbl["pk"]:
            return c
    return None


def module_tables():
    """给侧边栏用：模块 -> 表列表（含行数）"""
    tables = load_meta()
    out = []
    for m in MODULES:
        items = [tables[t] for t in m["tables"] if t in tables]
        if items:
            out.append({**m, "items": items})
    return out


# ---------------------------------------------------------------- 字段类型推断
def enum_options(col):
    """从列注释里推断可选值，如 '订单状态：未发货/在途/到港/签收' -> 列表

    「、」是显式清单分隔符，优先级高于「/」：因为值本身可能带斜杠，
    像网点类型 '销售、售后、充电、销售/售后、销售/充电'，用 / 分就全乱了。
    """
    cm = (col.get("comment") or "").strip()
    if not cm:
        return None
    tail = cm
    for sep in ("：", ":"):
        if sep in cm:
            tail = cm.split(sep)[-1].strip()
            break
    # 「是否召回Y/N」这种没有冒号的写法，要先识别出 Y/N，否则会被按 / 拆成
    # ['是否召回Y', 'N']，选第一项就超过 char(1) 的长度限制
    norm = tail.upper().replace(" ", "").rstrip("。")
    if norm.endswith("Y/N"):
        return ["Y", "N"]

    max_len = col.get("max_len")

    def _check(cand):
        if not (2 <= len(cand) <= 8 and all(1 <= len(o) <= 14 for o in cand)):
            return None
        # 防御：任何一个选项超出字段定义长度，说明注释不是枚举清单，退回普通文本框
        if max_len and any(len(o) > max_len for o in cand):
            return None
        return cand

    if "、" in tail and len(tail) <= 60:
        cand = _check([x.strip("。 ") for x in tail.split("、") if x.strip("。 ")])
        if cand:
            return cand
    if "/" in tail and len(tail) <= 40:
        cand = _check([x.strip("。 ") for x in tail.split("/") if x.strip("。 ")])
        if cand:
            return cand
    return None


def field_kind(col):
    t = col["type"]
    if col.get("fk"):
        return "fk"
    if enum_options(col):
        return "enum"
    if t == "date":
        return "date"
    if t in ("datetime", "timestamp"):
        return "datetime"
    if t in ("int", "smallint", "mediumint", "bigint"):
        return "int"
    if t in ("tinyint",):
        return "bool"
    if t in ("decimal", "double", "float"):
        return "decimal"
    if t in ("text", "mediumtext", "longtext", "tinytext"):
        return "textarea"
    if col["max_len"] and col["max_len"] > 100:
        return "textarea"
    return "text"


# ---------------------------------------------------------------- 通用查询构造
TEXT_TYPES = ("char", "varchar", "text", "tinytext", "mediumtext", "longtext", "enum")


def is_text(col):
    return any(k in col["type"] for k in TEXT_TYPES)


def missing_join(tbl, child_name):
    """「主表中没有对应子表记录」的 NOT EXISTS 条件。

    例如 exportorder + customs → 尚未报关的订单。只有在子表恰好有一个外键指回
    本表时才成立，否则条件有歧义，直接返回 None 不猜。
    """
    child = get_table(child_name)
    if not child:
        return None
    fks = [f for f in child["fks"] if f["ref_table"] == tbl["name"]]
    if len(fks) != 1:
        return None
    fk = fks[0]
    return ("NOT EXISTS (SELECT 1 FROM `%s` mc WHERE mc.`%s` = t.`%s`)"
            % (child_name, fk["col"], fk["ref_col"]))


def list_rows(tbl, page=1, size=20, keyword="", order_by=None, direction="desc",
              filters=None, missing=None):
    """通用分页查询：主表 + 外键 LEFT JOIN 取显示名

    filters 的取值支持三种写法，和筛选栏、首页待办卡片共用同一套语义：
      '在途'        等值
      '在途,到港'   多值 IN —— 枚举类「在途/到港」这种合起来的待办用得上
      '!签收'       不等值 —— 「未签收」这类否定条件
    missing 传子表名，表示只看没有对应子表记录的行（如尚未报关的订单）。
    """
    col_names = {c["name"] for c in tbl["columns"]}

    select = ["t.`%s` AS `%s`" % (c["name"], c["name"]) for c in tbl["columns"]]
    joins, labels, label_search = [], [], []
    for i, fk in enumerate(tbl["fks"]):
        ref = get_table(fk["ref_table"])
        disp = display_column(ref)
        if not disp or disp["name"] == fk["col"]:
            continue
        alias = "r%d" % i
        joins.append("LEFT JOIN `%s` %s ON t.`%s` = %s.`%s`"
                     % (fk["ref_table"], alias, fk["col"], alias, fk["ref_col"]))
        select.append("%s.`%s` AS `%s__label`" % (alias, disp["name"], fk["col"]))
        labels.append({"col": fk["col"], "ref": fk["ref_table"], "field": disp["name"]})
        label_search.append("%s.`%s`" % (alias, disp["name"]))

    where, params = [], []
    if keyword:
        # 同时匹配本表文本字段与外键关联表的名称字段（如用"泰国"搜订单）
        text_cols = [c["name"] for c in tbl["columns"] if is_text(c)]
        parts = ["t.`%s` LIKE %%s" % c for c in text_cols] + ["%s LIKE %%s" % c for c in label_search]
        if parts:
            where.append("(" + " OR ".join(parts) + ")")
            params += ["%%%s%%" % keyword] * len(parts)
    for col, val in (filters or {}).items():
        if col not in col_names or val in (None, ""):
            continue
        sval = str(val).strip()
        if sval.startswith("!") and len(sval) > 1:
            # NULL 不参与 <> 比较：状态为空的记录既不算「签收」也不会命中「未签收」，
            # 待办卡片和列表就会对不上。取反必须把 NULL 一起算进去。
            where.append("(t.`%s` <> %%s OR t.`%s` IS NULL)" % (col, col))
            params.append(sval[1:].strip())
        elif "," in sval:
            vals = [v.strip() for v in sval.split(",") if v.strip()]
            if not vals:
                continue
            where.append("t.`%s` IN (%s)" % (col, ", ".join(["%s"] * len(vals))))
            params += vals
        else:
            where.append("t.`%s` = %%s" % col)
            params.append(val)
    if missing:
        cond = missing_join(tbl, missing)
        if cond:
            where.append(cond)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    order_map = {c: "t.`%s`" % c for c in col_names}
    for lb in labels:
        order_map[lb["col"] + "__label"] = "`%s__label`" % lb["col"]
    if order_by in order_map:
        order_sql = "ORDER BY %s %s" % (order_map[order_by], "ASC" if direction == "asc" else "DESC")
    elif tbl["pk"]:
        order_sql = "ORDER BY " + ", ".join("t.`%s` ASC" % k for k in tbl["pk"])
    else:
        order_sql = "ORDER BY 1 ASC"

    total = q1("SELECT COUNT(*) AS n FROM `%s` t %s %s"
               % (tbl["name"], " ".join(joins), where_sql), params)["n"]

    rows = q("SELECT %s FROM `%s` t %s %s %s LIMIT %%s OFFSET %%s"
             % (", ".join(select), tbl["name"], " ".join(joins), where_sql, order_sql),
             params + [size, (page - 1) * size])
    return {"rows": rows, "total": int(total), "labels": labels}


def lookup_items(table_name, keyword="", limit=500):
    """外键下拉的候选清单。keyword 同时匹配主键与名称，供前端输入即筛选用。"""
    tbl = get_table(table_name)
    if not tbl:
        return []
    disp = display_column(tbl)
    key = tbl["pk"][0] if tbl["pk"] else tbl["columns"][0]["name"]
    sel = ["`%s` AS v" % key]
    if disp and disp["name"] != key:
        sel.append("`%s` AS l" % disp["name"])
    sql = "SELECT %s FROM `%s`" % (", ".join(sel), table_name)
    params = []
    if keyword and disp:
        sql += " WHERE `%s` LIKE %%s OR `%s` LIKE %%s" % (key, disp["name"])
        params = ["%%%s%%" % keyword] * 2
    elif keyword:
        sql += " WHERE `%s` LIKE %%s" % key
        params = ["%%%s%%" % keyword]
    sql += " ORDER BY 1 LIMIT %s"
    out = []
    for r in q(sql, params + [limit]):
        out.append({"v": r["v"], "l": r.get("l") or str(r["v"])})
    from collections import Counter
    dup = Counter(o["l"] for o in out)
    for o in out:
        if dup[o["l"]] > 1 and str(o["l"]) != str(o["v"]):
            o["l"] = "%s（%s）" % (o["l"], o["v"])
    return out


def label_of(table_name, value):
    """按主键取某条记录的人话名字，取不到就退回主键值本身"""
    if value in (None, ""):
        return ""
    tbl = get_table(table_name)
    if not tbl:
        return str(value)
    disp = display_column(tbl)
    key = tbl["pk"][0] if tbl["pk"] else tbl["columns"][0]["name"]
    if not disp or disp["name"] == key:
        return str(value)
    sql = "SELECT `%s` AS l FROM `%s` WHERE `%s`=%%s LIMIT 1" % (disp["name"], table_name, key)
    row = q1(sql, (value,))
    if row and row["l"] not in (None, ""):
        return str(row["l"])
    return str(value)

def module_of_table(name):
    """表所属的模块（用于面包屑与侧栏定位）"""
    for m in MODULES:
        if name in m["tables"]:
            return m
    return None


def module_title(name):
    m = module_of_table(name)
    return m["title"] if m else "其他数据表"

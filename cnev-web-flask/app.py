# -*- coding: utf-8 -*-
"""中国新能源汽车出口贸易数据管理系统 —— Flask 应用入口

技术栈：HTML + CSS + Flask + MySQL
页面全部由 Jinja2 服务端渲染，图表用纯 CSS / SVG 绘制，不依赖任何前端框架。
"""
import math
import time
import traceback

import pymysql
from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)

import db
from config import (COURSE_NAME, GROUP_NAME, SECRET_KEY, SERVER_HOST,
                    SERVER_PORT, SYSTEM_NAME, SYSTEM_SHORT)
from stats import PRESET_SQL, STATS, kpi_summary, prepare_chart

app = Flask(__name__)
# 密钥从环境变量 / 本地 secrets_local.py 取，源码里不留明文
app.secret_key = SECRET_KEY
app.teardown_appcontext(db.close_conn)


# ------------------------------------------------------------------ 通用工具
@app.template_filter("num")
def fmt_num(v):
    if v is None or v == "":
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    if isinstance(v, int) and abs(v) < 10000:
        return str(v)          # 年份、数量等小整数不加千分位
    if abs(f - round(f)) < 1e-9:
        return "{:,.0f}".format(f)
    return "{:,.2f}".format(f)


@app.template_filter("money")
def fmt_money(v):
    try:
        return "{:,.2f}".format(float(v))
    except (TypeError, ValueError):
        return "—"


@app.template_filter("val")
def fmt_val(v):
    if v is None or v == "":
        return "—"
    return v


@app.context_processor
def inject_globals():
    from decimal import Decimal

    def is_num(v):
        return isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)

    return {
        "NAV": db.module_tables(),
        "is_num": is_num,
        "SYS_NAME": SYSTEM_NAME,
        "SYS_SHORT": SYSTEM_SHORT,
        "GROUP_NAME": GROUP_NAME,
        "COURSE_NAME": COURSE_NAME,
        "CURRENT_TABLE": request.view_args.get("table") if request.view_args else None,
        "q": request.args.get("q", ""),
    }


@app.template_global()
def url_with(_path=None, **kwargs):
    """在保留当前查询串（搜索/筛选/排序/页码）的基础上改几个参数

    传 None 表示「把这个参数删掉」——排序、导出都要靠它清掉旧页码，
    否则在第 2 页点排序会带着 page=2 跳过去，结果集变短后停在空页。
    """
    from urllib.parse import urlencode
    args = request.args.to_dict()
    for k, v in kwargs.items():
        if v is None:
            args.pop(k, None)
        else:
            args[k] = v
    args = {k: v for k, v in args.items() if v not in ("", None)}
    path = _path or request.path
    return path + ("?" + urlencode(args) if args else "")


def filter_value_label(raw):
    """把一个筛选值翻成人话，用于下拉里补出来的选项（如 在途,到港 → 在途 / 到港）"""
    raw = str(raw or "").strip()
    if raw.startswith("!"):
        return "≠ " + raw[1:].strip()
    if "," in raw:
        return " / ".join(x.strip() for x in raw.split(",") if x.strip())
    return raw


def table_or_404(name):
    tbl = db.get_table(name)
    if not tbl:
        abort(404)
    return tbl


def pk_from_args(tbl):
    keys = {}
    for k in tbl["pk"]:
        v = request.args.get("pk_" + k)
        if v is None:
            v = request.form.get("pk_" + k)
        keys[k] = v
    return keys


# ------------------------------------------------------------------ 首页
# 待办卡片的「数字」和「点进去的列表」必须来自同一份条件，否则两处会各说各话。
# table+条件只写一份，计数与链接都由它推导。
TODO_CARDS = [
    {"tone": "blue", "table": "exportorder",
     "filters": {"OrderStatus": "在途,到港"},
     "text": "在途 / 到港订单，待跟进"},
    {"tone": "warn", "table": "exportorder",
     "missing": "customs",
     "text": "笔订单尚未报关"},
    {"tone": "teal", "table": "waybill",
     "filters": {"WaybillStatus": "!签收"},
     "text": "张运单未签收"},
]


def build_todo():
    """按 TODO_CARDS 生成待办卡片：先算数，再生成用同一条件筛选的链接"""
    out = []
    for spec in TODO_CARDS:
        tbl = db.get_table(spec["table"])
        if not tbl:
            continue
        filters = spec.get("filters") or {}
        missing = spec.get("missing")
        total = db.list_rows(tbl, page=1, size=1, filters=filters,
                             missing=missing)["total"]
        args = {"table": spec["table"]}
        for col, val in filters.items():
            args["f_" + col] = val
        if missing:
            args["missing"] = missing
        out.append({"tone": spec["tone"], "count": total, "text": spec["text"],
                    "url": url_for("table_list", **args)})
    return out


@app.route("/")
def dashboard():
    kpi = kpi_summary()
    charts = {}
    for s in STATS:
        if s["key"] in ("trend", "countryRank", "beltRoad"):
            try:
                rows = db.q(s["sql"])
                charts[s["key"]] = {**s, "rows": rows, "chart_data": prepare_chart(s, rows), "ok": True}
            except Exception as e:
                charts[s["key"]] = {**s, "rows": [], "chart_data": None, "ok": False, "error": str(e)}

    # 库中若只有一个年度，折线图只有孤立一点：改为按月展开
    if charts.get("trend", {}).get("ok") and len(charts["trend"]["rows"]) < 2:
        m = next((x for x in STATS if x["key"] == "monthly"), None)
        if m:
            mrows = db.q(m["sql"])
            if mrows:
                charts["trend"]["chart_data"] = prepare_chart(m, mrows)
                charts["trend"]["note"] = "库中仅 %d 个年度，趋势按月份展开" % len(charts["trend"]["rows"])

    recent = db.q("""
        SELECT o.OrderNo, e.EntName, c.CountryName, o.OrderDate,
               o.ContractAmount, o.CurrencyCode, o.OrderStatus
          FROM exportorder o
          LEFT JOIN autoenterprise e ON e.EntID = o.EntID
          LEFT JOIN country c ON c.CountryCode = o.CountryCode
         ORDER BY o.OrderDate DESC, o.OrderNo DESC LIMIT 6""")

    # 提醒列表必须和卡片上的数字同窗口（180 天），否则同一页面两个口径，一问就露
    warn = db.q("""
        SELECT m.ModelName, ct.CertName, mc.ExpireDate, DATEDIFF(mc.ExpireDate, CURDATE()) AS days
          FROM modelcert mc
          JOIN exportmodel m ON m.ModelID = mc.ModelID
          JOIN certification ct ON ct.CertID = mc.CertID
         WHERE mc.ExpireDate IS NOT NULL AND mc.ExpireDate <= DATE_ADD(CURDATE(), INTERVAL 180 DAY)
         ORDER BY mc.ExpireDate LIMIT 5""")

    # 待办与异常：业务主管每天上班先看这几个数
    todo = build_todo()
    todo.append({"tone": "gray", "count": int(kpi.get("expiring") or 0),
                 "text": "个车型认证已过期或临期（180 天内）",
                 "url": url_for("stats_page", only="certWarn")})

    total_tables = sum(len(m["items"]) for m in db.module_tables())

    return render_template("dashboard.html", page="dashboard", kpi=kpi,
                           charts=charts, recent=recent, warn=warn,
                           total_tables=total_tables, todo=todo)


# ------------------------------------------------------------------ 数据列表
@app.route("/t/<table>")
def table_list(table):
    tbl = table_or_404(table)
    page = max(1, int(request.args.get("page", 1) or 1))
    size = min(200, max(5, int(request.args.get("size", 20) or 20)))
    keyword = (request.args.get("q") or "").strip()
    order_by = request.args.get("sort") or None
    direction = "asc" if request.args.get("dir") == "asc" else "desc"

    filters = {c["name"]: request.args.get("f_" + c["name"]) for c in tbl["columns"]
               if request.args.get("f_" + c["name"])}
    # 「尚未报关」这类必须用反连接表达，不能靠某一个字段的等值筛选
    missing = (request.args.get("missing") or "").strip() or None
    if missing and not db.missing_join(tbl, missing):
        missing = None

    data = db.list_rows(tbl, page=page, size=size, keyword=keyword,
                        order_by=order_by, direction=direction,
                        filters=filters, missing=missing)
    pages = max(1, math.ceil(data["total"] / size))

    # 筛选控件：外键列 + 注释里带枚举值的列，最多 6 个（避免工具栏过挤）
    filter_fields = []
    for col in tbl["columns"]:
        if col["name"] in tbl["pk"]:
            continue
        kind = db.field_kind(col)
        if kind == "fk":
            filter_fields.append({
                "name": col["name"],
                "label": col.get("short") or col["comment"] or col["name"],
                "options": db.lookup_items(col["fk"]["table"]),
                "value": filters.get(col["name"], ""),
            })
        elif kind == "enum":
            raw = filters.get(col["name"], "")
            options = [{"v": o, "l": o} for o in (db.enum_options(col) or [])]
            # 多值 / 取反的筛选值不在选项清单里，补一个能看懂的选项，别让下拉显示成「全部」
            if raw and raw not in [o["v"] for o in options]:
                options.insert(0, {"v": raw, "l": filter_value_label(raw)})
            filter_fields.append({
                "name": col["name"],
                "label": col.get("short") or col["comment"] or col["name"],
                "options": options,
                "value": raw,
            })
        if len(filter_fields) >= 6:
            break

    missing_label = None
    if missing:
        child = db.get_table(missing)
        if child:
            missing_label = "只看没有「%s」记录的" % child["label"]

    # 外键列显示名映射，供表格展示 "代码（名称）"
    return render_template("table.html", page="table", tbl=tbl, data=data,
                           pages=pages, page_no=page, size=size, keyword=keyword,
                           sort=order_by or "", dir=direction,
                           module_title=db.module_title(tbl["name"]),
                           filter_fields=filter_fields, filters=filters,
                           missing=missing or "", missing_label=missing_label)


# ------------------------------------------------------------------ 新增 / 编辑表单
def build_fields(tbl, row=None, mode="new"):
    """把表结构翻译成表单控件描述，字段顺序与库中一致"""
    fields = []
    for col in tbl["columns"]:
        if col["auto"] and mode == "new":
            continue
        kind = db.field_kind(col)
        f = {
            "col": col, "name": col["name"], "kind": kind,
            "label": col.get("short") or col["comment"] or col["name"],
            "required": (not col["nullable"]) and not col["auto"] and col["default"] is None,
            "readonly": (col["name"] in tbl["pk"] and mode == "edit"),
            "placeholder": col["column_type"],
            "hint": "",
        }
        if kind == "fk":
            fk = col["fk"]
            ref = db.get_table(fk["table"])
            f["options"] = db.lookup_items(fk["table"])
            f["fk_table"] = fk["table"]
            f["ref_label"] = ref["label"] if ref else fk["table"]
            f["total"] = (ref or {}).get("row_count") or len(f["options"])
            f["hint"] = "外键 → %s.%s · 支持输入关键字筛选" % (fk["table"], fk["col"])
        elif kind == "enum":
            f["options"] = db.enum_options(col)
            f["hint"] = "可选：" + " / ".join(f["options"])
        elif kind == "textarea":
            f["hint"] = "最长 %s 字符" % (col["max_len"] or "不限")
        elif kind == "date":
            f["hint"] = "格式 2026-10-30（年-月-日）"
        elif kind in ("int", "decimal"):
            f["hint"] = col["column_type"]
        else:
            f["hint"] = "" if not col["max_len"] else "最长 %s 字符" % col["max_len"]

        if mode == "new":
            f["value"] = "" if col["default"] is None or str(col["default"]).upper() == "NULL" else col["default"]
        else:
            f["value"] = row.get(col["name"]) if row else ""
            if f["value"] is None:
                f["value"] = ""
        if kind == "fk":
            f["selected_label"] = db.label_of(f["fk_table"], f["value"]) if f["value"] != "" else ""
        elif kind == "enum" and f["value"] not in ("", None):
            # 兜底：库里已有的值若不在推荐清单里（历史数据、注释过时），必须原样保留。
            # 否则下拉一个都命中不了，用户点保存就把这一列写成 NULL 了。
            cur = str(f["value"])
            if cur not in f["options"]:
                f["options"] = list(f["options"]) + [cur]
                f["hint"] += " · 当前值「%s」不在推荐清单内，已原样保留" % cur
        fields.append(f)
    return fields


def _form_next_url(tbl):
    """表单页记住来源列表，保存后原样返回，避免"改完找不到刚才那条" """
    from urllib.parse import urlsplit
    ref = request.referrer or ""
    if not ref:
        return ""
    parts = urlsplit(ref)
    if parts.path == "/t/" + tbl["name"]:
        return parts.path + ("?" + parts.query if parts.query else "")
    return ""


def _back_to_list(tbl, keys=None):
    nxt = request.form.get("next") or request.args.get("next")
    if nxt and nxt.startswith("/t/" + tbl["name"]) and "//" not in nxt:
        return redirect(nxt)
    if keys:
        first = next((keys.get(k) for k in tbl["pk"] if keys.get(k)), None)
        if first:
            # 兜底：用主键值搜一下，保证用户能看到刚保存的那条
            return redirect(url_for("table_list", table=tbl["name"], q=str(first)))
    return redirect(url_for("table_list", table=tbl["name"]))


@app.route("/api/lookup/<table>")
def api_lookup(table):
    """外键下拉的远程候选：输入什么就筛什么，不受首屏 limit 影响"""
    tbl = db.load_meta().get(table)
    if not tbl:
        return jsonify({"ok": False, "items": [], "msg": "未知数据表：%s" % table}), 404
    kw = (request.args.get("q") or "").strip()
    items = db.lookup_items(table, kw, limit=60)
    return jsonify({"ok": True, "table": table, "label": tbl["label"],
                    "total": tbl.get("row_count", len(items)), "items": items})


@app.route("/t/<table>/new", methods=["GET", "POST"])
def table_new(table):
    tbl = table_or_404(table)
    # embed=1：在外键「＋ 新增」的浮层 iframe 里打开，成功后不跳列表页
    embed = request.args.get("embed") == "1"
    if request.method == "POST":
        try:
            values = {}
            for col in tbl["columns"]:
                if col["auto"]:
                    continue
                raw = request.form.get(col["name"], "")
                if raw == "":
                    values[col["name"]] = None
                else:
                    values[col["name"]] = raw
            cols = list(values.keys())
            sql = "INSERT INTO `%s` (%s) VALUES (%s)" % (
                tbl["name"], ", ".join("`%s`" % c for c in cols),
                ", ".join(["%s"] * len(cols)))
            new_id = db.insert(sql, [values[c] for c in cols])
            if embed:
                first = next((values.get(k) for k in tbl["pk"] if values.get(k)), None)
                if first is None and new_id:
                    first = new_id
                return render_template("embed_done.html", tbl=tbl,
                                       value="" if first is None else str(first),
                                       label=db.label_of(table, first))
            flash("已新增 1 条「%s」记录" % tbl["label"], "ok")
            return _back_to_list(tbl, {c: values.get(c) for c in tbl["pk"]})
        except pymysql.err.MySQLError as e:
            flash("新增失败：" + _friendly_db_error(e), "err")
        except Exception as e:
            flash("新增失败：" + str(e), "err")

    return render_template("form.html", page="table", tbl=tbl, mode="new",
                           fields=build_fields(tbl, mode="new"), row=None,
                           module_title=db.module_title(tbl["name"]),
                           embed=embed, next_url=_form_next_url(tbl))


@app.route("/t/<table>/edit", methods=["GET", "POST"])
def table_edit(table):
    tbl = table_or_404(table)
    keys = pk_from_args(tbl)
    if not tbl["pk"]:
        flash("该表没有主键，无法编辑", "err")
        return redirect(url_for("table_list", table=table))

    where = " AND ".join("`%s` = %%s" % k for k in tbl["pk"])
    row = db.q1("SELECT * FROM `%s` WHERE %s" % (tbl["name"], where),
                [keys[k] for k in tbl["pk"]])
    if not row:
        flash("记录不存在", "err")
        return redirect(url_for("table_list", table=table))

    if request.method == "POST":
        try:
            values, cols = {}, []
            for col in tbl["columns"]:
                if col["auto"] or col["name"] in tbl["pk"]:
                    continue
                raw = request.form.get(col["name"], "")
                values[col["name"]] = None if raw == "" else raw
                cols.append(col["name"])
            sql = "UPDATE `%s` SET %s WHERE %s" % (
                tbl["name"], ", ".join("`%s` = %%s" % c for c in cols), where)
            db.execute(sql, [values[c] for c in cols] + [keys[k] for k in tbl["pk"]])
            flash("已保存「%s」的修改" % tbl["label"], "ok")
            return _back_to_list(tbl, keys)
        except pymysql.err.MySQLError as e:
            flash("保存失败：" + _friendly_db_error(e), "err")
        except Exception as e:
            flash("保存失败：" + str(e), "err")

    return render_template("form.html", page="table", tbl=tbl, mode="edit",
                           fields=build_fields(tbl, row, "edit"), row=row, keys=keys,
                           module_title=db.module_title(tbl["name"]),
                           embed=False, next_url=_form_next_url(tbl))


@app.route("/t/<table>/delete", methods=["POST"])
def table_delete(table):
    tbl = table_or_404(table)
    keys = pk_from_args(tbl)
    if not tbl["pk"]:
        flash("该表没有主键，无法删除", "err")
        return redirect(url_for("table_list", table=table))
    try:
        n = db.execute("DELETE FROM `%s` WHERE %s" % (
            tbl["name"], " AND ".join("`%s` = %%s" % k for k in tbl["pk"])),
            [keys[k] for k in tbl["pk"]])
        flash("已删除 %d 条记录" % n, "ok")
    except pymysql.err.MySQLError as e:
        flash("删除失败：" + _friendly_db_error(e), "err")
    return redirect(url_for("table_list", table=table, page=request.args.get("page", 1)))


@app.route("/t/<table>/export")
def table_export(table):
    """把当前筛选结果导出为 CSV（UTF-8 BOM，Excel 直接打开不乱码）"""
    import csv
    import io

    tbl = table_or_404(table)
    keyword = (request.args.get("q") or "").strip()
    order_by = request.args.get("sort") or None
    direction = "asc" if request.args.get("dir") == "asc" else "desc"
    filters = {c["name"]: request.args.get("f_" + c["name"]) for c in tbl["columns"]
               if request.args.get("f_" + c["name"])}
    missing = (request.args.get("missing") or "").strip() or None
    if missing and not db.missing_join(tbl, missing):
        missing = None
    data = db.list_rows(tbl, page=1, size=5000, keyword=keyword,
                        order_by=order_by, direction=direction,
                        filters=filters, missing=missing)

    buf = io.StringIO()
    writer = csv.writer(buf)
    header = [c["short"] or c["name"] for c in tbl["columns"]]
    writer.writerow(header)
    for row in data["rows"]:
        line = []
        for c in tbl["columns"]:
            v = row.get(c["name"])
            label = row.get(c["name"] + "__label")
            if v is None:
                line.append("")
            elif label:
                line.append("%s (%s)" % (label, v))
            else:
                line.append(str(v))
        writer.writerow(line)

    from flask import Response
    csv_bytes = "\ufeff" + buf.getvalue()
    filename = "%s_%s.csv" % (tbl["name"], time.strftime("%Y%m%d_%H%M"))
    return Response(csv_bytes, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=%s" % filename})


def _friendly_db_error(e):
    """把 MySQL 约束报错翻译成看得懂的话"""
    code = e.args[0] if e.args else 0
    msg = e.args[1] if len(e.args) > 1 else str(e)
    mapping = {
        1062: "主键或唯一约束冲突（该编号已存在）",
        1451: "存在引用该记录的子表数据，不能删除（外键约束 RESTRICT）",
        1452: "外键约束失败：引用的记录不存在",
        1048: "必填字段不能为空",
        1264: "数值超出字段取值范围",
        1406: "字符串长度超出字段定义",
        1292: "日期或数值格式不正确",
    }
    return mapping.get(code, msg)


# ------------------------------------------------------------------ 订单全景（履约链路）
@app.route("/order/<order_no>")
def order_detail(order_no):
    """跟单员的一屏工作台：订单 + 明细 + 运单 + 报关 + 合规提示"""
    head = db.q1("""
        SELECT o.*, e.EntName, e.Brand, e.Province,
               c.CountryName, c.Continent, c.IsBeltRoad,
               d.DealerName, d.DealerType, d.CreditLevel,
               cu.CurrencyName,
               (SELECT er.RateToCNY FROM exchangerate er
                 WHERE er.CurrencyCode = o.CurrencyCode
                 ORDER BY er.YearMonth DESC LIMIT 1) AS rate
          FROM exportorder o
          LEFT JOIN autoenterprise e ON e.EntID = o.EntID
          LEFT JOIN country c        ON c.CountryCode = o.CountryCode
          LEFT JOIN dealer d         ON d.DealerID = o.DealerID
          LEFT JOIN currency cu      ON cu.CurrencyCode = o.CurrencyCode
         WHERE o.OrderNo = %s""", (order_no,))
    if not head:
        abort(404)

    lines = db.q("""
        SELECT od.*, m.ModelName, m.VehicleType, m.RangeKm, m.BatteryType, m.ModelStatus
          FROM orderdetail od
          LEFT JOIN exportmodel m ON m.ModelID = od.ModelID
         WHERE od.OrderNo = %s
         ORDER BY od.ModelID""", (order_no,))

    waybills = db.q("""
        SELECT w.*, cr.CarrierName, cr.TransportMode, cr.CreditLevel AS CarrierCredit,
               DATEDIFF(w.ActualArriveDate, w.ETA)  AS eta_diff,
               DATEDIFF(w.ActualArriveDate, w.ETD)  AS transit_days
          FROM waybill w
          LEFT JOIN carrier cr ON cr.CarrierID = w.CarrierID
         WHERE w.OrderNo = %s
         ORDER BY w.ETD""", (order_no,))

    customs = db.q1("""
        SELECT cu.* FROM customs cu WHERE cu.OrderNo = %s""", (order_no,))

    # 这笔订单涉及的车型，是否有认证即将到期（合规提醒）
    # 认证是按国家发布的（certification.CountryCode = 制定国家），必须只认目的国的那几张：
    # 发往科威特的单子拿泰国的认证来提醒，等于给错合规结论。
    certs = db.q("""
        SELECT m.ModelName, ct.CertName, ct.CountryCode AS CertCountry, mc.ExpireDate,
               DATEDIFF(mc.ExpireDate, CURDATE()) AS days
          FROM orderdetail od
          JOIN modelcert mc      ON mc.ModelID = od.ModelID
          JOIN exportmodel m     ON m.ModelID = od.ModelID
          JOIN certification ct  ON ct.CertID = mc.CertID
         WHERE od.OrderNo = %s AND ct.CountryCode = %s
           AND mc.ExpireDate IS NOT NULL
           AND mc.ExpireDate <= DATE_ADD(CURDATE(), INTERVAL 180 DAY)
         ORDER BY mc.ExpireDate""", (order_no, head["CountryCode"]))

    # 本目的国到底有没有认证记录（有但都不临期 / 一张都没有，是两种不同的合规风险）
    dest_cert_total = int(db.q1("""
        SELECT COUNT(*) AS n
          FROM orderdetail od
          JOIN modelcert mc     ON mc.ModelID = od.ModelID
          JOIN certification ct ON ct.CertID = mc.CertID
         WHERE od.OrderNo = %s AND ct.CountryCode = %s""",
        (order_no, head["CountryCode"]))["n"])

    total_qty = sum((l["Quantity"] or 0) for l in lines)
    total_amt = sum(float(l["Amount"] or 0) for l in lines)
    rate = float(head["rate"]) if head.get("rate") else None
    amount_cny = round(float(head["ContractAmount"] or 0) * rate, 2) if rate else None

    # 时效比对：优先取「已实际到港」的那张运单，没有就退回第一张
    eta_tag = None
    arrived = next((w for w in waybills if w.get("ActualArriveDate")), None)
    ref = arrived or (waybills[0] if waybills else None)
    if ref:
        d = ref.get("eta_diff")
        if d is None:
            eta_tag = {"level": "wait", "text": "尚未到港，暂无法比对时效"}
        elif d > 0:
            eta_tag = {"level": "err", "text": "延迟 %d 天到港" % d}
        elif d < 0:
            eta_tag = {"level": "ok", "text": "提前 %d 天到港" % -d}
        else:
            eta_tag = {"level": "ok", "text": "准点到港"}

    # 履约进度：用订单状态 + 运单日期还原四个阶段
    # 严格按"已推进到的环节"给日期：预计到港（ETA）不等于实际到港，不能拿来充数；
    # 运单表没有签收日期字段，签收环节不臆造日期，模板显示为「—」。
    steps = ["未发货", "在途", "到港", "签收"]
    status = head.get("OrderStatus") or "未发货"
    cur_step = steps.index(status) if status in steps else 0
    wb = waybills[0] if waybills else {}
    step_dates = [
        head.get("OrderDate"),
        wb.get("ETD") if cur_step >= 1 else None,
        wb.get("ActualArriveDate") if cur_step >= 2 else None,
        None,
    ]

    return render_template("order.html", page="table", o=head, lines=lines,
                           waybills=waybills, customs=customs, certs=certs,
                           dest_cert_total=dest_cert_total,
                           total_qty=total_qty, total_amt=total_amt,
                           rate=rate, amount_cny=amount_cny,
                           steps=steps, cur_step=cur_step, step_dates=step_dates,
                           eta_tag=eta_tag)


# ------------------------------------------------------------------ 统计分析
@app.route("/stats")
def stats_page():
    only = request.args.get("only")
    blocks = []
    for s in STATS:
        if only and s["key"] != only:
            continue
        t0 = time.time()
        try:
            rows = db.q(s["sql"])
            elapsed = round((time.time() - t0) * 1000, 1)
            blocks.append({**s, "rows": rows, "columns": list(rows[0].keys()) if rows else [],
                           "chart_data": prepare_chart(s, rows), "ok": True, "ms": elapsed})
        except Exception as e:
            blocks.append({**s, "rows": [], "columns": [], "chart_data": None,
                           "ok": False, "error": str(e), "ms": 0})
    # 趋势块：只有一个年度时折线只有孤立一点，改为说明块，月度图交给下方专属卡片
    for b in blocks:
        if b["key"] == "trend" and b["ok"] and len(b["rows"]) < 2:
            years = "、".join(str(r.get("年份")) for r in b["rows"])
            b["chart_data"] = {
                "type": "note",
                "text": "当前库中仅有 %s 年度数据，按年折线只有孤立一点，"
                        "无法体现趋势。请查看下方「月度出口节奏」观察年内分布。" % (years or "一个")
            }
            b["chart_note"] = "仅 1 个年度，折线退化为单点" 

    # 「没有数据的功能先不写」：全 0 或查询为空的统计块默认隐藏，可用 ?show_empty=1 查看
    show_empty = request.args.get("show_empty") == "1"
    hidden = []
    if not show_empty:
        visible = []
        for b in blocks:
            cd = b.get("chart_data") or {}
            empty = (not b["ok"]) or (not b["rows"]) or cd.get("all_zero") or len(b["rows"]) == 0
            if empty:
                hidden.append(b["title"])
            else:
                visible.append(b)
        blocks = visible

    return render_template("stats.html", page="stats", blocks=blocks, kpi=kpi_summary(),
                           only=only, hidden=hidden, show_empty=show_empty)


# ------------------------------------------------------------------ SQL 演示台
def _strip_sql(sql):
    """去掉注释与字符串字面量，避免用 '/*x*/ delete' 或 'delete' 这类写法绕过关键字判断"""
    out, i, n = [], 0, len(sql)
    while i < n:
        ch = sql[i]
        if ch in ("'", '"', "`"):
            q = ch
            i += 1
            while i < n:
                if sql[i] == "\\":
                    i += 2
                    continue
                if sql[i] == q:
                    if i + 1 < n and sql[i + 1] == q:   # 连写两个引号表示转义
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            out.append(" ")
            continue
        if sql.startswith("--", i) or ch == "#":
            j = sql.find("\n", i)
            i = n if j < 0 else j + 1
            out.append(" ")
            continue
        if sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(" ")
            continue
        out.append(ch)
        i += 1
    return "".join(out)


READONLY_HEADS = ("select", "with", "show", "desc", "describe", "explain", "table")


def _check_sql(sql):
    """按语句类型白名单判断，不能只砍开头几个字符：
    MySQL 8 允许 WITH x AS (...) DELETE FROM t，前缀是 WITH 却是写操作。"""
    import re as _re
    raw = (sql or "").strip().rstrip(";").strip()
    if not raw:
        return "请先输入一条查询语句"
    core = _strip_sql(raw)
    if ";" in core:
        return "一次只能执行一条语句（不要用分号分隔多条）"
    body = core.strip().lstrip("( \t\r\n")
    m = _re.match(r"[A-Za-z]+", body)
    head = (m.group(0) if m else "").lower()
    if head not in READONLY_HEADS:
        return "为了数据安全，演示台只允许只读查询（SELECT / WITH … SELECT / SHOW / EXPLAIN）"
    if head == "with":
        # CTE 之后的主体必须还是 SELECT，出现写操作关键字就拦掉
        for bad in ("insert", "update", "delete", "replace", "merge"):
            if _re.search(r"\b%s\b" % bad, body, _re.I):
                return "WITH 之后只允许接 SELECT，不能接写操作"
    lower = body.lower()
    for bad in ("into outfile", "into dumpfile", "for update", "lock in share mode"):
        if bad in lower:
            return "演示台不允许导出文件或加锁的查询"
    return None


@app.route("/query", methods=["GET", "POST"])
def query_page():
    idx = request.args.get("preset")
    sql = ""
    if idx is not None:
        try:
            sql = PRESET_SQL[int(idx)]["sql"]
        except (ValueError, IndexError):
            sql = ""
    if request.method == "POST":
        sql = request.form.get("sql", "")
        err = _check_sql(sql)
        if err:
            flash(err, "err")
            return render_template("query.html", page="query", sql=sql, presets=PRESET_SQL,
                                   columns=[], rows=[], ms=None, db_error=None)
        try:
            t0 = time.time()
            cols, rows = db.query_raw(sql, limit=300)
            ms = round((time.time() - t0) * 1000, 1)
            return render_template("query.html", page="query", sql=sql, presets=PRESET_SQL,
                                   columns=cols, rows=rows, ms=ms, db_error=None)
        except Exception as e:
            return render_template("query.html", page="query", sql=sql, presets=PRESET_SQL,
                                   columns=[], rows=[], ms=None, db_error=str(e))
    return render_template("query.html", page="query", sql=sql, presets=PRESET_SQL,
                           columns=[], rows=[], ms=None, db_error=None)


# ------------------------------------------------------------------ 数据字典（ER / 关系模式）
@app.route("/dictionary")
def dictionary():
    tables = db.load_meta(force=True)
    total_cols = sum(len(t["columns"]) for t in tables.values())
    total_fk = sum(len(t["fks"]) for t in tables.values())
    return render_template("dictionary.html", page="dictionary",
                           nav_modules=db.module_tables(), tables=tables,
                           total_cols=total_cols, total_fk=total_fk)


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404,
                           msg="页面或数据表不存在"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500,
                           msg="服务器内部错误，请检查数据库连接"), 500


def _preflight():
    """启动前自检数据库连接，把最常见的三类故障翻译成中文，避免对方只看到 Flask 500 页面"""
    cfg = db.DB_CONFIG
    if not cfg.get("password"):
        print("\n[失败] 没有拿到数据库口令。源码里不再写死口令，请二选一：")
        print("       1) 设环境变量：set DB_PASSWORD=你的MySQL口令")
        print("       2) 把 secrets_local.example.py 复制成 secrets_local.py，填上 DB_PASSWORD")
        print("       当前的取用顺序：环境变量 DB_PASSWORD → secrets_local.py\n")
        return False
    try:
        conn = pymysql.connect(**cfg)
        conn.ping(reconnect=False)
        conn.close()
        return True
    except pymysql.err.OperationalError as e:
        code = e.args[0] if e.args else 0
        tips = {
            1045: "账号或口令不对，请检查环境变量 DB_PASSWORD 或 secrets_local.py",
            2003: "数据库服务没启动，或 host/port 填错",
            1049: "数据库不存在，请先导入 sql/cnev_export_trade_db.sql",
        }
        reason = tips.get(code) or (e.args[1] if len(e.args) > 1 else str(e))
        print("\n[失败] 连不上数据库（错误码 %s）" % code)
        print("       目标：%s@%s:%s/%s" % (cfg["user"], cfg["host"], cfg["port"], cfg["database"]))
        print("       原因：%s" % reason)
        print("       改完环境变量或 secrets_local.py 后重新运行即可。\n")
        return False
    except Exception as e:
        print("\n[失败] 数据库连接异常：%s\n" % e)
        return False


if __name__ == "__main__":
    print("=" * 68)
    print(" %s" % SYSTEM_NAME)
    print(" 数据库：%s@%s:%s/%s" % (db.DB_CONFIG["user"], db.DB_CONFIG["host"],
                                 db.DB_CONFIG["port"], db.DB_CONFIG["database"]))
    print(" 访问：http://%s:%s" % (SERVER_HOST, SERVER_PORT))
    print("=" * 68)
    if not _preflight():
        raise SystemExit(1)
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=True, use_reloader=False)

# -*- coding: utf-8 -*-
"""统计分析：全部为真实的跨表 SQL（连接 / 分组聚合 / 相关子查询 / NOT EXISTS 等）。"""

STATS = [
    {
        "key": "trend",
        "title": "按年份出口趋势",
        "sub": "功能点 6.1",
        "chart": "line",
        "desc": "订单表按年份分组，关联订单明细汇总出口台数与金额（ExportOrder ⋈ OrderDetail，金额按币种最新中间价折人民币）",
        "label_field": "年份",
        "value_field": "出口台数",
        "unit": "台",
        "sql": """
SELECT YEAR(o.OrderDate)                            AS 年份,
       COUNT(DISTINCT o.OrderNo)                    AS 订单数,
       COALESCE(SUM(od.Quantity), 0)                AS 出口台数,
       ROUND(COALESCE(SUM(od.Amount * COALESCE(
           (SELECT er.RateToCNY FROM exchangerate er
             WHERE er.CurrencyCode = o.CurrencyCode
             ORDER BY er.YearMonth DESC LIMIT 1), 1)), 0), 2) AS 折人民币金额
  FROM exportorder o
  LEFT JOIN orderdetail od ON od.OrderNo = o.OrderNo
 GROUP BY YEAR(o.OrderDate)
 ORDER BY 年份
"""
    },
    {
        "key": "monthly",
        "title": "月度出口节奏",
        "sub": "功能点 6.1 细化",
        "chart": "bar",
        "desc": "按订单月份统计台数，观察年内出口节奏与旺季分布",
        "label_field": "月份",
        "value_field": "出口台数",
        "unit": "台",
        "sql": """
SELECT DATE_FORMAT(o.OrderDate, '%Y-%m')            AS 月份,
       COUNT(DISTINCT o.OrderNo)                    AS 订单数,
       COALESCE(SUM(od.Quantity), 0)                AS 出口台数
  FROM exportorder o
  LEFT JOIN orderdetail od ON od.OrderNo = o.OrderNo
 GROUP BY DATE_FORMAT(o.OrderDate, '%Y-%m')
 ORDER BY 月份
"""
    },
    {
        "key": "countryRank",
        "title": "按目的国出口排名",
        "sub": "功能点 6.2",
        "chart": "bar",
        "desc": "目的国 ⋈ 订单 ⋈ 明细 三表连接，按目的国汇总台数与订单数",
        "label_field": "目的国",
        "value_field": "出口台数",
        "unit": "台",
        "sql": """
SELECT c.CountryName                                  AS 目的国,
       c.Continent                                    AS 大洲,
       CASE c.IsBeltRoad WHEN 'Y' THEN '是' ELSE '否' END AS 一带一路,
       COUNT(DISTINCT o.OrderNo)                      AS 订单数,
       COALESCE(SUM(od.Quantity), 0)                  AS 出口台数
  FROM country c
  JOIN exportorder o  ON o.CountryCode = c.CountryCode
  LEFT JOIN orderdetail od ON od.OrderNo = o.OrderNo
 GROUP BY c.CountryCode, c.CountryName, c.Continent, c.IsBeltRoad
 ORDER BY 出口台数 DESC, 目的国
"""
    },
    {
        "key": "beltRoad",
        "title": "“一带一路”国家出口占比",
        "sub": "功能点 6.3 · 思政",
        "chart": "donut",
        "desc": "按目的国的 IsBeltRoad 标记分组，直观呈现共建“一带一路”倡议下的出口结构",
        "label_field": "类别",
        "value_field": "出口台数",
        "unit": "台",
        "sql": """
SELECT CASE c.IsBeltRoad WHEN 'Y' THEN '一带一路共建国家' ELSE '非共建国家' END AS 类别,
       COUNT(DISTINCT o.OrderNo)                      AS 订单数,
       COALESCE(SUM(od.Quantity), 0)                  AS 出口台数
  FROM country c
  JOIN exportorder o  ON o.CountryCode = c.CountryCode
  LEFT JOIN orderdetail od ON od.OrderNo = o.OrderNo
 GROUP BY 类别
 ORDER BY 出口台数 DESC
"""
    },
    {
        "key": "entRank",
        "title": "企业出口排名",
        "sub": "功能点 6.5",
        "chart": "bar",
        "desc": "企业 ⋈ 订单 ⋈ 明细 ⋈ 目的国 四表连接，统计台数、订单数与市场覆盖",
        "label_field": "企业名称",
        "value_field": "出口台数",
        "unit": "台",
        "sql": """
SELECT e.EntName                                   AS 企业名称,
       e.Province                                  AS 省份,
       COUNT(DISTINCT o.OrderNo)                   AS 订单数,
       COALESCE(SUM(od.Quantity), 0)               AS 出口台数,
       COUNT(DISTINCT o.CountryCode)               AS 覆盖国家数
  FROM autoenterprise e
  LEFT JOIN exportorder o   ON o.EntID = e.EntID
  LEFT JOIN orderdetail od  ON od.OrderNo = o.OrderNo
 GROUP BY e.EntID, e.EntName, e.Province
 ORDER BY 出口台数 DESC, 企业名称
"""
    },
    {
        "key": "modelRank",
        "title": "车型出口排名",
        "sub": "功能点 6.3 补充",
        "chart": "bar",
        "desc": "明细 ⋈ 车型 ⋈ 订单 三表连接，按车型汇总出口台数；金额按订单币种最新中间价折人民币（跨币种不可直接相加）。柱状图只画前 12 名，表格列出全部 20 款",
        "label_field": "车型名称",
        "value_field": "出口台数",
        "unit": "台",
        "max_rows": 20,
        "sql": """
SELECT m.ModelName                                  AS 车型名称,
       m.VehicleType                                AS 类型,
       COUNT(DISTINCT od.OrderNo)                   AS 订单数,
       SUM(od.Quantity)                             AS 出口台数,
       ROUND(SUM(od.Amount * COALESCE(
           (SELECT er.RateToCNY FROM exchangerate er
             WHERE er.CurrencyCode = o.CurrencyCode
             ORDER BY er.YearMonth DESC LIMIT 1), 1)), 2) AS 折人民币
  FROM orderdetail od
  JOIN exportmodel m ON m.ModelID = od.ModelID
  JOIN exportorder o ON o.OrderNo = od.OrderNo
 GROUP BY m.ModelID, m.ModelName, m.VehicleType
 ORDER BY 出口台数 DESC, 折人民币 DESC
"""
    },
    {
        "key": "policyCompare",
        "title": "政策生效后出口情况",
        "sub": "功能点 6.4",
        "chart": "bar",
        "desc": "对每条贸易政策的适用国家，用相关子查询统计政策生效至今的订单量，并用 EXISTS 过滤掉尚无订单的政策",
        "label_field": "政策名称",
        "value_field": "出口台数",
        "unit": "台",
        "sql": """
SELECT p.PolicyName                              AS 政策名称,
       p.PolicyType                              AS 类型,
       DATE_FORMAT(p.EffectDate, '%Y-%m-%d')     AS 生效日期,
       (SELECT COUNT(DISTINCT o.OrderNo) FROM exportorder o
          JOIN policyapply pa2 ON pa2.CountryCode = o.CountryCode
         WHERE pa2.PolicyID = p.PolicyID AND o.OrderDate >= p.EffectDate)  AS 订单数,
       (SELECT COALESCE(SUM(od.Quantity), 0) FROM orderdetail od
          JOIN exportorder o2  ON o2.OrderNo = od.OrderNo
          JOIN policyapply pa3 ON pa3.CountryCode = o2.CountryCode
         WHERE pa3.PolicyID = p.PolicyID AND o2.OrderDate >= p.EffectDate) AS 出口台数,
       (SELECT GROUP_CONCAT(DISTINCT c.CountryName ORDER BY c.CountryName SEPARATOR '、')
          FROM policyapply pa4
          JOIN country c      ON c.CountryCode = pa4.CountryCode
          JOIN exportorder o4 ON o4.CountryCode = pa4.CountryCode
                            AND o4.OrderDate >= p.EffectDate
         WHERE pa4.PolicyID = p.PolicyID)                                  AS 涉及国家
  FROM policy p
 WHERE EXISTS (SELECT 1 FROM policyapply pa
                 JOIN exportorder o ON o.CountryCode = pa.CountryCode
                WHERE pa.PolicyID = p.PolicyID AND o.OrderDate >= p.EffectDate)
 ORDER BY 出口台数 DESC, 订单数 DESC
"""
    },
    {
        "key": "currencyMix",
        "title": "币种结构与人民币折算",
        "sub": "功能点 5.3 / 5.4",
        "chart": "bar",
        "desc": "订单 ⋈ 币种表，按币种汇总合同额，并按该币种最新中间价折算人民币（不同币种不可直接相加）",
        "label_field": "币种",
        "value_field": "折人民币",
        "unit": "元",
        "sql": """
SELECT cu.CurrencyName                              AS 币种,
       o.CurrencyCode                               AS 代码,
       COUNT(*)                                     AS 订单数,
       ROUND(SUM(o.ContractAmount), 2)              AS 合同金额原币,
       (SELECT er.RateToCNY FROM exchangerate er
         WHERE er.CurrencyCode = o.CurrencyCode
         ORDER BY er.YearMonth DESC LIMIT 1)        AS 折算汇率,
       ROUND(SUM(o.ContractAmount * COALESCE(
           (SELECT er2.RateToCNY FROM exchangerate er2
             WHERE er2.CurrencyCode = o.CurrencyCode
             ORDER BY er2.YearMonth DESC LIMIT 1), 1)), 2) AS 折人民币
  FROM exportorder o
  JOIN currency cu ON cu.CurrencyCode = o.CurrencyCode
 GROUP BY o.CurrencyCode, cu.CurrencyName
 ORDER BY 折人民币 DESC
"""
    },
    {
        "key": "certWarn",
        "title": "认证到期预警",
        "sub": "加分项 · 预警",
        "chart": "none",
        "desc": "车型认证 ⋈ 车型 ⋈ 认证法规 ⋈ 目的国，筛出 180 天内到期或已过期证书",
        "label_field": "车型名称",
        "value_field": "剩余天数",
        "unit": "天",
        "sql": """
SELECT mc.CertNo                                   AS 证书号,
       m.ModelName                                 AS 车型名称,
       e.EntName                                   AS 所属企业,
       ct.CertName                                 AS 认证名称,
       c.CountryName                               AS 认证国家,
       DATE_FORMAT(mc.ExpireDate, '%Y-%m-%d')      AS 到期日期,
       DATEDIFF(mc.ExpireDate, CURDATE())          AS 剩余天数,
       CASE WHEN mc.ExpireDate < CURDATE() THEN '已过期'
            WHEN mc.ExpireDate <= DATE_ADD(CURDATE(), INTERVAL 30 DAY) THEN '30 天内到期'
            ELSE '180 天内到期' END                 AS 预警级别
  FROM modelcert mc
  JOIN exportmodel m     ON m.ModelID  = mc.ModelID
  JOIN autoenterprise e  ON e.EntID    = m.EntID
  JOIN certification ct  ON ct.CertID  = mc.CertID
  LEFT JOIN country c    ON c.CountryCode = ct.CountryCode
 WHERE mc.ExpireDate IS NOT NULL
   AND mc.ExpireDate <= DATE_ADD(CURDATE(), INTERVAL 180 DAY)
 ORDER BY mc.ExpireDate ASC
"""
    },
    {
        "key": "transit",
        "title": "承运商运输时效",
        "sub": "加分项 · 可视化",
        "chart": "bar",
        "desc": "运单 ⋈ 承运商，按实际到港日期与预计离港日期计算平均在途天数",
        "label_field": "承运商",
        "value_field": "平均在途天数",
        "unit": "天",
        "sql": """
SELECT cr.CarrierName                                  AS 承运商,
       cr.TransportMode                               AS 运输方式,
       COUNT(w.WaybillNo)                             AS 运单数,
       ROUND(AVG(DATEDIFF(w.ActualArriveDate, w.ETD)), 1) AS 平均在途天数,
       ROUND(AVG(w.Freight), 2)                       AS 平均运费
  FROM carrier cr
  LEFT JOIN waybill w ON w.CarrierID = cr.CarrierID
       AND w.ActualArriveDate IS NOT NULL AND w.ETD IS NOT NULL
 GROUP BY cr.CarrierID, cr.CarrierName, cr.TransportMode
 ORDER BY 平均在途天数 DESC, 承运商
"""
    },
    {
        "key": "customsSum",
        "title": "报关与退税汇总",
        "sub": "5.4 金额汇总",
        "chart": "none",
        "desc": "报关单 ⋈ 订单 ⋈ 目的国 三表连接，按目的国汇总退税合计与申报总额（合同额按币种中间价折人民币）",
        "label_field": "目的国",
        "value_field": "申报总额",
        "unit": "元",
        "sql": """
SELECT c.CountryName                              AS 目的国,
       COUNT(cu.DeclNo)                            AS 报关单数,
       ROUND(COALESCE(SUM(cu.TaxRefund), 0), 2)    AS 退税合计,
       ROUND(COALESCE(SUM(o.ContractAmount * COALESCE(
           (SELECT er.RateToCNY FROM exchangerate er
             WHERE er.CurrencyCode = o.CurrencyCode
             ORDER BY er.YearMonth DESC LIMIT 1), 1)), 0), 2) AS 申报总额折人民币
  FROM customs cu
  JOIN exportorder o ON o.OrderNo    = cu.OrderNo
  JOIN country c     ON c.CountryCode = o.CountryCode
 GROUP BY c.CountryCode, c.CountryName
 ORDER BY 申报总额折人民币 DESC
"""
    },
]

# SQL 演示台预置查询（答辩时点一下就能跑，证明核心 SQL 真的通）
PRESET_SQL = [
    {
        "title": "五表连接：订单全链路",
        "note": "订单 ⋈ 明细 ⋈ 车型 ⋈ 企业 ⋈ 目的国",
        "sql": """SELECT o.OrderNo, e.EntName, m.ModelName, c.CountryName,
       od.Quantity, od.UnitPrice, od.Amount, o.OrderStatus
FROM exportorder o
JOIN autoenterprise e ON e.EntID = o.EntID
JOIN orderdetail od   ON od.OrderNo = o.OrderNo
JOIN exportmodel m    ON m.ModelID = od.ModelID
JOIN country c        ON c.CountryCode = o.CountryCode
ORDER BY od.Amount DESC
LIMIT 30""",
    },
    {
        "title": "聚合 + HAVING",
        "note": "按目的国分组，筛出出口台数 ≥ 3 的国家",
        "sql": """SELECT c.CountryName AS 目的国, SUM(od.Quantity) AS 出口台数
FROM country c
JOIN exportorder o  ON o.CountryCode = c.CountryCode
JOIN orderdetail od ON od.OrderNo = o.OrderNo
GROUP BY c.CountryCode, c.CountryName
HAVING SUM(od.Quantity) >= 3
ORDER BY 出口台数 DESC""",
    },
    {
        "title": "相关子查询：高于本国均价",
        "note": "找出单价高于同目的国平均单价的明细行",
        "sql": """SELECT o.CountryCode, od.ModelID, od.UnitPrice,
       (SELECT ROUND(AVG(od2.UnitPrice), 2) FROM orderdetail od2
          JOIN exportorder o2 ON o2.OrderNo = od2.OrderNo
         WHERE o2.CountryCode = o.CountryCode) AS 该国均价
FROM orderdetail od
JOIN exportorder o ON o.OrderNo = od.OrderNo
WHERE od.UnitPrice > (
    SELECT AVG(od3.UnitPrice) FROM orderdetail od3
      JOIN exportorder o3 ON o3.OrderNo = od3.OrderNo
     WHERE o3.CountryCode = o.CountryCode)
ORDER BY o.CountryCode, od.UnitPrice DESC""",
    },
    {
        "title": "NOT EXISTS：零出口车型",
        "note": "反连接，找出还没有任何出口记录的车型",
        "sql": """SELECT m.ModelID, m.ModelName, m.RangeKm, m.ModelStatus
FROM exportmodel m
WHERE NOT EXISTS (
    SELECT 1 FROM orderdetail od WHERE od.ModelID = m.ModelID)
ORDER BY m.ModelID""",
    },
    {
        "title": "窗口函数：各国金额 Top2",
        "note": "ROW_NUMBER() OVER (PARTITION BY ...) 分组排名",
        "sql": """SELECT * FROM (
  SELECT o.CountryCode, o.OrderNo, o.ContractAmount,
         ROW_NUMBER() OVER (PARTITION BY o.CountryCode
                            ORDER BY o.ContractAmount DESC) AS rn
  FROM exportorder o) t
WHERE rn <= 2
ORDER BY CountryCode, rn""",
    },
    {
        "title": "汇率换算：订单折人民币",
        "note": "优先取当月中间价，缺失时回退到该币种最新中间价",
        "sql": """SELECT o.OrderNo, o.CurrencyCode, o.ContractAmount,
       DATE_FORMAT(o.OrderDate, '%Y%m') AS 订单月份,
       month_rate.RateToCNY  AS 当月汇率,
       latest_rate.RateToCNY AS 最新汇率,
       ROUND(o.ContractAmount * COALESCE(month_rate.RateToCNY, latest_rate.RateToCNY, 1), 2) AS 折合人民币
FROM exportorder o
LEFT JOIN exchangerate month_rate
       ON month_rate.CurrencyCode = o.CurrencyCode
      AND month_rate.YearMonth = DATE_FORMAT(o.OrderDate, '%Y%m')
LEFT JOIN exchangerate latest_rate
       ON latest_rate.CurrencyCode = o.CurrencyCode
      AND latest_rate.YearMonth = (SELECT MAX(e2.YearMonth) FROM exchangerate e2
                                    WHERE e2.CurrencyCode = o.CurrencyCode)
ORDER BY 折合人民币 DESC""",
    },
]


# ---------------------------------------------------------------- 图表数据准备
def prepare_chart(stat, rows):
    """把查询结果整理成 CSS/SVG 可直接渲染的结构（不依赖任何前端图表库）"""
    rows = rows or []
    chart = stat.get("chart", "none")
    if chart == "none" or not rows:
        return None

    lf = stat.get("label_field")
    vf = stat.get("value_field")
    vf2 = stat.get("value_field2")

    def num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    items = [{"label": str(r.get(lf, "")), "value": num(r.get(vf)),
              "value2": num(r.get(vf2)) if vf2 else None} for r in rows]

    all_zero = all((i["value"] or 0) == 0 and (i["value2"] or 0) == 0 for i in items)

    if chart in ("bar", "grouped"):
        top = items[:12] if chart == "bar" else items[:8]
        peak = max([max(i["value"], i["value2"] or 0) for i in top] + [1])
        for i in top:
            i["pct"] = round(i["value"] / peak * 100, 2)
            if i["value2"] is not None:
                i["pct2"] = round(i["value2"] / peak * 100, 2)
        return {"type": chart, "items": top, "peak": peak, "all_zero": all_zero,
                "legend": stat.get("legend")}

    if chart == "donut":
        total = sum(i["value"] for i in items) or 1
        acc = 0.0
        colors = ["#1e40af", "#0ea5e9", "#14b8a6", "#f59e0b", "#8b5cf6", "#ef4444"]
        segs = []
        for idx, i in enumerate(items):
            pct = i["value"] / total * 100
            i["pct"] = round(pct, 2)
            i["color"] = colors[idx % len(colors)]
            segs.append("%s %.2f%% %.2f%%" % (i["color"], acc, acc + pct))
            acc += pct
        return {"type": "donut", "items": items, "total": total, "all_zero": total <= 0,
                "gradient": "conic-gradient(%s)" % ", ".join(segs)}

    if chart == "line":
        w, h, pad_l, pad_r, pad_t, pad_b = 660, 220, 46, 16, 16, 34
        peak = max([i["value"] for i in items] + [1])
        n = len(items)
        step = (w - pad_l - pad_r) / max(1, n - 1) if n > 1 else 0
        pts = []
        for idx, i in enumerate(items):
            x = pad_l + step * idx if n > 1 else (w - pad_l - pad_r) / 2 + pad_l
            y = h - pad_b - (i["value"] / peak) * (h - pad_t - pad_b)
            pts.append({"x": round(x, 1), "y": round(y, 1), "label": i["label"], "value": i["value"]})
        # 网格线
        grid = []
        for g in range(5):
            gy = pad_t + (h - pad_t - pad_b) * g / 4
            grid.append({"y": round(gy, 1), "val": round(peak * (4 - g) / 4, 1)})
        return {"type": "line", "points": pts, "grid": grid, "peak": peak, "all_zero": all_zero,
                "w": w, "h": h, "pad_l": pad_l, "pad_r": pad_r, "pad_t": pad_t, "pad_b": pad_b,
                "polyline": " ".join("%s,%s" % (p["x"], p["y"]) for p in pts),
                "area": ("M%s,%s " % (pts[0]["x"], h - pad_b) +
                         " ".join("L%s,%s" % (p["x"], p["y"]) for p in pts) +
                         " L%s,%s Z" % (pts[-1]["x"], h - pad_b)) if pts else ""}
    return None


def kpi_summary():
    """首页 KPI"""
    from db import q1

    k = {}
    # 不同币种金额不能直接相加：统一按「该币种最新中间价」折算人民币
    a = q1("""SELECT COUNT(*) AS n,
                   COUNT(DISTINCT o.CurrencyCode) AS cur_n,
                   COALESCE(SUM(o.ContractAmount * COALESCE(
                       (SELECT er.RateToCNY FROM exchangerate er
                         WHERE er.CurrencyCode = o.CurrencyCode
                         ORDER BY er.YearMonth DESC LIMIT 1), 1)), 0) AS cny
              FROM exportorder o""")
    k["orders"] = int(a["n"]) if a else 0
    k["amount"] = float(a["cny"]) if a else 0
    k["currencies"] = int(a["cur_n"]) if a else 0

    b = q1("SELECT COALESCE(SUM(Quantity),0) AS n FROM orderdetail")
    k["units"] = int(b["n"]) if b else 0

    c = q1("SELECT COUNT(DISTINCT CountryCode) AS n FROM exportorder")
    k["countries"] = int(c["n"]) if c else 0

    d = q1("SELECT COUNT(*) AS n FROM autoenterprise")
    k["enterprises"] = int(d["n"]) if d else 0

    e = q1("""SELECT
                COALESCE(SUM(CASE WHEN c.IsBeltRoad='Y' THEN od.Quantity ELSE 0 END),0) AS belt,
                COALESCE(SUM(od.Quantity),0) AS allq
               FROM exportorder o
               JOIN country c ON c.CountryCode = o.CountryCode
               LEFT JOIN orderdetail od ON od.OrderNo = o.OrderNo""")
    if e and e["allq"]:
        k["belt_ratio"] = round(float(e["belt"]) / float(e["allq"]) * 100, 1)
        k["belt_units"] = int(e["belt"])
    else:
        k["belt_ratio"], k["belt_units"] = 0, 0

    # 预警口径：180 天窗，且必须把「已经过期」和「临近到期」分开数。
    # 只算 <= CURDATE()+180 会把早就过期的证书混进来，页面上说「180 天内到期」就成了假话。
    f = q1("""SELECT COUNT(*) AS n,
                     COALESCE(SUM(CASE WHEN ExpireDate < CURDATE() THEN 1 ELSE 0 END), 0) AS expired,
                     COALESCE(SUM(CASE WHEN ExpireDate >= CURDATE()
                                        AND ExpireDate <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
                                       THEN 1 ELSE 0 END), 0) AS soon
                FROM modelcert
               WHERE ExpireDate IS NOT NULL
                 AND ExpireDate <= DATE_ADD(CURDATE(), INTERVAL 180 DAY)""")
    k["expiring"] = int(f["n"]) if f else 0
    k["expired"] = int(f["expired"]) if f else 0
    k["expiring_soon"] = int(f["soon"]) if f else 0

    g = q1("SELECT COALESCE(SUM(TaxRefund),0) AS n FROM customs")
    k["refund"] = float(g["n"]) if g else 0

    return k

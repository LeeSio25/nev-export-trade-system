# -*- coding: utf-8 -*-
"""端到端测试：按"业务人员真实要干的事"验证系统，而不是逐个点页面。

运行：
    python tests/e2e_test.py            # 默认 http://127.0.0.1:5000
    python tests/e2e_test.py 5001       # 指定端口

每个用例模拟一条业务链路，例如「业务员录一笔新订单 → 立刻能查回来 → 导出给单证员」。
写库的用例会自己清理，跑完不留垃圾数据。
"""
import http.cookiejar
import re
import sys
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:%s" % (sys.argv[1] if len(sys.argv) > 1 else "5000")
JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(JAR))

PASS, FAIL = [], []


def get(path, **params):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with OPENER.open(url, timeout=30) as r:
        return r.getcode(), r.read().decode("utf-8", "ignore"), r.geturl()


def post(path, data, **params):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with OPENER.open(req, timeout=30) as r:
        return r.getcode(), r.read().decode("utf-8", "ignore"), r.geturl()


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print("  [PASS] %s" % name)
    else:
        FAIL.append((name, detail))
        print("  [FAIL] %s  %s" % (name, detail))


def flash_of(html):
    m = re.findall(r'<div class="flash (\w+)">\s*<span>(.*?)</span>', html, re.S)
    return m[-1] if m else ("?", "无提示")


def count_of(html):
    m = re.search(r"共 <b>(\d+)</b> 条记录", html)
    return int(m.group(1)) if m else None


# =====================================================================
print("\n【角色 1｜业务员】我要录一笔新订单，并确认它真的进了系统")
# =====================================================================
DUMMY = {"CurrencyCode": "ZZZ", "CurrencyName": "端到端测试币", "Symbol": "Q"}

# 先清理上次残留
try:
    post("/t/currency/delete", {"pk_CurrencyCode": "ZZZ"})
except Exception:
    pass

code, html, _ = post("/t/currency/new", DUMMY)
cat, msg = flash_of(html)
check("新增一条币种记录成功", cat == "ok", msg)

code, html, _ = get("/t/currency", q="端到端测试币")
check("用关键词能搜到刚录入的记录", count_of(html) == 1, "搜到 %s 条" % count_of(html))

code, html, _ = post("/t/currency/edit", {"CurrencyName": "端到端测试币V2", "Symbol": "Q2"},
                     pk_CurrencyCode="ZZZ")
cat, msg = flash_of(html)
check("修改保存成功", cat == "ok", msg)
check("修改值已回写", "端到端测试币V2" in html, "页面上没看到新值")

# --- 下拉选项必须覆盖库里的真实取值，否则一编辑就把这一列写成 NULL
code, html, _ = get("/t/aftersales/edit?pk_ASID=A002")
check("编辑页能选中库中已有的组合值", 'value="销售/售后" selected' in html,
      "售后网点 ASType 下拉里没有「销售/售后」，保存会把它清空")

code, html, _ = get("/t/customs/new")
check("报关单状态下拉含「已申报」", ">已申报<" in html, "CHECK 允许但下拉里选不到")
code, html, _ = get("/t/waybill/new")
check("运单状态下拉含「未发运」", ">未发运<" in html, "CHECK 允许但下拉里选不到")

# =====================================================================
print("\n【角色 2｜单证员】我要按目的国 + 订单状态筛选订单，而不是翻 10 条肉眼找")
# =====================================================================
code, html, _ = get("/t/exportorder", f_CountryCode="THA")
n_tha = count_of(html)
check("按目的国筛选生效（泰国）", n_tha is not None and n_tha < 10,
      "筛选后仍有 %s 条，说明筛选没起作用" % n_tha)

code, html, _ = get("/t/exportorder", f_CountryCode="THA", f_OrderStatus="在途")
check("多条件组合筛选可用", count_of(html) is not None,
      "组合筛选返回异常：%s" % count_of(html))

code, html, _ = get("/t/exportorder")
check("列表页提供筛选控件", 'name="f_CountryCode"' in html,
      "页面上没有 f_CountryCode 下拉框")

# =====================================================================
print("\n【角色 3｜跟单员】点开一笔订单，我要一眼看到 明细 + 运单 + 报关，而不是跳四个表手抄订单号")
# =====================================================================
code, html, _ = get("/t/exportorder", q="ORD202610240001")
m = re.search(r'href="(/order/[^"]+)"', html)
check("订单列表能点进订单全景页", m is not None, "列表里没有指向 /order/ 的链接")

if m:
    code, html2, _ = get(m.group(1))
    check("订单全景页可访问", code == 200, "HTTP %s" % code)
    check("全景页含订单明细", "订单明细" in html2, "没有明细区块")
    check("全景页含物流运单", "运单" in html2 or "物流" in html2, "没有物流区块")
    check("全景页含报关信息", "报关" in html2, "没有报关区块")
    check("全景页体现状态推进链路", re.search(r"(未发货|在途|到港|签收).{0,80}(未发货|在途|到港|签收)", html2) is not None,
          "看不到状态阶段")
    check("能比对预计到港与实际到港", ("提前" in html2) or ("延迟" in html2) or ("准点" in html2),
          "没有时效差异提示")

# =====================================================================
print("\n【角色 4｜业务主管】我要看到有数据支撑的统计，没数据的图表不要占版面")
# =====================================================================
code, html, _ = get("/stats")
check("统计页可访问", code == 200, "HTTP %s" % code)
check("政策统计已按新口径出数", "政策生效后出口情况" in html and "欧盟对华电动汽车反补贴税" in html,
      "政策块没有数据或仍是旧口径")
check("新增车型维度统计", "车型出口排名" in html and "比亚迪宋PLUS EV" in html,
      "车型排名缺失")
check("有数据的统计块仍在", "月度出口节奏" in html and "企业出口排名" in html, "有数据的块被误删")
check("全部统计块都有数据，无空图占版面", "暂未展示" not in html,
      "仍有全 0 的统计块")
check("金额标注了折算口径", "折人民币" in html, "没看到折人民币标注")

# =====================================================================
print("\n【角色 5｜合规专员】认证快到期了，我要一键拿到清单")
# =====================================================================
code, html, _ = get("/stats", only="certWarn")
check("认证预警清单可访问", code == 200 and ("剩余天数" in html), "预警页异常")

code, html, _ = get("/")
check("首页有待办入口指向预警/在途", ("在途" in html) or ("待办" in html), "首页没有待办入口")

# =====================================================================
print("\n【角色 6｜财务】我要把筛选结果导成 Excel 交给会计")
# =====================================================================
url = BASE + "/t/exportorder/export?" + urllib.parse.urlencode({"f_CountryCode": "THA"})
with OPENER.open(url, timeout=30) as r:
    csv_text = r.read().decode("utf-8", "ignore")
    disp = r.headers.get("Content-Disposition", "")
check("导出返回附件", "attachment" in disp, disp)
check("CSV 带 BOM（Excel 不乱码）", csv_text.startswith("\ufeff"), repr(csv_text[:6]))
check("导出行数跟随筛选条件", len([l for l in csv_text.splitlines() if l.strip()]) - 1 <= n_tha,
      "导出 %s 行，筛选显示 %s 行" % (len(csv_text.splitlines()) - 1, n_tha))

# =====================================================================
print("\n【角色 7｜数据库课代表】我要现场验证约束真的生效，而不是 PPT 上说有")
# =====================================================================
code, html, _ = post("/t/autoenterprise/delete", {"pk_EntID": "E001"})
cat, msg = flash_of(html)
check("删除被引用企业被外键拦下", cat == "err" and "引用" in msg, msg)

code, html, _ = post("/query", {"sql": "DELETE FROM exportorder"})
check("SQL 演示台拦截写操作", "只允许只读查询" in html, "写操作没被拦")

# 只用前缀判断会被这几种写法绕过，必须按语句类型判
code, html, _ = post("/query", {"sql": "WITH x AS (SELECT 1) DELETE FROM exportorder"})
check("SQL 演示台拦截 CTE 包着的写操作", "只允许" in html, "WITH … DELETE 没被拦")

code, html, _ = post("/query", {"sql": "/* 注释 */ DELETE FROM exportorder"})
check("SQL 演示台拦截注释开头绕过的写操作", "只允许只读查询" in html, "注释绕过后没被拦")

code, html, _ = post("/query", {"sql": "SELECT * FROM exportorder INTO OUTFILE '/tmp/x.txt'"})
check("SQL 演示台拦截导出文件", "导出文件" in html, "INTO OUTFILE 没被拦")

code, html, _ = post("/query", {"sql": "SELECT COUNT(*) AS n FROM exportorder"})
check("SQL 演示台能跑只读查询", "查询结果" in html, "查询没出结果")

# =====================================================================
print("\n【收尾】清理测试数据")
# =====================================================================
code, html, _ = post("/t/currency/delete", {"pk_CurrencyCode": "ZZZ"})
cat, msg = flash_of(html)
check("测试记录已删除（不留垃圾数据）", cat == "ok", msg)

# =====================================================================
print("\n" + "=" * 62)
print("通过 %d 项，失败 %d 项" % (len(PASS), len(FAIL)))
if FAIL:
    print("\n需要处理的问题：")
    for name, detail in FAIL:
        print("  - %s：%s" % (name, detail))
print("=" * 62)
sys.exit(1 if FAIL else 0)

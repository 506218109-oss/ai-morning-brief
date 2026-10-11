"""AI 日报 · 采集（不需要浏览器的部分）
来源：aihot.news 官方 JSON 接口、aihot.today 聚合页、GitHub Trending、即刻（话题页 + 博主主页）
怎么跑：python3 collect_web.py            → 写到 raw/今天日期/web.json
       python3 collect_web.py 2026-10-09 → 指定日期目录
任何一个来源失败都不会中断，错误记在 errors 里，最后照实写进日报 footer。
"""
import html, json, re, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
DATE = sys.argv[1] if len(sys.argv) > 1 else NOW.strftime("%Y-%m-%d")
CFG = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
SINCE = NOW - timedelta(hours=CFG["window_hours"])
UA_PC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36"
UA_M = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"


def get(url, ua=UA_PC, tries=3):
    # 用 curl 并开启压缩（AI Hot 官方建议的方式，也更稳）；失败自动重试，最多 3 次
    err = ""
    for i in range(tries):
        r = subprocess.run(["curl", "-fsSL", "--compressed", "-m", "40", "-A", ua, "-H", "Accept-Language: zh-CN,zh", url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout.decode("utf-8", "ignore")
        err = r.stderr.decode("utf-8", "ignore").strip()[:200] or f"curl 退出码 {r.returncode}"
        time.sleep(2 * (i + 1))
    raise RuntimeError(err)


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>|<!-- -->", "", s))).strip()


def in_window(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")) >= SINCE
    except Exception:
        return False


def aihot_news():
    # 官方匿名接口（个人非商业使用免费）；精选 + 全部动态各取一份
    out = {}
    for mode in ("selected", "all"):
        q = "window=24h&limit=30" + ("&mode=all" if mode == "all" else "")
        d = json.loads(get(f"https://aihot.news/api/v1/items?{q}", ua="aihot-api/2.0.0"))
        out[mode] = [{
            "title": x["title"], "summary": x.get("summary"), "reason": x.get("reason"),
            "score": x.get("score"), "source": (x.get("source") or {}).get("name"),
            "time": x.get("publishedAt"), "category": x.get("category"),
            "link": (x.get("links") or {}).get("original"), "aihot": (x.get("links") or {}).get("aihot"),
        } for x in d.get("items", [])]
    hot = json.loads(get("https://aihot.news/api/v1/hot-topics", ua="aihot-api/2.0.0"))
    out["hot"] = hot.get("items", [])[:10]
    return out


def aihot_today(per_source=8):
    # 页面按来源分栏：来源名 + 更新时间，下面是编号列表（没有单条时间）
    s = get("https://aihot.today/")
    heads = list(re.finditer(r'<span class="font-semibold[^"]*">([^<]+)</span></a><span[^>]*>([^<]+)</span>', s))
    out = []
    for i, h in enumerate(heads):
        block = s[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(s)]
        items = re.findall(r'<a href="(https?://[^"]+)" target="_blank"><div[^>]*><div[^>]*><div class="font-\[500\]">(.*?)</div>(?:<div class="mt-1[^"]*">(.*?)</div>)?', block, re.S)
        out.append({"source": h.group(1), "updated": h.group(2), "items": [
            {"title": re.sub(r"^\d+\s*\.\s*", "", clean(t)), "sub": clean(sub or ""), "link": u} for u, t, sub in items[:per_source]]})
    return out


def github_trending():
    s = get("https://github.com/trending?since=daily")
    out = []
    for row in re.findall(r'<article class="Box-row">(.*?)</article>', s, re.S)[:15]:
        name = clean(re.search(r"<h2.*?<a[^>]*>(.*?)</a>", row, re.S).group(1)).replace(" ", "")
        desc = re.search(r'<p class="col-9[^"]*">(.*?)</p>', row, re.S)
        lang = re.search(r'itemprop="programmingLanguage">(.*?)<', row)
        stars = re.search(r'href="/[^"]+/stargazers"[^>]*>(.*?)</a>', row, re.S)
        today = re.search(r"([\d,]+) stars (today|this week)", row)
        out.append({"name": name, "desc": clean(desc.group(1)) if desc else "", "lang": lang.group(1) if lang else "",
                    "stars": clean(stars.group(1)) if stars else "", "today": today.group(1) if today else "",
                    "link": f"https://github.com/{name}"})
    return out


def jike_next_data(url):
    s = get(url, ua=UA_M)
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', s, re.S)
    return json.loads(m.group(1))["props"]["pageProps"].get("posts", [])


def jike():
    def fmt(p, who=None):
        return {"author": who or p["user"]["screenName"], "time": p.get("createdAt"), "content": p.get("content", ""),
                "likes": p.get("likeCount"), "comments": p.get("commentCount"), "reposts": p.get("repostCount"),
                "link": f"https://m.okjike.com/originalPosts/{p['id']}"}
    out = {"topic": [fmt(p) for p in jike_next_data(f"https://m.okjike.com/topics/{CFG['jike_topic']}") if in_window(p.get("createdAt", ""))]}
    for name, uid in CFG["jike_users"].items():
        out[name] = [fmt(p, name) for p in jike_next_data(f"https://m.okjike.com/users/{uid}") if in_window(p.get("createdAt", ""))]
    return out


if __name__ == "__main__":
    result, errors = {"collected_at": NOW.isoformat(), "since": SINCE.isoformat()}, {}
    for key, fn in [("aihot_news", aihot_news), ("aihot_today", aihot_today), ("github", github_trending), ("jike", jike)]:
        try:
            result[key] = fn()
        except Exception as e:
            errors[key] = f"{type(e).__name__}: {e}"
    result["errors"] = errors
    out = ROOT / "raw" / DATE / "web.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    # 打印每个来源拿到多少条，便于一眼看出哪里坏了
    n = lambda v: sum(len(x) if isinstance(x, list) else len(x.get("items", [1])) for x in (v.values() if isinstance(v, dict) else v)) if v else 0
    print(out, {k: n(result.get(k)) for k in ("aihot_news", "aihot_today", "github", "jike")}, "errors:", errors or "无")

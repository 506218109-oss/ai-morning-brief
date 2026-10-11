"""AI 日报 · 把采集到的原始数据整理成一份精简清单，供选题用
怎么跑：python3 digest.py 2026-10-10                 → 写到 raw/日期/digest.txt 并打印统计
       python3 digest.py 2026-10-10 --full 片段 片段…  → 打印链接里含这些片段的条目全文（写稿前核对用）
清单里的时间都已换算成北京时间。
"""
import json, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DATE = sys.argv[1]
RAW = ROOT / "raw" / DATE
b = json.loads((RAW / "browser.json").read_text(encoding="utf-8")) if (RAW / "browser.json").is_file() else {"x": {}, "weibo": {}, "zhihu_hot": [], "errors": {"browser": "browser.json 不存在，浏览器采集没跑成功"}}
w = json.loads((RAW / "web.json").read_text(encoding="utf-8"))
c = lambda s, n=150: re.sub(r"\s+", " ", s or "")[:n]


def cst(t):
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M")
    except Exception:
        return "-"


def all_items():
    # 统一成 (平台, 作者, 时间, 互动, 正文, 链接)
    for h, ps in b.get("x", {}).items():
        for p in ps:
            yield ("X", h, p["time"], p.get("metrics", ""), p.get("text", ""), p["link"])
    for h, ps in b.get("weibo", {}).items():
        for p in ps:
            extra = f"\n↪转发自 {p['retweet_of']}" if p.get("retweet_of") else ""
            yield ("微博", h, p["time"], f"转{p['reposts']} 评{p['comments']} 赞{p['likes']}", p["text"] + extra, p["link"])
    for k, ps in w.get("jike", {}).items():
        for p in ps:
            yield ("即刻", p["author"] + ("（AI探索站）" if k == "topic" else ""), p["time"], f"赞{p['likes']} 评{p['comments']} 转{p.get('reposts')}", p["content"], p["link"])


if "--full" in sys.argv:
    frags = sys.argv[sys.argv.index("--full") + 1:]
    for plat, who, t, m, text, link in all_items():
        if any(f in link for f in frags):
            print(f"### {plat} {who} · {cst(t)} CST · {m}\n{text}\n{link}\n")
    for x in w.get("aihot_news", {}).get("selected", []) + w.get("aihot_news", {}).get("all", []):
        if any(f in (x.get("link") or "") + (x.get("aihot") or "") for f in frags):
            print(f"### AI Hot {x['score']} · {cst(x['time'])} CST · {x['source']}\n{x['title']}\n{x['summary']}\n推荐理由：{x['reason']}\n原文 {x['link']}\n")
    for z in b.get("zhihu_hot", []):
        if any(f in z["link"] for f in frags):
            print("### 知乎", json.dumps(z, ensure_ascii=False), "\n")
    sys.exit(0)

L = []
errs = {**w.get("errors", {}), **b.get("errors", {})}
L.append(f"采集时间 {cst(w['collected_at'])} CST · 窗口起点 {cst(w['since'])} CST")
L.append(f"采集报错：{json.dumps(errs, ensure_ascii=False) if errs else '无'}")
L.append("## X（时间为北京时间）")
for h, ps in b.get("x", {}).items():
    if not ps:
        L.append(f"[{h}] 窗口内无新帖")
    for p in ps:
        L.append(f"[{h}] {cst(p['time'])} {c(p.get('social'), 10)} | {c(p.get('metrics'), 60)} | {c(p.get('text'))} | {p['link'].split('/status/')[-1]}")
L.append("## 微博")
for h, ps in b.get("weibo", {}).items():
    if not ps:
        L.append(f"[{h}] 窗口内无新帖")
    for p in ps:
        L.append(f"[{h}] {cst(p['time'])} 转{p['reposts']}评{p['comments']}赞{p['likes']} | {c(p['text'], 120)} {('↪' + c(p['retweet_of'], 40)) if p.get('retweet_of') else ''} | {p['link'][-16:]}")
L.append("## 知乎热榜（只留 AI 相关）")
for z in b.get("zhihu_hot", []):
    L.append(f"第{z['rank']} {z['title']} | {z['heat']} | {z['link']} | {c(z.get('excerpt'), 260)}")
L.append("## 即刻")
for k, ps in w.get("jike", {}).items():
    for p in ps:
        L.append(f"[{k}/{p['author']}] {cst(p['time'])} 赞{p['likes']}评{p['comments']} | {c(p['content'])} | {p['link'][-24:]}")
a = w.get("aihot_news", {})
L.append("## AI Hot 精选（按评分）")
for x in sorted(a.get("selected", []), key=lambda x: -(x["score"] or 0)):
    L.append(f"{x['score']} {cst(x['time'])} | {x['title'][:70]} | {(x['source'] or '')[:24]} | {(x.get('aihot') or '')[-25:]}")
L.append("## AI Hot 全部动态（非精选，评分≥55）")
sel = {x["title"] for x in a.get("selected", [])}
for x in a.get("all", []):
    if x["title"] not in sel and (x["score"] or 0) >= 55:
        L.append(f"{x['score']} {cst(x['time'])} | {x['title'][:70]} | {(x['source'] or '')[:24]} | {(x.get('aihot') or '')[-25:]}")
L.append("## AI Hot 热点事件（多家同时在报，括号里是来源数）")
for h in a.get("hot", []):
    L.append(f"  {h.get('title')}（{h.get('sourceCount')}）")
L.append("## aihot.today 各媒体分栏（只有标题，没有单条时间）")
for s in w.get("aihot_today", []):
    if s["source"] in ("WSJ", "TechCrunch", "36Kr", "极客公园", "量子位", "CNBC", "Hacker News"):
        L.append(f"-- {s['source']}（更新于 {s['updated']}）")
        L += [f"    {i['title'][:64]} | {i['link']}" for i in s["items"][:7]]
L.append("## GitHub Trending")
for g in w.get("github", []):
    L.append(f"{g['name']} | {g['lang']} | {g['stars']} stars 今日+{g['today']} | {g['desc'][:110]}")
L.append("## 最近几期已经写过的标题（仅供判断延续性；持续热的话题可以继续上）")
for f in sorted((ROOT / "issues").glob("20??-??-??.json"))[-4:]:
    if f.stem != DATE:
        d = json.loads(f.read_text(encoding="utf-8"))
        L.append(f"-- {f.stem}：" + "；".join(p["title"][:30] for p in d["posts"]) + "｜GitHub：" + "、".join(r["name"] for r in d["repos"]))
(RAW / "digest.txt").write_text("\n".join(L), encoding="utf-8")
n = lambda o: sum(len(v) for v in o.values())
print(RAW / "digest.txt", f"{len(L)} 行 | X {n(b.get('x', {}))} · 微博 {n(b.get('weibo', {}))} · 知乎 {len(b.get('zhihu_hot', []))} · 即刻 {n(w.get('jike', {}))} · AI Hot {len(a.get('selected', []))}+{len(a.get('all', []))} · GitHub {len(w.get('github', []))} | 报错 {len(errs)} 项")

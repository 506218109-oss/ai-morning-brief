"""AI 日报 · 统一入口（每天自动运行只用这一个命令，子命令固定、日期自动取当天）
为什么要有它：权限是按“命令长什么样”记住的。以前命令里带日期、带每次不同的网址，
每天都变成“没见过的新命令”，于是每天都要重新点允许。现在所有步骤都是 `python3 run.py 子命令`，
允许一次以后就不会再问。

用法（都在项目目录里执行）：
  python3 run.py status                  看今天做到哪一步、下一步该做什么
  python3 run.py collect                 采集全部信源并生成选题清单（约 6 分钟）
  python3 run.py full 片段1 片段2 …       打印清单里某几条的全文（片段 = 清单每行末尾那串 ID）
  python3 run.py search "关键词"          在 AI Hot 搜最近 7 天的报道（加 --window 24h 只看一天）
  python3 run.py fetch "文章链接"         读一篇公开文章的正文（核对数字、时间用）
  python3 run.py save <<'JSON' … JSON    把当期稿子（JSON）存成 issues/日期.json
  python3 run.py build                   生成 HTML 并自动检查
  python3 run.py publish                 发布到 GitHub Pages 并等线上生效
  python3 run.py push                    预览 Bark 通知；加 --send 才真的发
  python3 run.py log "一句话记录"         追加一行运行记录
所有子命令默认处理今天（北京时间）；要处理别的日期加 --date 2026-10-11。
"""
import html, json, os, re, subprocess, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
TZ = timezone(timedelta(hours=8))
WEEK = "一二三四五六日"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36"

args = sys.argv[1:]
DATE = datetime.now(TZ).strftime("%Y-%m-%d")
if "--date" in args:
    i = args.index("--date")
    DATE = args[i + 1]
    del args[i:i + 2]
cmd, rest = (args[0] if args else "status"), args[1:]


def py(script, *a, timeout=900):
    # 运行项目里的另一个脚本，原样把输出打印出来，返回退出码
    r = subprocess.run([sys.executable, script, *a], cwd=ROOT, timeout=timeout)
    return r.returncode


def status():
    now = datetime.now(TZ)
    print(f"现在 {now:%Y-%m-%d %H:%M} 周{WEEK[now.weekday()]}（北京时间）｜处理日期 {DATE}")
    raw = ROOT / "raw" / DATE
    have = {n: (raw / n).is_file() for n in ("web.json", "browser.json", "digest.txt")}
    issue, out, rec = ROOT / "issues" / f"{DATE}.json", ROOT / "outputs" / f"ai-brief-{DATE}.html", ROOT / "state" / f"bark-{DATE}.json"
    bark = json.loads(rec.read_text(encoding="utf-8")).get("status") if rec.is_file() else None
    print(f"采集：{have}｜稿子 {issue.is_file()}｜成品 {out.is_file()}｜Bark 状态 {bark}")
    if bark == "accepted":
        print("下一步：今天已经推送过，直接结束。")
    elif out.is_file():
        print("下一步：成品已有但还没推送成功 → 从 publish 接着做（不要重新采集和写稿）。")
    elif issue.is_file():
        print("下一步：稿子已有 → 自查后 build。")
    elif all(have.values()):
        print("下一步：采集已完成 → 读 raw/日期/digest.txt 选题写稿。")
    else:
        print("下一步：collect。")


def collect():
    rc = py("collect_web.py", DATE)
    env = dict(os.environ, PATH=f"{Path.home()}/.local/bin:" + os.environ.get("PATH", ""))
    out = ROOT / "raw" / DATE / "browser.json"

    def browser_once():
        before = out.stat().st_mtime if out.is_file() else 0   # 记下旧文件的时间，采集后必须变新才算成功
        try:
            # ego-browser 里的脚本读不到环境变量，所以把日期作为第一行注入脚本
            head = f"globalThis.__AIDAILY_DATE = {json.dumps(DATE)}; globalThis.__AIDAILY_ROOT = {json.dumps(str(ROOT))};\n"
            script = head.encode() + (ROOT / "collect_browser.mjs").read_bytes()
            r = subprocess.run(["ego-browser", "nodejs"], input=script, env=env, cwd=ROOT, timeout=1500)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"浏览器采集出错：{type(e).__name__}: {e}")
            return False
        if r.returncode or not out.is_file() or out.stat().st_mtime <= before:
            return False
        errs = json.loads(out.read_text(encoding="utf-8")).get("errors", {})
        return "x:全部" not in errs

    ok = browser_once()
    if not ok:
        print("浏览器采集没成功：打开 Ego Lite，20 秒后重试 1 次……")
        subprocess.run(["open", "-a", "ego lite"])
        time.sleep(20)
        ok = browser_once()
    if not ok:
        print("【注意】X、微博、知乎本次没采集到（或 X 全部失败）。按手册用其余来源出报，并在页脚和最后回复里如实说明。")
    rc2 = py("digest.py", DATE)
    sys.exit(rc or rc2)


def search():
    window, limit, words = "7d", "6", []
    it = iter(rest)
    for a in it:
        if a == "--window":
            window = next(it)
        elif a == "--limit":
            limit = next(it)
        else:
            words.append(a)
    q = urllib.parse.urlencode({"q": " ".join(words), "window": window, "mode": "all", "limit": limit})
    items, err = None, ""
    for attempt in range(2):   # AI Hot 官方建议用 curl 并开启压缩；失败自动重试 1 次
        r = subprocess.run(["curl", "-sS", "--compressed", "-m", "25", "-A", "aihot-api/2.0.0", f"https://aihot.news/api/v1/items?{q}"], capture_output=True, text=True)
        try:
            items = json.loads(r.stdout).get("items", [])
            break
        except Exception as e:
            err = (r.stderr.strip() or f"{type(e).__name__}: {e}")[:200]
            time.sleep(3)
    if items is None:
        sys.exit(f"AI Hot 搜索失败（已重试 1 次）：{err}")
    if not items:
        print("没有搜到。")
    for x in items:
        t = datetime.fromisoformat(x["publishedAt"].replace("Z", "+00:00")).astimezone(TZ).strftime("%m-%d %H:%M")
        print(f"[评分 {x.get('score')}] {t} CST｜{x['title']}｜{(x.get('source') or {}).get('name')}\n   摘要：{x.get('summary')}\n   推荐理由：{x.get('reason')}\n   原文：{(x.get('links') or {}).get('original')}\n")


def fetch():
    if not rest:
        sys.exit("用法：python3 run.py fetch \"文章链接\" [最多字数，默认 5000]")
    url, limit = rest[0], int(rest[1]) if len(rest) > 1 else 5000
    if not url.startswith(("http://", "https://")):
        sys.exit("只支持 http/https 链接。")
    try:
        s = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh,en"}), timeout=30).read().decode("utf-8", "ignore")
    except Exception as e:
        sys.exit(f"打不开：{type(e).__name__}: {e}\n（遇到付费墙、登录墙或反爬拦截就不要绕过，换别的来源，并在页脚如实说明。）")
    for k in ("og:title", "og:description", "article:published_time"):
        m = re.search(r'<meta[^>]+(?:property|name)="' + k + r'"[^>]+content="([^"]*)"', s) or re.search(r'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="' + k + '"', s)
        print(f"{k}: {html.unescape(m.group(1)) if m else '-'}")
    m = re.search(r'<time[^>]*datetime="([^"]+)"', s)
    print("time 标签:", m.group(1) if m else "-")
    ps = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", p))).strip() for p in re.findall(r"<p[^>]*>(.*?)</p>", s, re.S)]
    body = "\n".join(p for p in ps if len(p) > 40)
    print("--- 正文（只取段落文字）---\n" + (body[:limit] or "（没取到段落文字，这个页面可能需要浏览器才能显示内容）"))


def save():
    # 从标准输入读整份稿子（JSON），校验后写入 issues/日期.json
    text = sys.stdin.read()
    try:
        d = json.loads(text)
    except json.JSONDecodeError as e:
        sys.exit(f"不是合法的 JSON，没有保存：{e}")
    miss = [k for k in ("date", "date_cn", "edition", "collected_at", "window", "tags", "top3", "posts", "repos", "takeaways", "footer_note") if k not in d]
    if miss:
        sys.exit(f"缺少字段 {miss}，没有保存。")
    if d["date"] != DATE:
        sys.exit(f"稿子里的 date 是 {d['date']}，和处理日期 {DATE} 不一致，没有保存。")
    p = ROOT / "issues" / f"{DATE}.json"
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已保存 {p}｜资讯 {len(d['posts'])} 条 + GitHub {len(d['repos'])} 个")


def log():
    p = ROOT / "logs" / "run-log.md"
    p.parent.mkdir(exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(f"- {datetime.now(TZ):%Y-%m-%d %H:%M} | {DATE} | {' '.join(rest)}\n")
    print("已记录。")


if cmd == "status":
    status()
elif cmd == "collect":
    collect()
elif cmd == "full":
    sys.exit(py("digest.py", DATE, "--full", *rest))
elif cmd == "search":
    search()
elif cmd == "fetch":
    fetch()
elif cmd == "save":
    save()
elif cmd == "build":
    sys.exit(py("build.py", DATE))
elif cmd == "publish":
    sys.exit(py("publish.py", DATE))
elif cmd == "push":
    sys.exit(py("push_bark.py", DATE, *[a for a in rest if a in ("--send", "--force")]))
elif cmd == "log":
    log()
else:
    sys.exit(__doc__)

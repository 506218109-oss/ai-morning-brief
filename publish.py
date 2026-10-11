"""AI 日报 · 发布到 GitHub Pages（手机在任何网络下都能打开）
改写自 WorkBuddy 版 publish.py，沿用同一个仓库和文件结构：
  index.html                往期列表
  latest.html               最新一期
  ai-brief-YYYY-MM-DD.html  每期归档
怎么跑：python3 publish.py 2026-10-10            → 发布并等网页生效
       python3 publish.py 2026-10-10 --dry-run  → 只在本地准备，不推送
和旧版的区别：先把线上已有内容拉下来再追加，不强制覆盖，往期不会丢。
推送用 gh 已登录的凭据，不改全局 git 配置，不保存任何 token。
"""
import json, re, subprocess, sys, time, urllib.request
from html import escape, unescape
from pathlib import Path

ROOT = Path(__file__).parent
PAGES = ROOT / "work" / "pages"
import settings
REMOTE = settings.need("pages_remote")                    # 发布到哪个仓库（在 config/local.json 里配）
BRANCH = settings.load().get("pages_branch", "gh-pages")
SITE = settings.need("site_url").rstrip("/")              # 网页地址
GIT = ["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]


def run(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and r.returncode:
        sys.exit(f"命令失败：{' '.join(cmd[-4:])}\n{r.stderr.strip()[:500]}")
    return r


def ensure_repo():
    # 第一次：把线上的 gh-pages 分支完整拉下来；以后每次先同步
    if not (PAGES / ".git").is_dir():
        PAGES.parent.mkdir(parents=True, exist_ok=True)
        run(GIT + ["clone", "-q", "--branch", BRANCH, "--single-branch", REMOTE, str(PAGES)])
    else:
        run(GIT + ["pull", "-q", "--ff-only", "origin", BRANCH], PAGES)
    # 提交署名用机器人身份，不暴露个人邮箱
    run(["git", "config", "user.name", "ai-brief-bot"], PAGES)
    run(["git", "config", "user.email", "ai-brief-bot@users.noreply.github.com"], PAGES)


def old_headlines():
    # 从线上现有的往期列表里，读出每一期原来的 3 条标题，保持不变
    idx = PAGES / "index.html"
    out = {}
    if idx.is_file():
        for day, body in re.findall(r'<a class="item" href="ai-brief-(\d{4}-\d{2}-\d{2})\.html">(.*?)</a>', idx.read_text(encoding="utf-8"), re.S):
            out[day] = [unescape(h) for h in re.findall(r'<p class="h">(.*?)</p>', body, re.S)]
    return out


INDEX_CSS = """
:root{--ink:#141821;--paper:#F4F1EA;--card:#fff;--line:#E6E1D6;--muted:#6B7280;--teal:#0F766E}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;font-size:16px;line-height:1.7}
.wrap{max-width:720px;margin:0 auto;padding:20px 14px 64px}
.hero{background:#161A23;color:#fff;border-radius:20px;padding:26px 22px}
.hero .eyebrow{font-size:11px;letter-spacing:.2em;font-weight:600;color:#F2C14E;text-transform:uppercase}
.hero h1{margin:8px 0 6px;font-size:32px;line-height:1.1}
.hero p{margin:0;color:#C7CDD8;font-size:14px}
h2{font-size:18px;margin:26px 0 12px}
.item{display:block;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:10px;text-decoration:none;color:inherit}
.item .d{font-size:12.5px;color:var(--muted);margin-bottom:6px}
.item .h{font-size:15px;font-weight:600;margin:0 0 4px;line-height:1.5}
.item .h:last-child{margin-bottom:0}
.badge{display:inline-block;font-size:11.5px;font-weight:600;color:#0F766E;background:#DFF5EF;padding:2px 9px;border-radius:999px;margin-left:8px}
"""


def build_index(heads):
    days = sorted((p.name[len("ai-brief-"):-len(".html")] for p in PAGES.glob("ai-brief-*.html")), reverse=True)
    blocks = []
    for i, day in enumerate(days):
        latest = '<span class="badge">最新</span>' if i == 0 else ""
        body = "".join(f'<p class="h">{escape(h)}</p>' for h in heads.get(day, [])) or '<p class="h">（本期摘要缺失）</p>'
        blocks.append(f'<a class="item" href="ai-brief-{day}.html"><div class="d">{day}{latest}</div>{body}</a>')
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>AI 早报 · 往期</title>
<style>{INDEX_CSS}</style></head><body><main class="wrap">
<header class="hero"><div class="eyebrow">Daily AI Brief</div><h1>AI 早报</h1>
<p>每天一份，挑出真正值得知道的 AI 动向。点击任意一期即可阅读。</p></header>
<h2>往期日报</h2>
{''.join(blocks)}
</main></body></html>
"""


def wait_live(name, expect, minutes=6):
    # 推送后 GitHub 要一两分钟才生效；等线上内容和本地一致再返回，避免通知点开是旧页面
    for i in range(minutes * 6):
        try:
            req = urllib.request.Request(f"{SITE}/{name}?t={int(time.time())}", headers={"Cache-Control": "no-cache"})
            if urllib.request.urlopen(req, timeout=15).read() == expect:
                return True
        except Exception:
            pass
        time.sleep(10)
    return False


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("用法：python3 publish.py YYYY-MM-DD [--dry-run]")
    day, dry = args[0], "--dry-run" in sys.argv
    src = ROOT / "outputs" / f"ai-brief-{day}.html"
    issue = ROOT / "issues" / f"{day}.json"
    if not src.is_file() or not issue.is_file():
        sys.exit(f"找不到 {src.name} 或 {issue.name}，无法发布。")
    ensure_repo()
    heads = old_headlines()
    heads[day] = [a.rstrip("。") for a, _ in json.loads(issue.read_text(encoding="utf-8"))["top3"]]
    (PAGES / src.name).write_bytes(src.read_bytes())
    newest = sorted(p.name for p in PAGES.glob("ai-brief-*.html"))[-1]
    (PAGES / "latest.html").write_bytes((PAGES / newest).read_bytes())   # latest 永远指向日期最新的一期
    (PAGES / "index.html").write_text(build_index(heads), encoding="utf-8")
    (PAGES / ".nojekyll").write_text("", encoding="utf-8")
    run(["git", "add", "-A"], PAGES)
    changed = bool(run(["git", "status", "--porcelain"], PAGES).stdout.strip())
    if changed:
        run(["git", "commit", "-q", "-m", f"brief: {day}"], PAGES)
    if dry:
        print(json.dumps({"published": False, "reason": "dry-run", "changed": changed, "files": sorted(p.name for p in PAGES.glob("*.html"))}, ensure_ascii=False))
        sys.exit(0)
    err = None
    for attempt in range(3):   # 网络失败自动重试 3 次（不强制覆盖）
        r = run(GIT + ["push", "-q", "origin", f"HEAD:refs/heads/{BRANCH}"], PAGES, check=False)
        if r.returncode == 0:
            err = None
            break
        err = r.stderr.strip()[:400]
        time.sleep(5 * (attempt + 1))
    if err:
        sys.exit(f"推送失败（已重试 3 次）：{err}")
    live = wait_live(src.name, src.read_bytes())
    print(json.dumps({"published": True, "live": live, "day": day, "changed": changed,
                      "url": f"{SITE}/{src.name}", "index": f"{SITE}/"}, ensure_ascii=False))
    if not live:
        sys.exit("已推送，但 6 分钟内线上页面还没更新。先不要发通知，稍后再查。")

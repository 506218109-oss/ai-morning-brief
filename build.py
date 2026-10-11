"""AI 日报 · 生成 HTML
输入：issues/日期.json（当期选题与文案）+ template/style.css（9/10 版样式 + 版式修正）
输出：outputs/ai-brief-日期.html（config/local.json 里配了 copy_to 的话，再另存一份到那里）
怎么跑：python3 build.py 2026-10-09
生成后自动检查：标签闭合、无 <script>、条数上限、单平台不超过 3 条、链接都是 http(s)。
"""
import json, shutil, sys
from collections import Counter
from html import escape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parent
DATE = sys.argv[1]
d = json.loads((ROOT / "issues" / f"{DATE}.json").read_text(encoding="utf-8"))
css = (ROOT / "template" / "style.css").read_text(encoding="utf-8")
e = lambda s: escape(str(s))


def grid_class(n):
    # 正好 3 张：3 列单排；奇数张（5、7、9…）：前面 2 列，最后 3 张合成一行 3 列；偶数张：2 列
    return "grid cols-3" if n == 3 else ("grid six" if n % 2 and n > 3 else "grid")


def card_class(i, n):
    return "card third" if n % 2 and n > 3 and i >= n - 3 else "card"


def card(cls, cid, head, more):
    # 手机上：默认只显示 head（来源 + 标题），点一下展开 more；电脑上 more 一直显示。
    # 用隐藏的勾选框 + label 实现展开/收起，纯 CSS，不需要脚本。
    # --ord / --ord-open：手机上的排列序号。展开时用 --ord-open 排到前一张之前，卡片就在被点的那一行原地展开。
    # 注意：变量名不能叫 --x，会和 style.css 里 X 平台徽标的颜色变量 --x 撞名。
    i = int(cid[1:])
    return f'''
        <article class="{cls}" id="a{cid}" style="--ord:{2 * i};--ord-open:{2 * i - 3}">
          <input type="checkbox" class="tg" id="c{cid}" hidden>{head}
          <label class="toggle" for="c{cid}"><span class="t-open">展开 ▾</span><span class="t-close">收起 ▴</span></label>
          <div class="more">{more}
            <a class="toggle-bottom" href="#a{cid}">↑ 回到本条开头</a>
          </div>
        </article>'''


def post_card(p, cls, cid):
    head = f'''
          <div class="card-top"><span class="badge {e(p["badge"])}">{e(p["platform"])}</span><span class="meta">{e(p["metrics"])}</span></div>
          <h3>{e(p["title"])}</h3>
          <p class="author">{e(p["author"])} · {e(p["time"])}</p>'''
    more = f'''
            <p class="summary-text">{e(p["summary"])}</p>
            <div class="discussion"><strong>讨论点：</strong>{e(p["discussion"])}</div>
            {f'<p class="impact"><strong>对运营/内容人：</strong>{e(p["impact"])}</p>' if p.get("impact") else ""}
            <a class="link" href="{escape(p["link"], quote=True)}" target="_blank" rel="noopener noreferrer">{e(p["link_text"])} →</a>'''
    return card(cls, cid, head, more)


def repo_card(r, cls, cid):
    head = f'''
          <div class="card-top"><span class="badge github">GitHub</span><span class="meta">{e(r["stars"])}</span></div>
          <h3>{e(r["name"])}</h3>
          <p class="author">{e(r["lang"])}</p>
          <p class="tagline">{e(r["desc"])}</p>'''
    more = f'''
            <p class="summary-text">{e(r["desc"])}</p>
            <div class="discussion"><strong>为什么值得看：</strong>{e(r["why"])}</div>
            {f'<p class="impact"><strong>对运营/内容人：</strong>{e(r["impact"])}</p>' if r.get("impact") else ""}
            <a class="link" href="{escape(r["link"], quote=True)}" target="_blank" rel="noopener noreferrer">打开项目 →</a>'''
    return card(cls, cid, head, more)


posts, repos = d["posts"], d["repos"]
plat = Counter(p["platform"] for p in posts)
plat_line = " · ".join(f"{k} {v}" for k, v in plat.items())
page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI 早报 · {e(DATE)}</title>
  <style>
{css}
  </style>
</head>
<body>
  <main class="page">
    <header class="hero">
      <div class="eyebrow">DAILY AI BRIEF · {e(d["edition"])}</div>
      <h1>AI 早报</h1>
      <p class="date">{e(d["date_cn"])}</p>
      <p class="lead">给不懂技术、但想跟上 AI 的人：今天大家主要在聊什么，以及这些变化为什么值得关心。</p>
      <div class="hero-tags">{"".join(f"<span>{e(t)}</span>" for t in d["tags"])}</div>
    </header>

    <section class="summary">
      <h2>今天先看这 3 件事</h2>
      <ol>
{"".join(f"        <li><strong>{e(a)}</strong> {e(b)}</li>" + chr(10) for a, b in d["top3"])}      </ol>
    </section>

    <section>
      <div class="section-head"><h2>平台热帖</h2><span>{len(posts)} 条 · {e(plat_line)}</span></div>
      <div class="{grid_class(len(posts))}">{"".join(post_card(p, card_class(i, len(posts)), f"p{i}") for i, p in enumerate(posts))}
      </div>
    </section>

    <section>
      <div class="section-head"><h2>GitHub 新鲜项目</h2><span>{len(repos)} 个 · 今日 Trending</span></div>
      <div class="{grid_class(len(repos))}">{"".join(repo_card(r, card_class(i, len(repos)), f"r{i}") for i, r in enumerate(repos))}
      </div>
    </section>

    <section class="takeaway">
      <h2>今日观察</h2>
      <div class="takeaway-grid">
{"".join(f'        <div class="takeaway-item"><span>{i:02d}</span><p><strong>{e(a)}</strong> {e(b)}</p></div>' + chr(10) for i, (a, b) in enumerate(d["takeaways"], 1))}      </div>
    </section>

    <footer>
      <p>数据采集时间：{e(d["collected_at"])} · 时间窗口：{e(d["window"])}</p>
      <p>说明：{e(d["footer_note"])}</p>
    </footer>
  </main>
</body>
</html>
'''


# ---- 自动检查：任何一项不过就报错退出，不产出半成品 ----
class Checker(HTMLParser):
    VOID = {"meta", "link", "br", "img", "hr", "input"}
    def __init__(self):
        super().__init__(); self.stack, self.errors = [], []
    def handle_starttag(self, t, a):
        if t not in self.VOID: self.stack.append(t)
    def handle_endtag(self, t):
        if t in self.VOID: return
        if not self.stack or self.stack[-1] != t: self.errors.append(f"</{t}> 不匹配")
        else: self.stack.pop()

c = Checker(); c.feed(page); c.close()
problems = c.errors + ([f"未闭合: {c.stack}"] if c.stack else [])
if "<script" in page: problems.append("含 <script>")
import re as _re
_ids = _re.findall(r'<input type="checkbox" class="tg" id="(c[pr]\d+)" hidden>', page)
_fors = _re.findall(r'<label class="toggle" for="(c[pr]\d+)">', page)
_arts = _re.findall(r'<article class="card[^"]*" id="a([pr]\d+)" style="--ord:\d+;--ord-open:-?\d+">', page)
_backs = _re.findall(r'<a class="toggle-bottom" href="#a([pr]\d+)">', page)
_n = len(posts) + len(repos)
if not (len(_ids) == len(set(_ids)) == _n and _ids == _fors and ["c" + x for x in _arts] == _ids and _arts == _backs):
    problems.append(f"卡片的展开/收起结构不完整（应有 {_n} 张：勾选框 {len(_ids)}、展开按钮 {len(_fors)}、卡片 {len(_arts)}、回到开头 {len(_backs)}）")
if len(posts) + len(repos) > 15: problems.append(f"总条数 {len(posts) + len(repos)} > 15")
if not 3 <= len(repos) <= 5: problems.append(f"GitHub 项目 {len(repos)} 个，应为 3–5")
problems += [f"{k} 有 {v} 条 > 3" for k, v in plat.items() if v > 3]
problems += [f"缺少“对运营/内容人”: {x.get('title', x.get('name'))}" for x in posts + repos if not x.get("impact")]
problems += [f"链接异常: {x['link']}" for x in posts + repos if not x["link"].startswith(("http://", "https://"))]
if problems:
    sys.exit("检查未通过：" + "；".join(problems))

out = ROOT / "outputs" / f"ai-brief-{DATE}.html"
out.parent.mkdir(exist_ok=True)
out.write_text(page, encoding="utf-8")
print(f"检查通过 · {len(posts)} 条资讯 + {len(repos)} 个项目 · {plat_line}\n{out}")
import settings
copy_to = settings.load().get("copy_to")   # 可选：成品另存一份（比如放到自己习惯的文稿文件夹）
if copy_to:
    copy = Path(copy_to.replace("{date}", DATE)).expanduser()
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(out, copy)
    print(copy)

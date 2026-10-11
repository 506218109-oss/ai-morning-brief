// AI 日报 · 采集（需要浏览器登录态的部分）：X、微博、知乎热榜
// 只读：不点赞、不发帖、不私信。用的是 Ego Lite 里用户已登录的账号。
// 怎么跑：python3 run.py collect
const fs = await import("node:fs/promises");
const path = await import("node:path");
// 项目目录由 run.py 在脚本开头注入（ego-browser 里的脚本读不到环境变量，也不知道自己在哪个目录）
const ROOT = globalThis.__AIDAILY_ROOT;
if (!ROOT) throw new Error("请用 python3 run.py collect 运行（需要它注入项目目录）");
const cfg = JSON.parse(await fs.readFile(`${ROOT}/sources.json`, "utf8"));
const now = new Date();
const since = new Date(now.getTime() - cfg.window_hours * 3600e3);
// 注意：ego-browser 里的脚本读不到环境变量。指定日期由 run.py 在脚本开头注入 globalThis.__AIDAILY_DATE；没注入就用今天（北京时间）
const DATE = globalThis.__AIDAILY_DATE || new Date(now.getTime() + 8 * 3600e3).toISOString().slice(0, 10);
const task = await taskSpace(`AI日报采集 ${DATE}`);
const t0 = Date.now();
const lap = (label) => console.log(`[${((Date.now() - t0) / 1000).toFixed(0)}s] ${label}`);
const page = task.page("p1");
const result = { collected_at: now.toISOString(), since: since.toISOString(), x: {}, weibo: {}, zhihu_hot: [], errors: {} };
const sleep = (ms) => page.waitForTimeout(ms);

// ---- X：逐个打开账号主页，取 24 小时内的帖子 ----
for (const h of cfg.x_accounts) {
  try {
    await page.goto(`https://x.com/${h}`, { timeout: 30000 });
    await page.waitForSelector("article", { timeout: 20000 });
    await sleep(2000);
    const seen = new Map();
    for (let i = 0; i < 3; i++) {   // 滚动 3 次，多加载几条
      const rows = await page.evaluate(() => [...document.querySelectorAll("article")].map((a) => {
        const t = a.querySelector("time");
        return {
          time: t?.getAttribute("datetime"), link: t?.closest("a")?.href,
          social: a.querySelector('[data-testid="socialContext"]')?.innerText || "",
          author: a.querySelector('[data-testid="User-Name"]')?.innerText?.split("\n")[0] || "",
          metrics: a.querySelector('[role="group"]')?.getAttribute("aria-label") || "",
          text: a.querySelector('[data-testid="tweetText"]')?.innerText || "",
        };
      }));
      rows.forEach((r) => r.link && seen.set(r.link, r));
      await page.evaluate(() => window.scrollBy(0, 2500));   // 让页面自己滚动，不依赖鼠标动画，窗口在后台也一样快
      await sleep(1500);
    }
    result.x[h] = [...seen.values()].filter((r) => r.time && new Date(r.time) >= since && !/置顶|Pinned/.test(r.social));
  } catch (e) { result.errors[`x:${h}`] = String(e).slice(0, 200); }
  await sleep(1500);
}
lap(`X 完成（${cfg.x_accounts.length} 个账号）`);

if (cfg.x_accounts.every((h) => result.errors[`x:${h}`])) result.errors["x:全部"] = "所有 X 账号都没抓到，可能掉登录或 Ego Lite 没开";
// ---- 微博：手机版接口（需登录态），长文再取全文 ----
await page.goto("https://m.weibo.cn/", { timeout: 30000 });
for (const [name, uid] of Object.entries(cfg.weibo_users)) {
  try {
    const r = await page.fetch(`/api/container/getIndex?containerid=107603${uid}`, { timeout: 15000 });
    const cards = (JSON.parse(r.body)?.data?.cards || []).filter((c) => c.mblog);
    if (!cards.length) result.errors[`weibo:${name}`] = "接口没返回任何微博，可能掉登录或被限流";
    const posts = [];
    for (const c of cards) {
      const m = c.mblog;
      if (new Date(m.created_at) < since || m.isTop) continue;
      let text = m.text.replace(/<br\s*\/?>/g, "\n").replace(/<[^>]+>/g, "");
      if (m.isLongText) {
        try { const ex = await page.fetch(`/statuses/extend?id=${m.id}`, { timeout: 15000 }); text = JSON.parse(ex.body).data.longTextContent.replace(/<br\s*\/?>/g, "\n").replace(/<[^>]+>/g, ""); } catch {}
      }
      posts.push({ time: new Date(m.created_at).toISOString(), author: name, text, reposts: m.reposts_count, comments: m.comments_count, likes: m.attitudes_count,
        retweet_of: m.retweeted_status ? `${m.retweeted_status.user?.screen_name}: ${m.retweeted_status.text.replace(/<[^>]+>/g, "").slice(0, 200)}` : null,
        link: `https://m.weibo.cn/status/${m.id}` });
    }
    result.weibo[name] = posts;
  } catch (e) { result.errors[`weibo:${name}`] = String(e).slice(0, 200); }
  await sleep(1200);
}

lap(`微博完成（${Object.keys(cfg.weibo_users).length} 位博主）`);
// ---- 知乎热榜：只留 AI 相关 ----
try {
  await page.goto("https://www.zhihu.com/hot", { timeout: 30000 });
  await page.waitForSelector(".HotItem", { timeout: 20000 });
  const hot = await page.evaluate(() => [...document.querySelectorAll(".HotItem")].map((x, i) => ({
    rank: i + 1, title: x.querySelector(".HotItem-title")?.innerText, excerpt: x.querySelector(".HotItem-excerpt")?.innerText || "",
    link: x.querySelector(".HotItem-content a")?.href, heat: (x.querySelector(".HotItem-metrics")?.innerText || "").split("\n")[0] })));
  result.zhihu_hot = hot.filter((h) => /AI|人工智能|大模型|模型|GPT|Claude|DeepSeek|OpenAI|Anthropic|智能体|Agent|算力|芯片|英伟达|机器人|豆包|Kimi|通义|元宝|Gemini/i.test(`${h.title} ${h.excerpt}`));
} catch (e) { result.errors.zhihu = String(e).slice(0, 200); }

lap("知乎完成");
const out = `${ROOT}/raw/${DATE}/browser.json`;
await fs.mkdir(path.dirname(out), { recursive: true });
await fs.writeFile(out, JSON.stringify(result, null, 1));
const count = (o) => Object.values(o).reduce((a, v) => a + v.length, 0);
console.log(out, { x: count(result.x), weibo: count(result.weibo), zhihu_hot: result.zhihu_hot.length }, "errors:", Object.keys(result.errors).length ? result.errors : "无");
await task.finish({ keep: [] });

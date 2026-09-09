# AI Morning Brief

A daily, non-technical AI briefing generator built around Codex automations, a clean HTML report, and optional Bark push notifications.

See [SECURITY.md](SECURITY.md) for the public-release security and privacy policy.

[中文说明](#中文说明)

---

## English

### Overview

AI Morning Brief collects recent AI-related discussions from Chinese and global platforms, turns them into a concise HTML report, and can push a short notification to an iPhone through Bark.

The project is designed for readers who want to follow AI news without needing a technical background. It prioritizes discussion points, controversies, trends, AIGC topics, AI products, Agent tools, and startup/funding news.

### Features

- Collects content from Jike, Zhihu, Twitter/X, Xiaohongshu, and Weibo.
- Selects around 10 posts, with no more than 3 posts per platform.
- Adds 3-5 trending, popular, or newly released GitHub projects.
- Produces a standalone, mobile-friendly HTML report.
- Sends a short Bark notification with a clickable link to the report.
- Supports a primary scheduled run and a later fallback run.
- Keeps the report readable for non-technical readers.
- Avoids marketing accounts, duplicate news, and pure advertisements.

### How it works

1. A Codex automation runs on a daily schedule.
2. The agent gathers recent public content from the configured platforms.
3. It writes a standalone HTML report to `outputs/`.
4. The Bark script copies the report into a local public directory.
5. A small local web server serves only that public directory.
6. Bark sends a normal notification with three highlights and a link.
7. Tapping the notification opens the HTML report on the iPhone.

### Requirements

- macOS with the Codex desktop app.
- A Bark iOS app and device key.
- Python 3.
- `curl` and `zsh`.
- The Mac and iPhone should be on the same local network for the clickable report link.

### Configuration

Create the local secret files:

```bash
cp config/bark-key.example.txt config/bark-key.txt
cp config/bark-proxy.example.txt config/bark-proxy.txt
chmod 600 config/bark-key.txt config/bark-proxy.txt
```

Edit `config/bark-key.txt` and put your Bark key there. The proxy file is optional; remove it or leave it empty if you do not use a local proxy.

Test Bark:

```bash
./scripts/send-bark.sh "AI Morning Brief" "Test" "This is a test notification." "https://example.com"
```

Run the local preview server:

```bash
./scripts/run-preview-server.sh
```

The server serves only the `public/` directory, not the repository root.

### Automation

Use `docs/automation-prompt.md` as a reference prompt for the Codex automation. Replace `<PROJECT_ROOT>` with the absolute path to this repository.

The recommended schedule is:

- Primary run: 12:00 local time.
- Fallback check: 14:00 local time.
- If today's report was already sent, stay silent.
- If the Mac is off or asleep at both times, no report is generated.

### Security Notes

Do not commit:

- Bark keys.
- GitHub tokens or credentials.
- Local proxy configuration.
- Personal file paths.
- Local IP addresses.
- Logs.
- Private configuration files.

The public server should serve only generated HTML reports. It must not serve the repository root.

### Limitations

- The Mac must be powered on and Codex must be running when the scheduled task executes.
- The clickable HTML link requires the iPhone and Mac to be on the same local network.
- If the Mac is off or asleep at both scheduled times, the daily report is skipped.
- Some platforms may require login or block automated access. The report should note unavailable sources instead of inventing data.

---

## 中文说明

### 项目简介

AI 早报是一个基于 Codex 自动化、HTML 报告和 Bark 推送的每日 AI 简报工具。

公开发布的安全与隐私说明见 [SECURITY.md](SECURITY.md)。

它会从即刻、知乎、Twitter/X、小红书、微博等平台收集近期 AI 讨论，整理成适合非技术读者阅读的 HTML 报告，并可以通过 Bark 向 iPhone 推送简短提醒。

内容重点包括 AI 技术、Agent 开发工具、AI 产品、创业融资、AIGC 和讨论度较高的观点。

### 主要功能

- 从即刻、知乎、Twitter/X、小红书、微博收集内容。
- 每天筛选约 10 条帖子，每个平台最多 3 条。
- 附加 3-5 个 GitHub 热门、流行或新发布项目。
- 生成独立、移动端友好的 HTML 报告。
- 通过 Bark 推送三条摘要和报告链接。
- 支持 12:00 主发送和 14:00 兜底检查。
- 面向不懂技术的读者，减少营销号和重复新闻。
- 不编造数据；平台无法访问时会注明。

### 工作流程

1. Codex 自动化按计划运行。
2. 从各平台收集最近的公开内容。
3. 生成 HTML 报告到 `outputs/`。
4. Bark 脚本把报告复制到本地公开目录。
5. 本地预览服务只提供该公开目录中的 HTML。
6. Bark 发送正常提醒，包含三条摘要和链接。
7. 点击通知后，在 iPhone 上打开 HTML 报告。

### 环境要求

- macOS 和 Codex 桌面应用。
- Bark iOS App 和设备 Key。
- Python 3。
- `curl` 和 `zsh`。
- 点击 HTML 链接时，Mac 和 iPhone 应在同一个局域网内。

### 配置方法

创建本地密钥文件：

```bash
cp config/bark-key.example.txt config/bark-key.txt
cp config/bark-proxy.example.txt config/bark-proxy.txt
chmod 600 config/bark-key.txt config/bark-proxy.txt
```

在 `config/bark-key.txt` 中填入你的 Bark Key。代理配置是可选的，不使用本地代理时可以删除或留空。

测试 Bark：

```bash
./scripts/send-bark.sh "AI 早报" "测试" "这是一条测试通知。" "https://example.com"
```

启动本地预览服务：

```bash
./scripts/run-preview-server.sh
```

该服务只提供 `public/` 目录，不会暴露整个项目目录。

### 自动化配置

请参考 `docs/automation-prompt.md`。把其中的 `<PROJECT_ROOT>` 替换成你本机的项目绝对路径。

推荐时间安排：

- 12:00 主发送。
- 14:00 兜底检查。
- 如果当天已经发送过，则静默跳过。
- 如果两个时间点电脑都没有开机，则当天不生成报告。

### 安全说明

不要提交：

- Bark Key。
- GitHub Token 或账号凭证。
- 本地代理配置。
- 个人文件路径。
- 本地 IP 地址。
- 日志。
- 私有配置文件。

本地预览服务只应提供生成的 HTML 报告，不能提供整个项目目录。

### 使用限制

- 定时任务执行时，Mac 必须开机且 Codex 正在运行。
- 点击 HTML 链接需要 iPhone 和 Mac 在同一个局域网内。
- 如果两个计划时间点电脑都没有开机，当天报告会被跳过。
- 部分平台可能需要登录或会限制自动化访问。遇到这种情况时应注明来源不可用，而不是编造内容。

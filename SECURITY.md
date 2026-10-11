# 安全与隐私 · Security & Privacy

## 仓库里没有什么

- 没有任何密钥：Bark 设备 Key 只放在本机的 `config/bark-key.txt`（已在 `.gitignore` 里，脚本要求它是仅本人可读的文件，并且不会把它打印到命令行、网址或日志里）。
- 没有账号信息：X、微博、知乎的登录状态只存在本机浏览器里，脚本不读取、不保存任何密码或 Cookie 文件。
- 没有采集到的原始数据：`raw/` 里是别人的帖子，不进仓库。
- 没有本机路径和个人配置：都在 `config/local.json`（不进仓库）。

## 脚本会做什么、不会做什么

- 只读：对 X、微博、知乎只读取公开帖子，不点赞、不发帖、不关注、不私信。
- 只往两个地方写：本机的项目目录，以及你在 `config/local.json` 里配置的 GitHub Pages 仓库。
- 遇到付费墙、登录墙、验证码不绕过。

## 发现问题

如果你发现仓库里不小心包含了敏感信息，或脚本有安全问题，请在 GitHub 上提 Issue（不要在 Issue 里贴出敏感内容本身）。

---

**English summary.** This repository contains no keys, no account data, no collected raw posts, and no machine-specific paths. The Bark device key lives only in a local, git-ignored file with owner-only permissions and is never printed or placed in a URL or log. The scripts read public posts only (no likes, posts, follows, or messages), write only to the project folder and the GitHub Pages repository you configure, and never bypass paywalls, login walls, or CAPTCHAs. If you find sensitive data or a security problem, please open an issue without pasting the sensitive content itself.

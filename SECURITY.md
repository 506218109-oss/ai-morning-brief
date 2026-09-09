# Security and Privacy / 安全与隐私

## English

This repository is intended to be safe for public release.

The following items are intentionally excluded:

- Bark device keys or push credentials.
- GitHub tokens or account credentials.
- Local proxy configuration.
- Personal file paths.
- Local IP addresses or hostnames.
- Runtime logs.
- Private Codex configuration files.
- Any other local or device-specific information.

The included Bark scripts read credentials from local files or environment variables. They do not contain real credentials.

The local preview server should serve only generated HTML reports. It must not serve the repository root.

## 中文

这个仓库用于公开发布，已刻意排除以下内容：

- Bark 设备 Key 或推送凭证。
- GitHub Token 或账号凭证。
- 本地代理配置。
- 个人文件路径。
- 本地 IP 地址或主机名。
- 运行时日志。
- Codex 私有配置文件。
- 其他本机或设备相关信息。

仓库中的 Bark 脚本只从本地文件或环境变量读取凭证，不包含真实 Key。

本地预览服务只应提供生成的 HTML 报告，不能提供整个仓库目录。

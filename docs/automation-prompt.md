# Codex Automation Prompt

This is a sanitized reference prompt for the daily AI briefing automation. Replace `<PROJECT_ROOT>` with the absolute path to this repository on your machine.

```text
Every day, generate a Chinese AI morning brief and send it to the current task. Before each run, check whether today's brief has already been generated and sent. If it has, stay silent and do not duplicate it. If it has not, generate it normally.

Use recent public content from Jike, Zhihu, Twitter/X, Xiaohongshu, and Weibo, prioritizing posts from the last 24-48 hours with high engagement or active discussion. Select about 10 posts, with no more than 3 posts per platform. Avoid marketing accounts, pure advertisements, and duplicate news. The total number of items, including GitHub projects, must not exceed 15.

Prefer AI technology, Agent development tools, AI products, startup funding, and practical industry developments. Write for a non-technical reader. Avoid deep technical implementation details. Explain the main argument, controversy, trend, and practical impact. Increase the weight of AIGC topics and viewpoints with active discussion.

Each post should include the platform, author, publication time, a short Chinese summary, the main discussion point or controversy, visible engagement metrics when available, and the original link. Add 3-5 trending, popular, or newly released GitHub projects, including the project name, one-line purpose, language/domain, stars or trend evidence, link, and why it is worth watching.

Create a clean, mobile-friendly standalone HTML report at:
<PROJECT_ROOT>/outputs/ai-morning-brief-YYYY-MM-DD.html

The HTML should include the date, sections, and clickable links. Do not depend on external JavaScript. After generating the report, send a short summary and the HTML file link in the current task. Then run:
<PROJECT_ROOT>/scripts/send-daily-brief-bark.sh "YYYY-MM-DD" "Highlight 1" "Highlight 2" "Highlight 3"

The script copies the HTML to the public preview directory and sends a Bark notification that opens the report when tapped. If Bark delivery fails, do not regenerate the report; only report the failure in the current task. Never print or expose the Bark key. Do not fabricate data. If a platform is unavailable, note that and compensate with other platforms.
```

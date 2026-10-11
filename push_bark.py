"""AI 日报 · 把当天 3 条重点推到手机（Bark）
改写自 WorkBuddy 版 push.py。默认只预览，加 --send 才真的发。
怎么跑：python3 push_bark.py 2026-10-10          → 预览通知内容（不发）
       python3 push_bark.py 2026-10-10 --send   → 发送
       加 --force：忽略时间限制和“已发过”的判断，立刻再发一条
保护措施：
- 密钥只从 config/bark-key.txt 读，只经标准输入进入请求，不出现在命令行、网址或日志里
- 只在北京时间 11:00–22:00 真发，其余时间只记状态，免得半夜吵人
- 同一期内容已经成功发过，就不重复发
"""
import argparse, fcntl, hashlib, json, re, subprocess, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
TZ = timezone(timedelta(hours=8))
KEY_FILE = ROOT / "config" / "bark-key.txt"
import settings
SITE = settings.need("site_url").rstrip("/")   # 网页地址，在 config/local.json 里配
GATE_START, GATE_END = 11, 22
WEEKDAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
LINE_WIDTH, LINE_BREAKS = 30, "，,；;。：:｜|—–"


def friendly_day(day):
    d = date.fromisoformat(day)
    return f"{d.month}/{d.day} {WEEKDAYS[d.weekday()]}"


def width(text):
    return sum(2 if ord(c) > 0x2E80 else 1 for c in text)


def short(text, limit=LINE_WIDTH):
    # 把标题压到通知里一行放得下：优先在标点处断开，断不开再截断加省略号
    text = re.sub(r"\s+", " ", str(text)).strip().rstrip("。")
    if width(text) <= limit:
        return text
    head = ""
    for piece in re.split(rf"(?<=[{re.escape(LINE_BREAKS)}])", text):
        if width(head + piece) > limit:
            break
        head += piece
    if width(head) >= 12:
        return head.rstrip(LINE_BREAKS)
    cut = ""
    for c in text:
        if width(cut + c) > limit - 2:
            break
        cut += c
    return cut + "…"


def save(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("day")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    issue = ROOT / "issues" / f"{a.day}.json"
    if not issue.is_file():
        sys.exit(f"找不到 {issue}，未发送。")
    d = json.loads(issue.read_text(encoding="utf-8"))
    if len(d.get("top3", [])) != 3:
        sys.exit("当期重点不是 3 条，未发送。")
    url = f"{SITE}/ai-brief-{a.day}.html"
    t = [short(x[0]) for x in d["top3"]]
    payload = {"title": f"AI 早报 · {friendly_day(a.day)}",
               "body": "\n".join([f"1. {t[0]}", f"2. {t[1]}", f"3. {t[2]}", f"共 {len(d['posts'])} 条资讯 · {len(d['repos'])} 个开源项目"]),
               "group": "AI早报", "level": "active", "id": f"ai-brief-{a.day}", "url": url}
    if not a.send:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(0)

    if not KEY_FILE.is_file() or KEY_FILE.is_symlink() or (KEY_FILE.stat().st_mode & 0o077):
        sys.exit("密钥文件不存在，或不是仅本人可读的普通文件，未发送。")
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[A-Za-z0-9]+", key):
        sys.exit("密钥文件格式不正确，未发送。")
    fp = hashlib.sha256(issue.read_bytes()).hexdigest()[:16]
    state = ROOT / "state"
    state.mkdir(exist_ok=True)
    receipt = state / f"bark-{a.day}.json"
    rec = {"date": a.day, "url": url, "fingerprint": fp}
    with (state / f"bark-{a.day}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit("已有发送进程在跑，未重复发送。")
        prev = json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else {}
        if not a.force and prev.get("status") == "accepted" and prev.get("fingerprint") == fp:
            print("这一期已经成功推送过，内容没变，不重复发。要强制重发加 --force。")
            sys.exit(0)
        now = datetime.now(TZ)
        if not a.force and not (GATE_START <= now.hour < GATE_END):
            rec.update(status="deferred_window", at=now.isoformat(timespec="seconds"))
            save(receipt, rec)
            print(f"现在 {now:%H:%M}，不在推送时段（{GATE_START}:00–{GATE_END}:00），只记状态不发通知。")
            sys.exit(0)
        if not a.force and prev.get("status") in ("sending", "unknown"):
            sys.exit("上次发送结果不确定，请先看手机有没有收到；不自动重发。")
        rec.update(status="sending", attempted_at=now.isoformat(timespec="seconds"))
        save(receipt, rec)
        payload["device_key"] = key
        cmd = ["curl", "-sS", "--max-time", "20", "--retry", "2", "--retry-delay", "2", "--request", "POST",
               "--header", "Content-Type: application/json", "--data-binary", "@-", "--write-out", "\n%{http_code}",
               "https://api.day.app/push"]
        try:
            r = subprocess.run(cmd, input=json.dumps(payload, ensure_ascii=False), text=True, capture_output=True, timeout=40)
            if r.returncode:
                raise RuntimeError(r.stderr.strip() or f"curl exit {r.returncode}")
            content, status = r.stdout.rsplit("\n", 1)
            code = json.loads(content).get("code")
            rec.update(http_status=int(status), api_code=code)
            if status == "200" and code == 200:
                rec.update(status="accepted", accepted_at=datetime.now(TZ).isoformat(timespec="seconds"))
            elif 400 <= int(status) < 500:
                rec.update(status="failed", error=content.replace(key, "[已隐藏]")[:300])
            else:
                rec.update(status="unknown", error=content.replace(key, "[已隐藏]")[:300])
        except Exception as e:
            rec.update(status="unknown", error=str(e).replace(key, "[已隐藏]")[:300])
        save(receipt, rec)
        if rec["status"] != "accepted":
            sys.exit("推送没有成功：" + json.dumps(rec, ensure_ascii=False))
        print(f"已推送到手机 · {url}")

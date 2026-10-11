"""读取本机配置 config/local.json（这个文件不进仓库，照 config/local.example.json 填）。
放在这里的是“每个人都不一样”的东西：发布到哪个 GitHub Pages 仓库、网页地址、成品要不要另存一份。
没有这个文件也能采集和生成；只是不能发布和推送，脚本会提示缺什么。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load():
    p = ROOT / "config" / "local.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def need(key):
    v = load().get(key)
    if not v:
        raise SystemExit(f"config/local.json 里缺少 {key}。请照 config/local.example.json 新建并填写。")
    return v

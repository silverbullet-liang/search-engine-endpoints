#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 /images/async 返回的 HTML 片段解析成结构化 JSON。

用法:
    python3 parse_images.py fragment.html
    python3 parse_images.py --url 'https://cn.bing.com/images/async?q=%E7%8C%AB&first=1&count=35&mmasync=1'

选项:
    --limit N    只输出前 N 条
    --dedupe K   cid | md5 | murl（默认 md5，跨批次去重更可靠）
    --mark       把 U+E000/U+E001 高亮转成 <mark>…</mark>，默认剥离

零依赖，只用标准库。单次请求、无重试、无并发 —— 见仓库 NOTICE.md 第 3 节。
"""
import argparse
import html
import json
import re
import sys
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

# 片段里每个结果是一个 <a class="iusc" … m="{转义后的 JSON}">
M_ATTR = re.compile(r'\sm="([^"]*)"')
HL_OPEN, HL_CLOSE = "\ue000", "\ue001"

FIELDS = {"cid": "cid", "purl": "page_url", "murl": "image_url",
          "turl": "thumbnail_url", "t": "title", "desc": "desc",
          "md5": "md5", "mid": "mid", "shkey": "shkey"}


def clean(text, mark=False):
    """去掉私有区高亮字符，或把它们换成 <mark>。"""
    if not text:
        return ""
    if mark:
        return text.replace(HL_OPEN, "<mark>").replace(HL_CLOSE, "</mark>")
    return text.replace(HL_OPEN, "").replace(HL_CLOSE, "")


def parse(html_text, mark=False):
    """返回结果列表。解析失败的单条被跳过，不抛异常。"""
    out = []
    for raw in M_ATTR.findall(html_text):
        try:
            data = json.loads(html.unescape(raw))
        except (ValueError, TypeError):
            continue
        if not isinstance(data, dict) or not data.get("cid"):
            continue
        item = {dst: clean(str(data.get(src) or ""), mark) for src, dst in FIELDS.items()}
        out.append(item)
    return out


def dedupe(items, key):
    seen, kept = set(), []
    for it in items:
        k = it.get(key, "")
        if k and k in seen:
            continue
        seen.add(k)
        kept.append(it)
    return kept


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="已保存的片段 HTML")
    ap.add_argument("--url", help="直接请求（单次）")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dedupe", default="md5", choices=["cid", "md5", "murl"])
    ap.add_argument("--mark", action="store_true")
    a = ap.parse_args()

    if a.url:
        text = fetch(a.url)
    elif a.file:
        with open(a.file, encoding="utf-8", errors="replace") as f:
            text = f.read()
    else:
        ap.error("需要 fragment.html 或 --url")
        return

    items = dedupe(parse(text, a.mark), a.dedupe)
    if a.limit:
        items = items[:a.limit]
    json.dump(items, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    print(f"# {len(items)} 条（按 {a.dedupe} 去重）", file=sys.stderr)


if __name__ == "__main__":
    main()

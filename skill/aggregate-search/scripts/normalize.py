#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨引擎合并：规范化去重 + RRF 融合排序。"""
import hashlib
import re
import unicodedata
import urllib.parse

DROP_QUERY = re.compile(r"^(utm_\w+|spm|from|fr|srcid|share_\w+|scene|ref)$", re.I)


def norm_url(u):
    """去掉协议差异、追踪参数、尾斜杠、锚点，用于判重。"""
    if not u:
        return ""
    try:
        p = urllib.parse.urlsplit(u)
    except Exception:
        return u
    qs = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=False)
          if not DROP_QUERY.match(k)]
    netloc = p.netloc.lower().removeprefix("www.")
    path = p.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit(("", netloc, path, urllib.parse.urlencode(sorted(qs)), ""))


def norm_title(t):
    t = unicodedata.normalize("NFKC", t or "")
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"[\s\u200b-\u200f\u202a-\u202e]+", "", t)
    t = re.sub(r"[，,。.、·\-—_|:：;；!！?？\"'“”‘’（）()\[\]【】…~～]+", "", t)
    return t.lower()


def fingerprint(item):
    key = norm_url(item.get("url")) or norm_title(item.get("title")) \
        or item.get("image") or item.get("text") or ""
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def rrf(rank, k=60):
    return 1.0 / (k + rank)


def merge(per_engine, kind, limit=None, k=60):
    """per_engine: {engine_id: [items]}，各引擎内部已按自身顺序排好。

    返回合并后的 items：同一资源（url / 图片地址 / 建议文本）跨引擎合并，
    分数按 RRF 累加，多引擎命中的条目自然上浮。
    """
    buckets = {}
    for eng, items in per_engine.items():
        for i, it in enumerate(items, 1):
            fp = fingerprint(it)
            if not fp:
                continue
            cur = buckets.get(fp)
            if cur is None:
                cur = {"_fp": fp, "_score": 0.0, "_engines": [], "_best_rank": 10 ** 6,
                       "_item": dict(it)}
                buckets[fp] = cur
            # 同一引擎内重复出现（如 360 的累积集合）只计一次分数
            if eng not in cur["_engines"]:
                cur["_score"] += rrf(i, k)
                cur["_engines"].append(eng)
            cur["_best_rank"] = min(cur["_best_rank"], i)
            # 字段补全：空字段用后来的补，不覆盖已有内容
            for f, v in it.items():
                if v not in (None, "", [], {}) and not cur["_item"].get(f):
                    cur["_item"][f] = v
            # 摘要取更长的那个
            if len(str(it.get("snippet") or "")) > len(str(cur["_item"].get("snippet") or "")):
                cur["_item"]["snippet"] = it["snippet"]

    rows = sorted(buckets.values(), key=lambda x: (-x["_score"], x["_best_rank"]))
    if limit:
        rows = rows[:limit]
    out = []
    for n, r in enumerate(rows, 1):
        it = dict(r["_item"])
        it.update({
            "rank": n,
            "score": round(r["_score"], 6),
            "engines": sorted(set(r["_engines"])),
            "engine": r["_engines"][0],
            "type": kind,
        })
        it.pop("_fp", None)
        out.append(it)
    return out

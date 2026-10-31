#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 聚合搜索 —— 多引擎并发、统一 JSON 输出。

用法：
    python3 search.py "量子计算"                        # 网页（神马 + Bing）
    python3 search.py "猫" --kind image --limit 40       # 图片（Bing + 360）
    python3 search.py "Rust 教程" --kind video           # 视频（B站）
    python3 search.py "什么是向量数据库" --kind ai --citations   # AI 搜索（秘塔 SSE）
    python3 search.py "天气" --kind hot                  # 热榜（抖音/B站/神马）
    python3 search.py "量子" --kind suggest              # 联想（百度/360/B站/抖音）
    python3 search.py "量子计算" --kind bundle           # 一次跑 web+image+video+hot
    python3 search.py "猫" --kind image --engines bing,so360 --pages 2 --out r.json
"""
import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import engines  # noqa: E402
from normalize import merge  # noqa: E402

BUNDLE = ["web", "image", "video", "hot"]


def run_one(engine_id, fn, query, kw):
    t0 = time.perf_counter()
    try:
        items = fn(query, **kw) or []
        return engine_id, items, None, int((time.perf_counter() - t0) * 1000)
    except Exception as e:
        detail = f"{type(e).__name__}: {e}"
        if kw.get("debug"):
            detail += "\n" + traceback.format_exc()
        return engine_id, [], detail, int((time.perf_counter() - t0) * 1000)


def aggregate(kind, query, wanted, pages, limit, timeout, debug, citations, fresh):
    table = engines.KINDS[kind]
    ids = wanted or list(table)
    bad = [x for x in ids if x not in table]
    if bad:
        sys.exit(f"[{kind}] 未知引擎: {', '.join(bad)}；可用: {', '.join(table)}")

    kw = {"pages": max(1, pages), "timeout": timeout, "debug": debug}
    per_engine, report = {}, []
    with ThreadPoolExecutor(max_workers=min(8, len(ids))) as pool:
        futs = [pool.submit(run_one, eid, table[eid], query, kw) for eid in ids]
        for f in futs:
            eid, items, err, ms = f.result()
            per_engine[eid] = items
            report.append({"id": eid, "ok": err is None, "count": len(items),
                           "took_ms": ms, "error": err})

    if kind == "ai" and citations:
        for it in per_engine.get("metaso") or []:
            if it.get("resultId"):
                try:
                    it["citations"] = engines.metaso_citations(it["resultId"], timeout=timeout)
                except Exception as e:
                    it["citations_error"] = f"{type(e).__name__}: {e}"

    if fresh:
        items = []
        for eid, its in per_engine.items():
            for n, it in enumerate(its, 1):
                row = dict(it)
                row.update({"engine": eid, "engines": [eid], "rank": n,
                            "score": None, "type": kind})
                items.append(row)
    else:
        items = merge(per_engine, kind, limit=limit or None)
    return items, report


def main():
    ap = argparse.ArgumentParser(description="AI 聚合搜索：多引擎并发 → 统一 JSON")
    ap.add_argument("query", help="检索词")
    ap.add_argument("--kind", default="web",
                    choices=["web", "image", "video", "ai", "suggest", "hot", "bundle"],
                    help="检索类型，默认 web；bundle = web+image+video+hot 一次跑完")
    ap.add_argument("--engines", default="", help="逗号分隔的引擎 id，默认全部")
    ap.add_argument("--pages", type=int, default=1, help="每个引擎取几批（视引擎支持）")
    ap.add_argument("--limit", type=int, default=0, help="每类最多返回多少条，0 = 不截断")
    ap.add_argument("--timeout", type=float, default=15, help="单请求超时秒数")
    ap.add_argument("--citations", action="store_true", help="AI 类型额外拉取引用条目")
    ap.add_argument("--out", default="", help="写入文件（默认打印到 stdout）")
    ap.add_argument("--pretty", action="store_true", help="缩进输出")
    ap.add_argument("--fresh", action="store_true", help="不跨引擎合并，按引擎原样返回")
    ap.add_argument("--debug", action="store_true", help="错误里附带堆栈")
    a = ap.parse_args()

    wanted = [x.strip() for x in a.engines.split(",") if x.strip()]
    t0 = time.perf_counter()

    if a.kind == "bundle":
        groups, report = {}, []
        for k in BUNDLE:
            items, rep = aggregate(k, a.query, wanted, a.pages, a.limit,
                                   a.timeout, a.debug, a.citations, a.fresh)
            groups[k] = items
            for r in rep:
                report.append(dict(r, kind=k, id=f"{k}:{r['id']}"))
        result = {
            "query": a.query, "kind": "bundle",
            "took_ms": int((time.perf_counter() - t0) * 1000),
            "count": sum(len(v) for v in groups.values()),
            "counts": {k: len(v) for k, v in groups.items()},
            "engines": report,
            "groups": groups,
        }
    else:
        items, report = aggregate(a.kind, a.query, wanted, a.pages, a.limit,
                                  a.timeout, a.debug, a.citations, a.fresh)
        result = {
            "query": a.query, "kind": a.kind,
            "took_ms": int((time.perf_counter() - t0) * 1000),
            "count": len(items),
            "engines": report,
            "items": items,
        }

    text = json.dumps(result, ensure_ascii=False, indent=2 if a.pretty else None)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
        ok = [r["id"] for r in report if r["ok"]]
        bad = [f'{r["id"]}({r["error"]})' for r in report if not r["ok"]]
        print(f"{a.query!r} → {result['count']} 条 / {result['took_ms']}ms")
        print(f"成功: {', '.join(ok) or '-'}")
        if bad:
            print(f"失败: {'; '.join(bad)}")
        print(f"已写入 {a.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()

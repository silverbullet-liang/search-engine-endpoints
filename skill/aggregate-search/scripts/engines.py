#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""各引擎适配器。每个函数签名统一：fn(query, **kw) -> list[dict]

只做两件事：发一次请求、把响应拆成统一的最小字段集。
字段映射在各自函数里完成，不在这里做跨引擎合并。
"""
import gzip
import html
import json
import re
import urllib.parse
import urllib.request

DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36")
MOBILE = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/156.0.0.0 Mobile Safari/537.36")

UA = DESKTOP


def fetch(url, *, ua=DESKTOP, headers=None, timeout=12, data=None, cookie=None):
    h = {"User-Agent": ua, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
    if headers:
        h.update(headers)
    if cookie:
        h["Cookie"] = cookie
    req = urllib.request.Request(url, data=data, headers=h,
                                 method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return r.status, dict(r.headers), raw.decode("utf-8", "replace")


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def _q(q):
    return urllib.parse.quote(q, safe="")


# ---------------------------------------------------------------- 网页搜索

def shenma_web(query, pages=1, limit=50, timeout=12, **kw):
    """神马极速版。普通 /s?q= 被 WAF 拒（cloud_ip_bl），/s/lite 不受影响。"""
    out = []
    for page in range(1, min(pages, 5) + 1):
        _, _, body = fetch(f"https://m.sm.cn/s/lite?q={_q(query)}&page={page}",
                           ua=MOBILE, headers={"Referer": "https://m.sm.cn/"}, timeout=timeout)
        # 标题节点是锚点；链接在标题之前（同一个 <a class="qk-link-wrapper"> 内），
        # 摘要与标签在标题之后、下一条标题之前。
        marks = list(re.finditer(r'<div class="qk-title-text qk-font-bold">(.*?)</div>', body, re.S))
        for n, m in enumerate(marks):
            title = strip_tags(m.group(1))
            if not title:
                continue
            head = body[max(0, m.start() - 900):m.start()]
            links = re.findall(r'href="(https?://[^"]+)"', head)
            if not links:
                continue
            url = html.unescape(links[-1])
            if "/adclick" in url or "sm.cn/adclick" in url:      # 广告位
                continue
            tail_end = marks[n + 1].start() if n + 1 < len(marks) else min(len(body), m.end() + 3000)
            tail = body[m.end():tail_end]
            sn = re.search(r'<div class="qk-paragraph-text">(.*?)</div>', tail, re.S)
            tag = re.search(r'<span class="qk-tag[^"]*">(.*?)</span>', tail, re.S)
            out.append({
                "title": title,
                "url": url,
                "snippet": strip_tags(sn.group(1)) if sn else "",
                "site": urllib.parse.urlparse(url).netloc,
                "label": strip_tags(tag.group(1)) if tag else "",
                "date": None,
            })
        if len(out) >= limit:
            break
    return out[:limit]


def bing_web(query, pages=1, limit=10, timeout=12, **kw):
    """Bing 网页。外部客户端只能稳定取第 1 页。"""
    out = []
    _, _, h = fetch(f"https://cn.bing.com/search?q={_q(query)}&first=1&setlang=zh-CN",
                    headers={"Referer": "https://cn.bing.com/"}, timeout=timeout)
    for m in re.finditer(r'<li class="b_algo"(.*?)</li>', h, re.S):
        blk = m.group(1)
        a = re.search(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', blk, re.S)
        if not a:
            continue
        p = re.search(r'<p[^>]*>(.*?)</p>', blk, re.S)
        out.append({
            "title": strip_tags(a.group(2)),
            "url": html.unescape(a.group(1)),
            "snippet": strip_tags(p.group(1)) if p else "",
            "site": urllib.parse.urlparse(html.unescape(a.group(1))).netloc,
            "label": "",
            "date": None,
        })
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- 图片搜索

def bing_images(query, pages=1, limit=100, timeout=12, **kw):
    """Bing 图片。a.iusc 的 m 属性是 JSON；first 为 1-based 起始序号。"""
    out, seen = [], set()
    step = 35
    for i in range(max(1, pages)):
        first = 1 + i * step
        _, _, h = fetch(f"https://cn.bing.com/images/async?q={_q(query)}&first={first}",
                        headers={"Referer": "https://cn.bing.com/images/search?q=" + _q(query)},
                        timeout=timeout)
        for tag in re.findall(r'<a[^>]*class="iusc"[^>]*>', h):
            mm = re.search(r'\sm="([^"]+)"', tag)
            if not mm:
                continue
            try:
                d = json.loads(html.unescape(mm.group(1)))
            except Exception:
                continue
            url = d.get("murl") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            out.append({
                "title": strip_tags(d.get("t", "")),
                "image": url,
                "thumb": d.get("turl") or "",
                "page": d.get("purl") or "",
                "width": None, "height": None,
                "format": url.rsplit(".", 1)[-1].lower()[:5] if "." in url else "",
            })
            if len(out) >= limit:
                return out
    return out


def so360_images(query, pages=1, limit=100, timeout=12, **kw):
    """360 图片 JSON。list 是累积集合，必须按 id 去重。"""
    out, seen = [], set()
    pn = 0
    for _ in range(max(1, pages)):
        _, _, body = fetch(f"https://image.so.com/j?q={_q(query)}&pn={pn}&rn=30", timeout=timeout)
        try:
            data = json.loads(body)
        except Exception:
            break
        batch = data.get("list") or []
        if not batch:
            break
        for it in batch:
            key = it.get("id") or it.get("img")
            if not key or key in seen:
                continue
            seen.add(key)
            img = it.get("img") or it.get("https") or ""
            if not img:
                continue
            out.append({
                "title": strip_tags(it.get("title") or ""),
                "image": img,
                "thumb": it.get("thumb") or "",
                "page": it.get("link") or it.get("purl") or "",
                "width": int(it["width"]) if str(it.get("width", "")).isdigit() else None,
                "height": int(it["height"]) if str(it.get("height", "")).isdigit() else None,
                "format": (it.get("imgtype") or "").lower(),
            })
            if len(out) >= limit:
                return out
        total = data.get("total") or 0
        pn += len(batch)
        if total and pn >= total:
            break
    return out


# ---------------------------------------------------------------- 视频

def bilibili_video(query, pages=1, limit=50, timeout=12, **kw):
    """B站视频搜索。需先取一次 buvid3，否则 412。"""
    _, hdrs, _ = fetch("https://www.bilibili.com/", timeout=timeout)
    cookie = ""
    for k, v in hdrs.items():
        if k.lower() == "set-cookie":
            m = re.search(r"buvid3=([^;]+)", v)
            if m:
                cookie = "buvid3=" + m.group(1)
    if not cookie:
        _, hdrs2, _ = fetch("https://api.bilibili.com/x/frontend/finger/spi", timeout=timeout)
        try:
            cookie = "buvid3=" + json.loads(hdrs2.get("x-body", "{}")).get("data", {}).get("b_3", "")
        except Exception:
            cookie = ""
    out = []
    for page in range(1, max(1, pages) + 1):
        _, _, body = fetch(
            "https://api.bilibili.com/x/web-interface/search/type?search_type=video"
            f"&keyword={_q(query)}&page={page}&page_size=50&order=totalrank",
            headers={"Referer": "https://search.bilibili.com/"}, cookie=cookie, timeout=timeout)
        try:
            data = json.loads(body)
        except Exception:
            break
        res = (data.get("data") or {}).get("result") or []
        for it in res:
            if it.get("type") != "video" or not it.get("bvid"):   # 过滤付费课堂
                continue
            dur = it.get("duration") or ""
            secs = None
            if re.fullmatch(r"\d+:\d+", dur):
                a, b = dur.split(":")
                secs = int(a) * 60 + int(b)
            pic = it.get("pic") or ""
            out.append({
                "title": strip_tags(it.get("title", "")),
                "url": "https://www.bilibili.com/video/" + it["bvid"],
                "cover": ("https:" + pic) if pic.startswith("//") else pic,
                "desc": strip_tags(it.get("description", ""))[:300],
                "author": it.get("author", ""),
                "play": it.get("play"),
                "duration": dur,
                "duration_sec": secs,
                "pubdate": it.get("pubdate"),
                "bvid": it["bvid"],
                # 直链与字幕体积大、且带时效，用二次脚本现取
                "detail": f"python3 scripts/bili_detail.py {it['bvid']} --asr",
            })
            if len(out) >= limit:
                return out
        if not res:
            break
    return out


# ---------------------------------------------------------------- AI 搜索

def metaso_ai(query, timeout=120, **kw):
    """秘塔网页端匿名 SSE。只需要 Cookie tid=<任意 UUID>。"""
    import uuid
    tid = str(uuid.uuid4())
    payload = {
        "model": "fast_thinking", "stream": True,
        "messages": [{
            "id": "temp-" + str(uuid.uuid4()), "key": "temp-" + str(uuid.uuid4()),
            "conversationId": "temp-" + str(uuid.uuid4()), "role": "user",
            "content": query, "markdownContent": query,
            "engineType": "", "filter": "all", "contentType": 0, "mode": "detail",
        }],
        "engineType": "", "mode": "detail", "filter": "all", "outputStyle": "正常",
        "darkMode": False, "outputLanguage": "中文", "htmlNoDisplayEnable": True,
        "metaso-pc": "pc",
    }
    req = urllib.request.Request(
        "https://metaso.cn/api/search/chat",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "accept": "text/event-stream",
                 "metaso-pc": "pc", "Cookie": "tid=" + tid, "Referer": "https://metaso.cn/",
                 "User-Agent": DESKTOP},
        method="POST")
    answer, think, result_id, conv_id, err = [], [], None, None, None
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            body = line[5:].strip()
            if body == "[DONE]":
                break
            try:
                ev = json.loads(body)
            except Exception:
                continue
            t = ev.get("type")
            if t == "conversation_init":
                conv_id = ev["data"]["id"]
            elif t == "error":
                err = ev
                break
            elif ev.get("object") == "chat.completion.qa_with_agent":
                result_id = ev.get("id") or result_id
                d = (ev.get("choices") or [{}])[0].get("delta", {})
                if d.get("reasoning_content"):
                    think.append(d["reasoning_content"])
                if d.get("content"):
                    answer.append(d["content"])
    if err:
        raise RuntimeError(f"metaso: {err.get('msg')} (code={err.get('code')})")
    return [{
        "question": query,
        "answer": "".join(answer),
        "thinking": "".join(think),
        "conversation": f"https://metaso.cn/chat/{conv_id}" if conv_id else None,
        "resultId": result_id,
        "citations": [],
    }]


def metaso_citations(result_id, timeout=20, **kw):
    """取引用的结构化条目（不受搜索限流影响）。"""
    import uuid
    req = urllib.request.Request(
        "https://metaso.cn/api/search-result",
        data=json.dumps({"resultId": result_id}).encode(),
        headers={"Content-Type": "application/json", "metaso-pc": "pc",
                 "Cookie": "tid=" + str(uuid.uuid4()), "Referer": "https://metaso.cn/",
                 "User-Agent": DESKTOP},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    out = []
    for c in (data.get("data") or {}).get("citations") or []:
        out.append({
            "title": c.get("title") or c.get("orig_title") or "",
            "url": c.get("link") or "",
            "snippet": (c.get("snippet") or "")[:800],
            "site": ".".join(c.get("site") or []) if isinstance(c.get("site"), list) else (c.get("site") or ""),
            "date": c.get("publish_date_str") or c.get("date"),
            "author": c.get("author") or c.get("institution") or "",
            "authority": c.get("authority"),
            "refer_id": (c.get("display") or {}).get("refer_id"),
        })
    return out


# ---------------------------------------------------------------- 联想

def baidu_suggest(query, timeout=8, **kw):
    _, _, body = fetch("https://www.baidu.com/sugrec?prod=pc&wd=" + _q(query), timeout=timeout)
    try:
        data = json.loads(body)
    except Exception:
        return []
    return [{"text": it.get("q", "")} for it in data.get("g") or [] if it.get("q")]


def so360_suggest(query, timeout=8, **kw):
    _, _, body = fetch("https://sug.so.360.cn/suggest?word=" + _q(query), timeout=timeout)
    try:
        data = json.loads(body)
    except Exception:
        return []
    return [{"text": it.get("word", "")} for it in data.get("result") or [] if it.get("word")]


def bilibili_suggest(query, timeout=8, **kw):
    _, _, body = fetch("https://s.search.bilibili.com/main/suggest?term=" + _q(query),
                       headers={"Referer": "https://www.bilibili.com/"}, timeout=timeout)
    try:
        data = json.loads(body)
    except Exception:
        return []
    return [{"text": it.get("value", ""), "highlight": it.get("name", "")}
            for it in (data.get("result") or {}).get("tag") or []]


def douyin_suggest(query, timeout=8, **kw):
    # 不带 Referer 会返回 0 字节
    _, _, body = fetch("https://www.douyin.com/aweme/v1/web/search/sug/?aid=6383&keyword=" + _q(query),
                       headers={"Referer": "https://www.douyin.com/"}, timeout=timeout)
    try:
        data = json.loads(body)
    except Exception:
        return []
    out = []
    for it in (data.get("sug_list") or data.get("data") or []):
        w = it.get("content") or it.get("word") or ""
        if w:
            out.append({"text": w})
    return out


# ---------------------------------------------------------------- 热榜

def douyin_hot(query="", timeout=10, **kw):
    _, _, body = fetch("https://www.douyin.com/aweme/v1/web/hot/search/list/?aid=6383&detail_list=1",
                       headers={"Referer": "https://www.douyin.com/"}, timeout=timeout)
    try:
        data = json.loads(body)
    except Exception:
        return []
    words = ((data.get("data") or {}).get("word_list")) or []
    out = []
    for it in words:
        out.append({
            "rank": it.get("position"),
            "title": it.get("word", ""),
            "query": it.get("word", ""),
            "hot": it.get("hot_value"),
            "cover": it.get("word_cover", {}).get("url_list", [None])[0]
            if isinstance(it.get("word_cover"), dict) else None,
        })
    return out


def bilibili_hot(query="", timeout=10, **kw):
    _, _, body = fetch("https://s.search.bilibili.com/main/hotword",
                       headers={"Referer": "https://www.bilibili.com/"}, timeout=timeout)
    try:
        data = json.loads(body)
    except Exception:
        return []
    out = []
    for i, it in enumerate((data.get("list") or []), 1):
        out.append({"rank": i, "title": it.get("keyword", ""), "query": it.get("keyword", ""),
                    "hot": None, "cover": None})
    return out


def shenma_hot(query="", timeout=10, **kw):
    # 注意：只传 method+format 会 500（java NullPointerException），
    # request_sc / _chain / request_app / channel_name / q 这五个不能省
    url = ("https://api.m.sm.cn/rest?method=sc.news_top_list&request_sc=news_top_list"
           "&format=json&_chain=default_chain&request_app=news_top_list"
           "&q=%E7%A5%9E%E9%A9%AC%E6%96%B0%E9%97%BB&channel_name=sm_hp&start=0&hit=30")
    _, _, body = fetch(url, ua=MOBILE, headers={"Referer": "https://m.sm.cn/"}, timeout=timeout)
    try:
        data = json.loads(body)
    except Exception:
        return []
    rows = list(data.values()) if isinstance(data, dict) else data
    out = []
    for it in rows:
        if not isinstance(it, dict) or "title" not in it:
            continue
        out.append({"rank": it.get("index"), "title": it.get("title", ""),
                    "query": it.get("query", ""),
                    "hot": float(it["weight"]) if str(it.get("weight", "")).replace(".", "").isdigit() else None,
                    "cover": it.get("news_image")})
    return out


# ---------------------------------------------------------------- 注册表

WEB = {"shenma": shenma_web, "bing": bing_web}
IMAGE = {"bing": bing_images, "so360": so360_images}
VIDEO = {"bilibili": bilibili_video}
AI = {"metaso": metaso_ai}
SUGGEST = {"baidu": baidu_suggest, "so360": so360_suggest,
           "bilibili": bilibili_suggest, "douyin": douyin_suggest}
HOT = {"douyin": douyin_hot, "bilibili": bilibili_hot, "shenma": shenma_hot}

KINDS = {"web": WEB, "image": IMAGE, "video": VIDEO, "ai": AI,
         "suggest": SUGGEST, "hot": HOT}

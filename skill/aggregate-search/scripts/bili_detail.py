#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B站视频详情（二次请求）—— 直链 / 封面 / 简介 / 字幕。

搜索结果里只放轻量字段，避免一次拉一堆 m3u8 和几千行字幕。
需要某个视频的详情时再单独调这个脚本。

    python3 bili_detail.py BV1rpWjevEip              # 直链 + 封面 + 简介 + 官方字幕
    python3 bili_detail.py BV1rpWjevEip --asr        # 没有官方字幕时，走必剪匿名 ASR
    python3 bili_detail.py "https://www.bilibili.com/video/BV1xx" --max-audio 600

依赖：ffmpeg（--asr 时需要，用来把 m4s 转成 mp3）
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import uuid

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36")
API = "https://api.bilibili.com"
BCUT = "https://member.bilibili.com/x/bcut/rubick-interface"


def http(url, *, headers=None, data=None, method=None, timeout=25, raw=False, retries=2):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=h,
                                         method=method or ("POST" if data is not None else "GET"))
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                return (r.status, dict(r.headers), body if raw else body.decode("utf-8", "replace"))
        except Exception as e:                      # 网络抖动 / 偶发 412，重试
            last = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last


def get_buvid3():
    _, hdrs, _ = http("https://www.bilibili.com/", timeout=15)
    for k, v in hdrs.items():
        if k.lower() == "set-cookie":
            m = re.search(r"buvid3=([^;]+)", v)
            if m:
                return "buvid3=" + m.group(1)
    return ""


BILI_HEADERS = {"Referer": "https://www.bilibili.com/", "Origin": "https://www.bilibili.com"}


def parse_bvid(s):
    m = re.search(r"(BV[0-9A-Za-z]{10})", s or "")
    return m.group(1) if m else None


def video_info(bvid, cookie):
    _, _, body = http(f"{API}/x/web-interface/view?bvid={bvid}",
                      headers={**BILI_HEADERS, "Cookie": cookie})
    d = json.loads(body)
    if d.get("code") != 0:
        raise RuntimeError(f"view: {d.get('code')} {d.get('message')}")
    v = d["data"]
    return {
        "bvid": v["bvid"], "aid": v["aid"], "cid": v["cid"],
        "title": v.get("title", ""), "desc": v.get("desc", ""),
        "cover": v.get("pic", ""),
        "duration": v.get("duration"),
        "owner": (v.get("owner") or {}).get("name", ""),
        "pubdate": v.get("pubdate"),
        "pages": [{"page": p.get("page"), "cid": p.get("cid"),
                   "part": p.get("part"), "duration": p.get("duration")}
                  for p in v.get("pages") or []],
        "has_subtitle": None,
    }


def play_url(bvid, cid, cookie):
    q = f"bvid={bvid}&cid={cid}&fnval=16&fnver=0&fourk=1"
    _, _, body = http(f"{API}/x/player/playurl?{q}", headers={**BILI_HEADERS, "Cookie": cookie})
    d = json.loads(body)
    data = d.get("data") or {}
    out = {"quality": data.get("quality"), "accept": data.get("accept_description"),
           "video": [], "audio": [], "durl": []}
    dash = data.get("dash") or {}
    for s in dash.get("video") or []:
        out["video"].append({"id": s.get("id"), "codec": s.get("codecs"),
                             "width": s.get("width"), "height": s.get("height"),
                             "bandwidth": s.get("bandwidth"), "url": s.get("baseUrl")})
    for s in dash.get("audio") or []:
        out["audio"].append({"id": s.get("id"), "codec": s.get("codecs"),
                             "bandwidth": s.get("bandwidth"), "url": s.get("baseUrl")})
    for s in data.get("durl") or []:
        out["durl"].append({"order": s.get("order"), "size": s.get("size"),
                            "duration": s.get("length"), "url": s.get("url")})
    return out


def official_subtitle(bvid, cid, cookie):
    _, _, body = http(f"{API}/x/player/v2?bvid={bvid}&cid={cid}",
                      headers={**BILI_HEADERS, "Cookie": cookie})
    d = json.loads(body)
    subs = ((d.get("data") or {}).get("subtitle") or {}).get("subtitles") or []
    if not subs:
        return None
    # 优先中文
    pick = next((s for s in subs if str(s.get("lan", "")).startswith("zh")), subs[0])
    url = pick.get("subtitle_url") or ""
    if url.startswith("//"):
        url = "https:" + url
    _, _, sb = http(url, headers=BILI_HEADERS)
    data = json.loads(sb)
    cues = [{"from": round(c.get("from", 0), 2), "to": round(c.get("to", 0), 2),
             "text": (c.get("content") or "").strip()}
            for c in data.get("body") or []]
    return {"source": "official", "lan": pick.get("lan"), "lan_doc": pick.get("lan_doc"),
            "cues": [c for c in cues if c["text"]]}


# ---------------------------------------------------------------- 必剪匿名 ASR

def _bcut_form(url, fields):
    data = urllib.parse.urlencode(fields).encode()
    _, _, body = http(url, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://www.bilibili.com/",
    })
    return json.loads(body)


def bcut_asr(audio_path, timeout=300, poll=2.0, verbose=False):
    """必剪（bcut）匿名语音转写：create → PUT 分片 → complete → task → result。"""
    size = os.path.getsize(audio_path)
    j = _bcut_form(f"{BCUT}/resource/create", {
        "type": "2", "name": os.path.basename(audio_path), "size": str(size),
        "resource_file_type": "mp3", "model_id": "7",
    })
    if j.get("code") != 0:
        raise RuntimeError(f"bcut create: {j.get('code')} {j.get('message')}")
    d = j["data"]
    urls, per = d["upload_urls"], d["per_size"]
    etags = []
    with open(audio_path, "rb") as f:
        for u in urls:
            chunk = f.read(per)
            req = urllib.request.Request(u, data=chunk, method="PUT")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                et = r.headers.get("Etag") or r.headers.get("ETag")
                if not et:
                    raise RuntimeError("bcut: 分片上传未返回 Etag")
                etags.append(et.strip('"'))
    j = _bcut_form(f"{BCUT}/resource/create/complete", {
        "in_boss_key": d["in_boss_key"], "resource_id": d["resource_id"],
        "etags": ",".join(etags), "upload_id": d["upload_id"], "model_id": "7",
    })
    if j.get("code") != 0:
        raise RuntimeError(f"bcut complete: {j.get('code')} {j.get('message')}")
    download_url = j["data"]["download_url"]

    _, _, body = http(f"{BCUT}/task",
                      data=json.dumps({"resource": download_url, "model_id": "7"}).encode(),
                      headers={"Content-Type": "application/json",
                               "Referer": "https://www.bilibili.com/"})
    task = json.loads(body)
    if task.get("code") != 0:
        raise RuntimeError(f"bcut task: {task.get('code')} {task.get('message')}")
    task_id = task["data"]["task_id"]

    deadline = time.time() + timeout
    while time.time() < deadline:
        _, _, body = http(f"{BCUT}/task/result?model_id=7&task_id={task_id}",
                          headers={"Referer": "https://www.bilibili.com/"})
        r = json.loads(body)
        state = (r.get("data") or {}).get("state")
        if state == 4:                       # 完成
            result = json.loads(r["data"]["result"])
            cues = []
            for u in result.get("utterances") or []:
                txt = (u.get("transcript") or "").strip()
                if not txt:
                    continue
                cues.append({"from": round(u.get("start_time", 0) / 1000, 2),
                             "to": round(u.get("end_time", 0) / 1000, 2),
                             "text": txt})
            return {"source": "bcut", "lan": "zh", "lan_doc": "必剪自动识别", "cues": cues}
        if state == 3:                       # 失败
            raise RuntimeError(f"bcut: 识别失败 {r.get('data')}")
        if verbose:
            print(f"  ...state={state} 等待中", file=sys.stderr)
        time.sleep(poll)
    raise RuntimeError("bcut: 识别超时")


def download_audio(audio_urls, bvid, cookie, out_mp3=None):
    """直接用 ffmpeg 带防盗链头拉流并转 mp3 —— 比 urllib 先下再转少一步，
    也避开了 CDN 对裸 urllib 请求偶发的 403。"""
    tmp = tempfile.mkdtemp(prefix="bili_")
    out_mp3 = out_mp3 or os.path.join(tmp, f"{bvid}.mp3")
    headers = (f"Referer: https://www.bilibili.com/video/{bvid}/\r\n"
               f"Cookie: {cookie}\r\nUser-Agent: {UA}\r\nOrigin: https://www.bilibili.com\r\n")
    last = None
    for url in [u for u in audio_urls if u]:
        for _ in range(2):
            cmd = ["ffmpeg", "-v", "quiet", "-y", "-headers", headers,
                   "-i", url, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", out_mp3]
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode == 0 and os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 10000:
                return out_mp3
            last = (r.stderr or b"")[-400:].decode("utf-8", "replace")
            time.sleep(1.5)
    raise RuntimeError(f"音频下载失败: {last}")


def main():
    ap = argparse.ArgumentParser(description="B站视频详情：直链 / 封面 / 简介 / 字幕")
    ap.add_argument("target", help="BV 号或视频链接")
    ap.add_argument("--asr", action="store_true", help="无官方字幕时走必剪匿名 ASR")
    ap.add_argument("--page", type=int, default=1, help="分 P 序号，默认 1")
    ap.add_argument("--max-audio", type=float, default=1800,
                    help="--asr 时允许的最长音频秒数，超了拒绝（默认 1800）")
    ap.add_argument("--quality", default="max", choices=["max", "min"],
                    help="视频直链取最高还是最低清晰度，默认 max")
    ap.add_argument("--out", default="", help="写入文件（默认 stdout）")
    ap.add_argument("--pretty", action="store_true")
    a = ap.parse_args()

    bvid = parse_bvid(a.target)
    if not bvid:
        sys.exit("没认出 BV 号")
    cookie = get_buvid3()

    info = video_info(bvid, cookie)
    pages = info.get("pages") or []
    cid = info["cid"]
    if a.page > 1 and len(pages) >= a.page:
        cid = pages[a.page - 1]["cid"]
    info["cid"] = cid
    info["page"] = a.page

    streams = play_url(bvid, cid, cookie)
    if streams["video"]:
        vs = sorted(streams["video"], key=lambda x: x["bandwidth"] or 0)
        streams["video"] = [vs[-1] if a.quality == "max" else vs[0]]

    sub = official_subtitle(bvid, cid, cookie)
    info["has_subtitle"] = bool(sub)
    if not sub and a.asr:
        if not streams["audio"]:
            sys.exit("没有可下载的音频流，无法转写")
        if (info.get("duration") or 0) > a.max_audio:
            sys.exit(f"视频时长 {info['duration']}s 超过 --max-audio {a.max_audio}s；"
                     f"这是为了保护 ASR 服务，可手动放大该值")
        audio = sorted(streams["audio"], key=lambda x: x["bandwidth"] or 0)[0]
        print("下载音频并转写…", file=sys.stderr)
        mp3 = download_audio([audio["url"], audio.get("backup")], bvid, cookie)
        try:
            sub = bcut_asr(mp3, verbose=True)
        finally:
            if os.path.exists(mp3):
                try:
                    os.remove(mp3)
                except OSError:
                    pass

    result = dict(info)
    result["streams"] = streams
    result["subtitles"] = sub or {"source": None, "cues": []}
    result["note"] = "直链带时效，播放前请现取"

    text = json.dumps(result, ensure_ascii=False, indent=2 if a.pretty else None)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
        print(f"{bvid} → {a.out}  字幕: {result['subtitles']['source'] or '无'} "
              f"({len(result['subtitles']['cues'])} 条)")
    else:
        print(text)


if __name__ == "__main__":
    main()

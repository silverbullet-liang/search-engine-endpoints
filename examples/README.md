# examples

只有一个脚本：`parse_images.py` —— 把 `/images/async` 的 HTML 片段转成 JSON。

```bash
# 从已保存的片段解析
python3 parse_images.py fragment.html

# 只取前 3 条
python3 parse_images.py fragment.html --limit 3

# 单次直接请求（不带 Cookie，只能拿到第 1 批）
python3 parse_images.py --url 'https://cn.bing.com/images/async?q=%E7%8C%AB&first=1&count=35&mmasync=1'

# 高亮词转 <mark>，跨批按 md5 去重
python3 parse_images.py fragment.html --mark --dedupe md5
```

输出：

```json
[
  {
    "cid": "UFcCituS",
    "page_url": "https://…",
    "image_url": "https://…",
    "thumbnail_url": "https://ts1.mm.bing.net/th?id=OIP.…&pid=15.1",
    "title": "…",
    "desc": "…",
    "md5": "…",
    "mid": "…",
    "shkey": "…"
  }
]
```

## 字段命名

原字段名与输出名的对应见 `bing/fields.md`。`purl` → `page_url`、`murl` → `image_url`、`turl` → `thumbnail_url`、`t` → `title`，是为了避免使用方把 `purl` 误当图片地址（它其实是图片所在页面）。

## 红线

脚本**只做一件事**：发一个请求（或不发），解析，输出。

它没有：翻页循环、并发、重试、缓存、增量抓取、Cookie 生成、指纹伪装。
需要跨批取结果时，按 `bing/image.md` 的做法自备浏览器会话 Cookie，自己控制节奏与停止条件。

`--url` 模式不带 Cookie，因此永远只拿到第 1 批 35 条 —— 这是刻意的：它演示的是"如何读这个端点"，不是"如何采集"。

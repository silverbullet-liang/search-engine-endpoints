# 哔哩哔哩搜索

三个 JSON 接口，**全部不需要登录**。视频搜索只需先访问一次首页拿 `buvid3` cookie，之后可稳定分页。

| 我要什么 | 调哪个 | 前提 | 返回 |
|---|---|---|---|
| 搜视频 | `/x/web-interface/search/type` | 一次首页 cookie | JSON，20 条/页，最多 50 页 |
| 输入联想 | `s.search.bilibili.com/main/suggest` | 无 | JSON，10 条，带高亮 |
| 热搜榜 | `s.search.bilibili.com/main/hotword` | 无 | JSON，10 条 + 热度 |

---

## 1 · 视频搜索

### 请求方式

```http
GET https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=<kw>&page=1&page_size=20
```

| 参数 | 必填 | 实测 |
|---|---|---|
| `search_type` | 是 | `video`（本页记录的类型） |
| `keyword` | 是 | 关键词，URL 编码 |
| `page` | 否 | 页码，1 起。`page=2` 实测生效 |
| `page_size` | 否 | 每页条数。实测 `50` 生效（返回 50 条） |
| `order` | 否 | 排序：`pubdate`（最新）、`click`（播放）实测生效；默认综合 |
| `duration` | 否 | 时长筛选，`1` = 10 分钟以下，实测生效 |

### 前提：一条首页 cookie

直接请求会返回 **412**。先访问一次首页拿到 `buvid3` 即可（这是正常浏览产生的会话 cookie，不是签名）：

```bash
curl -sS -c bili.jar -o /dev/null https://www.bilibili.com/
grep buvid3 bili.jar        # 确认已拿到
```

### 请求头

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36
Referer: https://search.bilibili.com/
Cookie: （含 buvid3，来自上面那一步）
```

### 请求示例

```bash
# 1) 取 cookie
curl -sS -c bili.jar -o /dev/null https://www.bilibili.com/

# 2) 搜索
curl -sS -b bili.jar \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://search.bilibili.com/' \
  'https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=%E7%BC%96%E7%A8%8B&page=1'
```

```python
import requests
s = requests.Session()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"}
s.get("https://www.bilibili.com/", headers=UA, timeout=10)      # 拿 buvid3
r = s.get("https://api.bilibili.com/x/web-interface/search/type",
          params={"search_type": "video", "keyword": "编程", "page": 1},
          headers={**UA, "Referer": "https://search.bilibili.com/"}, timeout=10)
videos = [x for x in r.json()["data"]["result"] if x["type"] == "video"]
```

### 返回示例（真实响应裁剪）

```json
{
  "code": 0, "message": "OK", "ttl": 1,
  "data": {
    "seid": "5650060432105697602",
    "page": 1, "pagesize": 20,
    "numResults": 1000, "numPages": 50,
    "result": [
      {
        "type": "video",
        "bvid": "BV1rpWjevEip",
        "aid": 113006243481679,
        "title": "【全748集】目前B站最全最细的Python零基础全套教程…",
        "author": "Python官方课程",
        "mid": 3546597933714079,
        "play": 21360579,
        "video_review": 135042,
        "favorites": 905768,
        "like": 588966,
        "duration": "2398:14",
        "pubdate": 1724338758,
        "pic": "//i2.hdslb.com/bfs/archive/a979056b1a32012cdd00d48fbc3732d253e30620.jpg",
        "arcurl": "http://www.bilibili.com/video/av113006243481679",
        "description": "【视频配套籽料、开发环境搭建安装包教程…】\r\n本套教程从零开始讲解…",
        "tag": "程序员,Python教程,Python入门零基础,计算机,编程语言",
        "typename": "计算机技术",
        "is_union_video": 0,
        "badgepay": false
      }
    ],
    "suggest_keyword": "",
    "next": 2
  }
}
```

### 字段（准确性重点）

| 字段 | 类型 | 说明 |
|---|---|---|
| `bvid` | string | BV 号。**构造链接优先用它**：`https://www.bilibili.com/video/{bvid}` |
| `aid` | number | 旧 av 号。`arcurl` 里给的是 av 链接 |
| `title` | string | **可能含 `<em class="keyword">` 高亮**（本样本 13/20 条），用于展示前必须清洗 |
| `duration` | string | **「分钟:秒」且秒不补零**：`2398:14`、`189:9`、`57:0`。按 `:` 切两段算秒，不要 `datetime.strptime` |
| `pubdate` | number | Unix 秒。`0` 表示无（课堂类） |
| `pic` | string | **`//` 开头的协议相对 URL**（17/20 条），使用前补 `https:` |
| `play` / `video_review` / `favorites` / `like` | number | 播放 / 弹幕 / 收藏 / 点赞 |
| `mid` | number | UP 主 UID |
| `description` | string | 简介，含 `\r\n`，长文本需截断 |
| `tag` | string | 逗号分隔的标签串，不是数组 |
| `typename` | string | 分区名 |
| `is_union_video` | number | `0`/`1`，是否联合投稿（数字不是布尔） |
| `badgepay` | bool | 是否付费内容 |
| `numResults` / `numPages` | number | **看着像总数，实际封顶 1000 / 50 页**，不要当真实结果量 |

### 三个必须处理的坑

1. **`result` 是混合类型。** 里面会混进 `type: "ketang"`（付费课堂）的条目，它们 `bvid` 为空、`duration` 为空、`pubdate` 为 0、`arcurl` 指向 `/cheese/play/ss…`。**不过滤就会拿到空 BV 号**。
2. **标题带 HTML 高亮。** `<em class="keyword">编程</em>` 直接渲染会显示标签，直接入库会污染数据。
3. **时长不是标准时间。** `2398:14` 是「2398 分 14 秒」（合集视频，748 集），不是 23:98。

---

## 2 · 搜索联想

```http
GET https://s.search.bilibili.com/main/suggest?term=<kw>
```

无需 cookie、无需 Referer。返回 10 条：

```json
{
  "code": 0,
  "exp_str": "",
  "result": {
    "tag": [
      { "value": "零基础编程入门教程", "term": "零基础编程入门教程", "ref": 0,
        "name": "零基础<em class=\"suggest_high_light\">编程</em>入门教程",
        "spid": 5, "type": "", "item_feature": "" }
    ]
  },
  "stoken": "", "total_count": 0,
  "debug_response_info": null, "user_feature": null
}
```

| 字段 | 说明 |
|---|---|
| `result.tag[].value` / `term` | 纯文本建议词（**用这个**） |
| `result.tag[].name` | 带高亮的展示文本，`<em class="suggest_high_light">` 包裹匹配片段 |
| `spid` | 建议来源编号，语义未公开 |

`value` 已经去掉高亮，直接拿来用即可；只有在需要「高亮显示」时才解析 `name`。

---

## 3 · 热搜榜

```http
GET https://s.search.bilibili.com/main/hotword
```

```json
{
  "code": 0,
  "list": [
    { "hot_id": 279882, "keyword": "BLG对战HLE生死局前瞻",
      "show_name": "BLG对战HLE生死局前瞻", "score": 0.0, "word_type": 4,
      "goto_type": 0, "icon": "http://i0.hdslb.com/bfs/activity-plat/…png",
      "live_id": [], "call_reason": 1, "heat_layer": 2 }
  ],
  "top_list": [], "seid": "…", "timestamp": 1793469000, "total_count": 10
}
```

| 字段 | 说明 |
|---|---|
| `keyword` / `show_name` | 热搜词（两者本样本相同） |
| `hot_id` | 热词 ID，可用于跳转 |
| `word_type` / `goto_type` | 类型编码（4 = 话题类），语义未公开 |
| `icon` | 图标 URL，可能为空 |
| `total_count` | 条数，本样本 10 |

固定 10 条，无分页。

---

## 给 AI 用

直接把这段放进 system prompt，模型就知道怎么取数据：

```
工具：B站视频搜索
- 先 GET https://www.bilibili.com/ 拿 buvid3（一次即可）
- GET https://api.bilibili.com/x/web-interface/search/type
  ?search_type=video&keyword={kw}&page={1..50}&page_size={<=50}
- 取 data.result[]，先过滤 type=="video"
- 每条取：bvid(→ https://www.bilibili.com/video/{bvid})、title(去 <em> 标签)、
  author、play、like、favorites、pubdate(Unix秒)、duration(分钟:秒)、pic(补 https:)
- data.numResults 封顶 1000，不要当真实总数
```

机器可读版本见仓库根目录 [`api.json`](../api.json) 中的 `bilibili` 段。

## 状态说明

- 三个接口在 2026-10-31 匿名实测全部返回 `code: 0`，可直接使用。
- `api.bilibili.com` 的 `robots.txt` 对 `*` 为 `Disallow: /`；`search.bilibili.com` 同。技术上可调用，取舍由使用者自行判断。
- 请求频率建议保持人工节奏；没有做压力测试，也不建议做。

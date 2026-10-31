# 抖音搜索

**联想与热榜不需要签名、不需要登录，直接返回完整 JSON。** 内容搜索需要登录态（返回 `status_code: 2483`），本文只记录其状态，不提供获取方式。

| 我要什么 | 调哪个 | 前提 | 返回 |
|---|---|---|---|
| 输入联想 | `/aweme/v1/web/search/sug/` | 无 | JSON，10 条，带高亮区间 |
| 热搜榜 | `/aweme/v1/web/hot/search/list/` | 无 | JSON，49 条 + 热度值 |
| 搜视频/用户 | `/aweme/v1/web/general/search/single/` | **需登录** | `2483 请先登录` |

---

## 1 · 输入联想

### 请求方式

```http
GET https://www.douyin.com/aweme/v1/web/search/sug/?keyword=<kw>&aid=6383
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `keyword` | 是 | 已输入文本 |
| `aid` | 是 | 应用 ID，网页端固定 `6383` |

### 请求头

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36
Referer: https://www.douyin.com/
Accept: */*
```

### 请求示例

```bash
curl -sS 'https://www.douyin.com/aweme/v1/web/search/sug/?keyword=test&aid=6383' \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://www.douyin.com/'
```

```python
import requests
r = requests.get("https://www.douyin.com/aweme/v1/web/search/sug/",
                 params={"keyword": "test", "aid": 6383},
                 headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
                          "Referer": "https://www.douyin.com/"}, timeout=10)
words = [x["content"] for x in r.json()["sug_list"]]
```

### 返回示例（真实响应裁剪）

```json
{
  "status_code": 0,
  "status_msg": "",
  "sug_list": [
    {
      "pos": [{ "begin": 0, "end": 3 }],
      "content": "testflight兑换码",
      "sug_type": "",
      "word_record": {
        "group_id": "6567089457927820552",
        "words_position": 1,
        "words_content": "testflight",
        "words_source": "sug"
      },
      "extra_info": { "ctr_score": "0.009927", "deep_think": 0, "ecpm_score": 2.03, "…": "…”" }
    }
  ],
  "sug_virtual_list": [],
  "words_query_record": null,
  "rid": "…", "time_cost": 0.03, "log_pb": { "impr_id": "…" },
  "cache_conf": {}, "extra": {}
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `status_code` | number | `0` = 成功 |
| `sug_list` | array | 建议列表，固定 10 条 |
| `sug_list[].content` | string | 建议词（纯文本，**直接用这个**） |
| `sug_list[].pos` | array | 高亮区间 `[{begin, end}]`，对 `content` 的字符下标，左闭右开 |
| `sug_list[].word_record` | object | 埋点记录（`group_id` / `words_content` / `words_source`），排序用，取词不需要 |
| `sug_list[].extra_info` | object | 排序特征（ctr/ecpm/ecom 等 40+ 项），**不要用**，会随策略变化 |

`pos` 是「哪几个字与输入匹配」的唯一可靠来源 —— `content` 本身不含任何高亮标记，比自己猜前缀安全。

---

## 2 · 热搜榜

### 请求方式

```http
GET https://www.douyin.com/aweme/v1/web/hot/search/list/?aid=6383&detail_list=1
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `aid` | 是 | `6383` |
| `detail_list` | 否 | `1` 时返回完整字段（不加会缺 `word_list` 之外的明细） |

### 请求示例

```bash
curl -sS 'https://www.douyin.com/aweme/v1/web/hot/search/list/?aid=6383&detail_list=1' \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://www.douyin.com/'
```

### 返回示例（真实响应裁剪）

```json
{
  "status_code": 0,
  "data": {
    "active_time": "2026-10-31 14:41:30",
    "display_style": 0,
    "banner_display": { "uri": "32e5200049fac86168117", "url_list": ["…"] },
    "trending_desc": "",
    "trending_list": [],
    "word_list": [
      {
        "word": "冬天奶茶要挖着吃才满足",
        "sentence_id": 2720819,
        "position": 1,
        "hot_value": 11362235,
        "label": 3,
        "event_time": 1793337690,
        "video_count": 3,
        "discuss_video_count": 1,
        "article_detail_count": 0,
        "word_cover": { "uri": "tos-cn-p-0015/o0IDq5B26waAABeFWIgATwnAELNLkCTE8gfF9C",
                        "url_list": ["https://p26-sign.douyinpic.com/…"] },
        "max_rank": 0, "sentence_tag": 130001, "word_type": 1,
        "is_n1": false, "display_style": 0,
        "group_id": "7700253299685545275",
        "hotlist_param": "{\"version\":1}",
        "label_url": "https://lf3-static.bytednsdoc.com/…"
      }
    ]
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.word_list` | array | 榜单，本样本 **49 条**（不是整 50） |
| `word` | string | 热搜词 |
| `position` | number | 排名，**从 1 开始** |
| `hot_value` | number | 热度值（整数，如 11362235），用于排序或展示 |
| `sentence_id` | number | 话题 ID |
| `event_time` | number | Unix 秒 |
| `label` / `word_type` / `sentence_tag` | number | 类型/标签编码（3 = 热，1 = 新），语义未公开 |
| `video_count` / `discuss_video_count` / `article_detail_count` | number | 关联视频/讨论/文章数，可能为 0 或 1 |
| `word_cover` | object | 封面图，`url_list[0]` 可直接用（签名的 CDN 链接，会过期） |
| `hotlist_param` / `label_url` / `max_rank` / `is_n1` | — | 前端展示用，取榜单不需要 |

排序已经按 `position` 排好，直接顺序遍历即可。

---

## 3 · 内容搜索（需登录）

```http
GET https://www.douyin.com/aweme/v1/web/general/search/single/?keyword=<kw>&aid=6383&…
```

匿名调用返回 HTTP 200 + 127 字节：

```json
{"log_pb":{"impr_id":"2026103114485182B956C13336E654BD93"},"status_code":2483,"status_msg":"请先登录，再继续搜索吧"}
```

- `status_code: 2483` = 需要登录态，不是参数错误，也不是签名问题。
- 因此本仓库**没有**抖音视频搜索的结果字段记录 —— 拿不到就不写。

---

## 给 AI 用

```
工具：抖音联想（无需登录）
GET https://www.douyin.com/aweme/v1/web/search/sug/?keyword={kw}&aid=6383
→ 取 sug_list[].content（10 条）

工具：抖音热搜（无需登录）
GET https://www.douyin.com/aweme/v1/web/hot/search/list/?aid=6383&detail_list=1
→ 取 data.word_list[]：word / position(1起) / hot_value(热度) / event_time(Unix秒)
注意：本样本 49 条；word_cover.url_list[0] 是签名链接，会过期
```

机器可读版本见 [`api.json`](../api.json) 的 `douyin` 段。

## 状态说明

- 联想与热搜 2026-10-31 匿名实测 `status_code: 0`，可直接用。
- `www.douyin.com/robots.txt` 里列了 28 个具名爬虫（含 GPTBot、PerplexityBot、deepseekbot），**没有 `User-agent: *` 段**。
- 内容搜索需登录，本仓库不涉及登录态获取。

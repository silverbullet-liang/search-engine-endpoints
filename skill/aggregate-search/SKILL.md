---
name: aggregate-search
description: 聚合多个搜索引擎的匿名接口，一次调用把网页、图片、视频、热榜、联想、AI 回答全部拉齐并规整成统一 JSON。当用户说「搜一下 XX」「帮我查资料」「聚合搜索」「多个引擎一起搜」「找几张图片」「搜图」「查热点/热搜」「AI 搜一下这个概念」「把搜索结果整理成 JSON」，或需要给下游程序/模型提供结构化检索结果时触发。不适用于：需要登录态的搜索（微博/知乎登录后内容）、需要 API Key 的官方搜索 API（如秘塔 /api/v1/search）、纯站内搜索、需要真实浏览器的验证码页面。
---

# 聚合搜索

把八家搜索引擎的**匿名可用接口**收敛成一次调用、一份统一 JSON。

不解析页面外观，只取结构化字段；单引擎失败不影响整体输出。

## 快速开始

```bash
# 网页（神马 + Bing）
python3 scripts/search.py "量子计算"

# 图片（Bing + 360）
python3 scripts/search.py "猫" --kind image --limit 40

# 一次跑 web + image + video + hot
python3 scripts/search.py "量子计算" --kind bundle --out r.json

# AI 回答（秘塔匿名 SSE）+ 引用条目
python3 scripts/search.py "什么是向量数据库" --kind ai --citations
```

输出默认打到 stdout，`--out` 写文件，`--pretty` 缩进。

## 参数

| 参数 | 说明 |
|---|---|
| `--kind` | `web`（默认）/ `image` / `video` / `ai` / `suggest` / `hot` / `bundle` |
| `--engines` | 逗号分隔，默认全用。如 `bing,so360` |
| `--pages` | 每个引擎取几批（神马最多 5，Bing 图片每批 35 条） |
| `--limit` | 每类最多几条，0 = 不截断 |
| `--citations` | `ai` 类型额外拉取结构化引用（30 字段） |
| `--fresh` | 不跨引擎合并，按引擎原样返回（排查用） |
| `--timeout` | 单请求超时秒数，默认 15 |

## 输出格式

```json
{
  "query": "量子计算",
  "kind": "web",
  "took_ms": 4416,
  "count": 20,
  "engines": [
    {"id": "shenma", "ok": true, "count": 7,  "took_ms": 1100, "error": null},
    {"id": "bing",   "ok": true, "count": 10, "took_ms": 720,  "error": null}
  ],
  "items": [
    {
      "title": "量子计算-百度百科",
      "url": "https://baike.baidu.com/item/量子计算/11035661",
      "snippet": "遵循量子力学规律的计算模式",
      "site": "baike.baidu.com",
      "label": "百科",
      "date": null,
      "rank": 1,
      "score": 0.032787,
      "engine": "shenma",
      "engines": ["shenma", "bing"],
      "type": "web"
    }
  ]
}
```

`bundle` 模式把四类结果放在 `groups.web / groups.image / groups.video / groups.hot`，另给 `counts` 汇总。

### 各类 items 的字段

**web**：`title` `url` `snippet` `site` `label` `date`

**image**：`title` `image`（原图）`thumb` `page`（来源页）`width` `height` `format`

**video**：`title` `url` `cover` `author` `play` `duration`（原始「分:秒」）`duration_sec` `pubdate` `bvid`

**ai**：`question` `answer`（Markdown）`thinking`（思考链）`conversation`（会话链接）`resultId` `citations[]`
　　citations 每项：`title` `url` `snippet` `site` `date` `author` `authority` `refer_id`

**suggest**：`text`（B站另给 `highlight` 高亮片段）

**hot**：`rank` `title` `query` `hot` `cover`

### 合并规则

- 判重键：网页按 `url`（去协议、去 utm/spm 等追踪参数、去尾斜杠、去锚点），图片按原图地址，联想按文本
- 打分：RRF，`score = Σ 1/(60 + 该引擎内排名)`，多引擎同时命中的条目自然上浮
- 同一引擎内重复出现（360 图片是累积集合）只计一次分
- 字段补全：某一引擎缺的字段用其它引擎的补，不覆盖已有值；摘要取更长的那条

## 引擎矩阵（全部匿名，实测 2026-10-31）

| kind | 引擎 | 端点 | 单次 |
|---|---|---|---|
| web | `shenma` | `m.sm.cn/s/lite?q=&page=1..5` | 约 7–10 条/页 |
| web | `bing` | `cn.bing.com/search?q=` | 10 条（仅第 1 页） |
| image | `bing` | `cn.bing.com/images/async?q=&first=` | 25–35 条/批 |
| image | `so360` | `image.so.com/j?q=&pn=` | 累积集合，100+ 条 |
| video | `bilibili` | `api.bilibili.com/x/web-interface/search/type` | 47 条/页，上限 50 |
| ai | `metaso` | `metaso.cn/api/search/chat`（SSE） | 1 条答案 |
| suggest | `baidu` / `so360` / `bilibili` / `douyin` | 各家联想接口 | 10 条 |
| hot | `douyin` / `bilibili` / `shenma` | 各家榜单 | 48 / 10 / 30 条 |

## 已知失败与处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `shenma` 返回 punish 壳 | 普通 `/s?q=` 按云 IP 段拉黑（`cloud_ip_bl`） | 只走 `/s/lite`，脚本已内置 |
| `metaso` 报 `Too Many Requests (code=429)` | 匿名 IP 级频次上限（连续 6–8 次触发） | 等几分钟再试；`search-result` 不受限 |
| `bing` web 只 10 条 | `first` 对外部客户端无效 | 需要更多结果换 `shenma` 或换关键词 |
| `baidu` suggest 偶发失败 | 并发时被限 | 单独重试，或 `--engines so360,bilibili` |
| 神马热搜返回 500 | 少传了 `request_sc`/`_chain`/`request_app`/`channel_name`/`q` | 脚本已用全参 |
| 抖音联想返回 0 字节 | 缺 `Referer` | 脚本已带 |

所有引擎都是 fail-soft：失败只在 `engines[].error` 里体现，不影响其它引擎的结果。

## 字段准确性提醒

- 神马标题与摘要里的命中词被 `<em>` 包裹 —— 已剥离
- 神马广告卡（`cpc-card`）链接是 `adclick?disguise_click_url=`，已过滤
- B站 `duration` 是「分:秒」且秒不补零（`2398:14`），本技能同时给 `duration_sec`
- B站 `result` 混有 `type:"ketang"`（bvid 为空），已过滤
- 抖音 `word_list` 实测 48–49 条，`position` 从 1 开始
- 神马 `data-total` 是匹配总数，不等于本页条数

## 扩展新引擎

在 `scripts/engines.py` 里加一个函数 `def xxx(query, pages=1, limit=50, timeout=12, **kw) -> list[dict]`，返回统一字段的 list，再注册进 `WEB` / `IMAGE` / `VIDEO` / `AI` / `SUGGEST` / `HOT` 中对应的表即可。合并与打分不需要改。

## 免责

接口均为公开可访问的网页端端点，未绕过鉴权、未使用账号凭证。请把请求频率控制在人工使用量级，遵守各站点服务条款。端点随对方改版可能失效，`engines[].error` 会如实反映。

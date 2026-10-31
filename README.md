# search-engine-endpoints

八家搜索引擎的公开 HTTP 端点实测记录：**Bing / 百度 / 360 / 搜狗**（通用搜索）+ **哔哩哔哩 / 抖音 / 神马 / 秘塔 AI**（垂直与 AI 搜索）。每条都写清能不能用、怎么调对、字段真值是什么。

**在线浏览：https://silverbullet-liang.github.io/search-engine-endpoints/** ← 全部内容做成了单文件文档站，含参数表、请求头、请求示例与返回示例。

所有结论来自 2026-10-25 至 10-31 的可复现实验。方法见 [bing/method.md](bing/method.md)。

> **非官方项目**。与 Microsoft、百度、360、搜狗、哔哩哔哩、抖音、神马、秘塔均无关联，未获授权或背书。
> 本仓库**不提供采集工具**，也不提供绕过验证码、伪造指纹、轮换 IP 的方法。
> 使用前请读 [NOTICE.md](NOTICE.md)。

---

## 一张表看清八家

**通用搜索**

| | Bing | 百度 | 360 | 搜狗 |
|---|---|---|---|---|
| **Web 结果页** | 200，但只有第 1 页 | 302 验证码¹ | 302 验证码 | 302 antispider |
| **图片接口** | 片段，**可分页** | 200 + `antiFlag` | **200 可用**（累积集合） | 200 + `forbid` |
| **输入联想** | 可用（HTML/JSON） | **可用**（JSON/JSONP） | **可用**（JSON） | 200 + 0 字节 |
| **返回格式** | 几乎全是 HTML | JSON | JSON | — |
| **文档** | [bing/](bing/README.md) | [baidu/](baidu/README.md) | [360/](360/README.md) | [sogou/](sogou/README.md) |

**垂直与 AI**

| | 哔哩哔哩 | 抖音 | 神马 | 秘塔 AI |
|---|---|---|---|---|
| **内容搜索** | **视频搜索可用**（需 buvid3） | 200 + `2483` 需登录 | **极速版可用**（`/s/lite`，5 页） | **匿名 SSE 可用**（免 Key） |
| **输入联想** | **可用**（带高亮区间） | **可用**（无需签名） | punish 脚本（`sugs` 子域被拦） | — |
| **榜单/热榜** | **可用**（10 条） | **可用**（49 条 + 热度值） | **可用**（`api.m.sm.cn/rest` JSON） | — |
| **引用条目** | — | — | — | **可用**（30 字段） |
| **返回格式** | JSON | JSON | HTML + JSON | SSE + JSON |
| **文档** | [bilibili/](bilibili/README.md) | [douyin/](douyin/README.md) | [shenma/](shenma/README.md) | [metaso/](metaso/README.md) |

¹ 百度 Web 结果页在**真实浏览器**里返回 200 正常结果，curl 则被 302 到验证码 —— 同一 IP、同一 URL，只有客户端不同。

可匿名稳定取到结构化数据的，集中在：图片（Bing、360）、联想（百度、360、B站、抖音）、榜单（B站 10 条、抖音 49 条、神马热搜）、视频（B站）、**网页搜索（神马极速版 5 页）**、**AI 搜索（秘塔匿名 SSE）**。百度 / 360 / 搜狗的 Web 结果页仍是验证码。

---

## 四条硬结论

**1. 只有 Bing 把图片分页做成了"片段级接口"，也只有它能被外部客户端复现。**
`/images/async` 返回一段可直接嵌入的 HTML，`first` 是 1-based 起始序号。带会话 Cookie 后 `first=1 / 36 / 71` 得到三批互不重叠的结果，且与页面上第 1/36/71 条精确对齐。`imgbf`、`dgState`、`IG`、`SFX` 等参数全部可剥离。

**2. 同一批"看起来是 200"的响应里，有五种完全不同的拒绝。**

| 形态 | 出现位置 | 判据 |
|---|---|---|
| `302` → 验证码 | 百度 `/s`、360 `/s` | `Location` 含 `wappass` / `qcaptcha` |
| `302` → antispider | 搜狗 `/web` | `Location` 含 `/antispider/`，带 `antip=` |
| `200` + `antiFlag:1` | 百度 `acjson` | `body["antiFlag"] == 1` |
| `200` + `info:"forbid"` | 搜狗 `napi` | `body["status"] == 1`，`data` 为 `null` |
| `200` + punish 壳 | 神马 `/s?q=` | 1 KB 跳转页，`qrcode` 里带 `cloud_ip_bl` |
| `200` + SSE `code:429` | 秘塔 `/api/search/chat` | **HTTP 200**，流内 `{"code":429,"type":"error"}` |

只判断 `status == 200` 的客户端，会把这些全部当成成功。

**3. 同一站点里，拦与不拦常常是两套后端。**
神马 `GET /s?q=` 被 WAF 按云 IP 段拉黑（`cloud_ip_bl`），同域的 `GET /s/lite?q=` 却不经 WAF、直接返回 500 KB 结果页；秘塔网页端匿名可用，官方 `/api/v1/search` 却要 Key。**遇到"没接口"的结论，先把同站的其它路径枚举一遍。**

**4. 这些端点没有版本、没有 SLA。**
风控判定会随出口 IP、客户端指纹、时段变化。今天测通的，明天可能 302。所有数值都带日期与环境，请在自己的环境里复测后再采信。

---

## 技能包：一次调用，一份 JSON

[skill/aggregate-search/](skill/aggregate-search/) 把这八家端点封装成聚合搜索技能。它与常见搜索封装的差别不在「能不能搜」，而在**失败怎么处理、结果怎么归一**：

| 维度 | 常见搜索封装 | 本技能 |
|---|---|---|
| 鉴权 | 要 API Key（Serper / Tavily / Bing API），按次计费 | 八家全是网页端匿名端点，**零密钥、零账号、零费用** |
| 覆盖 | 通常只包一家引擎 | 8 引擎 / 6 模态，一次调用并发 |
| 失败 | 单源失败即整体失败，或返回空数组让人猜 | **fail-soft**：错误进 `engines[].error`，其余引擎结果照常返回 |
| 结构 | 各源字段各异，下游为每个源写分支 | **统一 schema**，`rank / score / engine / engines / type` 恒在 |
| 去重 | 多是把几个数组拼起来 | URL 规范化（去 utm/spm/尾斜杠/锚点）+ **RRF 融合**，多引擎命中自动上浮 |
| 异构源 | 只管 JSON，HTML 留给你 | 神马的 SSR HTML 在适配器内解析成同构 JSON，`<em>` 高亮已剥离、广告卡已剔除 |
| AI 搜索 | 只给一段文本 | 秘塔给 `answer + thinking + citations[]`，引用 30 字段含 `refer_id`（对应正文角标） |
| 依赖 | requests + bs4 + lxml | **纯标准库**，Python 3.9+ 直接跑 |
| 排查 | 出错只有一句 traceback | `--fresh` 看各引擎原始结果、`--debug` 带堆栈、`engines[]` 报每引擎耗时与错误 |

```bash
python3 scripts/search.py "量子计算"                      # 网页：神马 + Bing
python3 scripts/search.py "猫" --kind image --limit 40     # 图片：Bing + 360
python3 scripts/search.py "量子计算" --kind bundle         # web + image + video + hot
python3 scripts/search.py "什么是向量数据库" --kind ai --citations
```

实测（2026-10-31）：`bundle` 四类并发 8 个引擎 4.4 秒；图片单轮 125 条；视频 47 条；热榜 88 条。

**它不适合什么** —— 说清楚比说好听有用：

- **覆盖不等于全互联网**：只有这八家，百度 / 360 / 搜狗的 Web 结果页被验证码挡住，取不到。
- **稳定性跟着对方前端走**：网页端端点随时可能改版失效；失效时 `engines[].error` 会如实报出，而不是静默返回空。
- **有 IP 级限流**：秘塔匿名连续 6–8 次 429，神马高频也会触发风控。这是配额，不是代码。
- **以中文语料为主**：英文检索建议只用 `--engines bing`。

详见 [SKILL.md](skill/aggregate-search/SKILL.md)。

## 给 AI 用

两个机器可读产物，专门给模型与 Agent 消费：

| 文件 | 用途 |
|---|---|
| [`api.json`](api.json) | 8 引擎、29 端点的结构化清单：`available`、参数、字段类型、翻页方式、坑。可直接当 tool 目录读 |
| [`llms.txt`](llms.txt) | 纯文本索引，五十行内说清「哪些能用、哪些不行、字段哪里会错」 |

在线地址：

- https://silverbullet-liang.github.io/search-engine-endpoints/api.json
- https://silverbullet-liang.github.io/search-engine-endpoints/llms.txt

站内还有一页 [给 AI 用](https://silverbullet-liang.github.io/search-engine-endpoints/#/ai-usage)，给出可直接粘进 system prompt 的调用说明。

## 引擎导航

### [bing/](bing/README.md) · Bing / 必应

7 篇文档，最完整。核心是 [image.md](bing/image.md)（分页契约与剥离实验）与 [session.md](bing/session.md)（同一 URL 两种响应的判据）。

- 微软已于 2025-08-11 退役 Bing Search APIs（[官方公告](https://learn.microsoft.com/lifecycle/announcements/bing-search-api-retirement)），端点因此只能从浏览器行为里反推。
- 唯一有 `first` 语义实证的分页接口，也是唯一有完整字段字典的（[fields.md](bing/fields.md)）。

### [baidu/](baidu/README.md) · 百度

`/s`（Web）、`/search/acjson`（图片）、`sugrec` + `su`（联想）。
看点：`acjson` 的完整参数是从浏览器实际请求里抄的，`gsm` 与 `pn` 的十六进制对应关系可验证；`antiFlag` 是最容易误判的拒绝形态。

### [360/](360/README.md) · 360 搜索

`/s`（Web，验证码）、`image.so.com/j`（图片，可用）、`sug.so.360.cn/suggest`（联想，可用）。
看点：`list` 是**累积集合**而非单页增量，`pn` 不是页码；`rn` 被忽略；大量字段是字符串化的布尔（`"False"`）。

### [sogou/](sogou/README.md) · 搜狗

三端点全部被拦，文档重点在"拒绝形态识别"。
看点：`/napi` 返回 200 + 合法 JSON + `{"status":1,"info":"forbid","data":null}`，结构最规整、最容易被误判为成功。

### [bilibili/](bilibili/README.md) · 哔哩哔哩

视频搜索、联想、热搜三个端点，全部匿名可用。
看点：`search/type` 与 `main/suggest` / `main/hotword` 不需要登录；视频搜索需先取一次 `buvid3`；`page_size` 最大 50；`order=pubdate|click` 实测生效。三个字段陷阱（`ketang` 混入、`<em>` 高亮、`duration` 是「分:秒」且秒不补零）见文档。

### [douyin/](douyin/README.md) · 抖音

联想与热搜免签名直接可用，内容搜索返回 `2483`「请先登录」。
看点：`word_list` 实测 **49 条**（不是整 50），`position` 从 1 开始，`hot_value` 是整数热度。

### [shenma/](shenma/README.md) · 神马

**极速版搜索 `GET /s/lite?q=&page=1..5` 匿名可用**，无 Cookie、无签名；同站普通 `/s?q=` 被 `cloud_ip_bl` 拒绝。另有一个 JSON 网关 `api.m.sm.cn/rest`，`method=sc.news_top_list` 取热搜榜。
看点：`page` 是唯一有效的翻页参数（`pn`/`start`/`p` 静默无效）；5 页封顶；广告卡 `cpc-card` 混在结果里必须过滤；热搜响应顶层是 `{"0":{…}}` 的 dict 不是数组。

### [metaso/](metaso/README.md) · 秘塔 AI

**网页端匿名接口免 Key 可用**：`POST /api/search/chat` 返回 SSE（思考链 + 正文），`POST /api/search-result` 取 30 字段引用条目，`GET /api/knowledge/detail/<id>` 取全文。
门槛只有一个 `Cookie: tid=<任意 UUID>`（自己生成即可）；匿名有 IP 级频次限制，超限时 HTTP 仍是 200、流内返回 `code:429`。官方 `/api/v1/search` 需 Key，与这条链是两回事。

---

## 快速开始（离线，不联网）

仓库自带脱敏样本与解析器，用来验证解析逻辑：

```bash
python3 examples/parse_images.py samples/async-fragment.html --limit 3
python3 test/test_parse.py
```

`parse_images.py` 只做两件事：发**一个**请求（或不发）、解析。没有翻页循环、没有并发、没有 Cookie 生成、没有指纹伪装。

需要真实响应时，请自行按各家文档手动请求一次，并把节奏控制在自己能负责的范围内 —— 详见 [NOTICE.md](NOTICE.md)。

---

## 仓库结构

```
.
├── index.html      在线文档站（单文件、零依赖，GitHub Pages 部署，28 页）
├── bing/           Bing：7 篇（web / image / suggest / related-queries / fields / session / method）
├── baidu/          百度：README + web / image / suggest
├── 360/            360：README + web / image / suggest
├── sogou/          搜狗：README + web / image / suggest
├── bilibili/       哔哩哔哩：README（视频搜索 / 联想 / 热搜，全部可用）
├── douyin/         抖音：README（联想 / 热搜可用，内容搜索需登录）
├── shenma/         神马：README（极速版搜索 + 热搜 JSON 网关）
├── metaso/         秘塔 AI：README（匿名 SSE 搜索 + 引用条目 + 全文）
├── skill/          聚合搜索技能包（aggregate-search）
├── api.json        机器可读端点清单（8 引擎 / 29 端点，20 个可用）
├── llms.txt        LLM 索引
├── examples/       parse_images.py（零依赖解析器）
├── samples/        脱敏片段样本
├── test/           离线自查（9 项）
├── NOTICE.md       各家 robots 原文与版权声明原文
└── README.md       本文件
```

每家的接口文档统一结构：**请求方式 → 请求头 → 请求示例 → 返回示例 → 字段说明 → 限制 / 坑**。

---

## 实测环境

| 项 | 值 |
|---|---|
| 时间 | 2026-10-25 ~ 2026-10-31 |
| 出口 | 中国大陆 |
| 客户端 | curl 8.14.1 + Chrome for Testing 156 headless |
| 会话 | 全部匿名（未登录、无 Key） |
| 复现 | 每个数值都标注了触发条件与失败形态 |

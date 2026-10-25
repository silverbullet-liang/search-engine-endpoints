# search-engine-endpoints

四家中文环境可访问的搜索引擎 —— **Bing / 百度 / 360 / 搜狗** —— 的 Web 搜索、图片搜索、输入联想三类公开 HTTP 端点实测记录：请求方式、请求头、参数语义、返回结构，以及**拒绝响应长什么样**。

**在线浏览：https://silverbullet-liang.github.io/search-engine-endpoints/** ← 全部内容做成了单文件文档站，含参数表、请求头、请求示例与返回示例。

所有结论来自 2026-10-25 的可复现实验。方法见 [bing/method.md](bing/method.md)。

> **非官方项目**。与 Microsoft、百度、360、搜狗均无关联，未获授权或背书。
> 本仓库**不提供采集工具**，也不提供绕过验证码、伪造指纹、轮换 IP 的方法。
> 使用前请读 [NOTICE.md](NOTICE.md)：里面是四家 `robots.txt` 与版权声明的原文，它们直接决定了哪些用法不可行。

---

## 一张表看清四家

| | Bing | 百度 | 360 | 搜狗 |
|---|---|---|---|---|
| **Web 结果页** | 200，但只有第 1 页 | 302 验证码¹ | 302 验证码 | 302 antispider |
| **图片接口** | 片段，**可分页** | 200 + `antiFlag` | **200 可用**（累积集合） | 200 + `forbid` |
| **输入联想** | 可用（HTML/JSON） | **可用**（JSON/JSONP） | **可用**（JSON） | 200 + 0 字节 |
| **返回格式** | 几乎全是 HTML | JSON | JSON | — |
| **`robots.txt`（`User-agent: *`）** | `Disallow: /search` 等 | `Disallow: /` | `Disallow: /s`、`/j?` | `Disallow: /`、`/napi` |
| **文档** | [bing/](bing/README.md) | [baidu/](baidu/README.md) | [360/](360/README.md) | [sogou/](sogou/README.md) |

¹ 百度 Web 结果页在**真实浏览器**里返回 200 正常结果，curl 则被 302 到验证码 —— 同一 IP、同一 URL，只有客户端不同。

**四个引擎的搜索端点，对通配代理（也就是任何未报名的程序）在 `robots.txt` 里全部处于禁止或受限状态。** 这是本仓库把定位收紧到"事实记录"的直接原因。

---

## 四条硬结论

**1. 只有 Bing 把图片分页做成了"片段级接口"，也只有它能被外部客户端复现。**
`/images/async` 返回一段可直接嵌入的 HTML，`first` 是 1-based 起始序号。带会话 Cookie 后 `first=1 / 36 / 71` 得到三批互不重叠的结果，且与页面上第 1/36/71 条精确对齐。`imgbf`、`dgState`、`IG`、`SFX` 等参数全部可剥离。
其余三家的分页藏在文档级导航里，风控严格得多，外部客户端一律拿不到第二页。

**2. 同一批"看起来是 200"的响应里，有四种完全不同的拒绝。**

| 形态 | 出现位置 | 判据 |
|---|---|---|
| `302` → 验证码 | 百度 `/s`、360 `/s` | `Location` 含 `wappass` / `qcaptcha` |
| `302` → antispider | 搜狗 `/web` | `Location` 含 `/antispider/`，带 `antip=` |
| `200` + `antiFlag:1` | 百度 `acjson` | `body["antiFlag"] == 1` |
| `200` + `info:"forbid"` | 搜狗 `napi` | `body["status"] == 1`，`data` 为 `null` |
| `200` + 0 字节 | 搜狗 `ajajjson` | `Content-Length: 0` |

只判断 `status == 200` 的客户端，会把这些全部当成成功。

**3. "技术上能调通"与"被允许自动化访问"是两件事。**
360 的 `image.so.com/j` 是四家里唯一能直接吐出结构化图片数据的接口（单次 124 KB、38 个字段），而它恰好被 `robots.txt` 的 `Disallow: /j?` 点名禁止。本仓库记录契约，不因此推荐使用。

**4. 这些端点没有版本、没有 SLA，且多数已不是"只读查询"。**
风控判定会随出口 IP、客户端指纹、时段变化。今天测通的，明天可能 302。所有数值都带日期与环境，请在自己的环境里复测后再采信。

---

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

---

## 快速开始（离线，不联网）

仓库自带脱敏样本与解析器，用来验证解析逻辑：

```bash
python3 examples/parse_images.py samples/async-fragment.html --limit 3
python3 test/test_parse.py
```

`parse_images.py` 只做两件事：发**一个**请求（或不发）、解析。没有翻页循环、没有并发、没有 Cookie 生成、没有指纹伪装。

需要真实响应时，请自行按各家文档手动请求一次，并把节奏控制在自己能负责的范围内 —— 四家的 `robots.txt` 都对此有限制，详见 [NOTICE.md](NOTICE.md)。

---

## 仓库结构

```
.
├── index.html      在线文档站（单文件、零依赖，GitHub Pages 部署）
├── bing/           Bing：7 篇（web / image / suggest / related-queries / fields / session / method）
├── baidu/          百度：README + web / image / suggest
├── 360/            360：README + web / image / suggest
├── sogou/          搜狗：README + web / image / suggest
├── examples/       parse_images.py（零依赖解析器）
├── samples/        脱敏片段样本
├── test/           离线自查（9 项）
├── NOTICE.md       合规边界 + 四家 robots 原文 + 版权声明原文
└── README.md       本文件
```

每家的三篇接口文档统一结构：**请求方式 → 请求头 → 请求示例 → 返回示例 → 字段说明 → 限制 → 合规状态**。

---

## 实测环境

| 项 | 值 |
|---|---|
| 日期 | 2026-10-25 |
| 出口 | 中国（腾讯云 AS45090 等，沙箱多出口，不同请求可能走不同 IP） |
| HTTP 客户端 | curl 8.14.1（OpenSSL 3.5.5，HTTP/2） |
| 浏览器 | Chrome for Testing 156.0.8078.47（headless） |
| 会话 | 全部为未登录的匿名访问 |
| 地域跳转 | `www.bing.com` → `cn.bing.com`；百度/360/搜狗不跳转 |

出口 IP 会影响风控结论（搜狗拦截页直接显示了 IP）。换网络环境请重新验证。

## 许可

文档与示例代码：[MIT](LICENSE)。被记录的搜索结果内容不属于本仓库。

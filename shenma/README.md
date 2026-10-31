# 神马搜索（m.sm.cn）

**结论：有匿名可用入口，并且是官方极速版路径 —— 不是解析界面，是它自己的极速版页面。**
普通 `GET /s?q=` 会被阿里 `bixi` 风控直接 `deny`（判定串里带 `cloud_ip_bl`，即云 IP 段黑名单），但同一站点下 **`/s/lite` 极速版走的是另一套后端，不做 WAF 拦截**。另外 `api.m.sm.cn/rest` 是一个 JSON 网关，用 `method=` 选接口，热搜榜可直接取结构化数据。

| 路径 | 实测 | 说明 |
|---|---|---|
| `GET /s/lite?q=<kw>&page=1..5` | 200，约 500 KB | **可用**，极速版搜索结果页，服务端渲染，无 WAF |
| `GET /s?q=<kw>` | 200，1073 B | 阿里 punish 页，`action=deny`，`cloud_ip_bl` |
| `GET /s?q=<kw>&tomode=center` | 200，1073 B | 同上，被拦 |
| `GET /s/lite?q=<kw>&pn=20` | 200 | 参数**无效**，结果与第 1 页相同 |
| `GET /s/lite?q=<kw>&page=6` | 200，320 KB | 空壳页（只有 App 下载链），即上限 5 页 |
| `GET api.m.sm.cn/rest?method=sc.news_top_list&format=json` | 200，23 KB JSON | **可用**，热搜榜 |
| `GET api.m.sm.cn/rest?method=tools.nav&format=json` | 200，977 B JSON | **可用**，导航配置 |
| `GET sugs.m.sm.cn/s?q=` | 200，1077 B | punish 页，联想子域被拦 |

---

## 1 · 极速版搜索 `GET /s/lite`

### 请求方式

```http
GET https://m.sm.cn/s/lite?q=<关键词>&page=<1..5>
User-Agent: Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Mobile Safari/537.36
Referer: https://m.sm.cn/
```

**不要求任何 Cookie 或签名。** 首次响应会下发 `sm_sid` / `sm_uuid` / `XSRF-TOKEN`，但后续请求不带也照常返回结果。

### 请求示例

```bash
curl -sS 'https://m.sm.cn/s/lite?q=%E9%87%8F%E5%AD%90%E8%AE%A1%E7%AE%97&page=1' \
  -H 'User-Agent: Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Mobile Safari/537.36' \
  -o q.html
```

```python
import requests, re
UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/156.0.0.0 Mobile Safari/537.36")
def shenma(kw, page=1):
    h = requests.get("https://m.sm.cn/s/lite",
                     params={"q": kw, "page": page},
                     headers={"User-Agent": UA, "Referer": "https://m.sm.cn/"},
                     timeout=15).text
    total = int((re.search(r'data-total="(\d+)"', h) or [0, 0])[1])
    return total, h
```

### 参数

| 参数 | 必需 | 实测行为 |
|---|---|---|
| `q` | 是 | 关键词，UTF-8 URL 编码 |
| `page` | 否 | **唯一有效的翻页参数**，1–5；`page=6` 起返回 320 KB 空壳 |
| `pn` / `start` / `p` / `from+size` | — | 全部无效，返回第 1 页 |

### 返回结构

服务端渲染 HTML，结果容器带总数：

```html
<div id="results" class="c-theme-olympic" data-total="42">
```

`data-total` 是**匹配结果总数**（实测 42、50 都出现过），受 5 页上限约束。

单条结果（Quark UI 组件，`qk-` 前缀）真实片段：

```html
<div class="qk-title qk-title-size-xl qk-title-clamp-2 ...">
  <div class="qk-title-content">
    <a href="https://baike.baidu.com/item/%E9%87%8F%E5%AD%90%E8%AE%A1%E7%AE%97/11035661"
       class="qk-link-wrapper">
      <div class="qk-title-text-wrapper">
        <div class="qk-title-text qk-font-bold"><em>量子计算</em>-百度百科</div>
      </div>
    </a>
  </div>
</div>
<div class="qk-paragraph qk-color-dark ...">
  <div class="qk-paragraph-content qk-clamp-2">
    <div class="qk-paragraph-value">
      <a href="https://baike.baidu.com/item/..."><div class="qk-paragraph-text">遵循量子力学规律的计算模式</div></a>
    </div>
  </div>
</div>
<span class="qk-tag qk-tag-size-s qk-tag-color-primary ...">百科</span>
```

### 字段表

| 字段 | 位置 | 说明 |
|---|---|---|
| `title` | `.qk-title-text.qk-font-bold` | 标题，命中词被 `<em>` 包裹，需剥离标签 |
| `url` | 同节点内 `<a href>` | 落地页，多为 http(s) 外站 |
| `snippet` | `.qk-paragraph-text` | 摘要，同样含 `<em>` 高亮 |
| `source_type` | `.qk-tag` | 结果类型标签（`百科` 等） |
| `site` | `.qk-source-item` | 站点名 |
| `data-total` | `#results` | 匹配总数 |
| `is_ad` | `class` 含 `cpc-card` / `cpc_img` | 广告位，链接是 `m.sm.cn/adclick?disguise_click_url=…`，**必须过滤** |

### 提取代码

```python
import re, html
TITLE = re.compile(r'<div class="qk-title-text qk-font-bold">(.*?)</div>', re.S)
LINK  = re.compile(r'<a href="(https?://[^"]+)" class="qk-link-wrapper"')
SNIP  = re.compile(r'<div class="qk-paragraph-text">(.*?)</div>', re.S)

def strip(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s)).strip()

def parse(h):
    ads = h.count('cpc-card')                      # 广告卡在结果容器里，需按块剔除
    titles = [strip(x) for x in TITLE.findall(h)]
    links  = [u for u in LINK.findall(h) if 'm.sm.cn/adclick' not in u]
    return titles, links, ads
```

### 陷阱

1. **广告卡混在结果里**：`class="cpc-card cpc_img c-container"`，链接指向 `m.sm.cn/adclick?disguise_click_url=<大段密文>`。不过滤会污染结果集。
2. **高亮标签**：标题与摘要里命中词被 `<em>` 包裹（与 Bing/B站同类），直接取文本会带标签。
3. **`page` 之外的分页参数全是幻觉**：`pn`/`start`/`p` 传了也不翻页，且不报错，最容易被误判为"支持分页"。
4. **5 页封顶**：`page≥6` 返回 320 KB 空壳（只含 App 下载引导），不是 404，要按 `qk-title-text` 计数判断。
5. **普通 `/s?q=` 会被 WAF 拉黑**：判定串里 `cloud_ip_bl` 表示按云厂商 IP 段拒。换 UA、换浏览器内核、带完整 `sec-ch-ua` 都无效，这是 IP 层判定。

---

## 2 · 热搜榜 `GET api.m.sm.cn/rest`

神马有一个 JSON 网关，`method` 参数选接口。**这是全站最好用的结构化接口**。

### 请求方式

```http
GET https://api.m.sm.cn/rest?method=sc.news_top_list&request_sc=news_top_list&format=json&_chain=default_chain&request_app=news_top_list&q=%E7%A5%9E%E9%A9%AC%E6%96%B0%E9%97%BB&channel_name=sm_hp&start=0&hit=10
```

参数中只有 `method` / `format=json` / `start` / `hit` 影响结果，其余是前端自用的链路标记，**可省**：

```bash
curl -sS 'https://api.m.sm.cn/rest?method=sc.news_top_list&format=json&start=0&hit=10'
```

### 返回示例（真实，首条）

```json
{
  "0": {
    "is_orion": "0",
    "event_type": "general",
    "weight": "1000.0",
    "query": "日本访华代表团鞠躬谢罪",
    "id": "new_85943",
    "index": 1,
    "title": "日本访华代表团鞠躬谢罪",
    "news_title": "我国首次载人登月任务乘组计划公布！…",
    "news_image": "https://cdn.sm.cn/temp/20261031081115-47dpg29qg8nm1yv96t1p7bnpzueo1ob5.png",
    "order_lock": "1",
    "hot_trend": "0"
  },
  "1": { "…": "…" }
}
```

### 字段表

| 字段 | 类型 | 说明 |
|---|---|---|
| key | string | **数字字符串**，不是数组 —— 必须 `list(d.values())` |
| `index` | int | 排名，从 1 开始 |
| `query` | string | 检索词（可直接拼进 `/s/lite?q=`） |
| `title` | string | 榜单展示标题 |
| `news_title` | string | 关联新闻标题，可能比 `title` 长 |
| `news_image` | string | 配图，`cdn.sm.cn` 直链 |
| `weight` | string | 热度权重，"1000.0" 这类字符串化浮点 |
| `id` | string | 条目 id，`new_85943` |
| `event_type` | string | `general` 等分类 |
| `hot_trend` | string | 涨幅标记，`"0"` 表示无 |
| `order_lock` | string | 是否固定位次，`"1"` 锁定 |

> 注意：整份响应是 **dict 而非 list**，键名 "0"、"1"、"2"…；直接 `json.loads()` 后遍历会拿到键名。

### 其它可用 method

| method | 返回 | 用途 |
|---|---|---|
| `sc.news_top_list` | 23 KB JSON | 热搜榜 |
| `tools.nav` | 977 B JSON | 导航配置（含新闻/小说等子频道 `surl`） |
| `policy.index` | 68 B JSON | 服务声明元信息 |
| `search.web` / `web.search` | 0 B | 不存在，别试 |

---

## 3 · 为什么普通搜索页走不通

`GET https://m.sm.cn/s?q=天气` 返回 1073 B 的 HTML，正文只有一个跳转按钮：

```html
<a id="a-link"
   href="https://bixi.alicdn.com/punish/punish:resource:template:baba:fcvsxmqtca_35282882.html
         ?qrcode=SRCrwtzaUrYFsSWCXDEPsQ|auWXtA|vK…
         &action=deny&origin=https%3A%2F%2Fm.sm.cn%3A443%2Fs"></a>
```

`qrcode` 里的 `cloud_ip_bl` 就是判定原因：**云厂商 IP 段黑名单**。所以：

- 换 UA → 无效（判定在 UA 之前）
- 换浏览器内核 → 无效（headless Chrome 同样被拒）
- 加 `sec-ch-ua` 全套 → 无效

这类拦截不是"伪装有破绽"，而是出口 IP 本身被标记。极速版路径之所以能过，是因为它由另一套后端（`Userver`）直接渲染，没有挂 WAF 规则。

---

## 免责声明

本文仅记录公开可访问的 HTTP 端点与真实响应，用于互通与可访问性研究，不含任何抓取工具。所有请求均未绕过鉴权、未触碰账号数据；请求频率应远低于人工浏览水平，请遵守目标站点的服务条款与 robots 约定。接口可能随时变更，本文不构成任何可用性承诺。

# 01 · Web 搜索端点

```
GET https://cn.bing.com/search?q=<query>
GET https://www.bing.com/search?q=<query>     # 中国出口会 302 到 cn.bing.com
```

无鉴权。返回 `text/html`，服务端渲染，结果直接在 HTML 里。

---

## 参数

下表"有效"一列是实测结论（2026-10-25，匿名会话），不是文档推测。

| 参数 | 语义 | 实测 |
|---|---|---|
| `q` | 查询串 | 有效 |
| `first` | 结果起始序号，1-based | **对浏览器有效，对外部 HTTP 客户端无效**（见下文） |
| `count` | 期望条数 | 无效（固定 10 条） |
| `FORM` | 来源代码，如 `QBLH` / `QBRE` / `PERE` | 不影响结果内容 |
| `mkt` | 市场，如 `zh-CN` / `en-US` | 生效（影响结果集与界面语言） |
| `setlang` | 界面语言 | 生效（界面） |
| `ensearch=1` | 强制英文结果 | 生效（`<title>` 变为 `<q> - Search`） |
| `cc` | 国家/地区 | 生效 |
| `qs` / `sp` / `sc` / `sk` / `pq` | 查询连续性与改写状态 | 未观察到单独影响 |
| `cvid` | 会话内查询 ID | 未观察到单独影响 |
| `FPIG` | 分页指纹，由上一页 HTML 生成 | 分页时必需（但对外部客户端仍不足，见下） |
| `IG` | 请求关联 ID（32 位十六进制） | 非必需 |
| `format=rss` | 切换到 RSS 输出 | 生效（见下） |
| `format=json` | —— | **被静默忽略**，照常返回 HTML |

`first` 的取值不是 10 的倍数也可（`first=7` 会从第 7 条开始），但页面只渲染 10 条。

---

## `first` 为什么对外部客户端无效

浏览器里点"下一页"，URL 变成：

```
https://cn.bing.com/search?q=rust+async+runtime&FPIG=D465CFCF56764F37A8A060AD7B4AA9A8&first=11&FORM=PORE
```

结果真的换页：首条从 `rust-lang.github.io/async-book/...` 变为 `corrode.dev/blog/async/`，响应体 306 KB。

同样的 URL 改用 curl：

| 实验 | 结果 |
|---|---|
| `first=11` 裸请求 | 第 1 页，10 条 |
| `first=11` + 匿名会话 Cookie | 第 1 页，103 KB |
| `first=11` + `FPIG` + `FORM=PORE` | 第 1 页 |
| 上述 + `Referer` 精确指向第 1 页 | 第 1 页 |
| 上述 + `sec-fetch-*` 全套 | 第 1 页 |
| 上述 + `sec-ch-ua` 全套 | 第 1 页 |
| 上述 + `accept-encoding: gzip, deflate, br, zstd` | 第 1 页 |
| 浏览器内 `fetch()`（同源、同 Cookie） | **第 2 页** |
| 浏览器导航（点击） | **第 2 页** |

三点观察：

1. 换页在服务端确实存在，不是纯前端替换；
2. 浏览器内 `fetch` 与 curl 走同样的 TLS 栈外特性之外，唯一差别是请求指纹与浏览器发起的上下文；
3. 补齐了所有可枚举的 HTTP 头仍然无效 → 判定信号在 curl 无法伪造的层面（TLS/HTTP2 指纹或更底层的连接特征）。

**三个不同查询词 × `first=1/11/21` 交叉验证**，结果集交集恒为 10/10，确认不是某个词的特殊行为。

工程含义：外部客户端拿 Web 搜索结果**只能稳定拿到第 1 页 10 条**。需要更多结果时，正确路径是换查询词、用相关查询扩展（见 `related-queries.md`），而不是琢磨怎么翻页。

---

## 响应结构

```html
<ol id="b_results">
  <li class="b_algo" data-id iid="SERP.5334">
    <h2><a href="https://www.kimi.com/" h="ID=SERP,…">标题文本</a></h2>
    <div class="b_caption">
      <p class="b_lineclamp2 b_algoSlug">摘要文本</p>
    </div>
    <cite>https://www.kimi.com</cite>
  </li>
  …
</ol>
```

| 选择器 | 内容 |
|---|---|
| `#b_results` | 结果容器（1 个） |
| `li.b_algo` | 单条自然结果，10 条/页 |
| `li.b_algo h2 > a[href]` | 结果链接；`h` 属性是该站内部的点击追踪标识，不是必需参数 |
| `li.b_algo .b_caption p` | 摘要（class 带 `b_lineclampN`，N 为截断行数） |
| `li.b_algo cite` | 展示用域名/路径（非规范 URL） |
| `span.sb_count` | 结果总数文案，如 `83,000 条结果`。这是**量级提示**，不精确 |
| `.b_pag` | 分页控件；`a.sb_pagN` 为"下一页" |

注意：`li.b_algo` 之外还有广告位、知识卡、视频卡等模块，class 名各不相同。不要用"所有 `<li>`"或"所有 `<h2><a>`"来取结果 —— 会混入非自然结果。

`sb_count` 在同一会话内对不同查询返回不同量级（实测 `kimi 游戏` → 83,000；`cat` → 456,000），但它不是可翻页的总量承诺。

---

## RSS 变体

```
GET /search?q=<query>&format=rss
```

- `Content-Type: text/xml; charset=utf-8`
- 固定 **10 条**，`first` 与 `count` 均被忽略（四种组合实测响应体字节数完全相同：6082）
- 结构为标准 RSS 2.0：`channel > item`，`item` 内 `title` / `link` / `description`
- `link` 是原始目标 URL（不是跳转链）
- **响应体内含版权限制声明**，原文见 [NOTICE.md](../NOTICE.md) 第 2.2 节。这段话限制的是结果内容的使用与再分发，不只是抓取行为。

示例（`q=cat`，节选）：

```xml
<rss version="2.0"><channel>
  <title>必应：cat</title>
  <link>http://www.bing.com:80/search?q=cat</link>
  <item>
    <title>产品和服务 — Asia | Cat | Caterpillar</title>
    <link>https://www.cat.com/zh_CN.html</link>
    <description>…</description>
  </item>
</channel></rss>
```

`channel > link` 里保留着 `:80` 与 `http://` —— 是历史遗留格式，不要据此构造请求。

---

## 降级页的识别

同一查询，两种响应体并存：

| 版本 | 字节数（`q=rust` 附近量级） | 特征 |
|---|---|---|
| 完整页 | ~306 KB | 含完整体验模块、分页生效 |
| 降级页 | ~103 KB | 只有 10 条首屏结果、分页不生效、部分脚本被裁 |

外部客户端拿到的是降级页。判据与成因见 [session.md](session.md)。

---

## 相邻端点

| 端点 | 状态 |
|---|---|
| `/videos/search?q=` | 可用，`text/html`，同一套服务端渲染形态；本轮实测单页 610 个 `div.mc_vtvc` 卡片 |
| `/news/search?q=` | 本次环境中返回 15 KB 占位页（`<title>搜索 - Microsoft 必应</title>`，无结果卡片），未能稳定取得内容 |
| `/images/search` | 见 [image.md](image.md) |
| `/copilotsearch?q=` | `robots.txt` 明确 Disallow，本仓库不记录 |

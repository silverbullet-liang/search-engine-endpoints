# 07 · 方法论：这套结论怎么测出来的

记录的结论会过期，方法不会。这一篇说明实验设计，便于你自己复现或推翻。

---

## 三段式

```
① 找线索  →  从页面里读接口的形状（模板 / 参数名）
② 抓实际  →  看真实会话发出的请求长什么样
③ 剥离验证 →  一次只去掉一个参数，比较结果集
```

三段都做完，才有资格写"这个参数必需/不必要"。少任何一段都会得出错结论 —— 本仓库前期就因此把"`first` 无效"写错过一次（实际是会话降级）。

---

## ① 找线索：先看页面自述

现代搜索结果页会把分页接口模板直接内嵌在 HTML 里，因为它要交给前端 JS 用。图片搜索页里有：

```js
_w["DgConfig"] = {
  "aurl": "/images/async?q=%QUERY%\u0026async=content\u0026first=%FIRST%\u0026count=%COUNT%"
          "\u0026dgst=%DGSTATE%\u0026IID=%IID%\u0026SFX=%SFX%\u0026IG=%IG%"
          "\u0026CW=%CW%\u0026CH=%CH%\u0026CT=%CT%",
  "ac": 35, "ptp": 1, "rth": 500, "ella": true, "ellt": 10000,
  "vn": "images", "appns": "images"
};
```

这一小段信息量极大：

- 端点路径与全部参数名（不用猜）
- `ac: 35` 解释了"为什么 `count=100` 也只回 35 条"
- `%QUERY%` 这类占位符说明这是模板，由前端填值

找法：

```bash
curl -sS 'https://cn.bing.com/images/search?q=%E7%8C%AB' -o page.html
grep -o 'DgConfig[^<]*' page.html | head -c 800
# 或直接搜占位符
grep -o '%QUERY%' -B1 -A1 page.html
```

同类线索：`_G.IG`、`IID`、`SFX`、`sfx`、`async`、`aurl`、`%[A-Z]*%`。凡是被 JS 当模板用的字符串，都会带 `%占位符%`。

页面里还能找到实际值（`IG:"<32 hex>"`），但**不要抄这些值当必需参数** —— 第 ③ 步会证明它们可以剥离。

---

## ② 抓实际：让浏览器自己发一次

用 CDP 记录 `Network.requestWillBeSent` / `responseReceived`，然后**触发交互**（滚动、点击），而不是只看首屏 —— 首屏的请求里没有分页接口。

关键点：

- 滚动要滚动到真实底部，且分页是异步追加的，等 2–3 秒再看有没有新请求
- 记录**响应体**（`Network.getResponseBody`），不只看 URL；很多线索在响应 HTML 里
- 记录 `postData`（有些端点是 POST）

最省事的替代：页面内直接 `fetch()` 并用 `performance.getEntriesByType('resource')` 事后取 URL 列表 —— 长度不受日志截断影响：

```js
performance.getEntriesByType('resource')
  .filter(e => e.name.includes('/images/async'))
  .map(e => e.name)
```

本仓库就是这样拿到带 `imgbf` / `dgState` 的完整 URL 的。

---

## ③ 剥离验证：一次只动一个变量

拿到"全参数"请求后，逐次去掉一个参数，比较结果集：

```python
base  = cids(full_url)                  # 全参数
for p in ["imgbf", "dgState", "IG", "SFX", "iid", "cw", "ch"]:
    got = cids(url_without(p))
    print(p, "removable" if got == base else "REQUIRED")
```

三条纪律：

1. **同一会话内做**。换会话后结果集会漂移，差异会被误判成"参数必需"。
2. **用集合比较，不用条数比较**。条数可能因为去重浮动 1–2 条，集合才说明是不是同一批。
3. **每个变量之间隔 1 秒以上**，避免被限速影响判断。

本次结果：`imgbf/dgState/IG/SFX/iid/cw/ch` 全部可剥离，只剩 `q` + `first`。

---

## 验证 `first` 语义：DOM 对齐法

"`first=36` 是什么意思"只靠响应看不出（可能是第 36 条，也可能是第 36 页、第 35 条之后）。做法是把它和**页面 DOM 的顺序**对齐：

1. 真实浏览器打开图片搜索，滚动加载到 ≥ 80 条
2. 按 DOM 顺序抽出前 80 条的 `cid` 列表，存为 `page_order`
3. 请求 `first=36`，取响应的第一条 `cid`
4. 比较：它等于 `page_order[35]`（0-based）还是 `page_order[36]`？

实测结果等于 `page_order[35]`，即 `first` 是 **1-based 起始序号**，第 36 条。方法本身不依赖对参数的猜测 —— 用页面自己的渲染顺序当参照物。

这个技巧适用于任何"偏移量语义不明"的分页参数。

---

## 区分"参数失效"与"环境降级"

最容易出错的一步。判据：

在同一上下文里，用两个明显不同的参数值（`first=1` vs `first=36`）请求：

- 结果不同 → 参数生效
- 结果相同 → **不要马上写"参数无效"**，先换一个上下文（真实浏览器内 `fetch` 同一 URL）再测一次

在浏览器里不同、在 curl 里相同，就是环境问题。详见 `session.md`。

本次踩坑记录：早期 7 组 curl 实验全部"证明" `first` 无效，直到在正常会话里点了一次"下一页"（首条从 `rust-lang.github.io` 变为 `corrode.dev`），才发现结论反了。

---

## 记录规范

本仓库对每个数字的要求：

| 要求 | 原因 |
|---|---|
| 带日期 | 这类接口无版本号，季度级变动 |
| 带环境（出口地区、客户端、是否登录） | 地域跳转与降级都会改变结果 |
| 带样本量 | "35 条"与"35 条 × 1 次"不是一回事 |
| 区分"观察"与"推断" | `cid` 与 `OIP` 的关系只是观察，未验证 |
| 不写未测的断言 | 曾写过"空 `qry` 返回空容器"，实测是另一套推荐容器，已改 |

推断必须显式标注为推断。读者据此做工程决策，混淆两者的代价由读者承担。

---

## 工具

| 用途 | 最小方案 |
|---|---|
| 单次请求与对照 | `curl`（`-o` 落盘，别只看 stdout） |
| 解析片段 | Python 标准库：`html.unescape` + `json.loads` |
| 抓真实请求 | Chrome CDP：`Network.enable` + `getResponseBody` |
| 页面内重放 | `fetch()` + `performance.getEntriesByType('resource')` |
| 无头浏览器 | chrome-headless-shell（`--remote-debugging-port`） |

不需要第三方爬虫框架。这个规模的观测，标准库 + curl + 一个无头浏览器就够；引入框架只会让"到底谁发的请求"变得不清楚。

---

## 常见误判

1. **把降级响应当成功**：200 + 结构完整 + 有真结果，但只有第 1 页。
2. **抄页面里的 `IG`/`SFX` 当必需参数**：它们是前端状态，剥离后结果不变。
3. **用条数判断参数是否生效**：条数会因去重浮动。
4. **跨会话比较**：结果集漂移会被误读成"参数生效"。
5. **凭 `Content-Type` 选解析器**：`/AS/Suggestions` 声明 JSON、实为 HTML。

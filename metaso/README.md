# 秘塔 AI 搜索（metaso）

AI 搜索这一类，**目前没有匿名可用的接口**。本文记录官方端点的真实行为，以及在不接官方 Key 的前提下怎么拿到等价能力。

| 路径 | 前提 | 实测 |
|---|---|---|
| `POST /api/v1/search` | **API Key** | 200 + `{"errCode":2005,"errMsg":"API密钥无效"}` |
| `GET /api/v1/search` | — | 405（该路径只接受 POST） |
| 网页端搜索 | 登录（桌面端提示扫码） | 无匿名搜索请求发出 |

---

## 1 · 官方端点（需 Key）

### 请求方式

```http
POST https://metaso.cn/api/v1/search
Content-Type: application/json

{"question": "..."}
```

### 请求示例

```bash
curl -sS -X POST 'https://metaso.cn/api/v1/search' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <你的 Key>' \
  -d '{"question":"什么是向量数据库"}'
```

### 返回示例（无 Key 时的真实响应）

```http
HTTP/1.1 200 OK
Content-Type: application/json;charset=UTF-8
```

```json
{"errCode":2005,"errMsg":"API密钥无效"}
```

`GET` 同一路径：

```http
HTTP/1.1 405 Method Not Allowed
```

```json
{"timestamp":"2026-10-31T06:52:00.738+00:00","status":405,"error":"Method Not Allowed","path":"/api/v1/search"}
```

### 判断要点

- **405 说明路径存在**，只是方法不对 —— 这是确认端点真实性的强信号。
- **200 + `errCode: 2005`** 说明：body 结构无关紧要，服务端先校验 Key。三种不同的 body 键（`question` / `q` / `query`）返回完全一致，所以**无法从错误响应反推请求体 schema**。
- 有 Key 之后的字段结构本文不写 —— 没有实测样本就不编造。

### 获取 Key

秘塔开放平台申请（站点导航里有 API 入口）。免费额度与计费以官方页面为准。

---

## 2 · 网页端（匿名不可用）

用真实浏览器打开 `https://metaso.cn/`：页面正常渲染（标题「秘塔AI搜索」），输入框存在、可输入，但提交后 `location` 不变、无搜索请求发出，页面提示「手机端 👆 扫码免费使用」。

结论：**匿名会话拿不到 AI 搜索结果**。这与 Bing/百度那种"能拿到但降级"不同，是彻底没有数据。

---

## 3 · 不接 Key 时的替代路线

AI 搜索 = 检索 + 生成。前者本仓库有可直接用的接口，后者接任意 LLM 即可。最小可行组合：

1. **检索**：用 [B站](../bilibili/README.md)（视频）、[抖音](../douyin/README.md)（热搜/联想）、[Bing](../bing/image.md)（图片分页）、[360](../360/image.md)（图片 JSON）。这些都是匿名可调、返回结构化字段的。
2. **正文抓取**：对结果里的 `arcurl` / `page_url` 取正文（注意各站正文页的抓取限制与自身条款）。
3. **生成**：把「标题 + 摘要 + 来源链接」拼成 context 交给模型，要求它在回答里标注来源编号。

这条路线的好处是：检索部分完全可控、可复现；坏处是要自己处理去重与排序。秘塔这类托管 AI 搜索的价值恰恰在于省掉这两步。

---

## 4 · 给 AI 用

```
秘塔：
- 没有匿名接口。POST /api/v1/search 需要官方 Key（无 Key 返回 errCode 2005）
- 不要尝试拼接网页端请求：桌面端要求扫码登录，匿名会话不发搜索请求
- 需要 AI 搜索能力但无 Key 时，改用「公开搜索接口取结果 + 自己接 LLM」的组合，
  参见 api.json 里 bilibili / douyin / bing / 360 段
```

机器可读版本见 [`api.json`](../api.json) 的 `metaso` 段。

## 状态说明

- `metaso.cn` 无 `robots.txt`（返回 404），未声明爬虫规则。
- 网页端为 Next.js 应用，静态资源在 `static-1.metaso.cn`。
- 端点行为实测于 2026-10-31，`/api/v1/search` 的路径与错误码在后续版本中可能变化。

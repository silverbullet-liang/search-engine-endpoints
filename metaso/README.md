# 秘塔 AI 搜索（metaso.cn）

**结论：网页端匿名接口完全可用，不需要 API Key、不需要登录。**
`POST /api/search/chat` 是网页版提问时发出的真实请求，返回 SSE 流（思考链 + 正文）；`POST /api/search-result` 拿引用条目（30 字段）；`GET /api/knowledge/detail/<id>` 拿网页全文。

唯一门槛是一个 Cookie：`tid=<任意 UUID>`。**自己生成一个 UUID 就能过**（实测：不带 `tid` 返回 429，带上随机 UUID 立即返回 50 KB 流）。

| 接口 | 前提 | 实测 |
|---|---|---|
| `POST /api/search/chat` | `Cookie: tid=<UUID>` | 200，SSE 流 50–90 KB |
| `POST /api/search-result` | `Cookie: tid=<UUID>` | 200，59 KB JSON，6 条 citations |
| `GET /api/knowledge/detail/<id>` | `Cookie: tid=<UUID>` | 200，2–3 KB JSON，网页正文 |
| `GET /api/meta-config/by-key?configKey=outputTheme` | 无 | 200，1.1 KB |
| `GET /api/search-template` | 无 | 200，6.8 KB |
| `GET /api/my-info` | 登录 | 200 + `{"errCode":401,"errMsg":"需要登录"}` |
| `POST /api/v1/search` | **官方 API Key** | 无 Key 返回 `{"errCode":2005,"errMsg":"API密钥无效"}` |

> 下面全部是**网页端匿名接口**，不是官方开放 API。

---

## 1 · 发起搜索 `POST /api/search/chat`

### 请求方式

```http
POST https://metaso.cn/api/search/chat
Content-Type: application/json
accept: text/event-stream
metaso-pc: pc
Cookie: tid=<任意 UUID>
Referer: https://metaso.cn/
```

### 请求示例

```bash
TID=$(python3 -c 'import uuid;print(uuid.uuid4())')

curl -sS -N -X POST 'https://metaso.cn/api/search/chat' \
  -H 'Content-Type: application/json' \
  -H 'accept: text/event-stream' \
  -H 'metaso-pc: pc' \
  -H "Cookie: tid=$TID" \
  -H 'Referer: https://metaso.cn/' \
  -d '{
    "model": "fast_thinking",
    "stream": true,
    "messages": [{
      "id": "temp-11111111-1111-4111-8111-111111111111",
      "key": "temp-22222222-2222-4222-8222-222222222222",
      "conversationId": "temp-33333333-3333-4333-8333-333333333333",
      "role": "user",
      "content": "量子计算是什么",
      "markdownContent": "量子计算是什么",
      "engineType": "",
      "filter": "all",
      "contentType": 0,
      "mode": "detail"
    }],
    "engineType": "",
    "mode": "detail",
    "filter": "all",
    "outputStyle": "正常",
    "darkMode": false,
    "outputLanguage": "中文",
    "htmlNoDisplayEnable": true,
    "metaso-pc": "pc"
  }'
```

### 请求字段

| 字段 | 实测取值 | 说明 |
|---|---|---|
| `model` | `fast_thinking` / `fast` / `ds` / `pro` | 网页默认 `fast_thinking`（带思考链）；四个值均被接受 |
| `stream` | `true` | 必须 true 才拿到 SSE |
| `messages[].content` | 问题文本 | 主体 |
| `messages[].markdownContent` | 同 content | 前端渲染用 |
| `messages[].id` / `key` / `conversationId` | `temp-<uuid>` 形式 | **前缀 `temp-` 是关键**，前端用它标记"尚未落库的本地会话" |
| `messages[].filter` | `all` | 搜索范围过滤 |
| `messages[].mode` / 顶层 `mode` | `detail` | `detail` 深度模式 |
| `engineType` | `""` / `pdf` / `quanwang` | 空串为综合搜索；`pdf` 论文库、`quanwang` 全网（见 `/api/metaso-ai-config` 的 demos） |
| `outputLanguage` | `中文` | 输出语言 |
| `token` | 152 字符 base64 密文 | 网页端会带；**实测可省**，不带也能正常出结果 |

### 返回示例（真实，事件头几帧）

```
data:{"data":{"id":"2116429832413700097"},"type":"conversation_init"}

data:{"data":{"id":"2116429832443060224"},"type":"user_message_init"}

data:{"data":{"id":"2116429832413700096"},"type":"response_message_init"}

data:{"type":"heartbeat"}

data:{"created":1793431168,"model":"metaso-qa-with-agent","id":"01a190d3-e511-7238-a7c5-f9a15ab88ff3","choices":[{"delta":{"role":"assistant","action":"搜索","reasoning_content":"\n搜索 “人工智能 定义 发展现状 2025 2026”\n"},"index":0}],"object":"chat.completion.qa_with_agent"}

data:{"created":1793431168,"model":"metaso-qa-with-agent","id":"01a190d3-…","choices":[{"delta":{"role":"assistant","reasoning_content":"搜索到15条结果。"},"index":0}],"object":"chat.completion.qa_with_agent"}

data:{"created":1793431168,"model":"metaso-qa-with-agent","id":"01a190d3-…","choices":[{"delta":{"took":8.99364948272705,"role":"assistant",…},"index":0}],"object":"chat.completion.qa_with_agent"}

data:{"created":1793431168,"model":"metaso-qa-with-agent","id":"01a190d3-…","choices":[{"delta":{"role":"assistant","content":"**人工智能**（Artificial I"},"index":0}],"object":"chat.completion.qa_with_agent"}

data:[DONE]
```

### 事件表

| `type` / `object` | 载荷 | 说明 |
|---|---|---|
| `conversation_init` | `data.id` | **会话 id**，可拼成 `https://metaso.cn/chat/<id>` |
| `user_message_init` | `data.id` | 用户消息 id |
| `response_message_init` | `data.id` | 回答消息 id |
| `heartbeat` | `{type:"heartbeat"}` | 空转保活，频率约 1 条/2 秒 |
| `chat.completion.qa_with_agent` | `choices[0].delta` | 主体。`delta` 内字段见下 |
| `error` | `{msg,code,showToast,type}` | 出错，如 `{"msg":"Too Many Requests","code":429}` |
| `[DONE]` | — | 流结束标记（无 `data:` 前缀之外的 JSON） |

`choices[0].delta` 逐帧出现的字段：

| 字段 | 含义 |
|---|---|
| `role` | 固定 `assistant` |
| `action` | `搜索` —— 正在检索 |
| `reasoning_content` | 思考链增量（"搜索到 15 条结果"这类），拼接成完整推理过程 |
| `took` | 本段耗时（秒，浮点） |
| `content` | **正文增量**，Markdown 文本，逐帧拼接 |

> 顶部 `id`（`01a190d3-e511-7238-a7c5-f9a15ab88ff3`）就是下一步 `search-result` 需要的 `resultId`。

### 解析代码

```python
import json, requests, uuid

def metaso(question, model="fast_thinking"):
    tid = str(uuid.uuid4())
    body = {
        "model": model, "stream": True,
        "messages": [{
            "id": f"temp-{uuid.uuid4()}", "key": f"temp-{uuid.uuid4()}",
            "conversationId": f"temp-{uuid.uuid4()}", "role": "user",
            "content": question, "markdownContent": question,
            "engineType": "", "filter": "all", "contentType": 0, "mode": "detail",
        }],
        "engineType": "", "mode": "detail", "filter": "all",
        "outputStyle": "正常", "darkMode": False, "outputLanguage": "中文",
        "htmlNoDisplayEnable": True, "metaso-pc": "pc",
    }
    r = requests.post("https://metaso.cn/api/search/chat", json=body, stream=True, timeout=120,
                      headers={"accept": "text/event-stream", "metaso-pc": "pc",
                               "Cookie": f"tid={tid}", "Referer": "https://metaso.cn/"})
    answer, think, result_id, conv_id = [], [], None, None
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        ev = json.loads(payload)
        t = ev.get("type")
        if t == "conversation_init":
            conv_id = ev["data"]["id"]
        elif t == "error":
            raise RuntimeError(ev)
        elif ev.get("object") == "chat.completion.qa_with_agent":
            result_id = ev.get("id") or result_id
            d = ev["choices"][0].get("delta", {})
            if d.get("reasoning_content"):
                think.append(d["reasoning_content"])
            if d.get("content"):
                answer.append(d["content"])
    return {"conversation": conv_id, "resultId": result_id,
            "answer": "".join(answer), "thinking": "".join(think)}
```

---

## 2 · 取引用条目 `POST /api/search-result`

上一步流里拿到的 `id` 就是 `resultId`。

### 请求方式

```http
POST https://metaso.cn/api/search-result
Content-Type: application/json
Cookie: tid=<UUID>

{"resultId":"01a190d3-e511-7238-a7c5-f9a15ab88ff3"}
```

### 返回示例（真实，节选首条 citations）

```json
{
  "errCode": 0,
  "errMsg": "success",
  "data": {
    "citations": [
      {
        "id": "9971e3ba-b937-4add-976d-6ff4b53ab6f4",
        "title": "2026-2030年全球及中国汞监测行业技术与市场分析报告（GEPD7M5K1S2L）",
        "link": "https://m.gepresearch.com/75/view-1108366-1.html",
        "snippet": "▉ 报告目录 第一章 行业概述与研究方法 …",
        "date": "2026年07月09日",
        "publish_date_str": "2026-07-09",
        "publish_date": 1783526400,
        "author": "GEP Research",
        "institution": "GEP Research",
        "site": ["m.gepresearch.com", "gepresearch.com", "com"],
        "authority": 4,
        "article_type": "行业分析报告",
        "language": "ZH",
        "type": "chunk",
        "chunk_id": 7,
        "engine": "meta",
        "version": 4,
        "rank_policy_score": 0.8135359454154968,
        "rank_policy_adjustment": 0.0,
        "display": { "refer_id": 1 },
        "origin_ids": [1],
        "ids": ["https://m.gepresearch.com/75/view-1108366-1.html"]
      }
    ],
    "not_citations": []
  }
}
```

### 字段表（30 个，实测全量）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` / `file_uuid` | string | 文档 id，可用于 `knowledge/detail` |
| `title` / `orig_title` / `orig_o_title` | string | 标题；`orig_*` 为未截断原文 |
| `link` | string | 落地页 |
| `snippet` | string | 命中片段（可能很长，是正文切片） |
| `date` / `publish_date_str` | string | 展示日期 / ISO 日期 |
| `publish_date` / `update_date` | int / string | 时间戳 / ISO 时间 |
| `orig_date` | string | 原始发布日期 |
| `author` / `author_ori` / `authors` / `authors_ori` | string / list | 作者，`*_ori` 为原文 |
| `institution` | string | 机构 |
| `site` | list | 域名拆分，如 `["m.gepresearch.com","gepresearch.com","com"]` |
| `ids` | list | 同 `link` 的去重集合 |
| `authority` | int | 权威度（实测 4） |
| `article_type` | string | 文章类型（`行业分析报告` 等） |
| `language` | string | `ZH` / `EN` |
| `type` | string | `chunk` = 正文切片 |
| `chunk_id` | int | 切片序号 |
| `engine` | string | 来源引擎，`meta` 等 |
| `version` | int | 文档版本 |
| `rank_policy_score` | float | 排序打分 0–1 |
| `rank_policy_adjustment` | float | 排序修正 |
| `display.refer_id` | int | **正文里的角标编号**，与 `[1]` 对应 |
| `origin_ids` | list | 引用编号集合 |
| `agent_qa_meta` | object | 触发它的子查询 `{query, display, id}` |
| `meta` | list | 附加元信息 |

> `display.refer_id` 是把答案正文里的 `[n]` 标记映射回具体链接的关键字段。

---

## 3 · 网页全文 `GET /api/knowledge/detail/<id>`

```http
GET https://metaso.cn/api/knowledge/detail/8701568319464501249
Cookie: tid=<UUID>
```

```json
{"errCode":0,"errMsg":"success","data":{"id":"…","dirRootId":"…","name":"…","byUser":"…","description":"…"}}
```

返回该文档的正文/描述，`data.id` 与 citations 的 `id` / `file_uuid` 对应。

---

## 4 · URL 直接搜索（无需写代码）

网页端支持把问题直接放进 URL，服务端创建会话并跳转：

```
https://metaso.cn/?q=<URL 编码的问题>
```

实测跳转到 `https://metaso.cn/chat/2116430779699875841`，页面直接给出完整答案。这条路径适合快速验证接口是否活着。

---

## 5 · 限流（重要）

匿名调用有 **IP 级频次上限**。超限时 SSE 首帧仍是 `conversation_init`，随后立刻给出：

```
data:{"msg":"Too Many Requests","code":429,"showToast":false,"type":"error"}
data:[DONE]
```

实测：连续 6–8 次搜索后触发；同一 IP 下**浏览器页面也一起被限**（不是客户端指纹判定）；等待 65 秒未恢复。判断方法：看流里是否出现 `"code":429`，不要只看 HTTP 状态码（**HTTP 一直是 200**）。

`search-result` 与 `knowledge/detail` 不受该限制影响（实测连续请求正常返回）。

---

## 6 · 与官方 API 的区别

| 项 | 网页端匿名接口 | 官方 API |
|---|---|---|
| 地址 | `metaso.cn/api/search/chat` | `metaso.cn/api/v1/search` |
| 鉴权 | `Cookie: tid=<UUID>` | `Authorization: Bearer <Key>` |
| 返回 | SSE 流（思考链 + 正文 + 引用 id） | 一次性 JSON |
| 费用 | 无 | 按官方计费 |
| 稳定性 | 会随前端改版变化 | 有版本承诺 |

无 Key 时官方端点真实响应：

```json
{"errCode":2005,"errMsg":"API密钥无效"}
```

---

## 免责声明

本文仅记录网页端公开可访问的 HTTP 端点与真实响应，用于互通与可访问性研究，不含抓取工具。请求中未使用任何账号凭证，`tid` 为本地随机 UUID。请控制请求频率（远低于人工使用强度），遵守目标站点服务条款。接口随时可能变更。

# 搜狗 · 输入联想

## 请求方式

```http
GET https://www.sogou.com/suggnew/ajajjson?key=<typed>&type=web
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `key` | 是 | 已输入文本 |
| `type` | 是 | 搜索类型，`web` 表示网页 |
| `ori` | 否 | `yes`，测试中未见影响 |

## 请求头

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36
Referer: https://www.sogou.com/
```

## 请求示例

```bash
curl -sS -D - \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://www.sogou.com/' \
  'https://www.sogou.com/suggnew/ajajjson?key=cat&type=web'
```

## 返回示例

```http
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Length: 0
```

**响应体 0 字节。**

这不是解析问题，是服务端没有返回内容：`Content-Type` 也是 `application/octet-stream`（而不是 `application/json`），说明请求在网关层就被处理掉了，没有走到业务逻辑。

## 尝试过的变体

| 请求 | 结果 |
|---|---|
| `?key=cat&type=web` | 200，0 字节 |
| `?key=cat&type=web&ori=yes` | 200，0 字节 |
| `/suggnew/web?key=cat` | 404（3407 字节错误页） |
| `/web-ajax/sugg?key=cat` | 404（同上） |
| `/sug?key=cat` | 301 |

结论：**本次环境未取得搜狗联想数据**。正常响应的结构（字段名、包裹形式）本仓库没有样本，因此不列、不推测。

## 说明

1. 0 字节 + 200 是最难排查的一种拒绝：没有错误码、没有错误文案，只有空。
2. 判断依据与 `/web`、`/napi` 一致（IP + 客户端环境），本次环境整体被拒。
3. 如果将来拿到正常响应，请按本仓库的规矩补：带日期、带环境、带真实样本片段，并区分"观察"与"推断"。

## 合规状态

该端点位于 `www.sogou.com`，其 `robots.txt` 对通配代理为 `Disallow: /`。

本文件记录请求形态与空响应现象，不提供采集用途。

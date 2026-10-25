# 百度 · 图片搜索（JSON）

## 请求方式

```http
GET https://image.baidu.com/search/acjson?tn=resultjson_com&word=<query>&pn=<offset>&rn=30&gsm=<hex>
```

| 参数 | 必填 | 实测说明 |
|---|---|---|
| `tn` | 是 | 固定值 `resultjson_com`，决定返回 JSON |
| `word` | 是 | 查询词，URL 编码 |
| `pn` | 是 | 起始偏移。浏览器实测只对 `pn=30`、`pn=60` 发请求（首屏是服务端渲染，不调接口） |
| `rn` | 否 | 每页条数，实测固定 `30` |
| `gsm` | 否 | 分页标记，**实测等于 `pn` 的十六进制**：`pn=30 → 1e`、`pn=60 → 3c`。两例吻合，未见其它取值说明 |
| `ie` | 否 | 编码，`utf-8` |
| `fp` | 否 | 固定 `result` |
| `fr` | 否 | 空串 |
| `ala` | 否 | `0` |
| `applid` | 否 | 19 位会话级应用 ID，由页面生成（每次会话不同） |
| `nojc` | 否 | `0` |
| `newReq` | 否 | `1` |
| `ipn` `ct` `queryWord` | 否 | 历史参数，`rn=30` 场景下可省略（实测仍返回拒绝响应，未验证正常场景） |

浏览器实际发出的完整 URL（观测值，`applid` 每次不同）：

```
https://image.baidu.com/search/acjson
  ?tn=resultjson_com&word=%E7%8C%AB&ie=utf-8&fp=result&fr=&ala=0
  &applid=8964688226984249294
  &pn=30&rn=30&nojc=0&gsm=1e&newReq=1
```

## 请求头

浏览器内观测到的请求头：

```http
User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/156.0.8078.47 Safari/537.36
Referer: https://image.baidu.com/search/index?tn=baiduimage&word=%E7%8C%AB
Accept: application/json, text/plain, */*
```

响应头（值得注意的两条）：

```http
HTTP/1.1 200 OK
Content-Type: application/json
Access-Control-Allow-Origin: https://image.baidu.com
Access-Control-Allow-Credentials: true
Bdqid: 7cc748a2122f5c47
Lid: 7cc748a2122f5c47
```

`Access-Control-Allow-Origin` 被锁定为 `https://image.baidu.com`，所以**跨域页面无法直接读这个接口**（CORS 会拦），只能在同源页面内调用。

## 请求示例

```bash
curl -sS \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://image.baidu.com/' \
  'https://image.baidu.com/search/acjson?tn=resultjson_com&word=%E7%8C%AB&pn=30&rn=30&gsm=1e'
```

## 返回示例

外部客户端（curl）得到 **HTTP 200 + 拒绝 JSON**，83 字节：

```json
{"antiFlag":1,"message":"Forbid spider access","bfe_log_id":"10155720265341393354"}
```

| 字段 | 说明 |
|---|---|
| `antiFlag` | `1` = 命中反爬。**这是关键判据**：HTTP 200 但内容不是结果 |
| `message` | `Forbid spider access`，服务端明示拒绝 |
| `bfe_log_id` | 请求追踪 ID，反馈问题时可提供 |

在 headless 浏览器（`HeadlessChrome/156` UA）里，同一个请求返回 **200 且响应体为空**（`len=0`）。

这两种表现都是拒绝，不是"参数不对"：换成浏览器 UA、补 `applid`、改 `gsm` 都不会变成正常结果。正常结果只会在被认可的真实浏览器会话里出现，本仓库不记录获取它的方式。

## 说明与限制

1. **首屏不走这个接口。** 浏览器打开 `/search/index?tn=baiduimage&word=` 时，首屏图片由服务端渲染进 HTML；接口从 `pn=30` 才开始用。所以"接口"与"页面结构"是两套数据源。
2. **`antiFlag` 必须当失败处理。** 任何只判断 `status == 200` 的客户端都会把拒绝当成功。
3. `gsm` 与 `pn` 的十六进制对应是可验证的规律（两个样本），但未做穷举验证，不要据此构造非常规偏移。
4. CORS 锁定同源，跨域页面拿不到（这是服务端的正常配置，不是 bug）。
5. 未验证：`rn` 上限、`pn` 上限、`gsm` 缺失时的行为、是否有尺寸/颜色过滤器参数。本次环境没有拿到正常响应，所以这些一律不写。

## 合规状态

`https://image.baidu.com/robots.txt`（50 行）：

```
User-agent: Baiduspider
Allow: /
Disallow: /pcdutu
…

User-agent: *
Disallow: /
```

对通配代理是全站 `Disallow: /`。接口层再用 `antiFlag` 做二次拦截 —— 意愿与技术两道门是一致的。

本文件记录契约与拒绝信号，不提供采集、不提供绕过。

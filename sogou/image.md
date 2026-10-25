# 搜狗 · 图片搜索（JSON）

## 请求方式

```http
GET https://pic.sogou.com/napi/pc/searchList?mode=1&start=0&xml_len=48&query=<query>
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `query` | 是 | 查询词，URL 编码 |
| `mode` | 是 | `1`（图片搜索模式）。其它取值未验证 |
| `start` | 是 | 起始偏移，`0` 起。步进应为 `xml_len`，**未验证**（未取得正常响应） |
| `xml_len` | 是 | 请求条数，本次 `48` |

## 请求头

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36
Referer: https://pic.sogou.com/
Accept: application/json, text/plain, */*
```

## 请求示例

```bash
curl -sS \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://pic.sogou.com/' \
  'https://pic.sogou.com/napi/pc/searchList?mode=1&start=0&xml_len=48&query=%E7%8C%AB'
```

## 返回示例

```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
```

响应体 40 字节：

```json
{"status":1,"info":"forbid","data":null}
```

| 字段 | 说明 |
|---|---|
| `status` | `1` 表示**拒绝**（不是"成功"）。正常响应应为 `0` 并带 `data` —— 该正常结构本仓库未取得，不做推测 |
| `info` | `forbid`，服务端明示拒绝 |
| `data` | `null` |

这是四家里最容易误判的一种拒绝：**HTTP 200 + 合法 JSON + 结构规整**，只有 `status`/`data` 两个字段暴露了真相。任何"200 就解析 `data`"的代码都会在 `null` 上崩掉。

## 页面侧观察

用真实浏览器（headless）打开 `https://pic.sogou.com/pics?query=猫` 时，**没有观察到对 `/napi/pc/searchList` 的请求** —— 首屏图片由服务端渲染进 HTML，接口只用于后续加载。因此本仓库也没有该接口的正常响应样本。

## 说明与限制

1. 拒绝是确定性的：换 UA、补 Referer、改 `start` 都不会改变结果。不要把它当参数问题排查。
2. 正常响应的字段结构**未验证**。网上流传的字段名（如 `picUrl`、`thumbUrl`、`width`、`height`）本仓库不予采信、不予列出 —— 没实测过的不写。
3. `start` 的步进关系未知，分页语义未知。

## 合规状态

`https://pic.sogou.com/robots.txt`（26 行，只有通配段）：

```
User-agent: *
Allow: /imgcate/
Allow: /help/
Allow: /fuwu/
Allow: /cate/
Allow: /venus/
Allow: /index.html
Disallow: /pics
Disallow: /pics?
…
Disallow: /napi
Disallow: /ris
Disallow: /ipics
Disallow: /idetail
```

**`/napi` 明确在禁止列表内。** 这是"白名单式"robots：只放行 6 个目录，其余一律禁止。

本文件记录接口形态与拒绝信号，不提供采集与绕过。

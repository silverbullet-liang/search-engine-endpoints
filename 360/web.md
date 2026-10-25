# 360 · Web 搜索

## 请求方式

```http
GET https://www.so.com/s?q=<query>&src=<来源标记>
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `q` | 是 | 查询词，需 URL 编码 |
| `src` | 否 | 来源标记。被风控跳转时服务端会写入 `src=captcha` |
| `pn` | 否 | 页码。**未验证**：本次环境未取得正常结果页，无法确认其语义 |
| `ie` | 否 | 编码，`utf-8` |

## 请求头

实测使用的请求头（记录用，非"推荐值"）：

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36
Referer: https://www.so.com/
Accept: text/html,application/xhtml+xml
Accept-Language: zh-CN,zh;q=0.9
```

## 请求示例

```bash
curl -sS -D - -o /dev/null \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://www.so.com/' \
  'https://www.so.com/s?q=test'
```

## 返回示例

本次环境（curl 与真实浏览器一致）返回 **302**，不是结果页：

```http
HTTP/1.1 302 Found
Location: http://qcaptcha.so.com/?ret=https%3A%2F%2Fwww.so.com%2Fs%3Fq%3Dtest%26src%3Dcaptcha&tk=637949005982971707507298924113098
```

响应体 0 字节。跟随跳转后落地页 `<title>` 为 `访问异常页面`，正文：

```
请输入验证码以便正常访问
网络或服务器异常
您的IP是：49.235.105.51
您使用的浏览器是：Mozilla/5.0 (X11; Linux x86_64) …
```

`tk` 每次请求不同，是验证码会话票据，无复用价值。

## 说明

1. **这是验证码拦截，不是参数错误。** 换参数、补 Referer、换 UA 都不会改变结果 —— 判据是来源 IP 与客户端环境，不是请求内容。
2. 本次用**真实浏览器**（非 curl）访问同一 URL，同样落到 `qcaptcha`，说明该出口 IP 整体处于风控状态。不同网络环境下的结果会不同，本记录不能外推。
3. 因此本仓库**没有** 360 Web 结果页的 HTML 结构记录：拿不到真实结果页，就不编造结构。
4. 拦截页明示了判定依据（IP + 浏览器指纹）。绕过它属于"规避技术措施"，不在本仓库范围内，见 [NOTICE.md](../NOTICE.md) 第 3 节。

## 合规状态

`https://www.so.com/robots.txt`：

```
User-agent: *
Disallow: /s
Disallow: /link
Disallow: /brw
```

`/s` 对通配代理明确禁止。本文件记录端点形态与拒绝信号，不提供采集用途的用法。

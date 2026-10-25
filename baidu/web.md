# 百度 · Web 搜索

## 请求方式

```http
GET https://www.baidu.com/s?wd=<query>&ie=utf-8
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `wd` | 是 | 查询词，URL 编码 |
| `ie` | 否 | 输入编码，`utf-8` 或 `gbk` |
| `rn` | 否 | 每页条数。**未验证**：本次环境未取得结果页，无法确认语义 |
| `pn` | 否 | 起始偏移。**未验证**，原因同上 |
| `tn` | 否 | 结果页模板，如 `baiduhome_pg`、`index`。未验证 |
| `rsv_spt` `f` `rsv_pq` | 否 | 内部标记，未见影响 |

`rn` / `pn` 这类分页参数**没有实测结论** —— 拿不到正常结果页就不写。这是本仓库的规矩。

## 请求头

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36
Referer: https://www.baidu.com/
Accept: text/html,application/xhtml+xml
Accept-Language: zh-CN,zh;q=0.9
```

## 请求示例

```bash
curl -sS -D - -o /dev/null \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://www.baidu.com/' \
  'https://www.baidu.com/s?wd=test'
```

## 返回示例

外部 HTTP 客户端拿到 **302**（不是结果页）：

```http
HTTP/1.1 302 Found
Location: https://wappass.baidu.com/static/captcha/tuxing_v2.html?&logid=8955532809027633370
          &ak=c27bbc89afca0463650ac9bde68ebe06
          &backurl=https%3A%2F%2Fwww.baidu.com%2Fs%3Fwd%3Dtest
          &ext=x9G9QDmMXq%2FNo87gjGO0P3dtEn33CQi4lxdPt6U…
          &signature=2d587565ad3cdea241df38605aec4664
          &timestamp=1792895283
Content-Type: text/html; charset=utf-8
```

响应体 416 字节：

```html
<a href="https://wappass.baidu.com/static/captcha/tuxing_v2.html?&amp;logid=…">Found</a>.
```

`tuxing_v2` 是图形验证码页。参数含义（按字面推断，未验证）：`logid` 请求日志 ID、`ak` 应用标识（固定值）、`backurl` 验证后回跳地址、`ext` 加密上下文、`signature` 签名、`timestamp` 秒级时间戳。

## 同一 URL 在真实浏览器里

```
location.href  https://www.baidu.com/s?wd=test
document.title test_百度搜索
body.scrollHeight 3232
body.innerText  "百度一下 百度首页设置登录 网页 图片 资讯 视频 笔记 地图 贴吧 文库 更多 搜索工具 相关搜索 test的用法和搭配 …"
```

**结论：同一个 URL，curl 302 到验证码，浏览器 200 正常返回结果。**

判定依据是客户端环境（TLS/HTTP2 指纹、浏览器行为特征），不是 IP —— 同一台机器、同一个出口 IP，只是换了客户端。

这也意味着：本仓库无法给出 `/s` 的 HTML 结果结构。**拿不到真实结果页，就不编造选择器。**

## 说明与限制

1. 302 的 `Location` 每次都不同（`logid`、`ext`、`signature`、`timestamp` 变化），不可复用。
2. 页面需要 JS 才能完整渲染（浏览器里 `scrollHeight` 3232，含异步模块），纯 HTML 解析即便拿到响应也不完整。
3. 想稳定取百度搜索结果，唯一正当路径是官方 API（百度智能云千帆/搜索开放平台），不是这个端点。
4. 本文件不提供任何"让 curl 变成浏览器"的方法。

## 合规状态

`https://www.baidu.com/robots.txt`（165 行，16 个 `User-agent` 段）：

```
User-agent: Baiduspider
Disallow: /baidu
Disallow: /s?
…
User-agent: *
Disallow: /
```

对通配代理是 `Disallow: /`。`/s` 亦在具名爬虫段的禁止列表中。

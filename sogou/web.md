# 搜狗 · Web 搜索

## 请求方式

```http
GET https://www.sogou.com/web?query=<query>&ie=utf8
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `query` | 是 | 查询词，URL 编码 |
| `ie` | 否 | 编码，`utf8` / `gbk` |
| `page` | 否 | 页码。**未验证**：本次未取得结果页 |
| `_asf` `_ast` | 否 | 内部标记。未验证 |

## 请求头

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36
Referer: https://www.sogou.com/
Accept: text/html,application/xhtml+xml
```

## 请求示例

```bash
curl -sS -D - -o /dev/null \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://www.sogou.com/' \
  'https://www.sogou.com/web?query=test'
```

## 返回示例

```http
HTTP/1.1 302 Found
Location: http://www.sogou.com/antispider/?m=1&antip=web_sh2&from=%2Fweb%3Fquery%3Dtest&suuid=1fc84ebf-3ff3-4c9b-b0a2-5116fd559696
Content-Type: text/html; charset=utf-8
```

响应体 295 字节：

```html
Redirecting to <a href="http://www.sogou.com/antispider/?m=1&amp;antip=web_sh2&amp;from=%2Fweb%3Fquery%3Dtest&amp;suuid=1fc84ebf-3ff3-4c9b-b0a2-5116fd559696">http://www.sogou.com/antispider/?m=1&amp;antip=web_sh2&amp;from=%2Fweb%3Fquery%3Dtest&amp;suuid=1fc84ebf-3ff3-4c9b-b0a2-5116fd559696</a>.
```

## 字段说明

| 参数 | 说明 |
|---|---|
| `m` | `1`，跳转标记 |
| `antip` | 触发的规则名，本次为 `web_sh2` |
| `from` | 原始请求路径（URL 编码） |
| `suuid` | 验证会话 UUID，每次请求不同 |

## 落地页（`/antispider/`）

真实浏览器访问同一 URL 也会落到这里，页面内容：

```
返回首页>>  IP：223.74.76.56  访问时间：2026.10.25 10:26:11  SourceVerifyCode：2998e5a7284c
```

`SourceVerifyCode` 与跳转参数里的 `suuid` 是同一套会话标识（值不同是因为两次请求不同）。

注意：本次浏览器出口 IP（`223.74.76.56`）与 curl 出口（`49.235.105.51`）不同 —— 沙箱有多出口，取哪台由环境决定。这解释了为什么同一天内不同工具的拦截结果会不一致。

## 说明与限制

1. **判定对象是 IP + 客户端环境**，两者任一不合格都会跳 `antispider`。
2. 本次 curl 与真实浏览器**都被拦**，所以本仓库没有搜狗 Web 结果页的 HTML 结构记录。拿不到就不编。
3. `/antispider/` 页面本身是可访问的（200），但它只是拦截说明，不含结果。
4. `page` 参数未验证：没拿到正常结果页，无法确认其语义与上限。

## 合规状态

`https://www.sogou.com/robots.txt`（520 行，15 个 `User-agent` 段）末尾：

```
User-agent: *
Disallow: /
```

对通配代理全站禁止。`/web?` 亦在具名爬虫段的 Disallow 列表中。

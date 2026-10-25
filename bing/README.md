# Bing / 必应

四家里端点最多、也是唯一提供**可用图片分页接口**的一家。

> **合规提示**：`www.bing.com/robots.txt` 对通配代理明确 Disallow 了 `/search`、`/images/async?`、`/images/search?`、`/th?` 等本目录记录的全部搜索端点。本目录是接口契约的事实记录，不是采集工具。

---

## 可用性矩阵（2026-10-25 实测）

| 端点 | 协议 | 可用性 |
|---|---|---|
| `GET /search?q=` | HTML | 仅第 1 页；`first` 对外部客户端无效 |
| `GET /search?q=&format=rss` | XML | 可用，固定 10 条 |
| `GET /images/search?q=` | HTML | 仅首屏 35 条 |
| `GET /images/async?q=&first=&count=` | HTML 片段 | **可用，支持 `first` 翻页**（需会话 Cookie） |
| `GET /AS/Suggestions` | HTML 片段 | 可用 |
| `GET /OSJSON.aspx?query=` | JSON | 可用 |
| `GET /instantsearch/getquerylist?query=` | JSON | 可用（需 Referer） |

## 合规状态（robots.txt 原文，节选）

`https://www.bing.com/robots.txt`（108 行）：

```
User-agent: *
Disallow: /search
Disallow: /Search
Disallow: /images/async?
Disallow: /images/search?
Disallow: /images/searchbyimage
Disallow: /api/
Disallow: /th?
Disallow: /th$
Disallow: /copilotsearch?q=
Disallow: /url
```

另外，RSS 输出内嵌一段版权声明，限制的是**结果内容的使用与再分发**（不只是抓取），原文见仓库根目录 [NOTICE.md](../NOTICE.md) 第 2.2 节。

## 文档索引

| 文件 | 内容 |
|---|---|
| [web.md](web.md) | `/search` 参数有效性、HTML 结构、RSS 变体、`first` 为何对外部客户端无效 |
| [image.md](image.md) | 两个图片端点、`first` 语义、`qft` 过滤器、剥离实验、片段结构 |
| [suggest.md](suggest.md) | `/AS/Suggestions`（HTML 片段）与 `/OSJSON.aspx`（OpenSearch JSON） |
| [related-queries.md](related-queries.md) | `/instantsearch/getquerylist` 与它的 Referer/Accept 契约 |
| [fields.md](fields.md) | 字段字典：`iusc.m` 的 11 个键、缩略图 URL 构成、私有区高亮字符 |
| [session.md](session.md) | 会话要求与降级判据（同一 URL 两种响应） |
| [method.md](method.md) | 实验方法论：找线索 → 抓实际 → 剥离验证 |

## 与其他三家的差异

| 维度 | Bing | 百度 | 360 | 搜狗 |
|---|---|---|---|---|
| 图片接口可分页 | ✅ `/images/async` | ✗（`antiFlag`） | ✗（累积集合，非分页） | ✗（`forbid`） |
| Web 结果页外部可取 | ✗（仅第 1 页） | ✗（302 验证码） | ✗（302 验证码） | ✗（302 antispider） |
| 联想接口可用 | ✅ | ✅ | ✅ | ✗（0 字节） |
| 返回格式 | 全部 HTML（除两个 JSON） | JSON / JSONP | JSON | — |

Bing 的特殊之处在于：它把分页做成了**片段级接口**，而其他三家把分页藏在文档级导航里。片段级接口的风控宽松得多，这就是为什么只有 Bing 的图片分页能被外部客户端复现。

## 免责声明

- 与 Microsoft 无关联，未获授权或背书。
- 不提供采集工具，不提供指纹伪装、IP 轮换、验证码绕过方法。
- 数值带实测日期与环境；不同出口地区的端点路径与结果会不同。
- 完整边界见仓库根目录 [NOTICE.md](../NOTICE.md)。

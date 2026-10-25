# 百度搜索（baidu.com）

三个端点的实测记录：Web 结果页、图片 JSON 接口、输入联想（两个）。

> **合规提示**：`www.baidu.com` 与 `image.baidu.com` 的 `robots.txt` 对通配代理（`User-agent: *`）均为 **`Disallow: /`**（全站禁止）。该站只对名单内的搜索引擎爬虫单独开口子。本目录是接口事实记录，不是采集工具。

---

## 可用性矩阵（2026-10-25 实测）

| 端点 | 协议 | curl | 真实浏览器 |
|---|---|---|---|
| `GET https://www.baidu.com/s?wd=` | HTML | **302 → 验证码** | **200 正常结果** |
| `GET https://image.baidu.com/search/acjson` | JSON | **200 但拒绝** | 响应体未取得¹ |
| `GET https://www.baidu.com/sugrec?prod=pc&wd=` | JSON | **200 可用** | 可用 |
| `GET https://suggestion.baidu.com/su?wd=&cb=` | JSONP（GBK） | **200 可用** | 可用 |

¹ 该接口在 headless 浏览器里发出的请求响应体为空（`len=0`），首屏图片由服务端渲染在 HTML 里，接口只用于翻页。本仓库不记录获取该响应的规避方式。

百度是三家里唯一"Web 结果页在真实浏览器里可用"的 —— 风控判定对象是客户端环境，不是 IP。

## 合规状态（robots.txt 原文）

`https://www.baidu.com/robots.txt` 共 165 行，包含 16 个 `User-agent` 段，末尾是通配段：

```
User-agent: *
Disallow: /
```

`https://image.baidu.com/robots.txt` 共 50 行，15 个 `User-agent` 段。注意它给各家爬虫的是 `Allow: /`：

```
User-agent: Baiduspider
Allow: /
Disallow: /pcdutu
…
User-agent: Googlebot
Allow: /
…
User-agent: *
Disallow: /
```

两条必须看清：

1. 对**具名**搜索引擎爬虫基本全站放行；
2. 对**通配代理**（也就是任何未报名的客户端）是 `Disallow: /`，全站禁止。

所以"百度允许抓取"这句话只对被认可的爬虫成立。第三方程序属于通配，落在 `Disallow: /` 之内。

## 文档

| 文件 | 内容 |
|---|---|
| [web.md](web.md) | `/s` 参数、验证码跳转与浏览器侧对照 |
| [image.md](image.md) | `acjson` 完整参数（浏览器观测）、拒绝响应、`antiFlag` 判据 |
| [suggest.md](suggest.md) | `sugrec`（JSON）与 `su`（JSONP/GBK） |

## 免责声明

- 与百度 / 北京百度网讯科技无任何关联，未获授权或背书。
- 不提供采集工具，不提供绕过 `wappass` / `antiFlag` 验证的方法，不提供指纹或 IP 伪装方法。
- 端点无版本、无 SLA；数值带实测日期，环境不同结论可能不同（尤其风控相关结论）。
- 完整边界见仓库根目录 [NOTICE.md](../NOTICE.md)。

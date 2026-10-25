# 360 搜索（so.com）

三个端点的实测记录：Web 结果页、图片 JSON 接口、输入联想。

> **合规提示**：本目录记录的 `/s` 与 `/j` 在 `image.so.com` / `www.so.com` 的 `robots.txt` 中均被 `User-agent: *` 明确 Disallow（原文见下）。本目录是**接口事实记录**，不是采集工具。任何自动化采集都与该站公开表达的意愿冲突。

---

## 可用性矩阵（2026-10-25 实测）

| 端点 | 协议 | 状态 | 说明 |
|---|---|---|---|
| `POST/GET https://www.so.com/s?q=` | HTML | **302 → 验证码** | 非浏览器客户端被导向 `qcaptcha.so.com` |
| `GET https://image.so.com/j?q=&pn=&rn=&src=srp` | JSON | **200 可用** | 本仓库四家里唯一可直接取到图片结构化数据的接口 |
| `GET https://sug.so.360.cn/suggest?word=` | JSON | **200 可用** | 10 条纯文本建议 |

## 合规状态（robots.txt 原文）

`https://www.so.com/robots.txt`（全文 4 行）：

```
User-agent: *
Disallow: /s
Disallow: /link
Disallow: /brw
```

`https://image.so.com/robots.txt`（全文 6 行）：

```
User-agent: *
Disallow: /j?
Disallow: /i?
Disallow: /z?
Disallow: /zv?
Disallow: /zj?
```

两点必须看清：

1. 这份 robots **只针对通配代理**（没有为各家搜索引擎单独开口子），所以"我是普通用户"不能作为例外。
2. 唯一可用的图片接口 `/j` **恰好**在禁止列表里（`Disallow: /j?`）。"技术上能调通"与"被允许自动化访问"是两件事。

## 文档

| 文件 | 内容 |
|---|---|
| [web.md](web.md) | `/s` 结果页与验证码跳转 |
| [image.md](image.md) | `image.so.com/j` 参数、20 个顶层键、33 个结果字段、分页语义 |
| [suggest.md](suggest.md) | `sug.so.360.cn/suggest` JSON 结构 |

## 免责声明

本目录内容为公开可观测的 HTTP 接口事实记录，用于互操作性研究与技术分析。

- 与 360 / 奇虎科技无任何关联，未获授权或背书。
- 不提供采集工具、不提供绕过验证码（`qcaptcha`）的方法、不提供指纹或 IP 伪装方法。
- 端点无版本、无 SLA，随时变更；所有数值带实测日期，过期即失效。
- 依赖这些端点做产品，等于把可用性押在明确不欢迎自动化访问的第三方服务上。
- 完整边界见仓库根目录 [NOTICE.md](../NOTICE.md)。

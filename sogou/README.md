# 搜狗搜索（sogou.com）

三个端点的实测记录。**本引擎在当前环境三端点全部被拦截** —— 记录的重点是"拒绝长什么样"，以及不要把它们误判为成功。

> **合规提示**：`www.sogou.com` 与 `pic.sogou.com` 的 `robots.txt` 对通配代理分别为 `Disallow: /` 与包含 `Disallow: /napi` 的白名单式规则。本目录是拒绝行为与接口形态的记录，不提供采集或绕过方式。

---

## 可用性矩阵（2026-10-25 实测）

| 端点 | 协议 | 结果 |
|---|---|---|
| `GET https://www.sogou.com/web?query=` | HTML | **302 → `/antispider/`** |
| `GET https://pic.sogou.com/napi/pc/searchList` | JSON | **200 但 `info: forbid`** |
| `GET https://www.sogou.com/suggnew/ajajjson` | JSON | **200 但 0 字节** |

三种不同的拒绝形态，都值得认识 —— 它们的共同点是**看起来像成功**（除 Web 的 302 外，其余两个都是 HTTP 200）。

## 合规状态（robots.txt 原文）

`https://www.sogou.com/robots.txt`：520 行，15 个 `User-agent` 段（自家各产品线爬虫 + Googlebot / MSNBot / Baiduspider / 360spider 等），末尾：

```
User-agent: *
Disallow: /
```

`https://pic.sogou.com/robots.txt`：26 行，只有通配段：

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
Disallow: /d
Disallow: /d?
Disallow: /websnapshot.do?
Disallow: /websearch/
Disallow: /xml?
Disallow: /pic
Disallow: /napi
Disallow: /ris
Disallow: /ipics
Disallow: /idetail
…
```

图片站是"白名单式"：只放行 6 个目录，其余全禁，且 **`/napi` 在禁止列表里**（正是那个 JSON 接口）。

## 文档

| 文件 | 内容 |
|---|---|
| [web.md](web.md) | `/web` 与 `antispider` 跳转、`suuid`/`SourceVerifyCode` 字段 |
| [image.md](image.md) | `napi/pc/searchList` 参数与 `forbid` 响应 |
| [suggest.md](suggest.md) | `suggnew/ajajjson` 的空响应现象 |

## 免责声明

- 与搜狗 / 北京搜狗科技无任何关联，未获授权或背书。
- 不提供采集工具，不提供绕过 `antispider` 的方法。
- 端点无版本、无 SLA；风控结论与出口 IP 强相关，换环境可能不同。
- 完整边界见仓库根目录 [NOTICE.md](../NOTICE.md)。

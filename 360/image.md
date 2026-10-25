# 360 · 图片搜索（JSON）

四家里唯一能直接取到结构化图片数据的接口。返回 JSON，字段完整度高于 HTML 解析。

## 请求方式

```http
GET https://image.so.com/j?q=<query>&pn=<已加载条数>&rn=<请求条数>&src=srp
```

| 参数 | 必填 | 实测行为 |
|---|---|---|
| `q` | 是 | 查询词，URL 编码 |
| `pn` | 建议 | **不是页码，是"已加载条数"**（见"分页语义"） |
| `rn` | 建议 | 请求条数。**实测被忽略**：`rn=30` 与 `rn=60` 返回条数差 ≤2 |
| `src` | 否 | 来源标记，`srp` 为结果页 |

响应头：

```http
HTTP/2 200
Content-Type: application/javascript; charset=utf-8
```

注意是 `application/javascript` 而不是 `application/json` —— 解析时不要按 `Content-Type` 判断，直接 `json.loads` 即可。

## 请求头

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36
Referer: https://image.so.com/
Accept: */*
```

## 请求示例

```bash
curl -sS \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://image.so.com/' \
  'https://image.so.com/j?q=%E7%8C%AB&pn=0&rn=30&src=srp' -o so.json
```

## 返回示例

单次响应约 124 KB。结构（字段名真实，取值已替换为示例域）：

```json
{
  "total": 1216,
  "end": false,
  "sid": "8b6dcd93b079…",
  "list": [
    {
      "id": "6a26067faa1f5a64a8a6ca217d25c510",
      "title": "示例标题",
      "litetitle": "",
      "width": "2048",
      "height": "1280",
      "imgsize": "160KB",
      "imgtype": "JPEG",
      "link": "http://p0.so.qhimg.com/t047d76cf7628f4758f.jpg",
      "img": "http://p0.so.qhimg.com/t047d76cf7628f4758f.jpg",
      "thumb": "https://p5.ssl.qhimgs1.com/t047d76cf7628f4758f.jpg",
      "_thumb": "https://p5.ssl.qhimgs1.com/sdr/_240_/t047d76cf7628f4758f.jpg",
      "thumbWidth": "384",
      "thumbHeight": "240",
      "site": "p0.so.qhimg.com",
      "dspurl": "p0.so.qhimg.com",
      "http": "p5.so.qhimg.com",
      "https": "p5.ssl.qhimgs1.com",
      "imgkey": "t047d76cf7628f4758f.jpg",
      "self_key": "8ae8d5adfac6085ca144130bc20540e7.jpg",
      "key": "d2d722580f",
      "index": "0",
      "type": "0",
      "src": "60",
      "source": "copyright_text_aigc",
      "copyright_owner": "0",
      "p_cluster": "861"
    }
  ],
  "boxresult": {},
  "wordguess": [],
  "prevsn": "",
  "lastindex": 0
}
```

## 顶层字段（实测 22 个）

| 字段 | 类型 | 说明 |
|---|---|---|
| `total` | int | 结果总数。**同一查询多次请求会浮动**（实测 1216 / 1222 / 1244），不能当精确值 |
| `end` | bool | 是否到底。`false` 表示还能继续加 |
| `sid` | string | 会话 ID |
| `list` | array | 结果数组，见下 |
| `lastindex` | int | 最后一条的序号 |
| `boxresult` | object | 聚合卡/专题位，本次为空对象 |
| `wordguess` | array | 相关搜索词，本次为空 |
| `sens` `pornn` | — | 内容分级/敏感度标记 |
| `ran` `ras` `cuben` `manun` `kn` `cn` `gn` `ps` `pc` `adstar` `query_class` `ceg` `prevsn` | — | 服务端内部状态，语义未验证，取数据时忽略即可 |

## 结果字段（`list[]`，实测 38 个键）

| 字段 | 说明 |
|---|---|
| `id` | 结果唯一标识，32 位十六进制 —— **去重就用它** |
| `title` | 标题，可能含站点名后缀 |
| `litetitle` | 短标题，常为空 |
| `width` `height` | 原图像素尺寸（**字符串**，不是数字） |
| `imgsize` | 原图体积文案，如 `160KB` |
| `imgtype` | 格式，如 `JPEG` / `PNG` |
| `link` | 原图直链（`http://`，多为 360 自家 CDN） |
| `img` | 与 `link` 同值（历史遗留的重复字段） |
| `thumb` | 缩略图直链（`https://`） |
| `_thumb` | 带尺寸前缀的缩略图，如 `/sdr/_240_/…` —— **列表场景用这个** |
| `thumb_bak` / `_thumb_bak` | 与 `thumb` / `_thumb` 同值的备份字段 |
| `grpcnt` | 字符串 `"False"` |
| `thumbWidth` `thumbHeight` | 缩略图尺寸（字符串） |
| `site` / `dspurl` | 展示用域名 |
| `http` / `https` | CDN 主机名（无协议前缀） |
| `imgkey` | CDN 上的文件名 |
| `self_key` | 内容键（含扩展名），跨查询稳定，可作备用去重键 |
| `key` | 10 位短键 |
| `index` | 序号（字符串）。**实测可出现重复值**（见下） |
| `type` / `src` / `color` | 内部类型与筛选项编码，未验证 |
| `source` | 来源/版权标记，如 `copyright_text_aigc` |
| `copyright_owner` | 版权方编码，`0` 表示无 |
| `p_cluster` | 聚类号，同组图片共享 |
| `grpmd5` / `downurl` / `qqface_down_url` | 实测恒为字符串 `"False"`，是历史遗留的布尔占位 |
| `downurl_true` / `dsptime` / `comm_purl` | 实测恒为空串 |
| `fnum` | 字符串 `"0"` |
| `fixedSize` | 字符串 `"False"` |

`"False"` 这类**字符串化的布尔**是这套接口最容易踩的坑：`if (item["grpmd5"])` 在 Python 里恒为真（非空字符串）。判断时必须显式比较字符串。

## 分页语义（重要）

`pn` 不是页码。实测三组：

| 请求 | `list` 条数 | `index` 首/末 | 与上一组重叠 |
|---|---|---|---|
| `pn=0&rn=30` | 85 | 0 / 49 | — |
| `pn=30&rn=30` | 176 | 0 / 140 | 85（全部包含） |
| `pn=60&rn=30` | 234 | 0 / 140+ | 全部包含 |

三条结论：

1. **`list` 是累积集合，不是本页增量。** `pn=30` 的响应包含 `pn=0` 的全部结果。
2. **`pn` 增大时顺序会重排。** 两次响应的前 3 条 `id` 不完全相同（同一批内容，排序不同）。
3. **`rn` 无效。** 服务端按自己的节奏给量（一屏约 85–110 条，随 `pn` 增长）。

实践含义：

- 去重必须用 `id`（或 `self_key`），不能用数组位置。
- "下一页"不是加 `pn=1`、`pn=2`，而是累加"已拿到的条数"。
- 判断到底看 `end`，不要看"条数是否变少"。

`index` 字段实测出现重复序列（`[0,0,0,1,0,2,0,3…]`），语义未验证，不要用它做游标。

## 说明与限制

1. **接口对非浏览器客户端开放**（curl 直接可用），这与该站的 Web 搜索端点形成对比。
2. 返回的是 360 自家 CDN 的图（`qhimg.com` / `qhimgs1.com`），不是第三方站点原图 —— 热链风险低于 Bing，但**仍应缓存到自己的存储**，不要在生产环境直接引用。
3. `total` 数字不可信（浮动 ±30），分页不能按 `total` 计算页数。
4. 未验证：`q` 为空的行为、`pn` 上限、是否有尺寸/颜色/类型过滤器参数。本次环境未取得 Web 结果页，无法从页面控件反查这些参数名。

## 合规状态

`https://image.so.com/robots.txt`：

```
User-agent: *
Disallow: /j?
Disallow: /i?
Disallow: /z?
Disallow: /zv?
Disallow: /zj?
```

**`/j?` 正是本文件记录的接口，且被通配代理明确禁止。**

因此：本文件是接口契约的事实记录，用于互操作性研究。不提供批量采集、不提供循环翻页脚本、不提供结果再分发。技术上可调用不等于被授权自动化访问 —— 这条判断留给读者，但本仓库的立场在 [NOTICE.md](../NOTICE.md) 第 3 节。

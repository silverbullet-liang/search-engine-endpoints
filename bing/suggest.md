# 03 · 输入联想（搜索建议）

两个端点做同一件事，格式完全不同。选哪个取决于你要不要 JSON。

| 端点 | `Content-Type` | 实际返回 | 条数 | 需要 Referer |
|---|---|---|---|---|
| `/AS/Suggestions` | `application/json` | **HTML `<ul>` 片段** | 12（zh-CN）/ 10（en-US） | 否 |
| `/OSJSON.aspx` | `application/json` | 真 JSON（OpenSearch 兼容） | 12 | 否 |

`/AS/Suggestions` 的 `Content-Type` 声明与内容不符是服务端行为 —— 它在 2026-10 的实测中稳定如此。不要按 `Content-Type` 选解析器。

---

## `/AS/Suggestions`

```
GET /AS/Suggestions?pt=page.home&mkt=zh-CN&qry=<typed>&cp=<len>&cvid=<id>
```

| 参数 | 语义 | 必需 |
|---|---|---|
| `qry` | 已输入文本 | 是 |
| `pt` | 输入位置，如 `page.home`、`page.result` | 是 |
| `mkt` | 市场，如 `zh-CN` | 是（缺失时返回 400） |
| `cp` | 光标位置（字符数），即 `len(qry)` | 是（缺失 → 400 `application/json` 空体） |
| `cvid` | 会话内查询 ID，16 位十六进制 | 是（可随手生成，服务端会回填到结果 URL 里） |

实际踩过的坑：只带 `pt & qry` 会返回 **400**，必须凑齐 `mkt`、`cp`、`cvid`。

### 响应

```html
<ul class="sa_drw" id="sa_ul" role="listbox" data-priority="2" aria-label="建议">
  <li class="sa_sg" role="option" id="sa_5006"
      url="/search?q=catti&amp;qs=MT&amp;pq=cat&amp;sk=MT1&amp;sc=12-3&amp;cvid=1A2B3C4D5E6F&amp;FORM=QBLH"
      query="catti" stype="MT" h="ID=autosuggest,5006.1">
    <div class="sa_sg_icon_area"><div class="sa_sg_icon sa_sg_searchicon_rdc"></div></div>
    <div class="sa_tm"><span class="sa_tm_text">cat<strong>ti</strong></span></div>
  </li>
  …
</ul>
```

| 属性 / 元素 | 内容 |
|---|---|
| `li.sa_sg[query]` | 建议文本（原始值，未高亮） |
| `li.sa_sg[url]` | 点击后跳转的相对 URL（含 `qs`/`pq`/`sk`/`sc`/`cvid` 连续性参数） |
| `li.sa_sg[stype]` | 建议类型。实测取值 `MT` / `FT` / `LT`，语义未公开，推测与匹配方式有关，**未验证** |
| `li.sa_sg[id]` | `sa_<序号>`，从 5005 起递增 |
| `li.sa_sg[h]` | 内部埋点标识（`ID=autosuggest,<序号>.<位置>`），无业务含义 |
| `span.sa_tm_text` | 高亮后的展示文本，匹配部分包在 `<strong>` 里 |

高亮用 `<strong>` 而不是私有区字符，这点与图片结果的 `desc` 不同（见 `fields.md`）。

`url` 属性里的 `&amp;` 必须反转义后才能当查询参数用。

---

## `/OSJSON.aspx`

```
GET /OSJSON.aspx?query=<typed>&form=OSDJAS
```

返回 OpenSearch Suggestions 兼容格式（Google 的同名格式）：

```json
["cat",
 ["cat","catti","cat vs dyj","catia下载","category","catena","catl","catti报名官网",
  "catalog","cat paw","cathay pacific","catime"],
 [],
 [],
 {"google:suggestrelevance":[1300,1299,1298,1297,1296,1295,1294,1293,1292,1291,1290,1289]}
]
```

| 下标 | 内容 |
|---|---|
| `[0]` | 原始查询 |
| `[1]` | 建议字符串数组（本条 12 项） |
| `[2]` | 描述数组（本端点恒为空） |
| `[3]` | URL 数组（本端点恒为空） |
| `[4]` | 元数据：`google:suggestrelevance` 为与 `[1]` 等长的相关度分数，单调递减 |

`form=OSDJAS` 不参与结果，作为来源标记保留（沿用 OpenSearch 惯例）。

优点：JSON、无 HTML 解析、无高亮标记、字段对齐直观。
缺点：没有 `stype`，没有可直接跳转的 URL，也没有 `cvid` 连续性 —— 要自己拼搜索 URL。

---

## 选择建议

- 需要**直接跳转**或想保留服务端的排序/连续性上下文 → `/AS/Suggestions`（解析 `li[query]` 与 `li[url]`）
- 只需要**字符串列表** → `/OSJSON.aspx`
- 两者都不返回图片/商品等富建议，只有纯文本

## 边界行为（实测）

**空输入不等于空响应。** 这一点最容易让解析器崩：

| 请求 | 结果 |
|---|---|
| `/AS/Suggestions?qry=&cp=0&…` | 200，5759 字节，返回完全不同的容器 `div.sa_drw_zis`（内含 `sa_zis_parent` 热门推荐模块） |
| `/OSJSON.aspx?query=&form=OSDJAS` | 200，353 字节，返回**当日热搜词**：`["",["首部龙标AI电影上映","任泽平公众号被禁关注",…],…]` |

两者都不是空数组、也不是 `ul#sa_ul`。按"建议列表"写死的解析器在空输入时会静默拿到错结构。

**条数随市场变化**：`mkt=zh-CN` 为 12 条；`mkt=en-US` 为 10 条，且 `<li>` 多一个 `sa_ent` 类（实体类建议），`url` 直接指向 `/search?q=<实体名>`。

无 `count` 参数，条数不可调。

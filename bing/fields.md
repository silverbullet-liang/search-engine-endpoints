# 05 · 字段字典

## 图片结果：`a.iusc[m]`

`m` 是 HTML 转义后的 JSON 对象，共 11 个键。实测 35 条样本中 9 个键恒非空，2 个恒为空。

| 键 | 类型 | 实测非空率 | 含义 |
|---|---|---|---|
| `cid` | string | 35/35 | 结果标识，8 字符 base64（含 `+` `/`），如 `UFcCituS` |
| `purl` | string | 35/35 | 图片**所在页面**的 URL（不是图片本身） |
| `murl` | string | 35/35 | 原图直链（第三方 CDN，非该站域名） |
| `turl` | string | 35/35 | 缩略图 URL，该站 CDN |
| `md5` | string | 35/35 | 32 位十六进制，疑为原图内容摘要，可用于跨批去重 |
| `shkey` | string | 35/35 | 44 字符 base64（尾部 `=`），用途未验证 |
| `t` | string | 35/35 | 标题（原始文本，常带站点名后缀，如 `…__财经头条`） |
| `mid` | string | 35/35 | 40 位十六进制，疑为图片内容指纹，用途未验证 |
| `desc` | string | 35/35 | 描述文本，含**私有区高亮字符**（见下） |
| `sid` | string | 0/35 | 恒为空串 |
| `cturl` | string | 0/35 | 恒为空串 |

样本（一条完整记录）：

```json
{
  "sid": "",
  "cturl": "",
  "cid": "4QyC+UNQ",
  "purl": "https://cj.sina.com.cn/articles/view/6225990601/p1731913c902",
  "murl": "https://k.sinaimg.cn/n/sinakd20120/773/w1029h1344/20240704/3…",
  "turl": "https://ts2.mm.bing.net/th?id=OIP.4QyC-UNQ0Bf4wpASK9cE2AHaJq&pid=15.1",
  "md5": "e10c82f94350d017f8c290122bd704d8",
  "shkey": "sAYpsqtlRIgGxhOq718I+68H0y3rv5fM9i/s4i6T68A=",
  "t": "新手养猫必看！猫咪品种大搜罗__财经头条",
  "mid": "06BDEF4AB881C8A875315125F9B949FEF384F76D",
  "desc": "新手养\ue000猫\ue001必看！猫咪品种大搜罗__财经头条"
}
```

### 去重键怎么选

- `cid`：**同一批次内**唯一，跨批次会变（同一张图在 `first=1` 与 `first=36` 里 `cid` 可能不同 —— 它是结果位置相关的短 ID）。
- `md5`：内容相关，跨批次稳定，是更好的去重键。
- 相邻批次实测重叠 6/35，用 `md5` 或 `murl` 去重都有效。

### `desc` 的私有区高亮字符

匹配词被 `U+E000` / `U+E001`（Unicode Private Use Area）包裹：

```
新手养\ue000猫\ue001必看！猫咪品种大搜罗__财经头条
```

- 34/35 条含这对字符。
- 直接渲染会显示为豆腐块或不可见；写进 JSON 也是非法可见字符。
- 处理方式二选一：**剥离**（`re.sub(r"[\ue000\ue001]", "", s)`），或**转成标记**（`\ue000` → `<mark>`，`\ue001` → `</mark>`）。
- 注意：`t` 字段的高亮用的是不同机制（有时完全不带标记），两个字段不要用同一套清洗逻辑。

### 缩略图 URL

```
https://ts2.mm.bing.net/th?id=OIP.4QyC-UNQ0Bf4wpASK9cE2AHaJq&pid=15.1
        └┬─┘                              └┬─┘ └──────────┬──────────┘ └──┬──┘
      分片 1-4                          固定路径        图片标识            规格参数
```

| 部分 | 说明 |
|---|---|
| `ts{1,2,3,4}.mm.bing.net` | 四台分片。同一批结果里分布均匀（本样本 10/7/7/7） |
| `ts{n}.explicit.bing.net` | 内容分级子域，本样本 4/35 命中。见 `image.md` |
| `/th` | 缩略图端点，`robots.txt` 中 `Disallow: /th?` 与 `/th$` |
| `id=OIP.<…>` | 图片标识，URL-safe base64 |
| `pid=15.1` | 规格/来源参数。改动它会得到不同尺寸的图，但取值含义未公开验证 |

`cid` 与 `OIP` 标识的关系（实测观察，**未验证为稳定规则**）：
`cid=4QyC+UNQ` 与 `id=OIP.4QyC-UNQ0Bf4wpASK9cE2AHaJq` —— `cid` 的 `+` 换成 `-` 后正好是 `OIP` 值的前 8 字符。所以 `cid` 看起来是该标识的前缀投影。不要依赖这个关系构造 URL：直接存 `turl`。

`th.bing.com` 是该 CDN 的另一个入口域名，同样出现在部分历史结果中。两者互换性未做验证。

**不要把 `murl` 当缩略图用**：它是第三方站点的原图，体积可达数 MB，且随时可能 404（对方删图）。列表场景用 `turl`。

---

## Web 结果：`li.b_algo`

| 选择器 | 内容 | 备注 |
|---|---|---|
| `li.b_algo` | 单条自然结果 | 10 条/页 |
| `h2 > a[href]` | 目标 URL | `h` 属性是内部埋点，忽略 |
| `h2 > a` 文本 | 标题 | 可能含 `<strong>` 高亮 |
| `.b_caption p` | 摘要 | class 含 `b_lineclampN`（截断行数） |
| `cite` | 展示用域名 | **不是**规范 URL，不要当链接用 |
| `span.sb_count` | 结果量级文案 | 如 `83,000 条结果`，不精确 |
| `a.sb_pagN` | 下一页 | 外部客户端点了也只回第 1 页 |

`li.b_algo` 之外的结果模块：广告（`li.b_ad`）、知识卡（`li.b_ans`）、视频卡、图片卡。取结果时必须限定 `li.b_algo`，不要用"所有 `li` 里第一个 `h2 a`"。

---

## RSS：`item`

| 元素 | 内容 |
|---|---|
| `channel > title` | `必应：<query>` |
| `channel > copyright` | 版权限制声明（原文见 `NOTICE.md`） |
| `item > title` | 标题（可能包 `CDATA`） |
| `item > link` | 目标 URL（原始，非跳转链） |
| `item > description` | 摘要，可能含 HTML 片段 |

固定 10 条。`item` 顺序即结果顺序。

---

## 通用坑

1. **`m` 与 `url` 属性都是 HTML 转义过的**（`&quot;` `&amp;`），不解转义就解析会得到一串字面量。
2. **JSON 里的 `trueSize` 是字符串**（`"4"`），不是数字。
3. **空输入返回不同结构**（见 `suggest.md`），不要假设键一定存在。
4. **同一查询的不同批次结果会漂移**，不要把"结果变了"当成"参数没生效"。

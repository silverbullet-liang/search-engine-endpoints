# 02 · 图片搜索端点

图片搜索有两个端点，分工明确：

| 端点 | 作用 | 分页 | 返回 |
|---|---|---|---|
| `/images/search` | 首屏结果页 | 否 | 完整 HTML（含外壳、脚本、样式） |
| `/images/async` | 后续批次 | **是** | HTML **片段**（无 `<html>`/`<body>`） |

**要拿数据只用 `/images/async`。** 首屏页面的 `first` 参数被忽略，永远返回第一批。

---

## `/images/async`

```
GET https://cn.bing.com/images/async?q=<query>&first=<1-based>&count=35&mmasync=1
```

### 最小可用参数

实测剥离实验（同一会话内，每次只去掉一个参数，比对结果集 `cid` 集合）：

| 组合 | 条数 | 首条 cid | 与全参数组一致 |
|---|---|---|---|
| A 全参数（`imgbf` + `dgState` + `IG` + `SFX` + `iid` + `cw/ch`） | 35 | `jue+tHyr` | — |
| B 去掉 `dgState` | 35 | `jue+tHyr` | ✅ |
| C 去掉 `imgbf` | 35 | `jue+tHyr` | ✅ |
| D 去掉 `IG` | 35 | `jue+tHyr` | ✅ |
| E 只剩 `q / first / count / mmasync` | 35 | `jue+tHyr` | ✅ |
| F `first=71` | 35 | `jcvGxm0i` | 换批（预期） |
| G `first=1` | 35 | `UFcCituS` | 回到首批（预期） |

**结论：`q`、`first` 足够；`count` 无实际作用但建议带上；其余参数全部可选。**

### `first`：1-based 起始序号

- 页面上第 36 条结果（`a.iusc` 的第 36 个）的 `cid` 恰是 `first=36` 响应的第一条 → 语义是**从第 N 条开始**，不是"第 N 页"。
- 粒度由返回条数决定，实测固定 35（偶尔 34，见下）。
- 越界不减到空：`first=1000` 仍返回 200 与 11 条尾部残余。**不要用"返回空"判断结果耗尽**，用"条数为 0"或"与上一批重叠率高"来判断。

### `count` 被忽略

`count=10 / 35 / 100` 三种取值，响应体字节数与条数完全相同（148,482 字节 / 35 条）。服务端按自己的页大小（35）返回。

页面内嵌的配置也印证这一点：

```js
_w["DgConfig"] = {"aurl":"/images/async?q=%QUERY%&async=content&first=%FIRST%&count=%COUNT%&dgst=%DGSTATE%&IID=%IID%&SFX=%SFX%&IG=%IG%&CW=%CW%&CH=%CH%&CT=%CT%","ac":35,…}
```

`ac:35` 即单批条数。

### 浏览器实际发出的完整 URL（备查）

滚动触发无限加载时，浏览器带的是：

```
/images/async?q=猫
  &first=36
  &count=35
  &cw=1440&ch=900          # 视口尺寸
  &relp=35
  &datsrc=I
  &layout=RowBased
  &apc=0
  &imgbf=<base64>          # 布局指纹，每批不同
  &mmasync=1
  &dgState=x*430_y*968_h*188_c*2_i*36_r*6   # 滚动位置状态
  &IG=<32 hex>
  &SFX=2                   # 批次序号，递增
  &iid=images.5612
```

`dgState` 的 `i*` 字段与 `first` 同值。这些参数看着像必需，实测全可剥离 —— 它们是给前端做布局恢复用的，不是鉴权。

### 翻页（跨批次取结果）

`first` 对外部客户端有效，但**需要一次浏览器会话的 Cookie**。没有 Cookie 或会话被判为自动化时，任何 `first` 都回落第 1 批（见 `session.md`）。

```bash
# 1) 用普通浏览器打开一次图片搜索，导出该站 Cookie 到 Netscape 格式文件
#    （浏览器扩展或开发者工具均可；这是正常浏览产生的会话，不是伪造）
# 2) 带 Cookie 请求不同批次
for f in 1 36 71; do
  curl -sS "https://cn.bing.com/images/async?q=%E7%8C%AB&first=$f&count=35&mmasync=1" \
    -b cookies.txt \
    -e "https://cn.bing.com/images/search?q=%E7%8C%AB" \
    -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
    -o "batch_$f.html"
done
```

实测结果：

| 请求 | 条数 | 首条 cid | 相邻批次重叠 |
|---|---|---|---|
| `first=1` | 35 | `4QyC+UNQ` | — |
| `first=36` | 35 | `qBplLjJ4` | 与第 1 批 0 条 |
| `first=71` | 34 | `rGwB5gmm` | 与第 2 批 6 条 |

两点必须知道：

1. **相邻批次会有少量重复**（本样本 6/35）。服务端结果集在翻页过程中会轻微漂移，去重键用 `cid`。
2. **结果非确定性**。同一 `first` 隔一段时间再请求，`cid` 会变。这不是参数没生效。

请求间隔保持在秒级，不要并发。频控行为未做压力测试，也不在本仓库范围内（见 `NOTICE.md` 第 3 节）。

---

## `/images/search`（首屏）

```
GET https://cn.bing.com/images/search?q=<query>
```

- 返回完整 HTML，结果同样是 `a.iusc` + `m="{JSON}"`，**35 条**（中文市场，视口 1440×900）
- `first` 参数被忽略：`first=1` 与 `first=36` 返回同一批（首条 `cid` 均为 `UFcCituS`）
- 市场切换生效：`&ensearch=1&cc=us` 后变为 **25 条**，内容完全不同
- 这个页面的用途是拿外壳里的元信息（`IG`、`DgConfig`、过滤器选项），不是拿数据

## 过滤器 `qft`

```
/images/async?q=猫&first=1&count=35&mmasync=1&qft=%2Bfilterui%3Aimagesize-large
```

`qft` 值是 `+filterui:<族>:<值>`，需 URL 编码（`+` → `%2B`，`:` → `%3A`）。实测有效：

| `qft` | 与无过滤结果的重叠 |
|---|---|
| `+filterui:imagesize-large` | 5 / 35 |
| `+filterui:photo-photo` | 4 / 35 |
| `+filterui:color2-color` | 4 / 35 |
| `+filterui:face-face` | 0 / 35 |

`qft` 与 `first` 可组合（`first=36` + `imagesize-large` 实测返回 35 条，与首批不同）。

常见族与值（取自页面过滤器控件，非穷举）：

| 族 | 值示例 | 含义 |
|---|---|---|
| `imagesize` | `small` / `medium` / `large` / `wallpaper` | 尺寸档 |
| `photo` | `photo` / `clipart` / `line` / `gif` | 图片类型 |
| `color2` | `color` / `bw` / `mono` | 彩色 / 黑白 / 单色 |
| `face` | `face` / `portrait` | 含人脸 / 人像 |
| `license` | `public` / `share` / `sharecommercially` / `modify` | 授权范围 |

`license` 族未在本轮实测（它依赖市场与合规状态），列在此处仅供定位控件用。

---

## 响应结构

片段开头是 `<style>`，随后是 `<ul>`，**没有 `<html>` / `<head>` / `<body>`**，可直接插进现有页面：

```html
<style type="text/css">.mc_fh{…}</style>
<ul data-row="0" class="dgControl_list" data-infullrow="1">
  <li data-idx="1" style="width:241px; height:234px">
    <div class="iuscp isv smallheight" data-hoverstyle data-evt="1" data-vie="1">
      <div class="imgpt">
        <a aria-label="猫 的图像结果" role="link" class="iusc"
           style="height:180px;width:241px"
           m="{&quot;sid&quot;:&quot;&quot;,&quot;cturl&quot;:&quot;&quot;,&quot;cid&quot;:&quot;UFcCituS&quot;,
              &quot;purl&quot;:&quot;https://www.nipic.com/show/…&quot;,
              &quot;murl&quot;:&quot;https://pic.nximg.cn/…jpg&quot;,
              &quot;turl&quot;:&quot;https://ts1.mm.bing.net/th?id=OIP.…&amp;pid=15.1&quot;,
              &quot;md5&quot;:&quot;5057028adb…&quot;,&quot;shkey&quot;:&quot;JISfICmD…=&quot;,
              &quot;t&quot;:&quot;猫 摄影图__家禽家畜…&quot;,&quot;mid&quot;:&quot;4DFD1E7B…&quot;,
              &quot;desc&quot;:&quot;\ue000猫\ue001 摄影图__家禽家畜…&quot;}"
           data-fnvg="1"></a>
      </div>
    </div>
  </li>
</ul>
```

要点：

- `m` 属性的值是 **HTML 转义后的 JSON**（`&quot;` → `"`，`&amp;` → `&`），必须先反转义再 `json.loads`。
- 每个 `a.iusc` 在片段里没有子元素，缩略图由前端脚本按 `turl` 注入。所以**不要**从 `<img src>` 取图 —— 片段里没有 `<img>`。
- 外层 `li` 没有稳定业务键，唯一可靠标识是 `m` 里的 `cid`。
- 片段末尾会带回 `sj_evt.bind('dg_init', …)` 之类的脚本，忽略即可。

字段含义见 [fields.md](fields.md)。

### 内容分级子域

缩略图域名除 `ts{1..4}.mm.bing.net` 外，还观察到 `ts{n}.explicit.bing.net`。本样本 35 条中 4 条落在 `explicit` 子域。这是服务端的内容分级标记，**不是**传输错误。需要干净结果的场景应据此过滤；本仓库不展开该子域的内容特性。

---

## 已知不存在 / 不可用

| 尝试 | 结果 |
|---|---|
| `/images/api/v2/search` | 404 |
| `/images/api/custom/knowledge?q=&mkt=` | 404（CN 站无此端点；国际站未验证） |
| `/images/async?...&format=json` | 忽略 `format`，返回 HTML 片段 |
| `/images/search?...&format=rss` | 忽略，返回 HTML |
| `q` 为空 | 302 重定向到图片首页 |
| `/images/searchbyimage` | `robots.txt` 明确 Disallow，本仓库不测试、不记录 |

`/images/svctrlpack?mmasync=1` 是"收藏/视图"组件的资源包，不含结果数据。

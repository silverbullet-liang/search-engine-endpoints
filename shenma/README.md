# 神马搜索（m.sm.cn）

**本次实测评测结论：没有匿名可用的接口。** 所有搜索路径都返回阿里 `bixi` 风控的 `deny` 页，桌面与移动 UA 无差别。

本文的价值是"确认这条路走不通"，以及给出等价的替代方案 —— 避免你重复试。

| 路径 | 实测 | 说明 |
|---|---|---|
| `GET /s?q=` | 200，1073 B | 阿里 punish 页，`action=deny` |
| `GET /su?wd=` | 404 | 该疑问路径不存在（16 B） |
| `GET sugs.m.sm.cn/web?q=` | 200，3856 B | 同样 punish（返回注入脚本） |
| `GET /s?q=&type=image` | 200，1073 B | 同一 punish 页 |

---

## 1 · 搜索页返回的是什么

```http
HTTP/1.1 200 OK
Content-Type: text/html;charset=UTF-8
```

响应体前 300 字节（真实）：

```html
<a id="a-link"
    href="https://bixi.alicdn.com/punish/punish:resource:template:baba:fcvsxmqtca_35282882.html
          ?qrcode=5Vcj8o_wkBETi4Pl4giQow|auWQSA|WXqniw_0|cloud_ip_bl|0
          &uuid=e55723f28ff09011138b83e5e20890a3
          &action=deny&origin=https%3A%2F%2Fm.sm.cn%3A443%2Fs"></a>
```

后续脚本做三件事：

```javascript
var cookie = "x5secdata=;maxAge=-100;expires=…;path=/;domain=.sm.cn;";
document.cookie = cookie;                 // 1. 清掉旧的 x5secdata
document.getElementById("a-link").click(); // 2. 跳到 bixi 惩罚页
window._config_ = { "action": "deny", … }; // 3. 声明本次判定为 deny
```

末尾还有一行标记：`<!--rgv587_flag:sm-->`。

### 判断要点

- **HTTP 200 但内容是一个跳转壳**，不是搜索结果。任何只看状态码的客户端会以为成功。
- `bixi.alicdn.com` 是阿里统一的防爬产品（淘宝/UC/夸克同源），所以**换 UA 无效**：桌面 Chrome UA、iPhone Safari UA 返回的都是同一份 1073 字节。
- `action=deny` 是明确拒绝，`cloud_ip_bl` 字样说明判定用到了出口 IP。
- 清 `x5secdata` 是风控流程的一部分 —— 这意味着未通过的会话会被反复送回惩罚页。

---

## 2 · 没有可用的替代入口

试过的其它形态：

| 尝试 | 结果 |
|---|---|
| `so.m.sm.cn/s?q=` | 200，1079 B，同一 punish 页 |
| 移动端 UA | 与桌面一致 |
| `/su?wd=`（联想） | 404 |

神马是阿里的移动搜索产品，其搜索结果与夸克搜索同源。**本仓库没有找到任何匿名的神马数据入口**，因此没有字段结构可记录。

---

## 3 · 等价替代

同样需求（中文通用搜索 + 图片）用这几家，都是本仓库实测可用的：

| 需求 | 推荐 | 依据 |
|---|---|---|
| 图片搜索（结构化、可分页） | **Bing** `/images/async` | [bing/image.md](../bing/image.md)，`first` 1-based，可跨批 |
| 图片搜索（单次大结果集） | **360** `image.so.com/j` | [360/image.md](../360/image.md)，单次 85–234 条、38 字段 |
| 输入联想 | **百度** `sugrec` / **360** `sug.so.360.cn` | [baidu/suggest.md](../baidu/suggest.md)、[360/suggest.md](../360/suggest.md) |
| 视频/UP 主 | **B站** | [bilibili/README.md](../bilibili/README.md) |
| 热点/趋势 | **抖音** 热搜 | [douyin/README.md](../douyin/README.md) |

---

## 4 · 给 AI 用

```
神马（m.sm.cn）：
- 没有匿名接口。所有请求返回 bixi punish 壳（HTTP 200，action=deny）
- 不要重试、不要换 UA：判定依据是出口 IP 与风控会话，换头部无效
- 需要中文通用搜索时改调：Bing（图片/网页首页）、360（图片 JSON）、百度（联想）
```

机器可读版本见 [`api.json`](../api.json) 的 `shenma` 段（该段 `available: false`）。

## 状态说明

- `m.sm.cn/robots.txt`：`User-Agent: *` → `Allow: /`，但 `Disallow: /*?*`（禁止所有带查询参数的 URL）、`Disallow: /s/*`、`Disallow: /s$`。
- 实测于 2026-10-31，出口为中国大陆。其它网络环境下的判定可能不同。

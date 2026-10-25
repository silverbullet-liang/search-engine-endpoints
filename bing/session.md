# 06 · 会话要求与降级判据

这是本仓库最实用的一篇。同一组 URL，服务端会返回**两种不同的东西**，而两者都是 `HTTP 200`。不识别这一点，会得出"参数无效"这种错误结论。

---

## 两种响应并存

| | 完整响应 | 降级响应 |
|---|---|---|
| `GET /search?q=rust…&first=11` | ~306 KB，分页生效（第 2 页） | ~103 KB，永远是第 1 页 |
| `GET /images/search?q=猫` | 滚动可持续加载（实测 35 → 70 → 205 条） | 固定 35 条，页面高度 1701 px |
| 分页 XHR | 正常发出，带 `imgbf`/`dgState`/`SFX` | **完全不发** |
| 页面内脚本 | 完整 | 部分被裁，`dgst` 相关逻辑不存在 |

降级响应**看起来是成功的**：状态码 200、`Content-Type` 正确、HTML 结构完整、能解析出 10 条真结果。只有对比字节数或尝试翻页才会发现不对。

---

## 判据清单

出现以下任一信号，说明当前会话已降级，此时"参数无效"的结论全部不可信：

| 信号 | 观察方式 |
|---|---|
| 图片页 `document.body.scrollHeight ≈ 1701`（一屏） | `eval "document.body.scrollHeight"` |
| 滚动后 `a.iusc` 数量不变（停在 35/70） | 滚动前后计数 |
| 网络面板无 `/images/async` 请求 | 抓包 |
| `/search` 响应体 ~103 KB 而非 ~306 KB | 响应长度 |
| 出现 `vcf.bing.com/bd/verify?IID=BdVerify&…` | 抓包 |
| 出现 `/web/chlrate?partner=BD&status=bdvexc` | 抓包 |

`bdvexc` 是该站的防护判定结果标记。看到它就说明本次会话已被识别为非人工浏览。

---

## 对照实验：同一会话 vs 外部客户端

### 图片 `/images/async`

| 上下文 | `first=36` 的结果 |
|---|---|
| headless 浏览器（降级会话） | 与 `first=1` 完全相同（35/35 重叠） |
| 带合法 Cookie 的 curl | **不同批次**（重叠 0/35） |
| 反检测浏览器（正常会话） | 不同批次，且可持续加载到 205 条 |

同一个 `first=36`，三种上下文三种结果。参数没变，环境变了。

### Web `/search`

| 上下文 | `first=11` 的结果 |
|---|---|
| curl（无 Cookie） | 第 1 页 |
| curl（17 项 Cookie） | 第 1 页，103 KB |
| curl（+ `FPIG` + `Referer` + `sec-fetch-*` + `sec-ch-ua` + `br,zstd`） | 第 1 页，103 KB |
| 浏览器**导航** | 第 2 页，306 KB |
| 浏览器内 `fetch()`（同源、同 Cookie） | 第 2 页，306 KB |

七组外部客户端全部失败，两种浏览器上下文全部成功。

### 已排除的因素

| 假设 | 实验 | 结论 |
|---|---|---|
| 缺 Cookie | 补到 17 项，含 `SRCHHPGUSR`/`BFPRResults`/`USRLOC` | 排除 |
| 缺 `FPIG` | 带上浏览器当前页生成的 `FPIG` | 排除 |
| `Referer` 不匹配 | 精确指向第 1 页 URL | 排除 |
| 缺 `sec-fetch-*` | 全套 `dest/mode/site/user` + `upgrade-insecure-requests` | 排除 |
| 缺 `sec-ch-ua` | 全套 UA 客户端提示 | 排除 |
| 压缩协商影响后端分支 | `accept-encoding: gzip, deflate, br, zstd` + `--compressed` | 排除 |
| 需要 `rdr`/`rdrig` | 补上点击时带的这两个参数 | 排除 |

剩下唯一未被排除的层：**连接本身的指纹**（TLS ClientHello / HTTP2 SETTINGS 与伪头顺序）。浏览器内 `fetch` 与 curl 的区别也恰好在这一层 —— 同样的 JS，同样的 Cookie，只有连接特征不同。

curl 8.14.1 不带该能力（`--impersonate` 在官方构建中不存在）。本仓库不安装、不推荐、不提供任何指纹伪装工具：那是 `NOTICE.md` 第 3 节明确划在边界外的事。

---

## 会话里到底有什么

匿名访客（未登录）一次正常会话会下发这些 Cookie（只列名字，不含值）：

```
_SS  _EDGE_V  _EDGE_S  MUID  MUIDB  MMCASM
SRCHUID  SRCHD  SRCHUSR  SRCHHPGUSR
_RwBf  _Rwho  __Host-XY  BFPRResults  USRLOC
.MSA.Auth.Nonce.<长哈希>
```

其中：

- `SRCHHPGUSR` 与 `SRCHUSR` 是页面视图状态（尺寸、DPI、时区、语言），浏览器首次渲染后才写入 —— 这也是"先开一次浏览器再导出"比"自己拼 Cookie"可靠的原因。
- `MUID`/`MUIDB` 是匿名用户 ID；`_EDGE_S` 带 `SID` 会话号。
- `.MSA.Auth.Nonce.*` 与登录相关，匿名会话里也存在，但不代表已登录。

**这些不是访问凭证，不含个人信息，也无法换取任何授权。** 抓它们只是为了让服务端把你的请求当成"一个刚看过页面的普通访客"。

---

## 两个层级的门槛

同一站点的不同端点，风控强度不一样：

| 层级 | 端点 | 门槛 |
|---|---|---|
| 文档导航级 | `/search`、`/images/search` | 高：连接指纹 + 完整会话 |
| 组件/片段级 | `/images/async`、`/AS/Suggestions`、`/OSJSON.aspx` | 低：合法 Cookie 即可（部分端点连 Cookie 都不要） |

工程含义：**能用片段级端点的，就不要碰文档级端点。** 图片分页走 `/images/async` 完全够用，不需要为了"看起来像人"去做文档级请求。

---

## 一份可复用的判定流程

```
1. 请求目标端点，记录 status / 字节数 / 关键结构计数
2. 用一个参数的两种取值（如 first=1 与 first=36）各请求一次
3. 比较两次结果集的标识集合（cid / md5 / url）
   - 有差异 → 参数生效，接口可用
   - 完全一致 → 进入 4
4. 在真实浏览器里对同一 URL 做一次 fetch，比较标识集合
   - 有差异 → 是环境/指纹问题，不是参数问题。停止调参。
   - 仍一致 → 参数确实无效，接受结论。
```

第 4 步是关键：它把"参数问题"和"环境问题"分开，避免在错误的方向上无限重试。

---

## 不要做的事

降级本身是服务端的判断结果。绕过它需要伪造连接指纹或规避防护 —— 本仓库不提供，也不会在 issue 里讨论。正确做法是接受"这个端点在我的上下文里不可用"，改用可用的端点，或者走官方授权渠道。

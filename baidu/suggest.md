# 百度 · 输入联想

两个端点，一个返回 JSON，一个返回 JSONP（GBK 编码）。都能用。

---

## 一、`sugrec`（JSON）

```http
GET https://www.baidu.com/sugrec?prod=pc&wd=<typed>&ie=utf-8
```

### 请求头

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36
Referer: https://www.baidu.com/
```

### 请求示例

```bash
curl -sS -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://www.baidu.com/' \
  'https://www.baidu.com/sugrec?prod=pc&wd=cat'
```

### 返回

`Content-Type: text/plain; charset=UTF-8`，1385 字节：

```json
{
  "q": "cat",
  "p": false,
  "g": [
    { "type": "sug", "sa": "s_1", "q": "catch",        "no_ai_sug": false },
    { "type": "sug", "sa": "s_2", "q": "catia软件",     "no_ai_sug": false },
    { "type": "sug", "sa": "s_3", "q": "cat怎么读音",   "no_ai_sug": false },
    { "type": "sug", "sa": "s_4", "q": "cat中文翻译",   "no_ai_sug": false }
    …共 10 条
  ],
  "slid": "…",
  "queryid": "…"
}
```

| 字段 | 说明 |
|---|---|
| `q` | 回显输入 |
| `p` | 布尔，语义未验证（样本恒 `false`） |
| `g` | 建议数组，固定 10 条 |
| `g[].q` | 建议文本 |
| `g[].type` | 样本恒 `sug` |
| `g[].sa` | 埋点标识 `s_1`…`s_10`，无业务含义 |
| `g[].no_ai_sug` | 布尔，是否抑制 AI 建议，样本恒 `false` |
| `slid` / `queryid` | 会话/查询 ID |

优点：纯 JSON、UTF-8、字段规整。
缺点：建议文本**不带高亮**，无法知道匹配了哪几个字。

---

## 二、`suggestion.baidu.com/su`（JSONP / GBK）

```http
GET https://suggestion.baidu.com/su?wd=<typed>&cb=<callback>
```

### 请求示例

```bash
curl -sS -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://www.baidu.com/' \
  'https://suggestion.baidu.com/su?wd=cat&cb=cb' | iconv -f gbk -t utf-8
```

### 返回

`Content-Type: text/javascript; charset=gbk`，160 字节：

```javascript
cb({q:"cat",p:false,s:["catch","cat中文翻译","catia软件","cat怎么读音","category","catch up","cater","catalog","catalogue","cathy"]});
```

| 字段 | 说明 |
|---|---|
| `cb(...)` | 回调名即请求里的 `cb` 参数（未验证省略时的默认值） |
| `q` | 回显输入 |
| `p` | 布尔，样本恒 `false` |
| `s` | 建议字符串数组，10 条 |

**这不是合法 JSON**：键名没有引号，外层是函数调用。解析前必须：

1. 剥掉 `<cb>(` 与 `);`；
2. 把裸键名补引号，或直接用 `json5` / 正则提取；
3. 内容按 **GBK** 解码，别用 UTF-8（否则中文全是乱码）。

这正是它不如 `sugrec` 的原因 —— 三个坑叠在一起。

---

## 选择建议

| 需求 | 用哪个 |
|---|---|
| 只要建议词 | `sugrec`（省掉编码与 JSONP 处理） |
| 需要传统 JSONP 跨域老页面兼容 | `su` |
| 需要高亮位置 | 两者都拿不到，Bing 的 `/AS/Suggestions` 才有（见 [../bing/suggest.md](../bing/suggest.md)） |

## 说明

1. 两个端点都返回固定 10 条，均无 `count` 参数（未验证其它参数能否改条数）。
2. 空输入行为未测 —— 本次不写未验证的结论。
3. 建议词是公开查询串，不含第三方内容。

## 合规状态

`sugrec` 位于 `www.baidu.com`，该站对 `User-agent: *` 是 `Disallow: /`。

`suggestion.baidu.com` 的 `/robots.txt` 返回 **302**，跳转到 `http://www.baidu.com/search/error.html` —— 该子域没有独立规则文件，因此适用父域约束。

结论同其余端点：本文件记录契约，不提供批量化用途。

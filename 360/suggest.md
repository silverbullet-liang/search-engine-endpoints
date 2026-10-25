# 360 · 输入联想

## 请求方式

```http
GET https://sug.so.360.cn/suggest?word=<typed>
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `word` | 是 | 已输入文本，URL 编码（中文、英文均可） |

其它参数（`type`、`output`、`callback` 等）**未验证**，本次未观察到影响。

响应头：

```http
HTTP/2 200
Content-Type: text/plain; charset=UTF-8
```

## 请求头

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36
Referer: https://www.so.com/
```

## 请求示例

```bash
curl -sS \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -e 'https://www.so.com/' \
  'https://sug.so.360.cn/suggest?word=cat'
```

## 返回示例

```json
{
  "errorcode": 0,
  "ext": "nlpv=test_403",
  "query": "cat",
  "result": [
    { "face": "", "word": "cat是什么意思" },
    { "face": "", "word": "cat gpt" },
    { "face": "", "word": "cat6是什么线" },
    { "face": "", "word": "catalog.update.microsoft.com" },
    { "face": "", "word": "catia是什么软件" },
    …共 10 条
  ],
  "sleep": 21600,
  "sp": "",
  "src": "other",
  "ssid": "29d71c0f1d9a4be8a7751f53ef64c6c2",
  "version": "revise"
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `errorcode` | int | `0` 为正常。非 0 时 `result` 可能缺失 |
| `query` | string | 回显输入 |
| `result` | array | 建议列表，**固定 10 条** |
| `result[].word` | string | 建议文本（原始，无高亮标记） |
| `result[].face` | string | 建议类型标记。本次样本恒为空串 |
| `sleep` | int | `21600`（= 6 小时），疑为该查询建议的缓存有效期。**未验证** |
| `ssid` | string | 会话 ID，32 位十六进制 |
| `ext` / `sp` / `src` / `version` | — | 内部标记（`src` 本次为 `other`，`version` 为 `revise`） |

## 说明

1. 纯 JSON，无 JSONP 包裹、无 HTML、无高亮标记 —— 四家里最容易解析的一个。
2. 中英文都返回 10 条；中文建议词为完整短语（如 `猫和老鼠动画片免费观看`），不是补全片段。
3. 建议词本身是公开的查询串，不含第三方内容，可直接用于输入框联想。
4. 未验证：空 `word` 行为、条数是否可调、是否有拼音/纠错类型区分（`face` 恒空，无法据此判断）。

## 合规状态

`sug.so.360.cn` 未在该站 `robots.txt` 中单独列出；`www.so.com/robots.txt` 的 `User-agent: *` 段只禁 `/s`、`/link`、`/brw`，不含本端点。

即便如此：本文件只记录契约与结构，不提供批量抓取建议词的用途。联想词用于输入框是正常互操作，用于批量构建词库则属于另一类用途，请自行评估。

# 04 · 相关查询（JSON）

```
GET /instantsearch/getquerylist?query=<query>
```

用途：拿"与该查询相关但不同的查询"。因为 Web 结果只能稳定拿到第 1 页 10 条（见 `web.md`），这个端点是把覆盖面扩出去的主要手段 —— 换查询词比琢磨翻页划算。

返回 `application/json`，是这批端点里**唯一真正的结构化搜索结果数据**。

---

## 请求契约（容易踩的两个坑）

实测矩阵（`query=cat`，其他头默认）：

| 请求 | 结果 |
|---|---|
| 不带任何自定义头 | **403**，空体 |
| `Accept: */*`，无 `Referer` | **404**，70 KB HTML（返回的是搜索页外壳） |
| `Accept: */*` + `Referer: https://cn.bing.com/…` | **200**，374 字节 JSON |
| `Accept: application/json` + `Referer` | **404**，同样 70 KB HTML |

两个结论：

1. **必须带 `Referer`**（该站任意路径即可）。缺了会 403 或 404 —— 典型防盗链。
2. **`Accept` 不能声明 `application/json`**。声明了反而被路由到静态处理分支而 404。用 `*/*` 或干脆不设。

第 2 条是反直觉的：越是"正确"地做内容协商，越拿不到数据。

```bash
curl -sS 'https://cn.bing.com/instantsearch/getquerylist?query=cat' \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -H 'accept: */*' \
  -e 'https://cn.bing.com/search?q=cat'
```

---

## 响应

```json
{
  "QueryList": [
    { "CandicateQuery": "catia官方下载官网", "Score": 0.74052685, "ModelResolver": null },
    { "CandicateQuery": "catia是什么软件",  "Score": 0.29035133, "ModelResolver": null },
    { "CandicateQuery": "cat5e",            "Score": 0.2802706,  "ModelResolver": null },
    { "CandicateQuery": "cat6是什么线",      "Score": 0.25187534, "ModelResolver": null }
  ],
  "Extension": { "trueSize": "4" },
  "ModelResolver": {}
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `QueryList[].CandicateQuery` | string | 候选查询。**字段名拼写就是 `CandicateQuery`**（服务端原文，不是 `Candidate`），照抄即可，不要"纠正" |
| `QueryList[].Score` | float | 相关度，0–1，降序排列 |
| `QueryList[].ModelResolver` | null | 本样本恒为 null |
| `Extension.trueSize` | string | 实际条数，**是字符串不是数字**（`"4"`） |
| `ModelResolver` | object | 本样本为空对象 |

`trueSize` 与 `len(QueryList)` 一致；类型不一致意味着任何 `if (d.Extension.trueSize > 0)` 的写法在强类型语言里都会编译失败。

---

## 边界行为

| 情况 | 结果 |
|---|---|
| 英文查询（`query=rust+async`） | `200`，`{}` —— **顶层是空对象，没有 `QueryList` 键** |
| 中文查询 | 4 条（本例） |
| 长查询串 | 未观察到长度截断，但条数不稳定（2–6 条） |

英文直接返回 `{}` 是实测结果：这个端点在中英文市场的行为不对称，取 `QueryList` 前必须判空，不能直接 `d["QueryList"]`。

推荐写法：

```python
items = (d.get("QueryList") or []) if isinstance(d, dict) else []
```

---

## 与其他端点的关系

| 想做的事 | 用哪个 |
|---|---|
| 用户正在输入，要补全 | `/AS/Suggestions` 或 `/OSJSON.aspx`（`suggest.md`） |
| 已有一个查询，要扩成一批相关查询 | **本端点** |
| 要完整结果列表 | 无解：Web 只给 10 条，图片给异步分页（`image.md`） |

本端点与 `/AS/Suggestions` 的差别：前者是"这个查询还能怎么问"，后者是"这个词还没打完时该补什么"。两者结果不重叠（本例 `cat` 的相关查询是 `catia…`，联想建议是 `catti` / `cat vs dyj` 等）。

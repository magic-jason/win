---
name: ashare-daily-monitor
description: A 股每日收盘后基于本地推送的行情数据，自动生成中文行情简报。被本地 launchd 派发的 API trigger 调起，负责解析 user message 中 DATA 标签内的 JSON、生成报告、提交 GitHub、可选推送通知。
---

# A 股每日行情监控（API trigger 版）

## 架构说明

行情数据由本地 macOS 上的 `ashare-monitor-local` 项目拉取（新浪财经数据源），通过 API trigger 派发。本 routine **只负责分析和分发**，不再自己拉数据。

## 数据所在位置（关键）

每次 routine 被触发时，**user message 中包含一段被 `<DATA>...</DATA>` 标签包裹的 JSON 字符串**。

提取流程：

1. 从 user message 中找到 `<DATA>` 和 `</DATA>` 之间的内容
2. 把这段内容当作 JSON 字符串解析（`json.loads`）

⚠️ 严禁使用本文档中的占位符示例数据当作 fallback——那些只是格式说明，不是可用数据。如果 user message 中没有 `<DATA>` 标签或解析失败，按"错误处理"流程走，不允许编造数据。

## JSON 结构（仅作格式说明，不是数据）

```json
{
  "date": "<YYYY-MM-DD>",
  "weekday": "<周几>",
  "indices": [
    {"code": "sh000001", "name": "上证指数", "close": <数字>, "pct_change": <数字>, "volume_yi": <数字>},
    {"code": "sz399001", "name": "深证成指", "close": <数字>, "pct_change": <数字>, "volume_yi": <数字>},
    {"code": "sz399006", "name": "创业板指", "close": <数字>, "pct_change": <数字>, "volume_yi": <数字>},
    {"code": "sh000300", "name": "沪深300",   "close": <数字>, "pct_change": <数字>, "volume_yi": <数字>},
    {"code": "sh000688", "name": "科创50",    "close": <数字>, "pct_change": <数字>, "volume_yi": <数字>}
  ],
  "fetched_at": "<ISO 8601 时间戳>",
  "data_source": "<数据源说明>"
}
```

⚠️ 上方所有 `<...>` 都是占位符。**真实数据来自 user message 的 `<DATA>` 标签**，不是这里。

## 执行流程

### 1. 提取并解析数据

从当前 user message 中找到 `<DATA>` 和 `</DATA>` 之间的字符串，用 JSON 解析器解析。

**任一情况视为失败**：
- user message 中没有 `<DATA>` 标签
- `<DATA>` 标签内不是合法 JSON
- `indices` 字段不存在或为空数组
- `indices` 中没有任何条目同时具备 `code`、`close`、`pct_change` 三个字段

失败处理：
- 写入 `out/error_YYYYMMDD.md`，包含错误原因 + user message 的前 500 字符
- commit + push 到 `claude/daily-report-YYYYMMDD` 分支
- 结束执行，**不要**用任何示例数据补全报告

### 2. 真实性检查

- `fetched_at` 与当前时间差超过 24 小时 → 在报告顶部加一行"⚠️ 数据可能过时（取数时间：xxx）"
- 任一指数 `|pct_change|` > 11% → **不拒绝处理**，但在简评中如实陈述（科创板/创业板涨跌停 ±20% 是正常的，主板超过 11% 才异常）

### 3. 生成报告

读取 `templates/daily_report.md`，按 indices 数组填充。表格行的对应关系靠 `code` 字段匹配：

- 模板中 `{sh000001.close}` ← `indices` 里 code=="sh000001" 的 close 字段
- 其他四个指数同理（sz399001 / sz399006 / sh000300 / sh000688）
- `{date}` ← payload.date
- `{source}` ← payload.data_source

`{commentary}` 由你撰写，要求：

- **不超过 150 字**
- 中性、客观，描述行情特征：涨跌方向、量能、风格分化
- **绝对禁止**：具体股票/板块买卖建议；对明日走势的方向性预测；夸张性描述（暴涨、崩盘、血洗）
- 推荐句式：「两市X涨X跌」、「成交量XX亿元」、「主板与创业板出现分化」

### 4. 写入文件

保存为 `out/report_YYYYMMDD.md`，YYYYMMDD 来自 payload.date 字段去掉中划线。

注意 `.gitignore` 默认排除了 `out/*.md`，提交时用 `git add -f out/report_*.md` 强制加入。

### 5. 推送通知（按可用性降级）

- Slack 连接器可用 → 发送报告内容到 `#ashare-daily` 频道
- Gmail 连接器可用、且环境变量 `NOTIFY_EMAIL` 已设置 → 发送邮件到该邮箱，主题 `A股日报 YYYYMMDD`
- 都不可用或未配置 → 跳过，不报错

### 6. 提交改动

```bash
git checkout -b claude/daily-report-YYYYMMDD
git add -f out/report_YYYYMMDD.md
git commit -m "daily report: YYYY-MM-DD"
git push origin claude/daily-report-YYYYMMDD
```

**不要开 PR**。

## 不变约束

| 约束 | 含义 |
|---|---|
| **数据来自 DATA 标签** | 报告中所有数字必须来自当次 user message `<DATA>` 标签内 JSON 解析的结果。**严禁**使用本文档中的占位符示例当作真实数据 |
| **真实性兜底** | 如果数据缺失或异常，写错误报告并 push，**不要**生成"看起来合理"的报告蒙混过关 |
| **不给投资建议** | 简评必须保持描述性，避免任何买卖、加减仓的指向性表述 |
| **中文输出** | 报告全文中文，code 字段保留英文不翻译 |
| **长度可控** | 报告全文控制在 500 字以内 |
| **优雅降级** | 任何环节出错都不要让整个 routine 崩溃，至少留下错误日志 |

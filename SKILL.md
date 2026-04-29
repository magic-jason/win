---
name: ashare-daily-monitor
description: A 股每日收盘后基于本地推送的行情数据，自动生成中文行情简报。被本地 launchd 派发的 API trigger 调起，负责解析 payload、生成报告、提交 GitHub、可选推送通知。
---

# A 股每日行情监控（API trigger 版）

## 架构说明

行情数据由本地 macOS 上的 `ashare-monitor-local` 项目拉取（akshare 国内访问稳定），通过 API trigger 的 `text` 字段以 JSON 形式传入。本 routine **只负责分析和分发**，不再自己拉数据。

## 输入数据格式

每次 routine 被触发时，`text` 字段是一段 JSON 字符串，结构如下：

```json
{
  "date": "2026-04-29",
  "weekday": "周二",
  "indices": [
    {"code": "sh000001", "name": "上证指数", "close": 3000.00, "pct_change": 0.50, "volume_yi": 4200.0},
    {"code": "sz399001", "name": "深证成指", "close": 9500.00, "pct_change": -0.30, "volume_yi": 5100.0},
    {"code": "sz399006", "name": "创业板指", "close": 2000.00, "pct_change": 0.80, "volume_yi": 1800.0},
    {"code": "sh000300", "name": "沪深300", "close": 3500.00, "pct_change": 0.40, "volume_yi": 2200.0},
    {"code": "sh000688", "name": "科创50",   "close": 800.00,  "pct_change": 1.20, "volume_yi": 600.0}
  ],
  "fetched_at": "2026-04-29T15:25:30",
  "data_source": "akshare (东方财富)"
}
```

## 执行流程

### 1. 解析 text

将 `text` 字段解析为 JSON。如果解析失败或 `indices` 为空：

- 写入 `out/error_YYYYMMDD.md`，记录错误信息和原始 text
- commit + push，结束

### 2. 真实性检查

- `fetched_at` 与当前时间差距是否合理（超过 24 小时则在报告中标注"数据可能过时"）
- `indices` 中每条数据的 `pct_change` 是否在合理范围（绝对值超过 11% 视为异常，因为 A 股涨跌停一般 ±10%，科创板/创业板 ±20% 例外）
- 如有异常，**不要拒绝处理**，而是在简评中如实指出

### 3. 生成报告

读取 `templates/daily_report.md`，按 `indices` 数组填充表格。模板里的占位符按 code 字段对应：

- `{sh000001.close}` 等 → 用 indices 数组里 code 匹配的 close 字段
- `{date}` → payload.date
- `{source}` → payload.data_source

`{commentary}` 字段由你（Claude）撰写：

- **不超过 150 字**
- 描述行情特征：涨跌方向、量能变化、风格分化（主板 vs 创业板/科创板）
- **绝对禁止**：
  - 具体股票/板块买卖建议（如"建议关注 XX"、"减仓 XX"）
  - 对明日走势的方向性预测（如"明日有望反弹"）
  - 夸张性描述（"暴涨"、"崩盘"、"血洗"等）
- **可以**：客观陈述 + 中性观察（如"两市分化明显"、"成交量较前一日有所放大"）

### 4. 写入文件

将完整报告保存为 `out/report_YYYYMMDD.md`（YYYYMMDD 用 payload.date）。

### 5. 推送通知（按可用性降级）

- 如有 Slack 连接器可用：发送报告内容到 `#ashare-daily` 频道（保留 Markdown 格式）
- 如有 Gmail 连接器可用：发送到环境变量 `NOTIFY_EMAIL` 指定的邮箱，主题 `A股日报 YYYYMMDD`
- 都不可用：跳过，不报错

### 6. 提交改动

将新报告文件 commit 并 push 到 `claude/daily-report-YYYYMMDD` 分支。**不开 PR**。

## 不变约束

| 约束 | 含义 |
|---|---|
| 数据真实性 | 所有数字必须来自 payload，禁止任何形式的估算、补全、编造 |
| 不给投资建议 | 简评必须保持描述性，避免任何买卖、加减仓的指向性表述 |
| 中文输出 | 报告全文中文，code 字段保留英文不翻译 |
| 长度可控 | 报告全文控制在 500 字以内，便于在 Slack/邮件里阅读 |
| 优雅降级 | 任何环节出错都不要让整个 routine 崩溃，至少留下错误日志 |

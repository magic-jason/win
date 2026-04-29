# ashare-monitor · A 股每日行情自动简报

最小可行版本（MVP）。Routine 每个交易日 15:30 触发一次，拉取主要指数行情，生成中文简报，输出到 `out/` 目录，可选推送到 Slack / Gmail。

## 项目结构

```
ashare-monitor/
├── SKILL.md                     # 给 Claude 看的"使用说明书"
├── README.md                    # 本文件，给人看
├── requirements.txt             # Python 依赖
├── ROUTINE_PROMPT.md            # 复制到 Routine 创建界面的 prompt
├── scripts/
│   └── fetch_market.py          # 拉行情，输出 JSON
├── templates/
│   └── daily_report.md          # 报告模板
└── out/                         # 生成的报告（运行时创建）
```

## 部署步骤

### 1. 把项目推到 GitHub

新建一个私有仓库（推荐私有，避免数据源密钥/连接器配置外泄），把整个目录推上去。

### 2. 在 Routine 创建配置

访问 [claude.ai/code/routines](https://claude.ai/code/routines)，点 **New routine**：

| 字段 | 填什么 |
|---|---|
| **Name** | `A 股每日简报` |
| **Repositories** | 选你刚推的仓库 |
| **Environment** | 默认环境即可，或自建一个把 `pip install -r requirements.txt` 放进 setup script |
| **Network access** | 必须开放，脚本要访问财经数据源 |
| **Connectors** | 按需保留 Slack / Gmail；其他全部移除 |
| **Permissions** | 允许 push 到 `claude/` 分支即可（默认） |
| **Trigger** | Schedule → Weekdays，时间 `15:30`（你的本地时区） |

**Prompt** 字段直接粘贴 `ROUTINE_PROMPT.md` 的内容。

### 3. 测试运行

不等到 15:30，在 Routine 详情页点 **Run now** 立即跑一次，看输出。常见问题：

- **akshare 在 Anthropic 云端访问不通**：脚本会自动回退到 yfinance（雅虎金融），但成交额数据会打折扣（雅虎给的是手数估算）
- **两个源都失败**：检查环境的 network access 是否开放
- **Slack 没收到**：检查 Routine 的 Connectors 列表是否包含 Slack，以及频道权限

## 本地手动测试

```bash
pip install -r requirements.txt
python scripts/fetch_market.py
```

正常会看到一段格式化的 JSON。

## 要扩展的话

这个 MVP 只覆盖最核心的指数行情。跑通 3 - 5 个交易日之后，可以按顺序加：

1. **北向资金当日净流入**（akshare 的 `stock_hsgt_fund_flow_summary_em`）
2. **行业板块涨跌前后 5**（akshare 的 `stock_board_industry_name_em`）
3. **个人持仓监控**：把你的关注股票列表放到 `config/watchlist.yaml`，加一个 `scripts/fetch_watchlist.py`
4. **新闻摘要**：让 Routine 用 web search 抓当日财经头条，混进 commentary
5. **历史对比**：把每日 JSON 也存档到 `out/history/`，新报告中加入"5 日均量对比"等维度

每加一个模块就改一次 `SKILL.md` 的"使用流程"小节，让 Claude 知道新脚本怎么调用。

## 安全注意事项

- **不要把 API key 写进代码**。如果将来接 tushare pro 等付费数据源，把 token 放在 Routine 的 Environment 变量里（如 `TUSHARE_TOKEN`），脚本通过 `os.environ.get(...)` 读取
- **仓库建议设为私有**，即使现在没有敏感信息
- **关闭 unrestricted branch push**，让 Claude 只能 push 到 `claude/` 前缀分支，避免误改主分支

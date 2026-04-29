#!/usr/bin/env python3
"""
拉取 A 股主要指数行情，输出 JSON 到 stdout。

设计：
- 优先使用 akshare（数据更准、含成交额）
- 失败回退 yfinance（雅虎金融，海外节点访问稳定）
- 任一数据源能拿到任一指数即视为部分成功
- 完全失败时退出码 1，部分/完全成功退出码 0
"""

import json
import sys
import traceback
from datetime import datetime

INDICES = [
    {"ak_code": "sh000001", "yf_code": "000001.SS", "name": "上证指数",  "key": "sh000001"},
    {"ak_code": "sz399001", "yf_code": "399001.SZ", "name": "深证成指",  "key": "sz399001"},
    {"ak_code": "sz399006", "yf_code": "399006.SZ", "name": "创业板指",  "key": "sz399006"},
    {"ak_code": "sh000300", "yf_code": "000300.SS", "name": "沪深300",   "key": "sh000300"},
    {"ak_code": "sh000688", "yf_code": "000688.SS", "name": "科创50",    "key": "sh000688"},
]


def fetch_via_akshare():
    """从 akshare 拉取所有指数的实时行情。"""
    import akshare as ak
    df = ak.stock_zh_index_spot_em()  # 东方财富数据源
    code_col = "代码"
    name_col = "名称"
    price_col = "最新价"
    pct_col = "涨跌幅"
    amount_col = "成交额"  # 单位：元

    result = []
    code_to_meta = {item["ak_code"]: item for item in INDICES}

    for _, row in df.iterrows():
        raw_code = str(row[code_col])
        # akshare em 接口返回的代码可能是纯数字，需要根据所属市场补前缀
        # 这里走名称匹配更稳妥
        for meta in INDICES:
            if row[name_col] == meta["name"]:
                try:
                    result.append({
                        "code": meta["key"],
                        "name": meta["name"],
                        "close": round(float(row[price_col]), 2),
                        "pct_change": round(float(row[pct_col]), 2),
                        "volume_yi": round(float(row[amount_col]) / 1e8, 1),
                    })
                except (ValueError, TypeError):
                    pass
                break
    return result


def fetch_via_yfinance():
    """从雅虎金融拉取指数收盘数据，作为 akshare 的备用。"""
    import yfinance as yf
    result = []
    for item in INDICES:
        try:
            ticker = yf.Ticker(item["yf_code"])
            hist = ticker.history(period="5d")
            if len(hist) < 1:
                continue
            last = hist.iloc[-1]
            prev_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else float(last["Open"])
            close = float(last["Close"])
            pct = (close - prev_close) / prev_close * 100 if prev_close else 0.0
            volume_yi = float(last["Volume"]) / 1e8  # 雅虎给的是手数，仅供参考
            result.append({
                "code": item["key"],
                "name": item["name"],
                "close": round(close, 2),
                "pct_change": round(pct, 2),
                "volume_yi": round(volume_yi, 1),
            })
        except Exception:
            continue
    return result


def main():
    errors = []
    indices = []
    source_used = None

    for source_name, fn in [("akshare", fetch_via_akshare), ("yfinance", fetch_via_yfinance)]:
        try:
            indices = fn()
            if indices:
                source_used = source_name
                break
        except Exception as e:
            errors.append({
                "source": source_name,
                "error": f"{type(e).__name__}: {e}",
                "trace": traceback.format_exc().splitlines()[-3:],
            })
            continue

    output = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": source_used,
        "indices": indices,
        "errors": errors,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if indices else 1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""命令行入口：python main_cli.py （交易日 9:25~9:30 运行）"""
import pandas as pd
from selector import StockSelector
from scorer import YaoScorer
from config import TOP_N_SHOW, DISCLAIMER

pd.set_option("display.unicode.east_asian_width", True)
pd.set_option("display.max_columns", 30)


def main():
    print("=" * 80)
    print("  妖股竞价选股器  |  六条件 + 游资席位 + 行为因子")
    print("=" * 80)
    selected, _, msg = StockSelector().run()
    if selected.empty:
        print(f"\n无符合条件个股：{msg}")
        return
    result = YaoScorer().score(selected)
    if result.empty:
        print("\n评分后无剩余标的")
        return

    cols = ["code", "name", "lianban", "auction_pct", "auction_turnover",
            "sell_ratio", "total_mv", "top_yzy", "lhb_net_buy",
            "seal_type", "妖股概率", "评级"]
    out = result[cols].head(TOP_N_SHOW).copy()
    out["lhb_net_buy"] = (out["lhb_net_buy"] / 1e4).round(0).astype(int)
    out.columns = ["代码", "名称", "连板", "竞价%", "竞价换手%", "委卖/委买",
                   "总市值(亿)", "顶级席位", "LHB净买(万)", "封单", "妖股概率", "评级"]
    print(f"\n{'=' * 80}")
    print(f"  选股结果（共 {len(result)} 只，显示概率前 {TOP_N_SHOW}）")
    print(f"{'=' * 80}")
    print(out.to_string(index=False))
    print(f"\n⚠️ {DISCLAIMER}")


if __name__ == "__main__":
    main()

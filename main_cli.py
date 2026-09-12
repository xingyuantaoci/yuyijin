# -*- coding: utf-8 -*-
"""命令行入口：python main_cli.py （交易日 9:25~9:30 运行）"""
from selector import StockSelector
from scorer import YaoScorer
from config import TOP_N_SHOW, DISCLAIMER


def _w(s, n):
    """中文按宽字符补空格对齐。"""
    s = str(s)
    w = sum(2 if ord(c) > 127 else 1 for c in s)
    return s + " " * max(0, n - w)


def main():
    print("=" * 80)
    print("  妖股竞价选股器  |  六条件 + 游资席位 + 行为因子")
    print("=" * 80)
    selected, _, msg = StockSelector().run()
    if not selected:
        print(f"\n无符合条件个股：{msg}")
        return
    result = YaoScorer().score(selected)
    if not result:
        print("\n评分后无剩余标的")
        return

    cols = [
        ("代码", "code", 8),
        ("名称", "name", 10),
        ("连板", "lianban", 6),
        ("竞价%", "auction_pct", 8),
        ("竞价换手%", "auction_turnover", 9),
        ("委卖/委买", "sell_ratio", 9),
        ("总市值(亿)", "total_mv", 10),
        ("顶级席位", "top_yzy", 12),
        ("LHB净买(万)", None, 11),
        ("封单", "seal_type", 14),
        ("妖股概率", "妖股概率", 9),
        ("评级", "评级", 6),
    ]
    head = "".join(_w(t, w) for t, _, w in cols)
    lines = []
    for r in result[:TOP_N_SHOW]:
        vals = []
        for title, key, w in cols:
            if title == "LHB净买(万)":
                v = int(round(r["lhb_net_buy"] / 1e4))
            else:
                v = r.get(key, "")
            if title in ("竞价%", "竞价换手%"):
                v = f"{v:.1f}" if isinstance(v, (int, float)) else v
            vals.append(_w(v, w))
        lines.append("".join(vals))

    print(f"\n{'=' * 80}")
    print(f"  选股结果（共 {len(result)} 只，显示概率前 {TOP_N_SHOW}）")
    print(f"{'=' * 80}")
    print(head)
    print("-" * len(head))
    for ln in lines:
        print(ln)
    print(f"\n⚠️ {DISCLAIMER}")


if __name__ == "__main__":
    main()

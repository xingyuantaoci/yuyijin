# -*- coding: utf-8 -*-
"""妖股概率评分模型：连板20% + 席位15% + 竞价15% + 卖压10%
                      + 市值5% + 新鲜度5% + 行为30%"""
import numpy as np
import pandas as pd
from mobile_fetcher import DataFetcher
from seat_matcher import SeatMatcher
from behavior_analyzer import BehaviorAnalyzer
from config import RATING_BINS, RATING_LABELS

WEIGHTS = {"lianban": 0.20, "lhb": 0.15, "auction": 0.15, "sell": 0.10,
           "mv": 0.05, "fresh": 0.05, "behavior": 0.30}


class YaoScorer:

    def __init__(self):
        self.fetcher = DataFetcher()
        self.matcher = SeatMatcher()
        self.behavior = BehaviorAnalyzer()

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        d = df.copy()

        # --- 席位因子（逐只拉取龙虎榜席位明细，识别顶级游资）---
        seat_map = {}
        lhb_rows = d[d["lhb_date"].astype(str) != ""]
        for _, r in lhb_rows.iterrows():
            try:
                dt = pd.to_datetime(str(r["lhb_date"])[:10]).strftime("%Y%m%d")
            except Exception:
                continue
            detail = self.fetcher.lhb_seat_detail(r["code"], dt)
            m = self.matcher.match(detail)
            if r["code"] in m:
                seat_map[r["code"]] = m[r["code"]]
        d["seat_score"]  = d["code"].map(lambda c: seat_map.get(c, {}).get("seat_score", 30))
        d["top_yzy"]     = d["code"].map(lambda c: seat_map.get(c, {}).get("top_tag", "无"))
        d["has_smasher"] = d["code"].map(lambda c: seat_map.get(c, {}).get("has_smasher", False))
        sig = 100 / (1 + np.exp(-3 * (d["lhb_net_buy"] / 1e8 - 0.5)))
        d["s_lhb"] = (d["seat_score"] * 0.7 + sig * 0.3)
        d.loc[d["has_smasher"], "s_lhb"] -= 15
        d["s_lhb"] = d["s_lhb"].clip(0, 100)

        # --- 连板因子 ---
        d["s_lianban"] = d["lianban"].apply(
            lambda x: min(95, 30 + 30 * int(str(x).replace("天", "") or 1)))

        # --- 竞价因子（5~9% 最佳，过高临近涨停反而扣分）---
        d["s_auction"] = (100 - (d["auction_pct"] - 7).abs() * 20 +
                          (d["auction_turnover"] - 2).clip(0, 5) * 4).clip(0, 100)

        # --- 卖压因子（委卖/委买 1~3倍=洗盘最佳，>5倍=真出货）---
        ratio = d["sell_vol"] / d["buy_vol"].replace(0, np.nan)
        d["sell_ratio"] = ratio.round(2)
        d["s_sell"] = np.where(ratio.between(1, 3), 90,
                      np.where(ratio > 5, 30, 60))

        # --- 市值因子（越小弹性越大）---
        d["s_mv"] = np.interp(d["total_mv"], [0, 50, 150, 300], [100, 90, 65, 40])

        # --- 新鲜度（涨停距今越近越好）---
        try:
            latest = self.fetcher.recent_trade_dates(1)[0]
            d["s_fresh"] = d["zt_date"].apply(
                lambda x: 100 - (pd.to_datetime(latest) -
                                 pd.to_datetime(str(x))).days * 15).clip(40, 100)
        except Exception:
            d["s_fresh"] = 100

        # --- 行为因子（竞价阶段封单中性，撤单/异动用当日分钟数据近似）---
        b_scores, seal_types, notes = [], [], []
        for _, r in d.iterrows():
            ss, st = self.behavior.seal_strength(0, r.get("price", 0),
                                                 r["circ_mv"], 0)
            cs, _, cn = self.behavior.cancel_rate(r["code"], 0)
            as_, an = self.behavior.intraday_anomaly(r["code"])
            b_scores.append(ss * 0.35 + cs * 0.30 + as_ * 0.35)
            seal_types.append(st)
            notes.append(f"撤:{cn} 异:{an}")
        d["s_behavior"] = pd.Series(b_scores, index=d.index).clip(0, 100)
        d["seal_type"] = seal_types
        d["behavior_note"] = notes

        # --- 总分 ---
        d["妖股概率"] = (
            d["s_lianban"]  * WEIGHTS["lianban"] +
            d["s_lhb"]      * WEIGHTS["lhb"] +
            d["s_auction"]  * WEIGHTS["auction"] +
            d["s_sell"]     * WEIGHTS["sell"] +
            d["s_mv"]       * WEIGHTS["mv"] +
            d["s_fresh"]    * WEIGHTS["fresh"] +
            d["s_behavior"] * WEIGHTS["behavior"]
        ).round(1)
        d["评级"] = pd.cut(d["妖股概率"], RATING_BINS, labels=RATING_LABELS)

        # --- 硬风控：疑似假封 + 高撤单直接剔除 ---
        bad = (d["seal_type"].str.contains("假封") &
               d["behavior_note"].str.contains("撤单诱多"))
        d = d[~bad]
        return d.sort_values("妖股概率", ascending=False)

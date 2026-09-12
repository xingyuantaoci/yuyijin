# -*- coding: utf-8 -*-
"""六条件硬性筛选"""
import pandas as pd
from mobile_fetcher import DataFetcher
from config import (MAX_TOTAL_MV, MIN_AUCTION_TURNOVER, MIN_AUCTION_PCT)


class StockSelector:
    """① 三日内涨停  ② 竞价换手>2%  ③ 竞价涨幅>5%
    ④ 委卖>委买    ⑤ 总市值<=300亿  ⑥ 龙虎榜资金(加分项)"""

    def __init__(self):
        self.fetcher = DataFetcher()

    def run(self, progress_cb=None):
        def log(m):
            print(m)
            if progress_cb:
                progress_cb(m)
            return m

        # ① 近三日涨停池
        log("① 拉取近三日涨停池...")
        pool = self.fetcher.limit_up_pool_3d()
        if pool.empty:
            return pd.DataFrame(), pd.DataFrame(), "涨停池为空（非交易日或接口异常）"
        cand = pool[["代码", "名称", "连板数", "换手率", "流通市值", "zt_date"]].copy()
        cand.columns = ["code", "name", "lianban", "to_yest",
                        "circ_mv_raw", "zt_date"]
        cand["code"] = cand["code"].astype(str).str.zfill(6)
        log(f"   涨停池 {len(cand)} 只")

        # ② 龙虎榜（近三日股票级净买额）
        log("② 拉取近三日龙虎榜...")
        lhb_agg = self.fetcher.lhb_recent()
        if not lhb_agg.empty:
            lhb_agg["code"] = lhb_agg["代码"].astype(str).str.zfill(6)
            cand = cand.merge(
                lhb_agg[["code", "lhb_net_buy", "lhb_date", "lhb_reason"]],
                on="code", how="left")
        else:
            cand["lhb_net_buy"] = 0
            cand["lhb_date"] = ""
            cand["lhb_reason"] = ""
        cand["lhb_net_buy"] = cand["lhb_net_buy"].fillna(0)
        cand["lhb_date"] = cand["lhb_date"].fillna("")
        log(f"   龙虎榜命中 {int((cand['lhb_net_buy'] != 0).sum())} 只")

        # ③ 竞价快照（须在交易日 9:25~9:30 运行）
        log("③ 抓取竞价快照（须在交易日 9:25~9:30 运行）...")
        auc = self.fetcher.auction_snapshot(cand["code"].tolist())
        if auc.empty:
            return pd.DataFrame(), cand, "竞价数据为空，请在交易日 9:25 后运行"
        cand = cand.merge(auc, on="code", how="inner")
        log(f"   快照成功 {len(cand)} 只")

        # ④ 硬性过滤
        log("④ 执行硬性条件过滤...")
        mask = ((cand["auction_turnover"] > MIN_AUCTION_TURNOVER) &
                (cand["auction_pct"]      > MIN_AUCTION_PCT) &
                (cand["sell_vol"]         > cand["buy_vol"]) &
                (cand["total_mv"]         <= MAX_TOTAL_MV) &
                (cand["circ_mv"]          > 0))
        selected = cand[mask].copy()
        log(f"   过滤后剩余 {len(selected)} 只")
        return selected, cand, "OK"

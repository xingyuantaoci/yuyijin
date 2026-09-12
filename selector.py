# -*- coding: utf-8 -*-
"""六条件硬性筛选（纯 Python list[dict] 数据层）"""
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
        if not pool:
            return [], [], "涨停池为空（非交易日或接口异常）"
        cand = [{
            "code": str(r["代码"]).zfill(6),
            "name": r["名称"],
            "lianban": r["连板数"],
            "to_yest": r["换手率"],
            "circ_mv_raw": r["流通市值"],
            "zt_date": r.get("zt_date", ""),
        } for r in pool]
        log(f"   涨停池 {len(cand)} 只")

        # ② 龙虎榜（近三日股票级净买额）
        log("② 拉取近三日龙虎榜...")
        lhb_agg = self.fetcher.lhb_recent()
        lhb_map = {str(r["代码"]).zfill(6): r for r in lhb_agg}
        for c in cand:
            l = lhb_map.get(c["code"])
            if l:
                c["lhb_net_buy"] = l["lhb_net_buy"]
                c["lhb_date"] = l["lhb_date"]
                c["lhb_reason"] = l["lhb_reason"]
            else:
                c["lhb_net_buy"] = 0
                c["lhb_date"] = ""
                c["lhb_reason"] = ""
        hit = sum(1 for c in cand if c["lhb_net_buy"] != 0)
        log(f"   龙虎榜命中 {hit} 只")

        # ③ 竞价快照（须在交易日 9:25~9:30 运行）
        log("③ 抓取竞价快照（须在交易日 9:25~9:30 运行）...")
        codes = [c["code"] for c in cand]
        auc = self.fetcher.auction_snapshot(codes)
        if not auc:
            return [], cand, "竞价数据为空，请在交易日 9:25 后运行"
        auc_map = {a["code"]: a for a in auc}
        merged = []
        for c in cand:
            a = auc_map.get(c["code"])
            if a:
                c.update(a)
                merged.append(c)
        cand = merged
        log(f"   快照成功 {len(cand)} 只")

        # ④ 硬性过滤
        log("④ 执行硬性条件过滤...")
        selected = [c for c in cand if
                   c.get("auction_turnover", 0) > MIN_AUCTION_TURNOVER and
                   c.get("auction_pct", 0) > MIN_AUCTION_PCT and
                   c.get("sell_vol", 0) > c.get("buy_vol", 0) and
                   c.get("total_mv", 0) <= MAX_TOTAL_MV and
                   c.get("circ_mv", 0) > 0]
        log(f"   过滤后剩余 {len(selected)} 只")
        return selected, cand, "OK"

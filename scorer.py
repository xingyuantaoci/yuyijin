# -*- coding: utf-8 -*-
"""妖股概率评分模型：连板20% + 席位15% + 竞价15% + 卖压10%
                      + 市值5% + 新鲜度5% + 行为30%（纯 Python，无 numpy/pandas）"""
import math
from datetime import datetime
from mobile_fetcher import DataFetcher
from seat_matcher import SeatMatcher
from behavior_analyzer import BehaviorAnalyzer
from config import RATING_BINS, RATING_LABELS

WEIGHTS = {"lianban": 0.20, "lhb": 0.15, "auction": 0.15, "sell": 0.10,
           "mv": 0.05, "fresh": 0.05, "behavior": 0.30}


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def _interp(x, xp, fp):
    """线性插值，等价 numpy.interp（xp 升序）。"""
    if x <= xp[0]:
        return fp[0]
    if x >= xp[-1]:
        return fp[-1]
    for i in range(len(xp) - 1):
        if xp[i] <= x <= xp[i + 1]:
            t = (x - xp[i]) / (xp[i + 1] - xp[i])
            return fp[i] + t * (fp[i + 1] - fp[i])
    return fp[-1]


def _parse_date(s):
    s = str(s)[:10].replace("-", "")
    return datetime(int(s[:4]), int(s[4:6]), int(s[6:8]))


def _rating(score):
    # pd.cut([0,40,60,75,100]) -> (0,40]观望 (40,60]关注 (60,75]潜伏 (75,100]重点
    if score <= RATING_BINS[1]:
        return RATING_LABELS[0]
    if score <= RATING_BINS[2]:
        return RATING_LABELS[1]
    if score <= RATING_BINS[3]:
        return RATING_LABELS[2]
    return RATING_LABELS[3]


class YaoScorer:

    def __init__(self):
        self.fetcher = DataFetcher()
        self.matcher = SeatMatcher()
        self.behavior = BehaviorAnalyzer()

    def score(self, rows):
        if not rows:
            return []

        # --- 席位因子（逐只拉取龙虎榜席位明细，识别顶级游资）---
        seat_map = {}
        for r in rows:
            if str(r.get("lhb_date", "")) == "":
                continue
            try:
                dt = str(r["lhb_date"])[:10].replace("-", "")
            except Exception:
                continue
            detail = self.fetcher.lhb_seat_detail(r["code"], dt)
            m = self.matcher.match(detail)
            if r["code"] in m:
                seat_map[r["code"]] = m[r["code"]]

        # --- 新鲜度基准 ---
        try:
            latest = _parse_date(self.fetcher.recent_trade_dates(1)[0])
        except Exception:
            latest = None

        for r in rows:
            sm = seat_map.get(r["code"], {})
            r["seat_score"] = sm.get("seat_score", 30)
            r["top_yzy"] = sm.get("top_tag", "无")
            r["has_smasher"] = sm.get("has_smasher", False)

            # 龙虎榜因子：sigmoid 映射净买额
            sig = 100 / (1 + math.exp(-3 * (r["lhb_net_buy"] / 1e8 - 0.5)))
            s_lhb = r["seat_score"] * 0.7 + sig * 0.3
            if r["has_smasher"]:
                s_lhb -= 15
            r["s_lhb"] = _clip(s_lhb, 0, 100)

            # 连板因子
            lb = int(str(r["lianban"]).replace("天", "") or 1)
            r["s_lianban"] = min(95, 30 + 30 * lb)

            # 竞价因子（5~9% 最佳）
            s_auction = 100 - abs(r["auction_pct"] - 7) * 20 + \
                        _clip(r["auction_turnover"] - 2, 0, 5) * 4
            r["s_auction"] = _clip(s_auction, 0, 100)

            # 卖压因子
            buy = r.get("buy_vol", 0)
            ratio = r["sell_vol"] / buy if buy else float("inf")
            r["sell_ratio"] = round(ratio, 2) if math.isfinite(ratio) else 99.99
            if 1 <= ratio <= 3:
                r["s_sell"] = 90
            elif ratio > 5:
                r["s_sell"] = 30
            else:
                r["s_sell"] = 60

            # 市值因子
            r["s_mv"] = _interp(r["total_mv"], [0, 50, 150, 300], [100, 90, 65, 40])

            # 新鲜度
            if latest is not None and r.get("zt_date"):
                try:
                    days = (latest - _parse_date(r["zt_date"])).days
                    r["s_fresh"] = _clip(100 - days * 15, 40, 100)
                except Exception:
                    r["s_fresh"] = 100
            else:
                r["s_fresh"] = 100

            # 行为因子
            ss, st = self.behavior.seal_strength(0, r.get("price", 0),
                                                 r.get("circ_mv", 0), 0)
            cs, _, cn = self.behavior.cancel_rate(r["code"], 0)
            as_, an = self.behavior.intraday_anomaly(r["code"])
            r["s_behavior"] = _clip(ss * 0.35 + cs * 0.30 + as_ * 0.35, 0, 100)
            r["seal_type"] = st
            r["behavior_note"] = f"撤:{cn} 异:{an}"

            # 总分
            total = (r["s_lianban"] * WEIGHTS["lianban"] +
                     r["s_lhb"] * WEIGHTS["lhb"] +
                     r["s_auction"] * WEIGHTS["auction"] +
                     r["s_sell"] * WEIGHTS["sell"] +
                     r["s_mv"] * WEIGHTS["mv"] +
                     r["s_fresh"] * WEIGHTS["fresh"] +
                     r["s_behavior"] * WEIGHTS["behavior"])
            r["妖股概率"] = round(total, 1)
            r["评级"] = _rating(r["妖股概率"])

        # --- 硬风控：疑似假封 + 高撤单直接剔除 ---
        result = [r for r in rows
                  if not ("假封" in r["seal_type"] and "撤单诱多" in r["behavior_note"])]
        result.sort(key=lambda r: r["妖股概率"], reverse=True)
        return result

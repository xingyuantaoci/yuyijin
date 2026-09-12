# -*- coding: utf-8 -*-
"""游资席位匹配引擎"""
import pandas as pd
from yzy_seats import YZY_SEATS, LEVEL_SCORE, SMASHER_TAGS, COMBO_BONUS


class SeatMatcher:
    """输入龙虎榜席位明细，输出 {code: 席位特征} 字典。
    明细需含列: 代码 / 交易营业部名称 / 买入金额 / 卖出金额
    """

    def match(self, detail: pd.DataFrame) -> dict:
        result = {}
        if detail is None or detail.empty:
            return result

        for code, grp in detail.groupby("代码"):
            seats, tags = [], set()
            max_level, top_tag = "C", "无"
            smasher = False

            for _, row in grp.iterrows():
                dept = str(row.get("交易营业部名称", ""))
                net = float(row.get("买入金额", 0) or 0) - \
                      float(row.get("卖出金额", 0) or 0)
                level, tag = self._match_seat(dept)
                seats.append((dept, level, tag, net))
                tags.add(tag)
                if LEVEL_SCORE[level] > LEVEL_SCORE[max_level]:
                    max_level, top_tag = level, tag
                if tag in SMASHER_TAGS and net < 0:   # 砸盘王且净卖出才计入
                    smasher = True

            score = self._seat_score(seats, max_level)
            combo = sum(v for k, v in COMBO_BONUS.items() if k.issubset(tags))
            result[str(code)] = {
                "max_level":   max_level,
                "top_tag":     top_tag if top_tag != "无" else "未知",
                "seat_score":  max(0, min(100, score + combo)),
                "has_smasher": smasher,
                "net_total":   sum(s[3] for s in seats),
            }
        return result

    @staticmethod
    def _match_seat(dept: str):
        for key, (level, tag) in YZY_SEATS.items():
            if key in dept:
                return level, tag
        return "C", "未知"

    @staticmethod
    def _seat_score(seats, max_level):
        base = LEVEL_SCORE[max_level]
        same = sum(1 for s in seats if s[1] == max_level)
        count_bonus = min(20, (same - 1) * 5)            # 同级席位数量加成
        amt_bonus = 0
        for _, lv, _, net in seats:
            if lv == "S" and net > 3e7:
                amt_bonus += 10
            elif lv == "A" and net > 2e7:
                amt_bonus += 5
        return base + count_bonus + min(amt_bonus, 20)

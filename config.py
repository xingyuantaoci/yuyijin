# -*- coding: utf-8 -*-
"""全局配置"""

MAX_TOTAL_MV = 300.0          # 总市值上限（亿）
MIN_AUCTION_TURNOVER = 2.0    # 竞价换手率下限（%）
MIN_AUCTION_PCT = 5.0         # 9:25 竞价涨幅下限（%）
LOOKBACK_DAYS = 3             # 回看涨停天数
REQUEST_SLEEP = 0.4           # 接口请求间隔（秒），防风控
TOP_N_SHOW = 20               # 显示前 N 只

RATING_BINS = [0, 40, 60, 75, 100]
RATING_LABELS = ["观望", "关注", "潜伏", "重点"]

DISCLAIMER = "仅供研究学习，不构成投资建议。妖股博弈风险极高，请严守止损纪律。"

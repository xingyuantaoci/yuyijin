# -*- coding: utf-8 -*-
"""行为因子：封单强度 / 撤单率估算 / 分时异动（免费数据源近似版）
盘中(9:30-15:00)调用才有完整意义；竞价阶段自动降级为中性分。
"""
import time
import requests
import pandas as pd
import numpy as np

EM_UT = "7eea3edcaed734bea9cbfc24409ed989"
HEADERS = {"User-Agent": "Mozilla/5.0 (Linux; Android 13)"}


class BehaviorAnalyzer:

    # ---------- 1. 封单强度 ----------
    @staticmethod
    def seal_strength(buy1_vol_hand, price, circ_mv_yi, limit_up):
        """封单金额/流通市值 倒U型评分：0.5%~3% 为黄金区间"""
        if limit_up <= 0 or price < limit_up * 0.998:
            return 50, "未涨停(中性)"
        seal_amt = buy1_vol_hand * 100 * price
        ratio = seal_amt / (circ_mv_yi * 1e8) * 100 if circ_mv_yi > 0 else 0
        if ratio < 0.1:
            return 20, f"弱封({ratio:.2f}%)"
        if ratio < 0.5:
            return 60, f"正常封({ratio:.2f}%)"
        if ratio <= 3.0:
            return 95, f"强封({ratio:.2f}%)"
        if ratio <= 8.0:
            return 70, f"超强封({ratio:.2f}%)"
        return 35, f"疑似假封({ratio:.2f}%)"

    # ---------- 2. 撤单率估算（分钟量能法） ----------
    @staticmethod
    def cancel_rate(code, buy1_vol_hand):
        minutes = BehaviorAnalyzer.minute_kline(code, limit=3)
        if len(minutes) < 2:
            return 50, 0.30, "数据不足(中性)"
        v_prev = minutes["volume"].iloc[-2]
        v_curr = minutes["volume"].iloc[-1]
        shrink = 1 - v_curr / v_prev if v_prev > 0 else 0
        if shrink > 0.7 and buy1_vol_hand > 5000:
            return 90, 0.10, "量缩封稳"
        if shrink > 0.7 and buy1_vol_hand < 1000:
            return 25, 0.50, "疑似撤单诱多"
        if shrink < 0.3:
            return 70, 0.20, "持续换手"
        return 55, 0.30, "一般"

    # ---------- 3. 分时异动 ----------
    @staticmethod
    def intraday_anomaly(code):
        minutes = BehaviorAnalyzer.minute_kline(code, limit=60)
        if len(minutes) < 10:
            return 50, "数据不足(中性)"
        avg_vol = minutes["volume"].mean()
        big_buys = int((minutes["volume"] > avg_vol * 3).sum())   # 大单脉冲次数
        vwap = (minutes["amount"].cumsum() /
                minutes["volume"].cumsum().replace(0, np.nan))
        above = float((minutes["close"] >= vwap).fillna(False).mean())
        if len(minutes) >= 20:
            recent = minutes["close"].iloc[-1] / minutes["close"].iloc[-10] - 1
            earlier = minutes["close"].iloc[-11] / minutes["close"].iloc[-20] - 1
            accel = float(recent - earlier)
        else:
            accel = 0.0
        score = (min(35, big_buys * 7) + min(35, above * 40) +
                 min(30, max(0.0, accel * 500)))
        notes = []
        if big_buys >= 3:
            notes.append(f"{big_buys}次大单")
        if above > 0.8:
            notes.append("守均价线")
        if accel > 0.02:
            notes.append("加速拉升")
        return min(100, round(score, 1)), (";".join(notes) or "无异动")

    # ---------- 分钟K线 ----------
    @staticmethod
    def minute_kline(code, limit=60):
        secid = ("1." if str(code).startswith("6") else "0.") + str(code).zfill(6)
        try:
            resp = requests.get(
                "https://push2his.eastmoney.com/api/qt/stock/kline/get",
                params={"secid": secid, "klt": "1", "fqt": "1",
                        "lmt": str(limit), "end": "20500101",
                        "fields1": "f1,f2,f3",
                        "fields2": "f51,f53,f56,f57",
                        "ut": EM_UT},
                timeout=6, headers=HEADERS).json()
            klines = (resp.get("data") or {}).get("klines") or []
            if not klines:
                return pd.DataFrame(columns=["time", "close", "volume", "amount"])
            rows = [k.split(",") for k in klines]
            df = pd.DataFrame(rows, columns=["time", "close", "volume", "amount"])
            for c in ("close", "volume", "amount"):
                df[c] = pd.to_numeric(df[c], errors="coerce")
            time.sleep(0.15)
            return df.tail(limit).reset_index(drop=True)
        except Exception:
            return pd.DataFrame(columns=["time", "close", "volume", "amount"])

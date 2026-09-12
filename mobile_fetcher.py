# -*- coding: utf-8 -*-
"""移动端/本地数据层：纯 requests 直连东方财富公开接口，无 akshare / pandas 依赖。

PC 命令行版与 APK 版共用本模块（APK 版直接 import 本文件）。
表格统一用 list[dict] 表示（空表为 []），字段与量纲已通过 2026-09-11 实盘数据验证：
  - 涨停池  getTopicZTPool：hs 换手率已是百分比（如 10.47 即 10.47%），不要再除以 1000
  - 龙虎榜  RPT_DAILYBILLBOARD_DETAILSNEW：BILLBOARD_NET_AMT 单位元，可为负
  - 席位明细 买入报表 RPT_BILLBOARD_DAILYDETAILSBUY / 卖出报表 RPT_BILLBOARD_DAILYDETAILSSELL（注意是双 S）
  - 实时快照 push2 stock/get：五档字段映射为
      买一价 f19 买一量 f20；买二 f17/f18；买三 f15/f16；买四 f13/f14；买五 f11/f12
      卖一价 f39 卖一量 f40；卖二 f37/f38；卖三 f35/f36；卖四 f33/f34；卖五 f31/f32
"""
import time
import requests
from datetime import datetime

UT = "7eea3edcaed734bea9cbfc24409ed989"
HEADERS = {"User-Agent": "Mozilla/5.0 (Linux; Android 13)"}
DC = "https://datacenter-web.eastmoney.com/api/data/v1/get"


class DataFetcher:
    """统一数据接口：交易日历 / 涨停池 / 龙虎榜 / 席位明细 / 竞价快照"""

    # ---------- 交易日历（上证指数日K近似；push2his 不可用时切腾讯日K） ----------
    @staticmethod
    def recent_trade_dates(n=3):
        today = datetime.now().strftime("%Y%m%d")
        for host in ("push2his.eastmoney.com", "web.ifzq.gtimg.cn"):
            try:
                if host.startswith("push2his"):
                    resp = requests.get(
                        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
                        params={"secid": "1.000001", "klt": "101", "fqt": "1",
                                "lmt": str(max(n, 5)), "end": "20500101",
                                "fields1": "f1", "fields2": "f51", "ut": UT},
                        timeout=8, headers=HEADERS).json()
                    klines = (resp.get("data") or {}).get("klines") or []
                    dates = [k.split(",")[0].replace("-", "") for k in klines]
                else:
                    resp = requests.get(
                        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
                        params={"param": "sh000001,day,,,%d,qfq" % max(n, 5)},
                        timeout=8, headers=HEADERS).json()
                    k = (resp.get("data") or {}).get("sh000001") or {}
                    days = k.get("day") or k.get("qfqday") or []
                    dates = [str(x[0]).replace("-", "") for x in days]
                dates = [d for d in dates if d <= today]
                if len(dates) >= n:
                    return dates[-n:]
            except Exception:
                continue
        return [today]

    # ---------- 涨停池（东财涨停板行情专题接口） ----------
    def limit_up_pool_3d(self):
        rows_all = []
        for d in self.recent_trade_dates(3):
            rows = self._zt_pool_one_day(d)
            if rows:
                for r in rows:
                    r["zt_date"] = d
                rows_all.extend(rows)
            time.sleep(0.4)
        if not rows_all:
            return []
        # 同一股票保留连板数最大的记录（同板数时保留更近一天）
        best = {}
        for r in rows_all:
            code = r["代码"]
            if code not in best or (r["连板数"], r["zt_date"]) > (best[code]["连板数"], best[code]["zt_date"]):
                best[code] = r
        return list(best.values())

    @staticmethod
    def _zt_pool_one_day(date):
        try:
            resp = requests.get(
                "https://push2ex.eastmoney.com/getTopicZTPool",
                params={"ut": UT, "dpt": "wz.ztzt", "Pageindex": "0",
                        "pagesize": "400", "sort": "fbt:asc", "date": date},
                timeout=8, headers=HEADERS).json()
            items = ((resp.get("data") or {}).get("pool")) or []
            if not items:
                return []
            return [{
                "代码": str(it.get("c", "")).zfill(6),
                "名称": it.get("n", ""),
                "连板数": it.get("lbc", 1) or 1,
                # 实测：hs 已是百分比（10.47 即 10.47%），直接保留
                "换手率": round(float(it.get("hs", 0) or 0), 2),
                "流通市值": (it.get("ltsz", 0) or 0),      # 元
                "炸板次数": it.get("zbc", 0) or 0,
            } for it in items]
        except Exception:
            return []

    # ---------- 龙虎榜（数据中心接口） ----------
    def lhb_recent(self):
        rows_all = []
        for d in self.recent_trade_dates(3):
            rows = self._lhb_one_day(d)
            if rows:
                rows_all.extend(rows)
            time.sleep(0.4)
        if not rows_all:
            return []
        # group by 代码：净买额求和、上榜日期取最大、原因去重拼接
        agg = {}
        for r in rows_all:
            code = str(r["代码"]).zfill(6)
            a = agg.get(code)
            if a is None:
                agg[code] = {
                    "代码": code,
                    "lhb_net_buy": r["龙虎榜净买额"],
                    "lhb_date": r["上榜日期"],
                    "lhb_reason_set": {str(r["上榜原因"])} if r["上榜原因"] else set(),
                }
            else:
                a["lhb_net_buy"] += r["龙虎榜净买额"]
                if r["上榜日期"] > a["lhb_date"]:
                    a["lhb_date"] = r["上榜日期"]
                if r["上榜原因"]:
                    a["lhb_reason_set"].add(str(r["上榜原因"]))
        out = []
        for a in agg.values():
            rs = sorted(x for x in a.pop("lhb_reason_set") if x and x != "None")
            a["lhb_reason"] = "/".join(rs)
            out.append(a)
        return out

    @staticmethod
    def _lhb_one_day(date):
        ymd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        try:
            resp = requests.get(DC, params={
                "sortColumns": "SECURITY_CODE,TRADE_DATE", "sortTypes": "1,-1",
                "pageSize": "500", "pageNumber": "1",
                "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
                "columns": "ALL", "source": "WEB", "client": "WEB",
                "filter": f"(TRADE_DATE<='{ymd}')(TRADE_DATE>='{ymd}')",
            }, timeout=8, headers=HEADERS).json()
            data = (resp.get("result") or {}).get("data") or []
            if not data:
                return []
            return [{
                "代码": str(it.get("SECURITY_CODE", "")).zfill(6),
                "名称": it.get("SECURITY_NAME_ABBR", ""),
                "上榜日期": str(it.get("TRADE_DATE", ""))[:10],
                "龙虎榜净买额": it.get("BILLBOARD_NET_AMT", 0) or 0,   # 元，可为负
                "上榜原因": it.get("EXPLANATION", ""),
            } for it in data]
        except Exception:
            return []

    # ---------- 龙虎榜席位明细（用于游资识别） ----------
    def lhb_seat_detail(self, code: str, date: str):
        """code: 6位代码, date: YYYYMMDD。返回买入+卖出席位合并明细 list[dict]。"""
        ymd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        rows = []
        # 注意卖出报表名是双 S：RPT_BILLBOARD_DAILYDETAILSSELL（实测单 S 报表不存在）
        for rpt in ("RPT_BILLBOARD_DAILYDETAILSBUY", "RPT_BILLBOARD_DAILYDETAILSSELL"):
            try:
                resp = requests.get(DC, params={
                    "sortColumns": "BUY,SELL,OPERATEDEPT_NAME",
                    "sortTypes": "-1,-1,1",
                    "pageSize": "50", "pageNumber": "1",
                    "reportName": rpt, "columns": "ALL",
                    "source": "WEB", "client": "WEB",
                    "filter": f"(TRADE_DATE<='{ymd}')(TRADE_DATE>='{ymd}')"
                              f'(SECURITY_CODE="{code}")',
                }, timeout=8, headers=HEADERS).json()
                data = (resp.get("result") or {}).get("data") or []
                for it in data:
                    rows.append({
                        "代码": str(code).zfill(6),
                        "交易营业部名称": it.get("OPERATEDEPT_NAME", ""),
                        "买入金额": it.get("BUY", 0) or 0,
                        "卖出金额": it.get("SELL", 0) or 0,
                    })
            except Exception:
                pass
            time.sleep(0.3)
        return rows

    # ---------- 竞价快照（9:25~9:30 调用才有意义） ----------
    EM_FIELDS = ("f43,f47,f60,f84,f85,f116,f117,f168,f170,"
                 "f19,f20,f17,f18,f15,f16,f13,f14,f11,f12,"
                 "f31,f32,f33,f34,f35,f36,f37,f38,f39,f40")

    def auction_snapshot(self, codes):
        rows = []
        for i, code in enumerate(codes):
            r = self._em_quote(str(code).zfill(6))
            if r:
                rows.append(r)
            if (i + 1) % 30 == 0:
                print(f"   快照进度 {i+1}/{len(codes)}")
            time.sleep(0.12)
        return rows

    def _em_quote(self, code):
        secid = ("1." if code.startswith("6") else "0.") + code
        d = None
        for attempt in range(3):   # 轻量重试，规避瞬时断连/限流
            try:
                resp = requests.get(
                    "https://push2.eastmoney.com/api/qt/stock/get",
                    params={"secid": secid, "fields": self.EM_FIELDS, "ut": UT},
                    timeout=5, headers=HEADERS).json()
                d = resp.get("data") or {}
                if d:
                    break
            except Exception:
                pass
            time.sleep(0.6)
        if not d:
            return None
        prev = (d.get("f60") or 0) / 100.0
        if not prev:
            return None
        price = (d.get("f43") or d.get("f60")) / 100.0
        circ_share = d.get("f85") or 0
        vol = d.get("f47") or 0                          # 手
        # 五档量（手）：买一量 f20 买二量 f18 买三量 f16 买四量 f14 买五量 f12
        #             卖一量 f32 卖二量 f34 卖三量 f36 卖四量 f38 卖五量 f40
        buy_vol = sum(d.get(k, 0) or 0 for k in ("f20", "f18", "f16", "f14", "f12"))
        sell_vol = sum(d.get(k, 0) or 0 for k in ("f32", "f34", "f36", "f38", "f40"))
        return {
            "code": code,
            "price": price,
            "auction_pct": round((price - prev) / prev * 100, 2),
            "auction_turnover": round(vol * 100 / circ_share * 100, 2) if circ_share else 0,
            "buy_vol": buy_vol,
            "sell_vol": sell_vol,
            "total_mv": (d.get("f116") or 0) / 1e8,     # 亿
            "circ_mv": (d.get("f117") or 0) / 1e8,      # 亿
        }

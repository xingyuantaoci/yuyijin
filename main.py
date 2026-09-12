# -*- coding: utf-8 -*-
"""Kivy APP 版（APK 打包入口）。数据层为纯 requests 的 mobile_fetcher，
与 PC 命令行版共用同一套 selector/scorer，无 akshare 依赖。"""
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
import threading

from selector import StockSelector
from scorer import YaoScorer
from config import TOP_N_SHOW, DISCLAIMER

HEADERS = ["名称/代码", "连板", "竞价%", "LHB净买(万)",
           "顶级席位", "封单/异动", "妖股概率/评级"]


class YaoStockApp(App):
    def build(self):
        self.title = "妖股竞价选股器"
        root = BoxLayout(orientation="vertical", padding=8, spacing=6)

        root.add_widget(Label(
            text="[b]妖股竞价选股器[/b]  六条件 + 席位 + 行为因子",
            markup=True, size_hint_y=None, height=40, font_size=17))

        self.lbl_status = Label(text="就绪：请在交易日 9:25~9:30 点击开始",
                                size_hint_y=None, height=36,
                                color=(1, .8, 0, 1), font_size=13)
        root.add_widget(self.lbl_status)

        self.btn = Button(text="开 始 选 股", size_hint_y=None, height=52,
                          background_color=(.9, .2, .2, 1), font_size=18)
        self.btn.bind(on_release=self.start_scan)
        root.add_widget(self.btn)

        scroll = ScrollView()
        self.grid = GridLayout(cols=len(HEADERS), size_hint_y=None, spacing=1)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        scroll.add_widget(self.grid)
        root.add_widget(scroll)
        self._draw_header()

        root.add_widget(Label(text=DISCLAIMER, size_hint_y=None, height=28,
                              font_size=10, color=(.6, .6, .6, 1)))
        return root

    def _draw_header(self):
        self.grid.clear_widgets()
        for h in HEADERS:
            self.grid.add_widget(Label(text=h, bold=True, size_hint_y=None,
                                       height=36, font_size=11, color=(0, 1, 1, 1)))

    def start_scan(self, *a):
        self.btn.disabled = True
        self.lbl_status.text = "选股中，请耐心等待..."
        threading.Thread(target=self._scan, daemon=True).start()

    def _log(self, m):
        Clock.schedule_once(lambda dt: setattr(self.lbl_status, "text", m))

    def _scan(self):
        try:
            selected, _, msg = StockSelector().run(progress_cb=self._log)
            result = YaoScorer().score(selected)
            Clock.schedule_once(lambda dt: self._render(result, msg))
        except Exception as e:
            Clock.schedule_once(lambda dt, err=str(e): setattr(
                self.lbl_status, "text", f"出错: {err[:120]}"))
        finally:
            Clock.schedule_once(lambda dt: setattr(self.btn, "disabled", False))

    def _render(self, df, msg):
        self._draw_header()
        if df.empty:
            self.lbl_status.text = f"无符合条件个股（{msg}）"
            return
        n = len(df)
        for _, r in df.head(TOP_N_SHOW).iterrows():
            hot = r["妖股概率"] >= 75
            c_hot = (1, .3, .3, 1) if hot else (1, 1, 1, 1)
            yzy_color = (1, .85, 0, 1) if r["top_yzy"] not in ("无", "未知") \
                        else (.5, .5, .5, 1)
            cells = [
                (f"{r['name']}\n{r['code']}",             c_hot),
                (str(r["lianban"]),                       c_hot),
                (f"{r['auction_pct']:.1f}",               c_hot),
                (f"{r['lhb_net_buy'] / 1e4:.0f}",         (1, 1, 1, 1)),
                (str(r["top_yzy"]),                       yzy_color),
                (f"{r['seal_type']}\n{r['behavior_note']}", (.7, .9, .7, 1)),
                (f"{r['妖股概率']}分\n[{r['评级']}]",      c_hot),
            ]
            for text, color in cells:
                self.grid.add_widget(Label(text=str(text), color=color,
                                           size_hint_y=None, height=56,
                                           font_size=10))
        self.lbl_status.text = f"完成：共 {n} 只，显示概率前 {min(n, TOP_N_SHOW)}"


if __name__ == "__main__":
    YaoStockApp().run()

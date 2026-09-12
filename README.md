# 妖股竞价选股器（yaostock）

根据 **当日龙虎榜资金流向 + 连板数据** 筛选妖股候选并输出"妖股概率"评分。
数据层为**纯 requests 直连东方财富公开接口**，无 akshare 依赖，PC 命令行版与 APK 版共用同一套代码。

## 六条件（硬性筛选）

1. 三个交易日内有过涨停（近三日涨停池）
2. 竞价阶段换手率 > 2%（9:25 集合竞价成交量 / 流通股本）
3. 9:25 竞价涨跌幅 > 5%
4. 集合竞价委卖量 > 委买量
5. 总市值 ≤ 300 亿
6. 龙虎榜资金介入（加分项，不硬性淘汰）

## 评分模型（0~100 妖股概率）

| 因子 | 权重 | 说明 |
|---|---|---|
| 连板高度 | 20% | 连板数越高情绪溢价越大 |
| 龙虎榜席位 | 15% | S/A/B/C 级游资识别 + 组合加成 |
| 竞价强度 | 15% | 涨幅 5~9% 最佳，过高临近涨停反而扣分 |
| 卖压特征 | 10% | 委卖/委买 1~3 倍为洗盘最佳，>5 倍为真出货 |
| 市值弹性 | 5% | 市值越小越好拉升 |
| 涨停新鲜度 | 5% | 最近涨停距今越近越好 |
| 行为因子 | 30% | 封单强度 + 撤单率估算 + 分时异动 |

## 接口字段验证（2026-09-11 实盘数据实测）

- 涨停池 `getTopicZTPool`：**hs 换手率已是百分比**（10.47 即 10.47%），勿再除以 1000
- 龙虎榜 `RPT_DAILYBILLBOARD_DETAILSNEW`：净买额单位元、可为负
- 席位明细卖出报表名为 **`RPT_BILLBOARD_DAILYDETAILSSELL`（双 S）**，单 S 报表不存在
- 实时快照五档字段：买一量 f20 / 买二量 f18 / 买三量 f16 / 买四量 f14 / 买五量 f12；卖一量 f32 / 卖二量 f34 / 卖三量 f36 / 卖四量 f38 / 卖五量 f40

## 使用

```bash
# ① PC 命令行版（交易日 9:25~9:30 运行）
pip install -r requirements.txt
python main_cli.py

# ② PC 图形版（需 kivy）
pip install kivy==2.3.0
python main.py
```

## 打包 APK

APK 必须用 Linux 环境交叉编译（python-for-android）。**本机 Windows 组件库已裁剪、无 WSL/Hyper-V 可选功能**，推荐用下面三种方式之一：

### ① 免费云端构建（GitHub Actions，推荐，无需本机装任何东西）

```bash
# 1) 在 GitHub 新建一个空仓库（Public/Private 均可）
# 2) 本机（需已装 git）执行：
git init && git add . && git commit -m "yaostock"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
# 3) 打开仓库 Actions 页面，手动触发 "Build APK" 工作流
#    （push 到 main 也会自动触发）
# 4) 约 30~60 分钟后，在 Actions 运行记录页下载 yao-stock-apk 产物
#    （bin/yaostock-1.0.0-arm64-v8a_debug.apk）
```

工作流文件已放在 `.github/workflows/build-apk.yml`，push 即可用，无需修改。

### ② 自己的 Linux 机器 / 云服务器

```bash
bash build_apk.sh      # 一键装依赖并打包，产物在 bin/
```

### ③ 本机 WSL2 / Docker（需完整版 Windows，可选功能齐全时）

```bash
# WSL2
wsl --install -d Ubuntu-22.04        # 装完重启
cp -r /mnt/c/.../yaostock/* ~/yaostock/
cd ~/yaostock && bash build_apk.sh

# 或 Windows 侧运行
.\build_apk.ps1
```

Docker 替代方案（装有 Docker Desktop 时）：

```bash
cd yaostock
docker run --rm -v $(pwd):/home/user/hostcwd -it --user 1000:1000 python:3.11 bash -c "
  apt update && apt install -y git zip unzip openjdk-17-jdk autoconf libtool \
  pkg-config zlib1g-dev libncurses-dev libssl-dev automake cmake libffi-dev liblzma-dev &&
  pip install buildozer==1.5.0 cython==0.29.36 &&
  cd /home/user/hostcwd && buildozer android debug"
```

## 已知限制

- 涨停池单页 400 条上限，极端行情（单日涨停 >400 只）会截断，属小概率事件
- 席位库需每季度人工更新（营业部会更换）
- 行为因子为分钟级免费数据近似，精确撤单率需 Level-2 数据源
- 概率分为经验模型，**不构成投资建议**

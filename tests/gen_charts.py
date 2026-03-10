"""
生成压测结果可视化图表，输出到 docs/diagrams/ 供 LaTeX 引用。
图表1: 各场景 TPS 对比柱状图
图表2: 各场景延迟分位数对比（分组柱状图）
图表3: 秒杀接口延迟时间序列（从 stats_history.csv）
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 从 .ttc 中提取简体中文字体 (face index 2 = Noto Sans CJK SC)
_SC_OTF = "/tmp/NotoSansCJK-SC-Regular.otf"
if not os.path.exists(_SC_OTF):
    from fontTools.ttLib import TTCollection
    tc = TTCollection("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    tc.fonts[2].save(_SC_OTF)

fm.fontManager.addfont(_SC_OTF)
_CJK_FONT_NAME = fm.FontProperties(fname=_SC_OTF).get_name()
plt.rcParams["font.family"] = _CJK_FONT_NAME
plt.rcParams["axes.unicode_minus"] = False

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "diagrams")
os.makedirs(OUT_DIR, exist_ok=True)

# ======================== 数据 ========================
scenarios = ["静态资源", "动态API", "秒杀接口"]
tps_vals = [458, 579, 597]
p50 = [220, 100, 87]
p95 = [430, 330, 280]
p99 = [590, 500, 2500]

colors_tps = ["#4A90D9", "#5CB85C", "#D9534F"]
colors_lat = ["#4A90D9", "#F0AD4E", "#D9534F"]

# ======================== 图1: TPS柱状图 ========================
fig, ax = plt.subplots(figsize=(7, 4.5))
bars = ax.bar(scenarios, tps_vals, color=colors_tps, width=0.5, edgecolor="white", linewidth=1.2)
for bar, val in zip(bars, tps_vals):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 12,
            str(val), ha="center", va="bottom", fontsize=13, fontweight="bold")
ax.set_ylabel("请求/秒 (TPS)", fontsize=12)
ax.set_title("各场景吞吐量对比（200~500并发, 30s）", fontsize=14, fontweight="bold")
ax.set_ylim(0, max(tps_vals) * 1.18)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "chart_tps.png"), dpi=200)
plt.close(fig)
print("✅ chart_tps.png")

# ======================== 图2: 延迟分位数分组柱状图 ========================
import numpy as np

x = np.arange(len(scenarios))
width = 0.22

fig, ax = plt.subplots(figsize=(8, 5))
b1 = ax.bar(x - width, p50, width, label="P50", color="#4A90D9", edgecolor="white")
b2 = ax.bar(x, p95, width, label="P95", color="#F0AD4E", edgecolor="white")
b3 = ax.bar(x + width, p99, width, label="P99", color="#D9534F", edgecolor="white")

for bars_group in [b1, b2, b3]:
    for bar in bars_group:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 30,
                f"{int(h)}", ha="center", va="bottom", fontsize=9)

ax.set_ylabel("延迟 (ms)", fontsize=12)
ax.set_title("各场景响应延迟分位数对比", fontsize=14, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(scenarios, fontsize=11)
ax.legend(fontsize=11)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "chart_latency.png"), dpi=200)
plt.close(fig)
print("✅ chart_latency.png")

# ======================== 图3: 秒杀接口时间序列 ========================
history_file = os.path.join(os.path.dirname(__file__), "..", "results", "seckill_stats_history.csv")
if os.path.exists(history_file):
    timestamps = []
    rps_list = []
    avg_list = []
    with open(history_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Name", "").strip() in ("Aggregated", "/api/inventory/seckill", ""):
                ts = float(row["Timestamp"])
                rps = float(row["Requests/s"])
                avg_str = row.get("Total Average Response Time", "0")
                avg = float(avg_str) if avg_str and avg_str != "N/A" else 0
                timestamps.append(ts)
                rps_list.append(rps)
                avg_list.append(avg)

    if timestamps:
        # 将时间戳转为相对秒
        t0 = timestamps[0]
        t_rel = [(t - t0) for t in timestamps]

        fig, ax1 = plt.subplots(figsize=(9, 4.5))
        color_rps = "#4A90D9"
        color_lat = "#D9534F"

        ax1.plot(t_rel, rps_list, color=color_rps, linewidth=1.8, label="TPS")
        ax1.set_xlabel("时间 (s)", fontsize=11)
        ax1.set_ylabel("TPS (请求/秒)", color=color_rps, fontsize=11)
        ax1.tick_params(axis="y", labelcolor=color_rps)

        ax2 = ax1.twinx()
        ax2.plot(t_rel, avg_list, color=color_lat, linewidth=1.8, linestyle="--", label="平均延迟")
        ax2.set_ylabel("平均延迟 (ms)", color=color_lat, fontsize=11)
        ax2.tick_params(axis="y", labelcolor=color_lat)

        ax1.set_title("秒杀接口 TPS 与延迟时间序列（500并发, 30s）", fontsize=13, fontweight="bold")
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=10)
        ax1.grid(alpha=0.3)
        ax1.spines["top"].set_visible(False)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, "chart_seckill_ts.png"), dpi=200)
        plt.close(fig)
        print("✅ chart_seckill_ts.png")
    else:
        print("⚠️ seckill_stats_history.csv 无有效数据行")
else:
    print("⚠️ seckill_stats_history.csv 不存在，跳过时间序列图")

print("\n所有图表已生成到", OUT_DIR)

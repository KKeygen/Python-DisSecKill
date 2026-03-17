"""Generate charts from k6 results into docs/diagrams/."""

import json
import os
from collections import defaultdict
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import matplotlib.font_manager as fm

    font_candidates = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "WenQuanYi Zen Hei",
    ]
    for name in font_candidates:
        try:
            fm.findfont(name, fallback_to_default=False)
            plt.rcParams["font.family"] = name
            break
        except Exception:
            continue
except Exception:
    pass

plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
OUT_DIR = os.path.join(BASE_DIR, "docs", "diagrams")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(OUT_DIR, exist_ok=True)


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


summary = load_json(os.path.join(RESULTS_DIR, "k6_summary.json"))

scenarios = ["静态资源", "动态API", "秒杀接口"]
tps_vals = [summary["static"]["tps"], summary["api"]["tps"], summary["seckill"]["tps"]]
p50 = [summary["static"]["p50"], summary["api"]["p50"], summary["seckill"]["p50"]]
p95 = [summary["static"]["p95"], summary["api"]["p95"], summary["seckill"]["p95"]]
p99 = [summary["static"]["p99"], summary["api"]["p99"], summary["seckill"]["p99"]]

colors_tps = ["#4A90D9", "#5CB85C", "#D9534F"]
colors_lat = ["#4A90D9", "#F0AD4E", "#D9534F"]

# ======================== 图1: TPS柱状图 ========================
fig, ax = plt.subplots(figsize=(7, 4.5))
bars = ax.bar(scenarios, tps_vals, color=colors_tps, width=0.5, edgecolor="white", linewidth=1.2)
for bar, val in zip(bars, tps_vals):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 12,
            str(val), ha="center", va="bottom", fontsize=13, fontweight="bold")
ax.set_ylabel("请求/秒 (TPS)", fontsize=12)
ax.set_title("各场景吞吐量对比", fontsize=14, fontweight="bold")
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
raw_file = os.path.join(RESULTS_DIR, "k6_seckill_raw.json")
if os.path.exists(raw_file):
    buckets = defaultdict(lambda: {"count": 0, "sum_dur": 0.0})
    with open(raw_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("type") != "Point":
                continue
            if item.get("metric") != "http_req_duration":
                continue
            data = item.get("data", {})
            t = data.get("time")
            v = data.get("value")
            if t is None or v is None:
                continue
            sec = int(datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp())
            buckets[sec]["count"] += 1
            buckets[sec]["sum_dur"] += float(v)

    if buckets:
        secs = sorted(buckets.keys())
        t0 = secs[0]
        t_rel = [s - t0 for s in secs]
        rps_list = [buckets[s]["count"] for s in secs]
        avg_list = [buckets[s]["sum_dur"] / max(1, buckets[s]["count"]) for s in secs]

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

        ax1.set_title("秒杀接口 TPS 与延迟时间序列", fontsize=13, fontweight="bold")
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
        print("⚠️ k6_seckill_raw.json 无有效点")
else:
    print("⚠️ k6_seckill_raw.json 不存在，跳过时间序列图")

print("\n所有图表已生成到", OUT_DIR)

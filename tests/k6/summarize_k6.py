import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"


def load_json(name: str):
    with (RESULTS / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def metric(summary: dict, key: str, field: str, default=0):
    return summary.get("metrics", {}).get(key, {}).get(field, default)


static = load_json("k6_static_summary.json")
api = load_json("k6_api_summary.json")
seckill = load_json("k6_seckill_summary.json")
lb = load_json("k6_lb_summary.json")
oversell = load_json("k6_oversell_summary.json")

lb_log = (RESULTS / "nginx_lb_access.log").read_text(encoding="utf-8", errors="ignore") if (RESULTS / "nginx_lb_access.log").exists() else ""

# upstream=172.22.0.12:8002
upstream_matches = re.findall(r"upstream=([^\s]+)", lb_log)
upstream_counts = {}
for u in upstream_matches:
    upstream_counts[u] = upstream_counts.get(u, 0) + 1

summary = {
    "static": {
        "requests": int(metric(static, "http_reqs", "count", 0)),
        "tps": round(metric(static, "http_reqs", "rate", 0), 2),
        "p50": round(metric(static, "http_req_duration", "med", 0), 2),
        "p95": round(metric(static, "http_req_duration", "p(95)", 0), 2),
        "p99": round(metric(static, "http_req_duration", "p(99)", metric(static, "http_req_duration", "max", 0)), 2),
        "fail_rate": round(metric(static, "http_req_failed", "value", 0) * 100, 2),
    },
    "api": {
        "requests": int(metric(api, "http_reqs", "count", 0)),
        "tps": round(metric(api, "http_reqs", "rate", 0), 2),
        "p50": round(metric(api, "http_req_duration", "med", 0), 2),
        "p95": round(metric(api, "http_req_duration", "p(95)", 0), 2),
        "p99": round(metric(api, "http_req_duration", "p(99)", metric(api, "http_req_duration", "max", 0)), 2),
        "fail_rate": round(metric(api, "http_req_failed", "value", 0) * 100, 2),
    },
    "seckill": {
        "requests": int(metric(seckill, "http_reqs", "count", 0)),
        "tps": round(metric(seckill, "http_reqs", "rate", 0), 2),
        "p50": round(metric(seckill, "http_req_duration", "med", 0), 2),
        "p95": round(metric(seckill, "http_req_duration", "p(95)", 0), 2),
        "p99": round(metric(seckill, "http_req_duration", "p(99)", metric(seckill, "http_req_duration", "max", 0)), 2),
        "fail_rate": round(metric(seckill, "http_req_failed", "value", 0) * 100, 2),
        "success": int(metric(seckill, "seckill_success_count", "count", 0)),
        "sold_out": int(metric(seckill, "seckill_sold_out_count", "count", 0)),
        "duplicate": int(metric(seckill, "seckill_duplicate_count", "count", 0)),
        "throttle": int(metric(seckill, "seckill_throttle_count", "count", 0)),
    },
    "oversell": {
        "requests": int(metric(oversell, "http_reqs", "count", 0)),
        "tps": round(metric(oversell, "http_reqs", "rate", 0), 2),
        "success": int(metric(oversell, "oversell_success_count", "count", 0)),
        "sold_out": int(metric(oversell, "oversell_sold_out_count", "count", 0)),
        "duplicate": int(metric(oversell, "oversell_duplicate_count", "count", 0)),
        "throttle": int(metric(oversell, "oversell_throttle_count", "count", 0)),
        "p50": round(metric(oversell, "http_req_duration", "med", 0), 2),
        "p95": round(metric(oversell, "http_req_duration", "p(95)", 0), 2),
    },
    "lb": {
        "requests": int(metric(lb, "http_reqs", "count", 0)),
        "tps": round(metric(lb, "http_reqs", "rate", 0), 2),
        "upstream_counts": upstream_counts,
    },
}

out = RESULTS / "k6_summary.json"
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote {out}")

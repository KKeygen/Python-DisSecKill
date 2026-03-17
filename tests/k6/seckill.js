import http from "k6/http";
import { check } from "k6";
import { Counter, Trend } from "k6/metrics";

const successCount = new Counter("seckill_success_count");
const soldOutCount = new Counter("seckill_sold_out_count");
const duplicateCount = new Counter("seckill_duplicate_count");
const throttleCount = new Counter("seckill_throttle_count");
const businessLatency = new Trend("seckill_business_latency", true);

const BASE_URL = __ENV.BASE_URL || "http://host.docker.internal";
const GOODS_ID = Number(__ENV.GOODS_ID || 1);
const STOCK = Number(__ENV.STOCK || 100);
const INIT = (__ENV.INIT_STOCK || "true").toLowerCase() === "true";
const PROFILE = (__ENV.PROFILE || "stress").toLowerCase();

const smokeScenario = {
  executor: "constant-arrival-rate",
  rate: 80,
  timeUnit: "1s",
  duration: "20s",
  preAllocatedVUs: 50,
  maxVUs: 200,
};

const stressScenario = {
  executor: "ramping-arrival-rate",
  startRate: 100,
  timeUnit: "1s",
  preAllocatedVUs: 200,
  maxVUs: 2000,
  stages: [
    { duration: "10s", target: 500 },
    { duration: "20s", target: 1200 },
    { duration: "20s", target: 1200 },
    { duration: "10s", target: 100 },
  ],
};

export const options = {
  scenarios: {
    spike: PROFILE === "smoke" ? smokeScenario : stressScenario,
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<1000"],
  },
};

export function setup() {
  if (!INIT) {
    return {};
  }

  const initResp = http.post(
    `${BASE_URL}/api/inventory/init/${GOODS_ID}`,
    JSON.stringify({ stock: STOCK }),
    { headers: { "Content-Type": "application/json" } }
  );

  check(initResp, {
    "init status is 200": (r) => r.status === 200,
  });

  return {};
}

export default function () {
  const userId = `${__VU}-${__ITER}-${Math.floor(Math.random() * 1000000)}`;
  const payload = JSON.stringify({ goods_id: GOODS_ID, user_id: Number(userId.replace(/-/g, "")) % 2147483647 });

  const resp = http.post(`${BASE_URL}/api/inventory/seckill`, payload, {
    headers: { "Content-Type": "application/json" },
    tags: { endpoint: "seckill" },
  });

  businessLatency.add(resp.timings.duration);

  if (resp.status === 200) {
    let body = {};
    try {
      body = resp.json();
    } catch (e) {
      body = {};
    }

    const msg = String(body.message || "");
    const ok = body.success === true;
    const soldOut = msg.includes("库存不足") || msg.includes("秒杀结束");
    const duplicate = msg.includes("重复") || msg.includes("已秒杀");

    if (ok) {
      successCount.add(1);
    } else if (soldOut) {
      soldOutCount.add(1);
    } else if (duplicate) {
      duplicateCount.add(1);
    }

    check(resp, {
      "status 200 business response": () => true,
    });
    return;
  }

  if (resp.status === 429 || resp.status === 503) {
    throttleCount.add(1);
    check(resp, {
      "throttled by gateway": () => true,
    });
    return;
  }

  check(resp, {
    "unexpected status": () => false,
  });
}

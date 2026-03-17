import http from "k6/http";
import { check } from "k6";
import { Counter } from "k6/metrics";

const successCount = new Counter("seckill_success_count");
const soldOutCount = new Counter("seckill_sold_out_count");
const duplicateCount = new Counter("seckill_duplicate_count");
const throttleCount = new Counter("seckill_throttle_count");

const BASE_URL = __ENV.BASE_URL || "http://host.docker.internal";
const GOODS_ID = Number(__ENV.GOODS_ID || 1);
const STOCK = Number(__ENV.STOCK || 50000);

export const options = {
  scenarios: {
    seckill_test: {
      executor: "constant-vus",
      vus: 500,
      duration: "30s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
  },
};

export function setup() {
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
  const userId = `${__VU}${__ITER}${Math.floor(Math.random() * 100000)}`;
  const payload = JSON.stringify({
    goods_id: GOODS_ID,
    user_id: Number(userId) % 2147483647,
  });

  const resp = http.post(`${BASE_URL}/api/inventory/seckill`, payload, {
    headers: { "Content-Type": "application/json" },
    tags: { scenario: "seckill" },
  });

  if (resp.status === 200) {
    let body = {};
    try {
      body = resp.json();
    } catch (e) {
      body = {};
    }

    const msg = String(body.message || "");
    if (body.success === true) {
      successCount.add(1);
    } else if (msg.includes("库存不足") || msg.includes("秒杀结束")) {
      soldOutCount.add(1);
    } else if (msg.includes("重复") || msg.includes("已秒杀")) {
      duplicateCount.add(1);
    }

    check(resp, { "business response": () => true });
    return;
  }

  if (resp.status === 429 || resp.status === 503) {
    throttleCount.add(1);
    check(resp, { "throttled": () => true });
    return;
  }

  check(resp, { "unexpected status": () => false });
}

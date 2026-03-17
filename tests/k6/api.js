import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://host.docker.internal";

export const options = {
  scenarios: {
    api_test: {
      executor: "constant-vus",
      vus: 200,
      duration: "30s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.6"],
  },
};

export default function () {
  const r = Math.random();
  let path = "/api/goods/?page=1&size=10";

  if (r < 0.6) {
    path = "/api/goods/?page=1&size=10";
  } else if (r < 0.9) {
    const goodsId = Math.floor(Math.random() * 5) + 1;
    path = `/api/goods/${goodsId}`;
  } else {
    path = "/health";
  }

  const resp = http.get(`${BASE_URL}${path}`, { tags: { scenario: "api" } });
  check(resp, {
    "api status<500": (v) => v.status < 500,
  });
}

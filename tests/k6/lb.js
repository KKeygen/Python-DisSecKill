import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://host.docker.internal";

export const options = {
  scenarios: {
    lb_test: {
      executor: "constant-vus",
      vus: 200,
      duration: "60s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.1"],
  },
};

export default function () {
  const r = Math.random();
  let path = "/api/goods/?page=1&size=5";

  if (r < 0.5) {
    path = "/api/goods/?page=1&size=5";
  } else if (r < 0.8) {
    path = "/api/user/profile";
  } else {
    path = "/api/inventory/1";
  }

  const resp = http.get(`${BASE_URL}${path}`, { tags: { scenario: "lb" } });
  check(resp, {
    "lb status<500": (v) => v.status < 500,
  });
}

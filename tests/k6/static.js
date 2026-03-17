import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://host.docker.internal";

export const options = {
  scenarios: {
    static_test: {
      executor: "constant-vus",
      vus: 200,
      duration: "30s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
  },
};

export default function () {
  const r = Math.random();
  let path = "/";
  if (r < 0.5) {
    path = "/";
  } else if (r < 0.8) {
    path = "/vite.svg";
  } else {
    path = "/assets/";
  }

  const resp = http.get(`${BASE_URL}${path}`, { tags: { scenario: "static" } });
  check(resp, {
    "static status<500": (v) => v.status < 500,
  });
}

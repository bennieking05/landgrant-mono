/**
 * k6 smoke: health endpoint (Phase 2).
 *
 *   k6 run scripts/k6/api-smoke.js -e BASE_URL=https://api.example.com
 */
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 3,
  duration: "30s",
  thresholds: {
    http_req_duration: ["p(95)<800"],
  },
};

export default function () {
  const base = __ENV.BASE_URL || "http://127.0.0.1:8050";
  const res = http.get(`${base}/health/live`);
  check(res, { "health 200": (r) => r.status === 200 });
  sleep(0.3);
}

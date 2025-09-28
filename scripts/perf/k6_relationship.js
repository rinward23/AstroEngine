import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  thresholds: {
    http_req_duration: ['p(50)<60', 'p(95)<150'],
  },
  scenarios: {
    synastry_hot: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '1m',
      preAllocatedVUs: 5,
      exec: 'synastry',
    },
    synastry_cold: {
      executor: 'per-vu-iterations',
      vus: 3,
      iterations: 1,
      exec: 'synastryCold',
      startTime: '1m10s',
    },
  },
};

const synPayload = JSON.stringify({
  pos_a: Object.fromEntries(Array.from({ length: 13 }, (_, i) => [
    `A${i + 1}`,
    ((i + 1) * 17) % 360,
  ])),
  pos_b: Object.fromEntries(Array.from({ length: 13 }, (_, i) => [
    `B${i + 1}`,
    ((i + 1) * 23 + 45) % 360,
  ])),
  aspects: [
    'conjunction',
    'opposition',
    'square',
    'trine',
    'sextile',
    'quincunx',
    'semisquare',
    'sesquisquare',
    'quintile',
    'biquintile',
  ],
});

export function synastry() {
  const res = http.post(`${__ENV.BASE_URL}/synastry/compute`, synPayload, {
    headers: { 'Content-Type': 'application/json' },
  });
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(0.5);
}

export function synastryCold() {
  const res = http.post(`${__ENV.BASE_URL}/synastry/compute`, synPayload, {
    headers: { 'Content-Type': 'application/json' },
  });
  check(res, { 'status is 200': (r) => r.status === 200 });
}

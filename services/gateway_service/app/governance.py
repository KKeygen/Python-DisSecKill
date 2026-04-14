import time
from dataclasses import dataclass


@dataclass
class TokenBucket:
    tokens: float
    capacity: float
    rate: float
    updated_at: float

    def allow(self, consume: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.updated_at = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens < consume:
            return False
        self.tokens -= consume
        return True


class RateLimiter:
    def __init__(self):
        self._buckets: dict[str, TokenBucket] = {}

    def allow(self, key: str, rate: float, burst: int) -> bool:
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(tokens=float(burst), capacity=float(burst), rate=rate, updated_at=time.monotonic())
            self._buckets[key] = bucket
        else:
            bucket.rate = rate
            bucket.capacity = float(burst)
            bucket.tokens = min(bucket.tokens, bucket.capacity)
        return bucket.allow()


@dataclass
class CircuitState:
    failures: int = 0
    opened_until: float = 0.0
    half_open: bool = False


class CircuitBreaker:
    def __init__(self):
        self._circuits: dict[str, CircuitState] = {}

    def allow(self, key: str) -> bool:
        state = self._circuits.get(key)
        if state is None:
            return True
        now = time.monotonic()
        if state.opened_until > now:
            return False
        if state.opened_until and state.opened_until <= now:
            state.half_open = True
            state.opened_until = 0.0
        return True

    def success(self, key: str):
        state = self._circuits.setdefault(key, CircuitState())
        state.failures = 0
        state.opened_until = 0.0
        state.half_open = False

    def failure(self, key: str, fail_threshold: int, open_seconds: int):
        state = self._circuits.setdefault(key, CircuitState())
        state.failures += 1
        if state.failures >= fail_threshold or state.half_open:
            state.opened_until = time.monotonic() + open_seconds
            state.failures = 0
            state.half_open = False

import time


class TokenBucket:
    """
    Refactored by: Mustakim.shaikh@placementshiksha.com

    Implements the Token Bucket algorithm for rate limiting.
    Note: Operations on a single key are not thread-safe in this implementation.

    Logic Flow:
    - Maintains a bucket of tokens for a given key.
    - `capacity`: Maximum number of tokens the bucket can hold.
    - `fill_rate`: Rate at which tokens are added to the bucket (tokens per second).
    - `default_capacity`: Initial number of tokens.
    - `consume`: Attempts to remove tokens from the bucket. Refills based on time elapsed since last check.
    """
    def __init__(self, key, capacity, fill_rate, default_capacity, redis_conn):
        """
        :param capacity: Max capacity
        :param fill_rate: Fill rate / second
        :param default_capacity: Initial capacity
        :param redis_conn: redis connection
        """
        self._key = key
        self._capacity = capacity
        self._fill_rate = fill_rate
        self._default_capacity = default_capacity
        self._redis_conn = redis_conn

        self._last_capacity_key = "last_capacity"
        self._last_timestamp_key = "last_timestamp"

    def _init_key(self):
        self._last_capacity = self._default_capacity
        now = time.time()
        self._last_timestamp = now
        return self._default_capacity, now

    @property
    def _last_capacity(self):
        last_capacity = self._redis_conn.hget(self._key, self._last_capacity_key)
        if last_capacity is None:
            return self._init_key()[0]
        else:
            return float(last_capacity)

    @_last_capacity.setter
    def _last_capacity(self, value):
        self._redis_conn.hset(self._key, self._last_capacity_key, value)

    @property
    def _last_timestamp(self):
        return float(self._redis_conn.hget(self._key, self._last_timestamp_key))

    @_last_timestamp.setter
    def _last_timestamp(self, value):
        self._redis_conn.hset(self._key, self._last_timestamp_key, value)

    def _try_to_fill(self, now):
        delta = self._fill_rate * (now - self._last_timestamp)
        return min(self._last_capacity + delta, self._capacity)

    def consume(self, num=1):
        """
        Consumes `num` tokens, returns whether successful.
        :param num: Number of tokens to consume
        :return: result: bool, wait_time: float (time to wait if failed)
        """
        # print("capacity ", self.fill(time.time()))
        if self._last_capacity >= num:
            self._last_capacity -= num
            return True, 0
        else:
            now = time.time()
            cur_num = self._try_to_fill(now)
            if cur_num >= num:
                self._last_capacity = cur_num - num
                self._last_timestamp = now
                return True, 0
            else:
                return False, (num - cur_num) / self._fill_rate

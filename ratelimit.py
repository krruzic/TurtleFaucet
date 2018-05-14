from redis import Redis
redis = Redis()

import time
import json
from functools import update_wrapper
from flask import request, g

class RateLimit(object):
    expiration_window = 10

    def __init__(self, ip_prefix, fp_prefix, limit, per, send_x_headers):
        self.reset = (int(time.time()) // per) * per + per

        self.ipkey = ip_prefix + str(self.reset)
        self.fpkey = fp_prefix + str(self.reset)

        self.limit = limit
        self.per = per
        self.send_x_headers = send_x_headers
        p = redis.pipeline()

        p.incr(self.ipkey)
        p.expireat(self.ipkey, self.reset + self.expiration_window)

        p.incr(self.fpkey)
        p.expireat(self.fpkey, self.reset + self.expiration_window)
        results = p.execute()
        self.ip_current = min(results[0], limit)
        self.fp_current = min(results[1], limit)

    remaining_ip = property(lambda x: x.limit - x.ip_current)
    over_ip_limit = property(lambda x: x.ip_current >= x.limit)
    remaining_fp = property(lambda x: x.limit - x.fp_current)
    over_fp_limit = property(lambda x: x.fp_current >= x.limit)

def get_view_rate_limit():
    return getattr(g, '_view_rate_limit', None)

def on_over_limit(limit):
    return json.dumps({'status':'Fail',
        'reason':'You can only use the faucet 3 times a day'}),429

def ratelimit(limit, per=300, send_x_headers=True,
              over_limit=on_over_limit,
              fp_func=lambda: request.form.get('fingerprint'),
              ip_func=lambda: request.environ['REMOTE_ADDR'],
              key_func=lambda: request.endpoint):
    def decorator(f):
        def rate_limited(*args, **kwargs):
            ip_key = 'ip-limit/%s/%s/' % (key_func(), ip_func())
            fp_key = 'fp-limit/%s/%s/' % (key_func(), fp_func())
            rlimit = RateLimit(ip_key, fp_key, limit, per, send_x_headers)
            g._view_rate_limit = rlimit

            # check if IP has been used LIMIT times
            if rlimit.over_ip_limit:
                return over_limit(rlimit)

            # IP is good, check fingerprint now
            if not rlimit.over_ip_limit:
                if rlimit.over_fp_limit:
                    return over_limit(rlimit)

            return f(*args, **kwargs)
        return update_wrapper(rate_limited, f)
    return decorator

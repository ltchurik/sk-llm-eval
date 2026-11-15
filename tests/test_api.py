import io
import json
import unittest
import urllib.error
from email.message import Message
from unittest import mock

from sk_llm_eval import api


def _http_error(code, headers=None):
    msg = Message()
    for k, v in (headers or {}).items():
        msg[k] = v
    return urllib.error.HTTPError("http://x", code, "err", msg, io.BytesIO(b"{}"))


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _ok(text):
    return _Resp(json.dumps({"choices": [{"message": {"content": text}}]}).encode())


class TestRetries(unittest.TestCase):
    def test_rate_limit_waits_and_does_not_use_up_retries(self):
        side = [_http_error(429, {"Retry-After": "3"})] * 5 + [_ok("áno")]
        with mock.patch("urllib.request.urlopen", side_effect=side), \
                mock.patch("time.sleep") as sleep:
            out = api.chat("p", model="m", base_url="http://x", retries=3)
        self.assertEqual(out, "áno")
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [3.0] * 5)

    def test_client_error_is_not_retried(self):
        with mock.patch("urllib.request.urlopen", side_effect=[_http_error(400)]) as urlopen, \
                mock.patch("time.sleep"):
            with self.assertRaises(api.ApiError):
                api.chat("p", model="m", base_url="http://x")
        self.assertEqual(urlopen.call_count, 1)


if __name__ == "__main__":
    unittest.main()

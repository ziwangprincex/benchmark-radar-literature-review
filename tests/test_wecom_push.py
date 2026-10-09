import unittest
from unittest import mock

from radar.publish import wecom_push


class WecomPushTest(unittest.TestCase):
    def test_message_fits_wecom_limit(self):
        text = wecom_push.build_message()
        self.assertLessEqual(len(text.encode("utf-8")), wecom_push.MAX_BYTES)
        self.assertIn("待读提醒", text)
        self.assertNotIn("撞车", text)

    def test_no_webhook_does_not_send(self):
        with mock.patch.object(wecom_push, "load_config", return_value={}), \
             mock.patch.object(wecom_push, "send") as send, \
             mock.patch.object(wecom_push, "LOG_PATH", wecom_push.ROOT / "outputs" / "_test_push_log.jsonl"):
            r = wecom_push.push()
        send.assert_not_called()
        self.assertFalse(r["ok"])
        (wecom_push.ROOT / "outputs" / "_test_push_log.jsonl").unlink(missing_ok=True)

    def test_rejects_non_wecom_url(self):
        with self.assertRaises(ValueError):
            wecom_push.save_webhook("https://example.com/hook")


if __name__ == "__main__":
    unittest.main()

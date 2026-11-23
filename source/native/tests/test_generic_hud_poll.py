"""Keep the generic BoostDeck HUD supply on its existing loopback HSFZ link."""
from contextlib import ExitStack
import os
import socket
import struct
import time
import unittest

import test_drive_apps
from test_transport import VALUES


def mono_ms():
    # Match the collector's CLOCK_MONOTONIC origin on macOS as well as Linux.
    return time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1_000_000


class GenericHudPollTest(unittest.TestCase):
    def run_default_gauges(self, rpm_responses=None, hud_listener=True):
        dids = (0x4201, 0x4205, 0x5889, 0x4A49, 0x580F, 0xDA12,
                0x56D7, 0x586F, 0x4300)
        transactions = [(f"22{did:04x}", [f"62{did:04x}" + VALUES[did].hex()])
                        for did in dids]
        targets = ["18" if did == 0xDA12 else "12" for did in dids]
        if rpm_responses is not None:
            transactions.append(("010c", rpm_responses))
            targets.append("12")
        env = dict(os.environ)
        for key in ("ID6_FAKE_MOST", "ID6_FAKE_AAD_INSTALLED", "ID6_FAKE_AAD_SHOWN",
                    "ID6_FAKE_CARPLAY_HUD"):
            env.pop(key, None)
        with ExitStack() as stack:
            display = stack.enter_context(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
            display.bind(("127.0.0.1", 0))
            if hud_listener:
                hud = stack.enter_context(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
                hud.bind(("127.0.0.1", 42970))
                hud.settimeout(2)
            # The helper accepts one TCP connection and checks every command on it.
            # 511 is the default nine gauges; it deliberately omits BD_RPM (bit 11).
            test_drive_apps.DriveAppsTest.run_worker(
                self, "boost-deck", ["--cycles", "1", "--session", "--signals", "511",
                                     "--transport", "hsfz", "--udp-port",
                                     str(display.getsockname()[1])],
                transactions, targets=targets, env=env)
            if not hud_listener:
                return None
            data, peer = hud.recvfrom(64)
            received = mono_ms()
        self.assertEqual(peer, ("127.0.0.1", 42971))
        self.assertEqual(len(data), 40)
        sample = struct.unpack("=QQQIIIi", data)
        self.assertEqual(sample[0], 0x31504D534455484E)
        self.assertEqual(sample[3], 42971)
        self.assertEqual(sample[4] & 4, 0, "Generic data must not claim the N57 profile")
        return sample, received

    def test_default_gauges_share_delayed_rpm_using_request_timestamp(self):
        request_times = []

        def delayed_rpm():
            request_times.append(mono_ms())
            time.sleep(.08)
            yield "410c0c80"

        sample, received = self.run_default_gauges(delayed_rpm())
        self.assertEqual(sample[4] & 1, 1)
        self.assertEqual(sample[5], 800)
        self.assertGreater(sample[1], 0)
        self.assertLessEqual(sample[1], request_times[0])
        self.assertGreaterEqual(received - sample[1], 65)
        self.assertLessEqual(sample[1], received)

    def test_no_hud_listener_adds_no_rpm_query(self):
        self.run_default_gauges(hud_listener=False)

    def test_extra_rpm_payload_is_not_published_as_valid(self):
        sample, _ = self.run_default_gauges(["410c0c80aa"])
        self.assertEqual(sample[4] & 1, 0)
        self.assertEqual((sample[1], sample[5]), (0, 0))


if __name__ == "__main__":
    unittest.main()

"""N57 ShiftDeck/LaunchDeck on loopback HSFZ, plus the lower shift threshold bindings."""
import ast
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

import test_drive_apps
import test_n57

NATIVE = Path(__file__).resolve().parents[1]
BUILD = NATIVE / "build"
sys.path.insert(0, str(NATIVE / "tools"))
import extend_shift_n57


class DriveN57Test(unittest.TestCase):
    def sample(self, speed_only=False, index="010203", rpm="0640", speed="0001", worker="shift-deck"):
        transactions = [("22f150", ["62f150" + index])]
        if index == "010203":
            if not speed_only:
                transactions += test_n57.dyn("5955", rpm)
            if speed_only or rpm not in ("ffff", ""):
                transactions += test_n57.dyn("4c14", speed)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.bind(("127.0.0.1", 0)); udp.settimeout(3)
            start = time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1000000
            args = ["--cycles", "1", "--n57-sgbd", "010203", "--udp-port", str(udp.getsockname()[1])]
            if speed_only:
                args += ["--speed-only"]
            test_drive_apps.DriveAppsTest.run_worker(self, worker, args, transactions)
            packet = udp.recv(128)
            self.assertEqual(len(packet), 24)
            magic, sampled, rpm_value, mkph = struct.unpack("=QQii", packet)
            self.assertLessEqual(start, sampled)
            self.assertLessEqual(sampled, time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1000000)
            self.assertEqual(magic, 0xFFFFFFFF31454444)
        return rpm_value, mkph

    def test_shift_uses_dde_with_fractional_speed_in_both_builds(self):
        for worker in ("shift-deck", "shift-deck-fast"):
            with self.subTest(worker=worker):
                self.assertEqual(self.sample(worker=worker), (800, 5))

    def test_launch_speed_only_never_queries_rpm_or_mode01(self):
        self.assertEqual(self.sample(speed_only=True, speed="2710"), (-1, 45780))

    def test_wrong_identity_and_invalid_rpm_cannot_produce_live_data(self):
        for changes in ({"index": "040506"}, {"rpm": "ffff"}, {"rpm": ""}):
            with self.subTest(changes=changes):
                self.assertEqual(self.sample(**changes), (-1, -1))

    def test_missing_speed_preserves_unavailable_state(self):
        self.assertEqual(self.sample(speed=""), (800, -1))

    def test_most_is_not_a_fallback_for_dynamic_dde_reads(self):
        result = subprocess.run([BUILD / "shift-deck", "--host", "127.0.0.1", "--n57-sgbd", "010203",
                                 "--transport", "most", "--cycles", "1"], capture_output=True, timeout=2)
        self.assertEqual(result.returncode, 2)

    def test_shift_layout_and_header_keep_old_ids_and_lower_thresholds(self):
        path = NATIVE / "plugin/ShiftDeck.xml"
        original = path.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / path.name
            generated.write_bytes(original)
            extend_shift_n57.update_xml(generated)
            self.assertEqual(generated.read_bytes(), original)
        app = ET.fromstring(original).find("pluginApp")
        actions = [x.get("id") for x in app.find("actions")]
        self.assertEqual(len(actions), len(set(actions)))
        choices = app.find("hmiStates/hmiState[@id='101']/components")
        for action, caption in (("41", "5,800 RPM"), ("45", "6,700 RPM"), ("48", "3,500 RPM"),
                                ("49", "4,000 RPM"), ("50", "4,500 RPM")):
            self.assertEqual(choices.find(f"button[@action='{action}']").get("text"), caption)
        source = (NATIVE / "tools/shift_art.py").read_text()
        targets = ast.literal_eval(re.search(r"^TARGETS = (.+)$", source, re.M)[1])
        header = (NATIVE / "src/shift_assets.h").read_text()
        self.assertIn("{" + ", ".join(map(str, targets)) + "}", header)
        self.assertIn("kDefaultN57Target = 6u", header)


if __name__ == "__main__":
    unittest.main()

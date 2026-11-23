"""N57 image-axis regression and lossless extension of shipped ShiftDeck artwork."""
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from PIL import Image

NATIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE.parent / "tools"))
import extend_shift_n57
import shift_art as art


class ShiftScaleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = dict(art.n57_bitmaps())

    def test_fresh_shift_generator_converts_the_entire_legacy_grid(self):
        import make_drive_apps
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "manifests"
            plugin.mkdir()
            (plugin / "BoostDeck.manifest").write_bytes((NATIVE / "manifests/BoostDeck.manifest").read_bytes())
            # This regression exercises XML generation; artwork has its own pixel tests.
            with mock.patch.object(make_drive_apps, "ROOT", plugin), mock.patch.object(art, "save_assets"):
                make_drive_apps.shift_app()
            path = plugin / "ShiftDeck.xml"
            page = ET.parse(path).find("pluginApp/hmiStates/hmiState[@id='100']/components")
            for identifier in (200, 201, 212, 213, 214):
                node = page.find(f"image[@id='{identifier}']")
                self.assertEqual(node.find("properties/property[@id='20']").get("value"), "0")
                self.assertEqual(node.find("properties/property[@id='9']").get("value"), str(art.BAR_WIDTH))
            target = page.find("image[@id='202']")
            props = {p.get("id"): int(p.get("value")) for p in target.findall("properties/property")
                     if p.get("id") in ("20", "9")}
            self.assertEqual(props["20"] + props["9"], art.BAR_WIDTH)
            before = path.read_bytes()
            extend_shift_n57.update_xml(path)
            self.assertEqual(path.read_bytes(), before)

    def test_axis_uses_factory_six_thousand_and_clamps(self):
        self.assertEqual(art.N57_MAX_RPM, 6000)
        self.assertEqual(art.n57_axis_x(-1), art.N57_AXIS_LEFT)
        self.assertEqual(art.n57_axis_x(0), art.N57_AXIS_LEFT)
        self.assertEqual(art.n57_axis_x(6000), art.N57_AXIS_RIGHT)
        self.assertEqual(art.n57_axis_x(100000), art.N57_AXIS_RIGHT)
        self.assertAlmostEqual(art.n57_axis_x(3000),
                               (art.N57_AXIS_LEFT + art.N57_AXIS_RIGHT) / 2, delta=.5)

    def test_scale_ticks_and_targets_share_the_bar_axis(self):
        scale = self.assets[art.N57_SCALE]
        self.assertEqual(scale.size, (art.BAR_WIDTH, 49))
        # Endpoint labels need clear ink margins even though the ticks reach the bar ends.
        self.assertIsNone(scale.crop((0, 18, art.N57_LABEL_INSET, 49)).getbbox())
        self.assertIsNone(scale.crop((art.BAR_WIDTH-art.N57_LABEL_INSET+1, 18, art.BAR_WIDTH, 49)).getbbox())
        for rpm in range(0, 6001, 500):
            self.assertNotEqual(scale.getpixel((art.n57_axis_x(rpm), 5))[3], 0)
        for index in (5, 6, 7):
            rpm = art.TARGETS[index]
            marker = self.assets[art.N57_MARK_BASE + index]
            x0, _, x1, _ = marker.getbbox()
            self.assertEqual((x0 + x1 - 1) / 2, art.n57_axis_x(rpm))
            # Both bar builds quantise on this axis, within half a step.
            for resolution in (32, 128):
                step = (rpm * resolution + 3000) // 6000
                bar_end = art.N57_AXIS_LEFT + (art.N57_AXIS_RIGHT - art.N57_AXIS_LEFT) * step / resolution
                half_step = (art.N57_AXIS_RIGHT - art.N57_AXIS_LEFT) / resolution / 2
                self.assertLessEqual(abs(bar_end - art.n57_axis_x(rpm)), half_step + .5)
        # Red decoration follows the owner's reference photo, not the selected shift threshold.
        red = tuple(int(art.RED[i:i+2], 16) for i in (1, 3, 5))
        self.assertNotEqual(scale.getpixel((art.n57_axis_x(5000), 5))[:3], red)
        self.assertEqual(scale.getpixel((art.n57_axis_x(5500), 5))[:3], red)

    def test_shipped_gasoline_and_smooth_assets_are_preserved(self):
        with ZipFile(NATIVE.parents[1] / "packages/dashboard.zip") as package:
            original_data = package.read("ShiftDeck/ShiftDeck_ALL_Images.zip")
        with tempfile.TemporaryDirectory() as directory:
            source, target, second, repeat = (Path(directory) / n for n in ("source.zip", "new.zip", "again.zip", "repeat.zip"))
            source.write_bytes(original_data)
            extend_shift_n57.update_images(source, target)
            extend_shift_n57.update_images(target, second)
            extend_shift_n57.update_images(source, repeat)
            self.assertEqual(target.read_bytes(), repeat.read_bytes())
            self.assertEqual(target.read_bytes(), second.read_bytes())
            with ZipFile(source) as old, ZipFile(target) as new, ZipFile(second) as again:
                self.assertEqual(len(new.namelist()), len(set(new.namelist())))
                self.assertEqual(set(new.namelist()), set(again.namelist()))
                for name in old.namelist():
                    self.assertEqual(new.read(name), old.read(name), name)
                    for field in ("date_time", "compress_type", "external_attr", "comment", "extra"):
                        self.assertEqual(getattr(new.getinfo(name),field),getattr(old.getinfo(name),field),(name,field))
                for name in new.namelist():
                    self.assertEqual(new.read(name), again.read(name), name)
                for index in range(8):
                    self.assertIn(f"{art.N57_MARK_BASE + index}.png", new.namelist())
                self.assertIn(f"{art.N57_SCALE}.png", new.namelist())
                # Both N57 resolutions sample the same profile-specific colours.
                for step in range(33):
                    self.assertEqual(new.read(f"{art.N57_BAR_BASE + step}.png"),
                                     new.read(f"{art.N57_SWEEP_NORMAL + step*4}.png"))
                    old_warning = Image.open(BytesIO(old.read(f"{56529 + step*4}.png"))).convert("RGBA")
                    resized_warning = old_warning.resize((art.BAR_WIDTH, old_warning.height), Image.Resampling.LANCZOS)
                    self.assertEqual(Image.open(BytesIO(new.read(f"{art.N57_BAR_WARN + step}.png"))).tobytes(), resized_warning.tobytes())
                    self.assertEqual(new.read(f"{art.N57_BAR_WARNING + step}.png"),
                                     new.read(f"{art.N57_SWEEP_WARNING + step*4}.png"))
                for step in (0, 1, 64, 96, 128):
                    normal = Image.open(BytesIO(old.read(f"{56400 + step}.png"))).convert("RGBA")
                    warning = Image.open(BytesIO(new.read(f"{art.N57_SWEEP_WARNING + step}.png"))).convert("RGBA")
                    self.assertEqual(warning.size, (art.BAR_WIDTH, normal.height))
                    expected = bytearray(normal.tobytes())
                    for offset in range(0, len(expected), 4):
                        if expected[offset:offset + 3] in (b"\x40\x9a\xf6", b"\xff\xbf\x52"):
                            expected[offset:offset + 3] = b"\xff\xc3\x4d"
                    self.assertEqual(warning.tobytes(), Image.frombytes("RGBA", normal.size, bytes(expected)).resize((art.BAR_WIDTH, normal.height), Image.Resampling.LANCZOS).tobytes())
                normal = Image.open(BytesIO(old.read("55879.png"))).convert("RGBA")
                warning = Image.open(BytesIO(new.read(f"{art.N57_LIGHTS_WARNING}.png"))).convert("RGBA")
                self.assertEqual((art.BAR_WIDTH, normal.height), warning.size)
                self.assertEqual(normal.resize(warning.size, Image.Resampling.LANCZOS).getchannel("A").tobytes(), warning.getchannel("A").tobytes())
                scale = Image.open(BytesIO(new.read(f"{art.N57_SCALE}.png")))
                self.assertEqual(scale.size, (art.BAR_WIDTH, 49))

    def test_generated_header_has_the_new_profile_resource_ids(self):
        header = (NATIVE / "src/plugins/shift_assets.h").read_text()
        self.assertEqual(header, art.constants_text())
        for name, number in (("kScale", art.SCALE), ("kN57Scale", art.N57_SCALE),
                             ("kN57MarkBase", art.N57_MARK_BASE),
                             ("kN57BarBase", art.N57_BAR_BASE), ("kN57BarWarn", art.N57_BAR_WARN)):
            self.assertIn(f"{name} = {number}u", header)
        for name, number in (("kN57SweepNormal", 59400), ("kN57SweepWarning", 59000), ("kN57BarWarning", 59129),
                             ("kN57DigitWarning", 59162), ("kN57LightsWarning", 59174),
                             ("kN57ShiftWarning", 59175), ("kN57LowerMarker", 59300),
                             ("kN57UpperMarker", 59301), ("kN57WindowLegend", 59302)):
            self.assertIn(f"{name} = {number}u", header)

    def test_private_normal_bank_removes_early_gasoline_amber_only_for_n57(self):
        with ZipFile(NATIVE.parents[1] / "packages/dashboard.zip") as package:
            original = package.read("ShiftDeck/ShiftDeck_ALL_Images.zip")
        with ZipFile(BytesIO(original)) as stock, ZipFile(NATIVE / "manifests/ShiftDeck_ALL_Images.zip") as actual:
            active = {b"\x40\x9a\xf6", b"\xff\xbf\x52"}
            for step in range(129):
                name = f"{56400 + step}.png"
                self.assertEqual(actual.read(name), stock.read(name), name)
                source = Image.open(BytesIO(stock.read(name))).convert("RGBA")
                normal = Image.open(BytesIO(actual.read(f"{59400 + step}.png"))).convert("RGBA")
                self.assertEqual(normal.size, (art.BAR_WIDTH, source.height))
                expected = bytearray(source.tobytes())
                for offset in range(0, len(expected), 4):
                    if bytes(expected[offset:offset + 3]) in active:
                        expected[offset:offset + 3] = b"\x40\x9a\xf6"
                self.assertEqual(normal.tobytes(), Image.frombytes("RGBA", source.size, bytes(expected)).resize(normal.size, Image.Resampling.LANCZOS).tobytes(), step)
                self.assertNotIn((255, 191, 82, 255), [rgba for _, rgba in normal.getcolors(1 << 20)])
            # 4500 RPM previously selected the gasoline amber tail before4600.
            normal = Image.open(BytesIO(actual.read("59496.png"))).convert("RGBA")
            self.assertEqual(normal.getpixel((750, 30)), (64, 154, 246, 255))

    def test_local_image_archive_matches_the_packaging_generator(self):
        with ZipFile(NATIVE.parents[1] / "packages/dashboard.zip") as package:
            original = package.read("ShiftDeck/ShiftDeck_ALL_Images.zip")
        with tempfile.TemporaryDirectory() as directory:
            source, output = (Path(directory) / name for name in ("source.zip", "expected.zip"))
            source.write_bytes(original)
            extend_shift_n57.update_images(source, output)
            with ZipFile(output) as expected, ZipFile(NATIVE / "manifests/ShiftDeck_ALL_Images.zip") as actual:
                self.assertEqual(set(expected.namelist()), set(actual.namelist()))
                for name in expected.namelist():
                    self.assertEqual(actual.read(name), expected.read(name), name)
    def test_window_marker_ink_is_thin_with_rhmi_safe_padding(self):
        for identifier, color in ((art.N57_LOWER_MARKER, (255, 195, 77)),
                                  (art.N57_UPPER_MARKER, (255, 69, 72))):
            marker = self.assets[identifier]
            self.assertEqual(marker.size, (64, 9))
            self.assertEqual(marker.getpixel((3, 4)), (*color, 255))
            self.assertIsNone(marker.getchannel("A").crop((7, 0, 64, 9)).getbbox())
            x0, _, x1, _ = marker.getbbox()
            self.assertEqual((x0 + x1 - 1) / 2, 3)
            for rpm in range(1000, 5501, 100):
                native_x = art.N57_AXIS_LEFT + ((art.N57_AXIS_RIGHT - art.N57_AXIS_LEFT) * rpm + 3000) // 6000 - 3
                self.assertGreaterEqual(native_x, 0)
                self.assertLessEqual(native_x + marker.width, art.BAR_WIDTH)
                self.assertAlmostEqual(native_x + 3, art.n57_axis_x(rpm), delta=1)

    def test_window_page_is_idempotent_and_preserves_gas_controls(self):
        source = NATIVE / "manifests/ShiftDeck.xml"
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "ShiftDeck.xml"
            candidate.write_bytes(source.read_bytes())
            extend_shift_n57.update_xml(candidate)
            self.assertEqual(candidate.read_bytes(), source.read_bytes())
            extend_shift_n57.update_xml(candidate)
            self.assertEqual(candidate.read_bytes(), source.read_bytes())
        app = ET.parse(source).find("pluginApp")
        ids = [node.get("id") for node in app.iter() if node.tag != "property" and node.get("id")]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(app.find("actions/hmiAction[@id='120']").get("target"), "102")
        for action in range(121, 126):
            self.assertIsNotNone(app.find(f"actions/raAction[@id='{action}']"))
        choices = app.find("hmiStates/hmiState[@id='101']/components")
        self.assertEqual([node.get("action") for node in choices.findall("button")],
                         ["41", "42", "43", "44", "45", "48", "49", "50"])
        settings = app.find("hmiStates/hmiState[@id='102']/components")
        self.assertEqual([node.get("action") for node in settings.findall("button")],
                         ["121", "122", "123", "124", "125"])
        self.assertEqual(settings.find("label").get("model"), "83")
        option = app.find("hmiStates/hmiState[@id='100']/optionComponents/button[@id='412']")
        self.assertEqual(option.get("action"), "120")
        self.assertEqual(option.find("properties/property[@id='3']").get("value"), "false")
        components = app.find("hmiStates/hmiState[@id='100']/components")
        for component in components:
            props = {int(item.get("id")): item.get("value") for item in component.findall("properties/property")}
            if {20, 21, 9, 10}.issubset(props):
                x, y, width, height = [int(props[key]) for key in (20, 21, 9, 10)]
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(x + width, art.BAR_WIDTH)
                self.assertLessEqual(y + height, 420)
        for component, rpm in ((250, 4600), (251, 4800)):
            image = components.find(f"image[@id='{component}']")
            props = {int(item.get("id")): item.get("value") for item in image.findall("properties/property")}
            self.assertEqual(int(props[20]) + 3, art.n57_axis_x(rpm))
            self.assertEqual((int(props[9]), int(props[10])), (64, 9))
            self.assertEqual(props[3], "false")
        for identifier in (252, 253):
            node = components.find(f"*[@id='{identifier}']")
            self.assertEqual(node.find("properties/property[@id='3']").get("value"), "false")


if __name__ == "__main__":
    unittest.main()

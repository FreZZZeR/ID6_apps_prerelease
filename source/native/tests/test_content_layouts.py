"""Regression checks for bounds/clipped columns observed on the N57 head unit."""
from io import BytesIO
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

NATIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE.parent / "tools"))
import launch_art
import make_boostdeck_extended as boost
import make_engine_codes_layout as codes
from content_layout import WIDTH, HEIGHT, PANEL_WIDTH, PANEL_PIXELS, LEFT, RIGHT, update_xdrive, update_hud


def rect(node):
    values = {int(p.get("id")): int(p.get("value")) for p in node.findall("properties/property")
              if p.get("id") in ("20", "21", "9", "10")}
    return tuple(values[key] for key in (20, 21, 9, 10))


class ContentLayoutTest(unittest.TestCase):
    def assert_in_viewport(self, rectangle):
        x, y, width, height = rectangle
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)
        self.assertLessEqual(x+width, WIDTH)
        self.assertLessEqual(y+height, HEIGHT)

    def test_all_dashboard_components_fit_content_instead_of_panel_coordinates(self):
        for app, state in (("BoostDeck", 100), ("ShiftDeck", 100), ("LaunchDeck", 100),
                           ("EngineCodes", 101), ("PowerDeck", 100), ("PowerDeck", 110),
                           ("PowerDeck", 111), ("HudTest", 100),
                           ("XDriveControl", 100), ("XDriveControl", 101), ("XDriveControl", 102)):
            page = ET.parse(NATIVE / f"manifests/{app}.xml").find(
                f"pluginApp/hmiStates/hmiState[@id='{state}']/components")
            for node in page:
                with self.subTest(app=app, component=node.get("id")):
                    self.assert_in_viewport(rect(node))

    def test_main_content_leaves_a_small_gutter_in_panel_pixels(self):
        # Exact 006 scales the 1440-design-unit FBO to 1280px. The common
        # gutter is 24 design units (~21px), rather than the old 139px gap.
        self.assertEqual((PANEL_WIDTH, PANEL_PIXELS, LEFT, RIGHT, WIDTH),
                         (1440, 1280, 180, 24, 1236))
        self.assertAlmostEqual((PANEL_WIDTH-LEFT-WIDTH)*PANEL_PIXELS/PANEL_WIDTH, 64/3)
        native = Path(os.environ.get("ID6_LAYOUT_TEST_NATIVE", NATIVE))
        edges = {"BoostDeck": (100, "label", 266, 32),
                 "ShiftDeck": (100, "image", 200, 0),
                 "LaunchDeck": (100, "image", 202, 60),
                 "EngineCodes": (101, "label", 320, 20),
                 "PowerDeck": (100, "image", 212, 24),
                 "HudTest": (100, "label", 150, 20)}
        for app, (state, tag, component, margin) in edges.items():
            with self.subTest(app=app):
                path = native / f"manifests/{app}.xml"
                root = ET.parse(path).getroot()
                node = root.find(f"pluginApp/hmiStates/hmiState[@id='{state}']/components/{tag}[@id='{component}']")
                x, _, width, _ = rect(node)
                self.assertGreaterEqual(x + width, WIDTH - margin)
                self.assertLessEqual(x + width, WIDTH)
                panel_edge = (LEFT+x+width)*PANEL_PIXELS/PANEL_WIDTH
                self.assertLessEqual(panel_edge, PANEL_PIXELS-RIGHT*PANEL_PIXELS/PANEL_WIDTH)
                self.assertGreaterEqual(panel_edge,
                                        PANEL_PIXELS-(RIGHT+margin)*PANEL_PIXELS/PANEL_WIDTH)
        root = ET.parse(native / "manifests/XDriveControl.xml")
        for node in root.findall("pluginApp/hmiStates/hmiState/components/*"):
            self.assertEqual(rect(node)[2], WIDTH - 32)
        root = ET.parse(native / "manifests/PowerDeck.xml")
        for state, background in ((110, 3180), (111, 4180)):
            node = root.find(f"pluginApp/hmiStates/hmiState[@id='{state}']/components/image[@id='{background}']")
            x, _, width, _ = rect(node)
            self.assertEqual((x, width), (0, WIDTH))

    def test_xdrive_short_pages_use_absolute_rows_not_width_capped_native_flow(self):
        native = Path(os.environ.get("ID6_LAYOUT_TEST_NATIVE", NATIVE))
        root = ET.parse(native / "manifests/XDriveControl.xml")
        app = root.find("pluginApp")
        expected = {100: (200, 201, 202, 203), 101: (204, 210, 205, 206), 102: (207, 211, 208, 209)}
        for state, identifiers in expected.items():
            previous_bottom = -8
            page = app.find(f"hmiStates/hmiState[@id='{state}']/components")
            self.assertEqual([int(node.get("id")) for node in page], list(identifiers))
            for node in page:
                with self.subTest(state=state, component=node.get("id")):
                    keys = {p.get("id") for p in node.findall("properties/property")}
                    # Width alone was ignored by real006 native flow.
                    # Keep absolute rows while leaving the common right gutter.
                    self.assertTrue({"20", "21", "9", "10"}.issubset(keys))
                    x, y, width, height = rect(node)
                    self.assert_in_viewport((x, y, width, height))
                    self.assertGreaterEqual(y, previous_bottom + 8)
                    self.assertEqual((x, width), (16, WIDTH-32))
                    previous_bottom = y + height
        for state, first, second in ((101, 204, 210), (102, 207, 211)):
            page = app.find(f"hmiStates/hmiState[@id='{state}']/components")
            self.assertEqual(page.find(f"label[@id='{first}']").get("text"), "In Park, parking brake set.")
            self.assertEqual(page.find(f"label[@id='{second}']").get("text"), "Engine off, or running on F-series DSC_25.")
        for identifier, action in ((200, 21), (201, 11), (202, 12), (205, 22), (208, 23)):
            self.assertEqual(app.find(f"hmiStates/hmiState/components/button[@id='{identifier}']").get("action"), str(action))
        for state in (100, 101, 102):
            self.assertEqual(app.find(f"hmiStates/hmiState[@id='{state}']/components/label[@model='50']").get("model"), "50")

    def test_xdrive_absolute_row_generator_is_idempotent(self):
        source = NATIVE / "manifests/XDriveControl.xml"
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / source.name
            candidate.write_bytes(source.read_bytes())
            update_xdrive(candidate)
            self.assertEqual(candidate.read_bytes(), source.read_bytes())
            update_xdrive(candidate)
            self.assertEqual(candidate.read_bytes(), source.read_bytes())

    def test_hud_positioned_rows_use_the_same_gutter_and_regenerate_idempotently(self):
        source = NATIVE / "manifests/HudTest.xml"
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / source.name
            candidate.write_bytes(source.read_bytes())
            update_hud(candidate)
            self.assertEqual(candidate.read_bytes(), source.read_bytes())
            update_hud(candidate)
            self.assertEqual(candidate.read_bytes(), source.read_bytes())
        root = ET.parse(source)
        for node in root.findall("pluginApp/hmiStates/hmiState/components/*"):
            x, _, width, _ = rect(node)
            self.assertEqual((x, width), (16, WIDTH-32))

    def test_shift_can_migrate_the_previous_full_width_grid_once(self):
        import extend_shift_n57
        source = NATIVE / "manifests/ShiftDeck.xml"
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / source.name
            tree = ET.parse(source)
            for node in tree.findall("pluginApp/hmiStates/hmiState[@id='100']/components/*"):
                props = {p.get("id"): p for p in node.findall("properties/property")}
                identifier = int(node.get("id"))
                if props["9"].get("value") == str(WIDTH):
                    props["9"].set("value", "1260")
                elif identifier in (202, 252, 253):
                    props["20"].set("value", str(int(props["20"].get("value"))+RIGHT))
                elif identifier in (203, 206, 207, 208, 209, 211):
                    props["20"].set("value", str(int(props["20"].get("value"))+RIGHT//2))
            tree.write(candidate, encoding="utf-8", xml_declaration=True)
            extend_shift_n57.update_xml(candidate)
            self.assertEqual(candidate.read_bytes(), source.read_bytes())
            extend_shift_n57.update_xml(candidate)
            self.assertEqual(candidate.read_bytes(), source.read_bytes())

    def test_native_rows_and_options_request_the_logical_content_width(self):
        for app in ("BoostDeck", "ShiftDeck", "LaunchDeck", "EngineCodes", "PowerDeck", "XDriveControl", "HudTest"):
            root = ET.parse(NATIVE / f"manifests/{app}.xml")
            for state in root.findall("pluginApp/hmiStates/hmiState"):
                for section in ("components", "optionComponents"):
                    for node in state.findall(section + "/*"):
                        if node.tag in ("label", "button", "checkbox", "radiobutton") and node.find("properties/property[@id='20']") is None:
                            self.assertEqual(node.find("properties/property[@id='9']").get("value"), str(WIDTH), (app, state.get("id"), node.get("id")))

    def test_ninth_boost_gauge_has_the_same_readable_width_as_other_slots(self):
        page = ET.parse(boost.XML).find("pluginApp/hmiStates/hmiState[@id='100']/components")
        for slot in range(9):
            caption, value, bar = [rect(page.find(f"*[@id='{base+slot}']")) for base in (260, 310, 280)]
            self.assertEqual((caption[2], value[2], bar[2]),
                             (boost.LABEL_WIDTH, boost.LABEL_WIDTH-84, boost.LABEL_WIDTH))
            self.assertLessEqual(caption[1]+caption[3], value[1])
            self.assertLessEqual(value[1]+value[3], bar[1])
        app = ET.parse(boost.XML).find("pluginApp")
        self.assertEqual(app.find("models/imageIdModel[@id='328']").get("imageId"), "55000")
        alert = rect(page.find("image[@id='208']"))
        self.assertEqual(alert, (0, HEIGHT-43, WIDTH, 43))
        for slot in range(9):
            value = rect(page.find(f"label[@id='{310+slot}']"))
            dial = rect(page.find(f"image[@id='{290+slot}']"))
            self.assertLessEqual(value[0]+value[2], dial[0])
            self.assertLessEqual(dial[1]+dial[3], alert[1])

    def test_fault_code_and_description_are_separate_full_width_lines(self):
        app = ET.parse(codes.XML).find("pluginApp")
        page = app.find("hmiStates/hmiState[@id='101']/components")
        self.assertEqual(len(page.findall("label")), 1+2*codes.PAGE_SIZE)
        for row in range(codes.PAGE_SIZE):
            code = rect(page.find(f"label[@model='{81+row}']"))
            detail = rect(page.find(f"label[@model='{91+row}']"))
            self.assertEqual(code[0], detail[0])
            self.assertEqual((code[2], detail[2]), (WIDTH-32,) * 2)
            self.assertLessEqual(code[1]+code[3], detail[1])
            self.assertGreaterEqual(detail[3], 52)
        cpp = (NATIVE / "src/plugins/engine_codes.cpp").read_text()
        self.assertEqual(int(re.search(r"kCodePageSize\s*=\s*(\d+)", cpp)[1]), codes.PAGE_SIZE)
        # The explicit user-confirmed clear action remains a separate page.
        self.assertIsNotNone(app.find("hmiStates/hmiState[@id='102']/components/button[@action='27']"))
        self.assertIsNotNone(app.find("hmiStates/hmiState[@id='101']/optionComponents/button[@action='29']"))

    def test_engine_xml_generation_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "EngineCodes.xml"
            path.write_bytes(codes.XML.read_bytes())
            codes.update_xml(path)
            self.assertEqual(path.read_bytes(), codes.XML.read_bytes())

    def test_launch_fills_content_and_glyphs_match_component_dimensions(self):
        images = launch_art.assets()
        self.assertEqual((launch_art.LEFT, launch_art.TOP), (0, 0))
        self.assertEqual(images[launch_art.BACKGROUND].size, (WIDTH, HEIGHT))
        # The obsolete inset outer border no longer frames the entire application.
        self.assertNotEqual(images[launch_art.BACKGROUND].getpixel((0, 0))[:3], launch_art.CARD_EDGE)
        for _, image_id, x, y, width, height in launch_art.layout():
            self.assert_in_viewport((x, y, width, height))
            self.assertEqual(images[image_id].size, (width, height))

    def test_rebuilt_backgrounds_match_layout_and_preserve_other_assets(self):
        from PIL import Image
        with ZipFile(NATIVE.parents[1] / "packages/dashboard.zip") as package:
            for app, generator, image_id in (("BoostDeck", boost, boost.BACKGROUND),
                                              ("EngineCodes", codes, codes.BACKGROUND)):
                original = package.read(f"{app}/{app}_ALL_Images.zip")
                with tempfile.TemporaryDirectory() as directory:
                    source, dest = Path(directory)/"before.zip", Path(directory)/"after.zip"
                    source.write_bytes(original)
                    generator.update_images(source, dest)
                    with ZipFile(BytesIO(original)) as before, ZipFile(dest) as after:
                        self.assertTrue(set(before.namelist()).issubset(set(after.namelist())))
                        for name in before.namelist():
                            if name == f"{image_id}.png":
                                self.assertEqual(Image.open(BytesIO(after.read(name))).size, (WIDTH, HEIGHT))
                            elif app != "BoostDeck" or not (boost.ALERT_BACKGROUND <= int(Path(name).stem) <= boost.DIAL_FIRST+(len(boost.COLORS)+len(boost.MULTICOLOR))*(boost.DIAL_STEPS+1)):
                                self.assertEqual(after.read(name), before.read(name))


if __name__ == "__main__":
    unittest.main()

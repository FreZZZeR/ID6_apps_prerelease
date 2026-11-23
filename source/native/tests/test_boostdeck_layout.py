"""Check the committed RHMI selectors against generated channel/action IDs."""
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

NATIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NATIVE.parent / "tools"))
import make_boostdeck_extended as layout


class BoostDeckLayoutTest(unittest.TestCase):
    def test_generated_xml_matches_committed(self):
        original = layout.XML
        try:
            with tempfile.TemporaryDirectory() as directory:
                layout.XML = Path(directory) / "BoostDeck.xml"
                # The generator uses the existing color/entry states as its base.
                layout.XML.write_bytes(original.read_bytes())
                layout.update_xml()
                self.assertEqual(layout.XML.read_bytes(), original.read_bytes())
        finally:
            layout.XML = original

    def test_all_nine_gauges_can_select_every_channel_without_id_collisions(self):
        app = ET.parse(layout.XML).find("pluginApp")
        for section in ("actions", "models", "hmiStates"):
            ids = [x.get("id") for x in app.find(section)]
            self.assertEqual(len(ids), len(set(ids)), section)
        actions = {x.get("id"): x.tag for x in app.find("actions")}
        components = []
        for slot in range(9):
            page = app.find(f"hmiStates/hmiState[@id='{510 + slot}']/components")
            choices = page.findall("radiobutton")
            self.assertEqual([x.get("text") for x in choices], layout.SIGNALS)
            self.assertEqual([x.get("action") for x in choices],
                             [str(3500 + i) for i in range(len(layout.SIGNALS))])
            for choice in choices:
                self.assertEqual(actions[choice.get("action")], "combinedAction")
                action = app.find("actions/combinedAction[@id='%s']/actions/raAction" % choice.get("action"))
                self.assertEqual(action.get("id"), str(600+choices.index(choice)))
            components += [x.get("id") for x in page]
        self.assertEqual(len(components), len(set(components)))
        self.assertEqual(layout.SIGNALS[31:], ["DPF soot", "DPF pressure", "DPF regen dist.",
                                              "EGT pre-DPF", "EGT pre-cat", "AdBlue level",
                                              "DDE torque", "Power (calc.)", "Fuel volume"])

    def test_layout_reuses_available_images(self):
        app = ET.parse(layout.XML).find("pluginApp")
        with ZipFile(NATIVE.parents[1] / "packages/dashboard.zip") as package:
            with ZipFile(BytesIO(package.read("BoostDeck/BoostDeck_ALL_Images.zip"))) as images:
                ids = {Path(x).stem for x in images.namelist()}
        for model in app.findall("models/imageIdModel"):
            self.assertIn(model.get("imageId"), ids)

    def test_emissions_visibility_controls_and_component_ids(self):
        app = ET.parse(layout.XML).find("pluginApp")
        profile = app.find("hmiStates/hmiState[@id='501']/components")
        self.assertIsNotNone(profile.find("label[@model='361']"))
        for action, caption in ((504, "Show emissions gauges"), (505, "Hide emissions gauges")):
            self.assertIsNotNone(app.find(f"actions/raAction[@id='{action}']"))
            self.assertEqual(profile.find(f"button[@action='{action}']").get("text"), caption)
        for slot in range(9):
            page = app.find(f"hmiStates/hmiState[@id='{510 + slot}']/components")
            for signal in (31, 32, 33, 36):
                self.assertEqual(page.find(f"radiobutton[@action='{3500 + signal}']").get("id"),
                                 str(1001 + slot * (len(layout.SIGNALS)+1) + signal))


if __name__ == "__main__":
    unittest.main()

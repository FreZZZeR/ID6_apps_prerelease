"""Native BMW RHMI layout units, before the HMI scales them to panel pixels."""
import xml.etree.ElementTree as ET
from pathlib import Path

# The common wide-screen HMI uses 1440 design units. On the 1280px panel it
# scales by 8/9; the 180-unit back-navigation strip occupies 160 physical px.
PANEL_WIDTH, PANEL_PIXELS, LEFT = 1440, 1280, 180
# Leave a small gutter before the physical screen edge (about 21px at 1280).
RIGHT = 24
WIDTH, HEIGHT = PANEL_WIDTH - LEFT - RIGHT, 420


def flow_widths(app):
    """Set preferred width while retaining BMW's native scrolling row layout."""
    for state in app.findall("hmiStates/hmiState"):
        for section in ("components", "optionComponents"):
            for node in state.findall(section + "/*"):
                if node.tag not in ("label", "button", "checkbox", "checkBox", "radiobutton"):
                    continue
                if node.find("properties/property[@id='20']") is not None:
                    continue
                props = node.find("properties")
                if props is None:
                    props = ET.SubElement(node, "properties")
                width = props.find("property[@id='9']")
                if width is None:
                    width = ET.SubElement(props, "property", id="9")
                width.set("value", str(WIDTH))


def update_xdrive(path):
    """Short control pages need absolute rows: native flow caps their width."""
    tree = ET.parse(path)
    pages = tree.find("pluginApp/hmiStates")
    for state, first, second in ((101, 204, 210), (102, 207, 211)):
        page = pages.find(f"hmiState[@id='{state}']/components")
        page.find(f"label[@id='{first}']").set("text", "In Park, parking brake set.")
        detail = page.find(f"label[@id='{second}']")
        if detail is None:
            detail = ET.Element("label", id=str(second))
            page.insert(1, detail)
        detail.set("text", "Engine off, or running on F-series DSC_25.")
    rows = {100: ((200, 0, 72), (201, 84, 72), (202, 168, 72), (203, 252, 160)),
            101: ((204, 0, 48), (210, 56, 48), (205, 120, 72), (206, 212, 200)),
            102: ((207, 0, 48), (211, 56, 48), (208, 120, 72), (209, 212, 200))}
    for state, components in rows.items():
        page = pages.find(f"hmiState[@id='{state}']/components")
        for identifier, y, height in components:
            node = page.find(f"*[@id='{identifier}']")
            props = node.find("properties")
            if props is None:
                props = ET.SubElement(node, "properties")
            for key, value in ((20, 16), (21, y), (9, WIDTH - 32), (10, height)):
                prop = props.find(f"property[@id='{key}']")
                if prop is None:
                    prop = ET.SubElement(props, "property", id=str(key))
                prop.set("value", str(value))
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def update_hud(path):
    tree = ET.parse(path)
    app = tree.find("pluginApp")
    for node in app.findall("hmiStates/hmiState/components/*"):
        node.find("properties/property[@id='9']").set("value", str(WIDTH - 32))
    flow_widths(app)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    plugin = Path(__file__).resolve().parents[1] / "native/manifests"
    update_xdrive(plugin / "XDriveControl.xml")
    update_hud(plugin / "HudTest.xml")

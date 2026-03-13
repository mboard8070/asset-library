import xml.etree.ElementTree as ET

import pytest
from assetlib.materialx import generate_mtlx


@pytest.fixture
def simple_zones():
    return {
        "body_plastic": {
            "type": "standard_surface",
            "base_color": [0.42, 0.18, 0.55],
            "specular_roughness": 0.15,
            "metalness": 0.0,
        }
    }


@pytest.fixture
def textured_zones():
    return {
        "label_front": {
            "type": "standard_surface",
            "base_color_map": "textures/label_diffuse.exr",
            "specular_roughness": 0.4,
            "normal_map": "textures/label_normal.exr",
        }
    }


@pytest.fixture
def multi_zone():
    return {
        "body": {
            "base_color": [0.8, 0.2, 0.6],
            "specular_roughness": 0.15,
        },
        "cap": {
            "base_color": [0.9, 0.9, 0.9],
            "specular_roughness": 0.05,
        },
    }


class TestMaterialXGeneration:
    def test_generates_valid_xml(self, tmp_path, simple_zones):
        out = tmp_path / "test.mtlx"
        generate_mtlx(simple_zones, out)
        assert out.exists()
        tree = ET.parse(out)
        root = tree.getroot()
        assert root.tag == "materialx"
        assert root.attrib["version"] == "1.39"

    def test_creates_shader_and_material(self, tmp_path, simple_zones):
        out = tmp_path / "test.mtlx"
        generate_mtlx(simple_zones, out)
        root = ET.parse(out).getroot()

        shader = root.find(".//standard_surface[@name='SR_body_plastic']")
        assert shader is not None
        assert shader.attrib["type"] == "surfaceshader"

        material = root.find(".//surfacematerial[@name='MAT_body_plastic']")
        assert material is not None

    def test_direct_value_inputs(self, tmp_path, simple_zones):
        out = tmp_path / "test.mtlx"
        generate_mtlx(simple_zones, out)
        root = ET.parse(out).getroot()

        shader = root.find(".//standard_surface[@name='SR_body_plastic']")
        inputs = {i.attrib["name"]: i.attrib for i in shader.findall("input")}

        assert "base_color" in inputs
        assert inputs["base_color"]["type"] == "color3"
        assert inputs["base_color"]["value"] == "0.42, 0.18, 0.55"

        assert "specular_roughness" in inputs
        assert inputs["specular_roughness"]["value"] == "0.15"

    def test_texture_creates_nodegraph(self, tmp_path, textured_zones):
        out = tmp_path / "test.mtlx"
        generate_mtlx(textured_zones, out)
        root = ET.parse(out).getroot()

        ng = root.find(".//nodegraph[@name='NG_label_front']")
        assert ng is not None

        # Should have image nodes for base_color and normal
        image_nodes = ng.findall("image")
        assert len(image_nodes) >= 1

    def test_normal_map_creates_normalmap_node(self, tmp_path, textured_zones):
        out = tmp_path / "test.mtlx"
        generate_mtlx(textured_zones, out)
        root = ET.parse(out).getroot()

        ng = root.find(".//nodegraph[@name='NG_label_front']")
        normalmap = ng.find("normalmap")
        assert normalmap is not None

    def test_multi_zone_output(self, tmp_path, multi_zone):
        out = tmp_path / "test.mtlx"
        generate_mtlx(multi_zone, out)
        root = ET.parse(out).getroot()

        materials = root.findall("surfacematerial")
        assert len(materials) == 2

        mat_names = {m.attrib["name"] for m in materials}
        assert "MAT_body" in mat_names
        assert "MAT_cap" in mat_names

    def test_creates_parent_dirs(self, tmp_path, simple_zones):
        out = tmp_path / "deep" / "nested" / "dir" / "test.mtlx"
        generate_mtlx(simple_zones, out)
        assert out.exists()

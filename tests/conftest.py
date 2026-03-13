import pytest
from pathlib import Path


@pytest.fixture
def schema_path():
    return Path(__file__).resolve().parent.parent / "schemas" / "manifest.schema.json"


@pytest.fixture
def sample_manifest_dict():
    return {
        "schema_version": "1.0",
        "sku": "030772008355",
        "product_name": "Safeguard Liquid Hand Soap - Notes of Lavender",
        "brand": "Safeguard",
        "parent_company": "Procter & Gamble",
        "category": "personal_care",
        "archetype": "pump_bottle",
        "dimensions": {"height_cm": 20.3, "width_cm": 8.9, "depth_cm": 5.1},
        "weight": {"value": 15.5, "unit": "fl_oz"},
        "pack_count": 1,
        "base_geometry": "geo/base.usd",
        "material": "materials/master.mtlx",
        "lods": {
            "hero": "geo/base.usd",
            "realtime": "geo/lod1.usd",
            "thumbnail": "geo/lod2.usd",
        },
        "variants": {
            "en-us": {
                "label_texture": "variants/en-us/label_diffuse.exr",
                "product_name_localized": "Safeguard Liquid Hand Soap - Notes of Lavender",
            }
        },
        "render_presets": {
            "ecommerce": {
                "resolution": [2048, 2048],
                "renderer": "arnold",
                "lighting_rig": "rigs/packshot_neutral.usd",
                "background": "white",
            }
        },
        "tags": ["hand soap", "antibacterial", "lavender"],
        "created": "2026-03-13",
        "updated": "2026-03-13",
    }


@pytest.fixture
def tmp_asset_dir(tmp_path, sample_manifest_dict):
    """Create a minimal valid asset directory for testing."""
    import yaml

    asset_dir = tmp_path / "test-product"
    asset_dir.mkdir()

    # Required dirs
    (asset_dir / "geo").mkdir()
    (asset_dir / "materials").mkdir()
    (asset_dir / "variants").mkdir()

    # Write manifest
    manifest_path = asset_dir / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(sample_manifest_dict, f, default_flow_style=False)

    return asset_dir

import pytest
from assetlib.validator import validate_asset_directory, validate_manifest


class TestDirectoryValidation:
    def test_valid_directory_passes(self, tmp_asset_dir):
        errors = validate_asset_directory(tmp_asset_dir)
        assert errors == []

    def test_missing_manifest_fails(self, tmp_asset_dir):
        (tmp_asset_dir / "manifest.yaml").unlink()
        errors = validate_asset_directory(tmp_asset_dir)
        assert any("manifest.yaml" in e for e in errors)

    def test_missing_required_dir_fails(self, tmp_asset_dir):
        import shutil
        shutil.rmtree(tmp_asset_dir / "geo")
        errors = validate_asset_directory(tmp_asset_dir)
        assert any("geo" in e for e in errors)

    def test_not_a_directory_fails(self, tmp_path):
        fake = tmp_path / "not-a-dir.txt"
        fake.write_text("nope")
        errors = validate_asset_directory(fake)
        assert any("Not a directory" in e for e in errors)


class TestManifestValidation:
    def test_valid_manifest_passes(self, sample_manifest_dict):
        errors = validate_manifest(sample_manifest_dict)
        assert errors == []

    def test_missing_sku_fails(self, sample_manifest_dict):
        del sample_manifest_dict["sku"]
        errors = validate_manifest(sample_manifest_dict)
        assert any("sku" in e for e in errors)

    def test_missing_brand_fails(self, sample_manifest_dict):
        del sample_manifest_dict["brand"]
        errors = validate_manifest(sample_manifest_dict)
        assert any("brand" in e for e in errors)

    def test_invalid_archetype_fails(self, sample_manifest_dict):
        sample_manifest_dict["archetype"] = "invalid_shape"
        errors = validate_manifest(sample_manifest_dict)
        assert any("archetype" in e for e in errors)

    def test_invalid_category_fails(self, sample_manifest_dict):
        sample_manifest_dict["category"] = "food"
        errors = validate_manifest(sample_manifest_dict)
        assert any("category" in e for e in errors)

    def test_extra_fields_rejected(self, sample_manifest_dict):
        sample_manifest_dict["unknown_field"] = "surprise"
        errors = validate_manifest(sample_manifest_dict)
        assert len(errors) > 0

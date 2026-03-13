from pathlib import Path

import jsonschema

from .constants import MANIFEST_FILENAME, REQUIRED_DIRS
from .manifest import load_manifest, load_schema


def validate_asset_directory(path: Path) -> list[str]:
    """Validate that an asset directory has the required structure.

    Returns a list of error strings. Empty list means valid.
    """
    errors = []
    asset_dir = Path(path)

    if not asset_dir.is_dir():
        return [f"Not a directory: {asset_dir}"]

    # Check manifest exists
    manifest_path = asset_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        errors.append(f"Missing {MANIFEST_FILENAME}")

    # Check required subdirectories
    for dirname in REQUIRED_DIRS:
        if not (asset_dir / dirname).is_dir():
            errors.append(f"Missing required directory: {dirname}/")

    return errors


def validate_manifest(manifest: dict) -> list[str]:
    """Validate a manifest dict against the JSON Schema.

    Returns a list of error strings. Empty list means valid.
    """
    errors = []
    schema = load_schema()

    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(manifest), key=lambda e: list(e.path)):
        field = ".".join(str(p) for p in error.path) or "(root)"
        errors.append(f"{field}: {error.message}")

    return errors


def validate_file_references(asset_dir: Path, manifest: dict) -> list[str]:
    """Soft-check that files referenced in the manifest exist.

    Returns warnings (not hard errors) for missing files — expected
    during scaffolding when USD/texture files haven't been created yet.
    """
    warnings = []

    # Check base geometry
    geo_path = asset_dir / manifest.get("base_geometry", "")
    if geo_path.name and not geo_path.exists():
        warnings.append(f"Referenced file not found: {manifest['base_geometry']}")

    # Check material
    mtl_path = asset_dir / manifest.get("material", "")
    if mtl_path.name and not mtl_path.exists():
        warnings.append(f"Referenced file not found: {manifest['material']}")

    # Check LODs
    for lod_name, lod_path in manifest.get("lods", {}).items():
        if not (asset_dir / lod_path).exists():
            warnings.append(f"LOD '{lod_name}' file not found: {lod_path}")

    # Check variant textures
    for locale, variant in manifest.get("variants", {}).items():
        tex = variant.get("label_texture", "")
        if tex and not (asset_dir / tex).exists():
            warnings.append(f"Variant '{locale}' texture not found: {tex}")

    return warnings


def run_full_validation(asset_dir: Path) -> tuple[list[str], list[str]]:
    """Run all validations on an asset directory.

    Returns (errors, warnings). Errors are fatal, warnings are informational.
    """
    errors = validate_asset_directory(asset_dir)
    if errors:
        return errors, []

    manifest = load_manifest(asset_dir)
    schema_errors = validate_manifest(manifest)
    errors.extend(schema_errors)

    warnings = validate_file_references(asset_dir, manifest)

    return errors, warnings

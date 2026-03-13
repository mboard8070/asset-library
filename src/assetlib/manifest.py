import json
from pathlib import Path

import yaml

from .constants import MANIFEST_FILENAME, get_schema_path


def load_manifest(path: Path) -> dict:
    """Load and parse a manifest YAML file."""
    manifest_path = path if path.is_file() else path / MANIFEST_FILENAME
    with open(manifest_path) as f:
        return yaml.safe_load(f)


def load_schema() -> dict:
    """Load the JSON Schema for manifest validation."""
    schema_path = get_schema_path()
    with open(schema_path) as f:
        return json.load(f)


def resolve_asset_root(manifest_path: Path) -> Path:
    """Return the asset directory containing the manifest."""
    if manifest_path.is_file():
        return manifest_path.parent
    return manifest_path

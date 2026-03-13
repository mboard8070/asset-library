from pathlib import Path

REQUIRED_DIRS = ["geo", "materials", "variants"]
OPTIONAL_DIRS = ["rigs", "renders"]
MANIFEST_FILENAME = "manifest.yaml"
SCHEMA_FILENAME = "manifest.schema.json"
SUPPORTED_GEO_FORMATS = [".usd", ".usda", ".usdc", ".usdz", ".abc"]
SUPPORTED_TEX_FORMATS = [".exr", ".png", ".tif", ".tiff", ".hdr", ".tx"]


def get_repo_root() -> Path:
    """Walk up from this file to find the repo root (contains .git/)."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    raise FileNotFoundError("Could not find repo root (.git directory)")


def get_schema_path() -> Path:
    return get_repo_root() / "schemas" / SCHEMA_FILENAME

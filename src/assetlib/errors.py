class AssetLibError(Exception):
    """Base error for asset library operations."""


class ManifestValidationError(AssetLibError):
    """Manifest failed schema validation."""


class DirectoryValidationError(AssetLibError):
    """Asset directory structure is invalid."""

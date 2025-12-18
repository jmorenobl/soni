"""Version information for Soni Framework.

The version is read from pyproject.toml to maintain a single source of truth.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("soni")
except PackageNotFoundError:
    # Package not installed, fallback for development
    __version__ = "0.0.0-dev"


def get_version_info() -> dict[str, str | int]:
    """Parse version string into components.

    Returns:
        Dictionary with major, minor, patch, and full version
    """
    parts = __version__.split(".")
    return {
        "major": int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0,
        "minor": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
        "patch": parts[2] if len(parts) > 2 else "0",  # May include suffix
        "full": __version__,
    }

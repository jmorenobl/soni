"""Tests for version management.

Verifies single source of truth for version.
"""


class TestVersion:
    """Tests for version management."""

    def test_version_importable_from_root(self):
        """Test that __version__ can be imported from soni."""
        from soni import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_follows_semver(self):
        """Test that version follows semantic versioning pattern."""
        from soni import __version__

        parts = __version__.split(".")
        assert len(parts) >= 2, "Version should have at least major.minor"

        # Major and minor should be numeric
        assert parts[0].isdigit(), "Major version should be numeric"
        assert parts[1].isdigit(), "Minor version should be numeric"

    def test_get_version_info_returns_dict(self):
        """Test that get_version_info returns proper structure."""
        from soni import get_version_info

        info = get_version_info()

        assert "major" in info
        assert "minor" in info
        assert "patch" in info
        assert "full" in info

        assert isinstance(info["major"], int)
        assert isinstance(info["minor"], int)

    def test_version_matches_pyproject(self):
        """Test that version matches pyproject.toml."""
        import tomllib
        from pathlib import Path

        from soni import __version__

        # Read version from pyproject.toml
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)

        expected_version = pyproject["project"]["version"]
        assert __version__ == expected_version


class TestVersionEndpoint:
    """Tests for /version API endpoint."""

    def test_version_endpoint_returns_version(self):
        """Test that /version endpoint returns version info."""
        from fastapi.testclient import TestClient

        from soni import __version__
        from soni.server.api import app

        client = TestClient(app)
        response = client.get("/version")

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == __version__
        assert "major" in data
        assert "minor" in data
        assert "patch" in data

    def test_health_endpoint_includes_version(self):
        """Test that /health endpoint includes correct version."""
        from fastapi.testclient import TestClient

        from soni import __version__
        from soni.server.api import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == __version__

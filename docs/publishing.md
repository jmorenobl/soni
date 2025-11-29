# Publishing to TestPyPI

This guide explains how to publish the Soni package to TestPyPI (PyPI test repository) before publishing to the official PyPI.

## Prerequisites

1. **TestPyPI Account**: Create an account at [https://test.pypi.org/account/register/](https://test.pypi.org/account/register/)
2. **API Token**: Generate an API token at [https://test.pypi.org/manage/account/token/](https://test.pypi.org/manage/account/token/)
   - Select "Entire account" or a specific scope
   - Copy the token (it's only shown once)

## Preparation

### 1. Verify Project Configuration

Make sure `pyproject.toml` is correctly configured:

- ✅ Package name: `soni`
- ✅ Version: `0.1.0` (or the version you want to publish)
- ✅ Description, authors, license, etc.

### 2. Clean Previous Builds

```bash
# Remove dist/ directory if it exists
rm -rf dist/

# Remove build files if they exist
rm -rf build/
rm -rf *.egg-info/
```

### 3. Verify Code is Ready

```bash
# Run tests
uv run pytest

# Check linting
uv run ruff check .

# Check types
uv run mypy src/soni
```

## Building the Package

### Option 1: Using `uv` (Recommended)

`uv` can build and publish packages directly:

```bash
# Build the package
uv build

# This will create files in dist/:
# - soni-0.1.0-py3-none-any.whl (wheel)
# - soni-0.1.0.tar.gz (sdist)
```

### Option 2: Using `build` (Alternative)

If you prefer to use the standard `build` tool:

```bash
# Install build if not installed
uv add --dev build

# Build the package
uv run python -m build
```

## Publishing to TestPyPI

### Option 1: Using `uv` (Recommended)

`uv` supports direct publishing to PyPI/TestPyPI:

```bash
# Publish to TestPyPI
uv publish --publish-url https://test.pypi.org/legacy/ dist/*

# It will prompt for:
# - Username: __token__
# - Password: <your-testpypi-token>
```

Or you can configure credentials as environment variables:

```bash
# Set environment variables
export UV_PUBLISH_USERNAME="__token__"
export UV_PUBLISH_PASSWORD="pypi-<your-testpypi-token>"

# Publish
uv publish --publish-url https://test.pypi.org/legacy/ dist/*
```

### Option 2: Using `twine` (Alternative)

If you prefer to use `twine` (PyPI's standard tool):

```bash
# Install twine
uv add --dev twine

# Verify the package before publishing (recommended)
uv run twine check dist/*

# Publish to TestPyPI
uv run twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# It will prompt for:
# - Username: __token__
# - Password: <your-testpypi-token>
```

### Option 3: Configure Credentials in File

You can create a `.pypirc` file in your home directory (`~/.pypirc`):

```ini
[distutils]
index-servers =
    testpypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-<your-testpypi-token>
```

Then use:

```bash
# With twine
uv run twine upload --repository testpypi dist/*

# With uv (doesn't use .pypirc, but you can use environment variables)
uv publish --publish-url https://test.pypi.org/legacy/ dist/*
```

## Verifying the Publication

1. Visit [https://test.pypi.org/project/soni/](https://test.pypi.org/project/soni/)
2. Verify that the published version is correct
3. Verify that metadata (description, authors, etc.) displays correctly

## Installing from TestPyPI

To test that installation works:

```bash
# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ soni

# Or with uv
uv pip install --index-url https://test.pypi.org/simple/ soni
```

**Note**: If the package has dependencies, you may need to also specify the official PyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ soni
```

## Publishing to Official PyPI

Once you've verified everything works on TestPyPI, you can publish to the official PyPI:

### 1. Create PyPI Account

- Register at [https://pypi.org/account/register/](https://pypi.org/account/register/)
- Generate API token at [https://pypi.org/manage/account/token/](https://pypi.org/manage/account/token/)

### 2. Publish

```bash
# With uv
uv publish dist/*

# Or with twine
uv run twine upload dist/*
```

## Pre-Publication Checklist

Before publishing, make sure:

- [ ] ✅ All tests pass (`uv run pytest`)
- [ ] ✅ Linting passes (`uv run ruff check .`)
- [ ] ✅ Type checking passes (`uv run mypy src/soni`)
- [ ] ✅ Version in `pyproject.toml` is correct
- [ ] ✅ README.md is updated
- [ ] ✅ Metadata in `pyproject.toml` is correct
- [ ] ✅ No sensitive files in the package (verify with `uv run twine check dist/*`)
- [ ] ✅ Package can be installed from TestPyPI

## Troubleshooting

### Error: "File already exists"

If you try to publish the same version twice, TestPyPI/PyPI will reject the publication. You must:

1. Increment the version in `pyproject.toml`
2. Rebuild the package
3. Publish again

### Error: "Invalid credentials"

- Verify that the token is correct
- Make sure to use `__token__` as username
- Verify that the token has the correct permissions

### Error: "Package name already taken"

If the package name already exists on PyPI, you need to:

1. Change the name in `pyproject.toml` (not recommended if you already have users)
2. Or request package transfer if you are the legitimate owner

### Verify Package Contents

Before publishing, you can verify which files will be included:

```bash
# With uv
uv build --sdist
tar -tzf dist/soni-*.tar.gz | head -20

# Or install the package locally and verify
uv pip install dist/soni-*.whl
python -c "import soni; print(soni.__file__)"
```

## Automation with GitHub Actions

You can automate publication using GitHub Actions. Example:

```yaml
name: Publish to TestPyPI

on:
  release:
    types: [created]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3

      - name: Build package
        run: uv build

      - name: Publish to TestPyPI
        env:
          UV_PUBLISH_USERNAME: __token__
          UV_PUBLISH_PASSWORD: ${{ secrets.TESTPYPI_API_TOKEN }}
        run: |
          uv publish --publish-url https://test.pypi.org/legacy/ dist/*
```

## References

- [TestPyPI Documentation](https://test.pypi.org/)
- [PyPI Documentation](https://packaging.python.org/)
- [uv publish documentation](https://docs.astral.sh/uv/publishing/)
- [twine documentation](https://twine.readthedocs.io/)

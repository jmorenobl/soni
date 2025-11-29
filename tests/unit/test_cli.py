"""Unit tests for CLI module"""

from typer.testing import CliRunner

from soni.cli.main import app


def test_cli_help():
    """Test CLI help command displays framework info and available commands"""
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["--help"])

    # Assert
    assert result.exit_code == 0
    assert "Soni Framework" in result.stdout
    assert "optimize" in result.stdout
    assert "server" in result.stdout


def test_cli_version():
    """Test CLI version command displays correct version"""
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["--version"])

    # Assert
    assert result.exit_code == 0
    assert "Soni Framework version 0.0.1" in result.stdout


def test_optimize_command():
    """Test optimize command shows placeholder message"""
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["optimize"])

    # Assert
    assert result.exit_code == 0
    assert "Coming soon in Hito 4" in result.stdout


def test_server_command():
    """Test server command shows placeholder message"""
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["server"])

    # Assert
    assert result.exit_code == 0
    assert "Coming soon in Hito 7" in result.stdout

"""Unit tests for CLI module"""

from typer.testing import CliRunner

from soni.cli.main import app

runner = CliRunner()


def test_cli_help():
    """Test CLI help command"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Soni Framework" in result.stdout
    assert "optimize" in result.stdout
    assert "server" in result.stdout


def test_cli_version():
    """Test CLI version command"""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Soni Framework version 0.0.1" in result.stdout


def test_optimize_command():
    """Test optimize command"""
    result = runner.invoke(app, ["optimize"])
    assert result.exit_code == 0
    assert "Coming soon in Hito 4" in result.stdout


def test_server_command():
    """Test server command"""
    result = runner.invoke(app, ["server"])
    assert result.exit_code == 0
    assert "Coming soon in Hito 7" in result.stdout

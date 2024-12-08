import pytest

from arrg import app, option, subcommand


def test_basic_subcommand(capsys):
  @subcommand
  class Status:
    verbose: bool = option(short=True, long=True, help='Show verbose output')

  @app
  class Git:
    status: Status

  result = Git.from_iter(['status', '--verbose'])
  assert result.status.verbose


def test_subcommand_help_text(capsys):
  @subcommand
  class Status:
    verbose: bool = option(short=True, long=True, help='Show verbose output')

  @app
  class Git:
    status: Status

  with pytest.raises(SystemExit):
    Git.from_iter(['--help'])

  captured = capsys.readouterr()
  assert 'status' in captured.out

  with pytest.raises(SystemExit):
    Git.from_iter(['status', '--help'])

  captured = capsys.readouterr()
  assert '--verbose' in captured.out
  assert '-v' in captured.out
  assert 'Show verbose output' in captured.out

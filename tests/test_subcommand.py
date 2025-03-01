import pytest

from arrg import app, argument, subcommand


def test_basic_subcommand():
  @subcommand
  class Status:
    verbose: bool = argument('--verbose')

  @app
  class Git:
    status: Status

  result = Git.from_iter(['status'])
  assert not result.status.verbose

  result = Git.from_iter(['status', '--verbose'])
  assert result.status.verbose


def test_nested_subcommands():
  @subcommand
  class Remove:
    name: str = argument()

  @subcommand
  class Remote:
    remove: Remove

  @app
  class Git:
    remote: Remote

  result = Git.from_iter(['remote', 'remove', 'origin'])
  assert result.remote.remove.name == 'origin'


def test_multiple_subcommands_same_level():
  @subcommand
  class Add:
    all: bool = argument('-a')

  @subcommand
  class Commit:
    message: str = argument('-m', '--message')

  @app
  class Git:
    add: Add
    commit: Commit

  result = Git.from_iter(['add', '-a'])
  assert result.add.all
  assert result.commit is None

  result = Git.from_iter(['commit', '-m', 'test commit'])
  assert result.commit.message == 'test commit'
  assert result.add is None


def test_subcommand_help_text(capsys):
  @subcommand
  class Status:
    verbose: bool = argument('-v', '--verbose', help='Show verbose output')

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


def test_subcommand_with_positional_args():
  @subcommand
  class Clone:
    repository: str = argument()
    destination: str = argument('--destination')

  @app
  class Git:
    clone: Clone

  result = Git.from_iter(
    ['clone', 'https://github.com/user/repo', '--destination', '/path/to/dest']
  )

  assert result.clone.repository == 'https://github.com/user/repo'
  assert result.clone.destination == '/path/to/dest'


def test_multiple_subcommands_same_level_with_same_arguments():
  @subcommand
  class Add:
    foo: bool = argument('-f')

  @subcommand
  class Commit:
    foo: bool = argument('-f')

  @app
  class Git:
    add: Add
    commit: Commit

  result = Git.from_iter(['add', '-f'])
  assert result.add.foo
  assert result.commit is None

  result = Git.from_iter(['commit', '-f'])
  assert result.commit.foo
  assert result.add is None

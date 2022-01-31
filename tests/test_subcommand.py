import pytest

from arrg import app, option, subcommand


def test_basic_subcommand(capsys):
  @subcommand
  class Status:
    verbose: bool = option(short=True, long=True, help='Show verbose output')

  @app
  class Git:
    status: Status

  result = Git.from_iter(['status'])
  assert not result.status.verbose

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


def test_nested_subcommands(capsys):
  @subcommand
  class Push:
    force: bool = option(short=True, help='Force push')
    remote: str = option(long=True, default_value='origin')

  @subcommand
  class Remote:
    push: Push
    verbose: bool = option(short=True)

  @app
  class Git:
    remote: Remote

  result = Git.from_iter(['remote', 'push', '-f', '--remote', 'upstream'])
  assert result.remote.push.force
  assert result.remote.push.remote == 'upstream'
  assert not result.remote.verbose


def test_multiple_subcommands_same_level():
  @subcommand
  class Add:
    all: bool = option(short=True)

  @subcommand
  class Commit:
    message: str = option(short='m', long='message')

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


def test_subcommand_with_positional_args():
  @subcommand
  class Clone:
    repository: str
    destination: str = option(long=True)

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
    foo: bool = option(short=True)

  @subcommand
  class Commit:
    foo: bool = option(short=True)

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

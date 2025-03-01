import typing as t

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


def test_subcommand_inheritance_basic():
  @subcommand
  class BaseCommand:
    verbose: bool = argument('-v', '--verbose', help='Show verbose output')
    quiet: bool = argument('-q', '--quiet', help='Suppress output')

  @subcommand
  class Status(BaseCommand):
    all: bool = argument('-a', '--all', help='Show all statuses')

  @app
  class Git:
    status: Status

  # Test with no arguments
  result = Git.from_iter(['status'])
  assert not result.status.verbose
  assert not result.status.quiet
  assert not result.status.all

  # Test with base class argument
  result = Git.from_iter(['status', '--verbose'])
  assert result.status.verbose
  assert not result.status.quiet
  assert not result.status.all

  # Test with derived class argument
  result = Git.from_iter(['status', '--all'])
  assert not result.status.verbose
  assert not result.status.quiet
  assert result.status.all

  # Test with mixed arguments
  result = Git.from_iter(['status', '--verbose', '--all', '--quiet'])
  assert result.status.verbose
  assert result.status.quiet
  assert result.status.all


def test_subcommand_inheritance_multilevel():
  @subcommand
  class BaseCommand:
    global_flag: bool = argument('--global', help='Apply globally')

  @subcommand
  class RemoteCommand(BaseCommand):
    remote_name: str = argument('--name', default='origin')

  @subcommand
  class RemotePush(RemoteCommand):
    force: bool = argument('-f', '--force', help='Force push')

  @app
  class Git:
    push: RemotePush

  # Test with arguments from all levels
  result = Git.from_iter(['push', '--global', '--name', 'upstream', '--force'])
  assert result.push.global_flag
  assert result.push.remote_name == 'upstream'
  assert result.push.force


def test_subcommand_inheritance_override():
  @subcommand
  class BaseCommand:
    flag: bool = argument('-f', '--flag', help='Base flag')
    value: str = argument('--value', default='base')

  @subcommand
  class ChildCommand(BaseCommand):
    # Override flag with different help but same functionality
    flag: bool = argument('-f', '--flag', help='Child flag')
    # Add a new argument
    extra: bool = argument('-e', '--extra')

  @app
  class App:
    base: BaseCommand
    child: ChildCommand

  # Test base command
  result = App.from_iter(['base', '-f'])
  assert result.base.flag
  assert result.base.value == 'base'

  # Test child command with overridden flag
  result = App.from_iter(['child', '-f'])
  assert result.child.flag
  assert result.child.value == 'base'
  assert not result.child.extra

  # Test child command with all flags
  result = App.from_iter(['child', '-f', '--value', 'custom', '-e'])
  assert result.child.flag
  assert result.child.value == 'custom'
  assert result.child.extra


def test_subcommand_inheritance_with_method():
  @subcommand
  class BaseCommand:
    verbose: bool = argument('-v', '--verbose')

    def get_verbosity(self):
      return 2 if self.verbose else 1

  @subcommand
  class StatusCommand(BaseCommand):
    all: bool = argument('-a', '--all')

    def get_status_mode(self):
      return 'full' if self.all else 'basic'

  @app
  class Git:
    status: StatusCommand

  # Test method from base class
  result = Git.from_iter(['status', '-v'])
  assert result.status.verbose
  assert result.status.get_verbosity() == 2

  # Test method from child class
  result = Git.from_iter(['status', '-a'])
  assert result.status.get_status_mode() == 'full'
  assert result.status.get_verbosity() == 1


def test_nested_subcommands_with_inheritance():
  @subcommand
  class BaseCommand:
    verbose: bool = argument('-v', '--verbose')

  @subcommand
  class PushCommand(BaseCommand):
    force: bool = argument('-f', '--force')

  @subcommand
  class Remote(BaseCommand):
    # Need to specify this as a field with None default
    push: t.Optional[PushCommand] = None
    name: str = argument('--name', default='origin')

  @app
  class Git:
    remote: Remote

  # Test command with inheritance
  result = Git.from_iter(['remote', '-v'])
  assert result.remote.verbose
  assert result.remote.name == 'origin'

  # For the nested subcommand, we need to check if it was properly initialized
  result = Git.from_iter(['remote', 'push', '-f'])
  assert result.remote.push is not None
  assert result.remote.push.force
  assert not result.remote.push.verbose


def test_nested_subcommands_no_default_value():
  @subcommand
  class BaseCommand:
    verbose: bool = argument('-v', '--verbose')

  @subcommand
  class PushCommand(BaseCommand):
    force: bool = argument('-f', '--force')

  @subcommand
  class Remote(BaseCommand):
    # No need to specify default=None anymore
    push: PushCommand
    name: str = argument('--name', default='origin')

  @app
  class Git:
    remote: Remote

  # Test command with inheritance
  result = Git.from_iter(['remote', '-v'])
  assert result.remote.verbose
  assert result.remote.name == 'origin'

  # For the nested subcommand, we need to check if it was properly initialized
  result = Git.from_iter(['remote', 'push', '-f'])
  assert result.remote.push is not None
  assert result.remote.push.force
  assert not result.remote.push.verbose


def test_subcommand_inheritance_with_properties():
  @subcommand
  class BaseCommand:
    verbose: bool = argument('-v', '--verbose', help='Show verbose output')

  @subcommand
  class StatusCommand(BaseCommand):
    all: bool = argument('-a', '--all')

  @app
  class Git:
    status: StatusCommand

  # Test property from base class
  result = Git.from_iter(['status', '-v'])
  assert result.status.verbose
  assert not result.status.all

  # Test field from child class
  result = Git.from_iter(['status', '-a'])
  assert not result.status.verbose
  assert result.status.all

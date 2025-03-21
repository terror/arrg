import argparse
import sys
import typing as t
from io import StringIO

import pytest

from arrg import app, argument, subcommand


def test_app_with_description(capsys):
  @app(description='Custom app description')
  class Arguments:
    name: str

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--help'])

  captured = capsys.readouterr()
  assert 'Custom app description' in captured.out


def test_app_with_epilog(capsys):
  @app(epilog='Custom epilog text')
  class Arguments:
    name: str

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--help'])

  captured = capsys.readouterr()
  assert 'Custom epilog text' in captured.out


def test_app_with_prog(capsys):
  @app(prog='custom-program')
  class Arguments:
    name: str

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--help'])

  captured = capsys.readouterr()
  assert 'usage: custom-program' in captured.out


def test_app_with_usage(capsys):
  @app(usage='custom usage: %(prog)s [options]')
  class Arguments:
    name: str

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--help'])

  captured = capsys.readouterr()
  assert 'custom usage:' in captured.out


def test_app_with_prefix_chars():
  @app(prefix_chars='+')
  class Arguments:
    name: str = argument('+name')

  result = Arguments.from_iter(['+name', 'test'])
  assert result.name == 'test'

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--name', 'test'])


def test_app_with_formatter_class(capsys):
  @app(formatter_class=argparse.RawDescriptionHelpFormatter, description='Line 1\nLine 2\nLine 3')
  class Arguments:
    name: str

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--help'])

  captured = capsys.readouterr()

  assert 'Line 1\nLine 2\nLine 3' in captured.out


def test_app_without_help():
  @app(add_help=False)
  class Arguments:
    name: str

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--help'])


def test_app_with_argument_default():
  @app(argument_default='DEFAULT')
  class Arguments:
    name: str = argument('--name')

  result = Arguments.from_iter([])
  assert result.name == 'DEFAULT'


def test_app_with_conflict_handler():
  @app(conflict_handler='resolve')
  class Arguments:
    value1: str = argument('-x')
    value2: str = argument('-x')

  result = Arguments.from_iter(['-x', 'test'])

  assert result.value2 == 'test'


def test_app_with_allow_abbrev():
  @app(allow_abbrev=False)
  class Arguments:
    verbose: bool = argument('--verbose', action='store_true')

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--ver'])


def test_all_app_parameters_together(capsys):
  @app(
    prog='test-prog',
    usage='custom usage',
    description='Test description',
    epilog='Test epilog',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    prefix_chars='-+',
    argument_default='DEFAULT',
    add_help=True,
    allow_abbrev=False,
    conflict_handler='resolve',
  )
  class Arguments:
    name: str = argument('--name')
    value: str = argument('+value')

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--help'])

  captured = capsys.readouterr()
  assert 'custom usage' in captured.out
  assert 'Test description' in captured.out
  assert 'Test epilog' in captured.out

  result = Arguments.from_iter(['+value', 'test'])
  assert result.value == 'test'

  result = Arguments.from_iter([])
  assert result.name == 'DEFAULT'


def test_exit_on_error(monkeypatch):
  if sys.version_info >= (3, 9):
    stderr_capture = StringIO()
    monkeypatch.setattr(sys, 'stderr', stderr_capture)

    @app(exit_on_error=False)
    class Arguments:
      required: str = argument('--required', required=True)

    with pytest.raises(argparse.ArgumentError):
      Arguments.from_iter([])

    @app
    class DefaultArguments:
      required: str = argument('--required', required=True)

    with pytest.raises(SystemExit):
      DefaultArguments.from_iter([])


def test_app_fromfile_prefix_chars(tmp_path):
  args_file = tmp_path / 'args.txt'
  args_file.write_text('--name\ntest_name\n--value\ntest_value')

  @app(fromfile_prefix_chars='@')
  class Arguments:
    name: str = argument('--name')
    value: str = argument('--value')

  result = Arguments.from_iter([f'@{args_file}'])
  assert result.name == 'test_name'
  assert result.value == 'test_value'


def test_app_parents():
  parent_parser = argparse.ArgumentParser(add_help=False)
  parent_parser.add_argument('--parent-arg', default='parent_default')

  @app(parents=[parent_parser])
  class Arguments:
    parent_arg: str
    child_arg: str = argument('--child-arg', default='child_default')

  result = Arguments.from_iter(['--parent-arg', 'parent_value', '--child-arg', 'child_value'])
  assert result.parent_arg == 'parent_value'
  assert result.child_arg == 'child_value'

  result = Arguments.from_iter([])
  assert result.parent_arg == 'parent_default'
  assert result.child_arg == 'child_default'


def test_app_combining_with_other_decorators():
  def add_method(cls):
    cls.additional_method = lambda _: True
    return cls

  @app
  @add_method
  class Arguments:
    input: str = argument()

  result = Arguments.from_iter(['test'])
  assert result.input == 'test'

  additional_method = getattr(result, 'additional_method', None)
  assert callable(additional_method)
  assert additional_method()


def test_positional_argument():
  @app
  class Arguments:
    input: str = argument()

  assert Arguments.from_iter(['test']).input == 'test'


def test_long_optional_argument():
  @app
  class Arguments:
    input: str = argument('--input')

  assert Arguments.from_iter(['--input', 'test']).input == 'test'


def test_short_optional_argument():
  @app
  class Arguments:
    input: str = argument('-i')

  assert Arguments.from_iter(['-i', 'test']).input == 'test'


def test_argument_name_defaults_to_field_name():
  @app
  class Arguments:
    name: str = argument()

  result = Arguments.from_iter(['hello'])
  assert result.name == 'hello'


def test_setting_default_values():
  @app
  class Arguments:
    name: str = argument('--name', default='default_name')
    count: int = argument('--count', type=int, default=42)
    verbose: bool = argument('--verbose', action='store_true', default=False)

  result = Arguments.from_iter([])
  assert result.name == 'default_name'
  assert result.count == 42
  assert not result.verbose

  result = Arguments.from_iter(['--name', 'custom', '--count', '10', '--verbose'])
  assert result.name == 'custom'
  assert result.count == 10
  assert result.verbose


def test_mixed_positional_and_optional_arguments():
  @app
  class Arguments:
    source: str = argument()
    destination: str = argument('--destination')
    recursive: bool = argument('-r', action='store_true')

  result = Arguments.from_iter(['src_dir', '--destination', 'dest_dir', '-r'])
  assert result.source == 'src_dir'
  assert result.destination == 'dest_dir'
  assert result.recursive


def test_list_type_argument():
  @app
  class Arguments:
    files: list[str] = argument('--files')

  result = Arguments.from_iter([])
  assert result.files is None

  result = Arguments.from_iter(['--files', 'a.txt', 'b.txt', 'c.txt'])
  assert result.files == ['a.txt', 'b.txt', 'c.txt']


def test_choices_argument():
  @app
  class Arguments:
    mode: str = argument('--mode', choices=['read', 'write', 'append'])

  result = Arguments.from_iter(['--mode', 'write'])
  assert result.mode == 'write'

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--mode', 'invalid'])


def test_required_argument():
  @app
  class Arguments:
    name: str = argument('--name', required=True)

  with pytest.raises(SystemExit):
    Arguments.from_iter([])


def test_command_line_arguments(monkeypatch):
  monkeypatch.setattr('sys.argv', ['script.py', 'test_input'])

  @app
  class Arguments:
    input: str = argument()

  result = Arguments.from_args()
  assert result.input == 'test_input'


def test_optional_type_argument():
  @app
  class Arguments:
    name: t.Optional[str] = argument('--name')
    count: t.Optional[int] = argument('--count')

  result = Arguments.from_iter(['--name', 'test', '--count', '5'])
  assert result.name == 'test'
  assert result.count == 5

  result = Arguments.from_iter([])
  assert result.name is None
  assert result.count is None


def test_custom_type_converter():
  def parse_key_value(arg: str) -> tuple:
    key, value = arg.split('=')
    return (key, value)

  @app
  class Arguments:
    config: tuple = argument('--config', type=parse_key_value)

  result = Arguments.from_iter(['--config', 'server=localhost'])
  assert result.config == ('server', 'localhost')


def test_nested_dataclass():
  from dataclasses import dataclass

  @dataclass
  class ServerConfig:
    host: str
    port: int

  def parse_server_config(arg: str) -> ServerConfig:
    host, port = arg.split(':')
    return ServerConfig(host, int(port))

  @app
  class Arguments:
    server: ServerConfig = argument('--server', type=parse_server_config)

  result = Arguments.from_iter(['--server', 'localhost:8080'])
  assert result.server.host == 'localhost'
  assert result.server.port == 8080


def test_invalid_argument_type_conversion():
  @app
  class Arguments:
    count: int = argument('--count', type=int)

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--count', 'not-an-int'])


def test_original_class_methods_get_preserved():
  @app
  class Arguments:
    count: int = argument('--count', type=int)

    def get_count(self):
      return self.count

    def double_count(self):
      return self.count * 2

  result = Arguments.from_iter(['--count', '5'])
  assert result.get_count() == 5
  assert result.double_count() == 10


def test_original_class_name_is_preserved():
  @app
  class CustomArguments:
    pass

  assert CustomArguments.__name__ == 'CustomArguments'


def test_app_inheritance():
  @app
  class A:
    a: str = argument('--a')

  @app
  class B(A):
    b: str = argument('--b')

  result = B.from_iter(['--a', 'a', '--b', 'b'])
  assert result.a == 'a'
  assert result.b == 'b'

  result = B.from_iter([])
  assert result.a is None
  assert result.b is None


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

  result = Git.from_iter(['status'])
  assert not result.status.verbose
  assert not result.status.quiet
  assert not result.status.all

  result = Git.from_iter(['status', '--verbose'])
  assert result.status.verbose
  assert not result.status.quiet
  assert not result.status.all

  result = Git.from_iter(['status', '--all'])
  assert not result.status.verbose
  assert not result.status.quiet
  assert result.status.all

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

  result = Git.from_iter(['push', '--global', '--name', 'upstream', '--force'])
  assert result.push.global_flag
  assert result.push.remote_name == 'upstream'
  assert result.push.force


def test_subcommand_inheritance_override(capsys):
  @subcommand
  class BaseCommand:
    flag: bool = argument('-f', '--flag', help='Base flag')
    value: str = argument('--value', default='base')

  @subcommand
  class ChildCommand(BaseCommand):
    flag: bool = argument('-f', '--flag', help='Child flag')
    extra: bool = argument('-e', '--extra')

  @app
  class App:
    base: BaseCommand
    child: ChildCommand

  result = App.from_iter(['base', '-f'])
  assert result.base.flag
  assert result.base.value == 'base'

  result = App.from_iter(['child', '-f'])
  assert result.child.flag
  assert result.child.value == 'base'
  assert not result.child.extra

  result = App.from_iter(['child', '-f', '--value', 'custom', '-e'])
  assert result.child.flag
  assert result.child.value == 'custom'
  assert result.child.extra

  with pytest.raises(SystemExit):
    App.from_iter(['child', '--help'])

  captured = capsys.readouterr()
  assert 'Base flag' in captured.out


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

  result = Git.from_iter(['status', '-v'])
  assert result.status.verbose
  assert result.status.get_verbosity() == 2

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
    name: str = argument('--name', default='origin')
    push: PushCommand

  @app
  class Git:
    remote: Remote

  result = Git.from_iter(['remote', '-v'])
  assert result.remote.verbose
  assert result.remote.name == 'origin'

  result = Git.from_iter(['remote', 'push', '-f'])
  assert result.remote.push is not None
  assert result.remote.push.force
  assert not result.remote.push.verbose


def test_app_inheritance_with_subcommands():
  @subcommand
  class C:
    c: str = argument('--c')

  @app
  class B:
    b: str = argument('--b')
    c: C

  @app
  class A(B):
    a: str = argument('--a')

  result = A.from_iter([])
  assert result.a is None
  assert result.b is None
  assert result.c is None

  result = A.from_iter(['--a', 'foo', '--b', 'bar', 'c', '--c', 'baz'])
  assert result.a == 'foo'
  assert result.b == 'bar'
  assert result.c.c == 'baz'


def test_app_inheritance_with_subcommand_inheritance():
  @subcommand
  class Base:
    v: bool = argument('-v')

  @subcommand
  class C(Base):
    d: str = argument('--d')

  @app
  class A:
    a: str = argument('--a')
    c: C

  @app
  class B(A):
    b: str = argument('--b')

  result = B.from_iter([])
  assert result.a is None
  assert result.b is None
  assert result.c is None

  result = B.from_iter(['--a', 'a', '--b', 'b', 'c', '--d', 'd', '-v'])
  assert result.a == 'a'
  assert result.b == 'b'
  assert result.c.d == 'd'
  assert result.c.v


def test_subcommand_with_parameters(capsys):
  @subcommand(
    description='Create a new pull request with specified parameters',
    help='Create a new pull request',
  )
  class PullRequest:
    title: str = argument('--title', help='Title of the pull request')
    base: str = argument('--base', default='main', help='Base branch')

  @app
  class Git:
    pr: PullRequest

  result = Git.from_iter(['pr', '--title', 'Fix bug'])
  assert result.pr.title == 'Fix bug'
  assert result.pr.base == 'main'

  result = Git.from_iter(['pr', '--title', 'Add feature'])
  assert result.pr.title == 'Add feature'

  with pytest.raises(SystemExit):
    Git.from_iter(['--help'])

  captured = capsys.readouterr()
  assert 'pr' in captured.out
  assert 'Create a new pull request' in captured.out

  with pytest.raises(SystemExit):
    Git.from_iter(['pr', '--help'])

  captured = capsys.readouterr()
  assert 'Create a new pull request with specified parameters' in captured.out
  assert '--title' in captured.out
  assert 'Title of the pull request' in captured.out


def test_union_int_str_type_conversion():
  @app
  class Arguments:
    input: t.Union[int, str] = argument()

  result = Arguments.from_iter(['1'])
  assert isinstance(result.input, int)
  assert result.input == 1

  result = Arguments.from_iter(['test'])
  assert isinstance(result.input, str)
  assert result.input == 'test'


def test_list_default_value():
  @app
  class Arguments:
    input: list[float] = argument('--input', default=[1.0, 2.0, 3.0])

  result = Arguments.from_iter([])
  assert isinstance(result.input, list)
  assert result.input == [1.0, 2.0, 3.0]

  result = Arguments.from_iter(['--input', '4.0', '5.0'])
  assert isinstance(result.input, list)
  assert result.input == [4.0, 5.0]

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

  # Should recognize + as a prefix
  result = Arguments.from_iter(['+name', 'test'])
  assert result.name == 'test'

  # Should not recognize - as a prefix
  with pytest.raises(SystemExit):
    Arguments.from_iter(['--name', 'test'])


def test_app_with_formatter_class(capsys):
  @app(formatter_class=argparse.RawDescriptionHelpFormatter, description='Line 1\nLine 2\nLine 3')
  class Arguments:
    name: str

  # Trigger help output
  with pytest.raises(SystemExit):
    Arguments.from_iter(['--help'])

  captured = capsys.readouterr()

  # `RawDescriptionHelpFormatter` preserves newlines
  assert 'Line 1\nLine 2\nLine 3' in captured.out


def test_app_without_help():
  @app(add_help=False)
  class Arguments:
    name: str

  # Should not recognize --help
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


def test_app_inheritance_with_subcommands():
  @subcommand
  class C:
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

  result = B.from_iter(['--a', 'a', '--b', 'b', 'c', '--d', 'd'])
  assert result.a == 'a'
  assert result.b == 'b'
  assert result.c.d == 'd'

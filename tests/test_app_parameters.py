import argparse
import sys
from io import StringIO

import pytest

from arrg import app, argument


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
    # count: int = argument('--count', type=int)

  # Arguments should default to "DEFAULT"
  result = Arguments.from_iter([])
  assert result.name == 'DEFAULT'

  # n.b. This should type convert
  #
  # assert result.count == 0


def test_app_with_conflict_handler():
  @app(conflict_handler='resolve')
  class Arguments:
    # Define the same argument twice, but with different destinations
    # With 'resolve', the second one should override the first
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


def test_all_parameters_together(capsys):
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


def test_fromfile_prefix_chars(tmp_path):
  args_file = tmp_path / 'args.txt'
  args_file.write_text('--name\ntest_name\n--value\ntest_value')

  @app(fromfile_prefix_chars='@')
  class Arguments:
    name: str = argument('--name')
    value: str = argument('--value')

  result = Arguments.from_iter([f'@{args_file}'])
  assert result.name == 'test_name'
  assert result.value == 'test_value'


def test_parents():
  parent_parser = argparse.ArgumentParser(add_help=False)
  parent_parser.add_argument('--parent-arg', default='parent_default')

  @app(parents=[parent_parser])
  class Arguments:
    parent_arg: str
    child_arg: str = argument('--child-arg', default='child_default')

  # Should recognize arguments from both parsers
  result = Arguments.from_iter(['--parent-arg', 'parent_value', '--child-arg', 'child_value'])
  assert result.parent_arg == 'parent_value'
  assert result.child_arg == 'child_value'

  # Parent defaults should work
  result = Arguments.from_iter([])
  assert result.parent_arg == 'parent_default'
  assert result.child_arg == 'child_default'

import pytest

from arrg import app, option


def test_positional():
  @app
  class Arguments:
    input: str

  assert Arguments.from_iter(['test']).input == 'test'


def test_long_bool():
  @app
  class Arguments:
    input: str = option(long=True)

  assert Arguments.from_iter(['--input', 'test']).input == 'test'


def test_long_str():
  @app
  class Arguments:
    input: str = option(long='long_input')

  assert Arguments.from_iter(['--long_input', 'test']).input == 'test'


def test_short_bool():
  @app
  class Arguments:
    input: str = option(short=True)

  assert Arguments.from_iter(['-i', 'test']).input == 'test'


def test_short_str():
  @app
  class Arguments:
    input: str = option(short='i')

  assert Arguments.from_iter(['-i', 'test']).input == 'test'


def test_default_value():
  @app
  class Arguments:
    name: str = option(long=True, default_value='default_name')
    count: int = option(long=True, default_value=42)
    verbose: bool = option(long=True, default_value=False)

  result = Arguments.from_iter([])
  assert result.name == 'default_name'
  assert result.count == 42
  assert not result.verbose

  result = Arguments.from_iter(['--name', 'custom', '--count', '10', '--verbose'])
  assert result.name == 'custom'
  assert result.count == 10
  assert result.verbose


def test_multiple_options():
  @app
  class Arguments:
    input: str = option(short='i', long='input-file')
    output: str = option(short='o', long='output-file')
    verbose: bool = option(short=True, long=True)

  result = Arguments.from_iter(['-i', 'input.txt', '-o', 'output.txt', '--verbose'])
  assert result.input == 'input.txt'
  assert result.output == 'output.txt'
  assert result.verbose


def test_mixed_positional_and_options():
  @app
  class Arguments:
    source: str  # positional
    destination: str = option(long=True)
    recursive: bool = option(short='r')

  result = Arguments.from_iter(['src_dir', '--destination', 'dest_dir', '-r'])
  assert result.source == 'src_dir'
  assert result.destination == 'dest_dir'
  assert result.recursive


def test_list_type_option():
  @app
  class Arguments:
    files: list[str] = option(long=True, nargs='+')

  result = Arguments.from_iter(['--files', 'file1.txt', 'file2.txt', 'file3.txt'])
  assert result.files == ['file1.txt', 'file2.txt', 'file3.txt']


def test_choices_option():
  @app
  class Arguments:
    mode: str = option(long=True, choices=['read', 'write', 'append'])

  result = Arguments.from_iter(['--mode', 'write'])
  assert result.mode == 'write'

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--mode', 'invalid'])


def test_required_option():
  @app
  class Arguments:
    name: str = option(long=True, required=True)

  with pytest.raises(SystemExit):
    Arguments.from_iter([])


def test_command_line_args(capsys, monkeypatch):
  monkeypatch.setattr('sys.argv', ['script.py', 'test_input'])

  @app
  class Arguments:
    input: str

  result = Arguments.from_args()
  assert result.input == 'test_input'

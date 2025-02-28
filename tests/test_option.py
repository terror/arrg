import typing as t

import pytest

from arrg import app, option


def test_positional():
  @app
  class Arguments:
    input: str

  assert Arguments.from_iter(['test']).input == 'test'


def test_long_option():
  @app
  class Arguments:
    input: str = option('--input')

  assert Arguments.from_iter(['--input', 'test']).input == 'test'


def test_short_option():
  @app
  class Arguments:
    input: str = option('-i')

  assert Arguments.from_iter(['-i', 'test']).input == 'test'


def test_default_values():
  @app
  class Arguments:
    name: str = option('--name', default='default_name')
    count: int = option('--count', type=int, default=42)
    verbose: bool = option('--verbose', action='store_true', default=False)

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
    input: str = option('-i', '--input-file')
    output: str = option('-o', '--output-file')
    verbose: bool = option('-v', '--verbose', action='store_true')

  result = Arguments.from_iter(['-i', 'input.txt', '-o', 'output.txt', '--verbose'])

  assert result.input == 'input.txt'
  assert result.output == 'output.txt'
  assert result.verbose


def test_mixed_positional_and_options():
  @app
  class Arguments:
    source: str  # positional
    destination: str = option('--destination')
    recursive: bool = option('-r', action='store_true')

  result = Arguments.from_iter(['src_dir', '--destination', 'dest_dir', '-r'])

  assert result.source == 'src_dir'
  assert result.destination == 'dest_dir'
  assert result.recursive


def test_list_type_option():
  @app
  class Arguments:
    files: list[str] = option('--files')

  result = Arguments.from_iter(['--files', 'file1.txt', 'file2.txt', 'file3.txt'])

  assert result.files == ['file1.txt', 'file2.txt', 'file3.txt']


def test_choices_option():
  @app
  class Arguments:
    mode: str = option('--mode', choices=['read', 'write', 'append'])

  result = Arguments.from_iter(['--mode', 'write'])

  assert result.mode == 'write'

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--mode', 'invalid'])


def test_required_option():
  @app
  class Arguments:
    name: str = option('--name', required=True)

  with pytest.raises(SystemExit):
    Arguments.from_iter([])


def test_command_line_args(monkeypatch):
  monkeypatch.setattr('sys.argv', ['script.py', 'test_input'])

  @app
  class Arguments:
    input: str

  result = Arguments.from_args()

  assert result.input == 'test_input'


def test_optional_type():
  @app
  class Arguments:
    name: t.Optional[str] = option('--name')
    count: t.Optional[int] = option('--count', type=int)

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
    config: tuple = option('--config', type=parse_key_value)

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
    server: ServerConfig = option('--server', type=parse_server_config)

  result = Arguments.from_iter(['--server', 'localhost:8080'])

  assert result.server.host == 'localhost'
  assert result.server.port == 8080


def test_invalid_type_conversion():
  @app
  class Arguments:
    count: int = option('--count', type=int)

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--count', 'not-an-int'])


def test_methods_get_preserved():
  @app
  class Arguments:
    count: int = option('--count', type=int)

    def get_count(self):
      return self.count

  assert Arguments.from_iter(['--count', '5']).get_count() == 5


def test_class_name_is_preserved():
  @app
  class CustomArguments:
    pass

  assert CustomArguments.__name__ == 'CustomArguments'

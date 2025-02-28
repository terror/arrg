import typing as t

import pytest

from arrg import app, argument


def test_positional():
  @app
  class Arguments:
    input: str

  assert Arguments.from_iter(['test']).input == 'test'


def test_long_argument():
  @app
  class Arguments:
    input: str = argument('--input')

  assert Arguments.from_iter(['--input', 'test']).input == 'test'


def test_short_argument():
  @app
  class Arguments:
    input: str = argument('-i')

  assert Arguments.from_iter(['-i', 'test']).input == 'test'


def test_argument_name_defaults_to_field_name():
  @app
  class Arguments:
    name: str = argument()  # This is positional.

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


def test_multiple_arguments():
  @app
  class Arguments:
    input: str = argument('-i', '--input-file')
    output: str = argument('-o', '--output-file')
    verbose: bool = argument('-v', '--verbose', action='store_true')

  result = Arguments.from_iter(['-i', 'input.txt', '-o', 'output.txt', '--verbose'])
  assert result.input == 'input.txt'
  assert result.output == 'output.txt'
  assert result.verbose


def test_mixed_positional_and_arguments():
  @app
  class Arguments:
    source: str  # positional
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
  assert result.files == []

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
    name: t.Optional[str] = argument('--name')
    count: t.Optional[int] = argument('--count', type=int)

  result = Arguments.from_iter(['--name', 'test', '--count', '5'])
  assert result.name == 'test'
  assert result.count == 5

  result = Arguments.from_iter([])
  assert result.name == ''
  assert result.count == 0


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


def test_invalid_type_conversion():
  @app
  class Arguments:
    count: int = argument('--count', type=int)

  with pytest.raises(SystemExit):
    Arguments.from_iter(['--count', 'not-an-int'])


def test_methods_get_preserved():
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


def test_class_name_is_preserved():
  @app
  class CustomArguments:
    pass

  assert CustomArguments.__name__ == 'CustomArguments'


def test_at_property_decorators():
  @app
  class Arguments:
    @property
    def count(self):
      return argument('--count', '-c', type=int, default=42)

  assert Arguments.from_iter(['--count', '5']).count == 5


def test_property_with_default():
  @app
  class Arguments:
    @property
    def verbose(self):
      return argument('--verbose', action='store_true', default=False)

  result = Arguments.from_iter([])
  assert not result.verbose

  result = Arguments.from_iter(['--verbose'])
  assert result.verbose


def test_multiple_properties():
  @app
  class Arguments:
    @property
    def input(self):
      return argument('-i', '--input', default='default.txt')

    @property
    def count(self) -> int:
      return argument('-c', '--count', default=1)

    @property
    def verbose(
      self,
    ) -> bool:  # Because we set this type annotation here, we default the action to `store_true`.
      return argument('-v', '--verbose')

  result = Arguments.from_iter(['-i', 'test.txt', '-c', '10', '-v'])
  assert result.input == 'test.txt'
  assert result.count == 10
  assert result.verbose


def test_methods_with_properties():
  @app
  class Arguments:
    @property
    def count(self) -> int:
      return argument('--count', type=int, default=1)

    def double_count(self):
      return self.count * 2

    def triple_count(self):
      return self.count * 3

  result = Arguments.from_iter(['--count', '5'])
  assert result.count == 5
  assert result.double_count() == 10
  assert result.triple_count() == 15


def test_mixed_arguments():
  @app
  class Arguments:
    input: str
    count: int = argument('--count', default=0)

    @property
    def multiplier(self) -> int:
      return argument('--multiplier', default=1)

    def value(self):
      return self.count * self.multiplier

  result = Arguments.from_iter(['foo', '--count', '5', '--multiplier', '2'])
  assert result.input == 'foo'
  assert result.value() == 10


def test_infer_default_value_for_int():
  @app
  class Arguments:
    input: int = argument('--input')

  result = Arguments.from_iter([])
  assert result.input == 0


def test_infer_default_value_for_str():
  @app
  class Arguments:
    input: str = argument('--input')

  result = Arguments.from_iter([])
  assert result.input == ''


def test_infer_default_value_for_float():
  @app
  class Arguments:
    input: float = argument('--input')

  result = Arguments.from_iter([])
  assert result.input == 0.0


def test_infer_default_value_for_bool():
  @app
  class Arguments:
    input: bool = argument('--input')

  result = Arguments.from_iter([])
  assert not result.input


def test_infer_default_value_for_list():
  @app
  class Arguments:
    input: list = argument('--input')

  result = Arguments.from_iter([])
  assert result.input == []


def test_combining_with_other_decorators():
  def add_method(cls):
    cls.additional_method = lambda _: True
    return cls

  @app
  @add_method
  class Arguments:
    input: str

  result = Arguments.from_iter(['test'])
  assert result.input == 'test'

  additional_method = getattr(result, 'additional_method', None)
  assert callable(additional_method)
  assert additional_method()


def test_positional_union_type_conversion_int_str():
  @app
  class Arguments:
    input: t.Union[int, str]

  result = Arguments.from_iter(['1'])
  assert isinstance(result.input, int)
  assert result.input == 1

  result = Arguments.from_iter(['test'])
  assert isinstance(result.input, str)
  assert result.input == 'test'


def test_optional_union_type_conversion_int_str():
  @app
  class Arguments:
    input: t.Union[int, str] = argument('--input')

  result = Arguments.from_iter(['--input', '1'])
  assert isinstance(result.input, int)
  assert result.input == 1

  result = Arguments.from_iter(['--input', 'test'])
  assert isinstance(result.input, str)
  assert result.input == 'test'

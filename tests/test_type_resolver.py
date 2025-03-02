import typing as t

from arrg.type_resolver import (
  _create_union_converter,
  _resolve_bool_from_string,
  _resolve_list_type,
  _resolve_union_type,
  resolve_type,
)


class TestResolveBoolFromString:
  def test_true_values(self):
    for value in ('true', 'True', 'TRUE', 't', 'yes', 'y', '1'):
      assert _resolve_bool_from_string(value) is True

  def test_false_values(self):
    for value in ('false', 'False', 'FALSE', 'f', 'no', 'n', '0'):
      assert _resolve_bool_from_string(value) is False

  def test_invalid_values(self):
    for value in ('not_a_bool', '2', 'maybe'):
      assert _resolve_bool_from_string(value) is None


class TestCreateUnionConverter:
  def test_int_str_conversion(self):
    converter = _create_union_converter([int, str])

    assert converter('42') == 42
    assert isinstance(converter('42'), int)

    assert converter('hello') == 'hello'
    assert isinstance(converter('hello'), str)

  def test_bool_int_str_conversion(self):
    converter = _create_union_converter([bool, int, str])

    assert converter('true') is True
    assert converter('false') is False
    assert converter('42') == 42
    assert converter('hello') == 'hello'

  def test_fallback_to_string(self):
    class NonConvertible:
      pass

    converter = _create_union_converter([NonConvertible])
    assert converter('test') == 'test'


class TestResolveListType:
  def test_typed_list(self):
    resolver = _resolve_list_type(t.List[int])
    assert resolver('42') == 42
    assert isinstance(resolver('42'), int)

  def test_untyped_list(self):
    resolver = _resolve_list_type(t.List[t.Any])
    assert resolver('42') == '42'
    assert isinstance(resolver('42'), str)

  def test_nested_list(self):
    resolver = _resolve_list_type(t.List[t.List[int]])
    assert resolver('42') == 42


class TestResolveUnionType:
  def test_optional_type(self):
    resolver = _resolve_union_type(t.Optional[int])
    assert resolver('42') == 42
    assert isinstance(resolver('42'), int)

  def test_union_of_primitives(self):
    resolver = _resolve_union_type(t.Union[int, str])

    assert resolver('42') == 42
    assert resolver('hello') == 'hello'

  def test_empty_union(self):
    resolver = _resolve_union_type(t.Union[t.Any])
    assert resolver('test') == 'test'
    assert isinstance(resolver('test'), str)

  def test_none_only_union(self):
    resolver = _resolve_union_type(t.Union[type(None)])
    assert resolver('test') == 'test'


class TestResolveType:
  def test_primitive_types(self):
    assert resolve_type(bool)('true') is True
    assert resolve_type(int)('42') == 42
    assert resolve_type(float)('3.14') == 3.14
    assert resolve_type(str)('hello') == 'hello'

  def test_list_types(self):
    list_converter = resolve_type(t.List[int])
    assert list_converter('42') == 42

  def test_union_types(self):
    union_converter = resolve_type(t.Union[int, str])
    assert union_converter('42') == 42
    assert union_converter('hello') == 'hello'

  def test_class_types(self):
    class CustomType:
      def __init__(self, value):
        self.value = value

    assert resolve_type(CustomType) is CustomType


class TestIntegration:
  def test_real_world_scenario(self):
    from arrg import app, argument

    @app
    class Arguments:
      pos_arg: str = argument()
      int_arg: int = argument('--int-arg')
      float_arg: float = argument('--float-arg')
      bool_arg: bool = argument('--bool-arg')
      list_arg: t.List[str] = argument('--list-arg')
      opt_arg: t.Optional[int] = argument('--opt-arg')
      union_arg: t.Union[int, str] = argument('--union-arg')

    result = Arguments.from_iter(
      [
        'positional',
        '--int-arg',
        '42',
        '--float-arg',
        '3.14',
        '--bool-arg',
        '--list-arg',
        'a',
        'b',
        'c',
        '--opt-arg',
        '100',
        '--union-arg',
        'string_val',
      ]
    )

    assert result.pos_arg == 'positional'
    assert result.int_arg == 42
    assert result.float_arg == 3.14
    assert result.bool_arg is True
    assert result.list_arg == ['a', 'b', 'c']
    assert result.opt_arg == 100
    assert result.union_arg == 'string_val'

    result = Arguments.from_iter(['positional', '--union-arg', '123'])
    assert result.union_arg == 123
    assert isinstance(result.union_arg, int)

  def test_inferred_default_values(self):
    from arrg import app, argument

    @app
    class Arguments:
      int_arg: int = argument('--int-arg')
      float_arg: float = argument('--float-arg')
      bool_arg: bool = argument('--bool-arg')
      str_arg: str = argument('--str-arg')
      list_arg: t.List[str] = argument('--list-arg')
      opt_arg: t.Optional[int] = argument('--opt-arg')

    result = Arguments.from_iter([])

    assert result.int_arg is None
    assert result.float_arg is None
    assert result.bool_arg is False
    assert result.str_arg is None
    assert result.list_arg is None
    assert result.opt_arg is None

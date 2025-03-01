import typing as t
from dataclasses import dataclass

from arrg.utils import (
  _create_union_converter,
  _resolve_bool_from_string,
  _resolve_list_type,
  _resolve_union_type,
  infer_default_value,
  resolve_type,
)


class TestInferDefaultValue:
  def test_primitive_types(self):
    assert infer_default_value(bool) is False
    assert infer_default_value(int) == 0
    assert infer_default_value(float) == 0.0
    assert infer_default_value(str) == ''

  def test_collection_types(self):
    assert infer_default_value(list) == []
    assert infer_default_value(t.List[int]) == []
    assert infer_default_value(tuple) == ()

  def test_union_types(self):
    assert infer_default_value(t.Union[int, str]) is None  # TODO: Should this be 0?
    assert infer_default_value(t.Optional[str]) == ''

  def test_custom_types(self):
    @dataclass
    class CustomType:
      value: int = 0

    assert infer_default_value(CustomType) is None


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

    # Should convert to int when possible
    assert converter('42') == 42
    assert isinstance(converter('42'), int)

    # Should leave as str when not an int
    assert converter('hello') == 'hello'
    assert isinstance(converter('hello'), str)

  def test_bool_int_str_conversion(self):
    converter = _create_union_converter([bool, int, str])

    # Should convert to bool for boolean strings
    assert converter('true') is True
    assert converter('false') is False

    # Should convert to int when possible
    assert converter('42') == 42

    # Should leave as str for other values
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

    # Should convert to int when possible
    assert resolver('42') == 42

    # Should leave as str when not an int
    assert resolver('hello') == 'hello'

  def test_empty_union(self):
    # This is an edge case, but should return a string converter
    resolver = _resolve_union_type(t.Union[t.Any])
    assert resolver('test') == 'test'
    assert isinstance(resolver('test'), str)

  def test_none_only_union(self):
    # Another edge case, should return a string converter
    resolver = _resolve_union_type(t.Union[type(None)])
    assert resolver('test') == 'test'


class TestResolveType:
  def test_primitive_types(self):
    assert resolve_type(bool)('true') is True
    assert resolve_type(int)('42') == 42
    assert resolve_type(float)('3.14') == 3.14
    assert resolve_type(str)('hello') == 'hello'

  def test_list_types(self):
    # For a List[int], values should be converted to int
    list_converter = resolve_type(t.List[int])
    assert list_converter('42') == 42

  def test_union_types(self):
    # For a Union[int, str], values should be converted to int when possible
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

    assert result.int_arg == 0
    assert result.float_arg == 0.0
    assert result.bool_arg is False
    assert result.str_arg == ''
    assert result.list_arg == []
    assert result.opt_arg == 0

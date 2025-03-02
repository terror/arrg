import datetime
import ipaddress
import pathlib
import re
import typing as t
import uuid
from decimal import Decimal
from enum import Enum, auto

import pytest

from arrg.type_resolver import TypeResolver


class Color(Enum):
  RED = 'red'
  GREEN = 'green'
  BLUE = 'blue'


class Status(Enum):
  PENDING = 1
  ACTIVE = 2
  COMPLETED = 3


class AutoEnum(Enum):
  ONE = auto()
  TWO = auto()
  THREE = auto()


def test_bool_conversion():
  resolver = TypeResolver.resolve(bool)

  assert resolver('') is False
  assert resolver('true') is True
  assert resolver(0) is False
  assert resolver(1) is True
  assert resolver(False) is False
  assert resolver(True) is True


def test_int_conversion():
  resolver = TypeResolver.resolve(int)

  assert resolver('42') == 42
  assert resolver('-100') == -100

  with pytest.raises(ValueError):
    resolver('not_an_int')


def test_float_conversion():
  resolver = TypeResolver.resolve(float)

  assert resolver('3.14') == 3.14
  assert resolver('-2.5') == -2.5

  with pytest.raises(ValueError):
    resolver('not_a_float')


def test_str_conversion():
  resolver = TypeResolver.resolve(str)

  assert resolver('hello') == 'hello'
  assert resolver('42') == '42'


def test_uuid_conversion():
  resolver = TypeResolver.resolve(uuid.UUID)

  uuid_str = '550e8400-e29b-41d4-a716-446655440000'

  assert resolver(uuid_str) == uuid.UUID(uuid_str)

  with pytest.raises(ValueError):
    resolver('not_a_uuid')


def test_date_conversion():
  resolver = TypeResolver.resolve(datetime.date)

  assert resolver('2023-01-15') == datetime.date(2023, 1, 15)

  with pytest.raises(ValueError):
    resolver('not_a_date')


def test_time_conversion():
  resolver = TypeResolver.resolve(datetime.time)

  assert resolver('12:30:45') == datetime.time(12, 30, 45)

  with pytest.raises(ValueError):
    resolver('not_a_time')


def test_path_conversion():
  resolver = TypeResolver.resolve(pathlib.Path)

  assert resolver('/tmp/file.txt') == pathlib.Path('/tmp/file.txt')


def test_ipv4_conversion():
  resolver = TypeResolver.resolve(ipaddress.IPv4Address)

  assert resolver('192.168.1.1') == ipaddress.IPv4Address('192.168.1.1')

  with pytest.raises(ValueError):
    resolver('not_an_ip')


def test_ipv6_conversion():
  resolver = TypeResolver.resolve(ipaddress.IPv6Address)

  assert resolver('::1') == ipaddress.IPv6Address('::1')

  with pytest.raises(ValueError):
    resolver('not_an_ip')


def test_regex_pattern_conversion():
  resolver = TypeResolver.resolve(re.Pattern)

  pattern = resolver(r'\d+')

  assert isinstance(pattern, re.Pattern)
  assert pattern.match('123')
  assert not pattern.match('abc')


def test_list_type():
  resolver = TypeResolver.resolve(t.List[int])

  assert resolver('42') == 42

  with pytest.raises(ValueError):
    resolver('not_an_int')


def test_list_with_complex_type():
  resolver = TypeResolver.resolve(t.List[datetime.date])
  assert resolver('2023-01-15') == datetime.date(2023, 1, 15)


def test_dict_type():
  resolver = TypeResolver.resolve(t.Dict[str, int])
  assert resolver('answer=42') == {'answer': 42}

  with pytest.raises(ValueError):
    resolver('answer=not_an_int')


def test_dict_with_complex_types():
  resolver = TypeResolver.resolve(t.Dict[str, datetime.date])
  assert resolver('date=2023-01-15') == {'date': datetime.date(2023, 1, 15)}


def test_set_type():
  resolver = TypeResolver.resolve(t.Set[int])
  assert resolver('42') == 42


def test_tuple_type():
  resolver = TypeResolver.resolve(t.Tuple[str, int, float])
  assert resolver('name,42,3.14') == ('name', 42, 3.14)

  with pytest.raises(ValueError):
    resolver('name,not_an_int,3.14')

  with pytest.raises(ValueError):
    resolver('only_one_value')


def test_optional_int():
  resolver = TypeResolver.resolve(t.Optional[int])
  assert resolver('42') == 42
  assert resolver(None) is None

  with pytest.raises(ValueError):
    resolver('not_an_int')


def test_int_or_str():
  resolver = TypeResolver.resolve(t.Union[int, str])

  assert resolver('42') == 42
  assert isinstance(resolver('42'), int)

  assert resolver('hello') == 'hello'
  assert isinstance(resolver('hello'), str)


def test_complex_union():
  resolver = TypeResolver.resolve(t.Union[int, float, datetime.date, str])

  assert resolver('42') == 42
  assert isinstance(resolver('42'), int)

  assert resolver('3.14') == 3.14
  assert isinstance(resolver('3.14'), float)

  assert resolver('2023-01-15') == datetime.date(2023, 1, 15)
  assert isinstance(resolver('2023-01-15'), datetime.date)

  assert resolver('hello') == 'hello'
  assert isinstance(resolver('hello'), str)


def test_literal_strings():
  resolver = TypeResolver.resolve(t.Literal['red', 'green', 'blue'])

  assert resolver('red') == 'red'
  assert resolver('green') == 'green'
  assert resolver('blue') == 'blue'

  with pytest.raises(ValueError):
    resolver('yellow')


def test_enum_by_name():
  resolver = TypeResolver.resolve(Color)

  assert resolver('RED') == Color.RED
  assert resolver('GREEN') == Color.GREEN
  assert resolver('BLUE') == Color.BLUE

  with pytest.raises(ValueError):
    resolver('YELLOW')


def test_enum_by_value():
  resolver = TypeResolver.resolve(Status)

  assert resolver('1') == Status.PENDING
  assert resolver('2') == Status.ACTIVE
  assert resolver('3') == Status.COMPLETED

  with pytest.raises(ValueError):
    resolver('4')


def test_auto_enum():
  resolver = TypeResolver.resolve(AutoEnum)

  assert resolver('ONE') == AutoEnum.ONE
  assert resolver('TWO') == AutoEnum.TWO
  assert resolver('THREE') == AutoEnum.THREE

  with pytest.raises(ValueError):
    resolver('FOUR')


def test_all():
  test_types = [
    str,
    int,
    float,
    bool,
    datetime.date,
    uuid.UUID,
    pathlib.Path,
    t.List[str],
    t.Dict[str, int],
    t.Union[int, str],
    t.Optional[int],
    Color,
    Status,
    t.Literal['read', 'write', 'append'],
  ]

  for field_type in test_types:
    resolver = TypeResolver.resolve(field_type)
    assert callable(resolver), f'Failed to get resolver for {field_type}'


def test_union_bool_int():
  resolver = TypeResolver.resolve(t.Union[bool, int])

  assert resolver('true') is True
  assert resolver('false') is False
  assert resolver('yes') is True
  assert resolver('no') is False
  assert resolver('42') == 42
  assert resolver('-10') == -10
  assert resolver('1') is True  # '1' is a valid bool string, so it should convert to True
  assert resolver('0') is False  # '0' is a valid bool string, so it should convert to False


def test_union_int_bool():
  resolver = TypeResolver.resolve(t.Union[int, bool])

  assert resolver('42') == 42
  assert resolver('-10') == -10

  assert resolver('1') == 1
  assert resolver('0') == 0

  assert resolver('true') is True
  assert resolver('false') is False


def test_union_float_int_str():
  resolver = TypeResolver.resolve(t.Union[float, int, str])

  assert resolver('3.14') == 3.14
  assert isinstance(resolver('3.14'), float)

  assert resolver('42') == 42.0
  assert isinstance(resolver('42'), float)

  assert resolver('hello') == 'hello'
  assert isinstance(resolver('hello'), str)


def test_union_with_none():
  resolver = TypeResolver.resolve(t.Union[int, None])

  assert resolver('42') == 42
  assert resolver(None) is None


def test_union_with_enum():
  resolver = TypeResolver.resolve(t.Union[Color, int])

  assert resolver('RED') == Color.RED
  assert resolver('42') == 42
  assert resolver('1') == 1  # Not a valid Color name


def test_union_nested():
  inner_union = t.Union[int, float]
  resolver = TypeResolver.resolve(t.Union[inner_union, str])

  assert resolver('42') == 42
  assert isinstance(resolver('42'), int)

  assert resolver('3.14') == 3.14
  assert isinstance(resolver('3.14'), float)

  assert resolver('hello') == 'hello'
  assert isinstance(resolver('hello'), str)


def test_union_with_numeric_types():
  resolver = TypeResolver.resolve(t.Union[int, float, Decimal, str])

  assert resolver('42') == 42
  assert isinstance(resolver('42'), int)

  assert resolver('3.14') == 3.14
  assert isinstance(resolver('3.14'), float)

  assert resolver('hello') == 'hello'
  assert isinstance(resolver('hello'), str)


def test_union_with_path_and_str():
  resolver = TypeResolver.resolve(t.Union[pathlib.Path, str])

  result = resolver('/tmp/file.txt')
  assert isinstance(result, pathlib.Path)
  assert result == pathlib.Path('/tmp/file.txt')

  result = resolver('hello')
  assert isinstance(result, pathlib.Path)
  assert result == pathlib.Path('hello')


def test_union_with_str_and_path():
  resolver = TypeResolver.resolve(t.Union[str, pathlib.Path])

  result = resolver('/tmp/file.txt')
  assert isinstance(result, str)
  assert result == '/tmp/file.txt'

  result = resolver('hello')
  assert isinstance(result, str)
  assert result == 'hello'


def test_union_with_ip_addresses():
  resolver = TypeResolver.resolve(t.Union[ipaddress.IPv4Address, ipaddress.IPv6Address, str])

  assert resolver('192.168.1.1') == ipaddress.IPv4Address('192.168.1.1')
  assert resolver('::1') == ipaddress.IPv6Address('::1')
  assert resolver('hello') == 'hello'

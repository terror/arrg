import datetime
import ipaddress
import pathlib
import re
import typing as t
import uuid
from enum import Enum

T = t.TypeVar('T')


class TypeResolver:
  PRIMITIVE_TYPES = {
    bool: bool,
    int: int,
    float: float,
    str: str,
    tuple: tuple,
    uuid.UUID: uuid.UUID,
    datetime.date: lambda s: datetime.date.fromisoformat(s),
    datetime.datetime: lambda s: datetime.datetime.fromisoformat(s.replace('T', ' ')),
    datetime.time: lambda s: datetime.time.fromisoformat(s),
    pathlib.Path: pathlib.Path,
    ipaddress.IPv4Address: ipaddress.IPv4Address,
    ipaddress.IPv6Address: ipaddress.IPv6Address,
    re.Pattern: re.compile,
  }

  BOOL_TRUE_VALUES = ('true', 't', 'yes', 'y', '1')
  BOOL_FALSE_VALUES = ('false', 'f', 'no', 'n', '0')

  @classmethod
  def resolve(cls, field_type: t.Any) -> t.Callable[[t.Any], t.Any]:
    origin = t.get_origin(field_type)

    if origin is list or origin is t.List:
      return cls._resolve_list_type(field_type)

    if origin is dict or origin is t.Dict:
      return cls._resolve_dict_type(field_type)

    if origin is set or origin is t.Set:
      return cls._resolve_set_type(field_type)

    if origin is tuple or origin is t.Tuple:
      return cls._resolve_tuple_type(field_type)

    if origin is t.Union or origin is t.Optional:
      return cls._resolve_union_type(field_type)

    if origin is t.Literal:
      return cls._resolve_literal_type(field_type)

    if isinstance(field_type, type) and issubclass(field_type, Enum):
      return cls._create_enum_converter(field_type)

    if isinstance(field_type, type):
      for primitive_type, converter in cls.PRIMITIVE_TYPES.items():
        if issubclass(field_type, primitive_type):
          return converter

    return str

  @classmethod
  def _resolve_bool_from_string(cls, value: t.Optional[str]) -> t.Optional[bool]:
    if isinstance(value, str) and value.lower() in cls.BOOL_TRUE_VALUES:
      return True

    if isinstance(value, str) and value.lower() in cls.BOOL_FALSE_VALUES:
      return False

    return None

  @classmethod
  def _create_union_converter(cls, types: t.List[t.Type]) -> t.Callable[[t.Any], t.Any]:
    def union_converter(value: t.Any) -> t.Any:
      if bool in types:
        bool_result = cls._resolve_bool_from_string(value)
        if bool_result is not None:
          return bool_result

      for arg_type in types:
        try:
          if arg_type is type(None):
            continue

          if arg_type is bool:
            bool_result = cls._resolve_bool_from_string(value)

            if bool_result is not None:
              return bool_result

            continue

          if isinstance(arg_type, type) and issubclass(arg_type, Enum):
            try:
              return arg_type[value]
            except KeyError:
              try:
                return arg_type(value)
              except (ValueError, TypeError):
                continue

          converter = cls.resolve(arg_type)

          return converter(value)
        except (ValueError, TypeError):
          continue

      return str(value)

    return union_converter

  @classmethod
  def _resolve_list_type(cls, field_type: t.Any) -> t.Callable[[t.Any], t.Any]:
    args = t.get_args(field_type)

    if args and args[0] != t.Any:
      element_converter = cls.resolve(args[0])
      return element_converter

    return str

  @classmethod
  def _resolve_dict_type(cls, field_type: t.Any) -> t.Callable[[str], t.Dict]:
    args = t.get_args(field_type)

    if len(args) >= 2:
      key_type, value_type = args[0], args[1]
      key_converter = cls.resolve(key_type)
      value_converter = cls.resolve(value_type)

      def dict_converter(s: str) -> t.Dict:
        key, value = s.split('=', 1)
        return {key_converter(key): value_converter(value)}

      return dict_converter

    def default_dict_converter(s: str) -> t.Dict:
      key, value = s.split('=', 1)
      return {key: value}

    return default_dict_converter

  @classmethod
  def _resolve_set_type(cls, field_type: t.Any) -> t.Callable[[t.Any], t.Any]:
    args = t.get_args(field_type)

    if args and args[0] != t.Any:
      element_converter = cls.resolve(args[0])
      return element_converter

    return str

  @classmethod
  def _resolve_tuple_type(cls, field_type: t.Any) -> t.Callable[[str], tuple]:
    args = t.get_args(field_type)

    if args:
      converters = [cls.resolve(arg) for arg in args]

      def tuple_converter(s: str) -> tuple:
        parts = s.split(',')

        if len(parts) != len(converters):
          raise ValueError(f'Expected {len(converters)} comma-separated values, got {len(parts)}')

        return tuple(converter(part) for converter, part in zip(converters, parts))

      return tuple_converter

    def default_tuple_converter(s: str) -> tuple:
      return tuple(s.split(','))

    return default_tuple_converter

  @classmethod
  def _resolve_union_type(cls, field_type: t.Any) -> t.Callable[[t.Any], t.Any]:
    args = t.get_args(field_type)

    if not args:
      return str

    if type(None) in args and len(args) == 2:
      non_none_type = next(arg for arg in args if arg is not type(None))

      def optional_converter(value):
        if value is None:
          return None
        return cls.resolve(non_none_type)(value)

      return optional_converter

    non_none_args = [arg for arg in args if arg is not type(None)]

    if not non_none_args:
      return str

    if len(non_none_args) == 1:
      return cls.resolve(non_none_args[0])

    return cls._create_union_converter(non_none_args)

  @classmethod
  def _resolve_literal_type(cls, field_type: t.Any) -> t.Callable[[str], t.Any]:
    literals = t.get_args(field_type)

    def literal_converter(s: str) -> t.Any:
      for lit in literals:
        if isinstance(lit, str) and s == lit:
          return lit

        try:
          if isinstance(lit, int) and int(s) == lit:
            return lit
          if isinstance(lit, float) and float(s) == lit:
            return lit
        except (ValueError, TypeError):
          continue

        if isinstance(lit, bool):
          bool_result = cls._resolve_bool_from_string(s)

          if bool_result is not None and bool_result == lit:
            return lit

      accepted_values = ', '.join(repr(lit) for lit in literals)

      raise ValueError(f"'{s}' is not one of the accepted values: {accepted_values}")

    return literal_converter

  @classmethod
  def _create_enum_converter(cls, enum_type: t.Type[Enum]) -> t.Callable[[str], Enum]:
    def enum_converter(s: str) -> Enum:
      try:
        return enum_type[s]
      except KeyError:
        try:
          for member in enum_type:
            if isinstance(member.value, (int, float, bool)) and str(member.value) == s:
              return member

          return enum_type(int(s) if s.isdigit() else s)
        except (ValueError, TypeError):
          choices = ', '.join(f"'{item.name}'" for item in enum_type)
          raise ValueError(f"'{s}' is not a valid {enum_type.__name__}. Choices: {choices}")

    return enum_converter

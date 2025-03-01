import typing as t

T = t.TypeVar('T')

PRIMITIVE_TYPES = {
  bool: bool,
  int: int,
  float: float,
  str: str,
  tuple: tuple,
}

BOOL_TRUE_VALUES = ('true', 't', 'yes', 'y', '1')
BOOL_FALSE_VALUES = ('false', 'f', 'no', 'n', '0')


def infer_default_value(field_type: t.Any) -> t.Any:
  """Infer a default value for a given type."""
  if field_type is bool:
    return False

  if field_type is int:
    return 0

  if field_type is float:
    return 0.0

  if field_type is str:
    return ''

  if field_type is list or t.get_origin(field_type) is list:
    return []

  if field_type is tuple:
    return ()

  if t.get_origin(field_type) is t.Union:
    return infer_default_value(resolve_type(field_type))

  return None


def resolve_type(field_type: t.Any) -> t.Callable[[t.Any], t.Any]:
  """Determine the type conversion function for a given type."""
  if t.get_origin(field_type) is list:
    return _resolve_list_type(field_type)

  if t.get_origin(field_type) is t.Union:
    return _resolve_union_type(field_type)

  if isinstance(field_type, type):
    return field_type

  for primitive_type, type_function in PRIMITIVE_TYPES.items():
    if field_type is primitive_type:
      return type_function

  return str


def _resolve_bool_from_string(value: str) -> t.Optional[bool]:
  """Convert a string to a boolean value if possible."""
  if value.lower() in BOOL_TRUE_VALUES:
    return True

  if value.lower() in BOOL_FALSE_VALUES:
    return False

  return None


def _create_union_converter(types: t.List[t.Type]) -> t.Callable[[t.Any], t.Any]:
  """Create a converter function for union types."""

  def union_converter(value: t.Any) -> t.Any:
    for arg_type in types:
      try:
        if arg_type is bool:
          bool_result = _resolve_bool_from_string(value)
          if bool_result is not None:
            return bool_result
          continue
        return t.cast(t.Any, arg_type(value))
      except (ValueError, TypeError):
        continue
    return str(value)

  return union_converter


def _resolve_list_type(field_type: t.Any) -> t.Callable[[t.Any], t.Any]:
  """Resolve the type for a list."""
  args = t.get_args(field_type)

  if args and args[0] != t.Any:
    return resolve_type(args[0])

  return str


def _resolve_union_type(field_type: t.Any) -> t.Callable[[t.Any], t.Any]:
  """Resolve the type for a union."""
  args = t.get_args(field_type)

  if not args:
    return str

  non_none_args = [arg for arg in args if arg is not type(None)]

  if not non_none_args:
    return str

  if len(non_none_args) > 1 and any(t in non_none_args for t in PRIMITIVE_TYPES.keys()):
    return _create_union_converter(non_none_args)

  return resolve_type(non_none_args[0])

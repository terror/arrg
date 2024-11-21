import typing as t
from argparse import ArgumentParser, Namespace, _SubParsersAction
from dataclasses import MISSING, Field, dataclass, field

CUSTOM = 'custom'
SUPPORTED = 'supported'


class Argument:
  def __init__(self, name: str, parameters: t.Dict[str, str] | None) -> None:
    self.name = name
    self.parameters = parameters

  def run(self) -> t.List[str]:
    if not self.parameters:
      return [f'{self.name}']

    return [
      f'--{self.name}',
      *list(
        filter(
          lambda output: output is not None,
          map(lambda pair: getattr(self, f'_{pair[0]}')(pair[1]), self.parameters.items()),
        )
      ),
    ]

  def _short(self, value: str | bool | None) -> str | None:
    if isinstance(value, bool):
      return f'-{self.name[0]}'
    if isinstance(value, str):
      return f'-{value}'
    return None

  def _long(self, value: str | None) -> str | None:
    if isinstance(value, str):
      return f'--{value}'
    return None


def app(cls=None, *args, **kwargs):
  def wrap(cls):
    return process(cls, *args, **kwargs)

  if cls is None:
    return wrap
  return wrap(cls)


def option(
  short: t.Optional[t.Union[str, bool]] = None,
  long: t.Optional[t.Union[str, bool]] = None,
  **kwargs: t.Any,
) -> Field:
  return field(
    metadata={
      'custom': {
        'short': short,
        'long': long,
      },
      'supported': kwargs,
    }
  )


T = t.TypeVar('T')


def make_optional_field() -> Field:
  """Create a field with default=None."""
  return field(default=None)


def has_default(field_info: Field) -> bool:
  """Check if a field has a default value."""
  return field_info.default is not MISSING or field_info.default_factory is not MISSING


def get_field_default(field_info: Field) -> t.Any:
  """Get the default value for a field."""
  if field_info.default is not MISSING:
    return field_info.default
  if field_info.default_factory is not MISSING:
    return field_info.default_factory()
  return MISSING


def add_argument_to_parser(parser: ArgumentParser, name: str, field_info: Field) -> None:
  """Add an argument to the parser based on field information."""
  metadata = field_info.metadata.get(CUSTOM, {})
  kwargs = field_info.metadata.get(SUPPORTED, {})

  if field_info.type == bool:
    kwargs['action'] = 'store_true'
    kwargs.setdefault('default', False)
  elif field_info.type == int:
    kwargs['type'] = int

  default = get_field_default(field_info)
  if default is not MISSING:
    kwargs.setdefault('default', default)

  arg_strings = Argument(name, metadata).run()

  if metadata:
    parser.add_argument(*arg_strings, **kwargs)
  else:
    parser.add_argument(name, **kwargs)


def subcommand(cls: t.Optional[t.Type[T]] = None) -> t.Type[T]:
  """Decorator to mark a class as a subcommand."""

  def wrap(cls: t.Type[T]) -> t.Type[T]:
    setattr(cls, '_is_subcommand', True)

    hints = t.get_type_hints(cls)
    for name, hint in hints.items():
      if name == 'return':
        continue

      if hasattr(cls, name):
        continue

      if is_subcommand(hint):
        setattr(cls, name, make_optional_field())

    if not hasattr(cls, '__dataclass_fields__'):
      cls = dataclass(cls)

    return cls

  if cls is None:
    return wrap
  return wrap(cls)


def is_subcommand(cls: t.Any) -> bool:
  """Check if a class is marked as a subcommand."""
  return hasattr(cls, '_is_subcommand') and getattr(cls, '_is_subcommand')


def get_or_create_subparsers(parser: ArgumentParser) -> _SubParsersAction:
  """Get existing subparsers or create new ones."""
  for action in parser._actions:
    if isinstance(action, _SubParsersAction):
      return action

  return parser.add_subparsers(dest='command', required=False)


def process_subcommand(
  parent_parser: ArgumentParser,
  name: str,
  field_type: t.Type[t.Any],
) -> None:
  """Process a subcommand field, creating necessary parsers and arguments."""
  if not is_subcommand(field_type):
    raise TypeError(f'Command {name} must be decorated with @subcommand')

  subparsers = get_or_create_subparsers(parent_parser)

  subparser = subparsers.add_parser(name)

  for field_name, field_info in field_type.__dataclass_fields__.items():
    if field_name == 'return':
      continue

    field_type_hint = t.get_type_hints(field_type)[field_name]

    if is_subcommand(field_type_hint):
      process_subcommand(subparser, field_name, field_type_hint)
    else:
      add_argument_to_parser(subparser, field_name, field_info)


def build_subcommand_instance(
  cls: t.Type[t.Any],
  parsed_args: Namespace,
  command_path: str = '',
) -> t.Optional[t.Any]:
  """Recursively build instances of subcommands from parsed arguments."""
  command = getattr(parsed_args, 'command', None)
  if command is None:
    return None

  if not command_path:
    command_path = command.split()[0] if command else None

  kwargs: t.Dict[str, t.Any] = {}

  for field_name, field_info in cls.__dataclass_fields__.items():
    if field_name == 'return':
      continue

    field_type = t.get_type_hints(cls)[field_name]
    default = get_field_default(field_info)

    if is_subcommand(field_type):
      if command and command.startswith(field_name):
        nested_instance = build_subcommand_instance(field_type, parsed_args)
        if nested_instance is not None:
          kwargs[field_name] = nested_instance
      elif default is not MISSING:
        kwargs[field_name] = default
    else:
      value = getattr(parsed_args, field_name, default)
      if value is not None and value is not MISSING:
        kwargs[field_name] = value

  try:
    return cls(**kwargs)
  except TypeError:
    return None


def process(cls: t.Type[T], *args: t.Any, **kwargs: t.Any) -> t.Type[T]:
  """Process a class decorated with @app."""

  def add_field_defaults(cls: t.Type[t.Any]) -> None:
    """Add default None values for subcommand fields."""
    hints = t.get_type_hints(cls)
    for name, hint in hints.items():
      if name != 'return' and is_subcommand(hint):
        if not hasattr(cls, name):
          setattr(cls, name, make_optional_field())

  def parse(cls: t.Type[T], args: list = []) -> t.Dict[str, t.Any]:
    parser = ArgumentParser(**kwargs)
    result: t.Dict[str, t.Any] = {}

    for field_name, field_info in cls.__dataclass_fields__.items():
      if field_name == 'return':
        continue

      field_type = t.get_type_hints(cls)[field_name]

      if is_subcommand(field_type):
        process_subcommand(parser, field_name, field_type)
      else:
        add_argument_to_parser(parser, field_name, field_info)

    parsed_args = parser.parse_args(args)

    for field_name, field_info in cls.__dataclass_fields__.items():
      if field_name == 'return':
        continue

      field_type = t.get_type_hints(cls)[field_name]
      default = get_field_default(field_info)

      if is_subcommand(field_type):
        instance = build_subcommand_instance(field_type, parsed_args, field_name)
        if instance is not None:
          result[field_name] = instance
        elif default is not MISSING:
          result[field_name] = default
      else:
        value = getattr(parsed_args, field_name, default)
        if value is not None and value is not MISSING:
          result[field_name] = value

    return result

  @classmethod
  def from_args(cls: t.Type[T]) -> T:
    return cls(**parse(cls))

  @classmethod
  def from_iter(cls: t.Type[T], args: list) -> T:
    return cls(**parse(cls, args))

  if not hasattr(cls, '__dataclass_fields__'):
    cls = dataclass(cls)

  add_field_defaults(cls)

  cls.from_args = from_args
  cls.from_iter = from_iter

  return cls


__all__ = ['option', 'app', 'subcommand']

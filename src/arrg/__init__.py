import typing as t
from argparse import ArgumentParser, Namespace, _SubParsersAction
from dataclasses import MISSING, Field, dataclass, field

CUSTOM = 'custom'
SUPPORTED = 'supported'


T = t.TypeVar('T')


def _format_argument(name: str, parameters: dict[str, str | bool | None] | None) -> list[str]:
  """
  Format command line arguments based on name and optional parameters.

  The function handles both long and short form arguments:
  - Long form arguments are prefixed with '--'
  - Short form arguments are prefixed with '-'

  Args:
    name: The base name of the argument
    parameters: Optional dictionary containing:
      - 'short': If True, uses first letter of name. If string, uses that value
      - 'long': If string, uses that value as long form name

  Returns:
    List of formatted argument strings

  Examples:
    >>> format_argument(
    ...   'verbose',
    ...   {'short': True},
    ... )
    ['--verbose', '-v']

    >>> format_argument(
    ...   'output',
    ...   {
    ...     'short': 'o',
    ...     'long': 'output-file',
    ...   },
    ... )
    ['--output', '-o', '--output-file']

    >>> format_argument(
    ...   'name', None
    ... )
    ['name']
  """
  if not parameters:
    return [name]

  result = [f'--{name}']

  for param_type, value in parameters.items():
    formatted = None

    if param_type == 'short':
      if isinstance(value, bool):
        formatted = f'-{name[0]}'
      elif isinstance(value, str):
        formatted = f'-{value}'
    elif param_type == 'long' and isinstance(value, str):
      formatted = f'--{value}'

    if formatted is not None:
      result.append(formatted)

  return result


def _make_optional_field() -> Field:
  """
  Create a dataclass field with default value of None.

  Creates a field suitable for optional subcommands, ensuring they
  default to None when not specified in the command line arguments.

  Returns:
    Field: A dataclass field with default=None
  """
  return field(default=None)


def _get_field_default_value(field_info: Field) -> t.Any:
  """
  Get the default value for a dataclass field.

  Checks for default values in the following order:
  1. Explicit default value
  2. Default factory function
  3. MISSING sentinel if no default is found

  Args:
    field_info: The field to get the default value from

  Returns:
    The default value, or MISSING if no default is specified
  """
  if field_info.default is not MISSING:
    return field_info.default

  if field_info.default_factory is not MISSING:
    return field_info.default_factory()

  return MISSING


def _add_argument_to_parser(parser: ArgumentParser, name: str, field_info: Field) -> None:
  """
  Add an argument to the ArgumentParser based on field information and metadata.

  This function takes a field from a dataclass and converts it into an argument
  for argparse. It handles type conversion, default values, and special cases
  for boolean and integer types.

  Args:
    parser: The ArgumentParser instance to add the argument to
    name: The name of the argument
    field_info: Field object containing type and metadata information

  Special handling:
    - Boolean fields are converted to store_true flags with default False
    - Integer fields are set to use int type conversion
    - Default values from the field are passed to argparse
    - Custom metadata determines if argument uses short/long form

  Example:
    For a dataclass field like:
    name: str = option(short='n', default_value='test')

    This creates an argument that can be used as:
    --name value OR -n value
    with 'test' as the default value
  """
  metadata, kwargs = field_info.metadata.get(CUSTOM, {}), field_info.metadata.get(SUPPORTED, {})

  if field_info.type is bool:
    kwargs['action'] = 'store_true'
    kwargs.setdefault('default', False)
  elif field_info.type is int:
    kwargs['type'] = int

  default = _get_field_default_value(field_info)

  if default is not MISSING:
    kwargs.setdefault('default', default)

  if metadata:
    parser.add_argument(*_format_argument(name, metadata), **kwargs)
  else:
    parser.add_argument(name, **kwargs)


def _is_subcommand(cls: t.Any) -> bool:
  """
  Check if a class is marked as a subcommand.

  Tests whether the class has been decorated with @subcommand by checking
  for the presence and value of the '_is_subcommand' attribute.

  Args:
    cls: The class to check

  Returns:
    bool: True if the class is a subcommand, False otherwise
  """
  return hasattr(cls, '_is_subcommand') and getattr(cls, '_is_subcommand')


def _get_or_create_subparsers(parser: ArgumentParser) -> _SubParsersAction:
  """
  Get existing subparsers or create new ones for an ArgumentParser.

  Searches for an existing subparser in the ArgumentParser's actions.
  If none exists, creates a new subparser with 'command' as the destination
  for storing the chosen subcommand.

  Args:
    parser: The ArgumentParser to get or create subparsers for

  Returns:
    _SubParsersAction: The subparser action, either existing or newly created
  """
  for action in parser._actions:
    if isinstance(action, _SubParsersAction):
      return action

  return parser.add_subparsers(dest='command', required=False)


def _process_subcommand(
  parent_parser: ArgumentParser,
  name: str,
  field_type: t.Type[t.Any],
) -> None:
  """
  Process a subcommand field by creating subparsers and recursively adding arguments.

  This function handles the creation of nested command-line interfaces, similar to how
  Git uses subcommands (e.g., 'git commit', 'git push'). It recursively processes
  nested subcommands and their arguments to build a complete command hierarchy.

  Args:
    parent_parser: The parent ArgumentParser to attach subcommands to
    name: The name of the subcommand (used in CLI)
    field_type:
      The type of the field being processed, expected to be a class
      decorated with @subcommand

  Raises:
    TypeError: If field_type is not decorated with @subcommand

  Notes:
    - Skips processing of any field named 'return'
    - Recursively processes nested subcommands
    - Automatically adds arguments based on field types and options
    - Creates a new subparser for each subcommand level
  """
  if not _is_subcommand(field_type):
    raise TypeError(f'Command {name} must be decorated with @subcommand')

  subparsers = _get_or_create_subparsers(parent_parser)
  subparser = subparsers.add_parser(name)

  for field_name, field_info in field_type.__dataclass_fields__.items():
    if field_name == 'return':
      continue

    field_type_hint = t.get_type_hints(field_type)[field_name]

    if _is_subcommand(field_type_hint):
      _process_subcommand(subparser, field_name, field_type_hint)
    else:
      _add_argument_to_parser(subparser, field_name, field_info)


def _build_subcommand_instance(
  cls: t.Type[t.Any],
  parsed_args: Namespace,
  command_path: str = '',
) -> t.Optional[t.Any]:
  """
  Recursively build instances of subcommands from parsed arguments.

  This function takes parsed command line arguments and constructs instances
  of subcommand classes, handling the entire command hierarchy.

  Args:
    cls: The class type to instantiate
    parsed_args: Parsed command line arguments from ArgumentParser
    command_path: Current path in the command hierarchy (for nested commands)

  Returns:
    An instance of the subcommand class, or None if unable to construct

  Notes:
    - Handles nested subcommands recursively
    - Preserves default values when specified
    - Skips 'return' fields
    - Returns None if construction fails
  """
  command = getattr(parsed_args, 'command', None)

  if command is None:
    return None

  if not command_path:
    command_path = command.split()[0] if command else None

  kwargs: t.Dict[str, t.Any] = {}

  for field_name, field_info in cls.__dataclass_fields__.items():
    if field_name == 'return':
      continue

    field_type, default = t.get_type_hints(cls)[field_name], _get_field_default_value(field_info)

    if _is_subcommand(field_type):
      if command and command.startswith(field_name):
        nested_instance = _build_subcommand_instance(field_type, parsed_args)

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


def _process_app(cls: t.Type[T], *args: t.Any, **kwargs: t.Any) -> t.Type[T]:
  """
  Process a class decorated with @app by adding CLI functionality.

  This function transforms a regular class into a CLI application by:
  - Converting it to a dataclass if needed
  - Adding parser generation functionality
  - Setting up argument handling
  - Adding methods for parsing from command line or list

  Args:
    cls: The class to transform
    *args: Positional arguments for ArgumentParser
    **kwargs: Keyword arguments for ArgumentParser

  Returns:
    The processed class with added CLI functionality:
      - from_args(): Create instance from command line arguments
      - from_iter(): Create instance from list of arguments

  Notes:
    - Automatically handles subcommands
    - Preserves type hints and default values
    - Adds None defaults for optional subcommands
  """

  def add_field_defaults(cls: t.Type[t.Any]) -> None:
    """
    Add default None values for subcommand fields in a class.

    Examines class type hints and ensures all subcommand fields have
    a default value of None if not already specified.

    Args:
      cls: The class to process

    Notes:
      - Only processes fields that are subcommands
      - Skips fields named 'return'
      - Only adds defaults if not already present
    """
    hints = t.get_type_hints(cls)

    for name, hint in hints.items():
      if name != 'return' and _is_subcommand(hint):
        if not hasattr(cls, name):
          setattr(cls, name, _make_optional_field())

  def parse(cls: t.Type[T], args: list = []) -> t.Dict[str, t.Any]:
    """
    Parse command line arguments into a dictionary of values.

    Creates an ArgumentParser, adds all arguments from the class fields,
    and parses the provided arguments into a format suitable for class instantiation.

    Args:
      cls: The class containing field definitions
      args: List of command line arguments to parse (default: empty list)

    Returns:
      Dictionary mapping field names to parsed values

    Notes:
      - Handles both regular arguments and subcommands
      - Preserves type information and defaults
      - Skips 'return' fields
      - Processes nested subcommands recursively
    """
    parser = ArgumentParser(**kwargs)

    result: t.Dict[str, t.Any] = {}

    for field_name, field_info in cls.__dataclass_fields__.items():
      if field_name == 'return':
        continue

      field_type = t.get_type_hints(cls)[field_name]

      if _is_subcommand(field_type):
        _process_subcommand(parser, field_name, field_type)
      else:
        _add_argument_to_parser(parser, field_name, field_info)

    parsed_args = parser.parse_args(args)

    for field_name, field_info in cls.__dataclass_fields__.items():
      if field_name == 'return':
        continue

      field_type, default = t.get_type_hints(cls)[field_name], _get_field_default_value(field_info)

      if _is_subcommand(field_type):
        instance = _build_subcommand_instance(field_type, parsed_args, field_name)

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


def option(
  short: t.Optional[t.Union[str, bool]] = None,
  long: t.Optional[t.Union[str, bool]] = None,
  default_value: t.Any = MISSING,
  **kwargs: t.Any,
) -> Field:
  """
  Define a command-line option for a field in a CLI application.

  This decorator configures how a class field is presented in the command-line interface.
  It supports both short (-x) and long (--xyz) format arguments, along with additional
  configuration through kwargs.

  Args:
    short: Short form configuration
      - If True, uses first letter of field name (e.g., 'verbose' -> '-v')
      - If string, uses that character (e.g., 'n' -> '-n')
      - If None, no short form
    long: Long form configuration
      - If string, uses that name (e.g., 'output-file' -> '--output-file')
      - If None, uses field name
    default_value: Default value for the argument if not provided
    **kwargs: Additional arguments passed to ArgumentParser.add_argument()

  Returns:
    Field: A dataclass field with CLI metadata
  """
  if default_value is not MISSING:
    kwargs['default'] = default_value

  return field(
    metadata={
      CUSTOM: {
        'short': short,
        'long': long,
      },
      SUPPORTED: kwargs,
    },
    default=default_value if default_value is not MISSING else MISSING,
  )


def app(cls=None, *args, **kwargs):
  """
  Main decorator for creating a command-line interface from a class.

  Transforms a Python class into a complete CLI application. All fields become
  command-line arguments, and nested classes decorated with @subcommand become
  subcommands.

  Args:
    cls: The class to transform
    *args: Positional arguments passed to ArgumentParser
    **kwargs: Keyword arguments passed to ArgumentParser

  Returns:
    The processed class with CLI capabilities
  """

  def wrap(cls):
    return _process_app(cls, *args, **kwargs)

  if cls is None:
    return wrap

  return wrap(cls)


def subcommand(cls: t.Optional[t.Type[T]] = None) -> t.Type[T]:
  """
  Decorator to mark a class as a CLI subcommand.

  Transforms a nested class into a subcommand, similar to how Git uses 'commit'
  in 'git commit'. Subcommands can be nested to create complex command hierarchies.

  Args:
    cls: The class to transform into a subcommand

  Returns:
    The processed class with subcommand capabilities
  """

  def wrap(cls: t.Type[T]) -> t.Type[T]:
    setattr(cls, '_is_subcommand', True)

    hints = t.get_type_hints(cls)

    for name, hint in hints.items():
      if name == 'return':
        continue

      if hasattr(cls, name):
        continue

      if _is_subcommand(hint):
        setattr(cls, name, _make_optional_field())

    if not hasattr(cls, '__dataclass_fields__'):
      cls = dataclass(cls)

    return cls

  if cls is None:
    return wrap

  return wrap(cls)


__all__ = ['option', 'app', 'subcommand']

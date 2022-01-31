import sys
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

  This function creates a field suitable for optional subcommands in a CLI application.

  The field is configured with:
  - default=None: Makes the field optional
  - init=False: Excludes the field from the class's __init__ signature

  This configuration ensures that subcommands can be optional in the CLI without
  affecting the class initialization process.

  Returns:
    Field: A dataclass field configured for optional subcommands
  """
  return field(
    default=None,
    init=False,
  )


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
  parent_path: str = '',
) -> None:
  """
  Process a subcommand field by creating subparsers and recursively adding arguments.

  Creates a subparser for the given field and processes all of its arguments. For nested
  subcommands, builds a full command path that tracks the hierarchy (e.g., "remote push").

  Args:
    parent_parser: The parent ArgumentParser to attach subcommands to
    name: The name of the subcommand (used in CLI)
    field_type: The type of the field being processed
    parent_path: The command path of the parent parser, used for nested commands

  Raises:
    TypeError: If field_type is not decorated with @subcommand
  """
  if not _is_subcommand(field_type):
    raise TypeError(f'Command {name} must be decorated with @subcommand')

  subparsers = _get_or_create_subparsers(parent_parser)
  command_path = f'{parent_path} {name}'.strip()

  subparser = subparsers.add_parser(name)
  subparser.set_defaults(command=command_path)

  for field_name, field_info in field_type.__dataclass_fields__.items():
    if field_name == 'return':
      continue

    field_type_hint = t.get_type_hints(field_type)[field_name]

    if _is_subcommand(field_type_hint):
      _process_subcommand(subparser, field_name, field_type_hint, command_path)
    else:
      _add_argument_to_parser(subparser, field_name, field_info)


def _build_subcommand_instance(
  cls: t.Type[t.Any],
  parsed_args: Namespace,
  command_path: str = '',
) -> t.Optional[t.Any]:
  """
  Build a subcommand instance from parsed arguments.

  Recursively constructs instances of subcommand classes based on the command path.
  For nested subcommands, only creates instances for commands that are part of the
  active command path and properly assigns arguments at each level.

  Args:
    cls: The class type to instantiate
    parsed_args: Parsed command line arguments
    command_path: Current path in the command hierarchy (e.g., "remote" or "remote push")

  Returns:
    An instance of the subcommand class, or None if the command path doesn't match
  """
  command = getattr(parsed_args, 'command', None)

  if not command:
    return None

  command_parts = command.split()
  path_parts = command_path.split() if command_path else []

  # Match command path
  if path_parts and command_parts[: len(path_parts)] != path_parts:
    return None

  kwargs: t.Dict[str, t.Any] = {}

  for field_name, _ in cls.__dataclass_fields__.items():
    if field_name == 'return':
      continue

    field_type = t.get_type_hints(cls)[field_name]

    if _is_subcommand(field_type):
      next_path = f'{command_path} {field_name}'.strip()

      # If this is the next command in the path
      if len(command_parts) > len(path_parts) and command_parts[len(path_parts)] == field_name:
        nested_instance = _build_subcommand_instance(field_type, parsed_args, next_path)

        if nested_instance is not None:
          kwargs[field_name] = nested_instance
    else:
      value = getattr(parsed_args, field_name, None)

      if value is not None:
        kwargs[field_name] = value

  try:
    return cls(**kwargs)
  except TypeError:
    return None


def _process_inherited_fields(cls: t.Type[t.Any]) -> dict:
  """
  Process fields from parent classes for subcommands.

  This function handles the inheritance of fields for CLI subcommands by:
  1. Collecting fields from all parent classes
  2. Adding fields from the current class's annotations
  3. Preserving any existing field configurations

  Args:
    cls: The class to process inherited fields for

  Returns:
    dict:
      A dictionary of field names to Field objects, containing all
       inherited and current class fields

  Notes:
    - Fields from parent classes are collected first
    - Current class fields override parent fields of the same name
    - Fields without explicit values get a default MISSING sentinel
    - The 'return' field is included in processing

  Example:
    @subcommand
    class BaseCommand:
      verbose: bool = option(short=True)

    @subcommand
    class Status(BaseCommand):
      quiet: bool = option(short=True)

    fields = _process_inherited_fields(Status)
    # Contains both 'verbose' and 'quiet' fields with their options
  """
  fields = {}

  # Get fields from parent classes
  for base in cls.__bases__:
    if hasattr(base, '__dataclass_fields__'):
      fields.update(base.__dataclass_fields__)

  # Add current class fields
  if hasattr(cls, '__annotations__'):
    for name, _ in cls.__annotations__.items():
      if name not in fields:
        if hasattr(cls, name):
          fields[name] = getattr(cls, name)
        else:
          fields[name] = field(default=MISSING)

  return fields


def _process_app(cls: t.Type[T], *args: t.Any, **kwargs: t.Any) -> t.Type[T]:
  """
  Process a class decorated with @app to create a command-line interface.

  This function transforms a Python class into a CLI application by:
  1. Converting it to a dataclass if needed
  2. Adding parser generation functionality
  3. Setting up argument handling
  4. Adding methods for parsing from command line or list

  Args:
    cls: The class to transform into a CLI application
    *args: Positional arguments passed to ArgumentParser
    **kwargs: Keyword arguments passed to ArgumentParser

  Returns:
    The processed class with added CLI functionality:
    - from_args(): Create instance from command line arguments
    - from_iter(): Create instance from list of arguments

  Example:
    @app
    class Git:
      status: Status
      verbose: bool = option(short=True)

    # Creates a CLI that can be used as:
    # git status --verbose
    # The class can then be instantiated with:
    instance = Git.from_args()  # From sys.argv
    instance = Git.from_iter(['status', '-v'])  # From list
  """

  def add_field_defaults(cls: t.Type[t.Any]) -> None:
    """
    Add default None values for subcommand fields in a class.

    This function ensures all subcommand fields have proper default values,
    making them optional in the CLI interface. It examines the class's type
    hints and adds default values where needed.

    Args:
      cls: The class to process

    Notes:
      - Only processes fields that are subcommands
      - Skips fields named 'return'
      - Uses _make_optional_field() to create default values
    """
    hints = t.get_type_hints(cls)

    for name, hint in hints.items():
      if name != 'return' and _is_subcommand(hint):
        if not hasattr(cls, name):
          setattr(cls, name, _make_optional_field())

  def parse(cls: t.Type[T], args: list | None = None) -> t.Dict[str, t.Any]:
    """
    Parse command line arguments into a dictionary of values.

    This function creates an ArgumentParser, adds all arguments from the class
    fields, and parses the provided arguments into a format suitable for class
    instantiation.

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

    Example:
      @app
      class MyApp:
        name: str
        count: int = option(short=True)

      # Parsing arguments
      values = parse(MyApp, ['--name', 'test', '-c', '42'])
      # Returns: {'name': 'test', 'count': 42}
    """
    if args is None:
      args = sys.argv[1:]

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

    # Add None for any missing subcommand fields
    for name, _ in cls.__dataclass_fields__.items():
      if name not in result and _is_subcommand(t.get_type_hints(cls)[name]):
        result[name] = None

    return result

  @classmethod
  def from_args(cls: t.Type[T]) -> T:
    """
    Create a class instance from command line arguments (sys.argv).

    This classmethod creates an instance of the class by parsing command
    line arguments from sys.argv.

    Returns:
      An instance of the class with values from command line arguments

    Example:
      instance = MyApp.from_args()  # Parses from sys.argv
    """
    return cls(**parse(cls))

  @classmethod
  def from_iter(cls: t.Type[T], args: list) -> T:
    """
    Create a class instance from a list of arguments.

    This classmethod creates an instance of the class by parsing a provided
    list of arguments.

    Args:
      args: List of command line arguments to parse

    Returns:
      An instance of the class with values from the arguments

    Example:
      instance = MyApp.from_iter(['--name', 'test'])
    """
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
  Decorator to mark a class as a CLI subcommand with inheritance support.

  This decorator transforms a Python class into a subcommand that can be used
  within a CLI application. It handles inheritance of fields and options from
  parent classes, and configures the class for use in command hierarchies.

  Args:
    cls:
      The class to transform into a subcommand. If None, returns a wrapper
       function for use with parameters.

  Returns:
    The processed class with subcommand capabilities

  Raises:
    TypeError: If applied to a non-class object

  Notes:
    - Supports class inheritance, preserving fields and options from parent classes
    - Automatically converts the class to a dataclass if it isn't one already
    - Handles nested subcommands (subcommands that have their own subcommands)
    - Makes all subcommand fields optional by default
  """

  def wrap(cls: t.Type[T]) -> t.Type[T]:
    """
    Inner wrapper function that performs the actual class transformation.

    This function:
    1. Processes inherited fields from parent classes
    2. Marks the class as a subcommand
    3. Processes type hints for nested subcommands
    4. Converts the class to a dataclass if needed

    Args:
      cls: The class to process

    Returns:
      The processed class with all subcommand functionality added

    Notes:
      - Preserves existing field values when inheriting from parent classes
      - Ensures all subcommand fields are optional with None defaults
      - Maintains proper dataclass functionality and initialization
    """
    inherited_fields = _process_inherited_fields(cls)

    for name, field_info in inherited_fields.items():
      if not hasattr(cls, name):
        setattr(cls, name, field_info)

    setattr(cls, '_is_subcommand', True)

    hints = t.get_type_hints(cls)

    for name, hint in hints.items():
      if name == 'return':
        continue
      if _is_subcommand(hint):
        if not hasattr(cls, name):
          setattr(cls, name, _make_optional_field())

    if not hasattr(cls, '__dataclass_fields__'):
      cls = dataclass(cls)

    return cls

  if cls is None:
    return wrap

  return wrap(cls)


__all__ = ['option', 'app', 'subcommand']

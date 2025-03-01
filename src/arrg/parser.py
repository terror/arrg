import argparse
import shlex
import sys
import typing as t
from collections import defaultdict
from inspect import getmembers, isdatadescriptor

from .argument import Argument
from .utils import infer_default_value, resolve_type

R = t.TypeVar('R')

ArgParser = argparse.ArgumentParser
ArgNamespace = argparse.Namespace
SubparsersAction = argparse._SubParsersAction


class Parser:
  def __init__(self, **parser_kwargs: t.Any):
    self._exit_on_error = parser_kwargs.pop('exit_on_error', True)
    self._override_field_names: t.List[str] = []
    self._parser: ArgParser = ArgParser(**parser_kwargs)
    self._subcommand_parsers: t.Dict[str, ArgParser] = {}
    self._subparsers: t.Optional[SubparsersAction] = None

  @staticmethod
  def from_instance(instance: t.Type[R], **parser_kwargs: t.Any) -> 'Parser':
    """Create a parser from a class instance with defaults."""
    if 'description' not in parser_kwargs:
      parser_kwargs['description'] = f'{instance.__name__} command-line interface'

    parser = Parser(**parser_kwargs)
    parser._process_class(instance, parser._parser)

    return parser

  def _is_subcommand_field(self, field_type: t.Type) -> bool:
    """Check if field type is a subcommand (directly or via Optional)."""
    # Direct subcommand
    if hasattr(field_type, '__subcommand__'):
      return True

    # Optional[Subcommand]
    origin = t.get_origin(field_type)
    if origin is t.Union:
      args = t.get_args(field_type)
      for arg in args:
        if arg is not type(None) and hasattr(arg, '__subcommand__'):
          return True

    return False

  def _get_subcommand_type(self, field_type: t.Type) -> t.Type:
    """Extract subcommand type from Optional[Subcommand] if needed."""
    if hasattr(field_type, '__subcommand__'):
      return field_type

    origin = t.get_origin(field_type)
    if origin is t.Union:
      args = t.get_args(field_type)
      for arg in args:
        if arg is not type(None) and hasattr(arg, '__subcommand__'):
          return arg

    return field_type

  def _ensure_processed_fields(self, parser: ArgParser) -> t.Set[str]:
    """Ensure parser has a set to track processed fields."""
    if not hasattr(parser, '_processed_fields'):
      setattr(parser, '_processed_fields', set())
    return getattr(parser, '_processed_fields')

  def _process_class(self, cls: t.Type, parser: ArgParser) -> None:
    """Process a class's fields and properties for arguments, including inherited ones."""
    self._ensure_processed_fields(parser)

    # Get all classes in the inheritance hierarchy (excluding object)
    classes_to_process = [c for c in cls.__mro__ if c is not object]

    # Process from base classes to derived classes (reversed MRO)
    for current_cls in reversed(classes_to_process):
      self._process_fields(current_cls, parser)
      self._process_properties(current_cls, parser)

  def _process_fields(self, cls: t.Type, parser: ArgParser) -> None:
    """Process the fields of a class, including all annotations."""
    processed_fields = self._ensure_processed_fields(parser)
    annotations = getattr(cls, '__annotations__', {})

    for field_name, field_type in annotations.items():
      # Skip already processed fields
      if field_name in processed_fields:
        continue

      # Handle subcommand fields (direct or via Optional)
      if self._is_subcommand_field(field_type):
        actual_type = self._get_subcommand_type(field_type)
        self._process_subcommand_field(field_name, actual_type, parser)
        processed_fields.add(field_name)
        continue

      # Handle regular argument fields
      self._process_argument_field(cls, field_name, field_type, parser, processed_fields)

  def _process_argument_field(
    self,
    cls: t.Type,
    field_name: str,
    field_type: t.Type,
    parser: ArgParser,
    processed_fields: t.Set[str],
  ) -> None:
    """Process a regular argument field."""
    # Try to get the field value directly from the class
    field_value = getattr(cls, field_name, None)

    # If it's a properly defined argument field
    if field_value and hasattr(field_value, 'metadata') and 'argument' in field_value.metadata:
      self._add_argument(field_name, field_type, field_value.metadata['argument'], parser=parser)
      processed_fields.add(field_name)
      return

    # If we have a dataclass field
    if hasattr(cls, '__dataclass_fields__') and field_name in cls.__dataclass_fields__:
      field = cls.__dataclass_fields__[field_name]
      if 'argument' in field.metadata:
        self._add_argument(field_name, field_type, field.metadata['argument'], parser=parser)
        processed_fields.add(field_name)

  def _process_subcommand_field(
    self, field_name: str, field_type: t.Type, parser: ArgParser
  ) -> None:
    """Process a subcommand field."""
    # Get or create subparsers for this parser level
    subparsers = self._get_subparsers_for_parser(parser)

    # Create a subparser for this command
    subparser = subparsers.add_parser(field_name, help=f'{field_name} command')

    # Track top-level subcommand parsers
    if parser is self._parser:
      self._subcommand_parsers[field_name] = subparser

    # Recursively process the subcommand class
    self._process_class(field_type, subparser)

  def _get_subparsers_for_parser(self, parser: ArgParser) -> SubparsersAction:
    """Get or create subparsers for a parser."""
    if parser is self._parser:
      # Handle main parser
      if self._subparsers is None:
        self._subparsers = parser.add_subparsers(title='subcommands')
      return self._subparsers
    else:
      # Handle nested parsers
      return self._get_or_create_subparsers(parser)

  def _get_or_create_subparsers(self, parser: ArgParser) -> SubparsersAction:
    """Get existing subparsers or create new ones for the parser."""
    for action in parser._actions:
      if isinstance(action, SubparsersAction):
        return action
    return parser.add_subparsers(title='subcommands')

  def _process_properties(self, cls: t.Type, parser: ArgParser) -> None:
    """Process class properties decorated with @property."""
    dataclass_fields = getattr(cls, '__dataclass_fields__', {})

    for member_name, member_value in getmembers(cls, isdatadescriptor):
      # Skip fields that are already in dataclass fields
      if member_name in dataclass_fields:
        continue

      if not hasattr(member_value, '__get__'):
        continue

      try:
        # Create a temporary instance to access the property
        temp_instance = cls(**{field_name: None for field_name in dataclass_fields})

        field = getattr(temp_instance, member_name)

        # Skip if not an argument field
        if not hasattr(field, 'metadata') or 'argument' not in field.metadata:
          continue

        argument = field.metadata['argument']

        # Get the property's return type annotation
        fget = getattr(member_value, 'fget')
        fget_func = getattr(fget, '__func__', fget)
        member_return_type = t.get_type_hints(fget_func).get('return')

        # Add as argument
        self._add_argument(
          member_name,
          argument.type or member_return_type or field.default.__class__,
          argument,
          parser=parser,
        )

        # Track property names for later
        self._override_field_names.append(member_name)
      except Exception:
        pass

  def _add_argument(
    self,
    field_name: str,
    field_type: t.Any,
    argument: Argument,
    parser: t.Optional[ArgParser] = None,
  ) -> None:
    """Add a standard argument to the specified parser."""
    if parser is None:
      parser = self._parser

    # Start with resolved kwargs from the argument
    kwargs = argument.resolve_kwargs()

    # Handle type inference and special cases
    self._prepare_argument_kwargs(field_name, field_type, argument, kwargs)

    # Add the argument to the parser
    if argument.name_or_flags:
      parser.add_argument(*argument.name_or_flags, **kwargs)
    else:
      parser.add_argument(field_name, **kwargs)

  def _prepare_argument_kwargs(
    self, field_name: str, field_type: t.Any, argument: Argument, kwargs: t.Dict[str, t.Any]
  ) -> None:
    """Prepare kwargs for argparse.add_argument based on field type and argument."""
    resolved_type = resolve_type(field_type)

    # Handle type based on field type
    if 'type' not in kwargs and resolved_type is not bool:
      kwargs['type'] = resolved_type

    # Special handling for boolean fields
    if resolved_type is bool:
      if 'type' in kwargs:
        del kwargs['type']
      if 'action' not in kwargs:
        kwargs['action'] = 'store_true'

    # Special handling for list fields
    if t.get_origin(field_type) is list and 'nargs' not in kwargs:
      kwargs['nargs'] = '+'

    # Add default if not provided
    if 'default' not in kwargs and not getattr(self._parser, 'argument_default'):
      kwargs['default'] = infer_default_value(field_type)

    # Set destination if not positional and not provided
    if 'dest' not in kwargs and not argument.positional:
      kwargs['dest'] = field_name

    # Remove required for positional arguments
    if 'required' in kwargs and argument.positional:
      del kwargs['required']

  def parse_args(
    self, args: t.Optional[t.Union[str, t.Sequence[str]]] = None
  ) -> t.Dict[str, t.Any]:
    """Parse command line arguments and return a dictionary of parsed values."""
    # Normalize args to a sequence of strings
    if args is None:
      args = sys.argv[1:]
    elif isinstance(args, str):
      args = shlex.split(args)

    try:
      # Handle simple case with no subparsers
      if self._subparsers is None:
        return self._parse_simple(args)
      else:
        # Handle complex case with subparsers
        return self._parse_level(self._subparsers, args)
    except SystemExit as e:
      # Handle exit_on_error=False mode
      if not self._exit_on_error:
        error_code = e.code if isinstance(e.code, int) else 1
        raise argparse.ArgumentError(None, f'Argument parsing error with code {error_code}') from e
      raise  # Re-raise the SystemExit exception if exit_on_error=True

  def _parse_simple(self, args: t.Sequence[str]) -> t.Dict[str, t.Any]:
    """Parse arguments without subcommands."""
    temp_ns = ArgNamespace()
    self._parser.parse_args(args, temp_ns)
    return vars(temp_ns)

  def _parse_level(self, commands: SubparsersAction, args: t.Sequence[str]) -> t.Dict[str, t.Any]:
    """Parse arguments at a specific command level."""
    # Get available commands at this level
    cmd_choices = list(commands.choices.keys())

    # Group args by command
    cmd_groups = self._group_args_by_command(args, cmd_choices)

    # Parse top-level args (those not associated with any command)
    temp_ns = ArgNamespace()
    self._parser.parse_args(cmd_groups.get(None, []), temp_ns)
    result = vars(temp_ns)

    # Initialize all commands to None or appropriate empty dict
    for cmd in cmd_choices:
      result[cmd] = None

    # Process each command with its args
    for cmd, cmd_args in cmd_groups.items():
      if cmd is None:
        continue

      # Get parser for this command
      cmd_parser = commands.choices[cmd]

      # Find any subparsers for this command
      subcmds = self._find_subparsers(cmd_parser)

      # Parse the command args
      if subcmds and self._has_subcommand_arg(subcmds, cmd_args):
        # Recursive parsing for nested commands
        cmd_dict = self._parse_level(subcmds, cmd_args)
      else:
        # Simple parsing for leaf commands
        temp_ns = ArgNamespace()
        cmd_parser.parse_args(cmd_args, temp_ns)
        cmd_dict = vars(temp_ns)

      result[cmd] = cmd_dict

    return result

  def _find_subparsers(self, parser: ArgParser) -> t.Optional[SubparsersAction]:
    """Find subparsers action for a parser if it exists."""
    for action in parser._actions:
      if isinstance(action, SubparsersAction):
        return action
    return None

  def _has_subcommand_arg(self, subparsers: SubparsersAction, args: t.Sequence[str]) -> bool:
    """Check if any argument is a subcommand of the given subparsers."""
    return any(arg in subparsers.choices for arg in args)

  def _group_args_by_command(
    self, args: t.Sequence[str], command_choices: t.Iterable[str]
  ) -> t.Dict[t.Optional[str], t.List[str]]:
    """Group arguments by command name."""
    result = defaultdict(list)
    current_cmd = None

    for arg in args:
      if arg in command_choices:
        # This is a new command
        current_cmd = arg
        # Important: Create empty entry for the command to ensure it's included
        # even if it has no arguments (prevents the bug with empty subcommands)
        result[current_cmd] = []
      elif current_cmd is None:
        # This is a top-level arg
        result[None].append(arg)
      else:
        # This is an arg for the current command
        result[current_cmd].append(arg)

    return result

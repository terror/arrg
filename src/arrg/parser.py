import argparse
import shlex
import sys
import typing as t
from inspect import getmembers, isdatadescriptor

from .argument import Argument
from .utils import infer_default_value, resolve_type

R = t.TypeVar('R')


class Parser:
  def __init__(self, description: str):
    self._override_field_names = []
    self._parser = argparse.ArgumentParser(description=description)
    self._subcommand_parsers = {}
    self._subparsers = None

  @staticmethod
  def from_instance(instance: t.Type[R]) -> 'Parser':
    parser = Parser(description=f'{instance.__name__} command-line interface')
    parser._process_class(instance, parser._parser)
    return parser

  def parse_args(self, args=None) -> dict:
    """Parse command line arguments and return a dictionary of parsed values."""
    if args is None:
      args = sys.argv[1:]
    elif isinstance(args, str):
      args = shlex.split(args)

    if self._subparsers is None:
      # Simple case - no subcommands
      temp_ns = argparse.Namespace()
      self._parser.parse_args(args, temp_ns)
      return vars(temp_ns)

    # Handle subcommands
    return self._parse_level(self._subparsers, args)

  def _process_class(self, cls: t.Type, parser: argparse.ArgumentParser):
    """Process a class's fields and properties for arguments."""
    # Process regular fields
    self._process_fields(cls, parser)

    # Process properties decorated with @property
    self._process_properties(cls, parser)

  def _process_fields(self, cls: t.Type, parser: argparse.ArgumentParser):
    """Process the fields of a class."""
    for field_name, field_type in t.get_type_hints(cls).items():
      field = getattr(cls, '__dataclass_fields__', {}).get(field_name)

      if hasattr(field_type, '__subcommand__'):
        # Handle subcommand field
        self._process_subcommand_field(field_name, field_type, parser)
      elif field and 'argument' in field.metadata:
        # Regular argument with explicit configuration
        self._add_argument(field_name, field_type, field.metadata['argument'], parser=parser)
      else:
        # Regular positional argument
        parser.add_argument(field_name, type=resolve_type(field_type))

  def _process_subcommand_field(
    self, field_name: str, field_type: t.Type, parser: argparse.ArgumentParser
  ):
    """Process a subcommand field."""
    # Create subparsers if needed for the current level
    if parser is self._parser and self._subparsers is None:
      self._subparsers = parser.add_subparsers(title='subcommands')

    # Get the right subparsers object
    subparsers = (
      self._subparsers if parser is self._parser else self._get_or_create_subparsers(parser)
    )

    # Create a parser for this subcommand
    assert subparsers is not None
    subparser = subparsers.add_parser(field_name, help=f'{field_name} command')

    # Track it if this is a top-level subcommand
    if parser is self._parser:
      self._subcommand_parsers[field_name] = subparser

    # Process the subcommand class recursively
    self._process_class(field_type, subparser)

  def _process_properties(self, cls: t.Type, parser: argparse.ArgumentParser):
    """Process class properties decorated with @property."""
    for member_name, member_value in getmembers(cls, isdatadescriptor):
      if member_name in getattr(cls, '__dataclass_fields__', {}):
        continue

      if hasattr(member_value, '__get__'):
        try:
          # Create a temporary instance to access the property
          temp_instance = cls(
            **{field_name: None for field_name in getattr(cls, '__dataclass_fields__', {})}
          )

          field = getattr(temp_instance, member_name)

          if not hasattr(field, 'metadata') or 'argument' not in field.metadata:
            continue

          argument = field.metadata['argument']
          field_type = self._get_property_type(member_value, argument, field)

          self._add_argument(member_name, field_type, argument, parser=parser)
          self._override_field_names.append(member_name)
        except Exception:
          pass

  def _get_property_type(self, member_value, argument, field):
    """Determine the type of a property."""
    return (
      argument.type
      or t.get_type_hints(
        getattr(getattr(member_value, 'fget'), '__func__', getattr(member_value, 'fget'))
      ).get('return')
      or field.default.__class__
    )

  def _get_or_create_subparsers(self, parser: argparse.ArgumentParser):
    """Get existing subparsers or create new ones for the parser."""
    for action in parser._actions:
      if isinstance(action, argparse._SubParsersAction):
        return action

    # No subparsers found, create new ones
    return parser.add_subparsers(title='subcommands')

  def _add_argument(
    self, field_name: str, field_type: t.Any, argument: Argument, parser=None
  ) -> None:
    """Add a standard argument to the specified parser."""
    if parser is None:
      parser = self._parser

    kwargs = argument.resolve_kwargs()
    resolved_type = resolve_type(field_type)

    if 'type' not in kwargs and resolved_type is not bool:
      kwargs['type'] = resolved_type

    if resolved_type is bool and 'type' in kwargs:
      del kwargs['type']

    if resolved_type is bool and 'action' not in kwargs:
      kwargs['action'] = 'store_true'

    if t.get_origin(field_type) is list and 'nargs' not in kwargs:
      kwargs['nargs'] = '+'

    if 'default' not in kwargs:
      kwargs['default'] = infer_default_value(field_type)

    if 'dest' not in kwargs and not argument.positional:
      kwargs['dest'] = field_name

    if 'required' in kwargs and argument.positional:
      del kwargs['required']

    if argument.name_or_flags:
      parser.add_argument(*argument.name_or_flags, **kwargs)
    else:
      parser.add_argument(field_name, **kwargs)

  def _parse_level(self, commands, args):
    """Parse arguments at a specific command level."""
    cmd_choices = commands.choices.keys()
    cmd_groups = self._group_args_by_command(args, cmd_choices)

    # Parse top-level arguments
    temp_ns = argparse.Namespace()
    self._parser.parse_args(cmd_groups.get(None, []), temp_ns)
    result = vars(temp_ns)

    # Initialize all command fields to None
    for cmd in cmd_choices:
      result[cmd] = None

    # Parse subcommand arguments
    for cmd, cmd_args in cmd_groups.items():
      if cmd is None:
        continue

      cmd_parser, subcmds = commands.choices[cmd], None

      # Find nested subparsers
      for action in cmd_parser._actions:
        if isinstance(action, argparse._SubParsersAction):
          subcmds = action
          break

      # Parse recursively if there are nested subcommands
      if subcmds and any(arg in subcmds.choices for arg in cmd_args):
        cmd_dict = self._parse_level(subcmds, cmd_args)
      else:
        # Parse normally
        temp_ns = argparse.Namespace()
        cmd_parser.parse_args(cmd_args, temp_ns)
        cmd_dict = vars(temp_ns)

      result[cmd] = cmd_dict

    return result

  def _group_args_by_command(self, args, command_choices):
    """Group arguments by command name."""
    result, current_cmd = {None: []}, None

    for arg in args:
      if arg in command_choices:
        current_cmd = arg
        if current_cmd not in result:
          result[current_cmd] = []
      elif current_cmd is None:
        result[None].append(arg)
      else:
        result[current_cmd].append(arg)

    return result

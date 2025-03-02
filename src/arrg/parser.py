import argparse
import shlex
import sys
import typing as t
from collections import defaultdict

from .argument import Argument
from .type_resolver import TypeResolver
from .utils import get_subcommand_type, is_subcommand_type

R = t.TypeVar('R')

ArgParser = argparse.ArgumentParser
ArgNamespace = argparse.Namespace
SubparsersAction = argparse._SubParsersAction


class Parser:
  def __init__(self, **parser_kwargs: t.Any):
    self._exit_on_error = parser_kwargs.pop('exit_on_error', True)
    self._override_field_names: t.List[str] = []
    self._parser: ArgParser = ArgParser(**parser_kwargs)
    self._processed_fields: t.Dict[ArgParser, t.Set[str]] = defaultdict(set)
    self._subparsers: t.Optional[SubparsersAction] = None

  @staticmethod
  def from_instance(instance: t.Type[R], **parser_kwargs: t.Any) -> 'Parser':
    if 'description' not in parser_kwargs:
      parser_kwargs['description'] = f'{instance.__name__} command-line interface'

    parser = Parser(**parser_kwargs)
    parser._process_class(instance, parser._parser)

    return parser

  def parse_args(
    self, args: t.Optional[t.Union[str, t.Sequence[str]]] = None
  ) -> t.Dict[str, t.Any]:
    if args is None:
      args = sys.argv[1:]
    elif isinstance(args, str):
      args = shlex.split(args)

    try:
      if self._subparsers is None:
        return self._parse_simple(args)
      else:
        return self._parse_level(self._subparsers, args)
    except SystemExit as e:
      if not self._exit_on_error:
        error_code = e.code if isinstance(e.code, int) else 1
        raise argparse.ArgumentError(None, f'Argument parsing error with code {error_code}') from e
      raise

  def _add_argument(
    self,
    field_name: str,
    field_type: t.Any,
    argument: Argument,
    parser: t.Optional[ArgParser] = None,
  ) -> None:
    if parser is None:
      parser = self._parser

    kwargs = argument.resolve_kwargs()

    self._prepare_argument_kwargs(field_name, field_type, argument, kwargs)

    if argument.name_or_flags:
      parser.add_argument(*argument.name_or_flags, **kwargs)
    else:
      parser.add_argument(field_name, **kwargs)

  def _find_subparsers(self, parser: ArgParser) -> t.Optional[SubparsersAction]:
    for action in parser._actions:
      if isinstance(action, SubparsersAction):
        return action

    return None

  def _get_or_create_subparsers(self, parser: ArgParser) -> SubparsersAction:
    for action in parser._actions:
      if isinstance(action, SubparsersAction):
        return action

    return parser.add_subparsers(title='subcommands')

  def _get_subparsers_for_parser(self, parser: ArgParser) -> SubparsersAction:
    if parser is self._parser:
      if self._subparsers is None:
        self._subparsers = parser.add_subparsers(title='subcommands')

      return self._subparsers

    return self._get_or_create_subparsers(parser)

  def _group_arguments_by_command(
    self, args: t.Sequence[str], command_choices: t.Iterable[str]
  ) -> t.Dict[t.Optional[str], t.List[str]]:
    result, current_cmd = defaultdict(list), None

    for arg in args:
      if arg in command_choices:
        current_cmd = arg
        result[current_cmd] = []
      elif current_cmd is None:
        result[None].append(arg)
      else:
        result[current_cmd].append(arg)

    return result

  def _parse_simple(self, args: t.Sequence[str]) -> t.Dict[str, t.Any]:
    temp_ns = ArgNamespace()
    self._parser.parse_args(args, temp_ns)
    return vars(temp_ns)

  def _parse_level(self, commands: SubparsersAction, args: t.Sequence[str]) -> t.Dict[str, t.Any]:
    cmd_choices = list(commands.choices.keys())

    cmd_groups = self._group_arguments_by_command(args, cmd_choices)

    result = self._parse_simple(cmd_groups[None])

    for cmd in cmd_choices:
      result[cmd] = None

    for cmd, cmd_args in cmd_groups.items():
      if cmd is None:
        continue

      cmd_parser = commands.choices[cmd]

      subcmds = self._find_subparsers(cmd_parser)

      if subcmds and any(arg in subcmds.choices for arg in cmd_args):
        cmd_dict = self._parse_level(subcmds, cmd_args)
      else:
        temp_ns = ArgNamespace()
        cmd_parser.parse_args(cmd_args, temp_ns)
        cmd_dict = vars(temp_ns)

      result[cmd] = cmd_dict

    return result

  def _prepare_argument_kwargs(
    self, field_name: str, field_type: t.Any, argument: Argument, kwargs: t.Dict[str, t.Any]
  ) -> None:
    resolved_type = TypeResolver.resolve(field_type)

    if 'type' not in kwargs and resolved_type is not bool:
      kwargs['type'] = resolved_type

    if resolved_type is bool:
      if 'type' in kwargs:
        del kwargs['type']
      if 'action' not in kwargs:
        kwargs['action'] = 'store_true'

    if t.get_origin(field_type) is list and 'nargs' not in kwargs:
      kwargs['nargs'] = '+'

    if 'dest' not in kwargs and not argument.positional:
      kwargs['dest'] = field_name

    if 'required' in kwargs and argument.positional:
      del kwargs['required']

  def _process_argument_field(
    self,
    cls: t.Type,
    field_name: str,
    field_type: t.Type,
    parser: ArgParser,
  ) -> None:
    field_value = getattr(cls, field_name, None)

    if field_value and hasattr(field_value, 'metadata') and 'argument' in field_value.metadata:
      self._add_argument(field_name, field_type, field_value.metadata['argument'], parser=parser)
      self._processed_fields[parser].add(field_name)
      return

    if hasattr(cls, '__dataclass_fields__') and field_name in cls.__dataclass_fields__:
      field = cls.__dataclass_fields__[field_name]

      if 'argument' in field.metadata:
        self._add_argument(field_name, field_type, field.metadata['argument'], parser=parser)
        self._processed_fields[parser].add(field_name)

  def _process_class(self, cls: t.Type, parser: ArgParser) -> None:
    classes_to_process = [c for c in cls.__mro__ if c is not object]

    for current_cls in reversed(classes_to_process):
      self._process_fields(current_cls, parser)

  def _process_fields(self, cls: t.Type, parser: ArgParser) -> None:
    annotations = getattr(cls, '__annotations__', {})

    for field_name, field_type in annotations.items():
      if field_name in self._processed_fields[parser]:
        continue

      if is_subcommand_type(field_type):
        actual_type = get_subcommand_type(field_type)
        self._process_subcommand_field(field_name, actual_type, parser)
        self._processed_fields[parser].add(field_name)
        continue

      self._process_argument_field(cls, field_name, field_type, parser)

  def _process_subcommand_field(
    self, field_name: str, field_type: t.Type, parser: ArgParser
  ) -> None:
    subcommand_config = getattr(field_type, '__subcommand_config__', {})

    subcommand_name = subcommand_config.pop('name', field_name)

    if 'help' not in subcommand_config:
      subcommand_config['help'] = f'{field_name} command'

    subparser = self._get_subparsers_for_parser(parser).add_parser(
      subcommand_name, **subcommand_config
    )

    self._process_class(field_type, subparser)

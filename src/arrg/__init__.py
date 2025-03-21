import typing as t
from dataclasses import dataclass
from dataclasses import field as dataclass_field

from .argument import Argument
from .constants import SUBCOMMAND_MARKER
from .parser import Parser
from .utils import get_subcommand_type, is_subcommand_type

R = t.TypeVar('R')
T = t.TypeVar('T', covariant=True)


def _set_default_subcommands(cls: t.Any) -> None:
  for field_name, field_type in getattr(cls, '__annotations__', {}).items():
    if is_subcommand_type(field_type):
      setattr(cls, field_name, None)


class AppProtocol(t.Protocol[T]):
  @staticmethod
  def from_args() -> T: ...

  @staticmethod
  def from_iter(args: t.Sequence[str]) -> T: ...


@t.overload
def app(cls: t.Type[R]) -> t.Type[AppProtocol[R]]: ...


@t.overload
def app(
  cls: None = None,
  *,
  add_help: bool = True,
  allow_abbrev: bool = True,
  argument_default: t.Optional[t.Any] = None,
  conflict_handler: t.Optional[str] = None,
  description: t.Optional[str] = None,
  epilog: t.Optional[str] = None,
  exit_on_error: bool = True,
  formatter_class: t.Optional[t.Type] = None,
  fromfile_prefix_chars: t.Optional[str] = None,
  parents: t.Optional[t.List[t.Any]] = None,
  prefix_chars: t.Optional[str] = None,
  prog: t.Optional[str] = None,
  usage: t.Optional[str] = None,
) -> t.Callable[[t.Type[R]], t.Type[AppProtocol[R]]]: ...


def app(
  cls: t.Optional[t.Type[R]] = None,
  *,
  add_help: bool = True,
  allow_abbrev: bool = True,
  argument_default: t.Optional[t.Any] = None,
  conflict_handler: t.Optional[str] = None,
  description: t.Optional[str] = None,
  epilog: t.Optional[str] = None,
  exit_on_error: bool = True,
  formatter_class: t.Optional[t.Type] = None,
  fromfile_prefix_chars: t.Optional[str] = None,
  parents: t.Optional[t.List[t.Any]] = None,
  prefix_chars: t.Optional[str] = None,
  prog: t.Optional[str] = None,
  usage: t.Optional[str] = None,
) -> t.Union[t.Type[AppProtocol[R]], t.Callable[[t.Type[R]], t.Type[AppProtocol[R]]]]:
  """
  Decorator to convert a class into a command-line application.

  Accepts all the same parameters as argparse.ArgumentParser.

  Args:
    cls: The class to decorate
    prog: The name of the program
    usage: A usage message
    description: A description of what the program does
    epilog: Text following the argument descriptions
    parents: Parsers whose arguments should be copied
    formatter_class: HelpFormatter class for printing help messages
    prefix_chars: Characters that prefix optional arguments
    fromfile_prefix_chars: Characters that prefix files containing additional arguments
    argument_default: The default value for all arguments
    conflict_handler: String indicating how to handle conflicts
    add_help: Add a -h/--help option
    allow_abbrev: Allow long options to be abbreviated unambiguously
    exit_on_error: Whether to exit with error info when an error occurs

  Returns:
    A decorated class or a decorator function
  """
  parser_kwargs = {
    'prog': prog,
    'usage': usage,
    'description': description,
    'epilog': epilog,
    'parents': parents,
    'formatter_class': formatter_class,
    'prefix_chars': prefix_chars,
    'fromfile_prefix_chars': fromfile_prefix_chars,
    'argument_default': argument_default,
    'conflict_handler': conflict_handler,
    'add_help': add_help,
    'allow_abbrev': allow_abbrev,
    'exit_on_error': exit_on_error,
  }

  parser_kwargs = {k: v for k, v in parser_kwargs.items() if v is not None}

  def decorator(cls: t.Type[R]) -> t.Type[AppProtocol[R]]:
    _set_default_subcommands(cls)

    cls = dataclass(cls)

    class App(cls):
      @staticmethod
      def from_args() -> 'cls':
        """Create an application instance from command-line arguments."""
        return create_instance_from_args(None)

      @staticmethod
      def from_iter(args: t.Sequence[str]) -> 'cls':
        """Create an application instance from an iterable of arguments."""
        return create_instance_from_args(args)

    def create_instance_from_args(args: t.Optional[t.Sequence[str]]) -> 'cls':
      parser = Parser.from_instance(cls, **parser_kwargs)

      return cls(
        **_process_parsed_args(
          cls,
          parser.parse_args(args),
        )
      )

    def _process_parsed_args(
      cls: t.Type,
      parsed_args: t.Dict[str, t.Any],
    ) -> t.Dict[str, t.Any]:
      instance_args: t.Dict[str, t.Any] = {}
      subcommand_args: t.Dict[str, t.Dict[str, t.Any]] = {}

      for name, value in list(parsed_args.items()):
        if isinstance(value, dict):
          subcommand_args[name] = value
        else:
          instance_args[name] = value

      def _find_subcommand(cls: t.Type, subcommand_name: str) -> t.Type | None:
        for field_name, field_type in getattr(cls, '__annotations__', {}).items():
          if field_name == subcommand_name and is_subcommand_type(field_type):
            return field_type

        for base in getattr(cls, '__bases__'):
          subcommand_type = _find_subcommand(base, subcommand_name)

          if subcommand_type is not None:
            return subcommand_type

        return None

      for name, args_dict in subcommand_args.items():
        subcommand_type = _find_subcommand(cls, name)

        if subcommand_type is None:
          continue

        if not args_dict:
          instance_args[name] = None
          continue

        actual_type = get_subcommand_type(subcommand_type)
        instance_args[name] = _process_subcommand(actual_type, args_dict)

      for name, field_type in cls.__annotations__.items():
        if is_subcommand_type(field_type) and name not in instance_args:
          instance_args[name] = None

      return instance_args

    def _process_subcommand(subcommand_type: t.Type, args_dict: t.Dict[str, t.Any]) -> t.Any:
      nested_subcommands: t.Dict[str, t.Dict[str, t.Any]] = {}

      for subcommand_name, value in list(args_dict.items()):
        if isinstance(value, dict) and subcommand_name in subcommand_type.__annotations__:
          nested_subcommands[subcommand_name] = value

      subcommand_instance = subcommand_type(**args_dict)

      for subcommand_name, subcommand_args in nested_subcommands.items():
        if subcommand_args:
          annotation_type = subcommand_type.__annotations__[subcommand_name]
          actual_type = get_subcommand_type(annotation_type)
          nested_instance = _process_subcommand(actual_type, subcommand_args)
          setattr(subcommand_instance, subcommand_name, nested_instance)

      return subcommand_instance

    App.__name__ = cls.__name__

    return t.cast(t.Type[AppProtocol[R]], App)

  if cls is None:
    return decorator

  return decorator(cls)


def argument(*name_or_flags: str, **kwargs: t.Any) -> t.Any:
  """
  Create an argument field with custom configuration.

  Args:
    *name_or_flags: Argument name(s) or flag(s)
    **kwargs: Additional arguments for argparse.add_argument

  Returns:
    A field with custom configuration
  """
  return dataclass_field(
    default_factory=lambda: kwargs.get('default', None),
    metadata={'argument': Argument(*name_or_flags, **kwargs)},
  )


@t.overload
def subcommand(cls: t.Type[R]) -> t.Type[R]: ...


@t.overload
def subcommand(
  cls: None = None,
  *,
  add_help: t.Optional[bool] = None,
  aliases: t.Optional[t.Sequence[str]] = None,
  allow_abbrev: t.Optional[bool] = None,
  argument_default: t.Optional[t.Any] = None,
  conflict_handler: t.Optional[str] = None,
  description: t.Optional[str] = None,
  epilog: t.Optional[str] = None,
  exit_on_error: t.Optional[bool] = None,
  formatter_class: t.Optional[t.Type] = None,
  fromfile_prefix_chars: t.Optional[str] = None,
  help: t.Optional[str] = None,
  name: t.Optional[str] = None,
  parents: t.Optional[t.Sequence[t.Any]] = None,
  prefix_chars: t.Optional[str] = None,
  prog: t.Optional[str] = None,
  usage: t.Optional[str] = None,
) -> t.Callable[[t.Type[R]], t.Type[R]]: ...


def subcommand(
  cls: t.Optional[t.Type[R]] = None,
  *,
  add_help: t.Optional[bool] = None,
  aliases: t.Optional[t.Sequence[str]] = None,
  allow_abbrev: t.Optional[bool] = None,
  argument_default: t.Optional[t.Any] = None,
  conflict_handler: t.Optional[str] = None,
  description: t.Optional[str] = None,
  epilog: t.Optional[str] = None,
  exit_on_error: t.Optional[bool] = None,
  formatter_class: t.Optional[t.Type] = None,
  fromfile_prefix_chars: t.Optional[str] = None,
  help: t.Optional[str] = None,
  name: t.Optional[str] = None,
  parents: t.Optional[t.Sequence[t.Any]] = None,
  prefix_chars: t.Optional[str] = None,
  prog: t.Optional[str] = None,
  usage: t.Optional[str] = None,
) -> t.Union[t.Type[R], t.Callable[[t.Type[R]], t.Type[R]]]:
  """
  Decorator to mark a class as a subcommand with optional configuration.

  Args:
    cls: The class to decorate
    name: Optional explicit name for the subcommand (defaults to class name in lowercase)
    deprecated: Whether the subcommand is deprecated
    help: Help text for the subcommand
    aliases: Alternative names for the subcommand
    prog: The name of the program
    usage: A usage message
    description: A description of what the program does
    epilog: Text following the argument descriptions
    parents: Parsers whose arguments should be copied
    formatter_class: HelpFormatter class for printing help messages
    prefix_chars: Characters that prefix optional arguments
    fromfile_prefix_chars: Characters that prefix files containing additional arguments
    argument_default: The default value for all arguments
    conflict_handler: String indicating how to handle conflicts
    add_help: Add a -h/--help option
    allow_abbrev: Allow long options to be abbreviated unambiguously
    exit_on_error: Whether to exit with error info when an error occurs
    **kwargs: Additional keyword arguments for the subparser

  Returns:
    The decorated class or a decorator function
  """
  parser_kwargs = {
    'name': name,
    'help': help,
    'aliases': aliases,
    'prog': prog,
    'usage': usage,
    'description': description,
    'epilog': epilog,
    'parents': parents,
    'formatter_class': formatter_class,
    'prefix_chars': prefix_chars,
    'fromfile_prefix_chars': fromfile_prefix_chars,
    'argument_default': argument_default,
    'conflict_handler': conflict_handler,
    'add_help': add_help,
    'allow_abbrev': allow_abbrev,
    'exit_on_error': exit_on_error,
  }

  parser_kwargs = {k: v for k, v in parser_kwargs.items() if v is not None}

  def decorator(cls: t.Type[R]) -> t.Type[R]:
    _set_default_subcommands(cls)

    cls = dataclass(cls)

    setattr(cls, SUBCOMMAND_MARKER, True)

    if parser_kwargs:
      setattr(cls, '__subcommand_config__', parser_kwargs)

    return cls

  if cls is None:
    return decorator

  return decorator(cls)


__all__ = ['app', 'argument', 'subcommand']

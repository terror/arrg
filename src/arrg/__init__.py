import types
import typing as t
from dataclasses import dataclass, is_dataclass
from dataclasses import field as dataclass_field

from .argument import Argument
from .parser import Parser

R = t.TypeVar('R')
T = t.TypeVar('T', covariant=True)


class AppProtocol(t.Protocol[T]):
  @staticmethod
  def from_args() -> T: ...

  @staticmethod
  def from_iter(args: t.Sequence[str]) -> T: ...


def _is_subcommand_type(field_type: t.Type) -> bool:
  if hasattr(field_type, '__subcommand__'):
    return True

  origin = t.get_origin(field_type)

  if origin is t.Union:
    args = t.get_args(field_type)

    for arg in args:
      if arg is not type(None) and hasattr(arg, '__subcommand__'):
        return True

  return False


def _get_actual_subcommand_type(field_type: t.Type) -> t.Type:
  if hasattr(field_type, '__subcommand__'):
    return field_type

  origin = t.get_origin(field_type)

  if origin is t.Union:
    args = t.get_args(field_type)

    for arg in args:
      if arg is not type(None) and hasattr(arg, '__subcommand__'):
        return arg

  return field_type


def app(
  cls: t.Optional[t.Type[R]] = None,
  *,
  prog: t.Optional[str] = None,
  usage: t.Optional[str] = None,
  description: t.Optional[str] = None,
  epilog: t.Optional[str] = None,
  parents: t.Optional[t.List[t.Any]] = None,
  formatter_class: t.Optional[t.Type] = None,
  prefix_chars: t.Optional[str] = None,
  fromfile_prefix_chars: t.Optional[str] = None,
  argument_default: t.Optional[t.Any] = None,
  conflict_handler: t.Optional[str] = None,
  add_help: bool = True,
  allow_abbrev: bool = True,
  exit_on_error: bool = True,
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
  parser_params = {
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

  parser_params = {k: v for k, v in parser_params.items() if v is not None}

  def decorator(cls_inner: t.Type[R]) -> t.Type[AppProtocol[R]]:
    for base in cls_inner.__bases__:
      if hasattr(base, '__subcommand__'):
        setattr(cls_inner, '__subcommand__', True)

    if not is_dataclass(cls_inner):
      cls_inner = dataclass(cls_inner)

    def build_app(args: t.Optional[t.Sequence[str]]) -> 'App':
      parser = Parser.from_instance(cls_inner, **parser_params)

      parsed_args = parser.parse_args(args)

      instance_args, overrides = _process_parsed_args(
        cls_inner, parsed_args, parser._override_field_names
      )

      app_instance = App(cls_inner(**instance_args), overrides)

      _attach_methods(cls_inner, app_instance)

      return app_instance

    def _process_parsed_args(
      cls_type: t.Type, parsed_args: t.Dict[str, t.Any], override_fields: t.List[str]
    ) -> t.Tuple[t.Dict[str, t.Any], t.Dict[str, t.Any]]:
      instance_args: t.Dict[str, t.Any] = {}
      subcommand_args: t.Dict[str, t.Dict[str, t.Any]] = {}
      overrides: t.Dict[str, t.Any] = {}

      for name, value in list(parsed_args.items()):
        if isinstance(value, dict) and name in cls_type.__annotations__:
          subcommand_args[name] = value
        else:
          if name in override_fields:
            overrides[name] = parsed_args.pop(name)
          else:
            instance_args[name] = value

      for name, args_dict in subcommand_args.items():
        subcommand_type = cls_type.__annotations__[name]

        if not args_dict:
          instance_args[name] = None
          continue

        actual_type = _get_actual_subcommand_type(subcommand_type)
        instance_args[name] = _process_subcommand(actual_type, args_dict)

      for name, field_type in cls_type.__annotations__.items():
        if _is_subcommand_type(field_type) and name not in instance_args:
          instance_args[name] = None

      return instance_args, overrides

    def _process_subcommand(subcommand_type: t.Type, args_dict: t.Dict[str, t.Any]) -> t.Any:
      nested_subcommands: t.Dict[str, t.Dict[str, t.Any]] = {}

      for subcommand_name, value in list(args_dict.items()):
        if isinstance(value, dict) and subcommand_name in subcommand_type.__annotations__:
          nested_subcommands[subcommand_name] = value

      subcommand_instance = subcommand_type(**args_dict)

      for subcommand_name, subcommand_args in nested_subcommands.items():
        if subcommand_args:  # Skip if the subcommand wasn't provided
          annotation_type = subcommand_type.__annotations__[subcommand_name]
          actual_type = _get_actual_subcommand_type(annotation_type)
          nested_instance = _process_subcommand(actual_type, subcommand_args)
          setattr(subcommand_instance, subcommand_name, nested_instance)

      return subcommand_instance

    def _attach_methods(cls_type: t.Type, app_instance: 'App') -> None:
      for name, attr in cls_type.__dict__.items():
        if callable(attr):
          setattr(app_instance, name, types.MethodType(attr, app_instance))

    class App:
      """Application instance wrapper that handles attribute overrides."""

      def __init__(self, instance: R, overrides: t.Optional[t.Dict[str, t.Any]] = None):
        self._instance: R = instance
        self._overrides: t.Dict[str, t.Any] = overrides or {}

      def __getattr__(self, name: str) -> t.Any:
        if name in self._overrides:
          return self._overrides[name]
        return getattr(self._instance, name)

      @staticmethod
      def from_args() -> 'App':
        """Create an application instance from command-line arguments."""
        return build_app(None)

      @staticmethod
      def from_iter(args: t.Sequence[str]) -> 'App':
        """Create an application instance from an iterable of arguments."""
        return build_app(args)

    setattr(App, '__name__', getattr(cls_inner, '__name__'))

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
  """
  return dataclass_field(
    default=kwargs.get('default', None), metadata={'argument': Argument(*name_or_flags, **kwargs)}
  )


def _has_subcommand_parent(cls: t.Type) -> bool:
  for base in cls.__bases__:
    if hasattr(base, '__subcommand__') and getattr(base, '__subcommand__'):
      return True

  return False


def subcommand(cls: t.Type[R]) -> t.Type[R]:
  """
  Decorator to mark a class as a subcommand.

  Ensures proper inheritance of dataclass fields.
  """
  current_annotations = getattr(cls, '__annotations__', {})

  for field_name, field_type in current_annotations.items():
    if hasattr(cls, field_name):
      continue

    if _is_subcommand_type(field_type):
      setattr(cls, field_name, None)

  if _has_subcommand_parent(cls):
    result_cls = dataclass(cls)

    for field_name, _ in current_annotations.items():
      if field_name not in getattr(result_cls, '__dataclass_fields__'):
        setattr(
          result_cls,
          field_name,
          dataclass_field(
            default=None, metadata={'argument': getattr(cls, field_name).metadata['argument']}
          ),
        )
  else:
    result_cls = dataclass(cls) if not is_dataclass(cls) else cls

  setattr(result_cls, '__subcommand__', True)

  return result_cls


__all__ = ['app', 'argument', 'subcommand']

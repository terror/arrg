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


def app(cls: t.Type[R]) -> t.Type[AppProtocol[R]]:
  """
  Decorator to convert a class into a command-line application.
  """
  if not is_dataclass(cls):
    cls = dataclass(cls)

  def build_app(args: t.Sequence[str] | None) -> 'App':
    parser = Parser.from_instance(cls)

    parsed_args = parser.parse_args(args)

    # Process the parsed arguments to create the app instance
    instance_args, overrides = _process_parsed_args(cls, parsed_args, parser._override_field_names)
    app_instance = App(cls(**instance_args), overrides)

    # Attach methods from the original class to the app instance
    _attach_methods(cls, app_instance)

    return app_instance

  def _process_parsed_args(cls_type, parsed_args, override_fields):
    """
    Process parsed arguments and separate regular args from overrides and subcommands.
    Returns a tuple of (args_for_instantiation, override_values).
    """
    instance_args = {}
    subcommand_args = {}
    overrides = {}

    # Separate arguments into different categories
    for name, value in list(parsed_args.items()):
      if isinstance(value, dict) and name in cls_type.__annotations__:
        # This is a subcommand
        subcommand_args[name] = value
      else:
        # This is a regular argument or override
        if name in override_fields:
          overrides[name] = parsed_args.pop(name)
        else:
          instance_args[name] = value

    for name, args_dict in subcommand_args.items():
      subcommand_type = cls_type.__annotations__[name]

      if not args_dict:
        instance_args[name] = None
        continue

      # Process nested subcommands
      subcommand_instance = _process_subcommand(subcommand_type, args_dict)
      instance_args[name] = subcommand_instance

    return instance_args, overrides

  def _process_subcommand(subcommand_type, args_dict):
    """Process a subcommand and its nested subcommands."""
    nested_subcommands = {}

    for subname, subvalue in list(args_dict.items()):
      if isinstance(subvalue, dict) and subname in subcommand_type.__annotations__:
        nested_subcommands[subname] = subvalue

    subcommand_instance = subcommand_type(**args_dict)

    for subname, subargs in nested_subcommands.items():
      if subargs:  # Skip if the subcommand wasn't provided
        subtype = subcommand_type.__annotations__[subname]
        nested_instance = _process_subcommand(subtype, subargs)
        setattr(subcommand_instance, subname, nested_instance)

    return subcommand_instance

  def _attach_methods(cls_type, app_instance):
    """Attach methods from the original class to the app instance."""
    for name, attr in cls_type.__dict__.items():
      if callable(attr):
        setattr(app_instance, name, types.MethodType(attr, app_instance))

  class App:
    """Application instance wrapper that handles attribute overrides."""

    def __init__(self, instance, overrides=None):
      self._instance = instance
      self._overrides = overrides or {}

    def __getattr__(self, name):
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

  setattr(App, '__name__', getattr(cls, '__name__'))

  return t.cast(t.Type[AppProtocol[R]], App)


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


def subcommand(cls: t.Type[R]) -> t.Type[R]:
  """
  Decorator to mark a class as a subcommand.
  """
  if not is_dataclass(cls):
    cls = dataclass(cls)

  setattr(cls, '__subcommand__', True)

  return cls


__all__ = ['app', 'argument', 'subcommand']

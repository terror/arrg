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
  if not is_dataclass(cls):
    cls = dataclass(cls)

  def build_app(args: t.Sequence[str] | None) -> 'App':
    parser = Parser.from_instance(cls)

    parsed_args = vars(parser.get_argument_parser().parse_args(args))

    attribute_overrides = {
      name: parsed_args.pop(name) for name in parser._optional_argument_field_names
    }

    app_instance = App(cls(**parsed_args), attribute_overrides)

    for name, attr in cls.__dict__.items():
      if callable(attr):
        setattr(app_instance, name, types.MethodType(attr, app_instance))

    return app_instance

  class App:
    def __init__(self, instance, attribute_overrides=None):
      self._instance = instance
      self._attribute_overrides = attribute_overrides or {}

    def __getattr__(self, name):
      return (
        self._attribute_overrides[name]
        if name in self._attribute_overrides
        else getattr(self._instance, name)
      )

    @staticmethod
    def from_args() -> 'App':
      return build_app(None)

    @staticmethod
    def from_iter(args: t.Sequence[str]) -> 'App':
      return build_app(args)

  setattr(App, '__name__', getattr(cls, '__name__'))

  return t.cast(t.Type[AppProtocol[R]], App)


def argument(*name_or_flags: str, **kwargs: t.Any) -> t.Any:
  return dataclass_field(
    default=kwargs.get('default', None), metadata={'argument': Argument(*name_or_flags, **kwargs)}
  )


def subcommand(cls: t.Type[R]) -> t.Type[R]:
  if not is_dataclass(cls):
    cls = dataclass(cls)

  setattr(cls, '__subcommand__', True)

  return cls


__all__ = ['app', 'argument', 'subcommand']

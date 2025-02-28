import types
import typing as t
from argparse import Action, ArgumentParser
from dataclasses import dataclass, is_dataclass
from dataclasses import field as dataclass_field
from inspect import getmembers, isdatadescriptor
from typing import get_args, get_origin

R = t.TypeVar('R')
T = t.TypeVar('T', covariant=True)


class AppProtocol(t.Protocol[T]):
  @staticmethod
  def from_args() -> T: ...

  @staticmethod
  def from_iter(args: t.Sequence[str]) -> T: ...


class Option:
  def __init__(
    self,
    *name_or_flags: str,
    action: t.Optional[t.Union[str, t.Type[Action]]] = None,
    nargs: t.Optional[t.Union[int, str]] = None,
    const: t.Any = None,
    default: t.Any = None,
    type: t.Optional[t.Callable] = None,
    choices: t.Optional[t.Iterable[t.Any]] = None,
    required: bool = False,
    help: t.Optional[str] = None,
    metavar: t.Optional[t.Union[str, tuple[str, ...]]] = None,
    dest: t.Optional[str] = None,
    version: t.Optional[str] = None,
    **kwargs: t.Any,
  ):
    self.name_or_flags = name_or_flags
    self.action = action
    self.nargs = nargs
    self.const = const
    self.default = default
    self.type = type
    self.choices = choices
    self.required = required
    self.help = help
    self.metavar = metavar
    self.dest = dest
    self.version = version
    self.kwargs = kwargs

  def keyword_arguments(self):
    kwargs = {}

    for attribute, value in vars(self).items():
      if attribute == 'name_or_flags':
        continue

      if attribute == 'kwargs':
        kwargs.update(value)
        continue

      if value is not None:
        kwargs[attribute] = value

    return kwargs


def _build_parser(cls) -> ArgumentParser:
  parser = ArgumentParser(description=f'{cls.__name__} command-line interface')

  def _add_positional(field_name: str, field_type: t.Any):
    parser.add_argument(field_name, type=_resolve_type(field_type))

  def _add_option(field_name: str, field_type: t.Any, option: Option):
    kwargs = option.keyword_arguments()

    if 'type' not in kwargs and field_type is not bool:
      kwargs['type'] = _resolve_type(field_type)

    if get_origin(field_type) is list and 'nargs' not in kwargs:
      kwargs['nargs'] = '+'

    if 'dest' not in kwargs:
      kwargs['dest'] = field_name

    if option.name_or_flags:
      parser.add_argument(*option.name_or_flags, **kwargs)
    else:
      parser.add_argument(f'--{field_name}', **kwargs)

  # Process regular dataclass fields, i.e.
  #
  # ```
  # @dataclass
  # class Foo:
  #   field_name: field_type
  #   ...
  # ```
  #
  # If `option` is present in this fields metadata we should
  # add it as an option, otherwise add it as a positional argument.
  for field_name, field_type in t.get_type_hints(cls).items():
    field = getattr(cls, '__dataclass_fields__').get(field_name)

    if field and 'option' in field.metadata:
      _add_option(field_name, field_type, field.metadata['option'])
    else:
      _add_positional(field_name, field_type)

  # Process properties that are not part of the regular dataclass fields.
  #
  # This handles cases like:
  #
  # ```
  # @dataclass
  # class Foo:
  #   foo: int
  #
  #   @property
  #   def count(self) -> int:
  #     return option('--count', default=0)
  # ```
  #
  # The goal here is to essentially override the existing `count` return value
  # with the value parsed from the command-line arguments via `argparse`.
  #
  # We achieve this by creating a temporary instance of the class and evaluating
  # the property, then adding it as an option if it has the `option` metadata. Then
  # later we can override the value with the parsed value.
  for member_name, member_value in getmembers(cls, isdatadescriptor):
    if member_name in getattr(cls, '__dataclass_fields__'):
      continue

    if hasattr(member_value, '__get__'):
      try:
        field = getattr(cls(), member_name)

        if 'option' in field.metadata:
          _add_option(member_name, field.default.__class__, field.metadata['option'])
      except Exception:
        # Skip properties that don't return an option or can't be evaluated.
        pass

  return parser


def _resolve_type(field_type: t.Any) -> t.Callable:
  """
  Convert Python type annotations to callable type converters for argparse.
  This function analyzes Python type hints and returns an appropriate callable
  that argparse can use to convert command-line string arguments to the correct type.

  Args:
    field_type: A Python type annotation
      (can be a simple type like `int`, or a complex type like `list[int]`, `Optional[float]`, etc.)

  Returns:
    A callable that can convert a string to the appropriate type for argparse.
    Defaults to `str` if the type cannot be resolved.
  """
  match field_type:
    case _ if get_origin(field_type) is list:
      args = get_args(field_type)

      if args and args[0] != t.Any:
        return _resolve_type(args[0])

      return str

    case _ if get_origin(field_type) is t.Union:
      args = get_args(field_type)

      if type(None) in args:
        non_none_args = [arg for arg in args if arg is not type(None)]

        if non_none_args:
          return _resolve_type(non_none_args[0])

      return str

    case type() as cls:
      return cls

    case _ if field_type is bool:
      return bool

    case _:
      return str


def app(cls: t.Type[R]) -> t.Type[AppProtocol[R]]:
  if not is_dataclass(cls):
    cls = dataclass(cls)

  def initialize(args: t.Sequence[str] | None) -> 'App':
    parser = _build_parser(cls)

    parsed_args = vars(parser.parse_args(args=args))

    property_values = {
      name: parsed_args.pop(name)
      for name in [name for name in parsed_args if name not in getattr(cls, '__dataclass_fields__')]
    }

    app_instance = App(cls(**parsed_args), property_values)

    # Copy methods from original class to this new instance.
    #
    # When methods are called on this new instance, we want them to reference
    # `self` on the `App` wrapper instance, not the original class instance.
    for name, attr in cls.__dict__.items():
      if callable(attr) and not name.startswith('__') and not isinstance(attr, property):
        setattr(app_instance, name, types.MethodType(attr, app_instance))

    return app_instance

  class App:
    def __init__(self, instance, property_overrides=None):
      self._instance = instance
      self._property_overrides = property_overrides or {}

    def __getattr__(self, name):
      if name in self._property_overrides:
        return self._property_overrides[name]

      return getattr(self._instance, name)

    @staticmethod
    def from_args() -> 'App':
      return initialize(None)

    @staticmethod
    def from_iter(args: t.Sequence[str]) -> 'App':
      return initialize(args)

  setattr(App, '__name__', getattr(cls, '__name__'))

  return t.cast(t.Type[AppProtocol[R]], App)


def option(*name_or_flags: str, **kwargs: t.Any) -> t.Any:
  option = Option(*name_or_flags, **kwargs)

  default_value = kwargs.get('default', None)

  if kwargs.get('action') == 'store_true':
    default_value = False
  elif kwargs.get('action') == 'store_false':
    default_value = True

  return dataclass_field(default=default_value, metadata={'option': option})


def subcommand(cls: t.Type[R]) -> t.Type[R]:
  if not is_dataclass(cls):
    cls = dataclass(cls)

  setattr(cls, '__subcommand__', True)

  return cls


__all__ = ['app', 'option']
